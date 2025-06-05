from backend.routes.practice import cache_manager

from backend.connectDB import (
    init_connection_pool, cleanup_expired_practice_sessions, batch_update_tiku_usage
)

print("初始化数据库连接池...")
init_connection_pool()

print("测试Redis缓存管理器...")

# 测试刷新缓存
print("刷新所有缓存...")
result = cache_manager.refresh_all_cache()
print(f"缓存刷新结果: {result}")

# 测试获取题库列表
print("获取题库列表...")
tiku_data = cache_manager.get_tiku_list()
print(f"题库数量: {len(tiku_data.get('tiku_list', []))}")

# 测试获取文件选项
print("获取文件选项...")
file_options = cache_manager.get_file_options()
print(f"科目数量: {len(file_options)}")

# 测试获取指定题库的题目（如果存在题库ID为4的数据）
print("测试获取题库4的题目...")
try:
    questions = cache_manager.get_question_bank(4)
    print(f"题库4的题目数量: {len(questions)}")
except Exception as e:
    print(f"获取题库4失败: {e}")

print("测试完成！")