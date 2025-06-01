<template>
  <div class="system-control-content">
    <!-- 统计概览 -->
    <div class="stats-overview" v-if="stats">
      <div class="stat-card">
        <div class="stat-icon">👥</div>
        <div class="stat-content">
          <div class="stat-number">{{ stats.users.total }}</div>
          <div class="stat-label">总用户数</div>
          <div class="stat-detail">活跃: {{ stats.users.active }}</div>
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-icon">🎫</div>
        <div class="stat-content">
          <div class="stat-number">{{ stats.invitations.unused }}</div>
          <div class="stat-label">可用邀请码</div>
          <div class="stat-detail">总计: {{ stats.invitations.total }}</div>
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-icon">📚</div>
        <div class="stat-content">
          <div class="stat-number">{{ stats.subjects.total_questions }}</div>
          <div class="stat-label">题目总数</div>
          <div class="stat-detail">{{ stats.subjects.total_files }}个文件</div>
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-icon">🛡️</div>
        <div class="stat-content">
          <div class="stat-number">{{ stats.users.admins }}</div>
          <div class="stat-label">管理员</div>
          <div class="stat-detail">VIP: {{ stats.users.vips }}</div>
        </div>
      </div>
    </div>

    <!-- 功能选项卡 -->
    <div class="control-tabs">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        :class="['tab-button', { active: activeTab === tab.key }]"
        @click="switchTab(tab.key)"
      >
        <span class="tab-icon">{{ tab.icon }}</span>
        <span class="tab-text">{{ tab.label }}</span>
      </button>
    </div>

    <!-- 用户管理 -->
    <div v-if="activeTab === 'users'" class="control-section">
      <div class="section-header">
        <h2 class="section-title">👥 用户管理</h2>
        <div class="section-actions">
          <button class="refresh-btn" @click="loadUsers" :disabled="loading">
            <span class="btn-icon">🔄</span>
            刷新列表
          </button>
        </div>
      </div>

      <Loading v-if="loading" />

      <div v-else-if="users.length === 0" class="empty-state">
        <div class="empty-icon">👤</div>
        <p>暂无用户数据</p>
      </div>

      <div v-else class="users-table-container">
        <table class="users-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>用户名</th>
              <th>权限等级</th>
              <th>状态</th>
              <th>注册时间</th>
              <th>最后登录</th>
              <th>邀请码</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="user in users" :key="user.id" :class="{ disabled: !user.is_enabled }">
              <td>{{ user.id }}</td>
              <td class="username-cell">
                <span class="username">{{ user.username }}</span>
              </td>
              <td>
                <select
                  :value="user.model"
                  @change="updateUserModel(user.id, parseInt(($event.target as HTMLSelectElement).value))"
                  class="model-select"
                  :disabled="user.id === currentUserId"
                >
                  <option value="0">普通用户</option>
                  <option value="5">VIP用户</option>
                  <option value="10">ROOT用户</option>
                </select>
              </td>
              <td>
                <span :class="['status-badge', user.is_enabled ? 'status-active' : 'status-disabled']">
                  {{ user.is_enabled ? '启用' : '禁用' }}
                </span>
              </td>
              <td class="date-cell">{{ formatDate(user.created_at) }}</td>
              <td class="date-cell">
                <span :class="['last-login', getLastLoginClass(user.last_time_login)]">
                  {{ formatLastLogin(user.last_time_login) }}
                </span>
              </td>
              <td class="invitation-cell">
                <code class="invitation-code">{{ user.invitation_code || 'N/A' }}</code>
              </td>
              <td class="actions-cell">
                <button
                  @click="toggleUser(user.id)"
                  :class="['action-btn', user.is_enabled ? 'btn-disable' : 'btn-enable']"
                  :disabled="user.id === currentUserId"
                >
                  {{ user.is_enabled ? '禁用' : '启用' }}
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- 邀请码管理 -->
    <div v-if="activeTab === 'invitations'" class="control-section">
      <div class="section-header">
        <h2 class="section-title">🎫 邀请码管理</h2>
        <div class="section-actions">
          <button class="primary-btn" @click="showCreateInvitationDialog = true">
            <span class="btn-icon">➕</span>
            创建邀请码
          </button>
          <button class="refresh-btn" @click="loadInvitations" :disabled="loading">
            <span class="btn-icon">🔄</span>
            刷新列表
          </button>
        </div>
      </div>

      <Loading v-if="loading" />

      <div v-else-if="invitations.length === 0" class="empty-state">
        <div class="empty-icon">🎫</div>
        <p>暂无邀请码</p>
      </div>

      <div v-else class="invitations-table-container">
        <table class="invitations-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>邀请码</th>
              <th>状态</th>
              <th>使用者</th>
              <th>创建时间</th>
              <th>过期时间</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="invitation in invitations" :key="invitation.id" :class="{ used: invitation.is_used }">
              <td>{{ invitation.id }}</td>
              <td class="code-cell">
                <code class="invitation-code-display">{{ invitation.code }}</code>
                <button
                  class="copy-btn"
                  @click="copyInvitationCode(invitation.code)"
                  title="复制邀请码"
                >
                  📋
                </button>
              </td>
              <td>
                <span :class="['status-badge', invitation.is_used ? 'status-used' : 'status-available']">
                  {{ invitation.is_used ? '已使用' : '可用' }}
                </span>
              </td>
              <td>{{ invitation.used_by_username || '-' }}</td>
              <td class="date-cell">{{ formatDate(invitation.created_at) }}</td>
              <td class="date-cell">{{ invitation.expires_at ? formatDate(invitation.expires_at) : '永不过期' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- 题库管理 -->
    <div v-if="activeTab === 'subjects'" class="control-section">
      <div class="section-header">
        <h2 class="section-title">📚 题库管理</h2>
        <div class="section-actions">
          <button class="refresh-btn" @click="loadSubjectFiles" :disabled="loading">
            <span class="btn-icon">🔄</span>
            刷新列表
          </button>
        </div>
      </div>

      <Loading v-if="loading" />

      <div v-else-if="subjectFiles.length === 0" class="empty-state">
        <div class="empty-icon">📚</div>
        <p>暂无题库文件</p>
      </div>

      <div v-else class="files-table-container">
        <table class="files-table">
          <thead>
            <tr>
              <th>科目</th>
              <th>文件名</th>
              <th>显示名称</th>
              <th>题目数量</th>
              <th>文件大小</th>
              <th>修改时间</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="file in subjectFiles" :key="`${file.subject}-${file.filename}`">
              <td class="subject-cell">
                <span class="subject-tag">{{ file.subject }}</span>
              </td>
              <td class="filename-cell">
                <code>{{ file.filename }}</code>
              </td>
              <td>{{ file.display_name }}</td>
              <td class="number-cell">{{ file.question_count }}</td>
              <td class="size-cell">{{ formatFileSize(file.file_size) }}</td>
              <td class="date-cell">{{ formatDate(file.modified_time) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- 创建邀请码对话框 -->
    <div v-if="showCreateInvitationDialog" class="dialog-overlay" @click="closeCreateDialog">
      <div class="dialog" @click.stop>
        <div class="dialog-header">
          <h3 class="dialog-title">创建新邀请码</h3>
          <button class="dialog-close" @click="closeCreateDialog">✕</button>
        </div>

        <div class="dialog-content">
          <div class="form-group">
            <label class="form-label">邀请码（可选）</label>
            <input
              v-model="newInvitationCode"
              type="text"
              class="form-input"
              placeholder="留空自动生成"
              maxlength="64"
            >
            <div class="form-hint">留空将自动生成12位随机邀请码</div>
          </div>

          <div class="form-group">
            <label class="form-label">有效期（天）</label>
            <input
              v-model.number="newInvitationExpireDays"
              type="number"
              class="form-input"
              placeholder="留空表示永不过期"
              min="1"
              max="365"
            >
            <div class="form-hint">留空表示永不过期</div>
          </div>
        </div>

        <div class="dialog-actions">
          <button class="dialog-btn dialog-btn-cancel" @click="closeCreateDialog">
            取消
          </button>
          <button class="dialog-btn dialog-btn-confirm" @click="createInvitation" :disabled="creatingInvitation">
            {{ creatingInvitation ? '创建中...' : '创建' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script lang="ts" setup>
import { ref, onMounted, computed } from 'vue'
import { useToast } from 'vue-toastification'
import { useAuthStore } from '@/stores/auth'
import { apiService } from '@/services/api'
import Loading from '@/components/Loading.vue'

const toast = useToast()
const authStore = useAuthStore()

// 响应式数据
const loading = ref(false)
const activeTab = ref('users')
const stats = ref<any>(null)
const users = ref<any[]>([])
const invitations = ref<any[]>([])
const subjectFiles = ref<any[]>([])

// 创建邀请码对话框
const showCreateInvitationDialog = ref(false)
const newInvitationCode = ref('')
const newInvitationExpireDays = ref<number | null>(null)
const creatingInvitation = ref(false)

// 标签页配置
const tabs = [
  { key: 'users', label: '用户管理', icon: '👥' },
  { key: 'invitations', label: '邀请码管理', icon: '🎫' },
  { key: 'subjects', label: '题库管理', icon: '📚' }
]

// 当前用户ID
const currentUserId = computed(() => authStore.user?.user_id)

// 切换标签页
const switchTab = (tabKey: string) => {
  activeTab.value = tabKey
  toast.info(`已切换到${tabs.find(t => t.key === tabKey)?.label} 📌`)
}

// 加载统计信息
const loadStats = async () => {
  try {
    const response = await apiService.admin.getStats()
    if (response.success) {
      stats.value = response.stats
    } else {
      toast.error(response.message || '获取统计信息失败')
    }
  } catch (error) {
    console.error('获取统计信息失败:', error)
    toast.error('获取统计信息失败')
  }
}

// 用户管理相关函数
const loadUsers = async () => {
  loading.value = true
  try {
    const response = await apiService.admin.getUsers()
    if (response.success) {
      users.value = response.users || []
    } else {
      toast.error(response.message || '获取用户列表失败')
    }
  } catch (error) {
    console.error('获取用户列表失败:', error)
    toast.error('获取用户列表失败')
  } finally {
    loading.value = false
  }
}

const toggleUser = async (userId: number) => {
  try {
    const response = await apiService.admin.toggleUser(userId)
    if (response.success) {
      // 更新本地数据
      const user = users.value.find(u => u.id === userId)
      if (user) {
        user.is_enabled = response.is_enabled
      }
      toast.success(response.message || '操作成功')
      // 重新加载统计信息
      loadStats()
    } else {
      toast.error(response.message || '操作失败')
    }
  } catch (error) {
    console.error('切换用户状态失败:', error)
    toast.error('操作失败')
  }
}

const updateUserModel = async (userId: number, model: number) => {
  try {
    const response = await apiService.admin.updateUserModel(userId, model)
    if (response.success) {
      // 更新本地数据
      const user = users.value.find(u => u.id === userId)
      if (user) {
        user.model = response.model
      }
      toast.success(response.message || '权限更新成功')
      // 重新加载统计信息
      loadStats()
    } else {
      toast.error(response.message || '权限更新失败')
      // 恢复原来的值
      loadUsers()
    }
  } catch (error) {
    console.error('更新用户权限失败:', error)
    toast.error('权限更新失败')
    // 恢复原来的值
    loadUsers()
  }
}

// 邀请码管理相关函数
const loadInvitations = async () => {
  loading.value = true
  try {
    const response = await apiService.admin.getInvitations()
    if (response.success) {
      invitations.value = response.invitations || []
    } else {
      toast.error(response.message || '获取邀请码列表失败')
    }
  } catch (error) {
    console.error('获取邀请码列表失败:', error)
    toast.error('获取邀请码列表失败')
  } finally {
    loading.value = false
  }
}

const createInvitation = async () => {
  if (creatingInvitation.value) return

  creatingInvitation.value = true
  try {
    const response = await apiService.admin.createInvitation(
      newInvitationCode.value || undefined,
      newInvitationExpireDays.value || undefined
    )

    if (response.success) {
      toast.success('邀请码创建成功！')
      closeCreateDialog()
      loadInvitations()
      loadStats()
    } else {
      toast.error(response.message || '创建邀请码失败')
    }
  } catch (error) {
    console.error('创建邀请码失败:', error)
    toast.error('创建邀请码失败')
  } finally {
    creatingInvitation.value = false
  }
}

const copyInvitationCode = async (code: string) => {
  try {
    await navigator.clipboard.writeText(code)
    toast.success('邀请码已复制到剪贴板')
  } catch (error) {
    console.error('复制失败:', error)
    toast.error('复制失败')
  }
}

const closeCreateDialog = () => {
  showCreateInvitationDialog.value = false
  newInvitationCode.value = ''
  newInvitationExpireDays.value = null
}

// 题库管理相关函数
const loadSubjectFiles = async () => {
  loading.value = true
  try {
    const response = await apiService.admin.getSubjectFiles()
    if (response.success) {
      subjectFiles.value = response.files || []
    } else {
      toast.error(response.message || '获取题库文件失败')
    }
  } catch (error) {
    console.error('获取题库文件失败:', error)
    toast.error('获取题库文件失败')
  } finally {
    loading.value = false
  }
}

// 工具函数
const formatDate = (dateString: string) => {
  if (!dateString) return '-'
  return new Date(dateString).toLocaleString('zh-CN')
}

const formatLastLogin = (dateString?: string) => {
  if (!dateString) return '从未登录'

  const loginDate = new Date(dateString)
  const now = new Date()
  const timeDiff = now.getTime() - loginDate.getTime()

  // 计算时间差
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

const getLastLoginClass = (dateString?: string) => {
  if (!dateString) return 'never-login'

  const loginDate = new Date(dateString)
  const now = new Date()
  const timeDiff = now.getTime() - loginDate.getTime()
  const days = Math.floor(timeDiff / (1000 * 60 * 60 * 24))

  if (days === 0) {
    return 'recent-login' // 今天登录
  } else if (days <= 7) {
    return 'week-login' // 一周内登录
  } else if (days <= 30) {
    return 'month-login' // 一月内登录
  } else {
    return 'old-login' // 很久没登录
  }
}

const formatFileSize = (bytes: number) => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

// 组件挂载时加载数据
onMounted(async () => {
  await loadStats()
  await loadUsers()
})
</script>

<style scoped>
.system-control-content {
  width: 100%;
  min-height: calc(100vh - 64px);
  background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
  padding: 2rem;
  max-width: 1400px;
  margin: 0 auto;
  overflow-y: auto;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* 统计概览样式 */
.stats-overview {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1.5rem;
  margin-bottom: 3rem;
}

.stat-card {
  background: white;
  border-radius: 16px;
  padding: 2rem;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
  border: 2px solid transparent;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  gap: 1.5rem;
}

.stat-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1);
  border-color: #e2e8f0;
}

.stat-icon {
  font-size: 3rem;
  background: linear-gradient(135deg, #f8fafc, #e2e8f0);
  border-radius: 12px;
  width: 4rem;
  height: 4rem;
  display: flex;
  align-items: center;
  justify-content: center;
}

.stat-content {
  flex: 1;
}

.stat-number {
  font-size: 2rem;
  font-weight: 700;
  color: #1e293b;
  margin-bottom: 0.5rem;
}

.stat-label {
  font-size: 1rem;
  color: #64748b;
  font-weight: 500;
  margin-bottom: 0.25rem;
}

.stat-detail {
  font-size: 0.9rem;
  color: #94a3b8;
}

/* 标签页样式 */
.control-tabs {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 2rem;
  background: #f8fafc;
  padding: 0.5rem;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
}

.tab-button {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.5rem;
  background: transparent;
  border: 1px solid transparent;
  border-radius: 8px;
  color: #64748b;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s ease;
  flex: 1;
  justify-content: center;
}

.tab-button:hover {
  background: white;
  color: #3b82f6;
  border-color: #bfdbfe;
  transform: translateY(-1px);
}

.tab-button.active {
  background: linear-gradient(135deg, #3b82f6, #2563eb);
  color: white;
  border-color: #2563eb;
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
}

.tab-icon {
  font-size: 1.2rem;
}

.tab-text {
  font-weight: 600;
}

/* 控制区块样式 */
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

/* 按钮样式 */
.primary-btn, .refresh-btn, .action-btn {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.25rem;
  border: none;
  border-radius: 8px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  font-size: 0.9rem;
}

.primary-btn {
  background: linear-gradient(135deg, #10b981, #34d399);
  color: white;
}

.primary-btn:hover {
  background: linear-gradient(135deg, #059669, #10b981);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
}

.refresh-btn {
  background: #f8fafc;
  color: #64748b;
  border: 1px solid #e2e8f0;
}

.refresh-btn:hover {
  background: #f1f5f9;
  color: #475569;
  border-color: #cbd5e1;
}

.refresh-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.action-btn {
  padding: 0.5rem 1rem;
  font-size: 0.8rem;
}

.btn-enable {
  background: linear-gradient(135deg, #10b981, #34d399);
  color: white;
}

.btn-enable:hover {
  background: linear-gradient(135deg, #059669, #10b981);
}

.btn-disable {
  background: linear-gradient(135deg, #ef4444, #f87171);
  color: white;
}

.btn-disable:hover {
  background: linear-gradient(135deg, #dc2626, #ef4444);
}

.action-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none;
}

.btn-icon {
  font-size: 1rem;
}

/* 空状态样式 */
.empty-state {
  text-align: center;
  padding: 4rem 2rem;
  color: #64748b;
}

.empty-icon {
  font-size: 4rem;
  margin-bottom: 1rem;
  opacity: 0.5;
}

/* 表格样式 */
.users-table-container, .invitations-table-container, .files-table-container {
  overflow-x: auto;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
}

.users-table, .invitations-table, .files-table {
  width: 100%;
  border-collapse: collapse;
  background: white;
}

.users-table th, .invitations-table th, .files-table th {
  background: #f8fafc;
  color: #374151;
  font-weight: 600;
  padding: 1rem;
  text-align: left;
  border-bottom: 2px solid #e2e8f0;
  white-space: nowrap;
}

.users-table td, .invitations-table td, .files-table td {
  padding: 1rem;
  border-bottom: 1px solid #f1f5f9;
  vertical-align: middle;
}

.users-table tr:hover, .invitations-table tr:hover, .files-table tr:hover {
  background: #fafbfc;
}

.users-table tr.disabled {
  opacity: 0.6;
  background: #fef2f2;
}

.invitations-table tr.used {
  opacity: 0.7;
  background: #f9fafb;
}

/* 表格单元格特殊样式 */
.username-cell .username {
  font-weight: 600;
  color: #1e293b;
}

.model-select {
  padding: 0.5rem;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  background: white;
  font-size: 0.9rem;
}

.model-select:disabled {
  background: #f9fafb;
  color: #6b7280;
  cursor: not-allowed;
}

.status-badge {
  display: inline-block;
  padding: 0.25rem 0.75rem;
  border-radius: 999px;
  font-size: 0.8rem;
  font-weight: 500;
  white-space: nowrap;
}

.status-active {
  background: #d1fae5;
  color: #065f46;
}

.status-disabled {
  background: #fee2e2;
  color: #991b1b;
}

.status-available {
  background: #dbeafe;
  color: #1e40af;
}

.status-used {
  background: #e5e7eb;
  color: #374151;
}

.date-cell {
  font-size: 0.9rem;
  color: #6b7280;
  white-space: nowrap;
}

.invitation-cell {
  max-width: 150px;
}

.invitation-code {
  background: #f3f4f6;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-family: 'Courier New', monospace;
  font-size: 0.85rem;
  word-break: break-all;
}

.code-cell {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.invitation-code-display {
  background: #f3f4f6;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-family: 'Courier New', monospace;
  font-size: 0.9rem;
  flex: 1;
}

.copy-btn {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 1rem;
  padding: 0.25rem;
  border-radius: 4px;
  transition: background 0.2s ease;
}

.copy-btn:hover {
  background: #f3f4f6;
}

.subject-cell .subject-tag {
  background: linear-gradient(135deg, #eff6ff, #dbeafe);
  color: #1e40af;
  padding: 0.25rem 0.75rem;
  border-radius: 999px;
  font-size: 0.8rem;
  font-weight: 500;
  border: 1px solid #bfdbfe;
}

.filename-cell code {
  background: #f8fafc;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-size: 0.85rem;
}

.number-cell, .size-cell {
  text-align: right;
  font-weight: 500;
}

.actions-cell {
  white-space: nowrap;
}

/* 对话框样式 */
.dialog-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(4px);
}

.dialog {
  background: white;
  border-radius: 20px;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
  max-width: 500px;
  width: 90%;
  max-height: 80vh;
  overflow-y: auto;
}

.dialog-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 2rem 2rem 0;
}

.dialog-title {
  font-size: 1.5rem;
  font-weight: 600;
  color: #1e293b;
  margin: 0;
}

.dialog-close {
  background: none;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  color: #6b7280;
  width: 2rem;
  height: 2rem;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  transition: all 0.2s ease;
}

.dialog-close:hover {
  background: #f3f4f6;
  color: #374151;
}

.dialog-content {
  padding: 2rem;
}

.form-group {
  margin-bottom: 1.5rem;
}

.form-label {
  display: block;
  font-weight: 500;
  color: #374151;
  margin-bottom: 0.5rem;
}

.form-input {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  font-size: 1rem;
  transition: border-color 0.2s ease;
}

.form-input:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.form-hint {
  font-size: 0.85rem;
  color: #6b7280;
  margin-top: 0.25rem;
}

.dialog-actions {
  display: flex;
  gap: 1rem;
  padding: 0 2rem 2rem;
  justify-content: flex-end;
}

.dialog-btn {
  padding: 0.75rem 1.5rem;
  border-radius: 8px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  border: none;
}

.dialog-btn-cancel {
  background: #f8fafc;
  color: #64748b;
  border: 1px solid #e2e8f0;
}

.dialog-btn-cancel:hover {
  background: #f1f5f9;
  color: #475569;
}

.dialog-btn-confirm {
  background: linear-gradient(135deg, #10b981, #34d399);
  color: white;
}

.dialog-btn-confirm:hover {
  background: linear-gradient(135deg, #059669, #10b981);
}

.dialog-btn-confirm:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .system-control-content {
    padding: 1rem;
  }

  .control-title {
    font-size: 2rem;
  }

  .stats-overview {
    grid-template-columns: 1fr;
    gap: 1rem;
  }

  .stat-card {
    padding: 1.5rem;
  }

  .control-tabs {
    flex-direction: column;
  }

  .tab-button {
    flex: none;
  }

  .section-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 1rem;
  }

  .section-actions {
    width: 100%;
    justify-content: flex-end;
  }

  .users-table-container, .invitations-table-container, .files-table-container {
    font-size: 0.9rem;
  }

  .users-table th, .invitations-table th, .files-table th,
  .users-table td, .invitations-table td, .files-table td {
    padding: 0.75rem 0.5rem;
  }

  /* 在移动端隐藏一些不重要的列 */
  .users-table th:nth-child(1),
  .users-table td:nth-child(1),
  .users-table th:nth-child(5),
  .users-table td:nth-child(5),
  .users-table th:nth-child(7),
  .users-table td:nth-child(7) {
    display: none;
  }

  .dialog {
    width: 95%;
    margin: 1rem;
  }

  .dialog-content {
    padding: 1.5rem;
  }

  .dialog-actions {
    flex-direction: column;
    padding: 0 1.5rem 1.5rem;
  }
}

/* 最后登录时间样式 */
.last-login {
  padding: 0.25rem 0.5rem;
  border-radius: 6px;
  font-size: 0.8rem;
  font-weight: 500;
  white-space: nowrap;
}

.never-login {
  background: #fee2e2;
  color: #991b1b;
}

.recent-login {
  background: #d1fae5;
  color: #065f46;
}

.week-login {
  background: #dbeafe;
  color: #1e40af;
}

.month-login {
  background: #fef3c7;
  color: #92400e;
}

.old-login {
  background: #f3f4f6;
  color: #6b7280;
}
</style>
