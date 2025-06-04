<template>
  <aside class="answer-card-panel" :class="{ 'history-mode': isViewingHistory }">
    <div class="answer-card-header">
      <div class="answer-card-title">
        <h3>答题卡</h3>
        <!-- 小屏幕收缩模式的进度指示器 -->
        <div v-if="!isExpanded && isSmallScreen && progress" class="compact-progress">
          {{ progress.current }}/{{ progress.total }}
        </div>
        <button
          class="btn-toggle"
          @click="toggleAnswerCard"
          :title="isExpanded ? '收起答题卡' : '展开答题卡'"
        >
          {{ isExpanded ? '↑' : '↓' }}
        </button>
      </div>

      <div v-if="isExpanded" class="answer-card-legend">
        <span class="legend-item"> <span class="status-dot current"></span> 当前题目 </span>
        <span class="legend-item"> <span class="status-dot correct"></span> 已答对 </span>
        <span class="legend-item"> <span class="status-dot wrong"></span> 已答错 </span>
        <span class="legend-item"> <span class="status-dot"></span> 未作答 </span>
      </div>
    </div>

    <div class="answer-card-grid-container" :class="answerCardGridClass" v-show="isExpanded || !isSmallScreen">
      <!-- 中心指示器 -->
      <div v-if="!isExpanded && progress && progress.total > 11" class="center-indicator">
        <div class="center-line"></div>
        <div class="center-dot"></div>
      </div>
      
      <div class="answer-card-grid">
        <template v-if="isExpanded">
          <button
            v-for="(status, index) in questionStatuses"
            :key="index"
            :class="getQuestionNumberBtnClass(status, index)"
            @click="handleJumpToQuestion(index)"
            :disabled="!canJumpToQuestion || loadingSubmit"
          >
            {{ index + 1 }}
          </button>
        </template>
        <template v-else>
          <template v-for="item in allQuestionsWithPreview" :key="item.number">
            <button
              v-if="item.number > 0"
              :class="getQuestionNumberBtnClass(item.status, item.number - 1, item.isCurrent, item.isPreview)"
              @click="handleJumpToQuestion(item.number - 1)"
              :disabled="!canJumpToQuestion || loadingSubmit"
            >
              {{ item.number }}
            </button>
          </template>
        </template>
      </div>
    </div>

    <!-- 答题卡操作按钮 -->
    <div class="answer-card-actions" v-show="isExpanded || !isSmallScreen">
      <div v-if="!isViewingHistory && progress" class="navigation-buttons">
        <button
          class="btn-answer-card-action btn-navigation"
          @click="handleGoToPrevious"
          :disabled="!canGoPrevious"
          title="跳转到上一题"
        >
          <span class="action-icon">←</span>
          上一题
        </button>
        <button
          class="btn-answer-card-action btn-navigation"
          @click="handleGoToNext"
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
        @click="handleBackToCurrent"
        :disabled="loadingSubmit"
        title="返回到当前正在练习的题目"
      >
        <span class="action-icon">↩</span>
        返回当前题
      </button>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import type { Progress, QuestionStatus as QuestionStatusType } from '@/types'
import { QUESTION_STATUS, isCorrectStatus, isWrongStatus, isUnansweredStatus } from '@/types'

interface QuestionStatus {
  status: QuestionStatusType
  number: number
  isCurrent: boolean
  isPreview?: boolean
}

interface Props {
  questionStatuses: Array<QuestionStatusType>
  progress: Progress | null
  currentQuestionIndex: number
  isViewingHistory: boolean
  canJumpToQuestion: boolean
  loadingSubmit: boolean
}

