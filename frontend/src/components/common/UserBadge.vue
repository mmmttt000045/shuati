<template>
  <div class="user-badge" :class="badgeClass" :title="modelName">
    <!-- 普通用户图标 -->
    <svg v-if="props.model === USER_MODEL.NORMAL" class="user-badge-icon" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
      <circle cx="12" cy="8" r="4" fill="#64748b"/>
      <path d="M12 14c-6 0-8 4-8 6v2h16v-2c0-2-2-6-8-6z" fill="#64748b"/>
    </svg>
    
    <!-- VIP用户图标 -->
    <svg v-else-if="props.model === USER_MODEL.VIP" class="user-badge-icon" viewBox="0 0 1024 1024" version="1.1" xmlns="http://www.w3.org/2000/svg">
      <path d="M0 0h1024v1024H0V0z" fill="#202425" opacity=".01"></path>
      <path d="M743.867733 102.4a17.066667 17.066667 0 0 1 12.049067 4.983467l256.750933 256.750933a17.066667 17.066667 0 0 1 0.7168 23.3472L524.8 941.226667a17.066667 17.066667 0 0 1-25.6 0L10.615467 387.4816a17.066667 17.066667 0 0 1 0.7168-23.3472l256.750933-256.750933A17.066667 17.066667 0 0 1 280.132267 102.4h463.735466z" fill="#11AA66"></path>
      <path d="M499.165867 360.789333L278.016 108.066133A3.413333 3.413333 0 0 1 280.576 102.4h462.848a3.413333 3.413333 0 0 1 2.56 5.666133l-221.149867 252.7232a17.066667 17.066667 0 0 1-25.668266 0z" fill="#FFAA44"></path>
      <path d="M250.606933 383.8976a34.133333 34.133333 0 0 1 48.128 3.242667L512 630.852267l213.230933-243.712a34.133333 34.133333 0 0 1 51.4048 44.919466l-238.933333 273.066667a34.133333 34.133333 0 0 1-51.4048 0l-238.933333-273.066667a34.133333 34.133333 0 0 1 3.242666-48.128z" fill="#FFFFFF"></path>
    </svg>
    
    <!-- 管理员图标 -->
    <svg v-else-if="props.model === USER_MODEL.ROOT" class="user-badge-icon" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
      <path d="M12 2l-8 4v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V6l-8-4z" fill="#DC2626" stroke="#8B0000" stroke-width="0.5"/>
      <path d="M12 8l1 2h2l-1.5 1.5 0.5 2L12 12l-1.5 1.5 0.5-2L9 10h2l1-2z" fill="#FFD700"/>
      <circle cx="12" cy="6" r="0.5" fill="#FFD700"/>
    </svg>
    
    <span class="user-badge-text">{{ modelName }}</span>
  </div>
</template>

<script lang="ts" setup>
import { computed } from 'vue'
import { USER_MODEL, USER_MODEL_NAMES, type UserModel } from '@/types'

interface Props {
  model: UserModel
}

const props = defineProps<Props>()


const modelName = computed(() => {
  return USER_MODEL_NAMES[props.model] || '未知用户'
})

const badgeClass = computed(() => {
  switch (props.model) {
    case USER_MODEL.VIP:
      return 'user-badge-vip'
    case USER_MODEL.ROOT:
      return 'user-badge-root'
    default:
      return 'user-badge-normal'
  }
})
</script>

<style scoped>
.user-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.875rem;
  border-radius: 20px;
  font-size: 0.8rem;
  font-weight: 600;
  border: 1px solid transparent;
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  letter-spacing: 0.025em;
}

.user-badge-icon {
  width: 1.25rem;
  height: 1.25rem;
  flex-shrink: 0;
}

.user-badge-text {
  white-space: nowrap;
}

/* 普通用户样式 */
.user-badge-normal {
  background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
  color: #64748b;
  border-color: #e2e8f0;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

/* VIP用户样式 */
.user-badge-vip {
  background: linear-gradient(135deg, #fff7ed 0%, #fed7aa 50%, #fdba74 100%);
  color: #9a3412;
  border-color: #ea580c;
  box-shadow: 
    0 2px 8px rgba(234, 88, 12, 0.15),
    inset 0 1px 0 rgba(255, 255, 255, 0.3);
}

/* 管理员样式 */
.user-badge-root {
  background: linear-gradient(135deg, #fef2f2 0%, #fecaca 50%, #fca5a5 100%);
  color: #7f1d1d;
  border-color: #dc2626;
  box-shadow: 
    0 2px 8px rgba(220, 38, 38, 0.15),
    inset 0 1px 0 rgba(255, 255, 255, 0.3);
}

/* 移动端优化 */
@media (max-width: 768px) {
  .user-badge {
    font-size: 0.7rem;
    padding: 0.375rem 0.625rem;
    gap: 0.375rem;
    border-radius: 16px;
  }
  
  .user-badge-icon {
    width: 1rem;
    height: 1rem;
  }
  
  .user-badge-text {
    letter-spacing: 0;
  }
}

@media (max-width: 640px) {
  .user-badge {
    font-size: 0.65rem;
    padding: 0.25rem 0.5rem;
    gap: 0.25rem;
    border-radius: 14px;
  }
  
  .user-badge-icon {
    width: 0.875rem;
    height: 0.875rem;
  }
}
</style> 