<template>
  <div class="question-management">
    <div class="section-header">
      <h2 class="section-title">
        📝 题目管理 - {{ tikuInfo?.tiku_name || '未知题库' }}
      </h2>
      <div class="section-actions">
        <v-btn
          color="primary"
          prepend-icon="mdi-plus"
          @click="showCreateDialog = true"
          variant="elevated"
        >
          新增题目
        </v-btn>
        <v-btn
          color="secondary"
          prepend-icon="mdi-refresh"
          @click="loadQuestions"
          :loading="loading"
          variant="elevated"
        >
          刷新
        </v-btn>
        <v-btn
          color="default"
          prepend-icon="mdi-arrow-left"
          @click="$emit('goBack')"
          variant="elevated"
        >
          返回题库列表
        </v-btn>
      </div>
    </div>

    <!-- 题库信息卡片 -->
    <v-card v-if="tikuInfo" class="mb-4" variant="outlined">
      <v-card-text>
        <div class="d-flex flex-wrap align-center">
          <div class="me-4 mb-2">
            <span class="text-subtitle-2">科目：</span>
            <v-chip size="small" color="primary">{{ tikuInfo.subject_name }}</v-chip>
          </div>
          <div class="me-4 mb-2">
            <span class="text-subtitle-2">题目总数：</span>
            <v-chip size="small" color="info">{{ tikuInfo.tiku_nums }}</v-chip>
          </div>
          <div class="me-4 mb-2">
            <span class="text-subtitle-2">文件大小：</span>
            <span class="text-body-2">{{ formatFileSize(tikuInfo.file_size || 0) }}</span>
          </div>
          <div class="me-4 mb-2">
            <span class="text-subtitle-2">状态：</span>
            <v-chip
              size="small"
              :color="tikuInfo.is_active ? 'success' : 'error'"
            >
              {{ tikuInfo.is_active ? '启用' : '禁用' }}
            </v-chip>
          </div>
        </div>
      </v-card-text>
    </v-card>

    <!-- 搜索和筛选 -->
    <v-card class="mb-4" variant="outlined">
      <v-card-text>
        <v-row>
          <v-col cols="12" sm="6" md="4">
            <v-text-field
              v-model="search"
              label="搜索题目内容..."
              prepend-inner-icon="mdi-magnify"
              variant="outlined"
              hide-details
              clearable
              density="compact"
            />
          </v-col>
          <v-col cols="12" sm="6" md="3">
            <v-select
              v-model="typeFilter"
              :items="questionTypes"
              label="题目类型"
              variant="outlined"
              hide-details
              clearable
              density="compact"
            />
          </v-col>
          <v-col cols="12" sm="6" md="3">
            <v-select
              v-model="statusFilter"
              :items="statusOptions"
              label="状态"
              variant="outlined"
              hide-details
              clearable
              density="compact"
            />
          </v-col>
          <v-col cols="12" sm="6" md="2">
            <v-select
              v-model="difficultyFilter"
              :items="difficultyOptions"
              label="难度"
              variant="outlined"
              hide-details
              clearable
              density="compact"
            />
          </v-col>
        </v-row>
      </v-card-text>
    </v-card>

    <!-- 题目表格 -->
    <v-data-table
      :headers="questionHeaders"
      :items="filteredQuestions"
      :loading="loading"
      :items-per-page="itemsPerPage"
      :sort-by="sortBy"
      :items-per-page-options="itemsPerPageOptions"
      :items-per-page-text="'每页显示：'"
      class="elevation-2"
      density="comfortable"
      :no-data-text="'暂无题目数据'"
      :no-results-text="'没有找到匹配的题目'"
    >
      <!-- 题目内容列 -->
      <template v-slot:item.stem="{ item }">
        <div class="question-stem">
          <div class="text-truncate" style="max-width: 300px;" :title="item.stem">
            {{ item.stem }}
          </div>
        </div>
      </template>

      <!-- 题目类型列 -->
      <template v-slot:item.question_type="{ item }">
        <v-chip
          size="small"
          :color="getTypeColor(item.question_type)"
          variant="flat"
        >
          {{ getTypeName(item.question_type) }}
        </v-chip>
      </template>

      <!-- 难度列 -->
      <template v-slot:item.difficulty="{ item }">
        <v-rating
          :model-value="item.difficulty || 1"
          readonly
          size="small"
          density="compact"
          length="5"
        />
      </template>

      <!-- 状态列 -->
      <template v-slot:item.status="{ item }">
        <v-chip
          size="small"
          :color="item.status === 'active' ? 'success' : 'error'"
          variant="flat"
        >
          {{ item.status === 'active' ? '启用' : '禁用' }}
        </v-chip>
      </template>

      <!-- 创建时间列 -->
      <template v-slot:item.created_at="{ item }">
        <span class="text-caption">{{ formatDate(item.created_at) }}</span>
      </template>

      <!-- 操作列 -->
      <template v-slot:item.actions="{ item }">
        <v-btn
          color="primary"
          size="small"
          variant="outlined"
          @click="editQuestion(item)"
          class="mr-1"
        >
          编辑
        </v-btn>
        <v-btn
          color="info"
          size="small"
          variant="outlined"
          @click="viewQuestion(item)"
          class="mr-1"
        >
          查看
        </v-btn>
        <v-btn
          color="error"
          size="small"
          variant="outlined"
          @click="deleteQuestion(item)"
        >
          删除
        </v-btn>
      </template>
    </v-data-table>

    <!-- 新增/编辑题目对话框 -->
    <QuestionEditDialog
      v-model="showEditDialog"
      :question="selectedQuestion"
      :tiku-info="tikuInfo"
      @saved="onQuestionSaved"
    />

    <!-- 新增题目对话框 -->
    <QuestionEditDialog
      v-model="showCreateDialog"
      :question="null"
      :tiku-info="tikuInfo"
      @saved="onQuestionSaved"
    />

    <!-- 查看题目对话框 -->
    <QuestionViewDialog
      v-model="showViewDialog"
      :question="selectedQuestion"
    />

    <!-- 删除确认对话框 -->
    <v-dialog v-model="showDeleteDialog" max-width="500">
      <v-card>
        <v-card-title class="text-h5">
          确认删除题目
        </v-card-title>
        <v-card-text>
          确定要删除这道题目吗？此操作不可撤销。
          <div class="mt-2 pa-2 bg-grey-lighten-4 rounded">
            <div class="text-subtitle-2">题目内容：</div>
            <div class="text-body-2">{{ selectedQuestion?.stem }}</div>
          </div>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="showDeleteDialog = false">
            取消
          </v-btn>
          <v-btn
            color="error"
            @click="confirmDelete"
            :loading="deleting"
          >
            删除
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script lang="ts" setup>
import { ref, computed, onMounted } from 'vue'
import type { TikuItem, QuestionItem } from '@/services/api'
import { apiService } from '@/services/api'
import QuestionEditDialog from './QuestionEditDialog.vue'
import QuestionViewDialog from './QuestionViewDialog.vue'

