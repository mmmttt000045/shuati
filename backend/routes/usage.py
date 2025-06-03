"""
使用统计相关的路由模块
"""
import logging
from flask import Blueprint, jsonify, request

from ..decorators import handle_api_error, login_required
from ..utils import create_response
from ..connectDB import get_usage_statistics
from ..routes.practice import tiku_usage_stats, usage_stats_lock

logger = logging.getLogger(__name__)

# 创建蓝图
usage_bp = Blueprint('usage', __name__, url_prefix='/api')


@usage_bp.route('/usage-stats', methods=['GET'])
@login_required
@handle_api_error
def api_usage_stats():
    """获取使用统计信息"""
    try:
        stats_result = get_usage_statistics()
        
        if not stats_result:
            return create_response(False, "获取统计数据失败", status_code=500)
        
        if not stats_result.get('success'):
            return create_response(False, stats_result.get('error', '未知错误'), status_code=500)
        
        # 构造返回数据
        response_data = {
            'subject_stats': stats_result.get('subject_stats', []),
            'tiku_stats': stats_result.get('tiku_stats', [])
        }

        return create_response(True, "获取统计数据成功", data=response_data)
        
    except Exception as e:
        logger.error(f"获取使用统计失败: {str(e)}")
        return create_response(False, f"获取统计数据失败: {str(e)}", status_code=500)


@usage_bp.route('/usage-stats/summary', methods=['GET'])
@login_required
@handle_api_error
def api_usage_stats_summary():
    """获取使用统计摘要信息"""
    try:
        stats_result = get_usage_statistics()
        
        if not stats_result or not stats_result.get('success'):
            return create_response(False, "获取统计数据失败", status_code=500)
        
        subject_stats = stats_result.get('subject_stats', [])
        tiku_stats = stats_result.get('tiku_stats', [])
        
        # 计算摘要信息
        total_subject_usage = sum(item['used_count'] for item in subject_stats)
        total_tiku_usage = sum(item['used_count'] for item in tiku_stats)
        active_subjects = len([item for item in subject_stats if item['used_count'] > 0])
        active_tikues = len([item for item in tiku_stats if item['used_count'] > 0])
        
        # 获取最受欢迎的科目和题库
        most_popular_subject = subject_stats[0] if subject_stats else None
        most_popular_tiku = tiku_stats[0] if tiku_stats else None
        
        summary_data = {
            'total_subject_usage': total_subject_usage,
            'total_tiku_usage': total_tiku_usage,
            'active_subjects_count': active_subjects,
            'active_tikues_count': active_tikues,
            'most_popular_subject': most_popular_subject,
            'most_popular_tiku': most_popular_tiku,
            'total_subjects': len(subject_stats),
            'total_tikues': len(tiku_stats)
        }

        return create_response(True, "获取统计摘要成功", data=summary_data)
        
    except Exception as e:
        logger.error(f"获取使用统计摘要失败: {str(e)}")
        return create_response(False, f"获取统计摘要失败: {str(e)}", status_code=500)



@usage_bp.route('/usage-stats/top-subjects', methods=['GET'])
@login_required
@handle_api_error
def api_top_subjects():
    """获取热门科目排行榜"""
    try:
        # 获取数量参数，默认10个
        limit = request.args.get('limit', '10')
        try:
            limit = int(limit)
            limit = max(1, min(limit, 50))  # 限制在1-50之间
        except ValueError:
            limit = 10
        
        stats_result = get_usage_statistics()
        
        if not stats_result or not stats_result.get('success'):
            return create_response(False, "获取统计数据失败", status_code=500)
        
        subject_stats = stats_result.get('subject_stats', [])
        
        # 取前N个科目
        top_subjects = subject_stats[:limit]
        
        # 计算排名和百分比
        total_usage = sum(item['used_count'] for item in subject_stats) if subject_stats else 1
        
        for i, subject in enumerate(top_subjects):
            subject['rank'] = i + 1
            subject['usage_percentage'] = round((subject['used_count'] / total_usage) * 100, 2)
        
        response_data = {
            'top_subjects': top_subjects,
            'total_subjects': len(subject_stats),
            'limit': limit
        }

        return create_response(True, "获取热门科目排行榜成功", data=response_data)
        
    except Exception as e:
        logger.error(f"获取热门科目排行榜失败: {str(e)}")
        return create_response(False, f"获取热门科目排行榜失败: {str(e)}", status_code=500)


@usage_bp.route('/usage-stats/top-tikues', methods=['GET'])
@login_required
@handle_api_error
def api_top_tikues():
    """获取热门题库排行榜"""
    try:
        # 获取数量参数，默认20个
        limit = request.args.get('limit', '20')
        try:
            limit = int(limit)
            limit = max(1, min(limit, 100))  # 限制在1-100之间
        except ValueError:
            limit = 20
        
        stats_result = get_usage_statistics()
        
        if not stats_result or not stats_result.get('success'):
            return create_response(False, "获取统计数据失败", status_code=500)
        
        tiku_stats = stats_result.get('tiku_stats', [])
        
        # 取前N个题库
        top_tikues = tiku_stats[:limit]
        
        # 计算排名和百分比
        total_usage = sum(item['used_count'] for item in tiku_stats) if tiku_stats else 1
        
        for i, tiku in enumerate(top_tikues):
            tiku['rank'] = i + 1
            tiku['usage_percentage'] = round((tiku['used_count'] / total_usage) * 100, 2)
        
        response_data = {
            'top_tikues': top_tikues,
            'total_tikues': len(tiku_stats),
            'limit': limit
        }

        return create_response(True, "获取热门题库排行榜成功", data=response_data)
        
    except Exception as e:
        logger.error(f"获取热门题库排行榜失败: {str(e)}")
        return create_response(False, f"获取热门题库排行榜失败: {str(e)}", status_code=500)
