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

from flask import Blueprint, request, jsonify
from werkzeug.exceptions import BadRequest, NotFound

from ..config import SESSION_KEYS, QUESTION_STATUS
from ..connectDB import (
    get_questions_by_tiku, get_user_practice_history, get_tiku_by_subject, get_all_subjects,
    get_question_by_db_id
)
from ..decorators import handle_api_error, login_required
from ..redis_session import RedisSessionManager
from ..session_manager import (
    get_session_value, set_session_value, clear_practice_session,
    get_current_tiku_info,
    create_and_store_practice_session, update_current_practice_session,
    complete_current_practice_session, check_and_resume_practice_session,
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
        self.redis_manager = RedisSessionManager()
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
            logger.debug(f"使用Redis缓存的题目数据，题库ID: {tiku_id}")
            return cached_data

        logger.info(f"从数据库获取题库 {tiku_id} 的题目数据")
        try:
            # 从数据库获取题目列表
            question_bank_list = get_questions_by_tiku(tiku_id)

            if not question_bank_list:
                logger.warning(f"题库 {tiku_id} 为空或不存在")
                return []

            # 存储到Redis，题目数据缓存时间稍长一些
            self._set_to_redis(cache_key, question_bank_list, ttl=7200)  # 2小时
            logger.info(f"成功缓存题库 {tiku_id} 的 {len(question_bank_list)} 道题目到Redis")
            return question_bank_list

        except Exception as e:
            logger.error(f"获取题库 {tiku_id} 的题目数据失败: {e}")
            return []

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
                    'message': 'Redis不可用，缓存刷新失败'
                }

            # 删除所有相关缓存
            cache_keys = ['tiku_list', 'file_options']
            for key in cache_keys:
                self._delete_from_redis(key)

            # 删除所有题目缓存（使用模式匹配）
            try:
                pattern = self._get_cache_key('question_bank_*')
                keys = self.redis_manager._redis_client.keys(pattern)
                if keys:
                    self.redis_manager._redis_client.delete(*keys)
                    logger.info(f"删除了 {len(keys)} 个题目缓存")
            except Exception as e:
                logger.error(f"删除题目缓存失败: {e}")

            # 预热缓存
            tiku_data = self.get_tiku_list()
            file_options_data = self.get_file_options()

            logger.info("所有Redis缓存已刷新完成")

            return {
                'tiku_count': len(tiku_data['tiku_list']) if tiku_data else 0,
                'subjects_count': len(file_options_data) if file_options_data else 0,
                'message': 'Redis缓存刷新成功'
            }

        except Exception as e:
            logger.error(f"刷新Redis缓存失败: {e}")
            return {
                'tiku_count': 0,
                'subjects_count': 0,
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
    """优化的进度注入函数 - 避免深拷贝"""
    if not current_tiku_id or not current_progress:
        return subjects_data

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
                new_file_info['progress'] = current_progress
            result[subject_name]['files'].append(new_file_info)

    return result


@performance_monitor
def generate_questions(question_bank: List[dict], selected_types: Optional[List[str]] = None,
                       shuffle_enabled: bool = True) -> List[int]:
    """
    优化的题目生成函数 - 单次遍历 + 预分配列表
    """
    if not question_bank:
        return []

    # 预分配列表避免动态扩容
    indices_by_type = {
        QUESTION_TYPE_SINGLE: [],
        QUESTION_TYPE_MULTIPLE: [],
        QUESTION_TYPE_JUDGMENT: [],
        QUESTION_TYPE_OTHER: []
    }

    # 单次遍历分类
    for i, question in enumerate(question_bank):
        question_type = _classify_question_type(
            question.get('type', ''),
            question.get('is_multiple_choice', False)
        )
        indices_by_type[question_type].append(i)

    # 批量打乱（如果需要）
    if shuffle_enabled:
        for indices_list in indices_by_type.values():
            random.shuffle(indices_list)

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
    result_indices = []
    type_names = {
        QUESTION_TYPE_SINGLE: "单选题",
        QUESTION_TYPE_MULTIPLE: "多选题",
        QUESTION_TYPE_JUDGMENT: "判断题",
        QUESTION_TYPE_OTHER: "其他类型"
    }

    summary_parts = []
    for q_type in types_to_include:
        indices = indices_by_type[q_type]
        result_indices.extend(indices)
        if indices:
            summary_parts.append(f"{type_names[q_type]} {len(indices)} 道")

    shuffle_status = "已打乱" if shuffle_enabled else "未打乱"
    if summary_parts:
        logger.info(f"题目生成完成 ({shuffle_status}): {', '.join(summary_parts)}, 总计 {len(result_indices)} 道")

    return result_indices


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
        'selected_question_types': selected_types or ['single_choice', 'multiple_choice', 'judgment', 'other'],
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
    current_tiku_id = get_session_value(SESSION_KEYS['CURRENT_TIKU_ID'])
    if not current_tiku_id:
        # If there's no tiku_id in session, it's a clear sign of no active practice or expired session
        clear_practice_session()  # Defensive clear
        raise BadRequest("没有选择题库或会话已过期，请重新开始练习")

    try:
        current_tiku_id = int(current_tiku_id)
        question_bank = cache_manager.get_question_bank(current_tiku_id)
    except ValueError:
        clear_practice_session()
        raise BadRequest("无效的题库ID格式，请重新开始练习")
    except Exception as e:  # Catch potential errors from get_question_bank (e.g., DB issues)
        logger.error(f"Error fetching question bank for tiku {current_tiku_id}: {e}")
        clear_practice_session()
        raise BadRequest("加载题库数据失败，请稍后重试或重新开始练习")

    if not question_bank:
        # This implies the tiku was valid at start_practice but now isn't in cache and can't be reloaded,
        # or it was empty to begin with.
        logger.warning(f"Question bank for tiku {current_tiku_id} is unavailable. Clearing session.")
        clear_practice_session()
        raise BadRequest("题库数据丢失或无效，您的练习会话已清除，请重新开始")

    q_indices = get_session_value(SESSION_KEYS['QUESTION_INDICES'])
    if not q_indices:
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

    question_index = q_indices[current_idx]
    question_obj = question_bank[question_index]

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

    session_config = {
        'question_types': get_session_value('selected_question_types'),
        'shuffle_enabled': get_session_value('shuffle_enabled', True),
        'tiku_id': current_tiku_id
    }

    return create_response(True, data={
        'question': question_data,
        'progress': progress_data,
        'flash_messages': flash_messages,
        'session_config': session_config
    })


@practice_bp.route('/practice/submit', methods=['POST'])
@handle_api_error
@performance_monitor
def api_submit_answer():
    """提交答案 - 优化版本"""
    data = request.get_json()
    if not data:
        raise BadRequest("缺少请求数据")

    user_answer = data.get('answer', '').upper()
    question_id = data.get('question_id')
    peeked = data.get('peeked', False)
    is_review = data.get('is_review', False)

    if not question_id:
        raise BadRequest("缺少题目ID")

    current_tiku_id = get_session_value(SESSION_KEYS['CURRENT_TIKU_ID'])
    if not current_tiku_id:
        clear_practice_session()
        raise BadRequest("无效的会话或题库，请重新开始练习")

    try:
        current_tiku_id = int(current_tiku_id)
        question_bank = cache_manager.get_question_bank(current_tiku_id)
    except ValueError:
        clear_practice_session()
        raise BadRequest("无效的题库ID格式，请重新开始练习")
    except Exception as e:
        logger.error(f"Error fetching question bank for tiku {current_tiku_id} during submit: {e}")
        clear_practice_session()
        raise BadRequest("加载题库数据失败，请稍后重试或重新开始练习")

    if not question_bank:
        logger.warning(f"Question bank for tiku {current_tiku_id} unavailable during submit. Clearing session.")
        clear_practice_session()
        raise BadRequest("题库数据丢失或无效，您的练习会话已清除，请重新开始")

    q_indices = get_session_value(SESSION_KEYS['QUESTION_INDICES'], [])
    current_idx = get_session_value(SESSION_KEYS['CURRENT_INDEX'], 0)

    if current_idx >= len(q_indices):
        raise BadRequest("没有更多题目")

    question_index = q_indices[current_idx]
    question_data = question_bank[question_index]

    # 验证题目ID匹配
    if question_data['id'] != question_id:
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

    if not is_review:
        update_practice_record(question_data, is_correct, peeked, current_idx, user_answer)

    return create_response(True, data={
        "is_correct": is_correct,
        "user_answer_display": user_answer_display,
        "correct_answer_display": correct_answer_display,
        "question_id": question_id,
        "current_index": current_idx
    })


def update_practice_record(question_data, is_correct: bool, peeked: bool, current_idx: int, user_answer: str):
    """更新练习记录 - 优化版本"""
    q_indices = get_session_value(SESSION_KEYS['QUESTION_INDICES'], [])
    actual_question_index = q_indices[current_idx]

    # 批量获取session值避免多次调用
    question_statuses = get_session_value(SESSION_KEYS['QUESTION_STATUSES'], [])
    answer_history = get_session_value(SESSION_KEYS['ANSWER_HISTORY'], {})
    wrong_indices = get_session_value(SESSION_KEYS['WRONG_INDICES'], [])

    # 更新题目状态
    if current_idx < len(question_statuses):
        question_statuses[current_idx] = QUESTION_STATUS['CORRECT'] if (is_correct and not peeked) else QUESTION_STATUS[
            'WRONG']

    # 保存答题历史
    answer_history[str(current_idx)] = {
        'user_answer': user_answer,
        'is_correct': is_correct,
        'peeked': peeked,
        'question_data': question_data
    }

    # 处理错题和正确题
    if not is_correct or peeked:
        if actual_question_index not in wrong_indices:
            wrong_indices.append(actual_question_index)
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

    # 异步更新数据库记录
    try:
        update_data = {
            'current_question_index': next_index,
            'correct_first_try': get_session_value(SESSION_KEYS['CORRECT_FIRST_TRY'], 0),
            'round_number': get_session_value(SESSION_KEYS['ROUND_NUMBER'], 1),
            'wrong_indices': wrong_indices,
            'question_statuses': question_statuses,
            'answer_history': answer_history
        }

        if update_current_practice_session(**update_data):
            logger.debug("练习会话数据库记录更新成功")
        else:
            logger.warning("练习会话数据库记录更新失败")

    except Exception as e:
        logger.error(f"更新练习会话数据库记录时发生错误: {e}")


@practice_bp.route('/completed_summary', methods=['GET'])
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

    q_indices = get_session_value(SESSION_KEYS['QUESTION_INDICES'], [])
    if not q_indices or target_index >= len(q_indices):
        raise BadRequest("题目索引超出范围")

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
    current_tiku_id = get_session_value(SESSION_KEYS['CURRENT_TIKU_ID'])

    if not current_tiku_id:
        return create_response(True, '没有活跃的练习会话', {'has_session': False})

    # 获取题库显示名称
    tiku_info = get_current_tiku_info()
    display_name = tiku_info['tiku_name'] if tiku_info else str(current_tiku_id)

    current_indices = get_session_value(SESSION_KEYS['QUESTION_INDICES'], [])
    current_index = get_session_value(SESSION_KEYS['CURRENT_INDEX'], 0)

    return create_response(True, '当前有活跃的练习会话', {
        'has_session': True,
        'tiku_id': current_tiku_id,
        'file_info': {
            'display': display_name,
            'current_question': current_index + 1,
            'total_questions': len(current_indices)
        }
    })


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
            'subjects_count': result['subjects_count']
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
@handle_api_error
def api_get_question_history(question_index: int):
    """获取题目答题历史"""
    q_indices = get_session_value(SESSION_KEYS['QUESTION_INDICES'], [])

    if question_index < 0 or question_index >= len(q_indices):
        raise BadRequest(f'无效的题目索引。有效范围: 0-{len(q_indices) - 1}')

    answer_history = get_session_value(SESSION_KEYS['ANSWER_HISTORY'], {})
    history_key = str(question_index)

    if history_key not in answer_history:
        raise NotFound('该题目没有答题历史')

    history_data = answer_history[history_key]
    question_data = history_data['question_data']

    # 格式化答案显示
    options = question_data.get('options_for_practice', {})
    is_multiple_choice = question_data.get('is_multiple_choice', False)
    correct_answer = question_data['answer'].upper()
    user_answer = history_data['user_answer']

    user_answer_display = '未作答（直接查看答案）' if history_data['peeked'] else format_answer_display(user_answer,
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
            'peeked': history_data['peeked']
        }
    })


