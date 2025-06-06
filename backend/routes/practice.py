"""
练习相关的路由模块 - 性能优化版本
"""
import json
import logging
import random
import threading
import time
from collections import defaultdict
from functools import lru_cache, wraps
from typing import Dict, List, Optional, Any

from flask import Blueprint, request, jsonify, session
from werkzeug.exceptions import BadRequest, NotFound

from ..RedisManager import redis_manager
from ..config import SESSION_KEYS, QUESTION_STATUS
from ..connectDB import (
    get_questions_by_tiku, get_user_practice_history, get_tiku_by_subject, get_all_subjects,
    get_question_by_db_id
)
from ..decorators import handle_api_error, login_required
from ..session_manager import (
    get_session_value, set_session_value, clear_practice_session,
    get_current_tiku_info,
    create_and_store_practice_session, complete_current_practice_session, check_and_resume_practice_session,
    get_user_session_info
)
from ..utils import create_response, format_answer_display, validate_answer

logger = logging.getLogger(__name__)

# 创建蓝图
practice_bp = Blueprint('practice', __name__, url_prefix='/api')

# 题库使用统计 - 使用defaultdict优化
tiku_usage_stats = defaultdict(int)
usage_stats_lock = threading.Lock()

# 题型常量定义
QUESTION_TYPE_SINGLE = 'single_choice'
QUESTION_TYPE_MULTIPLE = 'multiple_choice'
QUESTION_TYPE_JUDGMENT = 'judgment'
QUESTION_TYPE_OTHER = 'other'

# 题型映射 - 预计算提升性能
QUESTION_TYPE_MAPPING = {
    'multiple_choice': {'keywords': ['多选题'], 'is_multiple': True},
    'judgment': {'keywords': ['判断题', 'judgment', 'true_false', 'tf'], 'is_multiple': False},
    'single_choice': {'keywords': ['单选题', 'single_choice', 'choice', 'sc'], 'is_multiple': False},
    'other': {'keywords': [], 'is_multiple': False}
}


