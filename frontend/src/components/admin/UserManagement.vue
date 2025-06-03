<template>
  <div class="control-section">
    <div class="section-header">
      <h2 class="section-title">👥 用户管理</h2>
      <div class="section-actions">
        <v-btn
          color="primary"
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
      :headers="userHeaders"
      :items="filteredUsers"
      :loading="loading"
      :search="userSearch"
      :items-per-page="userItemsPerPage"
      :sort-by="userSortBy"
      :items-per-page-options="itemsPerPageOptions"
      :items-per-page-text="'每页显示：'"
      class="elevation-2"
      density="comfortable"
      :no-data-text="'暂无用户数据'"
      :no-results-text="'没有找到匹配的用户'"
      loading-text="加载用户数据中..."
      hover
      sticky
      fixed-header
    >
      <!-- 搜索槽 -->
      <template v-slot:top>
        <div class="pa-4">
          <v-text-field
            v-model="userSearch"
            label="搜索用户名..."
            prepend-inner-icon="mdi-magnify"
            variant="outlined"
            hide-details
            clearable
            density="compact"
          ></v-text-field>
        </div>
      </template>

      <!-- 用户名列 -->
      <template v-slot:item.username="{ item }">
        <div class="font-weight-bold">{{ (item as any).username }}</div>
      </template>

      <!-- 权限等级列 -->
      <template v-slot:item.model="{ item }">
        <v-select
          :model-value="(item as any).model"
          @update:model-value="$emit('updateUserModel', (item as any).id, $event)"
          :items="modelOptions"
          variant="outlined"
          density="compact"
          hide-details
          :disabled="item.id === currentUserId"
        ></v-select>
      </template>

      <!-- 状态列 -->
      <template v-slot:item.is_enabled="{ item }">
        <v-chip
          :color="item.is_enabled ? 'success' : 'error'"
          size="small"
          variant="flat"
        >
          {{ item.is_enabled ? '启用' : '禁用' }}
        </v-chip>
      </template>

      <!-- 注册时间列 -->
      <template v-slot:item.created_at="{ item }">
        <span class="text-caption">{{ formatDate(item.created_at) }}</span>
      </template>

      <!-- 最后登录列 -->
      <template v-slot:item.last_time_login="{ item }">
        <v-chip
          :color="getLastLoginColor(item.last_time_login)"
          size="small"
          variant="outlined"
        >
          {{ formatLastLogin(item.last_time_login) }}
        </v-chip>
      </template>

      <!-- 邀请码列 -->
      <template v-slot:item.invitation_code="{ item }">
        <code class="text-caption">{{ item.invitation_code || 'N/A' }}</code>
      </template>

      <!-- 操作列 -->
      <template v-slot:item.actions="{ item }">
        <v-btn
          :color="item.is_enabled ? 'error' : 'success'"
          :disabled="item.id === currentUserId"
          @click="$emit('toggleUser', item.id)"
          size="small"
          variant="elevated"
        >
          {{ item.is_enabled ? '禁用' : '启用' }}
        </v-btn>
      </template>
    </v-data-table>
  </div>
</template>

<script lang="ts" setup>
import { ref, computed } from 'vue'

interface Props {
  users: any[]
  loading: boolean
  currentUserId?: number
}

interface Emits {
  (e: 'refresh'): void
  (e: 'updateUserModel', userId: number, model: number): void
  (e: 'toggleUser', userId: number): void
}

const props = defineProps<Props>()
defineEmits<Emits>()

// 表格配置
const userSearch = ref('')
const userItemsPerPage = ref(20)
const userSortBy = ref([{ key: 'id', order: 'desc' as const }])

const itemsPerPageOptions = [
  { value: 10, title: '10条/页' },
  { value: 20, title: '20条/页' },
  { value: 50, title: '50条/页' },
  { value: 100, title: '100条/页' },
  { value: -1, title: '全部显示' }
]

const userHeaders = [
  { title: 'ID', key: 'id', sortable: true, width: '80px' },
  { title: '用户名', key: 'username', sortable: true, width: '150px' },
  { title: '权限等级', key: 'model', sortable: true, width: '120px' },
  { title: '状态', key: 'is_enabled', sortable: false, width: '100px' },
  { title: '注册时间', key: 'created_at', sortable: true, width: '160px' },
  { title: '最后登录', key: 'last_time_login', sortable: true, width: '160px' },
  { title: '邀请码', key: 'invitation_code', sortable: false, width: '150px' },
  { title: '操作', key: 'actions', sortable: false, width: '120px', align: 'center' as const }
]

const modelOptions = [
  { title: '普通用户', value: 0 },
  { title: 'VIP用户', value: 5 },
  { title: 'ROOT用户', value: 10 }
]

// 计算属性
const filteredUsers = computed(() => {
  if (!userSearch.value) return props.users
  const searchTerm = userSearch.value.toLowerCase()
  return props.users.filter((user: any) => 
    user.username?.toLowerCase().includes(searchTerm) ||
    (user.invitation_code && user.invitation_code.toLowerCase().includes(searchTerm))
  )
})

// 工具函数
const formatDate = (dateString?: string) => {
  if (!dateString) return '-'
  return new Date(dateString).toLocaleString('zh-CN')
}

const formatLastLogin = (dateString?: string) => {
  if (!dateString) return '从未登录'

  const loginDate = new Date(dateString)
  const now = new Date()
  const timeDiff = now.getTime() - loginDate.getTime()

  const minutes = Math.floor(timeDiff / (1000 * 60))
  const hours = Math.floor(timeDiff / (1000 * 60 * 60))
  const days = Math.floor(timeDiff / (1000 * 60 * 60 * 24))

  if (minutes < 1) {
    return '刚刚'
  } else if (minutes < 60) {
    return `${minutes}分钟前`
  } else if (hours < 24) {
    return `${hours}小时前`
  } else if (days < 7) {
    return `${days}天前`
  } else {
    return loginDate.toLocaleString('zh-CN')
  }
}

const getLastLoginColor = (dateString?: string) => {
  if (!dateString) return 'error'

  const loginDate = new Date(dateString)
  const now = new Date()
  const timeDiff = now.getTime() - loginDate.getTime()
  const days = Math.floor(timeDiff / (1000 * 60 * 60 * 24))

  if (days === 0) {
    return 'success' // 今天登录
  } else if (days <= 7) {
    return 'info' // 一周内登录
  } else if (days <= 30) {
    return 'warning' // 一月内登录
  } else {
    return 'grey' // 很久没登录
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