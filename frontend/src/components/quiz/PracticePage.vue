<template>
  <div class="practice-page-wrapper">
    <!-- 使用新的导航栏组件 -->
    <NavigationBar v-if="showNavigationBar" />
    
    <div class="container">
      <div class="practice-container">
        <!-- 标题区域 -->
        <header class="practice-title" :class="{ 'mobile-hidden': isMobileScreen }">
          <h1>
            {{ fileDisplayName }}
            <span v-if="orderMode" class="order-mode-badge">{{ orderMode }}</span>
            <span v-if="questionTypesText" class="question-types-badge">{{ questionTypesText }}</span>
          </h1>
        </header>

        <div class="practice-layout">
          <!-- 左侧主要内容区域 -->
          <main class="practice-main">
            <!-- 页面头部 -->
            <div class="page-header" :class="{ 'mobile-compact': isMobileScreen }">
              <button class="btn btn-navigate-back" :class="{ 'mobile-compact-btn': isMobileScreen }" @click="goBackToIndexPage">
                <span class="arrow">←</span>
                <span v-if="!isMobileScreen">返回首页</span>
              </button>
              <div v-if="progress" class="progress-bar-wrapper" :class="{ 'mobile-compact-progress': isMobileScreen }">
                <div class="progress-bar-text" :class="{ 'mobile-compact-text': isMobileScreen }">
                  <template v-if="isMobileScreen">
                    {{ progress.current }}/{{ progress.total }}
                  </template>
                  <template v-else>
                    第 {{ progress.round_number }} 轮 - 题目 {{ progress.current }} / {{ progress.total }}
                  </template>
                </div>
                <div class="progress-bar-visual">
                  <div
                    :style="{ width: progressPercentage + '%' }"
                    class="progress-bar-inner"
                  ></div>
                </div>
              </div>
            </div>

            <!-- 提示消息 -->
            <ul v-if="messages.length" class="flash-messages">
              <li v-for="(message, index) in messages" :key="index" :class="message.category">
                {{ message.text }}
              </li>
            </ul>

            <!-- 主要内容区域 -->
            <div class="content-container">
              <transition name="content-fade">
                <!-- 题目显示模式 -->
                <div v-if="isQuestionMode" key="question" class="question-section card" :class="{ 'content-loading': loadingSubmit }">
                  <div class="question-content">
                    <div class="question-text">
                      <span class="question-type-badge" :class="questionTypeBadgeClass">
                        {{ question?.type }}
                      </span>
                      <span :class="questionTextClass">{{ question?.question }}</span>
                    </div>
                  </div>

                  <form class="answer-form" @submit.prevent="submitAnswer">
                    <div class="options-grid">
                      <!-- 选择题选项 -->
                      <template v-if="isChoiceQuestion">
                        <label
                          v-for="(optionText, key) in shuffledMcqOptions"
                          :key="key"
                          :class="getOptionLabelClass(key)"
                          class="card-hover"
                        >
                          <input
                            :checked="isOptionSelected(key)"
                            :disabled="!isQuestionMode"
                            :name="getInputName(key)"
                            :type="question?.is_multiple_choice ? 'checkbox' : 'radio'"
                            :value="key"
                            @change="handleOptionSelect(key)"
                            class="option-input"
                          />
                          <span :class="getCustomDisplayClass(key)"></span>
                          <span class="option-key">{{ key }}</span>
                          <span class="option-text">{{ optionText }}</span>
                        </label>
                      </template>

                      <!-- 判断题选项 -->
                      <template v-else-if="isTrueFalseQuestion">
                        <label
                          v-for="(option, key) in tfOptions"
                          :key="key"
                          :class="{ 'option-label': true, selected: selectedAnswer === key }"
                          class="card-hover"
                        >
                          <input
                            :checked="selectedAnswer === key"
                            :disabled="!isQuestionMode"
                            name="answer_tf"
                            type="radio"
                            :value="key"
                            @change="handleOptionSelect(key)"
                            class="option-input"
                            required
                          />
                          <span
                            class="radio-custom-display"
                            :class="{ checked: selectedAnswer === key }"
                          ></span>
                          <span class="option-text">{{ option.text }}</span>
                        </label>
                      </template>

                      <!-- 无效题目 -->
                      <p v-else class="empty-state-message">题目数据不完整或类型无法识别。</p>
                    </div>

                    <div class="action-buttons">
                      <button :disabled="!canSubmitAnswer" class="btn btn-submit" type="submit">
                        <span v-if="loadingSubmit" class="loading-spinner"></span>
                        {{ loadingSubmit ? '提交中...' : '提交答案' }}
                      </button>
                      <button
                        :disabled="!canRevealAnswer"
                        :class="['btn', 'btn-reveal', { loading: loadingReveal }]"
                        type="button"
                        @click="revealAnswer"
                      >
                        <span v-if="loadingReveal" class="loading-spinner"></span>
                        {{ loadingReveal ? '加载中...' : '查看答案' }}
                      </button>
                    </div>
                  </form>
                </div>

                <!-- 反馈显示模式 -->
                <div v-else-if="isFeedbackMode" key="feedback" class="feedback-section card">
                  <!-- 历史查看提示 -->
                  <div v-if="isViewingHistory" class="history-notice">
                    <span class="history-icon">📋</span>
                    <span class="history-text">查看答题历史记录</span>
                  </div>

                  <div class="question-review-content">
                    <h4>题目回顾：</h4>
                    <p :class="questionReviewClass">{{ question?.question }}</p>

                    <div class="answer-comparison">
                      <!-- 选项展示 -->
                      <div v-if="hasOptionsToReview" class="options-review">
                        <strong>{{ optionsReviewTitle }}：</strong>
                        <div class="options-grid review-mode">
                          <div
                            v-for="(option, key) in optionsForReview"
                            :key="key"
                            :class="getReviewOptionClass(key)"
                          >
                            <span class="option-key">{{ key }}</span>
                            <span class="option-text">{{ getOptionText(option) }}</span>
                          </div>
                        </div>
                      </div>

                      <!-- 答错时的答案对比 -->
                      <template v-if="currentFeedback && !currentFeedback.is_correct">
                        <div class="answer-item">
                          <strong>正确答案：</strong>
                          <span class="correct-answer-text">{{
                            currentFeedback.correct_answer_display
                          }}</span>
                        </div>
                      </template>

                      <!-- 分析和知识点 -->
                      <div v-if="question?.analysis" class="answer-item">
                        <strong>题目分析：</strong>
                        <p>{{ question.analysis }}</p>
                      </div>

                      <div v-if="hasKnowledgePoints" class="answer-item">
                        <strong>知识点：</strong>
                        <div class="knowledge-points">
                          <span
                            v-for="(point, index) in question?.knowledge_points"
                            :key="index"
                            class="knowledge-point-tag"
                          >
                            {{ point }}
                          </span>
                        </div>
                      </div>

                      <div v-if="currentFeedback?.explanation" class="answer-item">
                        <strong>解释：</strong>
                        <p>{{ currentFeedback.explanation }}</p>
                      </div>
                    </div>
                  </div>

                  <div class="feedback-actions">
                    <button class="btn-continue" @click="handleFeedbackAction">
                      {{ feedbackButtonText }}
                    </button>
                  </div>
                </div>
              </transition>
            </div>

            <!-- 空状态 -->
            <div v-if="showEmptyState" class="empty-state-message card">
              <p>当前没有题目可以练习，或题目加载失败。</p>
            </div>
          </main>

          <!-- 右侧答题卡 -->
          <AnswerCard
            :questionStatuses="questionStatuses"
            :progress="progress"
            :currentQuestionIndex="currentQuestionIndex"
            :isViewingHistory="isViewingHistory"
            :canJumpToQuestion="canJumpToQuestion"
            :loadingSubmit="loadingSubmit"
            @jumpToQuestion="jumpToQuestion"
            @goToPrevious="goToPreviousQuestion"
            @goToNext="goToNextQuestion"
            @backToCurrent="backToCurrentQuestion"
          />
        </div>

        <footer class="footer-credit">Created by MingTai</footer>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, watch, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { useToast } from 'vue-toastification'
