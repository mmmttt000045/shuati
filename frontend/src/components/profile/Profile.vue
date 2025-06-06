<template>
  <div class="profile-container">
    <!-- 背景装饰元素 -->
    <div class="background-decoration">
      <div class="decoration-circle circle-1"></div>
      <div class="decoration-circle circle-2"></div>
      <div class="decoration-circle circle-3"></div>
    </div>

    <v-container fluid class="profile-wrapper">
      <!-- 页面标题区域 -->
      <div class="profile-hero">
        <div class="hero-content">
          <div class="hero-avatar">
            <v-avatar 
              :size="$vuetify.display.mobile ? 80 : 120" 
              class="hero-avatar-img elevation-8"
            >
              <span class="hero-avatar-text">{{ getUserInitial() }}</span>
            </v-avatar>
            <div class="hero-status-indicator" :class="{ active: userInfo?.is_enabled }"></div>
          </div>
          <div class="hero-info">
            <h1 class="hero-title">{{ userInfo?.username || '未知用户' }}</h1>
            <div class="hero-meta">
              <UserBadge v-if="userInfo" :model="userInfo.model" class="hero-badge" />
              <v-chip class="hero-chip" size="small" variant="outlined">
                <v-icon start size="small">mdi-email</v-icon>
                {{ userInfo?.email || `${userInfo?.username || 'user'}@example.com` }}
              </v-chip>
            </div>
          </div>
        </div>
      </div>

      <!-- 统计信息卡片 -->
      <v-row class="stats-row mb-6">
        <v-col cols="6" md="3">
          <v-card class="stat-card" elevation="2" rounded="xl">
            <v-card-text class="stat-card-content">
              <div class="stat-icon-wrapper primary">
                <v-icon class="stat-icon">mdi-calendar-plus</v-icon>
              </div>
              <div class="stat-info">
                <div class="stat-label">注册时间</div>
                <div class="stat-value">{{ formatShortDate(userInfo?.created_at) }}</div>
              </div>
            </v-card-text>
          </v-card>
        </v-col>
        <v-col cols="6" md="3">
          <v-card class="stat-card" elevation="2" rounded="xl">
            <v-card-text class="stat-card-content">
              <div class="stat-icon-wrapper success">
                <v-icon class="stat-icon">mdi-clock-check-outline</v-icon>
              </div>
              <div class="stat-info">
                <div class="stat-label">最后登录</div>
                <div class="stat-value">{{ formatShortDate(userInfo?.last_time_login) }}</div>
              </div>
            </v-card-text>
          </v-card>
        </v-col>
        <v-col cols="6" md="3">
          <v-card class="stat-card" elevation="2" rounded="xl">
            <v-card-text class="stat-card-content">
              <div class="stat-icon-wrapper info">
                <v-icon class="stat-icon">mdi-account-check</v-icon>
              </div>
              <div class="stat-info">
                <div class="stat-label">账户状态</div>
                <div class="stat-value">{{ userInfo?.is_enabled ? '正常' : '已禁用' }}</div>
              </div>
            </v-card-text>
          </v-card>
        </v-col>
        <v-col cols="6" md="3">
          <v-card class="stat-card" elevation="2" rounded="xl">
            <v-card-text class="stat-card-content">
              <div class="stat-icon-wrapper warning">
                <v-icon class="stat-icon">mdi-school</v-icon>
              </div>
              <div class="stat-info">
                <div class="stat-label">年级</div>
                <div class="stat-value">{{ getGradeDisplay() }}</div>
              </div>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>

      <!-- 主要内容区域 -->
      <v-row class="main-content-row">
        <v-col cols="12">
          <!-- 标签页导航 -->
          <v-card class="tabs-card mb-4" elevation="0" rounded="xl">
            <v-tabs 
              v-model="activeTab" 
              class="profile-tabs" 
              color="primary"
              slider-color="primary"
              show-arrows
              height="90"
            >
              <v-tab value="info">
                <v-icon start>mdi-account-edit</v-icon>
                个人信息
              </v-tab>
              <v-tab value="security">
                <v-icon start>mdi-shield-lock</v-icon>
                安全设置
              </v-tab>
            </v-tabs>
          </v-card>

          <!-- 标签页内容 -->
          <v-tabs-window v-model="activeTab" class="tabs-window">
            <!-- 个人信息标签页 -->
            <v-tabs-window-item value="info">
              <v-card class="content-card" elevation="2" rounded="xl">
                <v-card-title class="content-header">
                  <div class="header-content">
                    <div class="header-info">
                      <v-icon class="header-icon">mdi-account-details</v-icon>
                      <div>
                        <h3 class="header-title">个人信息</h3>
                        <p class="header-subtitle">管理您的个人资料和基本信息</p>
                      </div>
                    </div>
                    <v-btn
                      v-if="!isEditing"
                      color="primary"
                      variant="elevated"
                      class="edit-btn"
                      @click="startEditing"
                      :loading="loading"
                      rounded
                    >
                      <v-icon start>mdi-pencil</v-icon>
                      编辑信息
                    </v-btn>
                  </div>
                </v-card-title>
                
                <v-card-text class="content-body">
                  <v-form ref="infoForm" v-model="infoFormValid" @submit.prevent="saveUserInfo">
                    <div class="form-section">
                      <h4 class="section-title">
                        <v-icon class="section-icon">mdi-account-outline</v-icon>
                        基本信息
                      </h4>
                      <v-row class="form-row">
                        <v-col cols="12" sm="6">
                          <v-text-field
                            v-model="editableInfo.username"
                            label="用户名"
                            prepend-inner-icon="mdi-account"
                            variant="outlined"
                            :readonly="!isEditing"
                            :rules="usernameRules"
                            counter="100"
                            hint="用户名用于登录系统"
                            persistent-hint
                            class="custom-field"
                          ></v-text-field>
                        </v-col>
                        <v-col cols="12" sm="6">
                          <v-text-field
                            v-model="editableInfo.email"
                            label="邮箱地址"
                            prepend-inner-icon="mdi-email"
                            variant="outlined"
                            :readonly="!isEditing"
                            :rules="emailRules"
                            hint="用于找回密码和接收通知"
                            persistent-hint
                            class="custom-field"
                          ></v-text-field>
                        </v-col>
                      </v-row>
                    </div>

                    <v-divider class="section-divider"></v-divider>

                    <div class="form-section">
                      <h4 class="section-title">
                        <v-icon class="section-icon">mdi-school-outline</v-icon>
                        学业信息
                      </h4>
                      <v-row class="form-row">
                        <v-col cols="12" sm="6">
                          <v-text-field
                            v-model="editableInfo.student_id"
                            label="学号"
                            prepend-inner-icon="mdi-school"
                            variant="outlined"
                            :readonly="!isEditing"
                            :rules="studentIdRules"
                            counter="15"
                            hint="您的学生学号"
                            persistent-hint
                            class="custom-field"
                          ></v-text-field>
                        </v-col>
                        <v-col cols="12" sm="6">
                          <v-select
                            v-model="editableInfo.grade"
                            :items="gradeOptions"
                            label="年级"
                            prepend-inner-icon="mdi-calendar-account"
                            variant="outlined"
                            :readonly="!isEditing"
                            hint="当前就读年级"
                            persistent-hint
                            class="custom-field"
                          ></v-select>
                        </v-col>
                        <v-col cols="12">
                          <v-text-field
                            v-model="editableInfo.major"
                            label="专业"
                            prepend-inner-icon="mdi-book-education"
                            variant="outlined"
                            :readonly="!isEditing"
                            counter="255"
                            hint="您所学的专业名称"
                            persistent-hint
                            class="custom-field"
                          ></v-text-field>
                        </v-col>
                      </v-row>
                    </div>
                    
                    <div v-if="isEditing" class="action-section">
                      <v-divider class="action-divider"></v-divider>
                      <div class="action-buttons">
                        <v-btn
                          variant="outlined"
                          color="grey-darken-1"
                          @click="cancelEditing"
                          :disabled="loading"
                          class="action-btn"
                          rounded
                        >
                          <v-icon start>mdi-close</v-icon>
                          取消
                        </v-btn>
                        <v-btn
                          color="primary"
                          type="submit"
                          :loading="loading"
                          :disabled="!infoFormValid"
                          class="action-btn"
                          variant="elevated"
                          rounded
                        >
                          <v-icon start>mdi-check</v-icon>
                          保存修改
                        </v-btn>
                      </div>
                    </div>
                  </v-form>
                </v-card-text>
              </v-card>
            </v-tabs-window-item>

            <!-- 安全设置标签页 -->
            <v-tabs-window-item value="security">
              <v-card class="content-card" elevation="2" rounded="xl">
                <v-card-title class="content-header">
                  <div class="header-content">
                    <div class="header-info">
                      <v-icon class="header-icon">mdi-shield-check</v-icon>
                      <div>
                        <h3 class="header-title">安全设置</h3>
                        <p class="header-subtitle">修改密码以保护您的账户安全</p>
                      </div>
                    </div>
                  </div>
                </v-card-title>
                
                <v-card-text class="content-body">
                  <v-form ref="passwordForm" v-model="passwordFormValid" @submit.prevent="changePassword">
                    <div class="form-section">
                      <h4 class="section-title">
                        <v-icon class="section-icon">mdi-lock-outline</v-icon>
                        密码修改
                      </h4>
                      <v-row class="form-row">
                        <v-col cols="12">
                          <v-text-field
                            v-model="passwordData.currentPassword"
                            label="当前密码"
                            type="password"
                            prepend-inner-icon="mdi-lock"
                            variant="outlined"
                            :rules="currentPasswordRules"
                            hint="请输入您的当前密码"
                            persistent-hint
                            class="custom-field"
                          ></v-text-field>
                        </v-col>
                        <v-col cols="12" sm="6">
                          <v-text-field
                            v-model="passwordData.newPassword"
                            label="新密码"
                            type="password"
                            prepend-inner-icon="mdi-lock-plus"
                            variant="outlined"
                            :rules="newPasswordRules"
                            hint="密码至少8位，包含字母和数字"
                            persistent-hint
                            class="custom-field"
                          ></v-text-field>
                        </v-col>
                        <v-col cols="12" sm="6">
                          <v-text-field
                            v-model="passwordData.confirmPassword"
                            label="确认新密码"
                            type="password"
                            prepend-inner-icon="mdi-lock-check"
                            variant="outlined"
                            :rules="confirmPasswordRules"
                            hint="请再次输入新密码"
                            persistent-hint
                            class="custom-field"
                          ></v-text-field>
                        </v-col>
                      </v-row>
                    </div>
                    
                    <div class="action-section">
                      <v-divider class="action-divider"></v-divider>
                      <div class="action-buttons">
                        <v-btn
                          variant="outlined"
                          color="grey-darken-1"
                          @click="resetPasswordForm"
                          :disabled="passwordLoading"
                          class="action-btn"
                          rounded
                        >
                          <v-icon start>mdi-refresh</v-icon>
                          重置
                        </v-btn>
                        <v-btn
                          color="primary"
                          type="submit"
                          :loading="passwordLoading"
                          :disabled="!passwordFormValid"
                          class="action-btn"
                          variant="elevated"
                          rounded
                        >
                          <v-icon start>mdi-shield-check</v-icon>
                          修改密码
                        </v-btn>
                      </div>
                    </div>
                  </v-form>
                </v-card-text>
              </v-card>
            </v-tabs-window-item>
          </v-tabs-window>
        </v-col>
      </v-row>
    </v-container>

    <!-- 成功/错误提示 -->
    <v-snackbar
      v-model="snackbar.show"
      :color="snackbar.color"
      :timeout="3000"
      location="top"
      rounded="pill"
      elevation="6"
    >
      <div class="snackbar-content">
        <v-icon start>{{ snackbar.color === 'success' ? 'mdi-check-circle' : 'mdi-alert-circle' }}</v-icon>
        {{ snackbar.message }}
      </div>
      <template #actions>
        <v-btn variant="text" icon @click="snackbar.show = false">
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </template>
    </v-snackbar>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import UserBadge from '@/components/common/UserBadge.vue'
