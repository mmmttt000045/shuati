<template>
  <div class="quiz-home-page">
    <div class="container">
      <div v-if="messages.length > 0" class="messages">
        <div v-for="(message, index) in messages" :key="index" :class="['message', message.category]">
          {{ message.text }}
        </div>
      </div>

      <Loading v-if="loading" text="正在加载题库..." />

      <div v-else-if="Object.keys(subjects).length === 0" class="empty-state">暂无可用的题目文件</div>

      <div v-else class="subjects-grid">
        <!-- 科目选择列表 -->
        <div v-if="!selectedSubject" class="subjects-list">
          <div
            v-for="(subjectData, subject) in subjects"
            :key="subject"
            class="subject-card"
            @click="selectSubject(subject)"
          >
            <h2 class="subject-title">{{ subject }}</h2>
            <!-- 考试时间显示 -->
            <div v-if="subjectData.exam_time && !isExamExpired(subjectData.exam_time)" class="exam-time-info">
              <div class="exam-time-content">
                <span class="exam-time-icon">📅</span>
                <div class="exam-time-text">
                  <span class="exam-time-label">距离考试还有</span>
                  <span class="exam-time-days">{{ getDaysUntilExam(subjectData.exam_time) }}天</span>
                </div>
              </div>
            </div>
            <div class="subject-info">
              <span class="subject-count">{{ subjectData.files.length }}个题库</span>
              <span class="subject-total">共{{ getTotalQuestions(subjectData.files) }}题</span>
            </div>
            
          </div>
        </div>

        <!-- 题库选择列表 -->
        <div v-else class="files-container">
          <div class="back-button-container">
            <button class="back-button" @click="goBackToSubjects">
              <span class="back-arrow">←</span> 返回科目列表
            </button>
            <h2 class="selected-subject-title">{{ selectedSubject }}</h2>
          </div>

          <!-- 题目顺序选择 -->
          <div class="order-selection">
            <div class="order-options">
              <label class="order-option" :class="{ selected: questionOrder === 'random' }">
                <input
                  type="radio"
                  value="random"
                  v-model="questionOrder"
                  name="questionOrder"
                  class="order-radio"
                />
                <div class="option-content">
                  <span class="option-icon">🎲</span>
                  <div class="option-text">
                    <span class="option-name">乱序练习</span>
                    <span class="option-desc">题目随机打乱，提高练习效果</span>
                  </div>
                </div>
              </label>

              <label class="order-option" :class="{ selected: questionOrder === 'sequential' }">
                <input
                  type="radio"
                  value="sequential"
                  v-model="questionOrder"
                  name="questionOrder"
                  class="order-radio"
                />
                <div class="option-content">
                  <span class="option-icon">📋</span>
                  <div class="option-text">
                    <span class="option-name">顺序练习</span>
                    <span class="option-desc">按照原始顺序练习题目</span>
                  </div>
                </div>
              </label>
            </div>
          </div>

          <div class="files-grid">
            <div
              v-for="file in subjects[selectedSubject].files"
              :key="file.key"
              class="file-card"
              @click="startPractice(selectedSubject, file.key)"
            >
              <div class="file-card-header">
                <h3 class="file-title">{{ file.display }}</h3>
                <span class="file-count-badge">{{ file.count }}题</span>
              </div>

              <div class="file-card-content">
                <!-- 显示练习进度 -->
                <div v-if="file.progress" class="progress-section">
                  <div class="progress-details">
                    <div class="progress-text">
                      <span class="round-info">历史进度：第{{ file.progress.round_number }}轮</span>
                      <span class="progress-percent-badge">{{ file.progress.progress_percent.toFixed(2).replace(/\.?0+$/, '') }}%</span>
                    </div>
                    <div class="question-info">{{ file.progress.current_question }}/{{ file.progress.total_questions }}题</div>
                  </div>
                  <div class="progress-bar-container">
                    <div class="progress-bar-card">
                      <div
                        class="progress-bar-fill-card"
                        :style="{ width: file.progress.progress_percent + '%' }"
                      ></div>
                    </div>
                  </div>
                </div>

                <div v-else class="no-progress-section">
                  <div class="no-progress-icon">🎯</div>
                  <div class="no-progress-text">
                    <span class="status-title">准备开始</span>
                    <span class="status-desc">点击开始你的学习之旅</span>
                  </div>
                </div>
              </div>

            </div>
          </div>
        </div>
      </div>

      <!-- 自定义确认对话框 -->
      <div v-if="showConfirmDialog" class="confirm-overlay" @click="closeConfirmDialog">
        <div class="confirm-dialog" @click.stop>
          <div class="confirm-header">
            <div class="confirm-icon">📚</div>
            <h3 class="confirm-title">发现练习进度</h3>
          </div>

          <div class="confirm-content">
            <div class="session-info">
              <div class="session-detail">
                <span class="session-label">题库：</span>
                <span class="session-value">{{ confirmData.fileName }}</span>
              </div>
              <div class="session-detail">
                <span class="session-label">Order：</span>
                <span class="session-value">{{ confirmData.order }}</span>
              </div>
              <div class="session-detail">
                <span class="session-label">进度：</span>
                <span class="session-value">第{{ confirmData.progress?.current }}/{{ confirmData.progress?.total }}题</span>
              </div>
              <div class="session-detail">
                <span class="session-label">轮次：</span>
                <span class="session-value">第{{ confirmData.progress?.round }}轮</span>
              </div>
            </div>

            <div class="progress-visual">
              <div class="progress-bar-large">
                <div
                  class="progress-bar-fill-large"
                  :style="{ width: confirmData.progressPercent + '%' }"
                ></div>
              </div>
              <div class="progress-text-large">{{ confirmData.progressPercent }}% 完成</div>
            </div>

            <p class="confirm-message">
              你想要继续之前的练习进度，还是重新开始？
            </p>
          </div>

          <div class="confirm-actions">
            <button class="confirm-btn confirm-btn-continue" @click="handleConfirmContinue">
              <span class="btn-icon">📖</span>
              继续练习
            </button>
            <button class="confirm-btn confirm-btn-restart" @click="handleConfirmRestart">
              <span class="btn-icon">🔄</span>
              重新开始
            </button>
            <button class="confirm-btn confirm-btn-cancel" @click="closeConfirmDialog">
              <span class="btn-icon">❌</span>
              取消
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script lang="ts" setup>
import { onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useToast } from 'vue-toastification'
import { apiService } from '@/services/api'
import { useAuthStore } from '@/stores/auth'
import type { FlashMessage, SubjectFile, SubjectData } from '@/types'
import Loading from '@/components/common/Loading.vue'