import type {
  Question,
  Progress,
  FlashMessage,
  Feedback,
  QuestionStatus as QuestionStatusType,
} from '@/types'
import { QUESTION_STATUS, isCorrectStatus, isWrongStatus, isUnansweredStatus } from '@/types'
import { apiService } from '@/services/api'
import { useAuthStore } from '@/stores/auth'
import NavigationBar from '@/components/layout/NavigationBar.vue'
import AnswerCard from './AnswerCard.vue'

interface QuestionStatus {
  status: QuestionStatusType
  number: number
  isCurrent: boolean
}

const props = defineProps<{
  tikuid: string
  order?: string
  types?: string  // 添加题型参数
  tiku_displayname?: string  // 添加题库显示名称参数
}>()

const router = useRouter()
const toast = useToast()
const authStore = useAuthStore()

// 控制导航栏显示状态
const showNavigationBar = ref(false)

// 响应式状态
const fileDisplayName = ref<string>('')
const orderMode = ref<string>('')  // 添加练习模式状态
const selectedQuestionTypes = ref<string[]>([])  // 添加题型状态
const question = ref<Question | null>(null)
const progress = ref<Progress | null>(null)
const messages = ref<FlashMessage[]>([])
const displayMode = ref<'question' | 'feedback'>('question')
const currentFeedback = ref<Feedback | null>(null)
const initializing = ref(true)
const selectedAnswer = ref<string>('')
const selectedAnswers = ref<Set<string>>(new Set())
const shuffledMcqOptions = ref<Record<string, string>>({})
const isViewingHistory = ref(false)
const questionStatuses = ref<Array<QuestionStatusType>>([])
const screenWidth = ref(typeof window !== 'undefined' ? window.innerWidth : 1024)

// 监听屏幕尺寸变化
const handleResize = () => {
  if (typeof window !== 'undefined') {
    screenWidth.value = window.innerWidth
  }
}

// 提交和揭示状态
const loadingSubmit = ref(false)
const loadingReveal = ref(false)

// 自动跳转相关状态
const autoNextTimer = ref<number | null>(null)
const autoNextCountdown = ref(0)
const showAutoNextHint = ref(false)

// 题目类型选项
const tfOptions = {
  T: { text: '正确' },
  F: { text: '错误' },
}

// 题型映射
const questionTypeNames = {
  'single_choice': '单选题',
  'multiple_choice': '多选题', 
  'judgment': '判断题',
  'other': '其他题型'
}

// 计算属性
const progressPercentage = computed(() => {
  if (!progress.value) return 0
  return (progress.value.current / progress.value.total) * 100
})

const currentQuestionIndex = computed(() => (progress.value ? progress.value.current - 1 : 0))

// 题型文本显示
const questionTypesText = computed(() => {
  if (selectedQuestionTypes.value.length === 0) return ''
  
  if (selectedQuestionTypes.value.length === Object.keys(questionTypeNames).length) {
    return '全部题型'
  }
  
  const typeNames = selectedQuestionTypes.value
    .map(type => questionTypeNames[type as keyof typeof questionTypeNames])
    .filter(Boolean)
  
  return typeNames.join('、')
})

// 小屏幕检测
const isMobileScreen = computed(() => screenWidth.value <= 768)

const showSessionInfo = computed(() => !initializing.value && displayMode.value === 'question')

const isQuestionMode = computed(() => displayMode.value === 'question' && question.value)

const isFeedbackMode = computed(
  () => displayMode.value === 'feedback' && currentFeedback.value && question.value,
)

const isChoiceQuestion = computed(
  () =>
    question.value?.type !== '判断题' &&
    question.value?.options_for_practice &&
    Object.keys(shuffledMcqOptions.value).length > 0,
)

const isTrueFalseQuestion = computed(() => question.value?.type === '判断题')

const questionTypeBadgeClass = computed(() => {
  if (!question.value) return ''
  return {
    'multiple-choice-badge': question.value.type === '多选题',
    'single-choice-badge': question.value.type === '单选题',
    'true-false-badge': question.value.type === '判断题',
  }
})

const canSubmitAnswer = computed(() => {
  if (loadingSubmit.value || !isQuestionMode.value || !question.value) return false

  if (question.value.type === '判断题') {
    return !!selectedAnswer.value
  }

  if (question.value.is_multiple_choice) {
    return selectedAnswers.value.size > 0
  }

  return !!selectedAnswer.value
})

