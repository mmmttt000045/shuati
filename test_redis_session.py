#!/usr/bin/env python3
"""
Redis Session 功能测试脚本
"""
import sys
import json
import uuid
from typing import Any, Dict

from backend import RedisManager


def test_redis_session():
    """测试Redis session功能"""
    try:
        from backend.RedisManager import redis_manager
        from backend.config import SESSION_KEYS
        
        print("=== Redis Session 功能测试 ===\n")
        
        # 1. 检查Redis连接
        print("1. 检查Redis连接状态...")
        if redis_manager.is_available:
            print("✓ Redis连接正常")
        else:
            print("✗ Redis连接失败")
            return False
        
        # 2. 生成测试session ID
        test_session_id = str(uuid.uuid4())
        print(f"2. 使用测试Session ID: {test_session_id}")
        
        # 3. 测试数据存储
        print("\n3. 测试数据存储...")
        test_data = {
            'question_indices': [1, 2, 3, 4, 5],
            'wrong_indices': [2, 4],
            'question_statuses': [1, 0, 1, 0, 1],
            'answer_history': ['A', 'B', 'C', 'D', 'A']
        }
        
        for key, value in test_data.items():
            success = redis_manager.store_session_data(test_session_id, key, value)
            if success:
                print(f"✓ 存储 {key}: {value}")
            else:
                print(f"✗ 存储 {key} 失败")
                return False
        
        # 4. 测试数据读取
        print("\n4. 测试数据读取...")
        for key, expected_value in test_data.items():
            retrieved_value = redis_manager.get_session_data(test_session_id, key)
            if retrieved_value == expected_value:
                print(f"✓ 读取 {key}: {retrieved_value}")
            else:
                print(f"✗ 读取 {key} 失败，期望: {expected_value}, 实际: {retrieved_value}")
                return False
        
        # 5. 测试获取所有数据
        print("\n5. 测试获取所有session数据...")
        all_data = redis_manager.get_all_session_data(test_session_id)
        if len(all_data) == len(test_data):
            print(f"✓ 获取所有数据成功，共 {len(all_data)} 个字段")
        else:
            print(f"✗ 获取所有数据失败，期望 {len(test_data)} 个字段，实际 {len(all_data)} 个")
            return False
        
        # 6. 测试TTL延长
        print("\n6. 测试TTL延长...")
        success = redis_manager.extend_session_ttl(test_session_id, 3600)
        if success:
            print("✓ TTL延长成功")
        else:
            print("✗ TTL延长失败")
            return False
        
        # 7. 测试单个字段删除
        print("\n7. 测试单个字段删除...")
        success = redis_manager.delete_session_data(test_session_id, 'wrong_indices')
        if success:
            print("✓ 删除单个字段成功")
            # 验证字段已删除
            value = redis_manager.get_session_data(test_session_id, 'wrong_indices')
            if value is None:
                print("✓ 字段确实已删除")
            else:
                print(f"✗ 字段删除验证失败，仍然存在: {value}")
                return False
        else:
            print("✗ 删除单个字段失败")
            return False
        
        # 8. 测试整个session删除
        print("\n8. 测试整个session删除...")
        success = redis_manager.delete_session_data(test_session_id)
        if success:
            print("✓ 删除整个session成功")
            # 验证session已删除
            all_data = redis_manager.get_all_session_data(test_session_id)
            if len(all_data) == 0:
                print("✓ Session确实已删除")
            else:
                print(f"✗ Session删除验证失败，仍然存在数据: {all_data}")
                return False
        else:
            print("✗ 删除整个session失败")
            return False
        
        print("\n✓ 所有Redis session功能测试通过！")
        return True
        
    except Exception as e:
        print(f"\n✗ Redis session测试异常: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_hybrid_session():
    """测试混合session接口"""
    try:
        from backend.RedisManager import get_hybrid_session_value, set_hybrid_session_value, REDIS_STORED_KEYS
        from backend.config import SESSION_KEYS
        
        print("\n=== 混合Session接口测试 ===")
        
        # 模拟Flask session
        class MockSession:
            def __init__(self):
                self.data = {}
                self.modified = False
            
            def get(self, key, default=None):
                return self.data.get(key, default)
            
            def __setitem__(self, key, value):
                self.data[key] = value
                self.modified = True
        
        # 替换全局session对象（仅用于测试）
        import backend.RedisManager
        original_session = RedisManager.session
        mock_session = MockSession()
        RedisManager.session = mock_session
        
        try:
            # 测试大数据key（应该存储在Redis中）
            print("\n1. 测试大数据key存储...")
            large_data_key = SESSION_KEYS['QUESTION_INDICES']
            test_indices = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
            
            # 设置session ID
            mock_session.data['session_id'] = str(uuid.uuid4())
            
            set_hybrid_session_value(large_data_key, test_indices)
            retrieved_indices = get_hybrid_session_value(large_data_key)
            
            if retrieved_indices == test_indices:
                print(f"✓ 大数据key存储和读取成功: {large_data_key}")
            else:
                print(f"✗ 大数据key测试失败，期望: {test_indices}, 实际: {retrieved_indices}")
                return False
            
            # 测试小数据key（应该存储在cookie中）
            print("\n2. 测试小数据key存储...")
            small_data_key = 'test_small_key'
            test_value = 'test_value'
            
            set_hybrid_session_value(small_data_key, test_value)
            retrieved_value = get_hybrid_session_value(small_data_key)
            
            if retrieved_value == test_value:
                print(f"✓ 小数据key存储和读取成功: {small_data_key}")
            else:
                print(f"✗ 小数据key测试失败，期望: {test_value}, 实际: {retrieved_value}")
                return False
            
            print("\n✓ 混合session接口测试通过！")
            return True
            
        finally:
            # 恢复原始session对象
            RedisManager.session = original_session
            
    except Exception as e:
        print(f"\n✗ 混合session测试异常: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_cache_functionality():
    """测试缓存功能"""
    try:
        from backend.RedisManager import redis_manager
        
        print("\n=== Redis缓存功能测试 ===")
        
        # 1. 测试基本缓存操作
        print("\n1. 测试基本缓存操作...")
        test_key = 'test_cache_key'
        test_data = {'name': '测试数据', 'value': 123, 'list': [1, 2, 3]}
        
        # 设置缓存
        success = redis_manager.cache_set(test_key, test_data, 300)  # 5分钟TTL
        if success:
            print(f"✓ 缓存设置成功: {test_key}")
        else:
            print(f"✗ 缓存设置失败: {test_key}")
            return False
        
        # 获取缓存
        cached_data = redis_manager.cache_get(test_key)
        if cached_data == test_data:
            print(f"✓ 缓存读取成功: {test_key}")
        else:
            print(f"✗ 缓存读取失败，期望: {test_data}, 实际: {cached_data}")
            return False
        
        # 检查缓存存在性
        exists = redis_manager.cache_exists(test_key)
        if exists:
            print(f"✓ 缓存存在性检查成功: {test_key}")
        else:
            print(f"✗ 缓存存在性检查失败: {test_key}")
            return False
        
        # 获取TTL
        ttl = redis_manager.cache_ttl(test_key)
        if ttl > 0:
            print(f"✓ 缓存TTL获取成功: {test_key}, TTL: {ttl}秒")
        else:
            print(f"✗ 缓存TTL获取失败: {test_key}, TTL: {ttl}")
            return False
        
        # 删除缓存
        success = redis_manager.cache_delete(test_key)
        if success:
            print(f"✓ 缓存删除成功: {test_key}")
        else:
            print(f"✗ 缓存删除失败: {test_key}")
            return False
        
        # 验证缓存已删除
        cached_data = redis_manager.cache_get(test_key)
        if cached_data is None:
            print(f"✓ 缓存删除验证成功: {test_key}")
        else:
            print(f"✗ 缓存删除验证失败，仍然存在: {cached_data}")
            return False
        
        print("\n✓ Redis缓存功能测试通过！")
        return True
        
    except Exception as e:
        print(f"\n✗ Redis缓存测试异常: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("开始Redis功能测试...\n")
    
    # 运行所有测试
    redis_test_passed = test_redis_session()
    hybrid_test_passed = test_hybrid_session()
    cache_test_passed = test_cache_functionality()
    
    print("\n" + "="*50)
    print("测试结果汇总:")
    print(f"Redis Session测试: {'✓ 通过' if redis_test_passed else '✗ 失败'}")
    print(f"混合Session测试: {'✓ 通过' if hybrid_test_passed else '✗ 失败'}")
    print(f"Redis缓存测试: {'✓ 通过' if cache_test_passed else '✗ 失败'}")
    
    if redis_test_passed and hybrid_test_passed and cache_test_passed:
        print("\n🎉 所有测试通过！Redis功能正常。")
        sys.exit(0)
    else:
        print("\n❌ 部分测试失败，请检查Redis配置和连接。")
        sys.exit(1) 