const router = useRouter()
const toast = useToast()
const authStore = useAuthStore()
const subjects = ref<Record<string, SubjectData>>({})
const selectedSubject = ref<string>('')
const messages = ref<FlashMessage[]>([])
const loading = ref(false)
const questionOrder = ref<'random' | 'sequential'>('random')
const showConfirmDialog = ref(false)
const confirmData = ref<{
  fileName: string;
  subject: string;
  order?: string;
  progress?: { current: number; total: number; round: number };
  progressPercent: number;
  sessionStatus?: any;
  tikuId: string;
}>({
  fileName: '',
  subject: '',
  progressPercent: 0,
  tikuId: ''
})

const getTotalQuestions = (files: SubjectFile[]) => {
  return files.reduce((total, file) => total + file.count, 0)
}

// 计算距离考试还有多少天
const getDaysUntilExam = (examTime: string) => {
  if (!examTime) return 0
  const examDate = new Date(examTime)
  const today = new Date()
  const diffTime = examDate.getTime() - today.getTime()
  const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24))
  return Math.max(0, diffDays)
}

// 检查考试是否已过期
const isExamExpired = (examTime: string) => {
  if (!examTime) return true
  const examDate = new Date(examTime)
  const today = new Date()
  return examDate < today
}

const selectSubject = (subject: string) => {
  selectedSubject.value = subject
  toast.success(`已选择科目：${subject}`, {
    timeout: 2000
  })
}

const goBackToSubjects = () => {
  selectedSubject.value = ''
  toast.success('已返回科目列表', {
    timeout: 2000
  })
}