const canRevealAnswer = computed(
  () => !loadingSubmit.value && !loadingReveal.value && isQuestionMode.value,
)

const showEmptyState = computed(
  () =>
    !initializing.value && !question.value && displayMode.value === 'question',
)

const autoNextCountdownText = computed(
  () => `${Math.ceil(autoNextCountdown.value)}秒后自动进入下一题`,
)

const hasOptionsToReview = computed(() => {
  if (!question.value) return false
  return question.value.type !== '判断题' ? !!question.value.options_for_practice : true
})

const optionsReviewTitle = computed(() =>
  question.value?.type === '判断题' ? '判断选项' : '所有选项',
)

const optionsForReview = computed(() => {
  if (!question.value) return {}
  return question.value.type === '判断题' ? tfOptions : question.value.options_for_practice || {}
})

const hasKnowledgePoints = computed(
  () => question.value?.knowledge_points && question.value.knowledge_points.length > 0,
)

const feedbackButtonText = computed(() => (isViewingHistory.value ? '返回当前题目' : '继续练习'))

const canJumpToQuestion = computed(
  () => (displayMode.value === 'question' || isViewingHistory.value) && !loadingSubmit.value,
)

const canGoPrevious = computed(() => !loadingSubmit.value && currentQuestionIndex.value > 0)

const canGoNext = computed(
  () =>
    !loadingSubmit.value && progress.value && currentQuestionIndex.value < progress.value.total - 1,
)

// 检测题目文本是否包含特殊空白字符（换行符、制表符、多个连续空格）
const hasSpecialWhitespace = computed(() => {
  if (!question.value?.question) return false
  const text = question.value.question
  // 检测换行符、制表符、或者连续的多个空格
  return /[\n\r\t]|  /.test(text)
})

// 题目文本的CSS类
const questionTextClass = computed(() => ({
  'question-text-content': true,
  'formatted-text': hasSpecialWhitespace.value, // 包含特殊空白字符，左对齐
  'plain-text': !hasSpecialWhitespace.value,     // 纯文本，居中对齐
}))

// 题目回顾文本的CSS类
const questionReviewClass = computed(() => ({
  'question-text-review': true,
  'formatted-text': hasSpecialWhitespace.value, // 包含特殊空白字符，左对齐
  'plain-text': !hasSpecialWhitespace.value,     // 纯文本，居中对齐
}))

// 方法
const getDisplayNameFromFilePath = (filePath: string): string => {
  try {
    const normalizedPath = filePath.replace(/\\/g, '/')
    const pathParts = normalizedPath.split('/')

    if (pathParts.length === 0) return filePath

    const filenameWithExt = pathParts[pathParts.length - 1]
    const displayName = filenameWithExt.replace(/\.(xlsx|xls)$/i, '')

    return displayName || filePath
  } catch (error) {
    console.error('Error extracting display name from file path:', error)
    return filePath
  }
}

const isOptionSelected = (key: string): boolean => {
  if (!question.value) return false
  return question.value.is_multiple_choice
    ? selectedAnswers.value.has(key)
    : selectedAnswer.value === key
}

const getInputName = (key: string): string => {
  if (!question.value) return ''
  return question.value.is_multiple_choice ? `answer_mcq_${key}` : 'answer_scq'
}

const getOptionLabelClass = (key: string) => ({
  'option-label': true,
  selected: isOptionSelected(key),
  'multiple-choice-option': question.value?.is_multiple_choice,
})

const getCustomDisplayClass = (key: string) => {
  if (!question.value) return ''
  const isSelected = isOptionSelected(key)
  return question.value.is_multiple_choice
    ? { 'checkbox-custom-display': true, checked: isSelected }
    : { 'radio-custom-display': true, checked: isSelected }
}

const getReviewOptionClass = (key: string) => {
  if (!currentFeedback.value || !question.value) return { 'option-review': true }

  const isCorrect =
    question.value.type === '判断题'
      ? question.value.answer === key
      : question.value.answer.includes(key)

  const isIncorrect =
    !currentFeedback.value.is_correct &&
    (question.value.type === '判断题'
      ? getUserAnswerFromTFDisplay(currentFeedback.value.user_answer_display) === key
      : currentFeedback.value.user_answer_display.startsWith(key) ||
        currentFeedback.value.user_answer_display.includes(` + ${key}.`))

  return {
    'option-review': true,
    'option-correct': isCorrect,
    'option-incorrect': isIncorrect,
  }
}

const getOptionText = (option: any): string => {
  return typeof option === 'string' ? option : option.text || ''
}

const handleFeedbackAction = () => {
  if (isViewingHistory.value) {
    backToCurrentQuestion()
  } else {
    handleContinueAfterReveal()
  }
}

// 自动跳转相关函数
const startAutoNextTimer = () => {
  // 添加延迟，让反馈页面先稳定显示
  setTimeout(() => {
    showAutoNextHint.value = true
    autoNextCountdown.value = 2

    const countdownInterval = setInterval(() => {
      autoNextCountdown.value -= 0.1
      if (autoNextCountdown.value <= 0) {
        clearInterval(countdownInterval)
        executeAutoNext()
      }
    }, 100)

    autoNextTimer.value = countdownInterval
  }, 300) // 延迟300ms显示自动跳转提示
}

const clearAutoNextTimer = () => {
  if (autoNextTimer.value) {
    clearInterval(autoNextTimer.value)
    autoNextTimer.value = null
  }
  showAutoNextHint.value = false
  autoNextCountdown.value = 0
}

const executeAutoNext = () => {
  clearAutoNextTimer()
  // 添加短暂延迟让UI稍微稳定
  setTimeout(() => {
    if (progress.value && currentQuestionIndex.value < progress.value.total - 1) {
      goToNextQuestion()
    }
  }, 100)
}

const handleOptionSelect = (key: string) => {
  if (!question.value) return

  if (question.value.is_multiple_choice) {
    if (selectedAnswers.value.has(key)) {
      selectedAnswers.value.delete(key)
    } else {
      selectedAnswers.value.add(key)
    }
  } else {
    selectedAnswer.value = key
  }
}

const resetState = () => {
  selectedAnswer.value = ''
  selectedAnswers.value = new Set()
  currentFeedback.value = null
  displayMode.value = 'question'
}