# 基于Redis的缓存管理器
class RedisCacheManager:
    """基于Redis的缓存管理器"""

    def __init__(self):
        self.redis_manager = redis_manager
        self._cache_ttl = 3600  # 1小时TTL
        self._cache_prefix = 'cache:'

    def _get_cache_key(self, key: str) -> str:
        """生成缓存键"""
        return f"{self._cache_prefix}{key}"

    def _is_redis_available(self) -> bool:
        """检查Redis是否可用"""
        return self.redis_manager.is_available

    def _get_from_redis(self, key: str, default=None):
        """从Redis获取数据"""
        if not self._is_redis_available():
            return default

        try:
            redis_key = self._get_cache_key(key)
            data = self.redis_manager._redis_client.get(redis_key)
            if data is None:
                return default
            return json.loads(data)
        except Exception as e:
            logger.error(f"从Redis获取缓存失败 {key}: {e}")
            return default

    def _set_to_redis(self, key: str, value, ttl: int = None):
        """存储数据到Redis"""
        if not self._is_redis_available():
            return False

        try:
            redis_key = self._get_cache_key(key)
            data = json.dumps(value, ensure_ascii=False)
            if ttl is None:
                ttl = self._cache_ttl
            self.redis_manager._redis_client.setex(redis_key, ttl, data)
            return True
        except Exception as e:
            logger.error(f"存储缓存到Redis失败 {key}: {e}")
            return False

    def _delete_from_redis(self, key: str):
        """从Redis删除数据"""
        if not self._is_redis_available():
            return False

        try:
            redis_key = self._get_cache_key(key)
            self.redis_manager._redis_client.delete(redis_key)
            return True
        except Exception as e:
            logger.error(f"从Redis删除缓存失败 {key}: {e}")
            return False

    def get_tiku_list(self):
        """获取缓存的题库列表"""
        cache_key = 'tiku_list'
        cached_data = self._get_from_redis(cache_key)

        if cached_data is not None:
            logger.debug("使用Redis缓存的题库列表数据")
            return cached_data

        logger.info("从数据库重新加载题库列表")
        try:
            # 并行获取数据
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                future_tiku = executor.submit(get_tiku_by_subject)
                future_subjects = executor.submit(get_all_subjects)

                db_tiku_list = future_tiku.result()
                all_subjects = future_subjects.result()

            subjects_exam_time = {s['subject_name']: s['exam_time'] for s in all_subjects}

            cache_data = {
                'tiku_list': db_tiku_list,
                'subjects_exam_time': subjects_exam_time
            }

            # 存储到Redis
            self._set_to_redis(cache_key, cache_data)
            logger.info(f"成功加载并缓存了 {len(db_tiku_list)} 个题库到Redis")
            return cache_data

        except Exception as e:
            logger.error(f"从数据库加载题库列表失败: {e}")
            raise

    def get_file_options(self):
        """获取缓存的文件选项数据"""
        cache_key = 'file_options'
        cached_data = self._get_from_redis(cache_key)

        if cached_data is not None:
            logger.debug("使用Redis缓存的文件选项数据")
            return cached_data

        logger.info("重新构建文件选项缓存")
        try:
            cached_tiku_data = self.get_tiku_list()
            db_tiku_list = cached_tiku_data['tiku_list']
            subjects_exam_time = cached_tiku_data['subjects_exam_time']

            # 使用defaultdict优化数据处理
            db_tiku_map = defaultdict(lambda: {'files': [], 'exam_time': None})

            for tiku in db_tiku_list:
                if not tiku['is_active']:
                    continue

                subject_name = tiku['subject_name']
                if db_tiku_map[subject_name]['exam_time'] is None:
                    db_tiku_map[subject_name]['exam_time'] = subjects_exam_time.get(subject_name)

                db_tiku_map[subject_name]['files'].append({
                    'key': tiku['tiku_position'],
                    'display': tiku['tiku_name'],
                    'count': tiku['tiku_nums'],
                    'file_size': tiku['file_size'],
                    'updated_at': tiku['updated_at'],
                    'tiku_id': tiku['tiku_id']
                })

            # 批量排序优化
            sorted_subjects = {
                subject: {
                    'files': sorted(data['files'], key=lambda x: x['display']),
                    'exam_time': data['exam_time']
                }
                for subject, data in sorted(db_tiku_map.items())
            }

            # 存储到Redis
            self._set_to_redis(cache_key, sorted_subjects)
            logger.info(f"成功处理并缓存了 {len(sorted_subjects)} 个科目的文件选项到Redis")
            return sorted_subjects

        except Exception as e:
            logger.error(f"处理文件选项缓存失败: {e}")
            raise

    def get_question_bank(self, tiku_id: int) -> List[Dict[str, Any]]:
        """获取指定题库的题目列表，使用Redis缓存"""
        cache_key = f'question_bank_{tiku_id}'
        cached_data = self._get_from_redis(cache_key)

        if cached_data is not None:
            logger.debug(f"使用Redis缓存的题库ID列表，题库ID: {tiku_id}")
            # 从缓存的ID列表获取完整题目数据
            question_ids = cached_data.get('question_ids', [])
            questions_data = []

            for question_id in question_ids:
                question_data = self.get_question_by_id(question_id)
                if question_data:
                    questions_data.append(question_data)
                else:
                    logger.warning(f"题目 {question_id} 在缓存中不存在，将从数据库重新加载")

            if len(questions_data) == len(question_ids):
                return questions_data
            else:
                logger.warning(f"题库 {tiku_id} 缓存不完整，重新从数据库加载")

        logger.info(f"从数据库获取题库 {tiku_id} 的题目数据")
        try:
            # 从数据库获取题目列表
            question_bank_list = get_questions_by_tiku(tiku_id)

            if not question_bank_list:
                logger.warning(f"题库 {tiku_id} 为空或不存在")
                return []

            # 提取题目ID列表用于题库缓存
            question_ids = []

            # 缓存每道题的完整数据
            for question in question_bank_list:
                question_id = question['id']
                question_ids.append(question_id)

                # 缓存单个题目数据
                question_cache_key = f'question_{question_id}'
                self._set_to_redis(question_cache_key, question, ttl=10800)  # 3小时

            # 缓存题库的ID列表（而不是完整数据）
            tiku_cache_data = {
                'question_ids': question_ids,
                'total_count': len(question_ids),
                'cached_at': time.time()
            }
            self._set_to_redis(cache_key, tiku_cache_data, ttl=7200)  # 2小时

            logger.info(f"成功缓存题库 {tiku_id} 的 {len(question_ids)} 道题目ID列表到Redis")
            logger.info(f"同时缓存了 {len(question_bank_list)} 道题目的完整数据")

            return question_bank_list

        except Exception as e:
            logger.error(f"获取题库 {tiku_id} 的题目数据失败: {e}")
            return []

    def get_question_by_id(self, question_id: int) -> Optional[Dict[str, Any]]:
        """根据题目ID获取单个题目，使用Redis缓存"""
        cache_key = f'question_{question_id}'
        cached_data = self._get_from_redis(cache_key)

        if cached_data is not None:
            return cached_data

        logger.debug(f"从数据库获取题目 {question_id} 的数据")
        try:
            # 从数据库获取单个题目
            question_data = get_question_by_db_id(question_id)

            if not question_data:
                logger.warning(f"题目 {question_id} 不存在或已禁用")
                return None

            # 存储到Redis，单个题目缓存时间更长
            self._set_to_redis(cache_key, question_data, ttl=10800)  # 3小时
            logger.debug(f"成功缓存题目 {question_id} 到Redis")
            return question_data

        except Exception as e:
            logger.error(f"获取题目 {question_id} 的数据失败: {e}")
            return None

    def get_question_ids_by_tiku(self, tiku_id: int) -> List[int]:
        """获取题库的题目ID列表（仅ID，用于轻量级操作）"""
        cache_key = f'question_bank_{tiku_id}'
        cached_data = self._get_from_redis(cache_key)

        if cached_data is not None:
            return cached_data.get('question_ids', [])

        # 如果缓存中没有，从数据库获取并建立缓存
        question_bank = self.get_question_bank(tiku_id)
        return [q['id'] for q in question_bank]

    def refresh_one_question(self, question_id: int) -> bool:
        """刷新单道题目的缓存"""

        if not isinstance(question_id, int) or question_id <= 0:
            logger.error(f"无效的题目ID: {question_id}")
            return False

        cache_key = f'question_{question_id}'
        try:
            # 从数据库获取题目数据
            question_data = get_question_by_db_id(question_id)

            if not question_data:
                logger.warning(f"题目 {question_id} 不存在或已禁用，删除其缓存")
                # 如果题目不存在，删除可能存在的缓存
                self._delete_from_redis(cache_key)
                return False

            # 设置缓存，使用与其他单题目缓存相同的TTL
            success = self._set_to_redis(cache_key, question_data, ttl=10800)  # 3小时

            if success:
                logger.debug(f"成功刷新题目 {question_id} 的缓存")
                return True
            else:
                logger.error(f"设置题目 {question_id} 缓存到Redis失败")
                return False

        except Exception as e:
            logger.error(f"刷新题目 {question_id} 缓存时发生异常: {e}")
            return False

    def refresh_all_cache(self):
        """刷新所有缓存"""
        logger.info("开始刷新所有Redis缓存")

        try:
            # 如果Redis不可用，直接返回
            if not self._is_redis_available():
                logger.warning("Redis不可用，无法刷新缓存")
                return {
                    'tiku_count': 0,
                    'subjects_count': 0,
                    'prewarmed_questions': 0,
                    'message': 'Redis不可用，缓存刷新失败'
                }

            # 删除所有相关缓存
            cache_keys = ['tiku_list', 'file_options']
            for key in cache_keys:
                self._delete_from_redis(key)

            # 删除所有题库缓存（使用模式匹配）
            try:
                pattern = self._get_cache_key('question_bank_*')
                keys = self.redis_manager._redis_client.keys(pattern)
                if keys:
                    self.redis_manager._redis_client.delete(*keys)
                    logger.info(f"删除了 {len(keys)} 个题库缓存")
            except Exception as e:
                logger.error(f"删除题库缓存失败: {e}")

            # 删除所有单个题目缓存（使用模式匹配）
            try:
                pattern = self._get_cache_key('question_*')
                keys = self.redis_manager._redis_client.keys(pattern)
                if keys:
                    self.redis_manager._redis_client.delete(*keys)
                    logger.info(f"删除了 {len(keys)} 个单题目缓存")
            except Exception as e:
                logger.error(f"删除单题目缓存失败: {e}")

            # 预热基础缓存
            logger.info("开始预热基础缓存...")
            tiku_data = self.get_tiku_list()
            file_options_data = self.get_file_options()

            # 预热题目缓存 - 只预热活跃的题库
            prewarmed_questions = 0
            if tiku_data and 'tiku_list' in tiku_data:
                logger.info("开始预热题目缓存...")
                active_tiku_list = [tiku for tiku in tiku_data['tiku_list'] if tiku.get('is_active', False)]

                # 根据题库使用统计排序，优先预热常用题库
                with usage_stats_lock:
                    active_tiku_list.sort(key=lambda x: tiku_usage_stats.get(x['tiku_id'], 0), reverse=True)

                # 限制预热的题库数量，避免一次加载过多数据
                max_prewarm_tiku = 10  # 最多预热10个题库
                tiku_to_prewarm = active_tiku_list[:max_prewarm_tiku]

                for tiku in tiku_to_prewarm:
                    try:
                        tiku_id = tiku['tiku_id']
                        tiku_name = tiku.get('tiku_name', f'题库{tiku_id}')
                        logger.info(f"预热题库 {tiku_id} ({tiku_name}) 的题目缓存...")
                        question_bank = self.get_question_bank(tiku_id)
                        if question_bank:
                            prewarmed_questions += len(question_bank)
                            logger.debug(f"成功预热题库 {tiku_id} 的 {len(question_bank)} 道题目")
                        else:
                            logger.warning(f"题库 {tiku_id} 为空或加载失败")
                    except Exception as e:
                        logger.error(f"预热题库 {tiku.get('tiku_id', 'unknown')} 失败: {e}")
                        continue

                if len(active_tiku_list) > max_prewarm_tiku:
                    logger.info(f"活跃题库共 {len(active_tiku_list)} 个，已预热最常用的 {max_prewarm_tiku} 个题库")
                else:
                    logger.info(f"所有 {len(active_tiku_list)} 个活跃题库已预热完成")

            logger.info("所有Redis缓存已刷新完成")

            return {
                'tiku_count': len(tiku_data['tiku_list']) if tiku_data else 0,
                'subjects_count': len(file_options_data) if file_options_data else 0,
                'prewarmed_questions': prewarmed_questions,
                'message': f'Redis缓存刷新成功，预热了 {prewarmed_questions} 道题目'
            }

        except Exception as e:
            logger.error(f"刷新Redis缓存失败: {e}")
            return {
                'tiku_count': 0,
                'subjects_count': 0,
                'prewarmed_questions': 0,
                'message': f'缓存刷新失败: {str(e)}'
            }