const startPractice = async (subject: string, fileName: string) => {
  loading.value = true

  try {
    // 获取题库ID - 需要从subjects数据中找到对应的tiku_id
    const file = subjects.value[subject]?.files?.find(f => f.key === fileName)
    if (!file || !file.tiku_id) {
      throw new Error('未找到题库ID信息')
    }

    // 正常启动练习，使用新的URL格式
    const orderText = questionOrder.value === 'random' ? '乱序练习' : '顺序练习'
    toast.success(`开始${orderText} 🎯`, {
      timeout: 2000
    })

    router.push({
      name: 'practice',
      query: {
        tikuid: file.tiku_id.toString(),
        order: questionOrder.value,
      },
    })
  } catch (error) {
    console.error('Error starting practice:', error)
    toast.error(error instanceof Error ? error.message : '启动练习失败', {
      timeout: 4000
    })
  } finally {
    loading.value = false
  }
}

const handleConfirmContinue = async () => {
  // 继续之前的练习
  showConfirmDialog.value = false
  toast.success('继续之前的练习进度 📚', {
    timeout: 2000
  })
  router.push({
    name: 'practice',
    query: {
      tikuid: confirmData.value.tikuId,
      order: 'random'  // 默认使用随机顺序
    },
  })
}

const handleConfirmRestart = async () => {
  // 重新开始练习，使用新的URL格式
  showConfirmDialog.value = false
  loading.value = true

  try {
    toast.info('重新开始练习 🔄', {
      timeout: 2000
    })

    // 启动成功后跳转，使用新的URL格式
    const orderText = questionOrder.value === 'random' ? '乱序练习' : '顺序练习'
    toast.success(`开始${orderText} 🎯`, {
      timeout: 2000
    })

    router.push({
      name: 'practice',
      query: {
        tikuid: confirmData.value.tikuId,
        order: questionOrder.value,
      },
    })
  } catch (error) {
    console.error('Error restarting practice:', error)
    toast.error(error instanceof Error ? error.message : '重新开始失败', {
      timeout: 4000
    })
  } finally {
    loading.value = false
  }
}

const closeConfirmDialog = () => {
  showConfirmDialog.value = false
  loading.value = false
}

onMounted(async () => {
  loading.value = true
  try {
    // 首先确保用户已认证
    if (!authStore.isAuthenticated) {
      await authStore.checkAuth()
      if (!authStore.isAuthenticated) {
        toast.error('用户认证已过期，请重新登录', {
          timeout: 3000
        })
        router.push('/login')
        return
      }
    }

    const response = await apiService.getFileOptions()
    subjects.value = response.subjects
    if (response.message) {
      // 显示欢迎或状态信息
      toast.info(response.message, {
        timeout: 3000
      })
      // 同时在页面上保留重要信息
      messages.value.push({
        category: 'info',
        text: response.message,
      })
    }
  } catch (error) {
    console.error('Error fetching subjects:', error)
    // 如果是认证错误，不显示错误信息，因为用户已被重定向到登录页
    if (error instanceof Error && error.message.includes('登录已过期')) {
      return
    }
    toast.error(error instanceof Error ? error.message : '获取科目列表失败', {
      timeout: 5000
    })
  } finally {
    loading.value = false
  }
})

// 监听题目顺序变化
watch(questionOrder, (newOrder, oldOrder) => {
  if (oldOrder) { // 避免初始化时触发
    const orderText = newOrder === 'random' ? '乱序练习模式' : '顺序练习模式'
    const icon = newOrder === 'random' ? '🎲' : '📋'
    toast.info(`已切换到${orderText} ${icon}`, {
      timeout: 2000
    })
  }
})
</script>

<style scoped>
.quiz-home-page {
  width: 100%;
  min-height: calc(100vh - 64px);
  padding-top: 2rem;
}

/* 确保内容容器在wrapper内部正确布局 */
.container {
  position: relative;
  width: 100%;
  max-width: 95%; /* 改为95%以充分利用空间 */
  margin: 0 auto;
  padding: var(--space-8);
  min-height: 100vh;
  box-sizing: border-box;
}

.page-title {
  text-align: center;
  margin-bottom: 4rem;
  color: #1e293b;
  font-size: 2.75rem;
  font-weight: 800;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  position: relative;
  letter-spacing: -0.5px;
}

