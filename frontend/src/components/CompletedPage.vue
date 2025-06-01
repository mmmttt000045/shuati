<template>
  <div class="page-layout">
    <NavigationBar />
    <div class="container">
      <h1 class="page-title">练习完成</h1>

      <div v-if="messages.length > 0" class="messages">
        <div
          v-for="(message, index) in messages"
          :key="index"
          :class="['message', message.category]"
        >
          {{ message.text }}
        </div>
      </div>

      <Loading v-if="loading" text="正在获取练习总结..." />

      <div v-else-if="summary" class="summary-card">
        <h2 class="summary-title">练习总结</h2>
        <div class="summary-content">
          <p class="file-name">题库：{{ summary.completed_filename }}</p>
          <div class="stats">
            <div class="stat-item">
              <span class="stat-label">总题数</span>
              <span class="stat-value">{{ summary.initial_total }}</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">首次答对</span>
              <span class="stat-value">{{ summary.correct_first_try }}</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">正确率</span>
              <span class="stat-value">{{ summary.score_percent.toFixed(1) }}%</span>
            </div>
          </div>
        </div>
        <div class="actions">
          <button class="btn-back" @click="goToIndex">返回首页</button>
        </div>
      </div>

      <div v-else class="empty-state">
        暂无练习总结信息
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { apiService } from '@/services/api';
import type { CompletedSummary, FlashMessage } from '@/types';
import NavigationBar from './NavigationBar.vue';
import Loading from '@/components/Loading.vue';

const router = useRouter();
const summary = ref<CompletedSummary | null>(null);
const messages = ref<FlashMessage[]>([]);
const loading = ref(false);

onMounted(async () => {
  loading.value = true;
  try {
    const response = await apiService.getCompletedSummary();
    if (response.success) {
      if (response.summary) {
        summary.value = response.summary;
      }
      if (response.flash_messages) {
        messages.value = response.flash_messages;
      }
    } else {
      messages.value.push({
        category: 'error',
        text: response.message || '获取完成信息失败'
      });
    }
  } catch (error) {
    messages.value.push({
      category: 'error',
      text: error instanceof Error ? error.message : '获取完成信息时发生错误'
    });
  } finally {
    loading.value = false;
  }
});

const goToIndex = () => {
  router.push('/');
};
</script>

<style scoped>
.page-layout {
  min-height: 100vh;
  background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
}

.container {
  max-width: 800px;
  margin: 0 auto;
  padding: 2rem;
}

.page-title {
  text-align: center;
  margin-bottom: 2rem;
  color: #2c3e50;
}

.messages {
  margin-bottom: 2rem;
}

.message {
  padding: 1rem;
  margin-bottom: 1rem;
  border-radius: 4px;
}

.message.error {
  background-color: #fef2f2;
  color: #dc2626;
  border: 1px solid #fecaca;
}

.message.info {
  background-color: #f0f9ff;
  color: #0369a1;
  border: 1px solid #bae6fd;
}

.summary-card {
  background-color: #ffffff;
  border-radius: 8px;
  padding: 2rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.summary-title {
  margin: 0 0 1.5rem;
  padding-bottom: 0.5rem;
  border-bottom: 2px solid #e5e7eb;
  color: #1f2937;
}

.summary-content {
  margin-bottom: 2rem;
}

.file-name {
  font-size: 1.125rem;
  color: #4b5563;
  margin-bottom: 1.5rem;
}

.stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 1.5rem;
}

.stat-item {
  text-align: center;
  padding: 1rem;
  background-color: #f3f4f6;
  border-radius: 6px;
}

.stat-label {
  display: block;
  font-size: 0.875rem;
  color: #6b7280;
  margin-bottom: 0.5rem;
}

.stat-value {
  display: block;
  font-size: 1.5rem;
  font-weight: 600;
  color: #1f2937;
}

.actions {
  text-align: center;
  margin-top: 2rem;
}

.btn-back {
  padding: 0.75rem 2rem;
  background-color: #3b82f6;
  color: #ffffff;
  border: none;
  border-radius: 4px;
  font-size: 1rem;
  font-weight: 500;
  cursor: pointer;
  transition: background-color 0.2s;
}

.btn-back:hover {
  background-color: #2563eb;
}

.empty-state {
  text-align: center;
  padding: 2rem;
  color: #6b7280;
}
</style> 