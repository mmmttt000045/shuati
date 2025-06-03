<template>
  <v-dialog v-model="showDialog" max-width="500px">
    <v-card>
      <v-card-title>
        <span class="text-h5">上传题库文件</span>
      </v-card-title>

      <v-card-text>
        <v-container>
          <v-row>
            <v-col cols="12">
              <v-text-field
                v-model="tikuName"
                label="题库名称"
                placeholder="留空将使用文件名"
                maxlength="50"
                variant="outlined"
                hint="题库名称不能超过50个字符"
                persistent-hint
              ></v-text-field>
            </v-col>
            <v-col cols="12">
              <v-file-input
                accept=".xlsx,.xls"
                @change="handleFileSelect"
                label="选择Excel文件"
                variant="outlined"
                prepend-icon="mdi-paperclip"
                hint="支持 .xlsx 和 .xls 格式的Excel文件"
                persistent-hint
                show-size
              ></v-file-input>
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
          @click="handleUpload"
          :disabled="!selectedFile"
          :loading="uploading"
        >
          上传
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script lang="ts" setup>
import { ref, watch } from 'vue'
import { useToast } from 'vue-toastification'

interface Props {
  modelValue: boolean
  uploading: boolean
}

interface Emits {
  (e: 'update:modelValue', value: boolean): void
  (e: 'upload', file: File, tikuName: string): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const toast = useToast()

const showDialog = ref(props.modelValue)
const tikuName = ref('')
const selectedFile = ref<File | null>(null)

// 监听外部传入的显示状态
watch(() => props.modelValue, (newVal) => {
  showDialog.value = newVal
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

const handleUpload = () => {
  if (!selectedFile.value) {
    toast.error('请选择文件')
    return
  }
  emit('upload', selectedFile.value, tikuName.value)
}

const handleFileSelect = (event: Event) => {
  const target = event.target as HTMLInputElement
  if (target.files && target.files.length > 0) {
    const file = target.files[0]
    
    // 验证文件类型
    if (!file.name.match(/\.(xlsx?|xls)$/i)) {
      toast.error('请选择Excel文件（.xlsx 或 .xls）')
      target.value = '' // 清除选择
      return
    }
    
    // 验证文件大小（限制为50MB）
    if (file.size > 50 * 1024 * 1024) {
      toast.error('文件大小不能超过50MB')
      target.value = '' // 清除选择
      return
    }
    
    selectedFile.value = file
    
    // 如果没有输入题库名称，使用文件名（去掉扩展名）
    if (!tikuName.value) {
      const fileName = file.name
      tikuName.value = fileName.replace(/\.(xlsx?|xls)$/i, '')
    }
  } else {
    selectedFile.value = null
  }
}

const resetForm = () => {
  tikuName.value = ''
  selectedFile.value = null
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