interface Emits {
  (e: 'jumpToQuestion', index: number): void
  (e: 'goToPrevious'): void
  (e: 'goToNext'): void
  (e: 'backToCurrent'): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

// 响应式状态
const isExpanded = ref(false)
const screenWidth = ref(typeof window !== 'undefined' ? window.innerWidth : 1024)

// 监听屏幕尺寸变化
const handleResize = () => {
  screenWidth.value = window.innerWidth
}

onMounted(() => {
  if (typeof window !== 'undefined') {
    window.addEventListener('resize', handleResize)
  }
})

onUnmounted(() => {
  if (typeof window !== 'undefined') {
    window.removeEventListener('resize', handleResize)
  }
})

// 计算属性
const answerCardGridClass = computed(() => ({
  expanded: isExpanded.value,
  'has-left-overflow': hasLeftOverflow.value,
  'has-right-overflow': hasRightOverflow.value,
}))

const canGoPrevious = computed(() => !props.loadingSubmit && props.currentQuestionIndex > 0)

const canGoNext = computed(
  () =>
    !props.loadingSubmit && 
    props.progress && 
    props.currentQuestionIndex < props.progress.total - 1,
)

// 小屏幕检测
const isSmallScreen = computed(() => screenWidth.value <= 768)

// 计算网格参数的辅助函数
const getGridParams = () => {
  if (!props.progress) return null
  
  const totalQuestions = props.progress.total
  const currentIndex = props.currentQuestionIndex
  const gridColumns = 5
  
  // 响应式调整网格行数
  const isSmallScreen = screenWidth.value <= 576
  const isMediumScreen = screenWidth.value <= 768
  
  let gridRows = 5
  if (isSmallScreen) {
    gridRows = 3
  } else if (isMediumScreen) {
    gridRows = 3
  }
  
  const totalSlots = gridColumns * gridRows
  const centerRow = Math.floor(gridRows / 2)
  const centerColumn = Math.floor(gridColumns / 2)
  
  // 计算理想的起始位置
  const idealCurrentSlotIndex = centerRow * gridColumns + centerColumn
  const idealStartQuestionIndex = currentIndex - idealCurrentSlotIndex
  
  // 边界处理：确保显示范围合理
  let startQuestionIndex: number
  
  if (idealStartQuestionIndex < 0) {
    startQuestionIndex = 0
  } else if (idealStartQuestionIndex + totalSlots > totalQuestions) {
    startQuestionIndex = Math.max(0, totalQuestions - totalSlots)
  } else {
    startQuestionIndex = idealStartQuestionIndex
  }
  
  return {
    totalQuestions,
    currentIndex,
    gridColumns,
    gridRows,
    totalSlots,
    centerRow,
    centerColumn,
    startQuestionIndex,
    idealStartQuestionIndex
  }
}

// 缩略模式下的所有题目（包括模糊预览）
const allQuestionsWithPreview = computed<Array<QuestionStatus>>(() => {
  if (isExpanded.value) return []
  
  const gridParams = getGridParams()
  if (!gridParams) return []
  
  const {
    totalQuestions,
    currentIndex,
    gridColumns,
    gridRows,
    totalSlots,
    startQuestionIndex
  } = gridParams
  
  const allItems: Array<QuestionStatus> = []
  
  // 填充网格
  for (let slotIndex = 0; slotIndex < totalSlots; slotIndex++) {
    const questionIndex = startQuestionIndex + slotIndex
    const row = Math.floor(slotIndex / gridColumns)
    
    if (questionIndex >= 0 && questionIndex < totalQuestions) {
      const isCurrent = questionIndex === currentIndex
      
      // 动态调整预览逻辑：只有在有足够题目时才使用预览
      let isPreview = false
      
      if (totalQuestions > totalSlots) {
        // 有超出显示范围的题目时，第一行和最后一行设为预览
        if (startQuestionIndex > 0 && row === 0) {
          isPreview = true // 前面还有题目，第一行预览
        }
        if (startQuestionIndex + totalSlots < totalQuestions && row === gridRows - 1) {
          isPreview = true // 后面还有题目，最后一行预览
        }
      }
      
      allItems.push({
        status: props.questionStatuses[questionIndex] || QUESTION_STATUS.UNANSWERED,
        number: questionIndex + 1,
        isCurrent,
        isPreview: isPreview && !isCurrent // 当前题目永远不模糊
      })
    }
  }
  
  return allItems
})

// 优化的溢出检测
const hasLeftOverflow = computed(() => {
  if (isExpanded.value) return false
  
  const gridParams = getGridParams()
  if (!gridParams) return false
  
  const { startQuestionIndex, idealStartQuestionIndex, totalQuestions, totalSlots } = gridParams
  
  // 判断是否有左侧溢出
  if (idealStartQuestionIndex < 0) {
    return false // 前几道题，没有左侧溢出
  } else if (idealStartQuestionIndex + totalSlots > totalQuestions) {
    // 最后几道题的情况
    return startQuestionIndex > 0
  } else {
    return startQuestionIndex > 0
  }
})

const hasRightOverflow = computed(() => {
  if (isExpanded.value) return false
  
  const gridParams = getGridParams()
  if (!gridParams) return false
  
  const { startQuestionIndex, idealStartQuestionIndex, totalQuestions, totalSlots } = gridParams
  
  // 判断是否有右侧溢出
  if (idealStartQuestionIndex < 0) {
    // 前几道题的情况
    return totalQuestions > totalSlots
  } else if (idealStartQuestionIndex + totalSlots > totalQuestions) {
    return false // 最后几道题，没有右侧溢出
  } else {
    return startQuestionIndex + totalSlots < totalQuestions
  }
})

// 方法
const toggleAnswerCard = () => {
  isExpanded.value = !isExpanded.value
}

const getQuestionNumberBtnClass = (
  status: QuestionStatusType,
  index: number,
  isCurrent?: boolean,
  isPreview?: boolean,
) => ({
  'question-number-btn': true,
  'preview-btn': isPreview, // 模糊预览样式
  current: isCurrent !== undefined ? isCurrent : index === props.currentQuestionIndex,
  correct: isCorrectStatus(status),
  wrong: isWrongStatus(status),
  unanswered: isUnansweredStatus(status),
})

const handleJumpToQuestion = (index: number) => {
  emit('jumpToQuestion', index)
}

const handleGoToPrevious = () => {
  emit('goToPrevious')
}

const handleGoToNext = () => {
  emit('goToNext')
}

const handleBackToCurrent = () => {
  emit('backToCurrent')
}
</script>

<style scoped>
/* 答题卡 */
.answer-card-panel {
  width: 320px;
  background: white;
  border-radius: 16px;
  padding: 1.5rem;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.06);
  position: sticky;
  top: 2rem;
  flex-shrink: 0;
  align-self: flex-start; /* 确保答题卡不会影响主内容区域的高度 */
}

