<template>
  <div class="usage-stats-page">
    <div class="page-container">
      <!-- 页面标题 -->
      <div class="page-header">
        <h1 class="page-title">
          <IconStats :size="48" color="#3b82f6" class="title-icon" />
          系统使用统计
        </h1>
        <p class="page-description">实时查看平台各科目和题库的热门排行榜</p>
      </div>

      <!-- 加载状态 -->
      <div v-if="loadingStats" class="loading-section">
        <v-progress-circular indeterminate color="primary" size="64"></v-progress-circular>
        <div class="loading-text">加载统计数据中...</div>
      </div>

      <!-- 空状态 -->
      <div v-else-if="!usageStats" class="empty-section">
        <div class="empty-icon">
          <IconStats :size="64" color="#9ca3af" />
        </div>
        <div class="empty-text">暂无统计数据</div>
        <div class="empty-subtitle">数据可能正在更新中，请稍后查看</div>
      </div>

      <!-- 统计内容 -->
      <div v-else class="stats-content">
        <!-- 科目使用统计 -->
        <div class="stats-section">
          <div class="section-header">
            <h2 class="section-title">
              <IconSubject :size="24" color="#3b82f6" class="title-icon" />
              科目使用排行
            </h2>
            <div class="section-subtitle">各科目被使用的次数统计Top 10</div>
          </div>
          
          <div v-if="usageStats.subject_stats && usageStats.subject_stats.length > 0" class="table-container">
            <v-data-table
              :headers="subjectStatsHeaders"
              :items="usageStats.subject_stats"
              :items-per-page="15"
              :sort-by="[{ key: 'used_count', order: 'desc' }]"
              class="elevation-2 stats-table"
              density="comfortable"
              :no-data-text="'暂无科目使用数据'"
              hide-default-footer
            >
              <!-- 排名列 -->
              <template v-slot:item.rank="{ index }">
                <v-chip
                  :color="(index as number) < 3 ? 'warning' : 'default'"
                  size="small"
                  variant="flat"
                  class="rank-chip"
                >
                  {{ (index as number) + 1 }}
                </v-chip>
              </template>

              <!-- 科目名称列 -->
              <template v-slot:item.subject_name="{ item }">
                <div class="subject-name">{{ (item as any).subject_name }}</div>
              </template>

              <!-- 使用次数列 -->
              <template v-slot:item.used_count="{ item }">
                <v-chip
                  v-if="(item as any).used_count === 0"
                  color="grey"
                  size="small"
                  variant="outlined"
                >
                  未使用
                </v-chip>
                <v-chip
                  v-else
                  color="success"
                  size="small"
                  variant="flat"
                >
                  {{ (item as any).used_count }}
                </v-chip>
              </template>

              <!-- 使用率列 -->
              <template v-slot:item.usage_rate="{ item }">
                <div class="usage-rate-container">
                  <v-progress-linear
                    v-if="(item as any).used_count > 0"
                    :model-value="getUsagePercentage((item as any).used_count, usageStats.subject_stats)"
                    color="primary"
                    height="8"
                    class="usage-bar"
                  ></v-progress-linear>
                  <span class="usage-text">
                    {{ (item as any).used_count > 0 ? getUsagePercentage((item as any).used_count, usageStats.subject_stats).toFixed(1) + '%' : '未使用' }}
                  </span>
                </div>
              </template>
            </v-data-table>
          </div>
          <div v-else class="empty-table">
            <div class="empty-table-icon">
              <IconSubject :size="48" color="#cbd5e1" />
            </div>
            <div class="empty-table-text">暂无科目使用数据</div>
          </div>
        </div>

        <!-- 题库使用统计 -->
        <div class="stats-section">
          <div class="section-header">
            <h2 class="section-title">📖 热门题库排行</h2>
            <div class="section-subtitle">最受欢迎的题库TOP 20</div>
          </div>
          
          <div v-if="usageStats.tiku_stats && usageStats.tiku_stats.length > 0" class="table-container">
            <v-data-table
              :headers="tikuStatsHeaders"
              :items="usageStats.tiku_stats.slice(0, 20)"
              :items-per-page="20"
              :sort-by="[{ key: 'used_count', order: 'desc' }]"
              class="elevation-2 stats-table"
              density="comfortable"
              :no-data-text="'暂无题库使用数据'"
              hide-default-footer
            >
              <!-- 排名列 -->
              <template v-slot:item.rank="{ index }">
                <v-chip
                  :color="index < 3 ? 'warning' : 'default'"
                  size="small"
                  variant="flat"
                  class="rank-chip"
                >
                  {{ index + 1 }}
                </v-chip>
              </template>

              <!-- 题库名称列 -->
              <template v-slot:item.tiku_name="{ item }">
                <div class="tiku-name">{{ (item as any).tiku_name }}</div>
              </template>

              <!-- 所属科目列 -->
              <template v-slot:item.subject_name="{ item }">
                <v-chip
                  color="info"
                  size="small"
                  variant="outlined"
                >
                  {{ (item as any).subject_name }}
                </v-chip>
              </template>

              <!-- 使用次数列 -->
              <template v-slot:item.used_count="{ item }">
                <v-chip
                  v-if="(item as any).used_count === 0"
                  color="grey"
                  size="small"
                  variant="outlined"
                >
                  未使用
                </v-chip>
                <v-chip
                  v-else
                  color="success"
                  size="small"
                  variant="flat"
                >
                  {{ (item as any).used_count }}
                </v-chip>
              </template>

              <!-- 使用率列 -->
              <template v-slot:item.usage_rate="{ item }">
                <div class="usage-rate-container">
                  <v-progress-linear
                    v-if="(item as any).used_count > 0"
                    :model-value="getUsagePercentage((item as any).used_count, usageStats.tiku_stats)"
                    color="primary"
                    height="8"
                    class="usage-bar"
                  ></v-progress-linear>
                  <span class="usage-text">
                    {{ (item as any).used_count > 0 ? getUsagePercentage((item as any).used_count, usageStats.tiku_stats).toFixed(1) + '%' : '未使用' }}
                  </span>
                </div>
              </template>
            </v-data-table>
          </div>
          <div v-else class="empty-table">
            <div class="empty-table-icon">
              <IconStats :size="48" color="#cbd5e1" />
            </div>
            <div class="empty-table-text">暂无题库使用数据</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useToast } from 'vue-toastification'