.page-title::after {
  content: '';
  position: absolute;
  bottom: -1rem;
  left: 50%;
  transform: translateX(-50%);
  width: 80px;
  height: 4px;
  background: linear-gradient(to right, #3b82f6, #2563eb);
  border-radius: 2px;
}

.messages {
  margin-bottom: 2rem;
  max-width: 95%; /* 改为95%以充分利用空间 */
  margin-left: auto;
  margin-right: auto;
}

.message {
  padding: 1.25rem 1.75rem;
  margin-bottom: 1rem;
  border-radius: 12px;
  font-weight: 500;
  animation: slideIn 0.3s ease-out;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

@keyframes slideIn {
  from {
    transform: translateY(-10px);
    opacity: 0;
  }
  to {
    transform: translateY(0);
    opacity: 1;
  }
}

.message.error {
  background-color: #fef2f2;
  color: #dc2626;
  border-left: 4px solid #dc2626;
}

.message.info {
  background-color: #f0f9ff;
  color: #0369a1;
  border-left: 4px solid #0369a1;
}

.empty-state {
  text-align: center;
  padding: 4rem 2rem;
  background-color: white;
  border-radius: 16px;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
  color: #64748b;
  font-size: 1.1rem;
  max-width: 600px;
  margin: 0 auto;
}

.subjects-grid {
  animation: fadeIn 0.4s ease-out;
}

.subjects-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 2rem;
  width: 100%;
  padding: 1rem;
  max-width: 95%; /* 改为95%以充分利用空间 */
  margin: 0 auto;
  align-items: stretch; /* 确保所有卡片高度一致 */
}

.subject-card {
  background-color: white;
  border-radius: 16px;
  padding: 2rem;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
  cursor: pointer;
  transition: all 0.3s ease;
  border: 2px solid transparent;
  position: relative;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  min-height: 160px; /* 设置最小高度确保统一 */
  height: 100%; /* 让卡片填满网格单元格 */
}

.subject-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
  background: linear-gradient(to right, #3b82f6, #2563eb);
  opacity: 0;
  transition: opacity 0.3s ease;
}

.subject-card:hover {
  transform: translateY(-6px);
  box-shadow:
    0 20px 25px -5px rgba(0, 0, 0, 0.1),
    0 10px 10px -5px rgba(0, 0, 0, 0.04);
}

.subject-card:hover::before {
  opacity: 1;
}

.subject-title {
  font-size: 1.5rem;
  font-weight: 600;
  color: #1e293b;
  margin-bottom: 1rem; /* 增加标题的下边距，让分割线更靠下 */
  line-height: 1.3;
  min-height: 3rem; /* 为标题设置最小高度，约2行文字 */
  display: -webkit-box;
  -webkit-line-clamp: 2; /* 限制为最多2行 */
  -webkit-box-orient: vertical;
  overflow: hidden;
  text-overflow: ellipsis;
  word-break: break-word;
}

.subject-info {
  display: flex;
  justify-content: space-between;
  margin-top: auto; /* 推到底部 */
  padding-top: 1rem; /* 增加顶部间距 */
  border-top: 1px solid #e2e8f0;
  flex-shrink: 0; /* 防止压缩 */
}

.subject-count,
.subject-total {
  background-color: #f8fafc;
  padding: 0.5rem 1rem;
  border-radius: 999px;
  color: #475569;
  font-size: 0.9rem;
  font-weight: 500;
  transition: all 0.2s ease;
}

.subject-card:hover .subject-count,
.subject-card:hover .subject-total {
  background-color: #f1f5f9;
  color: #3b82f6;
}

.files-container {
  width: 100%;
  max-width: 95%; /* 改为95%以充分利用空间 */
  margin: 0 auto;
  padding: 2rem;
  background-color: white;
  border-radius: 20px;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
}

.back-button-container {
  margin-bottom: 2.5rem;
}

.back-button {
  display: flex;
  align-items: center;
  padding: 0.875rem 1.75rem;
  background-color: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  color: #334155;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  font-size: 1.1rem;
}

.back-button:hover {
  background-color: #f1f5f9;
  transform: translateX(-4px);
  color: #3b82f6;
  border-color: #3b82f6;
}

.back-arrow {
  margin-right: 0.75rem;
  font-size: 1.3rem;
  transition: transform 0.2s ease;
}

.back-button:hover .back-arrow {
  transform: translateX(-4px);
}

.selected-subject-title {
  font-size: 2.25rem;
  color: #1e293b;
  margin-bottom: 2.5rem;
  padding-bottom: 1rem;
  border-bottom: 2px solid #e2e8f0;
  font-weight: 700;
}

.order-selection {
  margin-bottom: 2.5rem;
}

.order-title {
  font-size: 1.5rem;
  color: #1e293b;
  margin-bottom: 1rem;
  font-weight: 600;
}

.order-options {
  display: flex;
  gap: 1rem;
}

.order-option {
  flex: 1;
  display: flex;
  align-items: center;
  cursor: pointer;
  padding: 1.25rem;
  border: 2px solid #e2e8f0;
  border-radius: 12px;
  transition: all 0.3s ease;
  background-color: white;
  position: relative;
}

.order-option:hover {
  background-color: #f8fafc;
  border-color: #3b82f6;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.15);
}

.order-option.selected {
  background-color: #eff6ff;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.order-radio {
  position: absolute;
  opacity: 0;
  width: 1px;
  height: 1px;
}

.option-content {
  display: flex;
  align-items: center;
  width: 100%;
}

.option-icon {
  font-size: 2rem;
  margin-right: 1rem;
  flex-shrink: 0;
}

.option-text {
  display: flex;
  flex-direction: column;
  flex: 1;
}

.option-name {
  font-size: 1.2rem;
  font-weight: 600;
  color: #1e293b;
  margin-bottom: 0.5rem;
}

.option-desc {
  font-size: 0.95rem;
  color: #64748b;
  line-height: 1.4;
}

.files-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 2rem;
  margin-top: 1rem;
  align-items: stretch; /* 确保所有卡片高度一致 */
}

