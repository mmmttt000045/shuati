<template>
  <v-dialog v-model="dialog" max-width="800">
    <v-card v-if="question">
      <v-card-title class="text-h5 bg-info text-white">
        <div class="d-flex align-center">
          <v-icon class="me-2">mdi-eye</v-icon>
          题目详情
        </div>
      </v-card-title>

      <v-card-text class="pt-4">
        <v-container>
          <!-- 基本信息 -->
          <v-row class="mb-4">
            <v-col cols="12">
              <div class="d-flex flex-wrap align-center mb-3">
                <v-chip
                  size="small"
                  :color="getTypeColor(question.question_type)"
                  class="me-2 mb-2"
                >
                  {{ getTypeName(question.question_type) }}
                </v-chip>
                <v-chip
                  size="small"
                  :color="question.status === 'active' ? 'success' : 'error'"
                  class="me-2 mb-2"
                >
                  {{ question.status === 'active' ? '启用' : '禁用' }}
                </v-chip>
                <div class="d-flex align-center me-2 mb-2">
                  <span class="text-caption me-1">难度：</span>
                  <v-rating
                    :model-value="question.difficulty || 1"
                    readonly
                    size="small"
                    density="compact"
                    length="5"
                  />
                </div>
              </div>
            </v-col>
          </v-row>

          <!-- 题目内容 -->
          <v-row class="mb-4">
            <v-col cols="12">
              <div class="text-h6 mb-2">题目内容</div>
              <v-card variant="outlined" class="pa-3">
                <div class="text-body-1" style="white-space: pre-wrap; line-height: 1.6;">
                  {{ question.stem }}
                </div>
              </v-card>
            </v-col>
          </v-row>

          <!-- 选项（单选题和多选题） -->
          <v-row v-if="showOptions" class="mb-4">
            <v-col cols="12">
              <div class="text-h6 mb-2">选项</div>
              <v-list lines="two" density="compact">
                <v-list-item
                  v-if="question.option_a"
                  :class="{ 'bg-green-lighten-4': isCorrectOption('A') }"
                >
                  <template v-slot:prepend>
                    <v-avatar size="small" :color="isCorrectOption('A') ? 'success' : 'default'">
                      A
                    </v-avatar>
                  </template>
                  <v-list-item-title>{{ question.option_a }}</v-list-item-title>
                </v-list-item>
                
                <v-list-item
                  v-if="question.option_b"
                  :class="{ 'bg-green-lighten-4': isCorrectOption('B') }"
                >
                  <template v-slot:prepend>
                    <v-avatar size="small" :color="isCorrectOption('B') ? 'success' : 'default'">
                      B
                    </v-avatar>
                  </template>
                  <v-list-item-title>{{ question.option_b }}</v-list-item-title>
                </v-list-item>
                
                <v-list-item
                  v-if="question.option_c"
                  :class="{ 'bg-green-lighten-4': isCorrectOption('C') }"
                >
                  <template v-slot:prepend>
                    <v-avatar size="small" :color="isCorrectOption('C') ? 'success' : 'default'">
                      C
                    </v-avatar>
                  </template>
                  <v-list-item-title>{{ question.option_c }}</v-list-item-title>
                </v-list-item>
                
                <v-list-item
                  v-if="question.option_d"
                  :class="{ 'bg-green-lighten-4': isCorrectOption('D') }"
                >
                  <template v-slot:prepend>
                    <v-avatar size="small" :color="isCorrectOption('D') ? 'success' : 'default'">
                      D
                    </v-avatar>
                  </template>
                  <v-list-item-title>{{ question.option_d }}</v-list-item-title>
                </v-list-item>
              </v-list>
            </v-col>
          </v-row>

          <!-- 正确答案 -->
          <v-row class="mb-4">
            <v-col cols="12">
              <div class="text-h6 mb-2">正确答案</div>
              <v-card variant="outlined" class="pa-3 bg-green-lighten-5">
                <div class="d-flex align-center">
                  <v-icon color="success" class="me-2">mdi-check-circle</v-icon>
                  <span class="text-h6 text-success">{{ formatAnswer(question.answer, question.question_type) }}</span>
                </div>
              </v-card>
            </v-col>
          </v-row>

          <!-- 答案解析 -->
          <v-row v-if="question.explanation" class="mb-4">
            <v-col cols="12">
              <div class="text-h6 mb-2">答案解析</div>
              <v-card variant="outlined" class="pa-3 bg-blue-lighten-5">
                <div class="text-body-1" style="white-space: pre-wrap; line-height: 1.6;">
                  {{ question.explanation }}
                </div>
              </v-card>
            </v-col>
          </v-row>

          <!-- 其他信息 -->
          <v-row>
            <v-col cols="12">
              <div class="text-h6 mb-2">其他信息</div>
              <v-table density="compact">
                <tbody>
                  <tr>
                    <td class="text-subtitle-2" style="width: 120px;">题目ID</td>
                    <td>{{ question.id }}</td>
                  </tr>
                  <tr>
                    <td class="text-subtitle-2">科目ID</td>
                    <td>{{ question.subject_id }}</td>
                  </tr>
                  <tr>
                    <td class="text-subtitle-2">题库ID</td>
                    <td>{{ question.tiku_id }}</td>
                  </tr>
                  <tr v-if="question.created_at">
                    <td class="text-subtitle-2">创建时间</td>
                    <td>{{ formatDate(question.created_at) }}</td>
                  </tr>
                  <tr v-if="question.updated_at">
                    <td class="text-subtitle-2">更新时间</td>
                    <td>{{ formatDate(question.updated_at) }}</td>
                  </tr>
                </tbody>
              </v-table>
            </v-col>
          </v-row>
        </v-container>
      </v-card-text>

      <v-card-actions class="px-6 pb-4">
        <v-spacer />
        <v-btn @click="dialog = false">
          关闭
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script lang="ts" setup>
import { computed } from 'vue'

// 题目数据类型定义
interface Question {
  id?: number
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
  modelValue: boolean
  question: Question | null
}

interface Emits {
  (e: 'update:modelValue', value: boolean): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

// 计算属性
const dialog = computed({
  get: () => props.modelValue,
  set: (value: boolean) => emit('update:modelValue', value)
})

const showOptions = computed(() => {
  return props.question?.question_type === 0 || props.question?.question_type === 5
})

// 方法
const getTypeName = (type: number) => {
  const typeMap = { 0: '单选题', 5: '多选题', 10: '判断题' }
  return typeMap[type as keyof typeof typeMap] || '未知类型'
}

const getTypeColor = (type: number) => {
  const colorMap = { 0: 'blue', 5: 'green', 10: 'orange' }
  return colorMap[type as keyof typeof colorMap] || 'grey'
}

const isCorrectOption = (option: string) => {
  return props.question?.answer.includes(option) || false
}

const formatAnswer = (answer: string, questionType: number) => {
  if (questionType === 10) {
    // 判断题
    return answer === 'A' ? '正确' : '错误'
  } else if (questionType === 5) {
    // 多选题
    return answer.split('').join(', ')
  } else {
    // 单选题
    return answer
  }
}

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
.v-card-title {
  position: sticky;
  top: 0;
  z-index: 1;
}
</style> 