# 单例缓存管理器
cache_manager = RedisCacheManager()


# 性能监控装饰器
def performance_monitor(func):
    """性能监控装饰器"""

    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            duration = time.time() - start_time
            if duration > 1.0:  # 超过1秒记录警告
                logger.warning(f"{func.__name__} 执行时间: {duration:.2f}s")
            else:
                logger.debug(f"{func.__name__} 执行时间: {duration:.3f}s")
            return result
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"{func.__name__} 执行失败 ({duration:.2f}s): {e}")
            raise

    return wrapper


@lru_cache(maxsize=128)
def _classify_question_type(question_type_str: str, is_multiple: bool) -> str:
    """缓存的题目类型分类函数"""
    question_type_lower = question_type_str.lower()

    if is_multiple:
        return QUESTION_TYPE_MULTIPLE

    for q_type, config in QUESTION_TYPE_MAPPING.items():
        if any(keyword in question_type_lower for keyword in config['keywords']):
            return q_type

    return QUESTION_TYPE_OTHER


def increment_tiku_usage(tiku_id: int):
    """增加题库使用次数（优化版本）"""
    with usage_stats_lock:
        tiku_usage_stats[tiku_id] += 1
        logger.debug(f"题库 {tiku_id} 使用次数: {tiku_usage_stats[tiku_id]}")


def inject_user_progress(subjects_data: dict, current_tiku_id: int, current_progress: dict) -> dict:
    """优化的进度注入函数 - 避免深拷贝，并注入选择的题型信息"""
    if not current_tiku_id or not current_progress:
        return subjects_data

    # 从session获取选择的题型信息
    selected_question_types = get_session_value('select_types', [])
    shuffle_enabled = get_session_value('shuffle_enabled', True)

    # 题型显示名称映射
    type_display_names = {
        'single_choice': '单选题',
        'multiple_choice': '多选题',
        'judgment': '判断题',
        'other': '其他题型'
    }

    # 构建题型显示信息
    selected_types_display = []
    if selected_question_types:
        for q_type in selected_question_types:
            display_name = type_display_names.get(q_type, q_type)
            selected_types_display.append(display_name)

    # 增强的进度信息
    enhanced_progress = current_progress.copy()
    enhanced_progress.update({
        'selected_question_types': selected_question_types,
        'selected_types_display': selected_types_display,
        'practice_mode': '乱序练习' if shuffle_enabled else '顺序练习',
        'shuffle_enabled': shuffle_enabled
    })

    # 浅拷贝优化
    result = {}
    for subject_name, subject_data in subjects_data.items():
        result[subject_name] = {
            'files': [],
            'exam_time': subject_data['exam_time']
        }

        for file_info in subject_data['files']:
            new_file_info = file_info.copy()
            if file_info['tiku_id'] == current_tiku_id:
                new_file_info['progress'] = enhanced_progress
            result[subject_name]['files'].append(new_file_info)

    return result


@performance_monitor
def generate_questions(question_bank: List[dict], selected_types: Optional[List[str]] = None,
                       shuffle_enabled: bool = True) -> List[int]:
    """
    优化的题目生成函数 - 返回题目ID列表
    """
    if not question_bank:
        return []

    # 预分配列表避免动态扩容
    ids_by_type = {
        QUESTION_TYPE_SINGLE: [],
        QUESTION_TYPE_MULTIPLE: [],
        QUESTION_TYPE_JUDGMENT: [],
        QUESTION_TYPE_OTHER: []
    }

    # 单次遍历分类，直接使用题目ID而不是索引
    for question in question_bank:
        question_type = _classify_question_type(
            question.get('type', ''),
            question.get('is_multiple_choice', False)
        )
        question_id = question['id']
        ids_by_type[question_type].append(question_id)

    # 批量打乱（如果需要）
    if shuffle_enabled:
        for ids_list in ids_by_type.values():
            random.shuffle(ids_list)

    # 确定要包含的题型
    if selected_types is None:
        types_to_include = [QUESTION_TYPE_SINGLE, QUESTION_TYPE_MULTIPLE,
                            QUESTION_TYPE_JUDGMENT, QUESTION_TYPE_OTHER]
    elif not selected_types:
        logger.info("未选择任何题型，返回空列表")
        return []
    else:
        types_to_include = [t for t in [QUESTION_TYPE_SINGLE, QUESTION_TYPE_MULTIPLE,
                                        QUESTION_TYPE_JUDGMENT, QUESTION_TYPE_OTHER]
                            if t in selected_types]

        if not types_to_include:
            logger.info("指定的题型均无效，返回空列表")
            return []

    # 组合结果
    result_ids = []
    type_names = {
        QUESTION_TYPE_SINGLE: "单选题",
        QUESTION_TYPE_MULTIPLE: "多选题",
        QUESTION_TYPE_JUDGMENT: "判断题",
        QUESTION_TYPE_OTHER: "其他类型"
    }

    summary_parts = []
    for q_type in types_to_include:
        ids = ids_by_type[q_type]
        result_ids.extend(ids)
        if ids:
            summary_parts.append(f"{type_names[q_type]} {len(ids)} 道")

    shuffle_status = "已打乱" if shuffle_enabled else "未打乱"
    if summary_parts:
        logger.info(f"题目生成完成 ({shuffle_status}): {', '.join(summary_parts)}, 总计 {len(result_ids)} 道")

    return result_ids


