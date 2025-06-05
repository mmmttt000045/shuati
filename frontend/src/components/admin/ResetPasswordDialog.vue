<template>
  <v-dialog v-model="localShow" max-width="500px" persistent>
    <v-card class="reset-password-dialog">
      <v-card-title class="dialog-title">
        <span class="text-h5">🔑 重置用户密码</span>
      </v-card-title>

      <v-card-text>
        <div class="user-info">
          <p><strong>用户：</strong>{{ user?.username }}</p>
          <p><strong>用户ID：</strong>{{ user?.id }}</p>
        </div>

        <v-form ref="form" v-model="valid" @submit.prevent="handleReset">
          <v-text-field
            v-model="newPassword"
            label="新密码"
            :type="showPassword ? 'text' : 'password'"
            :append-inner-icon="showPassword ? 'mdi-eye' : 'mdi-eye-off'"
            @click:append-inner="showPassword = !showPassword"
            :rules="passwordRules"
            variant="outlined"
            density="comfortable"
            placeholder="请输入新密码"
            clearable
            autocomplete="new-password"
          ></v-text-field>

          <v-text-field
            v-model="confirmPassword"
            label="确认密码"
            :type="showConfirmPassword ? 'text' : 'password'"
            :append-inner-icon="showConfirmPassword ? 'mdi-eye' : 'mdi-eye-off'"
            @click:append-inner="showConfirmPassword = !showConfirmPassword"
            :rules="confirmPasswordRules"
            variant="outlined"
            density="comfortable"
            placeholder="请再次输入新密码"
            clearable
            autocomplete="new-password"
          ></v-text-field>
        </v-form>

        <v-alert
          v-if="error"
          type="error"
          variant="tonal"
          class="mt-4"
        >
          {{ error }}
        </v-alert>
      </v-card-text>

      <v-card-actions class="justify-end pa-6">
        <v-btn
          variant="outlined"
          @click="handleCancel"
          :disabled="loading"
        >
          取消
        </v-btn>
        <v-btn
          color="primary"
          variant="elevated"
          @click="handleReset"
          :loading="loading"
          :disabled="!valid"
        >
          重置密码
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script lang="ts" setup>
import { ref, computed, watch } from 'vue'

interface Props {
  modelValue: boolean
  user?: any
  loading?: boolean
}

interface Emits {
  (e: 'update:modelValue', value: boolean): void
  (e: 'reset', password: string): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

// 表单数据
const form = ref()
const valid = ref(false)
const newPassword = ref('')
const confirmPassword = ref('')
const showPassword = ref(false)
const showConfirmPassword = ref(false)
const error = ref('')

// 计算属性
const localShow = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value)
})

// 表单验证规则
const passwordRules = [
  (v: string) => !!v || '请输入新密码',
  (v: string) => v.length >= 6 || '密码长度至少6位',
  (v: string) => v.length <= 64 || '密码长度不能超过64位',
]

const confirmPasswordRules = [
  (v: string) => !!v || '请确认密码',
  (v: string) => v === newPassword.value || '两次输入的密码不一致',
]

// 监听对话框显示状态
watch(localShow, (newValue) => {
  if (newValue) {
    resetForm()
  }
})

// 重置表单
const resetForm = () => {
  newPassword.value = ''
  confirmPassword.value = ''
  showPassword.value = false
  showConfirmPassword.value = false
  error.value = ''
  if (form.value) {
    form.value.resetValidation()
  }
}

// 处理重置
const handleReset = async () => {
  error.value = ''
  
  if (!form.value) return
  
  const { valid: isValid } = await form.value.validate()
  if (!isValid) return

  if (newPassword.value !== confirmPassword.value) {
    error.value = '两次输入的密码不一致'
    return
  }

  emit('reset', newPassword.value)
}

// 处理取消
const handleCancel = () => {
  localShow.value = false
}
</script>

<style scoped>
.reset-password-dialog {
  border-radius: 16px;
}

.dialog-title {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 1.5rem 1.5rem 1rem 1.5rem;
}

.user-info {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 1rem;
  margin-bottom: 1.5rem;
}

.user-info p {
  margin: 0.25rem 0;
  color: #475569;
}

.v-card-text {
  padding: 1.5rem !important;
}

.v-card-actions {
  border-top: 1px solid #e2e8f0;
  background: #f8fafc;
}
</style> 