import { apiService } from '@/services/api'

// Store
const authStore = useAuthStore()

// 响应式数据
const activeTab = ref('info')
const isEditing = ref(false)
const loading = ref(false)
const passwordLoading = ref(false)
const infoFormValid = ref(false)
const passwordFormValid = ref(false)

// 用户信息 - 修复类型问题
const userInfo = computed(() => authStore.user || null)
const editableInfo = reactive({
  username: '',
  email: '',
  student_id: '',
  major: '',
  grade: null as number | null
})

// 密码修改数据
const passwordData = reactive({
  currentPassword: '',
  newPassword: '',
  confirmPassword: ''
})

// 年级选项
const gradeOptions = [
  { title: '2020级', value: 2020 },
  { title: '2021级', value: 2021 },
  { title: '2022级', value: 2022 },
  { title: '2023级', value: 2023 },
  { title: '2024级', value: 2024 },
  { title: '2025级', value: 2025 },
  { title: '2026级', value: 2026 },
  { title: '2027级', value: 2027 }
]

// 提示信息
const snackbar = reactive({
  show: false,
  message: '',
  color: 'success'
})

// 表单验证规则
const usernameRules = [
  (v: string) => !!v || '用户名不能为空',
  (v: string) => (v && v.length >= 3) || '用户名至少3个字符',
  (v: string) => (v && v.length <= 100) || '用户名不能超过100个字符'
]