@practice_bp.route('/file_options', methods=['GET'])
@login_required
@handle_api_error
@performance_monitor
def api_file_options():
    """获取可用题库选项 - 优化版本"""
    # 获取当前练习进度
    current_tiku_id = get_session_value(SESSION_KEYS['CURRENT_TIKU_ID'])
    current_progress = None

    if current_tiku_id:
        current_indices = get_session_value(SESSION_KEYS['QUESTION_INDICES'], [])
        current_index = get_session_value(SESSION_KEYS['CURRENT_INDEX'], 0)
        initial_total = get_session_value(SESSION_KEYS['INITIAL_TOTAL'], 0)

        if current_indices and initial_total > 0:
            current_progress = {
                'current_question': current_index + 1,
                'total_questions': len(current_indices),
                'initial_total': initial_total,
                'correct_first_try': get_session_value(SESSION_KEYS['CORRECT_FIRST_TRY'], 0),
                'round_number': get_session_value(SESSION_KEYS['ROUND_NUMBER'], 1),
                'progress_percent': min(100, (current_index / len(current_indices)) * 100) if current_indices else 0
            }

    try:
        subjects_data = cache_manager.get_file_options()
        if current_progress:
            subjects_data = inject_user_progress(subjects_data, current_tiku_id, current_progress)
    except Exception as e:
        logger.warning(f"获取题库选项失败: {e}")
        subjects_data = {}

    return create_response(True, data={'subjects': subjects_data})


@practice_bp.route('/start_practice', methods=['POST'])
@login_required
@handle_api_error
@performance_monitor
def api_start_practice():
    """开始练习 - 优化版本"""
    data = request.get_json()
    if not data:
        raise BadRequest("缺少请求数据")

    tiku_id = data.get('tikuid')
    shuffle_questions = data.get('shuffle_questions', True)
    force_restart = data.get('force_restart', False)
    selected_types = data.get('selected_types')

    if not tiku_id:
        raise BadRequest("缺少题库ID")

    try:
        tiku_id = int(tiku_id)
    except ValueError:
        raise BadRequest("无效的题库ID格式")

    # 首先验证题库是否存在和可用
    try:
        cached_tiku_data = cache_manager.get_tiku_list()
        tiku_list = cached_tiku_data['tiku_list']
        tiku_info = None

        for tiku in tiku_list:
            if tiku['tiku_id'] == tiku_id:
                tiku_info = tiku
                break

        if not tiku_info:
            raise BadRequest(f"题库ID {tiku_id} 不存在")

        if not tiku_info['is_active']:
            raise BadRequest(f"题库已禁用: {tiku_info['tiku_name']}")

    except BadRequest:
        # 重新抛出BadRequest异常
        raise
    except Exception as e:
        logger.error(f"验证题库失败: {e}")
        raise BadRequest(f"题库 {tiku_id} 不可用")

    # 获取题库的题目数据
    question_bank = cache_manager.get_question_bank(tiku_id)
    if not question_bank:
        raise BadRequest(f"题库 {tiku_id} 为空或加载失败")

    user_info = get_user_session_info()
    user_id = user_info['user_id']

    if not user_id:
        raise BadRequest("用户未登录")

    # 检查现有会话
    existing_tiku_id = get_session_value(SESSION_KEYS['CURRENT_TIKU_ID'])
    existing_indices = get_session_value(SESSION_KEYS['QUESTION_INDICES'])

    if not force_restart and existing_tiku_id == tiku_id and existing_indices:
        if not get_session_value('practice_session_id'):
            check_and_resume_practice_session(user_id, tiku_id)
        return create_response(True, '恢复现有练习会话', {'resumed': True})

    # 开始新会话
    increment_tiku_usage(tiku_id)

    # 生成题目索引
    question_indices = generate_questions(question_bank, selected_types, shuffle_questions)

    if not question_indices:
        raise BadRequest("没有符合条件的题目")

    # 创建练习会话
    session_type = data.get('session_type', 'normal')
    practice_session_id = create_and_store_practice_session(
        user_id=user_id,
        tiku_id=tiku_id,
        session_type=session_type,
        shuffle_enabled=shuffle_questions,
        selected_types=selected_types,
        total_questions=len(question_indices),
        question_indices=question_indices
    )

    # 批量设置session值
    session_data = {
        SESSION_KEYS['CURRENT_TIKU_ID']: tiku_id,
        SESSION_KEYS['QUESTION_INDICES']: question_indices,
        SESSION_KEYS['CURRENT_INDEX']: 0,
        SESSION_KEYS['WRONG_INDICES']: [],
        SESSION_KEYS['ROUND_NUMBER']: 1,
        SESSION_KEYS['INITIAL_TOTAL']: len(question_indices),
        SESSION_KEYS['CORRECT_FIRST_TRY']: 0,
        SESSION_KEYS['QUESTION_STATUSES']: [QUESTION_STATUS['UNANSWERED']] * len(question_indices),
        SESSION_KEYS['ANSWER_HISTORY']: {},
        SESSION_KEYS['SELECT_TYPES']: selected_types or ['single_choice', 'multiple_choice', 'judgment', 'other'],
        'shuffle_enabled': shuffle_questions
    }

    for key, value in session_data.items():
        set_session_value(key, value)

    practice_mode = "乱序练习" if shuffle_questions else "顺序练习"
    type_info = f"选择题型: {len(selected_types)} 种" if selected_types else "所有题型"

    logger.info(f"用户 {user_id} 开始新练习: 题库ID={tiku_id}, 会话ID={practice_session_id}, 模式={practice_mode}")

    return create_response(True, f'开始{practice_mode} - {type_info}', {
        'resumed': False,
        'practice_session_id': practice_session_id
    })