@practice_bp.route('/practice/question/<question_id>/details', methods=['GET'])
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
            SESSION_KEYS['CURRENT_TIKU_ID']: tiku_id,
            SESSION_KEYS['QUESTION_INDICES']: question_indices,
            SESSION_KEYS['CURRENT_INDEX']: 0,
            SESSION_KEYS['WRONG_INDICES']: [],
            SESSION_KEYS['ROUND_NUMBER']: 1,
            SESSION_KEYS['INITIAL_TOTAL']: len(question_indices),
            SESSION_KEYS['CORRECT_FIRST_TRY']: 0,
            SESSION_KEYS['QUESTION_STATUSES']: [QUESTION_STATUS['UNANSWERED']] * len(question_indices),
            SESSION_KEYS['ANSWER_HISTORY']: {},
            'selected_question_types': selected_types or ['single_choice', 'multiple_choice', 'judgment', 'other'],
            'shuffle_enabled': shuffle_questions
        }

        for key, value in session_data.items():
            set_session_value(key, value)

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


@practice_bp.route('/cache/test', methods=['GET'])
@login_required
@handle_api_error
def api_test_cache():
    """测试缓存系统是否正常工作"""
    try:
        # 测试题库列表缓存
        tiku_data = cache_manager.get_tiku_list()
        tiku_count = len(tiku_data['tiku_list']) if tiku_data and 'tiku_list' in tiku_data else 0

        # 测试文件选项缓存
        file_options = cache_manager.get_file_options()
        subjects_count = len(file_options) if file_options else 0

        # 测试题目缓存（如果有活跃的题库）
        question_bank_test = None
        if tiku_count > 0:
            first_tiku = tiku_data['tiku_list'][0]
            if first_tiku['is_active']:
                test_tiku_id = first_tiku['tiku_id']
                question_bank_test = cache_manager.get_question_bank(test_tiku_id)

        cache_test_result = {
            'tiku_list_cache': {
                'status': 'ok' if tiku_count > 0 else 'empty',
                'count': tiku_count
            },
            'file_options_cache': {
                'status': 'ok' if subjects_count > 0 else 'empty',
                'subjects_count': subjects_count
            },
            'question_bank_cache': {
                'status': 'ok' if question_bank_test else 'not_tested',
                'test_questions': len(question_bank_test) if question_bank_test else 0
            }
        }

        return create_response(True, '缓存系统测试完成', {
            'cache_test': cache_test_result,
            'timestamp': time.time()
        })

    except Exception as e:
        logger.error(f"缓存测试失败: {e}")
        return create_response(False, f'缓存测试失败: {str(e)}', status_code=500)