const updateQuestionStatus = (index: number, isCorrect: boolean) => {
  if (index >= 0 && index < questionStatuses.value.length) {
    questionStatuses.value[index] = isCorrect ? QUESTION_STATUS.CORRECT : QUESTION_STATUS.WRONG
  }
}

// 其他方法保持不变...
const getUserAnswerFromTFDisplay = (display: string): string => {
  if (!display) return ''
  if (display.includes('未作答')) return ''
  if (display.includes('正确')) return 'T'
  if (display.includes('错误')) return 'F'

  const trimmed = display.trim().toUpperCase()
  if (trimmed === 'T' || trimmed === 'F') return trimmed

  const match = display.match(/^([TF])\./)
  if (match) return match[1]

  return ''
}

const goToNextQuestion = () => {
  if (progress.value && currentQuestionIndex.value < progress.value.total - 1) {
    jumpToQuestion(currentQuestionIndex.value + 1)
  }
}

const goToPreviousQuestion = () => {
  if (progress.value && currentQuestionIndex.value > 0) {
    jumpToQuestion(currentQuestionIndex.value - 1)
  }
}

const jumpToQuestion = async (index: number) => {
  clearAutoNextTimer()

  try {
    if (index < 0 || index >= questionStatuses.value.length) {
      toast.error('题目索引无效', { timeout: 3000 })
      return
    }

    const questionStatus = questionStatuses.value[index]
    const isAnswered = !isUnansweredStatus(questionStatus)

    if (isAnswered) {
      try {
        const historyResponse = await apiService.getQuestionHistory(index)

        if (historyResponse.success && historyResponse.data?.question && historyResponse.data?.feedback) {
          question.value = historyResponse.data.question
          currentFeedback.value = historyResponse.data.feedback

          if (progress.value) {
            progress.value.current = index + 1
          }

          // 更新选项数据以确保反馈模式正常显示
          if (historyResponse.data.question.options_for_practice) {
            shuffledMcqOptions.value = { ...historyResponse.data.question.options_for_practice }
          } else {
            shuffledMcqOptions.value = {}
          }

          displayMode.value = 'feedback'
          isViewingHistory.value = true
          // 只清除选择状态，不重置反馈数据和显示模式
          selectedAnswer.value = ''
          selectedAnswers.value = new Set()
          return
        }
      } catch (error) {
        console.warn(`获取题目历史记录失败:`, error)
      }
    }

    if (isViewingHistory.value) {
      isViewingHistory.value = false
    }

    const response = await apiService.jumpToQuestion(index)
    if (response.success) {
      await loadQuestion()
    } else {
      toast.error(response.message || '跳转失败', { timeout: 3000 })
    }
  } catch (error) {
    console.error('Error jumping to question:', error)
    toast.error(error instanceof Error ? error.message : '跳转失败', {
      timeout: 4000,
    })
  }
}

const syncQuestionStatuses = async () => {
  try {
    const statusResponse = await apiService.getQuestionStatuses()
    if (statusResponse.success && statusResponse.data?.statuses && statusResponse.data.statuses.length > 0) {
      const currentStatusStr = JSON.stringify(questionStatuses.value)
      const newStatusStr = JSON.stringify(statusResponse.data.statuses)

      if (currentStatusStr !== newStatusStr) {
        questionStatuses.value = [...statusResponse.data.statuses]
      }
    }
  } catch (error) {
    console.warn('同步答题卡状态失败:', error)
  }
}

// 智能状态同步：只在确实需要时才请求
const syncQuestionStatusesIfNeeded = async (forceSync = false) => {
  // 如果是强制同步，或者状态数组全为未答状态（可能需要恢复历史状态）
  if (forceSync || questionStatuses.value.every(status => status === QUESTION_STATUS.UNANSWERED)) {
    await syncQuestionStatuses()
  }
}

// Helper function to process question data and update reactive state
const processQuestionDataAndUpdateState = (responseData: any, isNewSessionContext: boolean = false) => {
  const {
    question: newQuestion,
    progress: newProgress,
    flash_messages,
  } = responseData

  if (!newQuestion && !newProgress) { // If no question and no progress, likely nothing to practice
    question.value = null
    progress.value = null
    messages.value = flash_messages || []
    shuffledMcqOptions.value = {}
    questionStatuses.value = []
    if (selectedQuestionTypes.value.length === 0 && !props.types) {
      selectedQuestionTypes.value = Object.keys(questionTypeNames) // Default if completely empty start
    }
    return false
  }
  
  question.value = newQuestion || null
  progress.value = newProgress || null
  messages.value = flash_messages || []

  // 题型信息现在完全通过props获取，不再依赖session_config
  if (selectedQuestionTypes.value.length === 0 && !props.types) {
    // 只有在props没有题型信息时，才使用默认值
    selectedQuestionTypes.value = Object.keys(questionTypeNames)
  }

  if (newProgress) {
    const total = newProgress.total
    // Always ensure questionStatuses array is correctly sized.
    // If it's a new session context or total count differs, reset with UNANSWERED.
    // Otherwise, existing statuses are preserved for syncQuestionStatuses to update.
    if (isNewSessionContext || questionStatuses.value.length !== total) {
      questionStatuses.value = new Array(total).fill(QUESTION_STATUS.UNANSWERED)
    }
  } else {
    // No progress data, clear statuses. This case should be rare if questions exist.
    questionStatuses.value = []
  }

  if (newQuestion?.options_for_practice) {
    shuffledMcqOptions.value = { ...newQuestion.options_for_practice }
  } else {
    shuffledMcqOptions.value = {}
  }
  return !!newQuestion // Return true if a question was processed
}

