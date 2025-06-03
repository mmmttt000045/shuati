<template>
  <div class="enhanced-usage-stats-page">
    <div class="page-container">
      <!-- 页面标题 -->
      <div class="page-header">
        <h1 class="page-title">
          <IconStats :size="48" color="#3b82f6" class="title-icon" />
          智能使用统计
        </h1>
        <p class="page-description">深度分析平台使用情况，发现热门趋势与用户偏好</p>
      </div>

      <!-- 加载状态 -->
      <div v-if="loading" class="loading-section">
        <v-progress-circular indeterminate color="primary" size="64"></v-progress-circular>
        <div class="loading-text">加载统计数据中...</div>
      </div>

      <!-- 统计概览卡片 -->
      <div v-if="!loading" class="stats-overview">
        <!-- 如果没有summary数据，显示空状态 -->
        <div v-if="!summary" class="empty-state" style="text-align: center; padding: 2rem; background: white; border-radius: 16px; margin-bottom: 2rem;">
          <div style="font-size: 2rem; margin-bottom: 1rem;">📊</div>
          <h3>暂无统计数据</h3>
          <p>请稍后再试或联系管理员</p>
        </div>

        <!-- 有summary数据时显示 -->
        <div v-else>
          <v-row>
            <v-col cols="12" md="3">
              <v-card class="stats-card gradient-card-1" elevation="4">
                <v-card-text class="text-center">
                  <div class="stats-icon">📚</div>
                  <div class="stats-number">{{ summary.total_subject_usage || 0 }}</div>
                  <div class="stats-label">科目总使用次数</div>
                </v-card-text>
              </v-card>
            </v-col>
            <v-col cols="12" md="3">
              <v-card class="stats-card gradient-card-2" elevation="4">
                <v-card-text class="text-center">
                  <div class="stats-icon">📖</div>
                  <div class="stats-number">{{ summary.total_tiku_usage || 0 }}</div>
                  <div class="stats-label">题库总使用次数</div>
                </v-card-text>
              </v-card>
            </v-col>
            <v-col cols="12" md="3">
              <v-card class="stats-card gradient-card-3" elevation="4">
                <v-card-text class="text-center">
                  <div class="stats-icon">🔥</div>
                  <div class="stats-number">{{ summary.active_subjects_count || 0 }}</div>
                  <div class="stats-label">活跃科目数量</div>
                </v-card-text>
              </v-card>
            </v-col>
            <v-col cols="12" md="3">
              <v-card class="stats-card gradient-card-4" elevation="4">
                <v-card-text class="text-center">
                  <div class="stats-icon">⚡</div>
                  <div class="stats-number">{{ summary.active_tikues_count || 0 }}</div>
                  <div class="stats-label">活跃题库数量</div>
                </v-card-text>
              </v-card>
            </v-col>
          </v-row>

          <!-- 最受欢迎内容 -->
          <v-row class="mt-4">
            <v-col cols="12" md="6">
              <v-card class="popular-card" elevation="4">
                <v-card-title class="popular-title">
                  🏆 最受欢迎科目
                </v-card-title>
                <v-card-text>
                  <div v-if="summary.most_popular_subject" class="popular-item">
                    <div class="popular-name">{{ summary.most_popular_subject.subject_name }}</div>
                    <div class="popular-count">{{ summary.most_popular_subject.used_count }} 次使用</div>
                  </div>
                  <div v-else class="popular-item">
                    <div class="popular-name">暂无数据</div>
                    <div class="popular-count">0 次使用</div>
                  </div>
                </v-card-text>
              </v-card>
            </v-col>
            <v-col cols="12" md="6">
              <v-card class="popular-card" elevation="4">
                <v-card-title class="popular-title">
                  🏆 最受欢迎题库
                </v-card-title>
                <v-card-text>
                  <div v-if="summary.most_popular_tiku" class="popular-item">
                    <div class="popular-name">{{ summary.most_popular_tiku.tiku_name }}</div>
                    <div class="popular-count">{{ summary.most_popular_tiku.used_count }} 次使用</div>
                    <div class="popular-subject">{{ summary.most_popular_tiku.subject_name }}</div>
                  </div>
                  <div v-else class="popular-item">
                    <div class="popular-name">暂无数据</div>
                    <div class="popular-count">0 次使用</div>
                  </div>
                </v-card-text>
              </v-card>
            </v-col>
          </v-row>
        </div>
      </div>

      <!-- 标签切换 -->
      <div class="tabs-section">
        <v-tabs v-model="activeTab" color="primary" align-tabs="center">
          <v-tab value="subjects">📚 科目排行</v-tab>
          <v-tab value="tikues">📖 题库排行</v-tab>
          <v-tab value="analytics">📊 深度分析</v-tab>
        </v-tabs>

        <v-window v-model="activeTab" class="mt-4">
          <!-- 科目排行 -->
          <v-window-item value="subjects">
            <div class="ranking-section">
              <div class="section-header">
                <h2 class="section-title">热门科目排行榜 TOP 5</h2>
              </div>

              <div v-if="topSubjects?.length" class="ranking-cards">
                <v-card
                  v-for="(subject, index) in topSubjects"
                  :key="subject.subject_name"
                  class="ranking-card"
                  :class="getRankingCardClass(index)"
                  elevation="3"
                >
                  <v-card-text class="ranking-content">
                    <div class="rank-badge" :class="getRankBadgeClass(index)">
                      {{ index + 1 }}
                    </div>
                    <div class="ranking-details">
                      <div class="subject-name">{{ subject.subject_name }}</div>
                      <div class="usage-info">
                        <span class="usage-count">{{ subject.used_count }} 次使用</span>
                        <span class="usage-percentage">{{ (subject.usage_percentage || 0).toFixed(1) }}%</span>
                      </div>
                      <v-progress-linear
                        :model-value="subject.usage_percentage || 0"
                        color="primary"
                        height="6"
                        rounded
                        class="mt-2"
                      ></v-progress-linear>
                    </div>
                  </v-card-text>
                </v-card>
              </div>
              <div v-else class="empty-ranking">
                <div style="text-align: center; padding: 2rem; background: #f8fafc; border-radius: 12px;">
                  <div style="font-size: 2rem; margin-bottom: 1rem;">📚</div>
                  <h4>暂无科目数据</h4>
                  <p>请稍后再试</p>
                </div>
              </div>
            </div>
          </v-window-item>

          <!-- 题库排行 -->
          <v-window-item value="tikues">
            <div class="ranking-section">
              <div class="section-header">
                <h2 class="section-title">热门题库排行榜 TOP 10</h2>
              </div>

              <div v-if="topTikues?.length" class="tiku-list">
                <v-card
                  v-for="(tiku, index) in topTikues"
                  :key="tiku.tiku_name"
                  class="tiku-card"
                  elevation="2"
                >
                  <v-card-text class="tiku-content">
                    <div class="tiku-rank" :class="getRankBadgeClass(index)">
                      {{ index + 1 }}
                    </div>
                    <div class="tiku-info">
                      <div class="tiku-name">{{ tiku.tiku_name }}</div>
                      <div class="tiku-meta">
                        <v-chip color="info" size="small" variant="outlined">
                          {{ tiku.subject_name }}
                        </v-chip>
                        <span class="tiku-usage">{{ tiku.used_count }} 次使用</span>
                        <span class="tiku-percentage">{{ (tiku.usage_percentage || 0).toFixed(1) }}%</span>
                      </div>
                    </div>
                    <div class="tiku-progress">
                      <v-progress-linear
                        :model-value="tiku.usage_percentage || 0"
                        color="primary"
                        height="4"
                        rounded
                      ></v-progress-linear>
                    </div>
                  </v-card-text>
                </v-card>
              </div>
              <div v-else class="empty-ranking">
                <div style="text-align: center; padding: 2rem; background: #f8fafc; border-radius: 12px;">
                  <div style="font-size: 2rem; margin-bottom: 1rem;">📖</div>
                  <h4>暂无题库数据</h4>
                  <p>请稍后再试</p>
                </div>
              </div>
            </div>
          </v-window-item>

          <!-- 深度分析 -->
          <v-window-item value="analytics">
            <div class="analytics-section">
              <v-row>
                <v-col cols="12" md="6">
                  <v-card class="analytics-card" elevation="4">
                    <v-card-title>📊 科目使用分析</v-card-title>
                    <v-card-text>
                      <div v-if="fullStats?.subject_stats?.length" class="chart-placeholder">
                        <div class="chart-item" v-for="subject in fullStats.subject_stats.slice(0, 8)" :key="subject.subject_name">
                          <div class="chart-label">{{ subject.subject_name }}</div>
                          <div class="chart-bar-container">
                            <div 
                              class="chart-bar" 
                              :style="{ width: getPercentageWidth(subject.used_count, fullStats.subject_stats) + '%' }"
                            ></div>
                            <span class="chart-value">{{ subject.used_count }}</span>
                          </div>
                        </div>
                      </div>
                    </v-card-text>
                  </v-card>
                </v-col>
                <v-col cols="12" md="6">
                  <v-card class="analytics-card" elevation="4">
                    <v-card-title>🎯 使用趋势分析</v-card-title>
                    <v-card-text>
                      <div class="trend-metrics">
                        <div class="metric-item">
                          <div class="metric-label">平均科目使用率</div>
                          <div class="metric-value">
                            {{ summary ? (summary.total_subject_usage / summary.total_subjects).toFixed(1) : 0 }}
                          </div>
                        </div>
                        <div class="metric-item">
                          <div class="metric-label">平均题库使用率</div>
                          <div class="metric-value">
                            {{ summary ? (summary.total_tiku_usage / summary.total_tikues).toFixed(1) : 0 }}
                          </div>
                        </div>
                        <div class="metric-item">
                          <div class="metric-label">科目活跃度</div>
                          <div class="metric-value">
                            {{ summary ? ((summary.active_subjects_count / summary.total_subjects) * 100).toFixed(1) : 0 }}%
                          </div>
                        </div>
                        <div class="metric-item">
                          <div class="metric-label">题库活跃度</div>
                          <div class="metric-value">
                            {{ summary ? ((summary.active_tikues_count / summary.total_tikues) * 100).toFixed(1) : 0 }}%
                          </div>
                        </div>
                      </div>
                    </v-card-text>
                  </v-card>
                </v-col>
              </v-row>
            </div>
          </v-window-item>
        </v-window>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useToast } from 'vue-toastification'
