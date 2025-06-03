<template>
  <v-dialog v-model="showDialog" max-width="500px" persistent>
    <v-card>
      <v-card-title class="d-flex align-center">
        <v-icon color="warning" class="mr-2" size="28">mdi-account-alert</v-icon>
        <span class="text-h5">确认权限变更</span>
      </v-card-title>

      <v-card-text>
        <v-container>
          <v-alert
            type="warning"
            variant="tonal"
            prominent
            border="start"
            class="mb-4"
          >
            <v-alert-title>⚠️ 重要操作确认</v-alert-title>
            <div class="mt-2">
              权限变更是敏感操作，请仔细确认以下信息：
            </div>
          </v-alert>
          
          <v-row>
            <v-col cols="12">
              <v-card variant="outlined" class="pa-4">
                <div class="permission-change-info">
                  <div class="info-row">
                    <v-icon color="primary" class="mr-2">mdi-account</v-icon>
                    <span class="info-label">用户名：</span>
                    <span class="info-value username">{{ permissionData?.username }}</span>
                  </div>
                  
                  <v-divider class="my-3"></v-divider>
                  
                  <div class="info-row">
                    <v-icon color="info" class="mr-2">mdi-account-badge</v-icon>
                    <span class="info-label">当前权限：</span>
                    <v-chip 
                      :color="getModelColor(permissionData?.currentModel)" 
                      size="small" 
                      variant="flat"
                      class="ml-2"
                    >
                      {{ getModelName(permissionData?.currentModel) }}
                    </v-chip>
                  </div>
                  
                  <div class="info-row mt-2">
                    <v-icon color="success" class="mr-2">mdi-account-arrow-right</v-icon>
                    <span class="info-label">变更为：</span>
                    <v-chip 
                      :color="getModelColor(permissionData?.newModel)" 
                      size="small" 
                      variant="flat"
                      class="ml-2"
                    >
                      {{ getModelName(permissionData?.newModel) }}
                    </v-chip>
                  </div>
                </div>
              </v-card>
            </v-col>
            
            <v-col cols="12" v-if="permissionData?.newModel === 10">
              <v-alert
                type="error"
                variant="tonal"
                density="compact"
                class="text-caption"
              >
                <v-alert-title class="text-body-2">🔥 超级管理员权限</v-alert-title>
                <div class="mt-1">
                  该用户将获得系统最高权限，包括用户管理、系统配置等所有功能的访问权限。
                </div>
              </v-alert>
            </v-col>
            
            <v-col cols="12" v-else-if="permissionData?.newModel === 5">
              <v-alert
                type="info"
                variant="tonal"
                density="compact"
                class="text-caption"
              >
                <v-alert-title class="text-body-2">💎 VIP用户权限</v-alert-title>
                <div class="mt-1">
                  该用户将获得VIP功能访问权限，享受更好的服务体验。
                </div>
              </v-alert>
            </v-col>
            
            <v-col cols="12" v-else-if="permissionData?.newModel === 0">
              <v-alert
                type="info"
                variant="tonal"
                density="compact"
                class="text-caption"
              >
                <v-alert-title class="text-body-2">👤 普通用户权限</v-alert-title>
                <div class="mt-1">
                  该用户将只能访问基础功能，无法使用高级功能。
                </div>
              </v-alert>
            </v-col>
          </v-row>
        </v-container>
      </v-card-text>

      <v-card-actions class="px-6 pb-4">
        <v-spacer></v-spacer>
        <v-btn 
          color="grey" 
          variant="text" 
          @click="handleCancel"
          :disabled="updating"
        >
          取消
        </v-btn>
        <v-btn
          :color="permissionData?.newModel === 10 ? 'error' : 'primary'"
          variant="elevated"
          @click="handleConfirm"
          :loading="updating"
        >
          <v-icon class="mr-1" size="16">mdi-check-bold</v-icon>
          确认变更
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script lang="ts" setup>
import { ref, watch } from 'vue'

interface PermissionData {
  userId: number
  username: string
  currentModel: number
  newModel: number
}

interface Props {
  modelValue: boolean
  permissionData: PermissionData | null
  updating: boolean
}

interface Emits {
  (e: 'update:modelValue', value: boolean): void
  (e: 'confirm'): void
  (e: 'cancel'): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const showDialog = ref(props.modelValue)

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
  emit('cancel')
}

const handleConfirm = () => {
  emit('confirm')
}

const getModelColor = (model?: number) => {
  switch (model) {
    case 10:
      return 'error'
    case 5:
      return 'info'
    case 0:
      return 'success'
    default:
      return 'default'
  }
}

const getModelName = (model?: number) => {
  switch (model) {
    case 10:
      return 'ROOT用户'
    case 5:
      return 'VIP用户'
    case 0:
      return '普通用户'
    default:
      return '未知'
  }
}
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

.permission-change-info {
  font-size: 0.95rem;
}

.info-row {
  display: flex;
  align-items: center;
  margin-bottom: 0.75rem;
}

.info-row:last-child {
  margin-bottom: 0;
}

.info-label {
  font-weight: 500;
  color: #374151;
  min-width: 80px;
}

.info-value {
  color: #1e293b;
  margin-left: 0.5rem;
}

.info-value.username {
  font-weight: 600;
  color: #3b82f6;
  background: #eff6ff;
  padding: 0.25rem 0.75rem;
  border-radius: 6px;
  border: 1px solid #bfdbfe;
}
</style> 