onMounted(async () => {
  try {
    // 设置屏幕尺寸监听器
    if (typeof window !== 'undefined') {
      window.addEventListener('resize', handleResize)
    }
    
    // 隐藏导航栏，提供专注的练习体验
    showNavigationBar.value = false
    
    // 验证必需参数
    if (!props.tikuid) {
      toast.error('缺少题库ID参数', { timeout: 3000 })
      router.push('/')
      return
    }

    // 简化的显示信息初始化（避免不必要的API请求）
    initializeDisplayInfo()

    // 尝试获取当前题目或启动新练习
    let questionResponse = await apiService.getCurrentQuestion()

    if (questionResponse.success && questionResponse.data?.redirect_to_completed) {
      router.push('/completed')
      return
    }

    let isNewSession = false
    if (questionResponse.success && questionResponse.data?.question) {
      // 有现有会话，处理数据
      processQuestionDataAndUpdateState(questionResponse.data, false)
      // 智能同步：只有在需要恢复历史状态时才请求
      await syncQuestionStatusesIfNeeded()
    } else {
      // 没有现有会话，启动新练习
      console.warn('没有找到活跃的练习会话，启动新的练习会话')
      
      const shuffleQuestions = (props.order || 'random') === 'random'
      const typesToStart = selectedQuestionTypes.value.length > 0 ? selectedQuestionTypes.value : undefined

      const startResponse = await apiService.startPractice(
        props.tikuid,
        true, // 强制重启新会话
        shuffleQuestions,
        typesToStart
      )

      if (!startResponse.success) {
        throw new Error(startResponse.message || '启动练习失败')
      }
      
      isNewSession = true
      
      // 获取第一个题目
      questionResponse = await apiService.getCurrentQuestion()

      if (questionResponse.success && questionResponse.data?.redirect_to_completed) {
        router.push('/completed')
        return
      }

      if (!questionResponse.success || !questionResponse.data?.question) {
        throw new Error(questionResponse.message || '获取题目失败')
      }
      
      processQuestionDataAndUpdateState(questionResponse.data, true)
      // 新会话不需要同步状态，因为状态数组已经在processQuestionDataAndUpdateState中初始化
    }
    
    // 确保题型有默认值（最后的后备方案）
    if (selectedQuestionTypes.value.length === 0) {
      selectedQuestionTypes.value = Object.keys(questionTypeNames)
    }

    toast.success(`练习${isNewSession ? '启动' : '加载'}成功`, { timeout: 2000 })

  } catch (error) {
    console.error('Error initializing practice:', error)
    toast.error(error instanceof Error ? error.message : '练习会话初始化失败', {
      timeout: 5000,
    })
    setTimeout(() => router.push('/'), 3000)
  } finally {
    initializing.value = false
  }
})

// 简化的显示信息初始化函数，避免不必要的API请求
const initializeDisplayInfo = () => {
  // 直接使用props设置显示信息，避免额外的API请求
  fileDisplayName.value = props.tiku_displayname || `题库ID: ${props.tikuid}`
  orderMode.value = props.order === 'random' ? '乱序练习' : '顺序练习'

  // 从props解析题型
  if (props.types) {
    try {
      selectedQuestionTypes.value = [
        ...new Set(props.types.split(',').map((t) => t.trim()).filter(Boolean)),
      ]
    } catch (error) {
      console.warn('解析题型参数失败:', error)
      selectedQuestionTypes.value = []
    }
  } else {
    selectedQuestionTypes.value = []
  }
}

const loadQuestion = async () => {
  try {
    const response = await apiService.getCurrentQuestion()

    if (response.success && response.data?.redirect_to_completed) {
      router.push('/completed')
      return
    }

    if (response.success && response.data) { // Check for success flag and data
      processQuestionDataAndUpdateState(response.data, false) // Not a new session context
      resetState() // Reset answers, mode to question
      isViewingHistory.value = false
      // No need to call syncQuestionStatuses here usually, as jumpToQuestion handles history
      // and regular navigation implies statuses are managed.
      // However, if progress.total could change, statuses array length is handled by processQuestionDataAndUpdateState.
    } else {
      // Throw error if not successful or no question, to be caught by catch block
      throw new Error(response.message || 'Failed to load question data')
    }
  } catch (error) {
    console.error('Error loading question:', error)
    toast.error(error instanceof Error ? error.message : '题目加载失败', {
      timeout: 4000,
    })
  }
}

const submitAnswer = async () => {
  if (!question.value || loadingSubmit.value) return

  clearAutoNextTimer()
  loadingSubmit.value = true

  try {
    const answer = question.value.is_multiple_choice
      ? Array.from(selectedAnswers.value).sort().join('')
      : selectedAnswer.value

    const feedbackResponse = await apiService.submitAnswer(answer, question.value.id, false, false)

    if (feedbackResponse.success && feedbackResponse.data) {
      currentFeedback.value = feedbackResponse.data
      displayMode.value = 'feedback'
      isViewingHistory.value = false

      if (feedbackResponse.data.is_correct) {
        toast.success('回答正确！🎉', { timeout: 2000 })

        // 启动自动跳转（如果不是最后一题）
        if (progress.value && currentQuestionIndex.value < progress.value.total - 1) {
          startAutoNextTimer()
        }
      } else {
        toast.warning('回答错误，查看解析学习一下吧 📚', { timeout: 3000 })
      }

      // 更新答题卡状态
      updateQuestionStatus(currentQuestionIndex.value, feedbackResponse.data.is_correct)
    } else {
      throw new Error(feedbackResponse.message || '答案提交处理失败')
    }
  } catch (error) {
    console.error('Error submitting answer:', error)
    toast.error(error instanceof Error ? error.message : '答案提交失败', {
      timeout: 4000,
    })
  } finally {
    loadingSubmit.value = false
  }
}

const revealAnswer = async () => {
  if (!question.value || loadingReveal.value) return

  loadingReveal.value = true

  try {
    const questionId = question.value.id
    const currentIndex = currentQuestionIndex.value

    // 提交查看答案的请求
    const feedback = await apiService.submitAnswer('', questionId, true, false)

    // 获取题目解析
    const analysisResponse = await apiService.getQuestionAnalysis(questionId)

    // 准备反馈数据
    const feedbackData: Feedback = {
      is_correct: false,
      user_answer_display: '未作答（直接查看答案）',
      correct_answer_display: formatAnswerWithOptions(
        question.value.answer,
        question.value.options_for_practice,
        question.value.is_multiple_choice,
      ),
      question_id: questionId,
      current_index: currentIndex,
    }

    if (analysisResponse.success && analysisResponse.data) {
      question.value = {
        ...question.value,
        analysis: analysisResponse.data.analysis,
        knowledge_points: analysisResponse.data.knowledge_points,
      }
    }

    currentFeedback.value = feedbackData
    updateQuestionStatus(currentIndex, false)
    displayMode.value = 'feedback'
    isViewingHistory.value = true
  } catch (error) {
    console.error('Error revealing answer:', error)
    toast.error(error instanceof Error ? error.message : '查看答案失败', {
      timeout: 4000,
    })
  } finally {
    loadingReveal.value = false
  }
}