import { apiService } from '@/services/api'
import type { UsageSummary, UsageSubjectStat, UsageTikuStat, UsageStats } from '@/services/api'
import IconStats from '@/components/icons/IconStats.vue'

const toast = useToast()

// 响应式数据
const loading = ref(false)
const activeTab = ref('subjects')

const summary = ref<UsageSummary | null>(null)
const topSubjects = ref<UsageSubjectStat[]>([])
const topTikues = ref<UsageTikuStat[]>([])
const fullStats = ref<UsageStats | null>(null)

// 加载统计摘要
const loadSummary = async () => {
  try {
    const response = await apiService.usage.getUsageSummary()
    
    if (response.success && response.data) {
      summary.value = response.data
    } else {
      console.error('统计摘要加载失败:', response.message)
      toast.error(response.message || '获取统计摘要失败')
    }
  } catch (error) {
    console.error('获取统计摘要失败:', error)
    toast.error('获取统计摘要失败')
  }
}

// 加载热门科目
const loadTopSubjects = async () => {
  try {
    const response = await apiService.usage.getTopSubjects(5)
    
    if (response.success && response.data) {
      topSubjects.value = response.data.top_subjects
    } else {
      console.error('热门科目加载失败:', response.message)
      toast.error(response.message || '获取热门科目失败')
    }
  } catch (error) {
    console.error('获取热门科目失败:', error)
    toast.error('获取热门科目失败')
  }
}

