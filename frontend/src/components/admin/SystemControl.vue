<template>
  <div class="system-control-content">
    <!-- 统计概览 -->
    <StatsOverview :stats="stats" />

    <!-- 功能选项卡 -->
    <div class="control-tabs">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        :class="['tab-button', { active: activeTab === tab.key }]"
        @click="switchTab(tab.key)"
      >
        <span class="tab-icon">
          <IconSubject v-if="tab.icon === 'subject'" :size="20" color="currentColor" />
          <span v-else>{{ tab.icon }}</span>
        </span>
        <span class="tab-text">{{ tab.label }}</span>
      </button>
    </div>

    <!-- 用户管理 -->
    <UserManagement
      v-if="activeTab === 'users'"
      :users="users"
      :loading="loading"
      :current-user-id="currentUserId"
      @refresh="loadUsers"
      @update-user-model="updateUserModel"
      @toggle-user="toggleUser"
    />

    <!-- 邀请码管理 -->
    <InvitationManagement
      v-if="activeTab === 'invitations'"
      :invitations="invitations"
      :loading="loading"
      :deleting-invitation="deletingInvitation"
      @refresh="loadInvitations"
      @show-create-dialog="showCreateInvitationDialog = true"
      @delete-invitation="deleteInvitation"
    />

    <!-- 科目管理 -->
    <SubjectManagement
      v-if="activeTab === 'subjects'"
      :subjects="subjects"
      :loading="loading"
      @refresh="loadSubjects"
      @show-create-dialog="openSubjectDialog('create')"
      @show-edit-dialog="openSubjectDialog('edit', $event)"
      @delete-subject="deleteSubject"
    />

    <!-- 题库管理 -->
    <TikuManagement
      v-if="activeTab === 'tiku'"
      :subjects="subjects"
      :tiku-list="tikuList"
      :selected-subject-id="selectedSubjectId"
      :loading="loading"
      @select-subject="selectSubject"
      @show-upload-dialog="openUploadDialog"
      @reload-banks="reloadBanks"
      @toggle-tiku="toggleTiku"
      @delete-tiku="deleteTiku"
      @show-questions="showQuestionManagement"
    />

    <!-- 题目管理 -->
    <QuestionManagement
      v-if="activeTab === 'questions'"
      :tiku-info="selectedTiku"
      @go-back="goBackToTiku"
    />

    <!-- 创建邀请码对话框 -->
    <CreateInvitationDialog
      v-model="showCreateInvitationDialog"
      :creating="creatingInvitation"
      @create="createInvitation"
    />

    <!-- 科目管理对话框 -->
    <SubjectDialog
      v-model="showSubjectDialog"
      :mode="subjectDialogMode"
      :subject="currentSubject"
      :saving="loading"
      @save="saveSubject"
    />

    <!-- 题库上传对话框 -->
    <UploadTikuDialog
      v-model="showUploadDialog"
      :uploading="uploading"
      @upload="uploadTiku"
    />

    <!-- 权限变更确认对话框 -->
    <PermissionChangeDialog
      v-model="showPermissionChangeDialog"
      :permission-data="pendingPermissionChange"
      :updating="updatingPermission"
      @confirm="confirmPermissionChange"
      @cancel="cancelPermissionChange"
    />
  </div>
</template>

<script lang="ts" setup>
import { ref, onMounted, computed, onUnmounted } from 'vue'
import { useToast } from 'vue-toastification'
import { useAuthStore } from '@/stores/auth'
import { 
  apiService, 
  type AdminUser, 
  type AdminInvitation, 
  type Subject, 
  type TikuItem, 
  type UserSearchParams, 
  type SearchParams, 
  type Pagination,
  type AdminStats
} from '@/services/api'
import Loading from '@/components/common/Loading.vue'
import IconSubject from '@/components/icons/IconSubject.vue'

// 导入拆分的组件
import StatsOverview from './StatsOverview.vue'
import UserManagement from './UserManagement.vue'
import InvitationManagement from './InvitationManagement.vue'
import SubjectManagement from './SubjectManagement.vue'
import TikuManagement from './TikuManagement.vue'
import QuestionManagement from './QuestionManagement.vue'
import CreateInvitationDialog from './CreateInvitationDialog.vue'
import SubjectDialog from './SubjectDialog.vue'
import UploadTikuDialog from './UploadTikuDialog.vue'
import PermissionChangeDialog from './PermissionChangeDialog.vue'

// 类型定义
interface PermissionChangeData {
  userId: number
  username: string
  currentModel: number
  newModel: number
}

interface Tab {
  key: string
  label: string
  icon: string
}

const toast = useToast()
const authStore = useAuthStore()