@practice_bp.route('/practice/question', methods=['GET'])
@handle_api_error
@performance_monitor
def api_practice_question():
    """获取当前练习题目 - 优化版本"""
    q_indices = get_session_value(SESSION_KEYS['QUESTION_INDICES'], [])
    if not q_indices:
        logger.warning(f"QUESTION_INDICES为空，当前session keys: {list(session.keys())}")
        raise NotFound("没有可用题目或会话已过期")

    current_idx = get_session_value(SESSION_KEYS['CURRENT_INDEX'], 0)
    flash_messages = []

    # 检查新轮次
    if current_idx >= len(q_indices):
        wrong_indices = get_session_value(SESSION_KEYS['WRONG_INDICES'], [])
        if not wrong_indices:
            return create_response(True, '练习完成！', {'redirect_to_completed': True})

        # 批量更新session - 新轮次
        new_round_indices = list(wrong_indices)
        random.shuffle(new_round_indices)
        round_number = get_session_value(SESSION_KEYS['ROUND_NUMBER'], 1) + 1

        session_updates = {
            SESSION_KEYS['QUESTION_INDICES']: new_round_indices,
            SESSION_KEYS['WRONG_INDICES']: [],
            SESSION_KEYS['CURRENT_INDEX']: 0,
            SESSION_KEYS['ROUND_NUMBER']: round_number,
            SESSION_KEYS['QUESTION_STATUSES']: [QUESTION_STATUS['UNANSWERED']] * len(new_round_indices),
            SESSION_KEYS['ANSWER_HISTORY']: {}
        }

        for key, value in session_updates.items():
            set_session_value(key, value)

        flash_messages.append({
            'category': 'info',
            'text': f"开始第{round_number}轮，共{len(new_round_indices)}道错题！"
        })

        current_idx = 0
        q_indices = new_round_indices

    # 使用单个题目ID直接获取题目数据，而不是加载整个题库
    question_id = q_indices[current_idx]

    try:
        question_obj = cache_manager.get_question_by_id(question_id)
        if not question_obj:
            logger.error(f"题目 {question_id} 不存在或已禁用")
            raise BadRequest("当前题目不可用，请重新开始练习")

    except Exception as e:
        logger.error(f"获取题目 {question_id} 失败: {e}")
        raise BadRequest("加载题目失败，请稍后重试")

    # 预构建响应数据
    question_data = {
        'id': question_obj['id'],
        'type': question_obj['type'],
        'question': question_obj['question'],
        'options_for_practice': question_obj.get('options_for_practice'),
        'answer': question_obj['answer'],
        'is_multiple_choice': question_obj.get('is_multiple_choice', False),
        'analysis': question_obj.get('explanation', '暂无解析'),
        'knowledge_points': question_obj.get('knowledge_points', [])
    }

    progress_data = {
        'current': current_idx + 1,
        'total': len(q_indices),
        'initial_total': get_session_value(SESSION_KEYS['INITIAL_TOTAL'], 0),
        'correct_count': get_session_value(SESSION_KEYS['CORRECT_FIRST_TRY'], 0),
        'round_number': get_session_value(SESSION_KEYS['ROUND_NUMBER'], 1)
    }

    return create_response(True, data={
        'question': question_data,
        'progress': progress_data,
        'flash_messages': flash_messages
    })


@practice_bp.route('/practice/submit', methods=['POST'])
@handle_api_error
@performance_monitor
def api_submit_answer():
    """提交答案 - 优化版本（使用单题目缓存）"""
    data = request.get_json()
    if not data:
        raise BadRequest("缺少请求数据")

    user_answer = data.get('answer', '').upper()
    question_id = data.get('question_id')
    peeked = data.get('peeked', False)

    if not question_id:
        raise BadRequest("缺少题目ID")

    current_idx = get_session_value(SESSION_KEYS['CURRENT_INDEX'], 0)

    try:
        question_data = cache_manager.get_question_by_id(question_id)
        if not question_data:
            raise BadRequest(f"题目 {question_id} 不存在或已禁用")

    except Exception as e:
        logger.error(f"获取提交题目 {question_id} 失败: {e}")
        raise BadRequest("加载题目数据失败")

    # 验证题目ID匹配（如果前端传递了ID）
    if question_id and question_data['id'] != question_id:
        logger.warning(f"题目ID不匹配: 期望 {question_data['id']}, 实际 {question_id}")

    is_multiple_choice = question_data.get('is_multiple_choice', False)
    correct_answer = question_data['answer'].upper()

    # 判断答案正确性
    is_correct = False if peeked else validate_answer(user_answer, correct_answer, is_multiple_choice)

    # 格式化答案显示
    options = question_data.get('options_for_practice', {})
    user_answer_display = '未作答（直接查看答案）' if peeked else format_answer_display(user_answer, options,
                                                                                      is_multiple_choice)
    correct_answer_display = format_answer_display(correct_answer, options, is_multiple_choice)

    update_practice_record(question_id, is_correct, peeked, current_idx, user_answer)

    return create_response(True, data={
        "is_correct": is_correct,
        "user_answer_display": user_answer_display,
        "correct_answer_display": correct_answer_display,
        "question_id": question_data['id'],
        "current_index": current_idx
    })


def update_practice_record(question_id: int, is_correct: bool, peeked: bool, current_idx: int, user_answer: str):
    """更新练习记录 - 优化版本（处理题目ID）"""

    # 批量获取session值避免多次调用
    question_statuses = get_session_value(SESSION_KEYS['QUESTION_STATUSES'], [])
    answer_history = get_session_value(SESSION_KEYS['ANSWER_HISTORY'], {})
    wrong_indices = get_session_value(SESSION_KEYS['WRONG_INDICES'], [])

    # 更新题目状态
    if current_idx < len(question_statuses):
        question_statuses[current_idx] = QUESTION_STATUS['CORRECT'] if (is_correct and not peeked) else QUESTION_STATUS[
            'WRONG']

    # 保存答题历史 - 存储题目ID
    answer_history[str(current_idx)] = {
        'user_answer': user_answer,
        'is_correct': is_correct,
        'question_id': question_id  # 直接存储题目ID，因为q_indices现在存储的就是ID
    }

    # 处理错题和正确题 - 现在wrong_indices存储的是题目ID
    if not is_correct or peeked:
        if question_id not in wrong_indices:
            wrong_indices.append(question_id)
    else:
        if get_session_value(SESSION_KEYS['ROUND_NUMBER'], 1) == 1:
            correct_count = get_session_value(SESSION_KEYS['CORRECT_FIRST_TRY'], 0) + 1
            set_session_value(SESSION_KEYS['CORRECT_FIRST_TRY'], correct_count)

    next_index = current_idx + 1

    # 批量更新session值
    session_updates = {
        SESSION_KEYS['QUESTION_STATUSES']: question_statuses,
        SESSION_KEYS['ANSWER_HISTORY']: answer_history,
        SESSION_KEYS['WRONG_INDICES']: wrong_indices,
        SESSION_KEYS['CURRENT_INDEX']: next_index
    }

    for key, value in session_updates.items():
        set_session_value(key, value)

    # 异步更新数据库记录 - 修复版本
    try:
        # 在主线程中获取所有需要的数据，避免在异步线程中访问Flask session
        practice_session_id = get_session_value('practice_session_id')
        if not practice_session_id:
            # 尝试从session_manager获取
            from ..session_manager import get_current_practice_session_id
            practice_session_id = get_current_practice_session_id()

        if not practice_session_id:
            logger.warning("没有找到练习会话ID，跳过数据库更新")
            return

        update_data = {
            'current_question_index': next_index,
            'correct_first_try': get_session_value(SESSION_KEYS['CORRECT_FIRST_TRY'], 0),
            'round_number': get_session_value(SESSION_KEYS['ROUND_NUMBER'], 1),
            'wrong_indices': wrong_indices,
            'question_statuses': question_statuses,
            'answer_history': answer_history
        }

        # 异步执行数据库更新，避免阻塞主线程
        def async_update_session(session_id: int, data: dict):
            try:
                # 直接调用connectDB中的函数，不依赖Flask上下文
                from ..connectDB import update_practice_session
                result = update_practice_session(session_id, **data)
                if result['success']:
                    logger.debug("练习会话数据库记录更新成功")
                else:
                    logger.warning(f"练习会话数据库记录更新失败: {result.get('error', 'Unknown error')}")
            except Exception as e:
                logger.error(f"异步更新练习会话数据库记录时发生错误: {e}")

        # 在后台线程中执行数据库更新，传递所有必要的数据
        update_thread = threading.Thread(
            target=async_update_session,
            args=(practice_session_id, update_data),
            daemon=True
        )
        update_thread.start()

    except Exception as e:
        logger.error(f"启动异步更新练习会话数据库记录失败: {e}")


