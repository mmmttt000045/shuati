<template>
  <div class="not-found-container">
    <div class="not-found-content">
      <!-- 404 图标 -->
      <div class="error-icon">
        <svg viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg">
          <circle cx="100" cy="80" r="8" fill="#64748b" opacity="0.6">
            <animate attributeName="opacity" dur="1.5s" values="0.6;1;0.6" repeatCount="indefinite"/>
          </circle>
          <circle cx="100" cy="120" r="8" fill="#64748b" opacity="0.8">
            <animate attributeName="opacity" dur="1.5s" values="0.8;0.4;0.8" repeatCount="indefinite" begin="0.5s"/>
          </circle>
          <path d="M60 60 L140 60 L140 140 L60 140 Z" fill="none" stroke="#64748b" stroke-width="3" opacity="0.3"/>
          <path d="M70 70 L130 130 M130 70 L70 130" stroke="#ef4444" stroke-width="2" stroke-linecap="round"/>
        </svg>
      </div>

      <!-- 404 标题 -->
      <h1 class="error-title">404</h1>
      <h2 class="error-subtitle">页面未找到</h2>
      
      <!-- 描述信息 -->
      <p class="error-description">
        抱歉，您访问的页面不存在或已被移动。
        <br>
        请检查网址是否正确，或返回到主页面。
      </p>

      <!-- 操作按钮 -->
      <div class="action-buttons">
        <button 
          @click="goToLogin" 
          class="btn btn-primary"
        >
          <svg class="btn-icon" viewBox="0 0 20 20" fill="currentColor">
            <path fill-rule="evenodd" d="M3 3a1 1 0 011 1v12a1 1 0 11-2 0V4a1 1 0 011-1zm7.707 3.293a1 1 0 010 1.414L9.414 9H17a1 1 0 110 2H9.414l1.293 1.293a1 1 0 01-1.414 1.414l-3-3a1 1 0 010-1.414l3-3a1 1 0 011.414 0z" clip-rule="evenodd" />
          </svg>
          前往登录
        </button>
        
        <button 
          @click="goBack" 
          class="btn btn-secondary"
        >
          <svg class="btn-icon" viewBox="0 0 20 20" fill="currentColor">
            <path fill-rule="evenodd" d="M9.707 16.707a1 1 0 01-1.414 0l-6-6a1 1 0 010-1.414l6-6a1 1 0 011.414 1.414L5.414 9H17a1 1 0 110 2H5.414l4.293 4.293a1 1 0 010 1.414z" clip-rule="evenodd" />
          </svg>
          返回上页
        </button>
      </div>

      <!-- 额外链接 -->
      <div class="extra-links">
        <router-link to="/" class="link">回到首页</router-link>
        <span class="link-separator">|</span>
        <router-link to="/register" class="link">注册账号</router-link>
      </div>
    </div>

    <!-- 背景装饰 -->
    <div class="background-decoration">
      <div class="floating-shape shape-1"></div>
      <div class="floating-shape shape-2"></div>
      <div class="floating-shape shape-3"></div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router';

const router = useRouter();

const goToLogin = () => {
  router.push('/login');
};

const goBack = () => {
  if (window.history.length > 1) {
    router.go(-1);
  } else {
    router.push('/');
  }
};
</script>

<style scoped>
/* 确保全屏显示，移除默认边距 */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

.not-found-container {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  width: 100vw;
  height: 100vh;
  min-height: 100vh;
  min-height: 100dvh; /* 动态视口高度 */
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 2rem;
  overflow: hidden;
  box-sizing: border-box;
  z-index: 9999; /* 确保在最上层 */
  /* 防止移动端滚动 */
  -webkit-overflow-scrolling: touch;
  /* 防止选择和长按 */
  -webkit-user-select: none;
  -moz-user-select: none;
  -ms-user-select: none;
  user-select: none;
}

.not-found-content {
  text-align: center;
  max-width: 500px;
  z-index: 10;
  position: relative;
}

.error-icon {
  width: 120px;
  height: 120px;
  margin: 0 auto 2rem;
}