// 响应式数据
const loading = ref(false)
const activeTab = ref('users')
const stats = ref<AdminStats | null>(null)
const users = ref<AdminUser[]>([])
const invitations = ref<AdminInvitation[]>([])
const subjects = ref<Subject[]>([])
const tikuList = ref<TikuItem[]>([])
const selectedSubjectId = ref<number | null>(null)

// 创建邀请码对话框
const showCreateInvitationDialog = ref(false)
const creatingInvitation = ref(false)
const deletingInvitation = ref(false)

// 科目管理对话框
const showSubjectDialog = ref(false)
const subjectDialogMode = ref<'create' | 'edit'>('create')
const currentSubject = ref<Subject | null>(null)

// 题库管理状态
const showUploadDialog = ref(false)
const uploading = ref(false)

// 题目管理状态
const selectedTiku = ref<TikuItem | null>(null)

// 权限变更相关状态
const pendingPermissionChange = ref<PermissionChangeData | null>(null)
const updatingPermission = ref(false)
const showPermissionChangeDialog = ref(false)

// 标签页配置
const tabs: Tab[] = [
  { key: 'users', label: '用户管理', icon: '👥' },
  { key: 'invitations', label: '邀请码管理', icon: '🎫' },
  { key: 'subjects', label: '科目管理', icon: 'subject' },
  { key: 'tiku', label: '题库管理', icon: '📖' }
]

// 当前用户ID
const currentUserId = computed(() => authStore.user?.user_id)

// 切换标签页
const switchTab = (tabKey: string) => {
  activeTab.value = tabKey
  
  // 根据标签页加载对应数据
  if (tabKey === 'invitations' && invitations.value.length === 0) {
    loadInvitations()
  } else if (tabKey === 'subjects' && subjects.value.length === 0) {
    loadSubjects()
  }
  
  toast.info(`已切换到${tabs.find(t => t.key === tabKey)?.label} 📌`)
}

// 加载统计信息
const loadStats = async () => {
  try {
    const response = await apiService.admin.getStats()
    if (response.success) {
      stats.value = response.stats || null
    } else {
      handleError(new Error(response.message), '获取统计信息')
    }
  } catch (error) {
    handleError(error, '获取统计信息')
  }
}

// 用户管理相关函数
const loadUsers = async () => {
  loading.value = true
  try {
    const response = await apiService.admin.getUsers({
      search: '',
      order_by: 'id',
      order_dir: 'desc',
      page: 1,
      per_page: 1000
    })
    if (response.success) {
      users.value = response.users || []
    } else {
      handleError(new Error(response.message), '获取用户列表')
    }
  } catch (error) {
    handleError(error, '获取用户列表')
  } finally {
    loading.value = false
  }
}

const toggleUser = async (userId: number) => {
  try {
    const response = await apiService.admin.toggleUser(userId)
    if (response.success) {
      const user = users.value.find(u => u.id === userId)
      if (user) {
        user.is_enabled = response.is_enabled || false
      }
      handleSuccess(response.message || '操作成功', () => loadStats())
    } else {
      handleError(new Error(response.message), '切换用户状态')
    }
  } catch (error) {
    handleError(error, '切换用户状态')
  }
}

const updateUserModel = async (userId: number, model: number) => {
  const user = users.value.find(u => u.id === userId)
  if (!user) {
    toast.error('用户不存在')
    return
  }

  if (user.model === model) {
    return
  }

  pendingPermissionChange.value = {
    userId: userId,
    username: user.username,
    currentModel: user.model,
    newModel: model
  }
  showPermissionChangeDialog.value = true
}

