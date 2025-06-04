<template>
  <div class="stats-overview" v-if="stats">
    <div class="stat-card">
      <div class="stat-icon">👥</div>
      <div class="stat-content">
        <div class="stat-number">{{ stats.users.total }}</div>
        <div class="stat-label">总用户数</div>
        <div class="stat-detail">活跃: {{ stats.users.active }}</div>
      </div>
    </div>

    <div class="stat-card">
      <div class="stat-icon">🎫</div>
      <div class="stat-content">
        <div class="stat-number">{{ stats.invitations.unused }}</div>
        <div class="stat-label">可用邀请码</div>
        <div class="stat-detail">已用: {{ stats.invitations.used }} / 总计: {{ stats.invitations.total }}</div>
      </div>
    </div>

    <div class="stat-card">
      <div class="stat-icon">
        <IconSubject :size="32" color="#3b82f6" />
      </div>
      <div class="stat-content">
        <div class="stat-number">{{ stats.subjects.total_questions }}</div>
        <div class="stat-label">题目总数</div>
        <div class="stat-detail">{{ stats.subjects.total_files }}个文件</div>
      </div>
    </div>

    <div class="stat-card">
      <div class="stat-icon">🛡️</div>
      <div class="stat-content">
        <div class="stat-number">{{ stats.users.admins }}</div>
        <div class="stat-label">管理员</div>
        <div class="stat-detail">VIP: {{ stats.users.vips }}</div>
      </div>
    </div>
  </div>
</template>

<script lang="ts" setup>
import IconSubject from '@/components/icons/IconSubject.vue'
import type { AdminStats } from '@/types'

interface Props {
  stats: AdminStats | null
}

defineProps<Props>()
</script>

<style scoped>
.stats-overview {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1.5rem;
  margin-bottom: 3rem;
}

.stat-card {
  background: white;
  border-radius: 16px;
  padding: 2rem;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
  border: 2px solid transparent;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  gap: 1.5rem;
}

.stat-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1);
  border-color: #e2e8f0;
}

.stat-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 2rem;
  margin-bottom: 0.75rem;
  filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.1));
}

.stat-content {
  flex: 1;
}

.stat-number {
  font-size: 2rem;
  font-weight: 700;
  color: #1e293b;
  margin-bottom: 0.5rem;
}

.stat-label {
  font-size: 1rem;
  color: #64748b;
  font-weight: 500;
  margin-bottom: 0.25rem;
}

.stat-detail {
  font-size: 0.9rem;
  color: #94a3b8;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .stats-overview {
    grid-template-columns: 1fr;
    gap: 1rem;
  }

  .stat-card {
    padding: 1.5rem;
    flex-direction: column;
    text-align: center;
  }

  .stat-icon {
    margin-bottom: 0.5rem;
  }
}
</style> 