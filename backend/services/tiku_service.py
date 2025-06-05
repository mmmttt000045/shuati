"""
题库管理服务
高性能题库数据管理
"""
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict

from ..cache.hybrid_cache import HybridCacheManager
from ..models import TikuInfo
from ..connectDB import get_tiku_by_subject, get_all_subjects

logger = logging.getLogger(__name__)


class TikuService:
    """题库管理服务"""
    
    def __init__(self, cache_manager: Optional[HybridCacheManager] = None):
        self.cache_manager = cache_manager or HybridCacheManager()
        self._executor = ThreadPoolExecutor(max_workers=3, thread_name_prefix="tiku_")
    
    def get_tiku_list_with_cache(self) -> Dict[str, Any]:
        """获取题库列表（带缓存）"""
        # 尝试从缓存获取
        cached_data = self.cache_manager.get_tiku_list()
        if cached_data:
            logger.debug("使用缓存的题库列表数据")
            return cached_data
        
        logger.info("从数据库重新加载题库列表")
        return self._load_and_cache_tiku_list()
    
    def _load_and_cache_tiku_list(self) -> Dict[str, Any]:
        """从数据库加载并缓存题库列表"""
        try:
            # 并行获取数据
            with ThreadPoolExecutor(max_workers=2) as executor:
                future_tiku = executor.submit(get_tiku_by_subject)
                future_subjects = executor.submit(get_all_subjects)
                
                db_tiku_list = future_tiku.result()
                all_subjects = future_subjects.result()
            
            # 构建科目考试时间映射
            subjects_exam_time = {s['subject_name']: s['exam_time'] for s in all_subjects}
            
            cache_data = {
                'tiku_list': db_tiku_list,
                'subjects_exam_time': subjects_exam_time
            }
            
            # 存储到缓存
            self.cache_manager.set_tiku_list(cache_data)
            logger.info(f"成功加载并缓存了 {len(db_tiku_list)} 个题库")
            return cache_data
            
        except Exception as e:
            logger.error(f"从数据库加载题库列表失败: {e}")
            raise
    
    def get_file_options_with_cache(self) -> Dict[str, Any]:
        """获取文件选项（带缓存）"""
        # 尝试从缓存获取
        cached_data = self.cache_manager.get_file_options()
        if cached_data:
            logger.debug("使用缓存的文件选项数据")
            return cached_data
        
        logger.info("重新构建文件选项缓存")
        return self._build_and_cache_file_options()
    
    def _build_and_cache_file_options(self) -> Dict[str, Any]:
        """构建并缓存文件选项"""
        try:
            # 获取题库数据
            cached_tiku_data = self.get_tiku_list_with_cache()
            db_tiku_list = cached_tiku_data['tiku_list']
            subjects_exam_time = cached_tiku_data['subjects_exam_time']
            
            # 使用defaultdict优化数据处理
            db_tiku_map = defaultdict(lambda: {'files': [], 'exam_time': None})
            
            # 批量处理活跃题库
            active_tikus = [tiku for tiku in db_tiku_list if tiku['is_active']]
            
            for tiku in active_tikus:
                subject_name = tiku['subject_name']
                
                # 设置考试时间（只需设置一次）
                if db_tiku_map[subject_name]['exam_time'] is None:
                    db_tiku_map[subject_name]['exam_time'] = subjects_exam_time.get(subject_name)
                
                # 添加文件信息
                db_tiku_map[subject_name]['files'].append({
                    'key': tiku['tiku_position'],
                    'display': tiku['tiku_name'],
                    'count': tiku['tiku_nums'],
                    'file_size': tiku['file_size'],
                    'updated_at': tiku['updated_at'],
                    'tiku_id': tiku['tiku_id']
                })
            
            # 批量排序优化
            sorted_subjects = {}
            for subject, data in sorted(db_tiku_map.items()):
                sorted_subjects[subject] = {
                    'files': sorted(data['files'], key=lambda x: x['display']),
                    'exam_time': data['exam_time']
                }
            
            # 存储到缓存
            self.cache_manager.set_file_options(sorted_subjects)
            logger.info(f"成功处理并缓存了 {len(sorted_subjects)} 个科目的文件选项")
            return sorted_subjects
            
        except Exception as e:
            logger.error(f"处理文件选项缓存失败: {e}")
            raise
    
    def get_tiku_info(self, tiku_id: int) -> Optional[TikuInfo]:
        """获取指定题库的信息"""
        try:
            cached_tiku_data = self.get_tiku_list_with_cache()
            tiku_list = cached_tiku_data['tiku_list']
            
            for tiku in tiku_list:
                if tiku['tiku_id'] == tiku_id:
                    return TikuInfo.from_db_row(tiku)
            
            return None
            
        except Exception as e:
            logger.error(f"获取题库信息失败 (ID: {tiku_id}): {e}")
            return None
    
    def validate_tiku(self, tiku_id: int) -> Tuple[bool, str, Optional[TikuInfo]]:
        """验证题库是否可用"""
        try:
            tiku_info = self.get_tiku_info(tiku_id)
            
            if not tiku_info:
                return False, f"题库ID {tiku_id} 不存在", None
            
            if not tiku_info.is_active:
                return False, f"题库已禁用: {tiku_info.tiku_name}", None
            
            return True, "题库可用", tiku_info
            
        except Exception as e:
            logger.error(f"验证题库失败 (ID: {tiku_id}): {e}")
            return False, f"题库验证失败: {str(e)}", None
    
    def inject_user_progress(self, subjects_data: Dict[str, Any], 
                           current_tiku_id: int, current_progress: Dict[str, Any]) -> Dict[str, Any]:
        """注入用户进度信息（优化版本）"""
        if not current_tiku_id or not current_progress:
            return subjects_data
        
        # 浅拷贝优化 - 避免深拷贝的性能开销
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
    
    def refresh_cache(self) -> Dict[str, Any]:
        """刷新所有题库相关缓存"""
        try:
            # 清除缓存
            self.cache_manager.delete('tiku_list')
            self.cache_manager.delete('file_options')
            
            # 预热缓存
            tiku_data = self._load_and_cache_tiku_list()
            file_options_data = self._build_and_cache_file_options()
            
            return {
                'tiku_count': len(tiku_data['tiku_list']) if tiku_data else 0,
                'subjects_count': len(file_options_data) if file_options_data else 0,
                'message': '题库缓存刷新成功'
            }
            
        except Exception as e:
            logger.error(f"刷新题库缓存失败: {e}")
            return {
                'tiku_count': 0,
                'subjects_count': 0,
                'message': f'缓存刷新失败: {str(e)}'
            }
    
    def get_tiku_statistics(self) -> Dict[str, Any]:
        """获取题库统计信息"""
        try:
            cached_tiku_data = self.get_tiku_list_with_cache()
            tiku_list = cached_tiku_data['tiku_list']
            
            # 统计信息
            total_count = len(tiku_list)
            active_count = len([t for t in tiku_list if t['is_active']])
            total_questions = sum(t['tiku_nums'] for t in tiku_list if t['is_active'])
            
            # 按科目统计
            subject_stats = defaultdict(lambda: {'count': 0, 'questions': 0, 'active': 0})
            for tiku in tiku_list:
                subject = tiku['subject_name']
                subject_stats[subject]['count'] += 1
                subject_stats[subject]['questions'] += tiku['tiku_nums']
                if tiku['is_active']:
                    subject_stats[subject]['active'] += 1
            
            return {
                'total_tiku_count': total_count,
                'active_tiku_count': active_count,
                'total_questions': total_questions,
                'subjects_count': len(subject_stats),
                'subject_statistics': dict(subject_stats)
            }
            
        except Exception as e:
            logger.error(f"获取题库统计失败: {e}")
            return {
                'total_tiku_count': 0,
                'active_tiku_count': 0,
                'total_questions': 0,
                'subjects_count': 0,
                'error': str(e)
            }
    
    def __del__(self):
        """清理资源"""
        if hasattr(self, '_executor'):
            self._executor.shutdown(wait=False) 