// 加载热门题库
const loadTopTikues = async () => {
  try {
    const response = await apiService.usage.getTopTikues(10)
    
    if (response.success && response.data) {
      topTikues.value = response.data.top_tikues
    } else {
      console.error('热门题库加载失败:', response.message)
      toast.error(response.message || '获取热门题库失败')
    }
  } catch (error) {
    console.error('获取热门题库失败:', error)
    toast.error('获取热门题库失败')
  }
}

// 加载完整统计
const loadFullStats = async () => {
  try {
    const response = await apiService.usage.getUsageStats()
    
    if (response.success && response.data) {
      fullStats.value = response.data
    }
  } catch (error) {
    console.error('获取完整统计失败:', error)
  }
}

// 获取排行卡片样式
const getRankingCardClass = (index: number) => {
  if (index === 0) return 'rank-gold'
  if (index === 1) return 'rank-silver'
  if (index === 2) return 'rank-bronze'
  return 'rank-normal'
}

// 获取排名徽章样式
const getRankBadgeClass = (index: number) => {
  if (index === 0) return 'badge-gold'
  if (index === 1) return 'badge-silver'
  if (index === 2) return 'badge-bronze'
  return 'badge-normal'
}

// 获取百分比宽度
const getPercentageWidth = (value: number, list: any[]) => {
  if (!list.length) return 0
  const max = Math.max(...list.map(item => item.used_count))
  return max > 0 ? (value / max) * 100 : 0
}

