<template>
  <v-dialog v-model="dialog" max-width="900" persistent>
    <v-card>
      <v-card-title class="text-h5 bg-primary text-white">
        <div class="d-flex align-center">
          <v-icon class="me-2">mdi-pencil</v-icon>
          {{ isEdit ? '编辑题目' : '新增题目' }}
        </div>
      </v-card-title>

      <v-form ref="form" v-model="valid" @submit.prevent="handleSubmit">
        <v-card-text class="pt-4">
          <v-container>
            <v-row>
              <!-- 题目类型 -->
              <v-col cols="12" md="6">
                <v-select
                  v-model="formData.question_type"
                  :items="questionTypes"
                  label="题目类型"
                  variant="outlined"
                  :rules="[rules.required]"
                  @update:model-value="onTypeChange"
                />
              </v-col>

              <!-- 难度 -->
              <v-col cols="12" md="6">
                <v-select
                  v-model="formData.difficulty"
                  :items="difficultyOptions"
                  label="难度等级"
                  variant="outlined"
                  :rules="[rules.required]"
                />
              </v-col>

              <!-- 题目内容 -->
              <v-col cols="12">
                <v-textarea
                  v-model="formData.stem"
                  label="题目内容"
                  variant="outlined"
                  :rules="[rules.required]"
                  rows="3"
                  auto-grow
                />
              </v-col>

              <!-- 选项（单选题和多选题） -->
              <template v-if="showOptions">
                <v-col cols="12" md="6">
                  <v-textarea
                    v-model="formData.option_a"
                    label="选项A"
                    variant="outlined"
                    :rules="showOptions ? [rules.required] : []"
                    rows="2"
                    auto-grow
                  />
                </v-col>
                <v-col cols="12" md="6">
                  <v-textarea
                    v-model="formData.option_b"
                    label="选项B"
                    variant="outlined"
                    :rules="showOptions ? [rules.required] : []"
                    rows="2"
                    auto-grow
                  />
                </v-col>
                <v-col cols="12" md="6">
                  <v-textarea
                    v-model="formData.option_c"
                    label="选项C"
                    variant="outlined"
                    rows="2"
                    auto-grow
                  />
                </v-col>
                <v-col cols="12" md="6">
                  <v-textarea
                    v-model="formData.option_d"
                    label="选项D"
                    variant="outlined"
                    rows="2"
                    auto-grow
                  />
                </v-col>
              </template>

              <!-- 正确答案 -->
              <v-col cols="12" md="6">
                <div v-if="formData.question_type === 0">
                  <!-- 单选题答案 -->
                  <v-select
                    v-model="formData.answer"
                    :items="singleChoiceOptions"
                    label="正确答案"
                    variant="outlined"
                    :rules="[rules.required]"
                  />
                </div>
                <div v-else-if="formData.question_type === 5">
                  <!-- 多选题答案 -->
                  <v-select
                    v-model="multipleAnswers"
                    :items="multipleChoiceOptions"
                    label="正确答案（可多选）"
                    variant="outlined"
                    multiple
                    chips
                    :rules="[rules.required]"
                    @update:model-value="updateMultipleAnswers"
                  />
                </div>
                <div v-else-if="formData.question_type === 10">
                  <!-- 判断题答案 -->
                  <v-select
                    v-model="formData.answer"
                    :items="judgmentOptions"
                    label="正确答案"
                    variant="outlined"
                    :rules="[rules.required]"
                  />
                </div>
              </v-col>

              <!-- 状态 -->
              <v-col cols="12" md="6">
                <v-select
                  v-model="formData.status"
                  :items="statusOptions"
                  label="状态"
                  variant="outlined"
                  :rules="[rules.required]"
                />
              </v-col>

              <!-- 解析 -->
              <v-col cols="12">
                <v-textarea
                  v-model="formData.explanation"
                  label="答案解析（可选）"
                  variant="outlined"
                  rows="3"
                  auto-grow
                />
              </v-col>
            </v-row>
          </v-container>
        </v-card-text>

        <v-card-actions class="px-6 pb-4">
          <v-spacer />
          <v-btn @click="handleCancel">
            取消
          </v-btn>
          <v-btn
            type="submit"
            color="primary"
            :loading="loading"
            :disabled="!(valid || isFormValid)"
          >
            {{ isEdit ? '更新' : '创建' }}
          </v-btn>
        </v-card-actions>
      </v-form>
    </v-card>
  </v-dialog>
</template>

<script lang="ts" setup>
import { ref, computed, watch, nextTick } from 'vue'
import type { TikuItem, QuestionCreateData, QuestionUpdateData } from '@/services/api'
import { apiService } from '@/services/api'

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
  difficulty: number
  status: string
}

interface Props {
  modelValue: boolean
  question: Question | null
  tikuInfo: TikuItem | null
}

