<template>
  <v-dialog v-model="showDialog" max-width="500px">
    <v-card>
      <v-card-title>
        <span class="text-h5">创建新邀请码</span>
      </v-card-title>

      <v-card-text>
        <v-container>
          <v-row>
            <v-col cols="12">
              <v-text-field
                v-model="invitationCode"
                label="邀请码（可选）"
                placeholder="留空自动生成"
                maxlength="64"
                variant="outlined"
                hint="留空将自动生成12位随机邀请码"
                persistent-hint
              ></v-text-field>
            </v-col>
            <v-col cols="12">
              <v-text-field
                v-model="expireDays"
                label="有效期（天）"
                placeholder="留空表示永不过期"
                type="number"
                :min="1"
                :max="365"
                variant="outlined"
                hint="留空表示永不过期"
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
          @click="handleCreate"
          :loading="creating"
        >
          创建
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script lang="ts" setup>
import { ref, watch } from 'vue'

interface Props {
  modelValue: boolean
  creating: boolean
}

interface Emits {
  (e: 'update:modelValue', value: boolean): void
  (e: 'create', code: string | undefined, expireDays: number | undefined): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const showDialog = ref(props.modelValue)
const invitationCode = ref('')
const expireDays = ref<number | null>(null)

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

const handleCreate = () => {
  const code = invitationCode.value.trim() || undefined
  const days = expireDays.value || undefined
  emit('create', code, days)
}

const resetForm = () => {
  invitationCode.value = ''
  expireDays.value = null
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