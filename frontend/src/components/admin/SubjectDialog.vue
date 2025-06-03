<template>
  <v-dialog v-model="showDialog" max-width="500px">
    <v-card>
      <v-card-title>
        <span class="text-h5">{{ mode === 'create' ? '创建科目' : '编辑科目' }}</span>
      </v-card-title>

      <v-card-text>
        <v-container>
          <v-row>
            <v-col cols="12">
              <v-text-field
                v-model="subjectName"
                label="科目名称"
                placeholder="请输入科目名称"
                maxlength="50"
                variant="outlined"
                hint="科目名称不能超过50个字符"
                persistent-hint
                @keyup.enter="handleSave"
              ></v-text-field>
            </v-col>
            <v-col cols="12">
              <v-text-field
                v-model="examTime"
                label="考试时间"
                placeholder="请输入考试时间"
                type="datetime-local"
                variant="outlined"
                hint="考试时间格式为YYYY-MM-DDTHH:MM"
                persistent-hint
              ></v-text-field>
            </v-col>
          </v-row>
        </v-container>
      </v-card-text>

      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn color="grey" variant="text" @click="handleCancel">
          取消
        </v-btn>
        <v-btn
          color="primary"
          variant="elevated"
          @click="handleSave"
          :loading="saving"
        >
          {{ mode === 'create' ? '创建' : '保存' }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script lang="ts" setup>
import { ref, watch } from 'vue'

interface Props {
  modelValue: boolean
  mode: 'create' | 'edit'
  subject?: any
  saving: boolean
}

interface Emits {
  (e: 'update:modelValue', value: boolean): void
  (e: 'save', name: string, examTime: string): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const showDialog = ref(props.modelValue)
const subjectName = ref('')
const examTime = ref('')

// 监听外部传入的显示状态
watch(() => props.modelValue, (newVal) => {
  showDialog.value = newVal
  if (newVal && props.subject && props.mode === 'edit') {
    // 编辑模式时填充现有数据
    subjectName.value = props.subject.subject_name || ''
    examTime.value = props.subject.exam_time || ''
  }
})

// 监听内部显示状态变化
watch(showDialog, (newVal) => {
  if (newVal !== props.modelValue) {
    emit('update:modelValue', newVal)
  }
})

const handleCancel = () => {
  showDialog.value = false
  resetForm()
}

const handleSave = () => {
  if (!subjectName.value.trim()) {
    // 这里应该显示错误提示，但为了简化暂时忽略
    return
  }
  emit('save', subjectName.value.trim(), examTime.value)
}

const resetForm = () => {
  subjectName.value = ''
  examTime.value = ''
}

// 当对话框关闭时重置表单
watch(showDialog, (newVal) => {
  if (!newVal) {
    resetForm()
  }
})
</script>

<style scoped>
.v-card {
  border-radius: 16px;
}

.v-card-title {
  padding: 24px 24px 16px;
  font-size: 1.25rem;
  font-weight: 600;
  color: #1e293b;
}

.v-card-text {
  padding: 0 24px 16px;
}

.v-card-actions {
  padding: 16px 24px 24px;
  gap: 12px;
}
</style> 