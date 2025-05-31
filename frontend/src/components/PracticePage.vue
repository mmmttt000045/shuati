<template>
  <div class="practice-page-wrapper">
    <div class="container">
      <div class="practice-container">
        <!-- 标题区域 -->
        <header class="practice-title">
          <h1>{{ fileDisplayName }}</h1>
        </header>

        <div class="practice-layout">
          <!-- 左侧主要内容区域 -->
          <main class="practice-main">
            <!-- 页面头部 -->
            <div class="page-header">
              <button class="btn btn-navigate-back" @click="goBackToIndexPage">
                <span class="arrow">←</span> 返回首页
              </button>
              <div v-if="progress" class="progress-bar-wrapper">
                <div class="progress-bar-text">
                  第 {{ progress.round }} 轮 - 题目 {{ progress.current }} / {{ progress.total }}
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

            <!-- 友好提示 -->
            <div v-if="showSessionInfo" class="session-info">
              <span class="info-icon">💡</span>
              <span class="info-text">提示：刷新页面后练习进度会自动保存和恢复</span>
            </div>

            <!-- 主要内容区域 -->
            <transition name="content-fade" mode="out-in">
              <!-- 题目显示模式 -->
              <div v-if="isQuestionMode" key="question" class="question-section card">
                <div class="question-content">
                  <div class="question-text">
                    <span class="question-type-badge" :class="questionTypeBadgeClass">
                      {{ question?.type }}
                    </span>
                    <span class="question-text-content">{{ question?.question }}</span>
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
                      提交答案
                    </button>
                    <button
                      :disabled="!canRevealAnswer"
                      :class="['btn', 'btn-reveal', { loading: loadingReveal }]"
                      type="button"
                      @click="revealAnswer"
                    >
                      {{ loadingReveal ? '正在加载' : '查看答案' }}
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

                <!-- 自动跳转提示 -->
                <div v-if="showAutoNextHint && !isViewingHistory" class="auto-next-hint">
                  <span class="hint-icon">⏱️</span>
                  <span class="hint-text">{{ autoNextCountdownText }}</span>
                  <button class="btn-cancel-auto" @click="clearAutoNextTimer">取消</button>
                </div>

                <div class="question-review-content">
                  <h4>题目回顾：</h4>
                  <p class="question-text-review">{{ question?.question }}</p>

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
                        <strong>你的答案：</strong>
                        <span class="user-answer-text-incorrect">{{
                          currentFeedback.user_answer_display
                        }}</span>
                      </div>
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

            <!-- 加载状态 -->
            <div v-if="showLoadingIndicator" class="loading-indicator-fullscreen">
              <p>{{ loadingText }}</p>
            </div>

            <!-- 空状态 -->
            <div v-if="showEmptyState" class="empty-state-message card">
              <p>当前没有题目可以练习，或题目加载失败。</p>
            </div>
          </main>

          <!-- 右侧答题卡 -->
          <aside class="answer-card-panel" :class="{ 'history-mode': isViewingHistory }">
            <div class="answer-card-header">
              <div class="answer-card-title">
                <h3>答题卡</h3>
                <button
                  class="btn-toggle"
                  @click="toggleAnswerCard"
                  :title="isAnswerCardExpanded ? '收起答题卡' : '展开答题卡'"
                >
                  {{ isAnswerCardExpanded ? '↑' : '↓' }}
                </button>
              </div>

              <div v-if="isViewingHistory" class="history-navigation-tip">
                <span class="tip-icon">💡</span>
                <span class="tip-text">点击答题卡可查看其他题目</span>
              </div>

              <div v-if="isAnswerCardExpanded" class="answer-card-legend">
                <span class="legend-item"> <span class="status-dot current"></span> 当前题目 </span>
                <span class="legend-item"> <span class="status-dot correct"></span> 已答对 </span>
                <span class="legend-item"> <span class="status-dot wrong"></span> 已答错 </span>
                <span class="legend-item"> <span class="status-dot"></span> 未作答 </span>
              </div>
            </div>

            <div class="answer-card-grid-container" :class="answerCardGridClass">
              <div class="answer-card-grid">
                <template v-if="isAnswerCardExpanded">
                  <button
                    v-for="(status, index) in questionStatuses"
                    :key="index"
                    :class="getQuestionNumberBtnClass(status, index)"
                    @click="jumpToQuestion(index)"
                    :disabled="!canJumpToQuestion || loadingSubmit"
                  >
                    {{ index + 1 }}
                  </button>
                </template>
                <template v-else>
                  <button
                    v-for="item in visibleQuestions"
                    :key="item.number"
                    :class="getQuestionNumberBtnClass(item.status, item.number - 1, item.isCurrent)"
                    @click="jumpToQuestion(item.number - 1)"
                    :disabled="!canJumpToQuestion || loadingSubmit"
                  >
                    {{ item.number }}
                  </button>
                </template>
              </div>
            </div>

            <!-- 答题卡操作按钮 -->
            <div class="answer-card-actions">
              <div v-if="!isViewingHistory && progress" class="navigation-buttons">
                <button
                  class="btn-answer-card-action btn-navigation"
                  @click="goToPreviousQuestion"
                  :disabled="!canGoPrevious"
                  title="跳转到上一题"
                >
                  <span class="action-icon">←</span>
                  上一题
                </button>
                <button
                  class="btn-answer-card-action btn-navigation"
                  @click="goToNextQuestion"
                  :disabled="!canGoNext"
                  title="跳转到下一题"
                >
                  <span class="action-icon">→</span>
                  下一题
                </button>
              </div>
              <button
                v-else-if="isViewingHistory"
                class="btn-answer-card-action btn-return"
                @click="backToCurrentQuestion"
                :disabled="loadingSubmit"
                title="返回到当前正在练习的题目"
              >
                <span class="action-icon">↩</span>
                返回当前题
              </button>
            </div>
          </aside>
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