// 邀请码管理相关函数
const loadInvitations = async () => {
  loading.value = true
  try {
    const response = await apiService.admin.getInvitations({
      search: '',
      order_by: 'id',
      order_dir: 'desc',
      page: 1,
      per_page: 1000
    })
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

const createInvitation = async (code?: string, expireDays?: number) => {
  if (creatingInvitation.value) return

  creatingInvitation.value = true
  try {
    const response = await apiService.admin.createInvitation(code, expireDays)

    if (response.success) {
      toast.success('邀请码创建成功！')
      showCreateInvitationDialog.value = false
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

const deleteInvitation = async (invitation: AdminInvitation) => {
  if (!confirm(`确定要删除邀请码"${invitation.code}"吗？此操作不可恢复！`)) {
    return
  }

  deletingInvitation.value = true
  try {
    const response = await apiService.admin.deleteInvitation(invitation.id)
    if (response.success) {
      toast.success(response.message || '邀请码删除成功')
      loadInvitations()
      loadStats()
    } else {
      toast.error(response.message || '删除邀请码失败')
    }
  } catch (error) {
    console.error('删除邀请码失败:', error)
    toast.error('删除邀请码失败')
  } finally {
    deletingInvitation.value = false
  }
}

// 科目管理相关函数
const loadSubjects = async () => {
  loading.value = true
  try {
    const response = await apiService.admin.getSubjects({
      search: '',
      order_by: 'subject_id',
      order_dir: 'desc',
      page: 1,
      per_page: 1000
    })
    if (response.success) {
      subjects.value = response.subjects || []
    } else {
      toast.error(response.message || '获取科目列表失败')
    }
  } catch (error) {
    console.error('获取科目列表失败:', error)
    toast.error('获取科目列表失败')
  } finally {
    loading.value = false
  }
}

const openSubjectDialog = (mode: 'create' | 'edit', subject?: Subject) => {
  subjectDialogMode.value = mode
  currentSubject.value = subject || null
  showSubjectDialog.value = true
}

const saveSubject = async (name: string, examTime: string) => {
  if (!name.trim()) {
    toast.error('科目名称不能为空')
    return
  }

  loading.value = true
  try {
    if (subjectDialogMode.value === 'create') {
      const response = await apiService.admin.createSubject(name.trim(), examTime)
      if (response.success) {
        toast.success('科目创建成功')
        showSubjectDialog.value = false
        loadSubjects()
        loadStats()
      } else {
        toast.error(response.message || '创建科目失败')
      }
    } else if (currentSubject.value) {
      const response = await apiService.admin.updateSubject(currentSubject.value.subject_id, name.trim(), examTime)
      if (response.success) {
        toast.success('科目更新成功')
        showSubjectDialog.value = false
        loadSubjects()
      } else {
        toast.error(response.message || '更新科目失败')
      }
    }
  } catch (error) {
    console.error('保存科目失败:', error)
    toast.error('保存科目失败')
  } finally {
    loading.value = false
  }
}

const deleteSubject = async (subject: Subject) => {
  if (!confirm(`确定要删除科目"${subject.subject_name}"吗？这将同时删除该科目下的所有题库文件！`)) {
    return
  }

  loading.value = true
  try {
    const response = await apiService.admin.deleteSubject(subject.subject_id)
    if (response.success) {
      toast.success('科目删除成功')
      loadSubjects()
      loadStats()
      if (selectedSubjectId.value === subject.subject_id) {
        selectedSubjectId.value = null
        tikuList.value = []
      }
    } else {
      toast.error(response.message || '删除科目失败')
    }
  } catch (error) {
    console.error('删除科目失败:', error)
    toast.error('删除科目失败')
  } finally {
    loading.value = false
  }
}

// 题库管理相关函数
const loadTiku = async (subjectId?: number) => {
  loading.value = true
  try {
    const response = await apiService.admin.getTiku(subjectId, {
      search: '',
      order_by: 'tiku_id',
      order_dir: 'desc',
      page: 1,
      per_page: 1000
    })
    if (response.success) {
      tikuList.value = response.tiku_list || []
    } else {
      toast.error(response.message || '获取题库列表失败')
    }
  } catch (error) {
    console.error('获取题库列表失败:', error)
    toast.error('获取题库列表失败')
  } finally {
    loading.value = false
  }
}

const selectSubject = (subjectId: number) => {
  selectedSubjectId.value = subjectId
  if (subjectId) {
    loadTiku(subjectId)
  }
}

const openUploadDialog = () => {
  if (!selectedSubjectId.value) {
    toast.error('请先选择一个科目')
    return
  }
  showUploadDialog.value = true
}

const uploadTiku = async (file: File, tikuName: string) => {
  if (!selectedSubjectId.value) {
    toast.error('请先选择一个科目')
    return
  }

  uploading.value = true
  try {
    const response = await apiService.admin.uploadTiku(
      file,
      selectedSubjectId.value,
      tikuName || undefined
    )
    
    if (response.success) {
      toast.success(`题库上传成功！共${response.question_count}道题目`)
      showUploadDialog.value = false
      loadTiku(selectedSubjectId.value)
      loadStats()
    } else {
      toast.error(response.message || '上传题库失败')
    }
  } catch (error) {
    console.error('上传题库失败:', error)
    toast.error(`上传题库失败: ${error instanceof Error ? error.message : '未知错误'}`)
  } finally {
    uploading.value = false
  }
}

const deleteTiku = async (tiku: TikuItem) => {
  if (!confirm(`确定要删除题库"${tiku.tiku_name}"吗？`)) {
    return
  }

  loading.value = true
  try {
    const response = await apiService.admin.deleteTiku(tiku.tiku_id)
    if (response.success) {
      toast.success('题库删除成功')
      loadTiku(selectedSubjectId.value || undefined)
      loadStats()
    } else {
      toast.error(response.message || '删除题库失败')
    }
  } catch (error) {
    console.error('删除题库失败:', error)
    toast.error('删除题库失败')
  } finally {
    loading.value = false
  }
}

const toggleTiku = async (tiku: TikuItem) => {
  loading.value = true
  try {
    const response = await apiService.admin.toggleTiku(tiku.tiku_id)
    if (response.success) {
      tiku.is_active = response.is_active || false
      toast.success(response.message || '操作成功')
    } else {
      toast.error(response.message || '操作失败')
    }
  } catch (error) {
    console.error('切换题库状态失败:', error)
    toast.error('操作失败')
  } finally {
    loading.value = false
  }
}

const reloadBanks = async () => {
  if (!confirm('确定要重新加载所有题库吗？这可能需要一些时间。')) {
    return
  }

  loading.value = true
  try {
    const response = await apiService.admin.reloadBanks()
    if (response.success) {
      toast.success('题库重新加载完成')
      loadSubjects()
      loadTiku(selectedSubjectId.value || undefined)
      loadStats()
    } else {
      toast.error(response.message || '重新加载失败')
    }
  } catch (error) {
    console.error('重新加载失败:', error)
    toast.error('重新加载失败')
  } finally {
    loading.value = false
  }
}

// 题目管理相关函数
const showQuestionManagement = (tiku: TikuItem) => {
  selectedTiku.value = tiku
  activeTab.value = 'questions'
  toast.info(`进入题目管理 - ${tiku.tiku_name} 📝`)
}

const goBackToTiku = () => {
  selectedTiku.value = null
  activeTab.value = 'tiku'
  toast.info('返回题库列表 📖')
}

// 权限变更相关函数
const confirmPermissionChange = async () => {
  if (!pendingPermissionChange.value) return

  updatingPermission.value = true
  try {
    const response = await apiService.admin.updateUserModel(pendingPermissionChange.value.userId, pendingPermissionChange.value.newModel)
    if (response.success) {
      const user = users.value.find(u => u.id === pendingPermissionChange.value?.userId)
      if (user) {
        user.model = response.model || pendingPermissionChange.value.newModel
      }
      handleSuccess(response.message || '权限更新成功', () => loadStats())
      closePermissionChangeDialog()
    } else {
      handleError(new Error(response.message), '更新用户权限')
    }
  } catch (error) {
    handleError(error, '更新用户权限')
  } finally {
    updatingPermission.value = false
  }
}

const cancelPermissionChange = () => {
  if (pendingPermissionChange.value) {
    loadUsers()
  }
  closePermissionChangeDialog()
}

const closePermissionChangeDialog = () => {
  showPermissionChangeDialog.value = false
  pendingPermissionChange.value = null
}

// 错误处理优化
const handleError = (error: any, operation: string) => {
  console.error(`${operation}失败:`, error)
  const message = error?.response?.data?.message || error?.message || `${operation}失败`
  toast.error(message)
}

// 成功处理优化
const handleSuccess = (message: string, callback?: () => void) => {
  toast.success(message)
  if (callback) callback()
}

// 组件挂载时加载数据
onMounted(async () => {
  try {
    await Promise.all([
      loadStats(),
      loadUsers(),
      loadSubjects()
    ])
  } catch (error) {
    console.error('初始化失败:', error)
  }
})

// 组件卸载时清理
onUnmounted(() => {
  // 清理可能的定时器等资源
})
</script>

<style scoped>
.system-control-content {
  width: 100%;
  min-height: calc(100vh - 64px);
  background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
  padding: 2rem;
  max-width: 1600px;
  margin: 0 auto;
  overflow-y: auto;
}

/* 功能选项卡样式 */
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
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 0.5rem;
  font-size: 1.2rem;
  transition: all 0.3s ease;
}

.tab-button:hover .tab-icon {
  transform: scale(1.1);
}

.tab-text {
  font-weight: 600;
}

/* 使用统计部分样式 */
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

.stats-container {
  display: flex;
  flex-wrap: wrap;
  gap: 2rem;
  justify-content: space-between;
}

.stats-section {
  flex: 1;
  min-width: 300px;
}

.stats-title {
  font-size: 1.5rem;
  font-weight: 600;
  color: #1e293b;
  margin-bottom: 1rem;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .system-control-content {
    padding: 1rem;
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

  .stats-container {
    flex-direction: column;
  }

  .stats-section {
    min-width: 100%;
  }
}

@media (max-width: 480px) {
  .system-control-content {
    padding: 0.5rem;
  }

  .control-tabs {
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
  }

  .tab-button {
    white-space: nowrap;
    min-width: 120px;
  }
}
</style>