.file-card {
  background-color: white;
  border-radius: 16px;
  padding: 2rem;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
  cursor: pointer;
  transition: all 0.3s ease;
  border: 2px solid transparent;
  position: relative;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  min-height: 200px; /* 设置最小高度 */
  height: 100%; /* 让卡片填满网格单元格 */
}

.file-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
  background: linear-gradient(to right, #3b82f6, #2563eb);
  opacity: 0;
  transition: opacity 0.3s ease;
}

.file-card:hover {
  transform: translateY(-6px);
  box-shadow:
    0 20px 25px -5px rgba(0, 0, 0, 0.1),
    0 10px 10px -5px rgba(0, 0, 0, 0.04);
}

.file-card:hover::before {
  opacity: 1;
}

.file-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
}

.file-title {
  font-size: 1.5rem;
  font-weight: 600;
  color: #1e293b;
  line-height: 1.3;
  min-height: 3rem; /* 为标题设置最小高度，约2行文字 */
  display: -webkit-box;
  -webkit-line-clamp: 2; /* 限制为最多2行 */
  -webkit-box-orient: vertical;
  overflow: hidden;
  text-overflow: ellipsis;
  word-break: break-word;
}

.file-count-badge {
  background-color: #f8fafc;
  padding: 0.5rem 1rem;
  border-radius: 999px;
  color: #475569;
  font-size: 0.9rem;
  font-weight: 500;
}

