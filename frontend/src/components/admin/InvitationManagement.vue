<template>
  <div class="control-section">
    <div class="section-header">
      <h2 class="section-title">🎫 邀请码管理</h2>
      <div class="section-actions">
        <v-btn
          color="primary"
          prepend-icon="mdi-plus"
          @click="$emit('showCreateDialog')"
          variant="elevated"
        >
          创建邀请码
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
      :headers="invitationHeaders"
      :items="filteredInvitations"
      :loading="loading"
      :search="invitationSearch"
      :items-per-page="invitationItemsPerPage"
      :sort-by="invitationSortBy"
      :items-per-page-options="itemsPerPageOptions"
      :items-per-page-text="'每页显示：'"
      class="elevation-2"
      density="comfortable"
      :no-data-text="'暂无邀请码'"
      :no-results-text="'没有找到匹配的邀请码'"
    >
      <!-- 搜索槽 -->
      <template v-slot:top>
        <div class="pa-4">
          <v-text-field
            v-model="invitationSearch"
            label="搜索邀请码..."
            prepend-inner-icon="mdi-magnify"
            variant="outlined"
            hide-details
            clearable
            density="compact"
          ></v-text-field>
        </div>
      </template>

      <!-- 邀请码列 -->
      <template v-slot:item.code="{ item }">
        <div class="d-flex align-center">
          <code class="text-caption mr-2">{{ item.code }}</code>
          <v-btn
            icon="mdi-content-copy"
            size="x-small"
            variant="text"
            @click="copyInvitationCode(item.code)"
            title="复制邀请码"
          ></v-btn>
        </div>
      </template>

      <!-- 状态列 -->
      <template v-slot:item.is_used="{ item }">
        <v-chip
          :color="item.is_used ? 'warning' : 'success'"
          size="small"
          variant="flat"
        >
          {{ item.is_used ? '已使用' : '可用' }}
        </v-chip>
      </template>

      <!-- 使用者列 -->
      <template v-slot:item.used_by_username="{ item }">
        {{ item.used_by_username || '-' }}
      </template>

      <!-- 创建时间列 -->
      <template v-slot:item.created_at="{ item }">
        <span class="text-caption">{{ formatDate(item.created_at) }}</span>
      </template>

      <!-- 使用状态列 -->
      <template v-slot:item.used_time="{ item }">
        <span class="text-caption">{{ item.is_used ? '已使用' : '未使用' }}</span>
      </template>

      <!-- 过期时间列 -->
      <template v-slot:item.expires_at="{ item }">
        <span class="text-caption">{{ item.expires_at ? formatDate(item.expires_at) : '永不过期' }}</span>
      </template>

      <!-- 操作列 -->
      <template v-slot:item.actions="{ item }">
        <v-btn
          v-if="!item.is_used"
          color="error"
          size="small"
          variant="elevated"
          @click="$emit('deleteInvitation', item)"
          :disabled="deletingInvitation"
        >
          删除
        </v-btn>
        <span v-else class="text-disabled">已使用</span>
      </template>
    </v-data-table>
  </div>
</template>

<script lang="ts" setup>
import { ref, computed } from 'vue'
import { useToast } from 'vue-toastification'
import type { AdminInvitation } from '@/services/api'

interface Props {
  invitations: AdminInvitation[]
  loading: boolean
  deletingInvitation: boolean
}

interface Emits {
  (e: 'refresh'): void
  (e: 'showCreateDialog'): void
  (e: 'deleteInvitation', invitation: AdminInvitation): void
}

const props = defineProps<Props>()
defineEmits<Emits>()

const toast = useToast()

// 表格配置
const invitationSearch = ref('')
const invitationItemsPerPage = ref(20)
const invitationSortBy = ref([{ key: 'id', order: 'desc' as const }])

const itemsPerPageOptions = [
  { value: 10, title: '10条/页' },
  { value: 20, title: '20条/页' },
  { value: 50, title: '50条/页' },
  { value: 100, title: '100条/页' },
  { value: -1, title: '全部显示' }
]

const invitationHeaders = [
  { title: 'ID', key: 'id', sortable: true, width: '80px' },
  { title: '邀请码', key: 'code', sortable: false, width: '180px' },
  { title: '状态', key: 'is_used', sortable: false, width: '100px' },
  { title: '使用者', key: 'used_by_username', sortable: false, width: '120px' },
  { title: '创建时间', key: 'created_at', sortable: true, width: '160px' },
  { title: '使用状态', key: 'used_time', sortable: false, width: '160px' },
  { title: '过期时间', key: 'expires_at', sortable: false, width: '160px' },
  { title: '操作', key: 'actions', sortable: false, width: '100px', align: 'center' as const }
]

// 计算属性
const filteredInvitations = computed(() => {
  if (!invitationSearch.value) return props.invitations
  const searchTerm = invitationSearch.value.toLowerCase()
  return props.invitations.filter((invitation: AdminInvitation) => 
    invitation.code?.toLowerCase().includes(searchTerm) ||
    (invitation.used_by_username && invitation.used_by_username.toLowerCase().includes(searchTerm))
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

const formatUsedTime = (dateString?: string) => {
  if (!dateString) return '未使用'
  try {
    return new Date(dateString).toLocaleString('zh-CN')
  } catch {
    return '格式错误'
  }
}

const copyInvitationCode = async (code: string) => {
  try {
    // 首先尝试使用现代的 Clipboard API
    if (navigator.clipboard && navigator.clipboard.writeText) {
      await navigator.clipboard.writeText(code)
      toast.success('邀请码已复制到剪贴板')
      return
    }
    
    // 如果 Clipboard API 不可用，使用 Selection API 作为后备方案
    const textArea = document.createElement('textarea')
    textArea.value = code
    textArea.style.position = 'fixed'
    textArea.style.left = '-999999px'
    textArea.style.top = '-999999px'
    textArea.setAttribute('readonly', '')
    document.body.appendChild(textArea)
    
    // 选中文本
    textArea.select()
    textArea.setSelectionRange(0, code.length)
    
    // 尝试使用 Selection API
    const selection = document.getSelection()
    if (selection) {
      selection.removeAllRanges()
      const range = document.createRange()
      range.selectNodeContents(textArea)
      selection.addRange(range)
      
      document.body.removeChild(textArea)
      toast.success('邀请码已选中，请按 Ctrl+C (或 Cmd+C) 复制')
    } else {
      document.body.removeChild(textArea)
      throw new Error('无法选中文本')
    }
  } catch (error) {
    console.error('复制失败:', error)
    // 提供手动复制的选项
    const message = `复制失败，请手动复制邀请码：${code}`
    toast.error(message, { timeout: 8000 })
    
    // 也可以尝试打开一个提示框显示邀请码
    if (window.prompt) {
      window.prompt('请复制以下邀请码:', code)
    }
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