@practice_bp.route('/completed_summary', methods=['GET'])
@login_required
@handle_api_error
@performance_monitor
def api_completed_summary():
    """获取练习完成总结"""
    initial_total = get_session_value(SESSION_KEYS['INITIAL_TOTAL'], 0)
    correct_first_try = get_session_value(SESSION_KEYS['CORRECT_FIRST_TRY'], 0)
    score_percent = (correct_first_try / initial_total * 100) if initial_total > 0 else 0

    # 获取当前题库信息
    tiku_info = get_current_tiku_info()
    display_name = tiku_info['tiku_name'] if tiku_info else 'Unknown'

    summary_data = {
        'initial_total': initial_total,
        'correct_first_try': correct_first_try,
        'score_percent': score_percent,
        'completed_filename': display_name
    }

    # 准备最终统计数据
    final_stats = {
        'total_questions': initial_total,
        'correct_answers': correct_first_try,
        'practice_time_minutes': 0
    }

    # 完成练习会话记录
    try:
        if complete_current_practice_session(final_stats):
            logger.info("练习会话已标记为完成")
        else:
            logger.warning("无法标记练习会话为完成状态")
    except Exception as e:
        logger.error(f"完成练习会话时发生错误: {e}")

    # 保存并清除session
    clear_practice_session()

    return create_response(True, data={'summary': summary_data})


@practice_bp.route('/practice/jump', methods=['GET'])
@handle_api_error
def api_jump_to_question():
    """跳转到指定题目"""
    target_index = request.args.get('index', type=int)
    if target_index is None:
        raise BadRequest("缺少目标索引")

    if target_index < 0:
        raise BadRequest("无效的题目索引")

    set_session_value(SESSION_KEYS['CURRENT_INDEX'], target_index)
    return create_response(True, "成功跳转到题目")


@practice_bp.route('/practice/statuses', methods=['GET'])
@handle_api_error
def api_get_question_statuses():
    """获取所有题目状态"""
    statuses = get_session_value(SESSION_KEYS['QUESTION_STATUSES'], [])
    return create_response(True, data={'statuses': statuses})


@practice_bp.route('/practice/next', methods=['POST'])
@handle_api_error
def api_next_question():
    """跳转到下一题"""
    current_idx = get_session_value(SESSION_KEYS['CURRENT_INDEX'], 0)
    set_session_value(SESSION_KEYS['CURRENT_INDEX'], current_idx + 1)
    return create_response(True, "成功跳转到下一题")


@practice_bp.route('/session/status', methods=['GET'])
@login_required
@handle_api_error
def api_session_status():
    """获取会话状态"""
    start_time = time.time()  # 记录开始时间

    current_tiku_id = get_session_value(SESSION_KEYS['CURRENT_TIKU_ID'])
    step1_end_time = time.time()
    print(f"获取 current_tiku_id 耗时: {step1_end_time - start_time:.4f} 秒")

    if not current_tiku_id:
        return create_response(True, '没有活跃的练习会话', {'has_session': False})

    # 获取题库显示名称
    tiku_info = get_current_tiku_info()
    step2_end_time = time.time()
    print(f"获取 tiku_info 耗时: {step2_end_time - step1_end_time:.4f} 秒")

    display_name = tiku_info['tiku_name'] if tiku_info else str(current_tiku_id)
    step3_end_time = time.time()
    print(f"处理 display_name 耗时: {step3_end_time - step2_end_time:.4f} 秒")

    current_indices = get_session_value(SESSION_KEYS['QUESTION_INDICES'], [])
    step4_end_time = time.time()
    print(f"获取 current_indices 耗时: {step4_end_time - step3_end_time:.4f} 秒")

    current_index = get_session_value(SESSION_KEYS['CURRENT_INDEX'], 0)
    step5_end_time = time.time()
    print(f"获取 current_index 耗时: {step5_end_time - step4_end_time:.4f} 秒")

    round_number = get_session_value(SESSION_KEYS['ROUND_NUMBER'], 1)
    step6_end_time = time.time()
    print(f"获取 round_number 耗时: {step6_end_time - step5_end_time:.4f} 秒")

    # 获取题型和练习模式信息
    selected_types = get_session_value('select_types', [])
    step7_end_time = time.time()
    print(f"获取 selected_types 耗时: {step7_end_time - step6_end_time:.4f} 秒")

    shuffle_enabled = get_session_value('shuffle_enabled', True)
    step8_end_time = time.time()
    print(f"获取 shuffle_enabled 耗时: {step8_end_time - step7_end_time:.4f} 秒")

    response_data = {
        'has_session': True,
        'tiku_id': current_tiku_id,
        'file_info': {
            'display': display_name,
            'current_question': current_index + 1,
            'total_questions': len(current_indices),
            'round_number': round_number
        },
        'session_config': {
            'question_types': selected_types,
            'shuffle_enabled': shuffle_enabled,
            'practice_mode': '乱序练习' if shuffle_enabled else '顺序练习'
        }
    }
    step9_end_time = time.time()
    print(f"构建响应数据耗时: {step9_end_time - step8_end_time:.4f} 秒")

    total_end_time = time.time()
    print(f"api_session_status 函数总耗时: {total_end_time - start_time:.4f} 秒")

    return create_response(True, '当前有活跃的练习会话', response_data)


@practice_bp.route('/session/save', methods=['GET'])
@login_required
@handle_api_error
def api_save_session():
    """保存当前会话到数据库 (此功能已集成到练习流程中，不再需要单独调用)"""
    logger.warning("Endpoint /api/session/save is deprecated. Session saving is now automatic.")
    return create_response(True, '会话保存已集成到练习流程中，此端点不再执行特定操作。')


@practice_bp.route('/cache/refresh', methods=['POST'])
@login_required
@handle_api_error
@performance_monitor
def api_refresh_cache():
    """刷新缓存"""
    try:
        result = cache_manager.refresh_all_cache()
        return create_response(True, result['message'], {
            'tiku_count': result['tiku_count'],
            'subjects_count': result['subjects_count'],
            'prewarmed_questions': result['prewarmed_questions']
        })
    except Exception as e:
        logger.error(f"刷新缓存失败: {e}")
        return create_response(False, f'刷新缓存失败: {str(e)}', status_code=500)


