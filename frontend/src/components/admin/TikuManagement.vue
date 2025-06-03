<template>
  <div class="control-section">
    <div class="section-header">
      <h2 class="section-title">📖 题库管理</h2>
      <div class="section-actions">
        <v-btn
          color="primary"
          prepend-icon="mdi-upload"
          @click="$emit('showUploadDialog')"
          variant="elevated"
        >
          上传题库
        </v-btn>
        <v-btn
          color="secondary"
          prepend-icon="mdi-refresh"
          @click="$emit('reloadBanks')"
          :loading="loading"
          variant="elevated"
        >
          重新加载
        </v-btn>
      </div>
    </div>

    <!-- 科目选择器 -->
    <div v-if="subjects.length > 0" class="subject-selector pa-4">
      <v-chip-group
        :model-value="selectedSubjectId"
        color="primary"
        selected-class="text-primary"
        @update:model-value="(value: number | null) => $emit('selectSubject', value || 0)"
      >
        <v-chip
          v-for="subject in subjects"
          :key="subject.subject_id"
          :value="subject.subject_id"
          variant="outlined"
        >
          {{ subject.subject_name }}
        </v-chip>
      </v-chip-group>
    </div>

    <div v-if="loading">
      <Loading />
    </div>

    <div v-else-if="!selectedSubjectId" class="empty-state">
      <div class="empty-icon">📖</div>
      <p>请选择一个科目查看题库</p>
    </div>

    <div v-else-if="tikuList.length === 0" class="empty-state">
      <div class="empty-icon">📖</div>
      <p>{{ tikuSearch ? '没有找到匹配的题库' : '该科目下暂无题库' }}</p>
    </div>

    <v-data-table
      v-else
      :headers="tikuHeaders"
      :items="filteredTiku"
      :loading="loading"
      :search="tikuSearch"
      :items-per-page="tikuItemsPerPage"
      :sort-by="tikuSortBy"
      :items-per-page-options="itemsPerPageOptions"
      :items-per-page-text="'每页显示：'"
      class="elevation-2"
      density="comfortable"
      :no-data-text="'该科目下暂无题库'"
      :no-results-text="'没有找到匹配的题库'"
    >
      <!-- 搜索槽 -->
      <template v-slot:top>
        <div class="pa-4">
          <v-text-field
            v-model="tikuSearch"
            label="搜索题库名称..."
            prepend-inner-icon="mdi-magnify"
            variant="outlined"
            hide-details
            clearable
            density="compact"
          ></v-text-field>
        </div>
      </template>

      <!-- 题库名称列 -->
      <template v-slot:item.tiku_name="{ item }">
        <div class="font-weight-bold">{{ (item as any).tiku_name }}</div>
      </template>

      <!-- 题目数量列 -->
      <template v-slot:item.tiku_nums="{ item }">
        <v-chip size="small" color="info">{{ item.tiku_nums }}</v-chip>
      </template>

      <!-- 文件大小列 -->
      <template v-slot:item.file_size="{ item }">
        {{ formatFileSize(item.file_size || 0) }}
      </template>

      <!-- 状态列 -->
      <template v-slot:item.is_active="{ item }">
        <v-chip
          :color="item.is_active ? 'success' : 'error'"
          size="small"
          variant="flat"
        >
          {{ item.is_active ? '启用' : '禁用' }}
        </v-chip>
      </template>

      <!-- 创建时间列 -->
      <template v-slot:item.created_at="{ item }">
        <span class="text-caption">{{ formatDate(item.created_at) }}</span>
      </template>

      <!-- 更新时间列 -->
      <template v-slot:item.updated_at="{ item }">
        <span class="text-caption">{{ formatDate(item.updated_at) }}</span>
      </template>

      <!-- 操作列 -->
      <template v-slot:item.actions="{ item }">
        <v-btn
          :color="item.is_active ? 'warning' : 'success'"
          size="small"
          variant="elevated"
          @click="$emit('toggleTiku', item)"
          class="mr-2"
        >
          {{ item.is_active ? '禁用' : '启用' }}
        </v-btn>
        <v-btn
          color="error"
          size="small"
          variant="elevated"
          @click="$emit('deleteTiku', item)"
        >
          删除
        </v-btn>
      </template>
    </v-data-table>
  </div>
</template>

<script lang="ts" setup>
import { ref, computed } from 'vue'
import Loading from '@/components/common/Loading.vue'
import type { Subject, TikuItem } from '@/services/api'

interface Props {
  subjects: Subject[]
  tikuList: TikuItem[]
  selectedSubjectId: number | null
  loading: boolean
}

interface Emits {
  (e: 'selectSubject', subjectId: number): void
  (e: 'showUploadDialog'): void
  (e: 'reloadBanks'): void
  (e: 'toggleTiku', tiku: TikuItem): void
  (e: 'deleteTiku', tiku: TikuItem): void
}

const props = defineProps<Props>()
defineEmits<Emits>()

// 表格配置
const tikuSearch = ref('')
const tikuItemsPerPage = ref(20)
const tikuSortBy = ref([{ key: 'tiku_id', order: 'desc' as const }])

const itemsPerPageOptions = [
  { value: 10, title: '10条/页' },
  { value: 20, title: '20条/页' },
  { value: 50, title: '50条/页' },
  { value: 100, title: '100条/页' },
  { value: -1, title: '全部显示' }
]

const tikuHeaders = [
  { title: '题库名称', key: 'tiku_name', sortable: true, width: '250px' },
  { title: '题目数量', key: 'tiku_nums', sortable: true, width: '120px', align: 'center' as const },
  { title: '文件大小', key: 'file_size', sortable: true, width: '120px', align: 'center' as const },
  { title: '状态', key: 'is_active', sortable: false, width: '100px', align: 'center' as const },
  { title: '创建时间', key: 'created_at', sortable: true, width: '160px' },
  { title: '更新时间', key: 'updated_at', sortable: true, width: '160px' },
  { title: '操作', key: 'actions', sortable: false, width: '150px', align: 'center' as const }
]

// 计算属性
const filteredTiku = computed(() => {
  if (!tikuSearch.value) return props.tikuList
  const searchTerm = tikuSearch.value.toLowerCase()
  return props.tikuList.filter((tiku: TikuItem) => 
    tiku.tiku_name?.toLowerCase().includes(searchTerm) ||
    tiku.tiku_position?.toLowerCase().includes(searchTerm)
  )
})

// 工具函数
const formatDate = (dateString?: string) => {
  if (!dateString) return '-'
  try {
    return new Date(dateString).toLocaleString('zh-CN')
  } catch {
    return '-'
  }
}

const formatFileSize = (bytes: number) => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}
</script>

<style scoped>
.control-section {
  background: white;
  border-radius: 20px;
  padding: 2rem;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
  animation: slideIn 0.3s ease-out;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateX(-20px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
  padding-bottom: 1rem;
  border-bottom: 2px solid #f1f5f9;
}

.section-title {
  font-size: 1.5rem;
  font-weight: 600;
  color: #1e293b;
  margin: 0;
}

.section-actions {
  display: flex;
  gap: 1rem;
}

.subject-selector {
  margin-bottom: 2rem;
  padding: 1.5rem;
  background: #f8fafc;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
}

.empty-state {
  text-align: center;
  padding: 4rem 2rem;
  color: #64748b;
}

.empty-icon {
  font-size: 4rem;
  margin-bottom: 1rem;
  opacity: 0.5;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .section-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 1rem;
  }

  .section-actions {
    width: 100%;
    justify-content: flex-end;
  }
}
</style> 