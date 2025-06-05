#!/usr/bin/env python3
"""
测试Redis缓存管理器
"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.routes.practice import cache_manager
from backend.connectDB import init_connection_pool
init_connection_pool()

def test_redis_cache():
    """测试Redis缓存功能"""
    print("开始测试Redis缓存管理器...")
    
    # 检查Redis是否可用
    if not cache_manager._is_redis_available():
        print("❌ Redis不可用，请检查Redis服务是否启动")
        return False
        
    print("✅ Redis连接正常")
    
    # 测试基本的设置和获取
    print("\n测试基本缓存操作...")
    test_key = "test_key"
    test_value = {"message": "Hello Redis!", "number": 42}
    
    # 设置缓存
    success = cache_manager._set_to_redis(test_key, test_value, ttl=60)
    if success:
        print("✅ 缓存设置成功")
    else:
        print("❌ 缓存设置失败")
        return False
    
    # 获取缓存
    retrieved_value = cache_manager._get_from_redis(test_key)
    if retrieved_value == test_value:
        print("✅ 缓存获取成功，数据一致")
    else:
        print(f"❌ 缓存获取失败，期望: {test_value}, 实际: {retrieved_value}")
        return False
    
    # 删除缓存
    success = cache_manager._delete_from_redis(test_key)
    if success:
        print("✅ 缓存删除成功")
    else:
        print("❌ 缓存删除失败")
        return False
    
    # 验证删除后无法获取
    retrieved_value = cache_manager._get_from_redis(test_key, default="NOT_FOUND")
    if retrieved_value == "NOT_FOUND":
        print("✅ 缓存删除验证成功")
    else:
        print(f"❌ 缓存删除验证失败，仍能获取到: {retrieved_value}")
        return False
    
    print("\n✅ 所有基本测试通过！")
    
    # 测试缓存管理器的主要方法
    print("\n测试缓存管理器主要功能...")
    
    try:
        # 测试刷新缓存（这会尝试从数据库获取数据）
        print("测试缓存刷新功能...")
        result = cache_manager.refresh_all_cache()
        
        if result and result.get('message'):
            print(f"✅ 缓存刷新成功: {result['message']}")
            print(f"   - 题库数量: {result.get('tiku_count', 0)}")
            print(f"   - 科目数量: {result.get('subjects_count', 0)}")
        else:
            print("⚠️  缓存刷新返回了空结果，可能数据库连接有问题")
            
    except Exception as e:
        print(f"❌ 缓存刷新测试失败: {e}")
        print("这可能是由于数据库连接问题导致的，但Redis缓存本身功能正常")
    
    print("\n🎉 Redis缓存管理器测试完成！")
    return True

if __name__ == "__main__":
    test_redis_cache() 