@practice_bp.route('/history', methods=['GET'])
@login_required
@handle_api_error
@performance_monitor
def api_practice_history():
    """获取用户练习历史记录"""
    user_info = get_user_session_info()
    user_id = user_info['user_id']

    if not user_id:
        raise BadRequest("用户未登录")

    # 获取分页参数
    limit = request.args.get('limit', 10, type=int)
    limit = min(limit, 50)  # 限制最大为50条

    try:
        history = get_user_practice_history(user_id, limit)

        return create_response(True, '获取练习历史成功', {
            'history': history,
            'total_count': len(history)
        })

    except Exception as e:
        logger.error(f"获取练习历史失败: {e}")
        return create_response(False, '获取练习历史失败', status_code=500)


@practice_bp.route('/statistics', methods=['GET'])
@login_required
@handle_api_error
@performance_monitor
def api_practice_statistics():
    """获取用户练习统计信息"""
    user_info = get_user_session_info()
    user_id = user_info['user_id']

    if not user_id:
        raise BadRequest("用户未登录")

    try:
        # 获取基本历史数据
        history = get_user_practice_history(user_id, 100)

        # 计算统计信息
        total_sessions = len(history)
        completed_sessions = len([h for h in history if h['status'] == 'completed'])
        total_questions = sum(h['total_questions'] for h in history)
        total_correct = sum(h['correct_first_try'] for h in history)

        # 按科目统计
        subject_stats = defaultdict(lambda: {
            'sessions': 0, 'total_questions': 0, 'correct_answers': 0, 'avg_score': 0
        })

        for session in history:
            subject = session['subject_name']
            subject_stats[subject]['sessions'] += 1
            subject_stats[subject]['total_questions'] += session['total_questions']
            subject_stats[subject]['correct_answers'] += session['correct_first_try']

        # 计算平均分
        for subject, stats in subject_stats.items():
            if stats['total_questions'] > 0:
                stats['avg_score'] = round(stats['correct_answers'] / stats['total_questions'] * 100, 2)

        overall_avg_score = round(total_correct / total_questions * 100, 2) if total_questions > 0 else 0

        statistics = {
            'overall': {
                'total_sessions': total_sessions,
                'completed_sessions': completed_sessions,
                'total_questions': total_questions,
                'total_correct': total_correct,
                'avg_score': overall_avg_score
            },
            'by_subject': dict(subject_stats),
            'recent_activity': history[:10]
        }

        return create_response(True, '获取统计信息成功', {
            'statistics': statistics
        })

    except Exception as e:
        logger.error(f"获取练习统计失败: {e}")
        return create_response(False, '获取练习统计失败', status_code=500)


@practice_bp.route('/practice/history/<int:question_index>', methods=['GET'])
@login_required
@handle_api_error
def api_get_question_history(question_index: int):
    """获取题目答题历史 - 新格式版本（使用题目ID）"""
    q_indices = get_session_value(SESSION_KEYS['QUESTION_INDICES'], [])

    if question_index < 0 or question_index >= len(q_indices):
        raise BadRequest(f'无效的题目索引。有效范围: 0-{len(q_indices) - 1}')

    answer_history = get_session_value(SESSION_KEYS['ANSWER_HISTORY'], {})
    history_key = str(question_index)

    if history_key not in answer_history:
        raise NotFound('该题目没有答题历史')

    history_data = answer_history[history_key]

    # 验证新格式数据
    if 'question_id' not in history_data:
        raise BadRequest('答题历史数据格式错误，请重新开始练习')

    # 使用题目ID直接获取题目数据
    actual_question_id = history_data['question_id']

    try:
        question_data = cache_manager.get_question_by_id(actual_question_id)
        if not question_data:
            raise NotFound(f'题目 {actual_question_id} 不存在或已禁用')

    except Exception as e:
        logger.error(f"获取历史题目 {actual_question_id} 失败: {e}")
        raise BadRequest("加载题目数据失败")

    # 格式化答案显示
    options = question_data.get('options_for_practice', {})
    is_multiple_choice = question_data.get('is_multiple_choice', False)
    correct_answer = question_data['answer'].upper()
    user_answer = history_data['user_answer']

    user_answer_display = '未作答（直接查看答案）' if history_data['user_answer'] is None or not history_data[
        'user_answer'] else format_answer_display(user_answer,
                                                  options,
                                                  is_multiple_choice)
    correct_answer_display = format_answer_display(correct_answer, options, is_multiple_choice)

    return create_response(True, data={
        'question': {
            'id': question_data['id'],
            'type': question_data['type'],
            'question': question_data['question'],
            'options_for_practice': question_data.get('options_for_practice'),
            'answer': question_data['answer'],
            'is_multiple_choice': question_data.get('is_multiple_choice', False),
            'analysis': question_data.get('explanation', '暂无解析'),
            'knowledge_points': question_data.get('knowledge_points', [])
        },
        'feedback': {
            'is_correct': history_data['is_correct'],
            'user_answer_display': user_answer_display,
            'correct_answer_display': correct_answer_display,
            'question_id': question_data['id'],
            'current_index': question_index,
            'explanation': ''
        }
    })


@practice_bp.route('/practice/question/<question_id>/details', methods=['GET'])
@login_required
@handle_api_error
def api_get_question_details(question_id: str):
    """获取题目详细信息（包含解析）"""
    if not question_id.startswith('db_'):
        raise BadRequest('无效的题目ID格式')

    try:
        db_id = int(question_id.replace('db_', ''))
    except ValueError:
        raise BadRequest('无效的题目ID')

    # Use the new efficient function from connectDB
    question_data = get_question_by_db_id(db_id)

    if not question_data:
        raise NotFound('题目不存在')

    # The question_data from get_question_by_db_id is already mostly formatted.
    # We just need to add correct_answer_display.
    options = question_data.get('options_for_practice', {})
    is_multiple_choice = question_data.get('is_multiple_choice', False)
    correct_answer = question_data.get('answer', '').upper()
    correct_answer_display = format_answer_display(correct_answer, options, is_multiple_choice)

    # Add it to the question_data dictionary that will be returned
    question_data_for_response = question_data.copy()  # Avoid modifying the cached object if get_question_by_db_id returns a cached mutable object
    question_data_for_response['correct_answer_display'] = correct_answer_display

    return create_response(True, data={'question': question_data_for_response})