interface Emits {
  (e: 'update:modelValue', value: boolean): void
  (e: 'saved'): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

// 响应式数据
const form = ref()
const valid = ref(false)
const loading = ref(false)
const multipleAnswers = ref<string[]>([])

// 表单数据
const formData = ref<Question>({
  subject_id: 0,
  tiku_id: 0,
  question_type: 0,
  stem: '',
  option_a: '',
  option_b: '',
  option_c: '',
  option_d: '',
  answer: '',
  explanation: '',
  difficulty: 1,
  status: 'active'
})

// 计算属性
const dialog = computed({
  get: () => props.modelValue,
  set: (value: boolean) => emit('update:modelValue', value)
})

const isEdit = computed(() => !!props.question?.id)

const showOptions = computed(() => {
  return formData.value.question_type === 0 || formData.value.question_type === 5
})

// 添加计算属性来检查表单是否有效
const isFormValid = computed(() => {
  // 检查基本必填字段
  if (!formData.value.stem?.trim()) return false
  if (formData.value.difficulty === undefined || formData.value.difficulty < 1) return false
  if (!formData.value.status) return false
  if (!formData.value.answer?.trim()) return false
  
  // 如果是单选题或多选题，检查选项
  if (showOptions.value) {
    if (!formData.value.option_a?.trim()) return false
    if (!formData.value.option_b?.trim()) return false
  }
  
  return true
})

// 选项配置
const questionTypes = [
  { title: '单选题', value: 0 },
  { title: '多选题', value: 5 },
  { title: '判断题', value: 10 }
]

const difficultyOptions = [
  { title: '难度1星', value: 1 },
  { title: '难度2星', value: 2 },
  { title: '难度3星', value: 3 },
  { title: '难度4星', value: 4 },
  { title: '难度5星', value: 5 }
]

const statusOptions = [
  { title: '启用', value: 'active' },
  { title: '禁用', value: 'inactive' }
]

const singleChoiceOptions = [
  { title: 'A', value: 'A' },
  { title: 'B', value: 'B' },
  { title: 'C', value: 'C' },
  { title: 'D', value: 'D' }
]

const multipleChoiceOptions = [
  { title: 'A', value: 'A' },
  { title: 'B', value: 'B' },
  { title: 'C', value: 'C' },
  { title: 'D', value: 'D' }
]

const judgmentOptions = [
  { title: '正确 (A)', value: 'A' },
  { title: '错误 (B)', value: 'B' }
]

// 验证规则
const rules = {
  required: (value: any) => {
    if (value === null || value === undefined) {
      return '此项为必填项'
    }
    if (typeof value === 'string') {
      return value.trim() !== '' || '此项为必填项'
    }
    if (typeof value === 'number') {
      return !isNaN(value) || '此项为必填项'
    }
    return !!value || '此项为必填项'
  }
}

// 手动触发表单验证
const triggerValidation = () => {
  nextTick(() => {
    if (form.value) {
      form.value.validate()
    }
  })
}

// 方法
const resetForm = () => {
  if (props.question) {
    // 编辑模式，复制题目数据
    formData.value = { ...props.question }
    
    // 处理多选题答案
    if (props.question.question_type === 5 && props.question.answer) {
      multipleAnswers.value = props.question.answer.split('').filter(a => a.match(/[A-D]/))
    } else {
      multipleAnswers.value = []
    }
    
    // 确保必要字段有默认值
    if (!formData.value.status) {
      formData.value.status = 'active'
    }
    if (!formData.value.difficulty) {
      formData.value.difficulty = 1
    }
  } else {
    // 新增模式，使用默认值
    formData.value = {
      subject_id: props.tikuInfo?.subject_id || 0,
      tiku_id: props.tikuInfo?.tiku_id || 0,
      question_type: 0,
      stem: '',
      option_a: '',
      option_b: '',
      option_c: '',
      option_d: '',
      answer: '',
      explanation: '',
      difficulty: 1,
      status: 'active'
    }
    multipleAnswers.value = []
  }
  
  // 重置表单验证状态
  if (form.value) {
    form.value.resetValidation()
  }
  
  // 延迟触发验证，确保数据已经绑定
  setTimeout(() => {
    triggerValidation()
  }, 100)
}

const onTypeChange = () => {
  // 切换题目类型时清空答案
  formData.value.answer = ''
  multipleAnswers.value = []
  
  // 如果切换到判断题，清空选项
  if (formData.value.question_type === 10) {
    formData.value.option_a = ''
    formData.value.option_b = ''
    formData.value.option_c = ''
    formData.value.option_d = ''
  }
}

const updateMultipleAnswers = (answers: string[]) => {
  // 将多选答案数组转换为字符串
  formData.value.answer = answers.sort().join('')
}

const handleSubmit = async () => {
  // 使用自定义验证逻辑而不是只依赖Vuetify验证
  if (!isFormValid.value) {
    console.log('表单验证失败')
    return
  }

  loading.value = true
  try {
    // 这里调用API保存题目
    console.log('保存题目:', formData.value)
    
    // 模拟API调用
    await new Promise(resolve => setTimeout(resolve, 1000))
    
    emit('saved')
    handleCancel()
  } catch (error) {
    console.error('保存题目失败:', error)
  } finally {
    loading.value = false
  }
}

const handleCancel = () => {
  dialog.value = false
  nextTick(() => {
    form.value?.reset()
  })
}

// 监听表单数据变化，及时更新验证状态
watch(() => formData.value, () => {
  triggerValidation()
}, { deep: true })

// 监听对话框状态
watch(() => props.modelValue, (newValue) => {
  if (newValue) {
    resetForm()
    // 在下一个tick中触发表单验证
    triggerValidation()
  }
})

watch(() => formData.value.question_type, () => {
  // 题目类型改变时重新验证表单
  triggerValidation()
})
</script>

<style scoped>
.v-card-title {
  position: sticky;
  top: 0;
  z-index: 1;
}
</style> 