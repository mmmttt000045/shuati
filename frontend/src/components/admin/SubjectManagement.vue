<template>
  <div class="control-section">
    <div class="section-header">
      <h2 class="section-title">
        <IconSubject :size="24" color="#3b82f6" class="title-icon" />
        科目管理
      </h2>
      <div class="section-actions">
        <v-btn
          color="primary"
          prepend-icon="mdi-plus"
          @click="$emit('showCreateDialog')"
          variant="elevated"
        >
          创建科目
        </v-btn>
        <v-btn
          color="secondary"
          prepend-icon="mdi-refresh"
          @click="$emit('refresh')"
          :loading="loading"
          variant="elevated"
        >
          刷新列表
        </v-btn>
      </div>
    </div>

    <v-data-table
      :headers="subjectHeaders"
      :items="filteredSubjects"
      :loading="loading"
      :search="subjectSearch"
      :items-per-page="subjectItemsPerPage"
      :sort-by="subjectSortBy"
      :items-per-page-options="itemsPerPageOptions"
      :items-per-page-text="'每页显示：'"
      class="elevation-2"
      density="comfortable"
      :no-data-text="'暂无科目'"
      :no-results-text="'没有找到匹配的科目'"
    >
      <!-- 搜索槽 -->
      <template v-slot:top>
        <div class="pa-4">
          <v-text-field
            v-model="subjectSearch"
            label="搜索科目名称..."
            prepend-inner-icon="mdi-magnify"
            variant="outlined"
            hide-details
            clearable
            density="compact"
          ></v-text-field>
        </div>
      </template>

      <!-- 科目名称列 -->
      <template v-slot:item.subject_name="{ item }">
        <div class="font-weight-bold">{{ item.subject_name }}</div>
      </template>

      <!-- 考试时间列 -->
      <template v-slot:item.exam_time="{ item }">
        <span class="text-caption">{{ formatDate(item.exam_time) }}</span>
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
          color="primary"
          size="small"
          variant="elevated"
          @click="$emit('showEditDialog', item)"
          class="mr-2"
        >
          编辑
        </v-btn>
        <v-btn
          color="error"
          size="small"
          variant="elevated"
          @click="$emit('deleteSubject', item)"
        >
          删除
        </v-btn>
      </template>
    </v-data-table>
  </div>
</template>

<script lang="ts" setup>
import { ref, computed } from 'vue'
import IconSubject from '@/components/icons/IconSubject.vue'
import type { Subject } from '@/services/api'

interface Props {
  subjects: Subject[]
  loading: boolean
}

interface Emits {
  (e: 'refresh'): void
  (e: 'showCreateDialog'): void
  (e: 'showEditDialog', subject: Subject): void
  (e: 'deleteSubject', subject: Subject): void
}

const props = defineProps<Props>()
defineEmits<Emits>()

// 表格配置
const subjectSearch = ref('')
const subjectItemsPerPage = ref(20)
const subjectSortBy = ref([{ key: 'subject_id', order: 'desc' as const }])

const itemsPerPageOptions = [
  { value: 10, title: '10条/页' },
  { value: 20, title: '20条/页' },
  { value: 50, title: '50条/页' },
  { value: 100, title: '100条/页' },
  { value: -1, title: '全部显示' }
]

const subjectHeaders = [
  { title: 'ID', key: 'subject_id', sortable: true, width: '80px' },
  { title: '科目名称', key: 'subject_name', sortable: true, width: '200px' },
  { title: '考试时间', key: 'exam_time', sortable: true, width: '180px' },
  { title: '创建时间', key: 'created_at', sortable: true, width: '160px' },
  { title: '更新时间', key: 'updated_at', sortable: true, width: '160px' },
  { title: '操作', key: 'actions', sortable: false, width: '150px', align: 'center' as const }
]

// 计算属性
const filteredSubjects = computed(() => {
  if (!subjectSearch.value) return props.subjects
  const searchTerm = subjectSearch.value.toLowerCase()
  return props.subjects.filter((subject: Subject) => 
    subject.subject_name?.toLowerCase().includes(searchTerm)
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
  display: flex;
  align-items: center;
}

.title-icon {
  margin-right: 0.5rem;
  filter: drop-shadow(0 2px 4px rgba(59, 130, 246, 0.3));
  vertical-align: middle;
}

.section-actions {
  display: flex;
  gap: 1rem;
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