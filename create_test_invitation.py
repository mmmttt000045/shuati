#!/usr/bin/env python3
"""
创建测试邀请码的脚本
"""

from connectDB import create_invitation_code

def main():
    # 创建一个测试邀请码，有效期30天
    invitation_code = "guoyuan"
    expires_days = 30
    
    print(f"正在创建邀请码: {invitation_code}")
    result = create_invitation_code(invitation_code, expires_days)
    
    if result['success']:
        print(f"✅ 邀请码创建成功!")
        print(f"   邀请码: {result['code']}")
        print(f"   过期时间: {result['expires_at']}")
        print(f"\n🎯 您现在可以使用邀请码 '{invitation_code}' 来注册新用户了!")
    else:
        print(f"❌ 邀请码创建失败: {result['error']}")

if __name__ == "__main__":
    main() 