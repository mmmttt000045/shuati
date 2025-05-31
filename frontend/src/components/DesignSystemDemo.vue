<template>
  <div class="design-demo">
    <div class="container">
      <h1 class="text-3xl font-bold text-center mb-8">设计系统演示</h1>
      
      <!-- 颜色系统 -->
      <section class="mb-12">
        <h2 class="text-2xl font-semibold mb-6">颜色系统</h2>
        <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <div class="color-swatch bg-primary text-white">Primary</div>
          <div class="color-swatch" style="background: var(--color-success); color: white;">Success</div>
          <div class="color-swatch" style="background: var(--color-warning); color: white;">Warning</div>
          <div class="color-swatch" style="background: var(--color-error); color: white;">Error</div>
        </div>
      </section>

      <!-- 按钮组件 -->
      <section class="mb-12">
        <h2 class="text-2xl font-semibold mb-6">按钮组件</h2>
        <div class="flex flex-wrap gap-4 mb-6">
          <button class="btn btn-primary">主要按钮</button>
          <button class="btn btn-secondary">次要按钮</button>
          <button class="btn btn-outline">轮廓按钮</button>
          <button class="btn btn-success">成功按钮</button>
          <button class="btn btn-warning">警告按钮</button>
          <button class="btn btn-error">错误按钮</button>
        </div>
        
        <div class="flex flex-wrap gap-4 mb-6">
          <button class="btn btn-primary btn-sm">小按钮</button>
          <button class="btn btn-primary">默认按钮</button>
          <button class="btn btn-primary btn-lg">大按钮</button>
        </div>
        
        <button class="btn btn-primary btn-full mb-4">全宽按钮</button>
        <button class="btn btn-primary" disabled>禁用按钮</button>
      </section>

      <!-- 表单组件 -->
      <section class="mb-12">
        <h2 class="text-2xl font-semibold mb-6">表单组件</h2>
        <div class="max-w-md">
          <div class="form-group">
            <label class="form-label">用户名</label>
            <input type="text" class="form-control" placeholder="请输入用户名" />
          </div>
          
          <div class="form-group">
            <label class="form-label">密码</label>
            <input type="password" class="form-control" placeholder="请输入密码" />
            <div class="form-help">密码至少6个字符</div>
          </div>
          
          <div class="form-group">
            <label class="form-label">错误示例</label>
            <input type="text" class="form-control form-control-error" placeholder="有错误的输入" />
            <div class="form-error">请输入有效的内容</div>
          </div>
        </div>
      </section>

      <!-- 卡片组件 -->
      <section class="mb-12">
        <h2 class="text-2xl font-semibold mb-6">卡片组件</h2>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div class="card">
            <div class="card-header">
              <h3 class="font-semibold">基础卡片</h3>
            </div>
            <div class="card-body">
              <p>这是一个基础卡片的内容区域。</p>
            </div>
            <div class="card-footer">
              <button class="btn btn-primary btn-sm">操作</button>
            </div>
          </div>
          
          <div class="card card-hover">
            <div class="card-body">
              <h3 class="font-semibold mb-2">悬停卡片</h3>
              <p>鼠标悬停时会有动画效果。</p>
            </div>
          </div>
          
          <div class="card">
            <div class="card-body">
              <h3 class="font-semibold mb-2">简单卡片</h3>
              <p>只包含内容的简单卡片。</p>
            </div>
          </div>
        </div>
      </section>

      <!-- 消息组件 -->
      <section class="mb-12">
        <h2 class="text-2xl font-semibold mb-6">消息组件</h2>
        <div class="space-y-4">
          <div class="message message-success">
            <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
              <path d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"/>
            </svg>
            操作成功完成！
          </div>
          
          <div class="message message-warning">
            <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
              <path d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"/>
            </svg>
            请注意这个警告信息。
          </div>
          
          <div class="message message-error">
            <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
              <path d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"/>
            </svg>
            发生了一个错误！
          </div>
          
          <div class="message message-info">
            <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
              <path d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"/>
            </svg>
            这是一条信息提示。
          </div>
        </div>
      </section>

      <!-- 徽章组件 -->
      <section class="mb-12">
        <h2 class="text-2xl font-semibold mb-6">徽章组件</h2>
        <div class="flex flex-wrap gap-2">
          <span class="badge badge-primary">Primary</span>
          <span class="badge badge-success">Success</span>
          <span class="badge badge-warning">Warning</span>
          <span class="badge badge-error">Error</span>
          <span class="badge badge-neutral">Neutral</span>
        </div>
      </section>

      <!-- 进度条组件 -->
      <section class="mb-12">
        <h2 class="text-2xl font-semibold mb-6">进度条组件</h2>
        <div class="space-y-4">
          <div>
            <div class="text-sm text-secondary mb-2">默认进度条 (75%)</div>
            <div class="progress">
              <div class="progress-bar" style="width: 75%"></div>
            </div>
          </div>
          
          <div>
            <div class="text-sm text-secondary mb-2">大进度条 (45%)</div>
            <div class="progress progress-lg">
              <div class="progress-bar" style="width: 45%"></div>
            </div>
          </div>
          
          <div>
            <div class="text-sm text-secondary mb-2">小进度条 (90%)</div>
            <div class="progress progress-sm">
              <div class="progress-bar" style="width: 90%"></div>
            </div>
          </div>
        </div>
      </section>

      <!-- 工具类演示 -->
      <section class="mb-12">
        <h2 class="text-2xl font-semibold mb-6">工具类演示</h2>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-8">
          <div>
            <h3 class="text-lg font-semibold mb-4">间距</h3>
            <div class="space-y-2">
              <div class="p-2 bg-secondary rounded">p-2</div>
              <div class="p-4 bg-secondary rounded">p-4</div>
              <div class="p-6 bg-secondary rounded">p-6</div>
            </div>
          </div>
          
          <div>
            <h3 class="text-lg font-semibold mb-4">文本</h3>
            <div class="space-y-2">
              <div class="text-xs">超小文本 (text-xs)</div>
              <div class="text-sm">小文本 (text-sm)</div>
              <div class="text-base">基础文本 (text-base)</div>
              <div class="text-lg">大文本 (text-lg)</div>
              <div class="text-xl">超大文本 (text-xl)</div>
            </div>
          </div>
        </div>
      </section>

      <!-- 响应式网格 -->
      <section class="mb-12">
        <h2 class="text-2xl font-semibold mb-6">响应式网格</h2>
        <div class="grid-auto-fit">
          <div class="card">
            <div class="card-body">
              <h3 class="font-semibold mb-2">网格项目 1</h3>
              <p>这是一个自适应网格项目。</p>
            </div>
          </div>
          <div class="card">
            <div class="card-body">
              <h3 class="font-semibold mb-2">网格项目 2</h3>
              <p>响应式设计会自动调整列数。</p>
            </div>
          </div>
          <div class="card">
            <div class="card-body">
              <h3 class="font-semibold mb-2">网格项目 3</h3>
              <p>在不同屏幕尺寸下显示不同的列数。</p>
            </div>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.design-demo {
  min-height: 100vh;
  background-color: var(--bg-secondary);
  padding: var(--space-8) 0;
}

.color-swatch {
  padding: var(--space-4);
  border-radius: var(--radius-lg);
  text-align: center;
  font-weight: var(--font-medium);
  min-height: 80px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.space-y-4 > * + * {
  margin-top: var(--space-4);
}

.space-y-2 > * + * {
  margin-top: var(--space-2);
}

/* 演示网格样式 */
.grid {
  display: grid;
}

.grid-cols-1 {
  grid-template-columns: repeat(1, minmax(0, 1fr));
}

.grid-cols-2 {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

@media (min-width: 768px) {
  .md\:grid-cols-3 {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
  
  .md\:grid-cols-4 {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }
  
  .md\:grid-cols-2 {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

.w-5 {
  width: 1.25rem;
}

.h-5 {
  height: 1.25rem;
}
</style> 