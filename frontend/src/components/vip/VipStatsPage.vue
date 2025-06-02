<template>
  <div class="vip-stats-content">
    <Loading v-if="loading" text="正在加载学习统计..." :fullScreen="true" />
    
    <div v-else class="container">
      <h1 class="page-title">学习统计</h1>
      
      <div class="stats-grid">
        <div class="stat-card">
          <div class="stat-icon">📊</div>
          <div class="stat-content">
            <h3>总练习次数</h3>
            <p class="stat-value">{{ stats.totalPractices }}</p>
          </div>
        </div>
        
        <div class="stat-card">
          <div class="stat-icon">✅</div>
          <div class="stat-content">
            <h3>平均正确率</h3>
            <p class="stat-value">{{ stats.averageAccuracy }}%</p>
          </div>
        </div>
        
        <div class="stat-card">
          <div class="stat-icon">⏱️</div>
          <div class="stat-content">
            <h3>总学习时长</h3>
            <p class="stat-value">{{ stats.totalTime }}小时</p>
          </div>
        </div>
        
        <div class="stat-card">
          <div class="stat-icon">🎯</div>
          <div class="stat-content">
            <h3>完成题库数</h3>
            <p class="stat-value">{{ stats.completedSubjects }}</p>
          </div>
        </div>
      </div>
      
      <div class="chart-section">
        <h2>学习趋势</h2>
        <div class="chart-placeholder">
          <p>📈 学习趋势图表</p>
          <p class="chart-note">此功能正在开发中...</p>
        </div>
      </div>
      
      <div class="recent-activity">
        <h2>最近活动</h2>
        <div class="activity-list">
          <div v-for="activity in recentActivities" :key="activity.id" class="activity-item">
            <div class="activity-icon">
              <IconSubject v-if="activity.icon === 'subject'" :size="24" color="#3b82f6" />
              <span v-else>{{ activity.icon }}</span>
            </div>
            <div class="activity-content">
              <h4>{{ activity.title }}</h4>
              <p>{{ activity.description }}</p>
              <span class="activity-time">{{ activity.time }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import Loading from '@/components/common/Loading.vue'
import IconSubject from '@/components/icons/IconSubject.vue'

// 添加loading状态
const loading = ref(true)

// 模拟数据，实际应该从API获取
const stats = ref({
  totalPractices: 156,
  averageAccuracy: 87.5,
  totalTime: 42.3,
  completedSubjects: 12
})

const recentActivities = ref([
  {
    id: 1,
    icon: 'subject',
    title: '完成数学练习',
    description: '高等数学第三章，正确率 92%',
    time: '2小时前'
  },
  {
    id: 2,
    icon: '⭐',
    title: '收藏错题',
    description: '添加了 5 道错题到收藏夹',
    time: '1天前'
  },
  {
    id: 3,
    icon: '📄',
    title: '导出错题集',
    description: '导出了物理错题集 PDF',
    time: '3天前'
  }
])

onMounted(async () => {
  // 模拟数据加载
  loading.value = true
  try {
    // 模拟API调用延迟
    await new Promise(resolve => setTimeout(resolve, 1500))
    // 这里可以调用API获取真实的统计数据
    console.log('VIP Stats page loaded')
  } catch (error) {
    console.error('加载统计数据失败:', error)
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.vip-stats-content {
  width: 100%;
  min-height: calc(100vh - 64px);
  background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
  padding: 2rem 0;
  overflow-y: auto;
}

.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 2rem;
}

.page-title {
  text-align: center;
  margin-bottom: 2rem;
  color: #2c3e50;
  font-size: 2rem;
  font-weight: 600;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1.5rem;
  margin-bottom: 3rem;
}

.stat-card {
  background: white;
  border-radius: 12px;
  padding: 1.5rem;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  display: flex;
  align-items: center;
  gap: 1rem;
  transition: transform 0.2s, box-shadow 0.2s;
}

.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 15px rgba(0, 0, 0, 0.15);
}

.stat-icon {
  font-size: 2.5rem;
  width: 60px;
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 50%;
  color: white;
}

.stat-content h3 {
  margin: 0 0 0.5rem 0;
  color: #4a5568;
  font-size: 0.9rem;
  font-weight: 500;
}

.stat-value {
  margin: 0;
  font-size: 1.8rem;
  font-weight: 700;
  color: #2d3748;
}

.chart-section, .recent-activity {
  background: white;
  border-radius: 12px;
  padding: 2rem;
  margin-bottom: 2rem;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.chart-section h2, .recent-activity h2 {
  margin: 0 0 1.5rem 0;
  color: #2d3748;
  font-size: 1.5rem;
  font-weight: 600;
}

.chart-placeholder {
  text-align: center;
  padding: 3rem;
  background: #f7fafc;
  border-radius: 8px;
  border: 2px dashed #e2e8f0;
}

.chart-placeholder p {
  margin: 0.5rem 0;
  font-size: 1.2rem;
}

.chart-note {
  color: #718096;
  font-size: 0.9rem !important;
}

.activity-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.activity-item {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem;
  background: #f7fafc;
  border-radius: 8px;
  transition: background-color 0.2s;
}

.activity-item:hover {
  background: #edf2f7;
}

.activity-icon {
  font-size: 1.5rem;
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: white;
  border-radius: 50%;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.activity-content {
  flex: 1;
}

.activity-content h4 {
  margin: 0 0 0.25rem 0;
  color: #2d3748;
  font-size: 1rem;
  font-weight: 600;
}

.activity-content p {
  margin: 0 0 0.25rem 0;
  color: #4a5568;
  font-size: 0.9rem;
}

.activity-time {
  color: #718096;
  font-size: 0.8rem;
}

@media (max-width: 768px) {
  .container {
    padding: 1rem;
  }
  
  .stats-grid {
    grid-template-columns: 1fr;
  }
  
  .stat-card {
    padding: 1rem;
  }
  
  .chart-section, .recent-activity {
    padding: 1.5rem;
  }
}
</style> 