// 题目数据类型定义
interface Question {
  id: number
  subject_id: number
  tiku_id: number
  question_type: number
  stem: string
  option_a?: string
  option_b?: string
  option_c?: string
  option_d?: string
  answer: string
  explanation?: string
  difficulty?: number
  status: string
  created_at?: string
  updated_at?: string
}

interface Props {
  tikuInfo: TikuItem | null
}

interface Emits {
  (e: 'goBack'): void
}

const props = defineProps<Props>()
defineEmits<Emits>()

// 响应式数据
const loading = ref(false)
const deleting = ref(false)
const questions = ref<Question[]>([])
const selectedQuestion = ref<Question | null>(null)
const showEditDialog = ref(false)
const showCreateDialog = ref(false)
const showViewDialog = ref(false)
const showDeleteDialog = ref(false)

// 搜索和筛选
const search = ref('')
const typeFilter = ref<number | null>(null)
const statusFilter = ref<string | null>(null)
const difficultyFilter = ref<number | null>(null)

// 表格配置
const itemsPerPage = ref(20)
const sortBy = ref([{ key: 'id', order: 'desc' as const }])

const itemsPerPageOptions = [
  { value: 10, title: '10条/页' },
  { value: 20, title: '20条/页' },
  { value: 50, title: '50条/页' },
  { value: 100, title: '100条/页' },
  { value: -1, title: '全部显示' }
]

const questionHeaders = [
  { title: 'ID', key: 'id', sortable: true, width: '80px' },
  { title: '题目内容', key: 'stem', sortable: true, width: '300px' },
  { title: '类型', key: 'question_type', sortable: true, width: '100px', align: 'center' as const },
  { title: '难度', key: 'difficulty', sortable: true, width: '120px', align: 'center' as const },
  { title: '状态', key: 'status', sortable: true, width: '100px', align: 'center' as const },
  { title: '创建时间', key: 'created_at', sortable: true, width: '160px' },
  { title: '操作', key: 'actions', sortable: false, width: '200px', align: 'center' as const }
]