.file-card-content {
  margin-bottom: 1.5rem;
  flex: 1; /* 让内容区域占据剩余空间 */
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.progress-section {
  margin-bottom: 1.5rem;
}

.progress-details {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.progress-text {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.progress-bar-container {
  width: 100%;
}

.progress-bar-card {
  width: 100%;
  height: 8px;
  background-color: #e2e8f0;
  border-radius: 4px;
  overflow: hidden;
}

.progress-bar-fill-card {
  height: 100%;
  background: linear-gradient(90deg, #3b82f6, #60a5fa);
  transition: width 0.3s ease;
  border-radius: 4px;
}

.round-info {
  font-size: 0.9rem;
  color: #3b82f6;
  font-weight: 600;
}

.progress-percent-badge {
  font-size: 0.9rem;
  color: #3b82f6;
  font-weight: 600;
  background-color: #eff6ff;
  padding: 0.25rem 0.75rem;
  border-radius: 999px;
  border: 1px solid #bfdbfe;
}

.question-info {
  font-size: 0.9rem;
  color: #64748b;
  font-weight: 500;
}

.no-progress-section {
  display: flex;
  align-items: center;
  padding: 1.5rem;
  background-color: #f8fafc;
  border-radius: 12px;
  border: 2px dashed #cbd5e1;
}

.no-progress-icon {
  font-size: 2rem;
  margin-right: 1rem;
  flex-shrink: 0;
}

.no-progress-text {
  display: flex;
  flex-direction: column;
}

.status-title {
  font-size: 1.1rem;
  font-weight: 600;
  color: #1e293b;
  margin-bottom: 0.25rem;
}

.status-desc {
  font-size: 0.9rem;
  color: #64748b;
  font-weight: 500;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* 自定义确认对话框样式 */
.confirm-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(4px);
  animation: overlayFadeIn 0.3s ease-out;
}

@keyframes overlayFadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

.confirm-dialog {
  background: white;
  border-radius: 20px;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
  max-width: 500px;
  width: 90%;
  max-height: 80vh;
  overflow-y: auto;
  animation: dialogSlideIn 0.3s ease-out;
}

@keyframes dialogSlideIn {
  from {
    opacity: 0;
    transform: translateY(-20px) scale(0.95);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

.confirm-header {
  text-align: center;
  padding: 2rem 2rem 1rem;
  border-bottom: 1px solid #e2e8f0;
}

.confirm-icon {
  font-size: 3rem;
  margin-bottom: 1rem;
  animation: bounce 0.6s ease-in-out;
}

.confirm-title {
  font-size: 1.5rem;
  font-weight: 600;
  color: #1e293b;
  margin: 0;
}

.confirm-content {
  padding: 2rem;
}

.session-info {
  background: #f8fafc;
  border-radius: 12px;
  padding: 1.5rem;
  margin-bottom: 2rem;
  border-left: 4px solid #3b82f6;
}

.session-detail {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.75rem;
}

.session-detail:last-child {
  margin-bottom: 0;
}

.session-label {
  font-weight: 500;
  color: #64748b;
}

.session-value {
  font-weight: 600;
  color: #1e293b;
}

.progress-visual {
  margin-bottom: 2rem;
}

.progress-bar-large {
  width: 100%;
  height: 12px;
  background-color: #e2e8f0;
  border-radius: 6px;
  overflow: hidden;
  margin-bottom: 0.75rem;
  box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.1);
}

.progress-bar-fill-large {
  height: 100%;
  background: linear-gradient(90deg, #3b82f6, #60a5fa, #34d399);
  transition: width 0.8s ease;
  border-radius: 6px;
  position: relative;
}

.progress-bar-fill-large::after {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
  animation: shimmer 2s infinite;
}

@keyframes shimmer {
  0% {
    transform: translateX(-100%);
  }
  100% {
    transform: translateX(100%);
  }
}

.progress-text-large {
  text-align: center;
  font-size: 1rem;
  font-weight: 600;
  color: #3b82f6;
}

.confirm-message {
  font-size: 1.1rem;
  color: #475569;
  text-align: center;
  line-height: 1.6;
  margin: 0;
}

.confirm-actions {
  padding: 1.5rem 2rem 2rem;
  display: flex;
  gap: 1rem;
  justify-content: center;
  flex-wrap: wrap;
}

.confirm-btn {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.875rem 1.5rem;
  border-radius: 12px;
  font-weight: 600;
  font-size: 1rem;
  cursor: pointer;
  transition: all 0.3s ease;
  border: 2px solid transparent;
  min-width: 120px;
  justify-content: center;
}

.confirm-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.confirm-btn-continue {
  background: linear-gradient(135deg, #10b981, #34d399);
  color: white;
}

.confirm-btn-continue:hover {
  background: linear-gradient(135deg, #059669, #10b981);
  box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
}

.confirm-btn-restart {
  background: linear-gradient(135deg, #3b82f6, #60a5fa);
  color: white;
}

.confirm-btn-restart:hover {
  background: linear-gradient(135deg, #2563eb, #3b82f6);
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
}

.confirm-btn-cancel {
  background: #f8fafc;
  color: #64748b;
  border-color: #e2e8f0;
}

.confirm-btn-cancel:hover {
  background: #f1f5f9;
  color: #475569;
  border-color: #cbd5e1;
}

.btn-icon {
  font-size: 1.1rem;
}

/* 超大屏幕优化（新增） */
@media (min-width: 1920px) {
  .subjects-list {
    grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
    gap: 3rem;
  }

  .files-grid {
    grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
    gap: 2.5rem;
  }

  .subject-card {
    padding: 3rem;
    min-height: 180px; /* 超大屏幕下增加最小高度 */
  }

  .file-card {
    padding: 2.5rem;
    min-height: 220px; /* 超大屏幕下增加最小高度 */
  }

  .files-container {
    padding: 4rem;
  }
  
  .subject-title,
  .file-title {
    font-size: 1.6rem; /* 超大屏幕下稍微增大字体 */
    min-height: 2.8rem;
  }
}

/* 大屏幕优化 */
@media (min-width: 1400px) {
  .subjects-list {
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    gap: 2.5rem;
  }

  .files-grid {
    grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
    gap: 2rem;
  }

  .subject-card {
    padding: 2.5rem;
    min-height: 170px; /* 大屏幕下调整最小高度 */
  }

  .files-container {
    padding: 3rem;
  }

  .file-card {
    padding: 2rem;
    min-height: 210px; /* 大屏幕下调整最小高度 */
  }
}

/* 中等大屏幕 */
@media (min-width: 1200px) and (max-width: 1399px) {
  .subjects-list {
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  }
  
  .files-grid {
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  }
}

/* 平板横屏 */
@media (min-width: 769px) and (max-width: 1199px) {
  .container {
    max-width: 95%;
    padding: 1.5rem;
  }

  .subjects-list {
    grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
    gap: 1.5rem;
  }

  .files-container {
    max-width: 100%;
  }

  .files-grid {
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 1.5rem;
  }
}

/* 手机端 */
@media (max-width: 768px) {
  .quiz-home-page {
    padding-top: 1rem;
  }
  
  .container {
    padding: var(--space-4);
  }

  .page-title {
    font-size: 2rem;
    margin-bottom: 3rem;
  }

  .subjects-list {
    grid-template-columns: 1fr;
    gap: 1.5rem;
    padding: 0.5rem;
  }

  .files-container {
    padding: 1.5rem;
  }

  .files-grid {
    grid-template-columns: 1fr;
    gap: 1.5rem;
  }

  .selected-subject-title {
    font-size: 1.75rem;
  }

  .file-card {
    padding: 1.5rem;
  }

  .file-card-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.75rem;
  }

  .file-title {
    font-size: 1.25rem;
  }

  .file-count-badge {
    font-size: 0.9rem;
  }

  .progress-section,
  .no-progress-section {
    min-width: unset;
    width: 100%;
  }

  .no-progress-section {
    padding: 1rem;
  }

  .no-progress-icon {
    font-size: 1.5rem;
    margin-right: 0.75rem;
  }

  .order-options {
    flex-direction: column;
  }
}

@media (max-width: 576px) {
  .container {
    padding: var(--space-3);
  }
}

/* 移动端对话框优化 */
@media (max-width: 640px) {
  .confirm-dialog {
    width: 95%;
    margin: 1rem;
  }

  .confirm-header {
    padding: 1.5rem 1.5rem 1rem;
  }

  .confirm-content {
    padding: 1.5rem;
  }

  .confirm-actions {
    padding: 1rem 1.5rem 1.5rem;
    flex-direction: column;
  }

  .confirm-btn {
    width: 100%;
    min-width: unset;
  }

  .session-info {
    padding: 1rem;
  }

  .confirm-icon {
    font-size: 2.5rem;
  }

  .confirm-title {
    font-size: 1.25rem;
  }

  .confirm-message {
    font-size: 1rem;
  }
}

.exam-time-info {
  margin-top: 1.25rem;
  margin-bottom: 1.25rem;
}

.exam-time-content {
  display: flex;
  align-items: center;
  background: linear-gradient(135deg, #fef3c7, #fde68a);
  padding: 0.75rem 1rem;
  border-radius: 12px;
  border: 1px solid #fbbf24;
  box-shadow: 0 2px 4px rgba(251, 191, 36, 0.1);
}

.exam-time-icon {
  font-size: 1.2rem;
  margin-right: 0.75rem;
  flex-shrink: 0;
}

.exam-time-text {
  display: flex;
  flex-direction: column;
  flex: 1;
}

.exam-time-label {
  font-size: 0.8rem;
  color: #92400e;
  font-weight: 500;
  margin-bottom: 0.25rem;
}

.exam-time-days {
  font-size: 1rem;
  color: #b45309;
  font-weight: 700;
}

.subject-card:hover .exam-time-content {
  background: linear-gradient(135deg, #fde68a, #f59e0b);
  border-color: #f59e0b;
  transform: translateY(-1px);
  box-shadow: 0 4px 8px rgba(251, 191, 36, 0.2);
}
</style> 