import { apiService } from '@/services/api'
import IconStats from '@/components/icons/IconStats.vue'
import IconSubject from '@/components/icons/IconSubject.vue'

// 接口
interface StatItem {
  used_count: number
  subject_name?: string
  tiku_name?: string
  [key: string]: any
}

interface UsageStats {
  subject_stats: StatItem[]
  tiku_stats: StatItem[]
}

const toast = useToast()

// 响应式数据
const usageStats = ref<UsageStats | null>(null)
const loadingStats = ref(false)

// 表格表头
const subjectStatsHeaders = [
  { title: '排名', key: 'rank', sortable: false, width: '100px', align: 'center' as const },
  { title: '科目名称', key: 'subject_name', sortable: false, width: '250px' },
  { title: '使用次数', key: 'used_count', sortable: true, width: '150px', align: 'center' as const },
  { title: '使用率', key: 'usage_rate', sortable: false, width: '200px', align: 'center' as const }
]

const tikuStatsHeaders = [
  { title: '排名', key: 'rank', sortable: false, width: '80px', align: 'center' as const },
  { title: '题库名称', key: 'tiku_name', sortable: false, width: '200px' },
  { title: '科目', key: 'subject_name', sortable: false, width: '120px', align: 'center' as const },
  { title: '使用次数', key: 'used_count', sortable: true, width: '120px', align: 'center' as const },
  { title: '使用率', key: 'usage_rate', sortable: false, width: '160px', align: 'center' as const }
]

// 使用统计相关函数
const loadUsageStats = async () => {
  loadingStats.value = true
  try {
    const response = await apiService.admin.getUsageStats()
    if (response.success) {
      const stats = {
        subject_stats: response.subject_stats || [],
        tiku_stats: response.tiku_stats || []
      }
      usageStats.value = stats
    } else {
      toast.error(response.message || '获取使用统计数据失败')
    }
  } catch (error) {
    console.error('获取使用统计数据失败:', error)
    toast.error('获取使用统计数据失败')
  } finally {
    loadingStats.value = false
  }
}

const getUsagePercentage = (usedCount: number, totalStats: any[]) => {
  if (!totalStats || totalStats.length === 0 || usedCount === 0) return 0
  const maxCount = Math.max(...totalStats.map(item => item.used_count))
  return maxCount > 0 ? (usedCount / maxCount) * 100 : 0
}

// 组件挂载时加载数据
onMounted(() => {
  loadUsageStats()
})
</script>