.answer-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.answer-card-title {
  display: flex;
  align-items: center;
  gap: 0.75rem;
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
  height: 200px; /* 基础高度 - 适应3行 */
}

.answer-card-grid-container.expanded {
  height: auto;
  max-height: calc(100vh - 200px);
  overflow-y: auto;
}

/* 大屏幕 - 4行显示 */
@media (min-width: 769px) {
  .answer-card-grid-container {
    height: 240px;
  }
}

/* 添加渐变遮罩指示溢出 */
.answer-card-grid-container.has-left-overflow::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 30px;
  background: linear-gradient(to right, rgba(255, 255, 255, 0.9), transparent);
  z-index: 1;
  pointer-events: none;
}

.answer-card-grid-container.has-right-overflow::after {
  content: '';
  position: absolute;
  right: 0;
  top: 0;
  bottom: 0;
  width: 30px;
  background: linear-gradient(to left, rgba(255, 255, 255, 0.9), transparent);
  z-index: 1;
  pointer-events: none;
}

/* 中心指示器 */
.center-indicator {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  z-index: 0;
  pointer-events: none;
}

.center-line {
  width: 2px;
  height: 60px;
  background: linear-gradient(to bottom, transparent, rgba(59, 130, 246, 0.3), transparent);
  margin: 0 auto;
}

.center-dot {
  width: 8px;
  height: 8px;
  background: rgba(59, 130, 246, 0.5);
  border-radius: 50%;
  margin: -4px auto 0;
  animation: centerPulse 2s infinite;
}

@keyframes centerPulse {
  0%, 100% { 
    opacity: 0.5; 
    transform: scale(1); 
  }
  50% { 
    opacity: 0.8; 
    transform: scale(1.3); 
  }
}