const emailRules = [
  (v: string) => !v || /.+@.+\..+/.test(v) || '请输入有效的邮箱地址'
]

const studentIdRules = [
  (v: string) => !v || v.length <= 15 || '学号不能超过15个字符'
]

const currentPasswordRules = [
  (v: string) => !!v || '请输入当前密码'
]

const newPasswordRules = [
  (v: string) => !!v || '请输入新密码',
  (v: string) => (v && v.length >= 8) || '密码至少8个字符',
  (v: string) => /(?=.*[a-zA-Z])(?=.*\d)/.test(v) || '密码必须包含字母和数字'
]

const confirmPasswordRules = [
  (v: string) => !!v || '请确认新密码',
  (v: string) => v === passwordData.newPassword || '两次输入的密码不一致'
]

// Methods
const fetchUserProfile = async () => {
  try {
    const result = await apiService.profile.getUserProfile()
    
    if (result.success && result.data?.user) {
      // 更新userInfo和editableInfo
      Object.assign(authStore.user || {}, result.data.user)
      initEditableInfo()
    } else {
      console.error('获取用户信息失败:', result.message)
    }
  } catch (error: any) {
    console.error('获取用户信息失败:', error)
  }
}

const getUserInitial = () => {
  return userInfo.value?.username?.charAt(0).toUpperCase() || 'U'
}

