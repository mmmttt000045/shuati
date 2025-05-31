#!/usr/bin/env python3
"""
测试题目状态数组的内存优化效果
"""
import sys

# 定义状态常量
QUESTION_STATUS = {
    'UNANSWERED': 0,  # 未作答
    'CORRECT': 1,     # 答对
    'WRONG': 2        # 答错/查看答案
}

def test_memory_usage():
    """测试字符串vs数字状态的内存占用"""
    
    # 模拟1000道题目的状态数组
    question_count = 1000
    
    # 使用字符串状态
    string_statuses = ['unanswered'] * question_count
    
    # 使用数字状态  
    numeric_statuses = [QUESTION_STATUS['UNANSWERED']] * question_count
    
    # 计算内存占用
    string_size = sys.getsizeof(string_statuses)
    for status in string_statuses:
        string_size += sys.getsizeof(status)
    
    numeric_size = sys.getsizeof(numeric_statuses) 
    for status in numeric_statuses:
        numeric_size += sys.getsizeof(status)
    
    # 输出结果
    print(f"📊 题目状态数组内存占用测试 (题目数量: {question_count})")
    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"🔤 字符串状态: {string_size:,} bytes")
    print(f"🔢 数字状态:   {numeric_size:,} bytes")
    print(f"💾 节省内存:   {string_size - numeric_size:,} bytes ({((string_size - numeric_size) / string_size * 100):.1f}%)")
    print(f"📈 压缩比例:   {string_size / numeric_size:.1f}x")
    
    # 测试JSON序列化大小（模拟网络传输）
    import json
    
    string_json = json.dumps(string_statuses)
    numeric_json = json.dumps(numeric_statuses)
    
    print(f"\n📡 JSON序列化大小测试 (模拟网络传输)")
    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"🔤 字符串JSON: {len(string_json):,} bytes")
    print(f"🔢 数字JSON:   {len(numeric_json):,} bytes") 
    print(f"🌐 传输节省:   {len(string_json) - len(numeric_json):,} bytes ({((len(string_json) - len(numeric_json)) / len(string_json) * 100):.1f}%)")
    
    # 测试访问速度
    import time
    
    # 字符串比较测试
    start_time = time.time()
    for _ in range(100000):
        _ = string_statuses[0] == 'unanswered'
    string_time = time.time() - start_time
    
    # 数字比较测试
    start_time = time.time() 
    for _ in range(100000):
        _ = numeric_statuses[0] == 0
    numeric_time = time.time() - start_time
    
    print(f"\n⚡ 访问速度测试 (100,000次比较)")
    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"🔤 字符串比较: {string_time:.4f}s")
    print(f"🔢 数字比较:   {numeric_time:.4f}s")
    print(f"🚀 速度提升:   {string_time / numeric_time:.1f}x")

if __name__ == '__main__':
    test_memory_usage() 