// 初始化
const initializeData = async () => {
  loading.value = true
  try {
    await Promise.all([
      loadSummary(),
      loadTopSubjects(),
      loadTopTikues(),
      loadFullStats()
    ])
  } catch (error) {
    console.error('初始化数据失败:', error)
    toast.error('初始化数据失败')
  } finally {
    loading.value = false
  }
}

// 生命周期
onMounted(() => {
  initializeData()
})
</script>

<style scoped>
.enhanced-usage-stats-page {
  min-height: calc(100vh - 72px);
  background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
  padding: 2rem;
}

.page-container {
  max-width: 1400px;
  margin: 0 auto;
  animation: fadeIn 0.5s ease-out;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.page-header {
  text-align: center;
  margin-bottom: 3rem;
  padding: 2rem 2rem 1.5rem;
  background: white;
  border-radius: 20px;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
}

.page-title {
  font-size: 2.5rem;
  font-weight: 700;
  color: #1e293b;
  margin-bottom: 0.5rem;
  background: linear-gradient(135deg, #3b82f6, #8b5cf6);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
}

.page-description {
  font-size: 1.1rem;
  color: #64748b;
  font-weight: 500;
}

.loading-section {
  text-align: center;
  padding: 4rem 2rem;
  background: white;
  border-radius: 20px;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
}

.loading-text {
  margin-top: 1rem;
  font-size: 1.1rem;
  color: #64748b;
  font-weight: 500;
}

.stats-overview {
  margin-bottom: 3rem;
}

.stats-card {
  height: 160px;
  border-radius: 16px;
  color: white;
  position: relative;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
}

.gradient-card-1 {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.gradient-card-2 {
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
}

.gradient-card-3 {
  background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
}

.gradient-card-4 {
  background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
}

.stats-icon {
  font-size: 2.2rem;
  margin-bottom: 0.75rem;
}

.stats-number {
  font-size: 2.2rem;
  font-weight: 700;
  line-height: 1.1;
  margin-bottom: 0.5rem;
}

.stats-label {
  font-size: 0.95rem;
  opacity: 0.95;
  font-weight: 500;
  line-height: 1.3;
  text-align: center;
  word-wrap: break-word;
}

.popular-card {
  border-radius: 16px;
  background: linear-gradient(135deg, #ffeaa7 0%, #fab1a0 100%);
  color: #2d3436;
}

.popular-title {
  font-weight: 600;
  font-size: 1.1rem;
}

.popular-item {
  text-align: center;
}

.popular-name {
  font-size: 1.3rem;
  font-weight: 700;
  margin-bottom: 0.5rem;
}

.popular-count {
  font-size: 1rem;
  font-weight: 600;
  opacity: 0.8;
}

.popular-subject {
  font-size: 0.9rem;
  opacity: 0.7;
  margin-top: 0.25rem;
}

.tabs-section {
  background: white;
  border-radius: 20px;
  padding: 2rem;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
}

.section-header {
  margin-bottom: 1.5rem;
}

.section-title {
  font-size: 1.8rem;
  font-weight: 600;
  color: #1e293b;
}

.ranking-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  gap: 1.5rem;
}

.ranking-card {
  border-radius: 16px;
  transition: all 0.3s ease;
  border: 2px solid transparent;
}

.ranking-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 25px rgba(0, 0, 0, 0.15);
}

.rank-gold {
  border-color: #ffd700;
  background: linear-gradient(135deg, #fff9e6, #fffbeb);
}

.rank-silver {
  border-color: #c0c0c0;
  background: linear-gradient(135deg, #f8f9fa, #e9ecef);
}

.rank-bronze {
  border-color: #cd7f32;
  background: linear-gradient(135deg, #fdf4e3, #fbeee0);
}

.rank-normal {
  background: white;
}

.ranking-content {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.rank-badge {
  width: 50px;
  height: 50px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 1.2rem;
  flex-shrink: 0;
}

.badge-gold {
  background: linear-gradient(135deg, #ffd700, #ffed4a);
  color: #8b6914;
}

.badge-silver {
  background: linear-gradient(135deg, #c0c0c0, #e2e8f0);
  color: #374151;
}

.badge-bronze {
  background: linear-gradient(135deg, #cd7f32, #d69e2e);
  color: #7c2d12;
}

.badge-normal {
  background: linear-gradient(135deg, #6b7280, #9ca3af);
  color: white;
}

.ranking-details {
  flex: 1;
}

.subject-name {
  font-size: 1.2rem;
  font-weight: 600;
  color: #1e293b;
  margin-bottom: 0.5rem;
}

.usage-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}

.usage-count {
  font-weight: 600;
  color: #3b82f6;
}

.usage-percentage {
  font-weight: 600;
  color: #64748b;
}

.tiku-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.tiku-card {
  border-radius: 12px;
  transition: all 0.3s ease;
}

.tiku-card:hover {
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
  transform: translateX(5px);
}

.tiku-content {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.tiku-rank {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: 0.9rem;
  flex-shrink: 0;
}

.tiku-info {
  flex: 1;
}

.tiku-name {
  font-size: 1.1rem;
  font-weight: 600;
  color: #1e293b;
  margin-bottom: 0.5rem;
}

.tiku-meta {
  display: flex;
  align-items: center;
  gap: 1rem;
  flex-wrap: wrap;
}

.tiku-usage {
  font-weight: 500;
  color: #3b82f6;
}

.tiku-percentage {
  font-weight: 500;
  color: #64748b;
}

.tiku-progress {
  margin-top: 0.5rem;
}

.analytics-card {
  border-radius: 16px;
}

.chart-placeholder {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.chart-item {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.chart-label {
  min-width: 100px;
  font-weight: 500;
  font-size: 0.9rem;
}

.chart-bar-container {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.chart-bar {
  height: 20px;
  background: linear-gradient(90deg, #3b82f6, #1d4ed8);
  border-radius: 10px;
  min-width: 2px;
}

.chart-value {
  font-weight: 600;
  color: #374151;
  min-width: 30px;
}

.trend-metrics {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1.5rem;
}

.metric-item {
  text-align: center;
  padding: 1rem;
  background: #f8fafc;
  border-radius: 12px;
}

.metric-label {
  font-size: 0.9rem;
  color: #64748b;
  margin-bottom: 0.5rem;
}

.metric-value {
  font-size: 1.5rem;
  font-weight: 700;
  color: #1e293b;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .enhanced-usage-stats-page {
    padding: 1rem;
  }

  .page-header {
    padding: 1.5rem;
    margin-bottom: 2rem;
  }

  .page-title {
    font-size: 2rem;
  }

  .stats-card {
    height: 140px;
  }

  .stats-icon {
    font-size: 2rem;
    margin-bottom: 0.5rem;
  }

  .stats-number {
    font-size: 2rem;
    margin-bottom: 0.4rem;
  }

  .stats-label {
    font-size: 0.85rem;
    line-height: 1.2;
  }

  .ranking-cards {
    grid-template-columns: 1fr;
  }

  .section-header {
    flex-direction: column;
    align-items: stretch;
    gap: 1rem;
  }

  .usage-info {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.25rem;
  }

  .tiku-meta {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.5rem;
  }

  .trend-metrics {
    grid-template-columns: 1fr;
  }
}
</style> 