.error-icon svg {
  width: 100%;
  height: 100%;
  filter: drop-shadow(0 4px 6px rgba(0, 0, 0, 0.1));
}

.error-title {
  font-size: 6rem;
  font-weight: 900;
  color: white;
  margin: 0 0 0.5rem;
  text-shadow: 0 4px 8px rgba(0, 0, 0, 0.3);
  letter-spacing: -0.02em;
}

.error-subtitle {
  font-size: 2rem;
  font-weight: 600;
  color: white;
  margin: 0 0 1.5rem;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
}

.error-description {
  font-size: 1.125rem;
  color: rgba(255, 255, 255, 0.9);
  line-height: 1.6;
  margin: 0 0 3rem;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
}

.action-buttons {
  display: flex;
  gap: 1rem;
  justify-content: center;
  margin-bottom: 2rem;
  flex-wrap: wrap;
}

.btn {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.875rem 1.5rem;
  border: none;
  border-radius: 0.5rem;
  font-weight: 600;
  font-size: 1rem;
  cursor: pointer;
  transition: all 0.2s ease;
  text-decoration: none;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.btn-icon {
  width: 1.25rem;
  height: 1.25rem;
}

.btn-primary {
  background: #3b82f6;
  color: white;
}

.btn-primary:hover {
  background: #2563eb;
  transform: translateY(-1px);
  box-shadow: 0 6px 12px rgba(0, 0, 0, 0.15);
}

.btn-secondary {
  background: rgba(255, 255, 255, 0.2);
  color: white;
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.3);
}

.btn-secondary:hover {
  background: rgba(255, 255, 255, 0.3);
  transform: translateY(-1px);
  box-shadow: 0 6px 12px rgba(0, 0, 0, 0.15);
}

.extra-links {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 1rem;
}

.link {
  color: rgba(255, 255, 255, 0.8);
  text-decoration: none;
  font-weight: 500;
  transition: color 0.2s ease;
}

.link:hover {
  color: white;
  text-decoration: underline;
}

.link-separator {
  color: rgba(255, 255, 255, 0.5);
}

.background-decoration {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.floating-shape {
  position: absolute;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.1);
  animation: float 6s ease-in-out infinite;
}

.shape-1 {
  width: 200px;
  height: 200px;
  top: 10%;
  left: 10%;
  animation-delay: 0s;
}

.shape-2 {
  width: 150px;
  height: 150px;
  top: 60%;
  right: 10%;
  animation-delay: 2s;
}

.shape-3 {
  width: 100px;
  height: 100px;
  bottom: 20%;
  left: 20%;
  animation-delay: 4s;
}

@keyframes float {
  0%, 100% {
    transform: translateY(0px) rotate(0deg);
  }
  50% {
    transform: translateY(-20px) rotate(180deg);
  }
}

@media (max-width: 640px) {
  .not-found-container {
    padding: 1rem;
    width: 100vw;
    height: 100vh;
    min-height: 100vh;
    min-height: 100dvh; /* 支持动态视口高度 */
    /* 确保在移动设备上完全撑满 */
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
  }
  
  .error-title {
    font-size: 4rem;
  }
  
  .error-subtitle {
    font-size: 1.5rem;
  }
  
  .error-description {
    font-size: 1rem;
    margin: 0 0 2rem;
  }
  
  .action-buttons {
    flex-direction: column;
    align-items: center;
  }
  
  .btn {
    width: 100%;
    max-width: 200px;
  }
  
  .extra-links {
    flex-direction: column;
    gap: 0.5rem;
  }
  
  .link-separator {
    display: none;
  }
}

/* 超小屏幕优化 */
@media (max-width: 480px) {
  .not-found-container {
    padding: 0.75rem;
  }
  
  .error-title {
    font-size: 3rem;
  }
  
  .error-subtitle {
    font-size: 1.25rem;
  }
  
  .error-description {
    font-size: 0.9rem;
  }
  
  .error-icon {
    width: 80px;
    height: 80px;
    margin: 0 auto 1.5rem;
  }
}
</style> 