const handleContinueAfterReveal = async () => {
  try {
    clearAutoNextTimer()
    resetState()
    await loadQuestion()
  } catch (error) {
    console.error('Error continuing to next question:', error)
    toast.error(error instanceof Error ? error.message : '加载下一题失败', {
      timeout: 4000,
    })
  }
}

const backToCurrentQuestion = async () => {
  try {
    clearAutoNextTimer()
    resetState()
    await loadQuestion()
  } catch (error) {
    console.error('Error returning to current question:', error)
    toast.error(error instanceof Error ? error.message : '返回当前题目失败', {
      timeout: 4000,
    })
  }
}

const goBackToIndexPage = async () => {
  try {
    // 恢复导航栏显示
    showNavigationBar.value = true
    
    router.push('/')
  } catch (error) {
    console.error('Failed to navigate back to index page:', error)
    
    // 即使出现错误也恢复导航栏显示
    showNavigationBar.value = true
    
    router.push('/')
  }
}

const formatAnswerWithOptions = (
  answer: string,
  options?: Record<string, string>,
  isMultipleChoice = false,
) => {
  if (!options) return answer

  if (isMultipleChoice) {
    return answer
      .split('')
      .map((key) => `${key}. ${options[key] || ''}`)
      .join(' + ')
  }
  return `${answer}. ${options[answer] || ''}`
}

// 生命周期
onBeforeUnmount(() => {
  clearAutoNextTimer()
  
  // 清理屏幕尺寸监听器
  if (typeof window !== 'undefined') {
    window.removeEventListener('resize', handleResize)
  }
  
  // 恢复导航栏显示
  showNavigationBar.value = true
})
</script>

<style scoped>
/* 全屏布局 */
.practice-page-wrapper {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  width: 100vw;
  height: 100vh;
  background: linear-gradient(to bottom right, #ffffff, #f8f9fa);
  overflow-y: auto;
  overflow-x: hidden;
  z-index: 1000; /* 确保在最上层显示 */
}

.container {
  position: relative;
  width: 100%;
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem;
  min-height: 100vh;
  box-sizing: border-box;
}

/* 练习容器 */
.practice-container {
  background: white;
  border-radius: 16px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
  width: 100%;
  margin: 0 auto;
  padding: 1.5rem;
}

.practice-title {
  margin-bottom: 2rem;
  text-align: center;
}

.practice-title h1 {
  font-size: 1.75rem;
  font-weight: 600;
  color: #1f2937;
  line-height: 1.4;
  padding-bottom: 1rem;
  border-bottom: 2px solid #e5e7eb;
}

/* 布局 */
.practice-layout {
  display: flex;
  gap: 2rem;
  align-items: flex-start;
}

.practice-main {
  flex: 1;
  min-width: 0;
  min-height: 600px; /* 确保主内容区域有稳定的最小高度 */
}

/* 内容容器 */
.content-container {
  position: relative;
  min-height: 600px; /* 增加最小高度，提供更稳定的布局 */
  display: flex;
  flex-direction: column;
}

/* 页面头部 */
.page-header {
  display: flex;
  align-items: center;
  gap: 2rem;
  margin-bottom: 2rem;
  flex-wrap: wrap;
}

.btn-navigate-back {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.25rem;
  background-color: transparent;
  color: #3b82f6;
  border: 2px solid #3b82f6;
  border-radius: 8px;
  font-weight: 600;
  transition: all 0.3s ease;
  white-space: nowrap;
  flex-shrink: 0;
}

.btn-navigate-back:hover {
  background-color: #3b82f6;
  color: white;
  transform: translateY(-2px);
}

.progress-bar-wrapper {
  flex: 1;
  min-width: 300px;
  background: white;
  padding: 1rem 1.5rem;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.05);
}

.progress-bar-text {
  text-align: center;
  font-size: 1.1rem;
  color: #4b5563;
  margin-bottom: 0.75rem;
  font-weight: 500;
}

.progress-bar-visual {
  height: 8px;
  background-color: #e5e7eb;
  border-radius: 999px;
  overflow: hidden;
}