const formatDate = (dateString: string | null | undefined) => {
  if (!dateString) return '暂无'
  return new Date(dateString).toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

const formatShortDate = (dateString: string | null | undefined) => {
  if (!dateString) return '暂无'
  const date = new Date(dateString)
  const now = new Date()
  const diffTime = Math.abs(now.getTime() - date.getTime())
  const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24))
  
  if (diffDays === 0) return '今天'
  if (diffDays === 1) return '昨天'
  if (diffDays < 7) return `${diffDays}天前`
  if (diffDays < 30) return `${Math.ceil(diffDays / 7)}周前`
  if (diffDays < 365) return `${Math.ceil(diffDays / 30)}月前`
  return `${Math.ceil(diffDays / 365)}年前`
}

const getGradeDisplay = () => {
  if (!userInfo.value?.grade) return '未设置'
  const grade = gradeOptions.find(g => g.value === userInfo.value?.grade)
  return grade?.title || '未知'
}

const initEditableInfo = () => {
  editableInfo.username = userInfo.value?.username || ''
  editableInfo.email = userInfo.value?.email || ''
  editableInfo.student_id = userInfo.value?.student_id || ''
  editableInfo.major = userInfo.value?.major || ''
  editableInfo.grade = userInfo.value?.grade ?? null
}

const startEditing = () => {
  isEditing.value = true
  initEditableInfo()
}

const cancelEditing = () => {
  isEditing.value = false
  initEditableInfo()
}

