<template>
  <div class="loading-container" :class="{ 'full-screen': fullScreen }">
    <div class="loading-content">
      <div class="loading-card">
        <div class="loading-icon">
          <div class="loading-dots">
            <span class="dot"></span>
            <span class="dot"></span>
            <span class="dot"></span>
          </div>
        </div>
        <span class="loading-text">{{ text }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
interface Props {
  text?: string
  fullScreen?: boolean
}

withDefaults(defineProps<Props>(), {
  text: '加载中...',
  fullScreen: false
})
</script>

<style scoped>
.loading-container {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 3rem;
  position: relative;
}

.loading-container.full-screen {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(255, 255, 255, 0.95);
  z-index: 9999;
  backdrop-filter: blur(8px);
}

.loading-content {
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
}

.loading-card {
  background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
  border-radius: 20px;
  padding: 2.5rem 3rem;
  box-shadow: 
    0 20px 25px -5px rgba(0, 0, 0, 0.1),
    0 10px 10px -5px rgba(0, 0, 0, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(10px);
  text-align: center;
  position: relative;
  overflow: hidden;
  min-width: 200px;
}

.loading-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(
    90deg,
    transparent,
    rgba(59, 130, 246, 0.1),
    transparent
  );
  animation: shimmer 2s infinite;
}

.loading-icon {
  margin-bottom: 1.5rem;
  display: flex;
  justify-content: center;
  align-items: center;
}

.loading-dots {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: linear-gradient(135deg, #3b82f6, #1d4ed8);
  opacity: 0.7;
  animation: pulse 1.5s ease-in-out infinite;
}

.dot:nth-child(1) {
  animation-delay: 0s;
}

.dot:nth-child(2) {
  animation-delay: 0.2s;
}

.dot:nth-child(3) {
  animation-delay: 0.4s;
}

.loading-text {
  color: #374151;
  font-size: 1.1rem;
  font-weight: 600;
  letter-spacing: 0.025em;
  background: linear-gradient(135deg, #374151, #6b7280);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

@keyframes shimmer {
  0% {
    left: -100%;
  }
  100% {
    left: 100%;
  }
}

@keyframes pulse {
  0%, 100% {
    transform: scale(0.8);
    opacity: 0.5;
  }
  50% {
    transform: scale(1.2);
    opacity: 1;
  }
}

/* 暗色主题支持 */
@media (prefers-color-scheme: dark) {
  .loading-card {
    background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
    border-color: rgba(255, 255, 255, 0.1);
    box-shadow: 
      0 20px 25px -5px rgba(0, 0, 0, 0.4),
      0 10px 10px -5px rgba(0, 0, 0, 0.2);
  }
  
  .loading-container.full-screen {
    background: rgba(15, 23, 42, 0.95);
  }
  
  .loading-card::before {
    background: linear-gradient(
      90deg,
      transparent,
      rgba(59, 130, 246, 0.2),
      transparent
    );
  }
  
  .loading-text {
    color: #e2e8f0;
    background: linear-gradient(135deg, #e2e8f0, #cbd5e1);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }
  
  .dot {
    background: linear-gradient(135deg, #60a5fa, #3b82f6);
  }
}

/* 响应式设计 */
@media (max-width: 768px) {
  .loading-container {
    padding: 2rem;
  }
  
  .loading-card {
    padding: 2rem 2.5rem;
    min-width: 180px;
  }
  
  .loading-text {
    font-size: 1rem;
  }
  
  .dot {
    width: 6px;
    height: 6px;
  }
}

@media (max-width: 480px) {
  .loading-container {
    padding: 1.5rem;
  }
  
  .loading-card {
    padding: 1.5rem 2rem;
    min-width: 160px;
    border-radius: 16px;
  }
  
  .loading-icon {
    margin-bottom: 1rem;
  }
  
  .loading-text {
    font-size: 0.95rem;
  }
}

/* 减少动画偏好设置 */
@media (prefers-reduced-motion: reduce) {
  .loading-card::before {
    animation: none;
  }
  
  .dot {
    animation: none;
    opacity: 0.8;
  }
}

/* 高分辨率屏幕优化 */
@media (-webkit-min-device-pixel-ratio: 2), (min-resolution: 192dpi) {
  .loading-card {
    border-width: 0.5px;
  }
}
</style>
