#!/usr/bin/env python3
"""
全面的Redis缓存管理器测试
包含数据库连接重试和详细错误分析
"""
import sys
import os
import time

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.routes.practice import cache_manager
from backend.connectDB import init_connection_pool, get_tiku_by_subject, get_all_subjects

def test_database_connection():
    """测试数据库连接"""
    print("🔍 测试数据库连接...")
    
    try:
        init_connection_pool()
        print("✅ 数据库连接池初始化成功")
        
        # 测试基本查询
        print("📊 测试基本数据库查询...")
        
        # 尝试获取题库数据，带重试机制
        for attempt in range(3):
            try:
                print(f"   尝试第 {attempt + 1} 次获取题库数据...")
                tiku_list = get_tiku_by_subject()
                subjects = get_all_subjects()
                
                print(f"✅ 数据库查询成功")
                print(f"   - 题库数量: {len(tiku_list)}")
                print(f"   - 科目数量: {len(subjects)}")
                return True
                
            except Exception as e:
                print(f"❌ 第 {attempt + 1} 次尝试失败: {e}")
                if attempt < 2:
                    print("   等待5秒后重试...")
                    time.sleep(5)
                else:
                    print("❌ 所有数据库连接尝试都失败了")
                    return False
                    
    except Exception as e:
        print(f"❌ 数据库连接池初始化失败: {e}")
        return False

def test_redis_basic_operations():
    """测试Redis基本操作"""
    print("\n🔧 测试Redis基本操作...")
    
    if not cache_manager._is_redis_available():
        print("❌ Redis不可用，请检查Redis服务是否启动")
        return False
        
    print("✅ Redis连接正常")
    
    # 测试数据
    test_cases = [
        {
            'key': 'test_string',
            'value': 'Hello Redis!',
            'description': '字符串数据'
        },
        {
            'key': 'test_number',
            'value': 42,
            'description': '数字数据'
        },
        {
            'key': 'test_dict',
            'value': {'name': '测试', 'count': 100, 'active': True},
            'description': '字典数据'
        },
        {
            'key': 'test_list',
            'value': [1, 2, 3, '测试', {'nested': True}],
            'description': '列表数据'
        }
    ]
    
    for test_case in test_cases:
        print(f"   测试 {test_case['description']}...")
        
        # 设置缓存
        success = cache_manager._set_to_redis(test_case['key'], test_case['value'], ttl=60)
        if not success:
            print(f"   ❌ 设置失败")
            return False
            
        # 获取缓存
        retrieved_value = cache_manager._get_from_redis(test_case['key'])
        if retrieved_value != test_case['value']:
            print(f"   ❌ 数据不一致")
            print(f"      期望: {test_case['value']}")
            print(f"      实际: {retrieved_value}")
            return False
            
        # 删除缓存
        cache_manager._delete_from_redis(test_case['key'])
        
        # 验证删除
        retrieved_after_delete = cache_manager._get_from_redis(test_case['key'], default='DELETED')
        if retrieved_after_delete != 'DELETED':
            print(f"   ❌ 删除验证失败")
            return False
            
        print(f"   ✅ {test_case['description']} 测试通过")
    
    return True