<style scoped>
.usage-stats-page {
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
  padding: 2rem;
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

.title-icon {
  filter: drop-shadow(0 2px 4px rgba(59, 130, 246, 0.3));
}

.page-description {
  font-size: 1.1rem;
  color: #64748b;
  margin: 0;
  font-weight: 500;
}

.loading-section, .empty-section {
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

.empty-icon {
  font-size: 4rem;
  margin-bottom: 1rem;
  opacity: 0.6;
}

.empty-text {
  font-size: 1.2rem;
  color: #64748b;
  margin-bottom: 1rem;
  font-weight: 500;
}

.empty-subtitle {
  font-size: 1rem;
  color: #64748b;
  margin: 0;
  font-weight: 500;
}

.stats-content {
  display: flex;
  flex-direction: column;
  gap: 3rem;
}

.stats-section {
  background: white;
  border-radius: 20px;
  padding: 2rem;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
  transition: all 0.3s ease;
}

.stats-section:hover {
  box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.15);
  transform: translateY(-2px);
}

.section-header {
  margin-bottom: 2rem;
  padding-bottom: 1rem;
  border-bottom: 2px solid #f1f5f9;
}

.section-title {
  font-size: 1.8rem;
  font-weight: 600;
  color: #1e293b;
  margin-bottom: 0.5rem;
  display: flex;
  align-items: center;
}

.section-subtitle {
  font-size: 1rem;
  color: #64748b;
  font-weight: 500;
}

.table-container {
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid #e2e8f0;
}

.stats-table {
  background: white;
}

.stats-table :deep(.v-data-table-header) {
  background: #f8fafc;
}

.stats-table :deep(.v-data-table-header th) {
  background: #f8fafc !important;
  color: #374151 !important;
  font-weight: 600 !important;
  font-size: 0.9rem !important;
  border-bottom: 2px solid #e2e8f0 !important;
}

.stats-table :deep(.v-data-table__td) {
  border-bottom: 1px solid #f1f5f9 !important;
  padding: 16px 12px !important;
}

.stats-table :deep(.v-data-table__tr:hover) {
  background: #fafbfc !important;
}

.rank-chip {
  font-weight: 600;
  min-width: 32px;
}

.subject-name, .tiku-name {
  font-weight: 600;
  color: #1e293b;
  font-size: 0.95rem;
}

.usage-rate-container {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  min-width: 140px;
}

.usage-bar {
  flex: 1;
  border-radius: 4px;
}

.usage-text {
  font-size: 0.85rem;
  color: #6b7280;
  font-weight: 500;
  min-width: 50px;
  text-align: right;
}

.empty-table {
  text-align: center;
  padding: 4rem 2rem;
  color: #9ca3af;
}

.empty-table-icon {
  font-size: 3rem;
  margin-bottom: 1rem;
  opacity: 0.5;
}

.empty-table-text {
  font-size: 1.1rem;
  font-weight: 500;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .usage-stats-page {
    padding: 1rem;
  }

  .page-header {
    padding: 1.5rem;
    margin-bottom: 2rem;
  }

  .page-title {
    font-size: 2rem;
  }

  .page-description {
    font-size: 1rem;
  }

  .stats-section {
    padding: 1.5rem;
  }

  .section-title {
    font-size: 1.5rem;
  }

  .stats-table :deep(.v-data-table__td) {
    padding: 12px 8px !important;
  }

  .usage-rate-container {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.5rem;
    min-width: auto;
  }

  .usage-bar {
    width: 100%;
  }

  .usage-text {
    text-align: left;
    min-width: auto;
  }
}

@media (max-width: 480px) {
  .page-title {
    font-size: 1.8rem;
  }

  .stats-table :deep(.v-data-table__td) {
    padding: 8px 4px !important;
    font-size: 0.85rem;
  }

  .rank-chip {
    min-width: 28px;
    font-size: 0.7rem;
  }

  .subject-name, .tiku-name {
    font-size: 0.85rem;
  }
}

/* 滚动条美化 */
.table-container::-webkit-scrollbar {
  height: 8px;
  width: 8px;
}

.table-container::-webkit-scrollbar-track {
  background: #f1f5f9;
  border-radius: 4px;
}

.table-container::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 4px;
}

.table-container::-webkit-scrollbar-thumb:hover {
  background: #94a3b8;
}

/* 进度条样式增强 */
.stats-table :deep(.v-progress-linear) {
  border-radius: 4px;
  overflow: hidden;
}

.stats-table :deep(.v-progress-linear__determinate) {
  background: linear-gradient(90deg, #3b82f6, #2563eb);
}

/* 标题图标样式 */
.section-title .title-icon {
  margin-right: 0.5rem;
  filter: drop-shadow(0 2px 4px rgba(59, 130, 246, 0.3));
  vertical-align: middle;
}
</style> 