@practice_bp.route('/practice/question/<question_id>/analysis', methods=['GET'])
@login_required
@handle_api_error
def api_get_question_analysis(question_id: str):
    """获取题目解析"""
    if not question_id.startswith('db_'):
        raise BadRequest('无效的题目ID格式')

    try:
        db_id = int(question_id.replace('db_', ''))
    except ValueError:
        raise BadRequest('无效的题目ID')

    # Use the new efficient function from connectDB
    question_data = get_question_by_db_id(db_id)

    if not question_data:
        raise NotFound('题目不存在')

    return create_response(True, data={
        'analysis': question_data.get('explanation', '暂无解析'),
        'knowledge_points': question_data.get('knowledge_points', [])
        # Assuming knowledge_points might be part of question_data
    })


@practice_bp.route('/practice', methods=['GET'])
@login_required
@handle_api_error
@performance_monitor
def api_practice_url_params():
    """支持简化URL参数格式的练习路由：/practice?tikuid=123&order=random&types=single_choice,multiple_choice"""
    # 获取URL参数
    tiku_id = request.args.get('tikuid')
    order = request.args.get('order', 'random')
    types_param = request.args.get('types')

    if not tiku_id:
        raise BadRequest("缺少必要的URL参数: tikuid")

    try:
        tiku_id = int(tiku_id)
    except ValueError:
        raise BadRequest("无效的题库ID格式")

    # 解析题型参数
    selected_types = None
    if types_param:
        selected_types = [t.strip() for t in types_param.split(',') if t.strip()]
        # 验证题型参数有效性
        valid_types = [QUESTION_TYPE_SINGLE, QUESTION_TYPE_MULTIPLE, QUESTION_TYPE_JUDGMENT, QUESTION_TYPE_OTHER]
        invalid_types = [t for t in selected_types if t not in valid_types]
        if invalid_types:
            raise BadRequest(f"无效的题型参数: {', '.join(invalid_types)}")

    logger.info(f"URL practice access: tikuid={tiku_id}, order={order}, types={selected_types}")

    # 从缓存获取题库信息
    try:
        cached_tiku_data = cache_manager.get_tiku_list()
        tiku_list = cached_tiku_data['tiku_list']
        tiku_info = None

        for tiku in tiku_list:
            if tiku['tiku_id'] == tiku_id:
                tiku_info = tiku
                break

        if not tiku_info:
            raise NotFound(f"未找到题库ID: {tiku_id}")

        if not tiku_info['is_active']:
            raise BadRequest(f"题库已禁用: {tiku_info['tiku_name']}")

    except Exception as e:
        logger.warning(f"查找题库失败: {e}")
        raise NotFound(f"查找题库失败: {tiku_id}")

    # 使用缓存管理器获取题库题目
    question_bank = cache_manager.get_question_bank(tiku_id)
    if not question_bank:
        raise NotFound("选择的题库为空或不存在")

    # 检查是否有现有会话
    existing_tiku_id = get_session_value(SESSION_KEYS['CURRENT_TIKU_ID'])
    existing_indices = get_session_value(SESSION_KEYS['QUESTION_INDICES'])

    # 确定题目顺序
    shuffle_questions = order.lower() == 'random'

    if existing_tiku_id != tiku_id or not existing_indices:
        # 开始新的练习会话
        if not isinstance(question_bank, list) or not question_bank:
            raise BadRequest('选择的题库为空或无效')

        # 增加题库使用次数统计
        increment_tiku_usage(tiku_id)

        # 根据参数生成题目索引
        question_indices = generate_questions(
            question_bank,
            selected_types=selected_types,
            shuffle_enabled=shuffle_questions
        )

        if not question_indices:
            # 如果选择的题型在题库中不存在，返回友好错误
            type_names = []
            if selected_types:
                type_map = {
                    QUESTION_TYPE_SINGLE: '单选题',
                    QUESTION_TYPE_MULTIPLE: '多选题',
                    QUESTION_TYPE_JUDGMENT: '判断题',
                    QUESTION_TYPE_OTHER: '其他题型'
                }
                type_names = [type_map.get(t, t) for t in selected_types]

            error_msg = f"该题库中没有找到指定类型的题目" + (f"：{', '.join(type_names)}" if type_names else "")
            raise BadRequest(error_msg)

        # 获取用户信息并创建练习会话记录
        user_info = get_user_session_info()
        user_id = user_info['user_id']

        if user_id:
            practice_session_id = create_and_store_practice_session(
                user_id=user_id,
                tiku_id=tiku_id,
                session_type='url_direct',
                shuffle_enabled=shuffle_questions,
                selected_types=selected_types,
                total_questions=len(question_indices),
                question_indices=question_indices
            )

            if practice_session_id:
                logger.info(f"URL访问创建练习会话: 用户={user_id}, 题库={tiku_id}, 会话ID={practice_session_id}")

        # 批量设置session
        session_data = {
            SESSION_KEYS['QUESTION_INDICES']: question_indices,
            SESSION_KEYS['WRONG_INDICES']: [],
            SESSION_KEYS['QUESTION_STATUSES']: [QUESTION_STATUS['UNANSWERED']] * len(question_indices),
            SESSION_KEYS['ANSWER_HISTORY']: {},
            'selected_question_types': selected_types or ['single_choice', 'multiple_choice', 'judgment', 'other'],
            'shuffle_enabled': shuffle_questions
        }

        for key, value in session_data.items():
            set_session_value(key, value)

        # 验证关键的 session 值是否正确设置
        current_tiku_id_check = get_session_value(SESSION_KEYS['CURRENT_TIKU_ID'])
        if current_tiku_id_check != tiku_id:
            logger.error(f"Session 设置验证失败: 期望 tiku_id={tiku_id}, 实际={current_tiku_id_check}")
            raise BadRequest("会话设置失败，请重新开始练习")

        practice_mode = "乱序练习" if shuffle_questions else "顺序练习"
        types_text = "所有题型" if not selected_types else f"已选题型({len(selected_types)}种)"
        logger.info(f"开始新的{practice_mode} - {types_text}: {tiku_info['tiku_name']} (ID: {tiku_id})")

    # 获取当前题目数据
    try:
        question_response = api_practice_question()

        # 如果是重定向到完成页面
        if isinstance(question_response, tuple):
            response_data, status_code = question_response
            response_json = response_data.get_json()
            if response_json.get('redirect_to_completed'):
                return create_response(True, '练习完成！', {
                    'redirect_to_completed': True,
                    'url_mode': True
                })

        # 正常返回题目数据，添加URL模式标识
        if isinstance(question_response, tuple):
            response_data, status_code = question_response
            response_json = response_data.get_json()
            if response_json.get('success'):
                response_json['url_mode'] = True
                response_json['url_params'] = {
                    'tikuid': tiku_id,
                    'order': order,
                    'types': types_param,
                    'tiku_position': tiku_info['tiku_position'],
                    'tiku_name': tiku_info['tiku_name'],
                    'subject_name': tiku_info['subject_name']
                }
                return jsonify(response_json), status_code

        return question_response

    except Exception as e:
        logger.error(f"获取题目失败: {e}")
        raise BadRequest(f"获取题目失败: {str(e)}")