def test_cache_manager_methods():
    """测试缓存管理器的高级方法"""
    print("\n📚 测试缓存管理器高级功能...")
    
    try:
        # 测试缓存刷新
        print("   测试缓存刷新...")
        result = cache_manager.refresh_all_cache()
        
        if result and isinstance(result, dict):
            print(f"   ✅ 缓存刷新完成: {result.get('message', '无消息')}")
            print(f"      - 题库数量: {result.get('tiku_count', 0)}")
            print(f"      - 科目数量: {result.get('subjects_count', 0)}")
            
            # 如果数据为0，可能是数据库连接问题
            if result.get('tiku_count', 0) == 0:
                print("   ⚠️  题库数量为0，可能是数据库连接问题")
                return False
                
        else:
            print("   ❌ 缓存刷新返回了无效结果")
            return False
            
        # 测试获取题库列表
        print("   测试获取题库列表...")
        tiku_data = cache_manager.get_tiku_list()
        if tiku_data and isinstance(tiku_data, dict):
            tiku_list = tiku_data.get('tiku_list', [])
            print(f"   ✅ 获取题库列表成功，数量: {len(tiku_list)}")
        else:
            print("   ❌ 获取题库列表失败")
            return False
            
        # 测试获取文件选项
        print("   测试获取文件选项...")
        file_options = cache_manager.get_file_options()
        if file_options and isinstance(file_options, dict):
            print(f"   ✅ 获取文件选项成功，科目数量: {len(file_options)}")
        else:
            print("   ❌ 获取文件选项失败")
            return False
            
        # 测试获取题目数据（如果有可用的题库）
        if tiku_list:
            test_tiku = None
            for tiku in tiku_list:
                if tiku.get('is_active', False):
                    test_tiku = tiku
                    break
                    
            if test_tiku:
                print(f"   测试获取题库 {test_tiku['tiku_id']} 的题目...")
                questions = cache_manager.get_question_bank(test_tiku['tiku_id'])
                if questions and isinstance(questions, list):
                    print(f"   ✅ 获取题目成功，数量: {len(questions)}")
                else:
                    print("   ⚠️  题库为空或获取失败")
            else:
                print("   ⚠️  没有可用的活跃题库进行测试")
                
        return True
        
    except Exception as e:
        print(f"   ❌ 缓存管理器测试失败: {e}")
        return False

def test_cache_performance():
    """测试缓存性能"""
    print("\n⚡ 测试缓存性能...")
    
    # 测试大量小数据的性能
    print("   测试批量小数据操作...")
    start_time = time.time()
    
    for i in range(100):
        key = f"perf_test_{i}"
        value = {"id": i, "data": f"test_data_{i}"}
        cache_manager._set_to_redis(key, value, ttl=60)
        
    set_time = time.time() - start_time
    print(f"   ✅ 100个小数据写入耗时: {set_time:.3f}秒")
    
    # 测试读取性能
    start_time = time.time()
    for i in range(100):
        key = f"perf_test_{i}"
        cache_manager._get_from_redis(key)
        
    get_time = time.time() - start_time
    print(f"   ✅ 100个小数据读取耗时: {get_time:.3f}秒")
    
    # 清理测试数据
    for i in range(100):
        key = f"perf_test_{i}"
        cache_manager._delete_from_redis(key)
    
    print(f"   ✅ 性能测试完成 (写入: {set_time:.3f}s, 读取: {get_time:.3f}s)")
    return True

def main():
    """主测试函数"""
    print("🚀 开始全面的Redis缓存管理器测试")
    print("=" * 50)
    
    test_results = []
    
    # 1. 测试数据库连接
    db_result = test_database_connection()
    test_results.append(("数据库连接", db_result))
    
    # 2. 测试Redis基本操作
    redis_result = test_redis_basic_operations()
    test_results.append(("Redis基本操作", redis_result))
    
    # 3. 测试缓存管理器方法
    if db_result and redis_result:
        manager_result = test_cache_manager_methods()
        test_results.append(("缓存管理器功能", manager_result))
        
        # 4. 测试性能
        if manager_result:
            perf_result = test_cache_performance()
            test_results.append(("缓存性能", perf_result))
    
    # 输出测试结果
    print("\n" + "=" * 50)
    print("📊 测试结果总结:")
    
    all_passed = True
    for test_name, result in test_results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"   {test_name}: {status}")
        if not result:
            all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 所有测试都通过了！Redis缓存迁移完全成功！")
    else:
        print("⚠️  部分测试失败，请检查相关配置")
        print("\n💡 故障排除建议：")
        print("   1. 确保Redis服务正在运行")
        print("   2. 检查数据库连接配置")
        print("   3. 验证网络连接稳定性")
        print("   4. 查看详细错误日志")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 