.answer-card-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 0.4rem;
  padding: 0.5rem;
  justify-items: center;
  align-items: center;
  width: 100%;
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
  transition: all 0.3s ease;
  cursor: pointer;
  position: relative;
  min-width: 36px;
  min-height: 36px;
}

.question-number-btn:hover:not(.current):not(.correct):not(.wrong):not(.preview-btn) {
  border-color: #3b82f6;
  color: #3b82f6;
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(59, 130, 246, 0.2);
}

.question-number-btn.current {
  background: linear-gradient(135deg, #3b82f6, #60a5fa);
  color: white;
  border: none;
  transform: scale(1.15);
  box-shadow: 0 4px 16px rgba(59, 130, 246, 0.4);
  z-index: 2;
  position: relative;
}

.question-number-btn.current::before {
  content: '';
  position: absolute;
  inset: -3px;
  border-radius: 12px;
  background: linear-gradient(135deg, #3b82f6, #60a5fa);
  z-index: -1;
  opacity: 0.2;
  animation: currentPulse 2s infinite;
}

@keyframes currentPulse {
  0%, 100% { 
    opacity: 0.2; 
    transform: scale(1); 
  }
  50% { 
    opacity: 0.4; 
    transform: scale(1.1); 
  }
}

.question-number-btn.correct {
  background: linear-gradient(135deg, #10b981, #34d399);
  color: white;
  border: none;
}

.question-number-btn.wrong {
  background: linear-gradient(135deg, #ef4444, #f87171);
  color: white;
  border: none;
}

.question-number-btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

/* 优化的模糊预览按钮样式 */
.question-number-btn.preview-btn {
  opacity: 0.25;
  filter: blur(0.8px);
  transform: scale(0.88);
  pointer-events: none;
  transition: all 0.4s ease;
  font-size: 0.8rem;
  background: #f8fafc;
  color: #9ca3af;
  border-color: #e2e8f0;
}

/* 预览按钮的状态颜色 */
.question-number-btn.preview-btn.correct {
  background: rgba(16, 185, 129, 0.15);
  color: rgba(16, 185, 129, 0.5);
  border-color: rgba(16, 185, 129, 0.2);
}

.question-number-btn.preview-btn.wrong {
  background: rgba(239, 68, 68, 0.15);
  color: rgba(239, 68, 68, 0.5);
  border-color: rgba(239, 68, 68, 0.2);
}

.question-number-btn.preview-btn.unanswered {
  background: rgba(229, 231, 235, 0.3);
  color: rgba(107, 114, 128, 0.5);
  border-color: rgba(229, 231, 235, 0.4);
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

/* 响应式设计 */
@media (max-width: 1024px) {
  .answer-card-panel {
    order: -1;
    position: static;
    width: 100%;
  }
}

@media (max-width: 768px) {
  .answer-card-panel {
    width: 100%;
    padding: 1rem;
  }
  
  /* 收缩时的紧凑布局 */
  .answer-card-panel:not(.expanded) {
    padding: 0.75rem 1rem;
  }
  
  .answer-card-grid {
    gap: 0.3rem;
    padding: 0.3rem;
  }

  .question-number-btn {
    min-width: 32px;
    min-height: 32px;
    font-size: 0.8rem;
  }
}

@media (max-width: 576px) {
  .answer-card-panel {
    padding: 0.75rem;
  }
  
  .answer-card-grid {
    gap: 0.25rem;
    padding: 0.25rem;
  }

  .question-number-btn {
    min-width: 28px;
    min-height: 28px;
    font-size: 0.75rem;
    border-radius: 6px;
  }
  
  .question-number-btn.current {
    transform: scale(1.1);
  }
  
  .btn-answer-card-action {
    padding: 0.5rem 0.75rem;
    font-size: 0.8rem;
  }
}

.compact-progress {
  font-size: 0.9rem;
  color: #6b7280;
  background: #f3f4f6;
  padding: 0.25rem 0.75rem;
  border-radius: 999px;
  font-weight: 500;
}
</style> 