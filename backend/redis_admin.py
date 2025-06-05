#!/usr/bin/env python3
"""
Redis Session 管理工具
用于监控、管理和维护Redis中的session数据
"""
import argparse
import json
import sys
from datetime import datetime
from typing import Dict, List, Any
from redis_session import redis_session_manager, RedisConfig


class RedisSessionAdmin:
    """Redis Session管理工具类"""
    
    def __init__(self):
        self.redis_manager = redis_session_manager
    
    def check_status(self) -> Dict[str, Any]:
        """检查Redis状态"""
        if not self.redis_manager.is_available:
            return {
                'status': 'unavailable',
                'message': 'Redis连接不可用'
            }
        
        try:
            # 获取Redis信息
            info = self.redis_manager._redis_client.info()
            
            # 获取session统计
            pattern = f"{RedisConfig.REDIS_SESSION_PREFIX}*"
            keys = self.redis_manager._redis_client.keys(pattern)
            
            active_sessions = 0
            expired_sessions = 0
            
            for key in keys:
                ttl = self.redis_manager._redis_client.ttl(key)
                if ttl > 0:
                    active_sessions += 1
                elif ttl == -2:
                    expired_sessions += 1
            
            return {
                'status': 'available',
                'redis_version': info.get('redis_version'),
                'memory_used': info.get('used_memory_human'),
                'connected_clients': info.get('connected_clients'),
                'total_commands_processed': info.get('total_commands_processed'),
                'active_sessions': active_sessions,
                'expired_sessions': expired_sessions,
                'total_keys': len(keys)
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'message': f'获取Redis状态失败: {e}'
            }
    
    def list_sessions(self, limit: int = 50) -> List[Dict[str, Any]]:
        """列出活跃的sessions"""
        if not self.redis_manager.is_available:
            return []
        
        try:
            pattern = f"{RedisConfig.REDIS_SESSION_PREFIX}*"
            keys = self.redis_manager._redis_client.keys(pattern)
            
            sessions = []
            for key in keys[:limit]:
                session_id = key.replace(RedisConfig.REDIS_SESSION_PREFIX, '')
                ttl = self.redis_manager._redis_client.ttl(key)
                
                if ttl > 0:  # 只显示活跃的sessions
                    session_data = self.redis_manager.get_all_session_data(session_id)
                    sessions.append({
                        'session_id': session_id,
                        'ttl_seconds': ttl,
                        'data_keys': list(session_data.keys()),
                        'data_size': len(str(session_data))
                    })
            
            return sorted(sessions, key=lambda x: x['ttl_seconds'], reverse=True)
            
        except Exception as e:
            print(f"列出sessions失败: {e}")
            return []
    
    def get_session_detail(self, session_id: str) -> Dict[str, Any]:
        """获取session详细信息"""
        if not self.redis_manager.is_available:
            return {'error': 'Redis不可用'}
        
        try:
            redis_key = self.redis_manager._get_session_key(session_id)
            ttl = self.redis_manager._redis_client.ttl(redis_key)
            
            if ttl == -2:
                return {'error': 'Session不存在或已过期'}
            
            session_data = self.redis_manager.get_all_session_data(session_id)
            
            return {
                'session_id': session_id,
                'ttl_seconds': ttl,
                'expires_at': (datetime.now().timestamp() + ttl) if ttl > 0 else None,
                'data': session_data
            }
            
        except Exception as e:
            return {'error': f'获取session详情失败: {e}'}
    
    def delete_session(self, session_id: str) -> bool:
        """删除指定session"""
        if not self.redis_manager.is_available:
            return False
        
        return self.redis_manager.delete_session_data(session_id)
    
    def cleanup_expired_sessions(self) -> int:
        """清理过期sessions"""
        return self.redis_manager.cleanup_expired_sessions()
    
    def extend_session(self, session_id: str, ttl: int = None) -> bool:
        """延长session过期时间"""
        if not self.redis_manager.is_available:
            return False
        
        return self.redis_manager.extend_session_ttl(session_id, ttl)


def main():
    """命令行工具入口"""
    parser = argparse.ArgumentParser(description='Redis Session管理工具')
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # status命令
    status_parser = subparsers.add_parser('status', help='检查Redis状态')
    
    # list命令
    list_parser = subparsers.add_parser('list', help='列出活跃sessions')
    list_parser.add_argument('--limit', type=int, default=50, help='显示数量限制')
    
    # detail命令
    detail_parser = subparsers.add_parser('detail', help='查看session详情')
    detail_parser.add_argument('session_id', help='Session ID')
    
    # delete命令
    delete_parser = subparsers.add_parser('delete', help='删除session')
    delete_parser.add_argument('session_id', help='Session ID')
    
    # cleanup命令
    cleanup_parser = subparsers.add_parser('cleanup', help='清理过期sessions')
    
    # extend命令
    extend_parser = subparsers.add_parser('extend', help='延长session过期时间')
    extend_parser.add_argument('session_id', help='Session ID')
    extend_parser.add_argument('--ttl', type=int, help='新的TTL秒数')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    admin = RedisSessionAdmin()
    
    if args.command == 'status':
        status = admin.check_status()
        print(json.dumps(status, indent=2, ensure_ascii=False))
    
    elif args.command == 'list':
        sessions = admin.list_sessions(args.limit)
        if sessions:
            print(f"找到 {len(sessions)} 个活跃sessions:")
            for session in sessions:
                print(f"  {session['session_id'][:16]}... TTL: {session['ttl_seconds']}s, "
                      f"Keys: {session['data_keys']}, Size: {session['data_size']} bytes")
        else:
            print("没有找到活跃的sessions")
    
    elif args.command == 'detail':
        detail = admin.get_session_detail(args.session_id)
        print(json.dumps(detail, indent=2, ensure_ascii=False, default=str))
    
    elif args.command == 'delete':
        success = admin.delete_session(args.session_id)
        if success:
            print(f"Session {args.session_id} 已删除")
        else:
            print(f"删除Session {args.session_id} 失败")
    
    elif args.command == 'cleanup':
        count = admin.cleanup_expired_sessions()
        print(f"清理了 {count} 个过期sessions")
    
    elif args.command == 'extend':
        success = admin.extend_session(args.session_id, args.ttl)
        if success:
            print(f"Session {args.session_id} 过期时间已延长")
        else:
            print(f"延长Session {args.session_id} 过期时间失败")


if __name__ == '__main__':
    main() 