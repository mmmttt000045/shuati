# 组件目录结构说明

本目录已按功能模块重新组织，以提高代码的可维护性和可读性。

## 目录结构

```
components/
├── auth/                    # 认证相关组件
│   ├── LoginPage.vue       # 登录页面
│   └── RegisterPage.vue    # 注册页面
├── layout/                  # 布局相关组件
│   ├── NavigationBar.vue   # 导航栏
│   └── IndexPage.vue       # 主页面布局
├── quiz/                    # 题目练习相关组件
│   ├── QuizHomePage.vue    # 题目选择首页
│   ├── PracticePage.vue    # 练习页面
│   └── CompletedPage.vue   # 完成页面
├── admin/                   # 管理员功能组件
│   └── SystemControl.vue   # 系统管理控制台
├── stats/                   # 统计相关组件
│   └── UsageStatsPage.vue  # 使用统计页面
├── vip/                     # VIP功能组件
│   ├── VipStatsPage.vue    # VIP学习统计
│   ├── VipExportPage.vue   # VIP错题导出
│   └── VipCollectionsPage.vue # VIP错题集管理
├── common/                  # 通用组件
│   ├── Loading.vue         # 加载组件
│   ├── NotFoundPage.vue    # 404页面
│   └── UserBadge.vue       # 用户徽章
├── icons/                   # 图标组件
└── __tests__/              # 测试文件
```

## 组件分类说明

### 🔐 auth/ - 认证模块
包含用户登录、注册等认证相关的页面组件。

### 🎨 layout/ - 布局模块
包含应用的主要布局组件，如导航栏、主页面容器等。

### 📝 quiz/ - 题目练习模块
包含题目选择、练习、完成等与题目练习相关的所有组件。

### ⚙️ admin/ - 管理员模块
包含系统管理、用户管理等管理员专用功能组件。

### 📊 stats/ - 统计模块
包含各种统计数据展示的组件。

### ⭐ vip/ - VIP功能模块
包含VIP用户专享的功能组件，如高级统计、错题导出等。

### 🔧 common/ - 通用模块
包含在多个模块中都会用到的通用组件。

### 🎯 icons/ - 图标模块
包含应用中使用的各种图标组件。

## 导入路径示例

```typescript
// 认证组件
import LoginPage from '@/components/auth/LoginPage.vue'

// 布局组件
import NavigationBar from '@/components/layout/NavigationBar.vue'

// 题目练习组件
import QuizHomePage from '@/components/quiz/QuizHomePage.vue'

// 通用组件
import Loading from '@/components/common/Loading.vue'

// VIP功能组件
import VipStatsPage from '@/components/vip/VipStatsPage.vue'
```

## 优势

1. **清晰的功能分离**: 每个文件夹都有明确的功能职责
2. **更好的可维护性**: 相关功能的组件集中在一起，便于维护
3. **提高开发效率**: 开发者可以快速定位到需要的组件
4. **便于团队协作**: 不同团队成员可以专注于不同的功能模块
5. **易于扩展**: 新功能可以按模块添加到相应的文件夹中 