interface QuestionStatus {
  status: QuestionStatusType
  number: number
  isCurrent: boolean
}

const props = defineProps<{
  subject: string
  fileName: string
  order?: string
}>()

const router = useRouter()
const toast = useToast()
const authStore = useAuthStore()

// 响应式状态
const fileDisplayName = ref<string>('')
const question = ref<Question | null>(null)
const progress = ref<Progress | null>(null)
const messages = ref<FlashMessage[]>([])
const displayMode = ref<'question' | 'feedback'>('question')
const currentFeedback = ref<Feedback | null>(null)
const loading = ref(false)
const initializing = ref(true)
const selectedAnswer = ref<string>('')
const selectedAnswers = ref<Set<string>>(new Set())
const shuffledMcqOptions = ref<Record<string, string>>({})
const isViewingHistory = ref(false)
const questionStatuses = ref<Array<QuestionStatusType>>([])
const isAnswerCardExpanded = ref(false)

// 加载状态
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

// 计算属性
const progressPercentage = computed(() => {
  if (!progress.value) return 0
  return (progress.value.current / progress.value.total) * 100
})

const currentQuestionIndex = computed(() => (progress.value ? progress.value.current - 1 : 0))

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

const showLoadingIndicator = computed(
  () => (loading.value && displayMode.value === 'question') || initializing.value,
)

const loadingText = computed(() =>
  initializing.value ? '正在初始化练习会话，请稍候...' : '题目正在加载中，请稍候...',
)