const saveUserInfo = async () => {
  if (!infoFormValid.value || !userInfo.value) return
  
  loading.value = true
  try {
    // 调用API更新用户信息
    const profileData = {
      ...editableInfo,
      grade: editableInfo.grade ?? undefined
    }
    const result = await apiService.profile.updateUserProfile(profileData)
    
    if (result.success) {
      // 更新store中的用户信息
      Object.assign(userInfo.value, editableInfo)
      
      isEditing.value = false
      showSnackbar('个人信息更新成功', 'success')
    } else {
      throw new Error(result.message || '更新失败')
    }
  } catch (error: any) {
    console.error('更新用户信息失败:', error)
    showSnackbar(error.message || '更新失败，请稍后重试', 'error')
  } finally {
    loading.value = false
  }
}

const changePassword = async () => {
  if (!passwordFormValid.value) return
  
  passwordLoading.value = true
  try {
    // 调用API修改密码
    const result = await apiService.profile.changePassword({
      currentPassword: passwordData.currentPassword,
      newPassword: passwordData.newPassword,
      confirmPassword: passwordData.confirmPassword
    })
    
    if (result.success) {
      resetPasswordForm()
      showSnackbar('密码修改成功', 'success')
    } else {
      throw new Error(result.message || '密码修改失败')
    }
  } catch (error: any) {
    console.error('修改密码失败:', error)
    showSnackbar(error.message || '密码修改失败，请检查当前密码是否正确', 'error')
  } finally {
    passwordLoading.value = false
  }
}

const resetPasswordForm = () => {
  passwordData.currentPassword = ''
  passwordData.newPassword = ''
  passwordData.confirmPassword = ''
}

const showSnackbar = (message: string, color: string = 'success') => {
  snackbar.message = message
  snackbar.color = color
  snackbar.show = true
}

// 生命周期
onMounted(() => {
  fetchUserProfile()
})
</script>

<style scoped>
.profile-container {
  min-height: 100vh;
  position: relative;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  overflow-x: hidden;
}

/* 背景装饰 */
.background-decoration {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  pointer-events: none;
  overflow: hidden;
}

.decoration-circle {
  position: absolute;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(10px);
}

.circle-1 {
  width: 300px;
  height: 300px;
  top: -150px;
  right: -150px;
  animation: float 6s ease-in-out infinite;
}

.circle-2 {
  width: 200px;
  height: 200px;
  bottom: -100px;
  left: -100px;
  animation: float 8s ease-in-out infinite reverse;
}

.circle-3 {
  width: 150px;
  height: 150px;
  top: 50%;
  right: 10%;
  animation: float 7s ease-in-out infinite;
}

@keyframes float {
  0%, 100% { transform: translateY(0px) rotate(0deg); }
  50% { transform: translateY(-20px) rotate(180deg); }
}

/* 主容器 */
.profile-wrapper {
  position: relative;
  z-index: 1;
  padding: 2rem 1rem;
  max-width: 1200px;
  margin: 0 auto;
}

/* 英雄区域 */
.profile-hero {
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(20px);
  border-radius: 24px;
  padding: 3rem 2rem;
  margin-bottom: 2rem;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
}

.hero-content {
  display: flex;
  align-items: center;
  gap: 2rem;
  flex-wrap: wrap;
}

.hero-avatar {
  position: relative;
  flex-shrink: 0;
}

.hero-avatar-img {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
  border: 4px solid rgba(255, 255, 255, 0.9);
  box-shadow: 0 10px 30px rgba(102, 126, 234, 0.3);
}

.hero-avatar-text {
  font-size: 3rem;
  font-weight: 700;
  color: white;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
}

.hero-status-indicator {
  position: absolute;
  bottom: 8px;
  right: 8px;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #ef4444;
  border: 3px solid white;
  transition: all 0.3s ease;
}

.hero-status-indicator.active {
  background: #22c55e;
  box-shadow: 0 0 0 3px rgba(34, 197, 94, 0.3);
}

.hero-info {
  flex: 1;
  min-width: 200px;
}

.hero-title {
  font-size: 2.5rem;
  font-weight: 700;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  background-clip: text;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  margin-bottom: 1rem;
  line-height: 1.2;
}

.hero-meta {
  display: flex;
  align-items: center;
  gap: 1rem;
  flex-wrap: wrap;
}

.hero-badge {
  transform: scale(1.1);
}

