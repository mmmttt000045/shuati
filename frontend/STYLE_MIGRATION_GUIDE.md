# 样式系统迁移指南

## 📝 概述

本项目已经升级到统一的设计系统，所有样式现在使用一套标准化的设计令牌。

## 🎨 新的样式系统结构

```
src/assets/
├── design-system.css  # 核心设计系统 (颜色、间距、字体等)
├── components.css     # 组件样式 (按钮、表单、卡片等)
├── main.css          # 应用程序特定样式
└── theme.css         # 向后兼容层 (过渡期保留)
```

## 🚀 主要改进

### 1. 统一的颜色系统
- 使用数字化颜色等级 (50-900)
- 语义化颜色命名
- 支持暗色模式

### 2. 一致的间距系统
- 基于4px的间距单位
- 响应式间距变量

### 3. 完整的组件库
- 预定义的按钮样式
- 统一的表单组件
- 标准化的卡片样式

### 4. 无障碍优化
- 符合WCAG标准的颜色对比度
- 键盘导航支持
- 屏幕阅读器友好

## 📋 变量映射表

### 颜色变量

| 旧变量 | 新变量 | 说明 |
|--------|--------|------|
| `--primary-color` | `var(--color-primary)` | 主要颜色 |
| `--primary-hover` | `var(--color-primary-hover)` | 主要颜色悬停 |
| `--success-color` | `var(--color-success)` | 成功状态 |
| `--error-color` | `var(--color-error)` | 错误状态 |
| `--warning-color` | `var(--color-warning)` | 警告状态 |

### 间距变量

| 旧变量 | 新变量 | 值 |
|--------|--------|-----|
| `--space-1` | `var(--space-1)` | 4px |
| `--space-2` | `var(--space-2)` | 8px |
| `--space-3` | `var(--space-3)` | 12px |
| `--space-4` | `var(--space-4)` | 16px |

### 字体变量

| 旧变量 | 新变量 | 值 |
|--------|--------|-----|
| `--text-sm` | `var(--text-sm)` | 14px |
| `--text-base` | `var(--text-base)` | 16px |
| `--text-lg` | `var(--text-lg)` | 18px |

## 🔧 推荐的组件类

### 按钮

```css
/* 主要按钮 */
.btn.btn-primary

/* 次要按钮 */
.btn.btn-secondary

/* 轮廓按钮 */
.btn.btn-outline

/* 尺寸变体 */
.btn.btn-sm    /* 小按钮 */
.btn.btn-lg    /* 大按钮 */
.btn.btn-full  /* 全宽按钮 */
```

### 表单

```css
/* 表单组 */
.form-group

/* 表单标签 */
.form-label

/* 表单控件 */
.form-control

/* 错误状态 */
.form-control.form-control-error

/* 错误信息 */
.form-error
```

### 卡片

```css
/* 基础卡片 */
.card

/* 卡片头部 */
.card-header

/* 卡片内容 */
.card-body

/* 卡片底部 */
.card-footer

/* 悬停效果 */
.card.card-hover
```

### 消息提示

```css
/* 基础消息 */
.message

/* 状态变体 */
.message.message-success
.message.message-warning
.message.message-error
.message.message-info
```

## 📱 响应式工具类

### 间距

```css
.p-0, .p-1, .p-2, .p-3, .p-4, .p-6, .p-8, .p-10, .p-12
.m-0, .m-1, .m-2, .m-3, .m-4, .m-6, .m-8, .m-10, .m-12
```

### 布局

```css
.flex, .inline-flex, .grid, .block, .hidden
.items-center, .justify-center, .justify-between
.flex-col, .flex-row, .flex-wrap
.gap-1, .gap-2, .gap-3, .gap-4, .gap-6, .gap-8
```

### 文本

```css
.text-center, .text-left, .text-right
.text-primary, .text-secondary, .text-white
.font-normal, .font-medium, .font-semibold, .font-bold
```

## 🎯 最佳实践

### 1. 使用语义化类名
```css
/* ✅ 推荐 */
.btn.btn-primary
.message.message-success

/* ❌ 避免 */
.blue-button
.green-box
```

### 2. 利用设计令牌
```css
/* ✅ 推荐 */
padding: var(--space-4);
color: var(--text-primary);

/* ❌ 避免 */
padding: 16px;
color: #333;
```

### 3. 响应式优先
```css
/* ✅ 推荐 - 移动端优先 */
.container {
  padding: var(--space-4);
}

@media (min-width: 768px) {
  .container {
    padding: var(--space-8);
  }
}
```

### 4. 可访问性考虑
```css
/* ✅ 包含焦点状态 */
.btn:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
}

/* ✅ 触摸友好的尺寸 */
.btn {
  min-height: 44px;
  min-width: 44px;
}
```

## 🔄 迁移步骤

### 1. 更新导入
```css
/* 旧方式 */
@import './base.css';
@import './theme.css';

/* 新方式 */
@import './design-system.css';
@import './components.css';
```

### 2. 替换自定义样式
查找并替换硬编码的值为设计令牌。

### 3. 使用标准组件类
将自定义组件样式替换为标准组件类。

### 4. 测试响应式行为
确保在各种屏幕尺寸下的显示效果。

## ⚠️ 注意事项

1. **向后兼容**: `theme.css` 保留了旧变量的映射，但建议逐步迁移到新系统
2. **性能**: 新系统优化了CSS大小和加载性能
3. **维护性**: 统一的设计系统使维护更加容易

## 🆘 常见问题

### Q: 我的自定义颜色不见了？
A: 检查是否有对应的设计令牌，或者在 `design-system.css` 中添加项目特定的颜色。

### Q: 按钮样式看起来不同了？
A: 新的按钮系统更加标准化，请使用 `.btn` 配合修饰符类。

### Q: 响应式断点改变了？
A: 新系统使用标准断点 (640px, 768px, 1024px, 1280px, 1536px)。

## 📚 更多资源

- [Design System 完整文档](./design-system.css)
- [组件样式参考](./components.css)
- [实用工具类清单](./design-system.css#L200)

---

有问题请查看代码注释或联系开发团队！ 