// 筛选选项
const questionTypes = [
  { title: '单选题', value: 0 },
  { title: '多选题', value: 5 },
  { title: '判断题', value: 10 }
]

const statusOptions = [
  { title: '启用', value: 'active' },
  { title: '禁用', value: 'inactive' }
]

const difficultyOptions = [
  { title: '难度1星', value: 1 },
  { title: '难度2星', value: 2 },
  { title: '难度3星', value: 3 },
  { title: '难度4星', value: 4 },
  { title: '难度5星', value: 5 }
]

// 计算属性
const filteredQuestions = computed(() => {
  let filtered = questions.value

  // 文本搜索
  if (search.value) {
    const searchTerm = search.value.toLowerCase()
    filtered = filtered.filter(q => 
      q.stem?.toLowerCase().includes(searchTerm) ||
      q.answer?.toLowerCase().includes(searchTerm) ||
      q.explanation?.toLowerCase().includes(searchTerm)
    )
  }

  // 类型筛选
  if (typeFilter.value !== null) {
    filtered = filtered.filter(q => q.question_type === typeFilter.value)
  }

  // 状态筛选
  if (statusFilter.value) {
    filtered = filtered.filter(q => q.status === statusFilter.value)
  }

  // 难度筛选
  if (difficultyFilter.value !== null) {
    filtered = filtered.filter(q => q.difficulty === difficultyFilter.value)
  }

  return filtered
})

// 方法
const loadQuestions = async () => {
  if (!props.tikuInfo) return

  loading.value = true
  try {
    // 调用API获取题目列表
    const response = await apiService.admin.getQuestions(props.tikuInfo.tiku_id)
    
    // 转换后端数据格式为前端期望的格式
    if (response.questions) {
      questions.value = response.questions.map((backendQ: any) => {
        // 从 options_for_practice 对象中提取选项
        const options = backendQ.options_for_practice || {}
        
        // 将后端的 question_type 字符串转换为数字
        let question_type = 0
        if (backendQ.type === '单选题') question_type = 0
        else if (backendQ.type === '多选题') question_type = 5
        else if (backendQ.type === '判断题') question_type = 10
        
        return {
          id: backendQ.db_id || parseInt(backendQ.id.replace('db_', '')) || 0,
          subject_id: backendQ.subject_id,
          tiku_id: backendQ.tiku_id,
          question_type: question_type,
          stem: backendQ.question || '',
          option_a: options.A || '',
          option_b: options.B || '',
          option_c: options.C || '',
          option_d: options.D || '',
          answer: backendQ.answer || '',
          explanation: backendQ.explanation || '',
          difficulty: backendQ.difficulty || 1,
          status: 'active', // 后端返回的都是active状态
          created_at: '',
          updated_at: ''
        }
      })
    } else {
      questions.value = []
    }
  } catch (error) {
    console.error('加载题目失败:', error)
    questions.value = []
  } finally {
    loading.value = false
  }
}

const editQuestion = (question: Question) => {
  selectedQuestion.value = question
  showEditDialog.value = true
}

const viewQuestion = (question: Question) => {
  selectedQuestion.value = question
  showViewDialog.value = true
}

const deleteQuestion = (question: Question) => {
  selectedQuestion.value = question
  showDeleteDialog.value = true
}

const confirmDelete = async () => {
  if (!selectedQuestion.value) return

  deleting.value = true
  try {
    // 这里调用API删除题目
    await apiService.admin.deleteQuestion(selectedQuestion.value.id)
    
    // 删除成功后从列表中移除
    questions.value = questions.value.filter(q => q.id !== selectedQuestion.value!.id)
    showDeleteDialog.value = false
  } catch (error) {
    console.error('删除题目失败:', error)
  } finally {
    deleting.value = false
  }
}

const onQuestionSaved = () => {
  // 题目保存后重新加载列表
  loadQuestions()
  showEditDialog.value = false
  showCreateDialog.value = false
}

// 工具函数
const getTypeName = (type: number) => {
  const typeMap = { 0: '单选题', 5: '多选题', 10: '判断题' }
  return typeMap[type as keyof typeof typeMap] || '未知类型'
}

const getTypeColor = (type: number) => {
  const colorMap = { 0: 'blue', 5: 'green', 10: 'orange' }
  return colorMap[type as keyof typeof colorMap] || 'grey'
}

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

// 生命周期
onMounted(() => {
  loadQuestions()
})
</script>

<style scoped>
.question-management {
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

.question-stem {
  line-height: 1.4;
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