.progress-bar-inner {
  height: 100%;
  background: linear-gradient(to right, #3b82f6, #60a5fa);
  transition: width 0.3s ease;
}

/* 提示信息 */
.flash-messages {
  list-style: none;
  padding: 0;
  margin-bottom: 1rem;
}

.flash-messages li {
  padding: 1rem;
  margin-bottom: 0.5rem;
  border-radius: 8px;
  font-weight: 500;
}

.flash-messages .info {
  background: #eff6ff;
  color: #1e40af;
  border-left: 4px solid #3b82f6;
}

.session-info {
  background-color: #f8fafc;
  border-radius: 8px;
  padding: 1rem;
  margin-bottom: 1rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.info-icon {
  font-size: 1.25rem;
}

.info-text {
  font-size: 0.9rem;
  color: #6b7280;
}

/* 题目和反馈区域 */
.question-section,
.feedback-section {
  background: white;
  border-radius: 16px;
  padding: 2rem;
  margin-bottom: 2rem;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.06);
  min-height: 550px; /* 增加最小高度防止布局跳跃 */
  transition: opacity 0.3s ease;
  flex: 1; /* 填充可用空间 */
  display: flex;
  flex-direction: column;
}

.question-section.content-loading {
  opacity: 0.7;
  pointer-events: none;
}

.question-text {
  font-size: 1.25rem;
  line-height: 1.75;
  color: #1f2937;
  background-color: #f9fafb;
  padding: 1.5rem;
  border-radius: 12px;
  border-left: 4px solid #3b82f6;
  margin: 0 0 2rem 0;
  display: flex;
  align-items: flex-start;
  gap: 1rem;
}

.question-type-badge {
  display: inline-flex;
  padding: 0.4rem 0.8rem;
  font-size: 0.9rem;
  font-weight: 600;
  color: white;
  border-radius: 999px;
  flex-shrink: 0;
  margin-top: 0.2rem;
}

.question-type-badge.multiple-choice-badge {
  background: linear-gradient(135deg, #8b5cf6, #c084fc);
}

.question-type-badge.single-choice-badge {
  background: linear-gradient(135deg, #3b82f6, #60a5fa);
}

.question-type-badge.true-false-badge {
  background: linear-gradient(135deg, #10b981, #34d399);
}

.question-text-content {
  flex: 1;
  white-space: pre-wrap; /* 完整保留所有空白字符：换行符、制表符、空格 */
}

/* 纯文本题目 - 居中对齐 */
.question-text-content.plain-text {
  text-align: center;
}

/* 格式化文本题目（包含换行符、制表符等）- 左对齐 */
.question-text-content.formatted-text {
  text-align: left;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace; /* 使用等宽字体更好地显示格式化内容 */
  background-color: #f8f9fa; /* 轻微背景色区分格式化文本 */
  padding: 1rem;
  border-radius: 8px;
  border: 1px solid #e9ecef;
}

/* 选项样式 */
.options-grid {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  margin: 1.5rem 0 2rem 0;
}

.option-label {
  display: flex;
  align-items: center;
  padding: 1rem;
  background: white;
  border: 2px solid #e5e7eb;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
  position: relative;
  padding-left: 3rem;
}

.option-label:hover {
  border-color: #3b82f6;
  transform: translateX(4px);
  box-shadow: 0 2px 12px rgba(59, 130, 246, 0.1);
}

.option-label.selected {
  background-color: #eff6ff;
  border-color: #3b82f6;
}

.option-input {
  opacity: 0;
  position: absolute;
  width: 1px;
  height: 1px;
}

.checkbox-custom-display,
.radio-custom-display {
  position: absolute;
  left: 1rem;
  top: 50%;
  transform: translateY(-50%);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
  background-color: white;
}

.checkbox-custom-display {
  width: 1.5rem;
  height: 1.5rem;
  border: 2px solid #60a5fa;
  border-radius: 4px;
}

.radio-custom-display {
  width: 1.25rem;
  height: 1.25rem;
  border: 2px solid #60a5fa;
  border-radius: 50%;
}

.checkbox-custom-display.checked {
  background-color: #3b82f6;
  border-color: #3b82f6;
}

.checkbox-custom-display.checked::after {
  content: '\2713';
  color: white;
  font-size: 1rem;
  font-weight: bold;
}

.radio-custom-display.checked {
  background-color: #3b82f6;
  border-color: #3b82f6;
}

.radio-custom-display.checked::after {
  content: '';
  width: 0.625rem;
  height: 0.625rem;
  background-color: white;
  border-radius: 50%;
  display: block;
}

.option-key {
  font-weight: 600;
  color: #3b82f6;
  margin-right: 1rem;
  min-width: 24px;
}

.option-text {
  flex: 1;
  color: #4b5563;
  white-space: pre-wrap;
}

/* 按钮样式 */
.action-buttons {
  display: flex;
  gap: 1rem;
  justify-content: flex-end;
  margin-top: 2rem;
}

.btn {
  padding: 0.75rem 1.5rem;
  font-weight: 600;
  border-radius: 8px;
  transition: all 0.3s ease;
  min-width: 120px;
  text-align: center;
  cursor: pointer;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
}

.loading-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid transparent;
  border-top: 2px solid currentColor;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.btn-submit {
  background: linear-gradient(135deg, #3b82f6, #60a5fa);
  color: white;
  border: none;
}

.btn-submit:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.25);
}

.btn-reveal {
  background-color: transparent;
  color: #4b5563;
  border: 2px solid #e5e7eb;
}

.btn-reveal:hover:not(:disabled) {
  border-color: #3b82f6;
  color: #3b82f6;
}

.btn-reveal:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* 反馈区域 */
.history-notice {
  background: linear-gradient(135deg, #fef3c7, #fbbf24);
  color: #92400e;
  padding: 1rem 1.5rem;
  border-radius: 8px;
  margin-bottom: 1.5rem;
  display: flex;
  align-items: center;
  gap: 0.75rem;
  font-weight: 500;
}

.auto-next-hint {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
  padding: 1rem 1.5rem;
  background: linear-gradient(135deg, #f0f9ff, #e0f2fe);
  border: 1px solid #0ea5e9;
  border-radius: 8px;
  margin: 1rem 0;
  animation: slideInFromTop 0.3s ease-out;
  position: relative;
  overflow: hidden;
}

@keyframes slideInFromTop {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.countdown-icon {
  font-size: 1.25rem;
  animation: bounce 1s infinite;
}

@keyframes bounce {
  0%, 20%, 50%, 80%, 100% {
    transform: translateY(0);
  }
  40% {
    transform: translateY(-3px);
  }
  60% {
    transform: translateY(-2px);
  }
}

.countdown-text {
  font-weight: 500;
  color: #0369a1;
  font-size: 0.95rem;
}

.btn-cancel-auto {
  background: linear-gradient(135deg, #3b82f6, #60a5fa);
  color: white;
  border: none;
  padding: 0.5rem 1rem;
  border-radius: 6px;
  font-size: 0.85rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  flex-shrink: 0;
}

.btn-cancel-auto:hover {
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(59, 130, 246, 0.25);
}

.question-review-content {
  background: #f8fafc;
  padding: 2rem;
  border-radius: 12px;
  margin-bottom: 2rem;
  flex: 1; /* 填充可用空间 */
  min-height: 300px; /* 确保有最小高度 */
}

.question-text-review {
  font-size: 1.1rem;
  line-height: 1.75;
  color: #1f2937;
  margin-bottom: 2rem;
  padding-bottom: 1rem;
  border-bottom: 2px dashed #e5e7eb;
  white-space: pre-wrap; /* 完整保留所有空白字符：换行符、制表符、空格 */
}

/* 纯文本题目回顾 - 居中对齐 */
.question-text-review.plain-text {
  text-align: center;
}

/* 格式化文本题目回顾（包含换行符、制表符等）- 左对齐 */
.question-text-review.formatted-text {
  text-align: left;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace; /* 使用等宽字体更好地显示格式化内容 */
  background-color: #f8f9fa; /* 轻微背景色区分格式化文本 */
  padding: 1rem;
  border-radius: 8px;
  border: 1px solid #e9ecef;
}

.answer-comparison {
  display: grid;
  gap: 1.5rem;
  margin-top: 1.5rem;
}

.answer-item {
  background: white;
  padding: 1.5rem;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.answer-item strong {
  display: block;
  margin-bottom: 0.75rem;
  color: #374151;
}

.user-answer-text-incorrect {
  color: #dc2626;
  font-weight: 600;
  padding: 0.5rem 1rem;
  background: #fef2f2;
  border-radius: 6px;
  display: inline-block;
  text-decoration: line-through;
}

.correct-answer-text {
  color: #059669;
  font-weight: 600;
  padding: 0.5rem 1rem;
  background: #ecfdf5;
  border-radius: 6px;
  display: inline-block;
}

.knowledge-points {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-top: 0.5rem;
}

.knowledge-point-tag {
  background: #e0f2fe;
  color: #0369a1;
  padding: 0.25rem 0.75rem;
  border-radius: 999px;
  font-size: 0.9rem;
  font-weight: 500;
}

.options-review {
  margin: 1rem 0;
  padding: 1rem;
  background: #f8fafc;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
}

.review-mode {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  margin-top: 0.75rem;
}

.option-review {
  display: flex;
  align-items: center;
  padding: 0.75rem 1rem;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
  background: white;
}

.option-review.option-correct {
  background-color: #ecfdf5;
  border-color: #059669;
  color: #065f46;
}

.option-review.option-incorrect {
  background-color: #fef2f2;
  border-color: #dc2626;
  color: #991b1b;
}

.btn-continue {
  background: linear-gradient(135deg, #3b82f6, #60a5fa);
  color: white;
  padding: 0.75rem 2rem;
  border-radius: 8px;
  font-weight: 600;
  transition: all 0.3s ease;
  min-width: 160px;
  border: none;
  cursor: pointer;
}

.btn-continue:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.25);
}

/* 加载和空状态 */
.empty-state-message {
  padding: 2rem;
  text-align: center;
  color: #6b7280;
  background-color: #f9fafb;
  border-radius: 12px;
  border: 2px dashed #e5e7eb;
}

/* 页脚 */
.footer-credit {
  text-align: center;
  margin-top: 3rem;
  padding-top: 1.5rem;
  border-top: 2px solid #e5e7eb;
  color: #6b7280;
  font-size: 0.9rem;
}

/* 过渡动画优化 */
.content-fade-enter-active {
  transition: opacity 0.15s ease-in;
  transition-delay: 0.1s; /* 增加延迟，确保前一个元素完全消失 */
}

.content-fade-leave-active {
  transition: opacity 0.1s ease-out;
}

.content-fade-enter-from {
  opacity: 0;
}

.content-fade-leave-to {
  opacity: 0;
}

/* 响应式设计 */
@media (max-width: 1024px) {
  .practice-layout {
    flex-direction: column;
    gap: 1rem;
  }
}

/* 小屏幕专注模式优化 */
@media (max-width: 768px) {
  /* 基础布局 */
  .container {
    padding: 0.5rem;
  }

  .practice-container {
    padding: 0.75rem;
    border-radius: 12px;
  }

  /* 隐藏标题区域 */
  .practice-title.mobile-hidden {
    display: none;
  }

  /* 紧凑页面头部 */
  .page-header.mobile-compact {
    flex-direction: row;
    gap: 0.75rem;
    margin-bottom: 1rem;
    padding: 0.5rem;
    background: #f8fafc;
    border-radius: 8px;
    align-items: center;
  }

  /* 紧凑返回按钮 */
  .btn-navigate-back.mobile-compact-btn {
    padding: 0.5rem;
    min-width: auto;
    border-radius: 6px;
  }

  /* 紧凑进度条 */
  .progress-bar-wrapper.mobile-compact-progress {
    min-width: auto;
    flex: 1;
    padding: 0.5rem 0.75rem;
    margin: 0;
    background: transparent;
    box-shadow: none;
  }

  .progress-bar-text.mobile-compact-text {
    font-size: 0.9rem;
    margin-bottom: 0.5rem;
    font-weight: 600;
    color: #374151;
  }

  .progress-bar-visual {
    height: 6px;
  }

  /* 题目区域优化 */
  .question-section,
  .feedback-section {
    padding: 1.25rem;
    margin-bottom: 1rem;
    border-radius: 12px;
    min-height: auto;
  }

  .question-text {
    font-size: 1.1rem;
    padding: 1.25rem;
    margin-bottom: 1.5rem;
  }

  .question-type-badge {
    font-size: 0.8rem;
    padding: 0.3rem 0.6rem;
  }

  /* 选项优化 */
  .option-label {
    padding: 1rem;
    padding-left: 2.75rem;
    margin-bottom: 0.75rem;
  }

  .option-text {
    font-size: 0.95rem;
  }

  /* 按钮优化 */
  .action-buttons {
    flex-direction: column;
    gap: 0.75rem;
    margin-top: 1.5rem;
  }

  .btn {
    padding: 0.875rem 1.25rem;
    font-size: 0.95rem;
  }

  /* 页脚简化 */
  .footer-credit {
    font-size: 0.8rem;
    margin-top: 1.5rem;
    padding-top: 1rem;
  }
}

@media (max-width: 576px) {
  .practice-title h1 {
    font-size: 1.25rem;
  }

  .question-text {
    font-size: 1rem;
    padding: 1rem;
  }
}

/* 练习模式标识 */
.order-mode-badge {
  display: inline-block;
  margin-left: 1rem;
  padding: 0.5rem 1rem;
  background: linear-gradient(135deg, #10b981, #34d399);
  color: white;
  font-size: 0.9rem;
  font-weight: 600;
  border-radius: 999px;
  vertical-align: middle;
}

/* 题型标识 */
.question-types-badge {
  display: inline-block;
  margin-left: 1rem;
  padding: 0.5rem 1rem;
  background: linear-gradient(135deg, #8b5cf6, #c084fc);
  color: white;
  font-size: 0.9rem;
  font-weight: 600;
  border-radius: 999px;
  vertical-align: middle;
}

.feedback-actions {
  margin-top: auto; /* 将按钮推到底部 */
  padding-top: 1rem;
  display: flex;
  justify-content: center;
}
</style>