.hero-chip {
  background: rgba(102, 126, 234, 0.1) !important;
  color: #667eea !important;
  border-color: rgba(102, 126, 234, 0.3) !important;
}

/* 统计卡片 */
.stats-row {
  margin: 0 -0.5rem;
}

.stats-row .v-col {
  padding: 0 0.5rem;
}

.stat-card {
  background: rgba(255, 255, 255, 0.95) !important;
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.2);
  transition: all 0.3s ease;
  height: 100%;
}

.stat-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.15);
}

.stat-card-content {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1.5rem 1rem !important;
}

.stat-icon-wrapper {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.stat-icon-wrapper.primary {
  background: linear-gradient(135deg, #667eea, #764ba2);
}

.stat-icon-wrapper.success {
  background: linear-gradient(135deg, #22c55e, #16a34a);
}

.stat-icon-wrapper.info {
  background: linear-gradient(135deg, #3b82f6, #1d4ed8);
}

.stat-icon-wrapper.warning {
  background: linear-gradient(135deg, #f59e0b, #d97706);
}

.stat-icon {
  color: white !important;
  font-size: 1.5rem;
}

.stat-info {
  flex: 1;
  min-width: 0;
}

.stat-label {
  font-size: 0.875rem;
  color: #6b7280;
  font-weight: 500;
  margin-bottom: 0.25rem;
}

.stat-value {
  font-size: 1rem;
  color: #374151;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* 标签页 */
.tabs-card {
  background: rgba(255, 255, 255, 0.95) !important;
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.2);
}

.profile-tabs {
  padding: 1rem;
}

/* Vuetify标签页样式重置 */
.profile-tabs :deep(.v-tab) {
  text-transform: none !important;
  font-weight: 600 !important;
  font-size: 1rem !important;
  min-height: 90px !important;
  border-radius: 12px !important;
  margin: 0 0.5rem !important;
  padding: 1.5rem 1.5rem !important;
  opacity: 1 !important;
  color: #6b7280 !important;
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  flex-direction: row !important;
  gap: 0.5rem !important;
}

.profile-tabs :deep(.v-tab .v-icon) {
  margin: 0 !important;
  font-size: 1.125rem !important;
}

.profile-tabs :deep(.v-tab__content) {
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  gap: 0.5rem !important;
  width: 100% !important;
  height: 100% !important;
}

.profile-tabs :deep(.v-tab--selected) {
  background: rgba(102, 126, 234, 0.12) !important;
  color: #667eea !important;
}

.profile-tabs :deep(.v-tab:hover) {
  background: rgba(102, 126, 234, 0.08) !important;
  color: #667eea !important;
}

/* 内容卡片 */
.content-card {
  background: rgba(255, 255, 255, 0.95) !important;
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.2);
}

.content-header {
  padding: 2rem !important;
  border-bottom: 1px solid rgba(0, 0, 0, 0.08);
}

.header-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  width: 100%;
  flex-wrap: wrap;
}

.header-info {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.header-icon {
  color: #667eea;
  font-size: 2rem;
}

.header-title {
  font-size: 1.5rem;
  font-weight: 700;
  color: #374151;
  margin-bottom: 0.25rem;
}

.header-subtitle {
  font-size: 0.95rem;
  color: #6b7280;
  margin: 0;
}

.edit-btn {
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3) !important;
  text-transform: none !important;
  font-weight: 600 !important;
}

/* 表单内容 */
.content-body {
  padding: 2rem !important;
}

.form-section {
  margin-bottom: 2rem;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  font-size: 1.2rem;
  font-weight: 600;
  color: #374151;
  margin-bottom: 1.5rem;
}

.section-icon {
  color: #667eea;
}

.section-divider {
  margin: 2rem 0;
  opacity: 0.6;
}

.form-row {
  margin: 0 -0.5rem;
}

.form-row .v-col {
  padding: 0 0.5rem 1rem;
}

.custom-field :deep(.v-input__control) {
  border-radius: 12px;
}

.custom-field :deep(.v-field) {
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.8);
}

.custom-field :deep(.v-field--focused) {
  box-shadow: 0 0 0 2px rgba(102, 126, 234, 0.2);
}

/* 操作区域 */
.action-section {
  margin-top: 2rem;
}

.action-divider {
  margin: 1.5rem 0;
}

.action-buttons {
  display: flex;
  justify-content: flex-end;
  gap: 1rem;
  flex-wrap: wrap;
}

.action-btn {
  min-width: 120px;
  text-transform: none !important;
  font-weight: 600 !important;
}

/* 提示框 */
.snackbar-content {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

/* 响应式设计 */
@media (max-width: 960px) {
  .profile-wrapper {
    padding: 1rem 0.5rem;
  }
  
  .profile-hero {
    padding: 2rem 1.5rem;
  }
  
  .hero-content {
    flex-direction: column;
    text-align: center;
    gap: 1.5rem;
  }
  
  .hero-title {
    font-size: 2rem;
  }
  
  .stat-card-content {
    padding: 1rem 0.75rem !important;
  }
  
  .profile-tabs {
    padding: 0.75rem;
  }
  
  .profile-tabs :deep(.v-tab) {
    min-height: 76px !important;
    padding: 1.25rem 1rem !important;
    margin: 0 0.25rem !important;
    font-size: 0.95rem !important;
  }
  
  .profile-tabs :deep(.v-tab .v-icon) {
    font-size: 1rem !important;
  }
  
  .content-header {
    padding: 1.5rem !important;
  }
  
  .content-body {
    padding: 1.5rem !important;
  }
  
  .header-content {
    flex-direction: column;
    align-items: flex-start;
  }
  
  .action-buttons {
    justify-content: stretch;
  }
  
  .action-btn {
    flex: 1;
  }
}

@media (max-width: 600px) {
  .profile-wrapper {
    padding: 0.5rem;
  }
  
  .profile-hero {
    padding: 1.5rem 1rem;
    margin-bottom: 1rem;
  }
  
  .hero-title {
    font-size: 1.75rem;
  }
  
  .hero-meta {
    justify-content: center;
  }
  
  .stats-row {
    margin: 0 -0.25rem;
  }
  
  .stats-row .v-col {
    padding: 0 0.25rem 0.5rem;
  }
  
  .stat-card-content {
    flex-direction: column;
    text-align: center;
    padding: 1rem 0.5rem !important;
  }
  
  .stat-value {
    white-space: normal;
  }
  
  .profile-tabs {
    padding: 0.5rem;
  }
  
  .profile-tabs :deep(.v-tab) {
    min-height: 72px !important;
    padding: 1.125rem 0.75rem !important;
    margin: 0 0.125rem !important;
    font-size: 0.875rem !important;
  }
  
  .profile-tabs :deep(.v-tab .v-icon) {
    font-size: 1rem !important;
  }
  
  .content-header {
    padding: 1rem !important;
  }
  
  .content-body {
    padding: 1rem !important;
  }
  
  .section-title {
    font-size: 1.1rem;
  }
  
  .form-row .v-col {
    padding: 0 0.25rem 0.75rem;
  }
}

/* 深色模式支持 */
.v-theme--dark .profile-hero,
.v-theme--dark .tabs-card,
.v-theme--dark .content-card,
.v-theme--dark .stat-card {
  background: rgba(45, 55, 72, 0.95) !important;
  border-color: rgba(255, 255, 255, 0.1) !important;
}

.v-theme--dark .header-title {
  color: #e2e8f0 !important;
}

.v-theme--dark .header-subtitle {
  color: #a0aec0 !important;
}

.v-theme--dark .section-title {
  color: #e2e8f0 !important;
}

.v-theme--dark .stat-label {
  color: #a0aec0 !important;
}

.v-theme--dark .stat-value {
  color: #e2e8f0 !important;
}

.v-theme--dark .custom-field :deep(.v-field) {
  background: rgba(255, 255, 255, 0.05);
}

/* 动画效果 */
.tabs-window {
  animation: fadeInUp 0.3s ease-out;
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* 减少动画效果（无障碍支持） */
@media (prefers-reduced-motion: reduce) {
  .decoration-circle,
  .stat-card,
  .tab-item,
  .tabs-window {
    animation: none !important;
    transition: none !important;
  }
  
  .stat-card:hover {
    transform: none;
  }
}
</style>