const showEmptyState = computed(
  () =>
    !loading.value && !initializing.value && !question.value && displayMode.value === 'question',
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

const answerCardGridClass = computed(() => ({
  expanded: isAnswerCardExpanded.value,
  'has-left-overflow': hasLeftOverflow.value,
  'has-right-overflow': hasRightOverflow.value,
}))

// 可见题目列表
const visibleQuestions = computed<QuestionStatus[]>(() => {
  if (!progress.value) return []
  const totalQuestions = progress.value.total

  if (questionStatuses.value.length !== totalQuestions && totalQuestions > 0) {
    const newStatuses = new Array(totalQuestions).fill(QUESTION_STATUS.UNANSWERED)
    for (let i = 0; i < Math.min(questionStatuses.value.length, totalQuestions); i++) {
      newStatuses[i] = questionStatuses.value[i]
    }
    questionStatuses.value = newStatuses
  }

  const statusesToDisplay = questionStatuses.value.slice(0, totalQuestions)

  if (isAnswerCardExpanded.value) {
    return statusesToDisplay.map((status, index) => ({
      status,
      number: index + 1,
      isCurrent: index === currentQuestionIndex.value,
    }))
  }

  const currentIndex = currentQuestionIndex.value
  const displayCount = 15
  const halfDisplay = Math.floor(displayCount / 2)

  let startIndex = Math.max(0, currentIndex - halfDisplay)
  const endIndex = Math.min(totalQuestions, startIndex + displayCount)

  if (endIndex - startIndex < displayCount && totalQuestions >= displayCount) {
    startIndex = Math.max(0, endIndex - displayCount)
  }

  return statusesToDisplay.slice(startIndex, endIndex).map((status, index) => ({
    status,
    number: startIndex + index + 1,
    isCurrent: startIndex + index === currentIndex,
  }))
})

const hasLeftOverflow = computed(() => {
  if (isAnswerCardExpanded.value || !progress.value) return false
  const currentIndex = currentQuestionIndex.value
  const displayCount = 15
  const halfDisplay = Math.floor(displayCount / 2)
  return Math.max(0, currentIndex - halfDisplay) > 0
})

const hasRightOverflow = computed(() => {
  if (isAnswerCardExpanded.value || !progress.value) return false
  const currentIndex = currentQuestionIndex.value
  const totalQuestions = progress.value.total
  const displayCount = 15
  const halfDisplay = Math.floor(displayCount / 2)
  let startIndex = Math.max(0, currentIndex - halfDisplay)
  const endIndex = Math.min(totalQuestions, startIndex + displayCount)

  if (endIndex - startIndex < displayCount && totalQuestions >= displayCount) {
    startIndex = Math.max(0, endIndex - displayCount)
  }

  return endIndex < totalQuestions
})

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

const getQuestionNumberBtnClass = (
  status: QuestionStatusType,
  index: number,
  isCurrent?: boolean,
) => ({
  'question-number-btn': true,
  current: isCurrent !== undefined ? isCurrent : index === currentQuestionIndex.value,
  correct: isCorrectStatus(status),
  wrong: isWrongStatus(status),
  unanswered: isUnansweredStatus(status),
})

const toggleAnswerCard = () => {
  isAnswerCardExpanded.value = !isAnswerCardExpanded.value
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
  if (progress.value && currentQuestionIndex.value < progress.value.total - 1) {
    goToNextQuestion()
  }
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
  loading.value = true

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

        if (historyResponse.success && historyResponse.question && historyResponse.feedback) {
          question.value = historyResponse.question
          currentFeedback.value = historyResponse.feedback

          if (progress.value) {
            progress.value.current = index + 1
          }

          displayMode.value = 'feedback'
          isViewingHistory.value = true
          resetState()
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
  } finally {
    loading.value = false
  }
}

const syncQuestionStatuses = async () => {
  try {
    const statusResponse = await apiService.getQuestionStatuses()
    if (statusResponse.success && statusResponse.statuses.length > 0) {
      const currentStatusStr = JSON.stringify(questionStatuses.value)
      const newStatusStr = JSON.stringify(statusResponse.statuses)

      if (currentStatusStr !== newStatusStr) {
        questionStatuses.value = [...statusResponse.statuses]
      }
    }
  } catch (error) {
    console.warn('同步答题卡状态失败:', error)
  }
}

onMounted(async () => {
  try {
    // 首先确保用户已认证
    if (!authStore.isAuthenticated) {
      await authStore.checkAuth()
      if (!authStore.isAuthenticated) {
        toast.error('用户认证已过期，请重新登录', {
          timeout: 3000,
        })
        router.push('/login')
        return
      }
    }

    // 首先检查是否已有活跃的练习会话
    const sessionStatus = await apiService.checkSessionStatus()

    if (sessionStatus.active) {
      // 检查会话是否已完成
      if (sessionStatus.completed) {
        router.push('/completed')
        return
      }

      // 检查会话文件是否与当前请求的文件匹配
      if (sessionStatus.file_info && sessionStatus.file_info.key === props.fileName) {
        // 设置文件显示名称
        fileDisplayName.value = sessionStatus.file_info.display || props.fileName

        // 显示恢复会话的提示信息
        if (sessionStatus.progress) {
          // 使用 toast 进行即时通知
          toast.info(
            `已恢复练习进度：第${sessionStatus.progress.round}轮，第${sessionStatus.progress.current}/${sessionStatus.progress.total}题`,
            {
              timeout: 4000,
            },
          )

          // 同时在页面上显示持久信息
          messages.value.push({
            category: 'info',
            text: `练习进度已恢复：第${sessionStatus.progress.round}轮`,
          })
        }

        // 恢复答题卡状态 - 修复：确保状态数组正确初始化
        if (sessionStatus.question_statuses && sessionStatus.question_statuses.length > 0) {
          questionStatuses.value = [...sessionStatus.question_statuses]
          console.log('从会话状态恢复答题卡状态：', questionStatuses.value)
        } else if (sessionStatus.progress) {
          // 如果没有状态数组，根据进度创建默认状态数组
          const defaultStatuses = new Array(sessionStatus.progress.total).fill(
            QUESTION_STATUS.UNANSWERED,
          )
          questionStatuses.value = defaultStatuses
          console.log('创建默认答题卡状态：', questionStatuses.value)
        }

        // 直接加载当前题目，无需重新开始练习
        await loadQuestion()

        // 加载完成后立即同步状态，确保一致性
        await syncQuestionStatuses()
        return
      } else if (sessionStatus.file_info) {
        // 显示切换题库的提示信息
        toast.info(`已从《${sessionStatus.file_info.display}》切换到当前题库`, {
          timeout: 3000,
        })

        // 当前有其他文件的会话，需要强制重新开始
        const shuffleQuestions = props.order !== 'sequential' // 默认为随机，除非明确指定为顺序
        const startResponse = await apiService.startPractice(
          props.subject,
          props.fileName,
          true,
          shuffleQuestions,
        )
        if (!startResponse.success) {
          throw new Error(startResponse.message)
        }
        // 设置文件显示名称
        fileDisplayName.value = getDisplayNameFromFilePath(props.fileName)
      }
    } else {
      // 没有活跃会话，开始新的练习
      const shuffleQuestions = props.order !== 'sequential' // 默认为随机，除非明确指定为顺序
      const startResponse = await apiService.startPractice(
        props.subject,
        props.fileName,
        false,
        shuffleQuestions,
      )
      if (!startResponse.success) {
        throw new Error(startResponse.message)
      }
      // 设置文件显示名称
      fileDisplayName.value = getDisplayNameFromFilePath(props.fileName)
    }

    // 加载第一题或当前题目
    await loadQuestion()

    // 确保答题卡状态正确同步
    await syncQuestionStatuses()
  } catch (error) {
    console.error('Error initializing practice:', error)
    toast.error(error instanceof Error ? error.message : '练习会话初始化失败', {
      timeout: 5000,
    })
    setTimeout(() => {
      router.push('/')
    }, 3000)
  } finally {
    initializing.value = false // 初始化完成
  }
})

const loadQuestion = async () => {
  loading.value = true
  try {
    const response = await apiService.getCurrentQuestion()

    if (response.redirect_to_completed) {
      router.push('/completed')
      return
    }

    if (response.question) {
      question.value = response.question
      progress.value = response.progress
      messages.value = response.flash_messages || []
      displayMode.value = 'question'
      isViewingHistory.value = false
      resetState()

      // 确保答题卡状态数组长度匹配
      if (progress.value && questionStatuses.value.length !== progress.value.total) {
        const newLength = progress.value.total
        if (questionStatuses.value.length < newLength) {
          const additionalStatuses = new Array(newLength - questionStatuses.value.length).fill(
            QUESTION_STATUS.UNANSWERED,
          )
          questionStatuses.value = [...questionStatuses.value, ...additionalStatuses]
        } else {
          questionStatuses.value = questionStatuses.value.slice(0, newLength)
        }
      }

      // 重置选项
      if (question.value.options_for_practice) {
        shuffledMcqOptions.value = { ...question.value.options_for_practice }
      } else {
        shuffledMcqOptions.value = {}
      }
    } else {
      throw new Error('Failed to load question data')
    }
  } catch (error) {
    console.error('Error loading question:', error)
    toast.error(error instanceof Error ? error.message : '题目加载失败', {
      timeout: 4000,
    })
  } finally {
    loading.value = false
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

    const feedback = await apiService.submitAnswer(answer, question.value.id, false, false)

    currentFeedback.value = feedback
    displayMode.value = 'feedback'
    isViewingHistory.value = false

    if (feedback.is_correct) {
      toast.success('回答正确！🎉', { timeout: 2000 })

      // 启动自动跳转（如果不是最后一题）
      if (progress.value && currentQuestionIndex.value < progress.value.total - 1) {
        startAutoNextTimer()
      }
    } else {
      toast.warning('回答错误，查看解析学习一下吧 📚', { timeout: 3000 })
    }

    // 更新答题卡状态
    updateQuestionStatus(currentQuestionIndex.value, feedback.is_correct)

    // 同步后端状态
    setTimeout(async () => {
      await syncQuestionStatuses()
    }, 100)
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

    if (analysisResponse.success) {
      question.value = {
        ...question.value,
        analysis: analysisResponse.analysis,
        knowledge_points: analysisResponse.knowledge_points,
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
    await syncQuestionStatuses()
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
    const savingToast = toast.info('正在保存练习进度...', {
      timeout: false,
      closeOnClick: false,
      pauseOnHover: false,
    })

    await apiService.saveSession()
    toast.dismiss(savingToast)
    toast.success('练习进度已保存 💾', { timeout: 2000 })
    router.push('/')
  } catch (error) {
    console.error('Failed to save session progress:', error)
    toast.warning('保存进度失败，但可以继续使用 ⚠️', { timeout: 3000 })
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

// 监听器
watch(
  () => progress.value?.total,
  (newTotal) => {
    if (newTotal && newTotal > 0 && questionStatuses.value.length !== newTotal) {
      const newStatuses = new Array(newTotal).fill(QUESTION_STATUS.UNANSWERED)
      for (let i = 0; i < Math.min(questionStatuses.value.length, newTotal); i++) {
        newStatuses[i] = questionStatuses.value[i]
      }
      questionStatuses.value = newStatuses
    }
  },
  { immediate: true },
)

// 生命周期
onBeforeUnmount(() => {
  clearAutoNextTimer()
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
}

.question-text {
  font-size: 1.25rem;
  line-height: 1.75;
  color: #1f2937;
  background-color: #f9fafb;
  padding: 1.5rem;
  border-radius: 12px;
  border-left: 4px solid #3b82f6;
  margin: 0;
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
}

/* 选项样式 */
.options-grid {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  margin-bottom: 2rem;
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
}

.question-review-content {
  background: #f8fafc;
  padding: 2rem;
  border-radius: 12px;
  margin-bottom: 2rem;
}

.question-text-review {
  font-size: 1.1rem;
  line-height: 1.75;
  color: #1f2937;
  margin-bottom: 2rem;
  padding-bottom: 1rem;
  border-bottom: 2px dashed #e5e7eb;
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

/* 答题卡 */
.answer-card-panel {
  width: 280px;
  background: white;
  border-radius: 16px;
  padding: 1.5rem;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.06);
  position: sticky;
  top: 2rem;
  flex-shrink: 0;
}

.answer-card-title {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.answer-card-title h3 {
  font-size: 1.25rem;
  font-weight: 600;
  color: #1f2937;
}

.btn-toggle {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f3f4f6;
  border: none;
  color: #6b7280;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-toggle:hover {
  background: #e5e7eb;
  color: #374151;
}

.answer-card-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  font-size: 0.875rem;
  color: #6b7280;
  margin-bottom: 1rem;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.status-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background-color: #e5e7eb;
}

.status-dot.current {
  background-color: #3b82f6;
}

.status-dot.correct {
  background-color: #10b981;
}

.status-dot.wrong {
  background-color: #ef4444;
}

.answer-card-grid-container {
  position: relative;
  overflow: hidden;
  height: 240px;
}

.answer-card-grid-container.expanded {
  height: auto;
  max-height: calc(100vh - 200px);
  overflow-y: auto;
}

.answer-card-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 0.5rem;
  padding: 0.5rem;
}

.question-number-btn {
  aspect-ratio: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.9rem;
  font-weight: 600;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
  background: white;
  color: #6b7280;
  transition: all 0.2s ease;
  cursor: pointer;
}

.question-number-btn:hover:not(.current):not(.correct):not(.wrong) {
  border-color: #3b82f6;
  color: #3b82f6;
}

.question-number-btn.current {
  background: #3b82f6;
  color: white;
  border: none;
  transform: scale(1.1);
}

.question-number-btn.correct {
  background: #10b981;
  color: white;
  border: none;
}

.question-number-btn.wrong {
  background: #ef4444;
  color: white;
  border: none;
}

.question-number-btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

/* 答题卡操作按钮 */
.answer-card-actions {
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid #e5e7eb;
}

.navigation-buttons {
  display: flex;
  gap: 0.5rem;
}

.btn-answer-card-action {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  background: linear-gradient(135deg, #3b82f6, #60a5fa);
  color: white;
  border: none;
  border-radius: 8px;
  font-weight: 600;
  font-size: 0.9rem;
  cursor: pointer;
  transition: all 0.3s ease;
  flex: 1;
}

.btn-answer-card-action:hover:not(:disabled) {
  background: linear-gradient(135deg, #2563eb, #3b82f6);
  transform: translateY(-2px);
}

.btn-answer-card-action:disabled {
  background: #9ca3af;
  cursor: not-allowed;
  transform: none;
}

.btn-return {
  width: 100%;
}

/* 加载和空状态 */
.loading-indicator-fullscreen {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 4rem 2rem;
  text-align: center;
  color: #6b7280;
  font-size: 1.1rem;
}

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

/* 过渡动画 */
.content-fade-enter-active,
.content-fade-leave-active {
  transition: all 0.3s ease-in-out;
}

.content-fade-enter-from {
  opacity: 0;
  transform: translateY(20px);
}

.content-fade-leave-to {
  opacity: 0;
  transform: translateY(-20px);
}

/* 响应式设计 */
@media (max-width: 1024px) {
  .practice-layout {
    flex-direction: column;
    gap: 1rem;
  }

  .answer-card-panel {
    order: -1;
    position: static;
    width: 100%;
  }
}

@media (max-width: 768px) {
  .container {
    padding: 1rem;
  }

  .practice-container {
    padding: 1rem;
  }

  .page-header {
    flex-direction: column;
    gap: 1rem;
  }

  .progress-bar-wrapper {
    min-width: unset;
  }

  .question-text {
    font-size: 1.1rem;
    flex-direction: column;
    gap: 0.75rem;
    align-items: flex-start;
  }

  .option-label {
    padding-left: 2.75rem;
  }

  .action-buttons {
    flex-direction: column;
  }

  .navigation-buttons {
    flex-direction: column;
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

  .answer-card-grid {
    grid-template-columns: repeat(auto-fill, minmax(38px, 1fr));
  }

  .question-number-btn {
    height: 38px;
    font-size: 0.8rem;
  }
}
</style>
