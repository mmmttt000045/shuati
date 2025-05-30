<template>
  <div class="container practice-container">
    <div class="practice-layout">
      <!-- 左侧主要内容区域 -->
      <div class="practice-main">
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
                :style="{ width: (progress.current / progress.total) * 100 + '%' }"
                class="progress-bar-inner"
              ></div>
            </div>
          </div>
        </div>

        <ul v-if="messages.length > 0" class="flash-messages">
          <li v-for="(message, index) in messages" :key="index" :class="message.category">
            {{ message.text }}
          </li>
        </ul>

        <!-- 友好提示 -->
        <div v-if="!initializing && displayMode === 'question'" class="session-info">
          <div class="session-info-content">
            <span class="info-icon">💡</span>
            <span class="info-text">提示：刷新页面后练习进度会自动保存和恢复</span>
          </div>
        </div>

        <!-- 题目和反馈区域的过渡容器 -->
        <transition name="content-fade" mode="out-in">
          <!-- Question Display Mode -->
          <div v-if="displayMode === 'question' && question" key="question" class="question-section card">
            <div class="question-header">
              <div class="question-content">
                <div class="question-text">
                  <span
                    class="question-type-badge"
                    :class="{
                      'multiple-choice-badge': question.type === '多选题',
                      'single-choice-badge': question.type === '单选题',
                      'true-false-badge': question.type === '判断题'
                    }"
                  >
                    {{ getQuestionTypeDisplay(question) }}
                  </span>
                  <span class="question-text-content">{{ question.question }}</span>
                </div>
              </div>
            </div>

            <div class="question-content">
              <!-- 移除了原来的revealed-answer-notice，因为现在直接切换到feedback模式 -->
            </div>

            <form
              class="answer-form"
              @submit.prevent="submitAnswer()"
            >
              <div class="options-grid">
                <!-- 选择题 (单选/多选) -->
                <template v-if="question.type !== '判断题' && question.options_for_practice && Object.keys(shuffledMcqOptions).length > 0">
                  <label
                    v-for="(option_text, original_key) in shuffledMcqOptions"
                    :key="original_key"
                    :class="{
                      'option-label': true,
                      'selected': question.is_multiple_choice
                        ? selectedAnswers.has(original_key)
                        : selectedAnswer === original_key,
                      'multiple-choice-option': question.is_multiple_choice
                    }"
                    class="card-hover"
                  >
                    <input
                      :checked="question.is_multiple_choice ? selectedAnswers.has(original_key) : selectedAnswer === original_key"
                      :disabled="displayMode === 'feedback'"
                      :name="question.is_multiple_choice ? `answer_mcq_${original_key}` : 'answer_scq'"
                      :type="question.is_multiple_choice ? 'checkbox' : 'radio'"
                      :value="original_key"
                      @change="handleOptionSelect(original_key)"
                      class="option-input"
                    />
                    <span v-if="question.is_multiple_choice" class="checkbox-custom-display" :class="{'checked': selectedAnswers.has(original_key)}"></span>
                    <span v-else class="radio-custom-display" :class="{'checked': selectedAnswer === original_key}"></span>
                    <span class="option-key">{{ original_key }}</span>
                    <span class="option-text">{{ option_text }}</span>
                  </label>
                </template>
                <p v-else-if="question.type !== '判断题' && (!question.options_for_practice || Object.keys(shuffledMcqOptions).length === 0)" class="empty-state-message">
                  此选择题没有可显示的选项。
                </p>

                <!-- 判断题 -->
                <template v-else-if="question.type === '判断题'">
                  <label
                    v-for="(option, key) in tfOptions"
                    :key="key"
                    :class="{
                      'option-label': true,
                      'selected': selectedAnswer === key
                    }"
                    class="card-hover"
                  >
                    <input
                      :checked="selectedAnswer === key"
                      :disabled="displayMode === 'feedback'"
                      name="answer_tf"
                      type="radio"
                      :value="key"
                      @change="handleOptionSelect(key)"
                      class="option-input"
                      required
                    />
                    <span class="radio-custom-display" :class="{'checked': selectedAnswer === key}"></span>
                    <span class="option-text">{{ option.text }}</span>
                  </label>
                </template>
                <p v-else class="empty-state-message">
                   题目数据不完整或类型无法识别。
                </p>
              </div>

              <div class="action-buttons">
                <button
                  :disabled="loadingSubmit ||
                             (displayMode === 'question' && question.type !== '判断题' && question.is_multiple_choice && selectedAnswers.size === 0) ||
                             (displayMode === 'question' && question.type !== '判断题' && !question.is_multiple_choice && !selectedAnswer) ||
                             (displayMode === 'question' && question.type === '判断题' && !selectedAnswer)"
                  class="btn btn-submit"
                  type="submit"
                >
                  提交答案
                </button>
                <button
                  :disabled="loadingSubmit || loadingReveal || displayMode === 'feedback'"
                  :class="['btn', 'btn-reveal', { 'loading': loadingReveal }]"
                  type="button"
                  @click="revealAnswer"
                >
                  <span v-if="!loadingReveal">查看答案</span>
                  <span v-else>正在加载</span>
                </button>
              </div>
            </form>
          </div>

          <!-- Feedback Display Mode -->
          <div
            v-else-if="displayMode === 'feedback' && currentFeedback && question"
            key="feedback"
            class="feedback-section card"
          >
            <!-- 查看历史记录的标识 -->
            <div v-if="isViewingHistory" class="history-notice">
              <span class="history-icon">📋</span>
              <span class="history-text">查看答题历史记录</span>
            </div>

            <div
              :class="currentFeedback.is_correct ? 'feedback-correct' : 'feedback-incorrect'"
              class="feedback-banner"
            >
              <span class="feedback-icon">{{ currentFeedback.is_correct ? '🎉' : '❌' }}</span>
              {{ currentFeedback.is_correct ? '回答正确！' : '回答错误。' }}
            </div>

            <div class="question-review-content">
              <h4>题目回顾：</h4>
              <p class="question-text-review">{{ question.question }}</p>

              <div class="answer-comparison">
                <!-- 选择题的选项展示 -->
                <div v-if="question.type !== '判断题' && question.options_for_practice" class="options-review">
                  <strong>所有选项：</strong>
                  <div class="options-grid review-mode">
                    <div
                      v-for="(option_text, key) in question.options_for_practice"
                      :key="key"
                      :class="{
                        'option-review': true,
                        'option-correct': question.answer.includes(key),
                        'option-incorrect': !currentFeedback.is_correct &&
                                         (currentFeedback.user_answer_display.startsWith(key) ||
                                          currentFeedback.user_answer_display.includes(' + ' + key + '.'))
                      }"
                    >
                      <span class="option-key">{{ key }}</span>
                      <span class="option-text">{{ option_text }}</span>
                    </div>
                  </div>
                </div>

                <!-- 只在答错时显示答案比较 -->
                <template v-if="!currentFeedback.is_correct">
                  <div class="answer-item">
                    <strong>你的答案：</strong>
                    <span class="user-answer-text-incorrect">{{ currentFeedback.user_answer_display }}</span>
                  </div>

                  <div class="answer-item">
                    <strong>正确答案：</strong>
                    <span class="correct-answer-text">{{ currentFeedback.correct_answer_display }}</span>
                  </div>
                </template>

                <div v-if="question.analysis" class="answer-item">
                  <strong>题目分析：</strong>
                  <p>{{ question.analysis }}</p>
                </div>

                <div v-if="question.knowledge_points && question.knowledge_points.length > 0" class="answer-item">
                  <strong>知识点：</strong>
                  <div class="knowledge-points">
                    <span v-for="(point, index) in question.knowledge_points"
                          :key="index"
                          class="knowledge-point-tag">
                      {{ point }}
                    </span>
                  </div>
                </div>

                <div v-if="currentFeedback.explanation" class="answer-item">
                  <strong>解释：</strong>
                  <p>{{ currentFeedback.explanation }}</p>
                </div>
              </div>
            </div>

            <div class="feedback-actions">
              <button v-if="!isViewingHistory" class="btn-continue" @click="handleContinueAfterReveal">
                继续练习
              </button>
              <button v-else class="btn-continue" @click="backToCurrentQuestion">
                返回当前题目
              </button>
            </div>
          </div>
        </transition>

        <div v-if="loading && displayMode === 'question'" class="loading-indicator-fullscreen">
          <p>题目正在加载中，请稍候...</p>
        </div>

        <div v-if="initializing" class="loading-indicator-fullscreen">
          <p>正在初始化练习会话，请稍候...</p>
        </div>

        <div
          v-if="!loading && !initializing && !question && displayMode === 'question'"
          class="empty-state-message card"
        >
          <p>当前没有题目可以练习，或题目加载失败。</p>
        </div>
      </div>

      <!-- 右侧答题卡 -->
      <div class="answer-card-panel" :class="{ 'history-mode': isViewingHistory }">
        <div class="answer-card-header">
          <div class="answer-card-title">
            <h3>答题卡</h3>
            <button
              class="btn-toggle"
              @click="isAnswerCardExpanded = !isAnswerCardExpanded"
              :title="isAnswerCardExpanded ? '收起答题卡' : '展开答题卡'"
            >
              {{ isAnswerCardExpanded ? '↑' : '↓' }}
            </button>
          </div>

          <!-- 在查看历史时显示提示 -->
          <div v-if="isViewingHistory" class="history-navigation-tip">
            <span class="tip-icon">💡</span>
            <span class="tip-text">点击答题卡可查看其他题目</span>
          </div>

          <div class="answer-card-legend" v-if="isAnswerCardExpanded">
            <span class="legend-item">
              <span class="status-dot current"></span> 当前题目
            </span>
            <span class="legend-item">
              <span class="status-dot correct"></span> 已答对
            </span>
            <span class="legend-item">
              <span class="status-dot wrong"></span> 已答错
            </span>
            <span class="legend-item">
              <span class="status-dot"></span> 未作答
            </span>
          </div>
        </div>
        <div
          class="answer-card-grid-container"
          :class="{ 'expanded': isAnswerCardExpanded }"
        >
          <div class="answer-card-grid">
            <template v-if="isAnswerCardExpanded">
              <!-- 展开状态：显示所有题目 -->
              <button
                v-for="(status, index) in questionStatuses"
                :key="index"
                class="question-number-btn"
                :class="{
                  current: index === currentQuestionIndex,
                  correct: status === 'correct',
                  wrong: status === 'wrong',
                  unanswered: status === 'unanswered'
                }"
                @click="jumpToQuestion(index)"
                :disabled="!canJumpToQuestion"
              >
                {{ index + 1 }}
              </button>
            </template>
            <template v-else>
              <!-- 折叠状态：只显示部分题目 -->
              <button
                v-for="item in visibleQuestions"
                :key="item.number"
                class="question-number-btn"
                :class="{
                  current: item.isCurrent,
                  correct: item.status === 'correct',
                  wrong: item.status === 'wrong',
                  unanswered: item.status === 'unanswered'
                }"
                @click="jumpToQuestion(item.number - 1)"
                :disabled="!canJumpToQuestion"
              >
                {{ item.number }}
              </button>
            </template>
          </div>
        </div>
      </div>
    </div>

    <div class="footer-credit">Created by MingTai</div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue';
import { useRouter } from 'vue-router';
import type { Question, Progress, FlashMessage, Feedback } from '@/types';
import { apiService } from '@/services/api';

interface QuestionStatus {
  status: 'unanswered' | 'correct' | 'wrong';
  number: number;
  isCurrent: boolean;
}

const props = defineProps<{
  subject: string;
  fileName: string;
}>();

const router = useRouter();

const question = ref<Question | null>(null);
const progress = ref<Progress | null>(null);
const messages = ref<FlashMessage[]>([]);
const displayMode = ref<'question' | 'feedback'>('question');
const currentFeedback = ref<Feedback | null>(null);
const loadingSubmit = ref(false);
const loading = ref(false);
const initializing = ref(true);
const loadingReveal = ref(false);
const selectedAnswer = ref<string>('');
const selectedAnswers = ref<Set<string>>(new Set());
const shuffledMcqOptions = ref<Record<string, string>>({});

const tfOptions = {
  'T': { text: '正确' },
  'F': { text: '错误' }
};

// 添加是否为查看历史的状态
const isViewingHistory = ref(false);

onMounted(async () => {
  try {
    // 首先检查是否已有活跃的练习会话
    console.log('Checking existing session status...');
    const sessionStatus = await apiService.checkSessionStatus();

    if (sessionStatus.active) {
      console.log('Found active session:', sessionStatus);

      // 检查会话是否已完成
      if (sessionStatus.completed) {
        console.log('Session completed, redirecting to completed page');
        router.push('/completed');
        return;
      }

      // 检查会话文件是否与当前请求的文件匹配
      if (sessionStatus.file_info && sessionStatus.file_info.key === props.fileName) {
        console.log('Resuming existing session for same file');

        // 显示恢复会话的提示信息
        if (sessionStatus.progress) {
          messages.value.push({
            category: 'info',
            text: `已恢复练习进度：第${sessionStatus.progress.round}轮，第${sessionStatus.progress.current}/${sessionStatus.progress.total}题`
          });
        }

        // 恢复答题卡状态
        if (sessionStatus.question_statuses && sessionStatus.question_statuses.length > 0) {
          questionStatuses.value = [...sessionStatus.question_statuses];
          console.log('Restored question statuses:', questionStatuses.value);
        }

        // 直接加载当前题目，无需重新开始练习
        await loadQuestion();
        return;
      } else if (sessionStatus.file_info) {
        console.log('Active session for different file, starting new practice');

        // 显示切换题库的提示信息
        messages.value.push({
          category: 'info',
          text: `已从《${sessionStatus.file_info.display}》切换到当前题库`
        });

        // 当前有其他文件的会话，需要强制重新开始
        const startResponse = await apiService.startPractice(props.subject, props.fileName, true);
        if (!startResponse.success) {
          throw new Error(startResponse.message);
        }
      }
    } else {
      console.log('No active session found, starting new practice');
      // 没有活跃会话，开始新的练习
      const startResponse = await apiService.startPractice(props.subject, props.fileName);
      if (!startResponse.success) {
        throw new Error(startResponse.message);
      }
    }

    // 加载第一题或当前题目
    await loadQuestion();

  } catch (error) {
    console.error('Error initializing practice:', error);
    messages.value.push({
      category: 'error',
      text: error instanceof Error ? error.message : 'Failed to initialize practice session'
    });
    setTimeout(() => {
      router.push('/');
    }, 3000);
  } finally {
    initializing.value = false;  // 初始化完成
  }
});

const loadQuestion = async () => {
  loading.value = true;
  try {
    const response = await apiService.getCurrentQuestion();

    if (response.redirect_to_completed) {
      router.push('/completed');
      return;
    }

    if (response.question) {
      question.value = response.question;
      progress.value = response.progress;
      messages.value = response.flash_messages || [];
      displayMode.value = 'question';
      isViewingHistory.value = false;  // 重置查看历史状态
      selectedAnswer.value = '';
      selectedAnswers.value = new Set();
      currentFeedback.value = null;

      // 确保答题卡状态数组长度与当前轮次题目数量匹配
      if (progress.value && questionStatuses.value.length !== progress.value.total) {
        console.log(`Adjusting question statuses length from ${questionStatuses.value.length} to ${progress.value.total}`);

        if (questionStatuses.value.length < progress.value.total) {
          // 如果答题卡状态数组长度不够，用'unanswered'填充
          const additionalStatuses = new Array(progress.value.total - questionStatuses.value.length).fill('unanswered');
          questionStatuses.value = [...questionStatuses.value, ...additionalStatuses];
        } else {
          // 如果答题卡状态数组过长，截取到正确长度
          questionStatuses.value = questionStatuses.value.slice(0, progress.value.total);
        }
      }

      // 重置选项
      if (question.value.options_for_practice) {
        shuffledMcqOptions.value = JSON.parse(JSON.stringify(question.value.options_for_practice));
      } else {
        shuffledMcqOptions.value = {};
      }
    } else {
      throw new Error('Failed to load question data');
    }
  } catch (error) {
    console.error('Error loading question:', error);
    messages.value.push({
      category: 'error',
      text: error instanceof Error ? error.message : 'Failed to load question'
    });
  } finally {
    loading.value = false;
  }
};

const handleOptionSelect = (key: string) => {
  if (!question.value) return;

  if (question.value.is_multiple_choice) {
    if (selectedAnswers.value.has(key)) {
      selectedAnswers.value.delete(key);
    } else {
      selectedAnswers.value.add(key);
    }
  } else {
    selectedAnswer.value = key;
  }
};

const submitAnswer = async () => {
  if (!question.value || loadingSubmit.value) return;

  loadingSubmit.value = true;
  try {
    const answer = question.value.is_multiple_choice
      ? Array.from(selectedAnswers.value).sort().join('')
      : selectedAnswer.value;

    const feedback = await apiService.submitAnswer(
      answer,
      question.value.id,
      false, // 未查看答案
      false  // 不是复习模式
    );

    currentFeedback.value = feedback;
    displayMode.value = 'feedback';
    isViewingHistory.value = false;  // 正常答题，不是查看历史

    // 更新答题卡状态
    if (currentQuestionIndex.value >= 0 && currentQuestionIndex.value < questionStatuses.value.length) {
      updateQuestionStatus(currentQuestionIndex.value, feedback.is_correct);
    }

    // 同步后端状态，确保一致性
    setTimeout(async () => {
      await syncQuestionStatuses();
    }, 100); // 短暂延迟确保后端已更新
  } catch (error) {
    console.error('Error submitting answer:', error);
    messages.value.push({
      category: 'error',
      text: error instanceof Error ? error.message : 'Failed to submit answer'
    });
  } finally {
    loadingSubmit.value = false;
  }
};

const revealAnswer = async () => {
  if (!question.value || loadingReveal.value) return;

  loadingReveal.value = true;

  try {
    // 先准备所有需要的数据，避免多次状态切换
    const questionId = question.value.id;
    const currentIndex = currentQuestionIndex.value;

    // 提交查看答案的请求
    const feedback = await apiService.submitAnswer(
      '',  // 空答案
      questionId,
      true, // 标记为已查看答案
      false // 不是复习模式
    );

    // 获取题目解析
    const analysisResponse = await apiService.getQuestionAnalysis(questionId);

    // 准备反馈数据
    const feedbackData: Feedback = {
      is_correct: false,
      user_answer_display: '未作答（直接查看答案）',
      correct_answer_display: formatAnswerWithOptions(
        question.value.answer,
        question.value.options_for_practice,
        question.value.is_multiple_choice
      ),
      question_id: questionId,
      current_index: currentIndex
    };

    // 如果获取到解析，更新题目数据
    if (analysisResponse.success) {
      question.value = {
        ...question.value,
        analysis: analysisResponse.analysis,
        knowledge_points: analysisResponse.knowledge_points
      };
    }

    // 一次性更新所有状态，避免多次重渲染
    currentFeedback.value = feedbackData;

    // 标记当前题目为错误（用于答题卡显示）
    if (currentIndex >= 0 && currentIndex < questionStatuses.value.length) {
      updateQuestionStatus(currentIndex, false);
    }

    // 最后切换到反馈模式
    displayMode.value = 'feedback';
    isViewingHistory.value = true;

  } catch (error) {
    console.error('Error revealing answer:', error);
    messages.value.push({
      category: 'error',
      text: error instanceof Error ? error.message : 'Failed to reveal answer'
    });
  } finally {
    loadingReveal.value = false;
  }
};

const handleContinueAfterReveal = async () => {
  try {
    // 重置状态
    selectedAnswer.value = '';
    selectedAnswers.value = new Set();
    currentFeedback.value = null;
    displayMode.value = 'question';

    // 加载下一题
    await loadQuestion();

    // 同步答题卡状态，确保与后端一致
    await syncQuestionStatuses();
  } catch (error) {
    console.error('Error continuing to next question:', error);
    messages.value.push({
      category: 'error',
      text: error instanceof Error ? error.message : '加载下一题时发生错误'
    });
  }
};

const backToCurrentQuestion = async () => {
  try {
    // 重置状态
    selectedAnswer.value = '';
    selectedAnswers.value = new Set();
    currentFeedback.value = null;
    displayMode.value = 'question';

    // 加载当前题目
    await loadQuestion();
  } catch (error) {
    console.error('Error returning to current question:', error);
    messages.value.push({
      category: 'error',
      text: error instanceof Error ? error.message : '返回当前题目时发生错误'
    });
  }
};

const goBackToIndexPage = () => {
  router.push('/');
};

const formatAnswerWithOptions = (answer: string, options?: Record<string, string>, isMultipleChoice = false) => {
  if (!options) return answer;

  if (isMultipleChoice) {
    return answer.split('').map(key => `${key}. ${options[key] || ''}`).join(' + ');
  }
  return `${answer}. ${options[answer] || ''}`;
};

const getQuestionTypeDisplay = (q: Question): string => {
  return q.type;
};

// Answer Card State
const isAnswerCardExpanded = ref(false);
const questionStatuses = ref<Array<'unanswered' | 'correct' | 'wrong'>>([]);
const currentQuestionIndex = computed(() => (progress.value ? progress.value.current - 1 : 0));
const canJumpToQuestion = computed(() => {
  // 允许在以下情况下跳转：
  // 1. 正常的题目模式
  // 2. 正在查看历史记录的反馈模式
  return (displayMode.value === 'question' || isViewingHistory.value) && !loading.value;
});

const visibleQuestions = computed<QuestionStatus[]>(() => {
  if (!progress.value) return []; // Guard against progress being null
  const totalActualQuestions = progress.value.total; // This should be total in current round

  // If questionStatuses hasn't caught up with totalActualQuestions, initialize/resize it
  if (questionStatuses.value.length !== totalActualQuestions && totalActualQuestions > 0) {
    // This is a temporary fix. Ideally, questionStatuses is always in sync or derived differently.
    // For now, we fill with unanswered if it's out of sync.
    const newStatuses = new Array(totalActualQuestions).fill('unanswered');
    // Preserve existing statuses if possible (e.g. if total decreased, this won't happen often)
    for (let i = 0; i < Math.min(questionStatuses.value.length, totalActualQuestions); i++) {
      newStatuses[i] = questionStatuses.value[i];
    }
    // eslint-disable-next-line vue/no-side-effects-in-computed-properties
    questionStatuses.value = newStatuses;
  }

  const statusesToDisplay = questionStatuses.value.slice(0, totalActualQuestions);

  if (isAnswerCardExpanded.value) {
    return statusesToDisplay.map((status, index) => ({
      status,
      number: index + 1,
      isCurrent: index === currentQuestionIndex.value
    }));
  }

  const currentIndex = currentQuestionIndex.value;
  const displayCount = 15; // Number of items to show when collapsed
  const halfDisplay = Math.floor(displayCount / 2);

  let startIndex = Math.max(0, currentIndex - halfDisplay);
  const endIndex = Math.min(totalActualQuestions, startIndex + displayCount);

  if (endIndex - startIndex < displayCount && totalActualQuestions >= displayCount) {
    startIndex = Math.max(0, endIndex - displayCount);
  }

  return statusesToDisplay.slice(startIndex, endIndex).map((status, index) => ({
    status,
    number: startIndex + index + 1,
    isCurrent: (startIndex + index) === currentIndex
  }));
});

const initializeQuestionStatuses = (totalQuestions: number) => {
  if (totalQuestions > 0) {
    questionStatuses.value = new Array(totalQuestions).fill('unanswered');
  }
};

const updateQuestionStatus = (index: number, isCorrect: boolean) => {
  if (index >= 0 && index < questionStatuses.value.length) {
    questionStatuses.value[index] = isCorrect ? 'correct' : 'wrong';
  }
};

// Watch for changes in total questions to initialize/reset statuses
watch(() => progress.value?.total, (newTotal) => {
  if (newTotal && newTotal > 0) {
    // Only initialize if the number of statuses doesn't match or is empty
    // This prevents re-initializing on round changes if total is coincidentally the same
    if (questionStatuses.value.length !== newTotal) {
      initializeQuestionStatuses(newTotal);
    }
  } else {
    questionStatuses.value = []; // Clear statuses if no questions
  }
}, { immediate: true }); // Immediate true to run on mount if progress is already there

const jumpToQuestion = async (index: number) => {
  if (!canJumpToQuestion.value) return;

  loading.value = true;
  try {
    // 检查题目状态，如果已经做过，直接显示反馈
    const questionStatus = questionStatuses.value[index];

    if (questionStatus === 'correct' || questionStatus === 'wrong') {
      // 题目已做过，获取答题历史并显示反馈
      console.log(`Question ${index} already answered, showing feedback`);

      const historyResponse = await apiService.getQuestionHistory(index);
      if (historyResponse.success && historyResponse.question && historyResponse.feedback) {
        // 设置题目和反馈数据
        question.value = historyResponse.question;
        currentFeedback.value = historyResponse.feedback;

        // 更新进度信息
        if (progress.value) {
          progress.value.current = index + 1;
        }

        // 切换到反馈模式
        displayMode.value = 'feedback';
        isViewingHistory.value = true;

        return;
      } else {
        console.error('Failed to get question history:', historyResponse.message);
        // 如果获取历史失败，fallback到正常跳转
      }
    }

    // 未做过的题目或获取历史失败，正常跳转
    // 如果当前在查看历史，先清除查看历史状态
    if (isViewingHistory.value) {
      isViewingHistory.value = false;
    }

    const response = await apiService.jumpToQuestion(index);
    if (response.success) {
      await loadQuestion();
    } else {
      messages.value.push({
        category: 'error',
        text: response.message || '跳转失败'
      });
    }
  } catch (error) {
    console.error('Error jumping to question:', error);
    messages.value.push({
      category: 'error',
      text: error instanceof Error ? error.message : '跳转时发生错误'
    });
  } finally {
    loading.value = false;
  }
};

// 同步答题卡状态
const syncQuestionStatuses = async () => {
  try {
    const statusResponse = await apiService.getQuestionStatuses();
    if (statusResponse.success && statusResponse.statuses.length > 0) {
      // 只有当状态不同时才更新，避免不必要的重渲染
      if (JSON.stringify(questionStatuses.value) !== JSON.stringify(statusResponse.statuses)) {
        questionStatuses.value = [...statusResponse.statuses];
        console.log('Synced question statuses from backend:', questionStatuses.value);
      }
    }
  } catch (error) {
    console.error('Error syncing question statuses:', error);
  }
};

</script>

<style scoped>
.practice-container {
  max-width: 1200px;
  margin: 2rem auto;
  padding: 2rem;
  background: linear-gradient(to bottom right, #ffffff, #f8f9fa);
  border-radius: 16px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
}

.practice-layout {
  display: flex;
  gap: 2rem;
  align-items: flex-start;
}

.practice-main {
  flex: 1;
  min-width: 0;
}

.page-header {
  display: flex;
  align-items: center;
  gap: 2rem;
  margin-bottom: 2rem;
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

.progress-bar-wrapper {
  flex: 1;
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

.btn-navigate-back:hover {
  background-color: #3b82f6;
  color: white;
  transform: translateY(-2px);
}

.question-header {
  margin-bottom: 1.5rem;
}

.question-content {
  margin-bottom: 2rem;
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
  box-shadow: 0 2px 8px rgba(59, 130, 246, 0.15);
  flex-shrink: 0;
  margin-top: 0.2rem;
}

.question-text-content {
  flex: 1;
}

.question-section {
  background: white;
  border-radius: 16px;
  padding: 2rem;
  margin-bottom: 2rem;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.06);
}

.question-type-badge.multiple-choice-badge {
  background: linear-gradient(135deg, #8B5CF6, #C084FC);
}

.question-type-badge.single-choice-badge {
  background: linear-gradient(135deg, #3B82F6, #60A5FA);
}

.question-type-badge.true-false-badge {
  background: linear-gradient(135deg, #10B981, #34D399);
}

.options-grid {
  display: flex;
  flex-direction: column;
  gap: 1rem;
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

.checkbox-custom-display {
  width: 1.5rem;
  height: 1.5rem;
  border: 2px solid #60a5fa;
  position: absolute;
  left: 1rem;
  top: 50%;
  transform: translateY(-50%);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
  border-radius: 4px;
  background-color: white;
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

.option-label.multiple-choice-option {
  padding-left: 3.5rem;
  border-width: 2px;
}

.option-label.multiple-choice-option:hover {
  border-color: #3b82f6;
  background-color: #f8fafc;
}

.option-label.multiple-choice-option.selected {
  background-color: #eff6ff;
  border-color: #3b82f6;
}

.option-label.multiple-choice-option.correct-answer-highlight {
  background-color: #ecfdf5;
  border-color: #059669;
}

.multiple-choice-hint {
  margin: 1rem 0;
  padding: 1rem;
  background-color: #eff6ff;
  border: 2px solid #3b82f6;
  border-radius: 8px;
  color: #1e40af;
  display: flex;
  align-items: center;
  font-size: 0.95rem;
  font-weight: 500;
}

.hint-icon {
  margin-right: 0.75rem;
  font-size: 1.25rem;
}

.radio-custom-display {
  width: 1.25rem;
  height: 1.25rem;
  border: 2px solid #60a5fa;
  position: absolute;
  left: 0.75rem;
  top: 50%;
  transform: translateY(-50%);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
  border-radius: 50%;
  background-color: white;
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

.option-label:hover .checkbox-custom-display:not(.checked),
.option-label:hover .radio-custom-display:not(.checked) {
  border-color: #2563eb;
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
  position: relative;
  overflow: hidden;
}

.btn-reveal:hover:not(:disabled) {
  border-color: #3b82f6;
  color: #3b82f6;
}

.btn-reveal:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-reveal.loading {
  color: #3b82f6;
  border-color: #3b82f6;
}

.btn-reveal.loading::after {
  content: '';
  position: absolute;
  top: 50%;
  left: 50%;
  width: 16px;
  height: 16px;
  margin: -8px 0 0 -8px;
  border: 2px solid transparent;
  border-top: 2px solid currentColor;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.feedback-section {
  background: white;
  border-radius: 16px;
  padding: 2rem;
  animation: slideIn 0.3s ease-out;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.feedback-banner {
  display: flex;
  align-items: center;
  padding: 1.5rem 2rem;
  border-radius: 12px;
  margin-bottom: 2rem;
  font-weight: 600;
  font-size: 1.2rem;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

.feedback-banner.feedback-correct {
  background: linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%);
  color: #059669;
  border: none;
}

.feedback-banner.feedback-incorrect {
  background: linear-gradient(135deg, #fef2f2 0%, #fee2e2 100%);
  color: #dc2626;
  border: none;
}

.feedback-icon {
  font-size: 2rem;
  margin-right: 1rem;
  animation: bounce 0.6s ease-in-out;
}

@keyframes bounce {
  0%, 20%, 50%, 80%, 100% {
    transform: translateY(0);
  }
  40% {
    transform: translateY(-20px);
  }
  60% {
    transform: translateY(-10px);
  }
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

.user-answer-text-correct {
  color: #059669;
  font-weight: 600;
  padding: 0.5rem 1rem;
  background: #ecfdf5;
  border-radius: 6px;
  display: inline-block;
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

.feedback-actions {
  display: flex;
  justify-content: center;
  gap: 1rem;
  margin-top: 2rem;
  padding-top: 1rem;
  border-top: 2px solid #e5e7eb;
}

.btn-continue {
  background: linear-gradient(135deg, #3b82f6, #60a5fa);
  color: white;
  padding: 0.75rem 2rem;
  border-radius: 8px;
  font-weight: 600;
  transition: all 0.3s ease;
  min-width: 160px;
}

.btn-continue:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.25);
}

.answer-card-panel {
  width: 280px;
  background: white;
  border-radius: 16px;
  padding: 1.5rem;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.06);
  position: sticky;
  top: 2rem;
}

.answer-card-header {
  margin-bottom: 1.5rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid #e5e7eb;
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
  font-size: 1.1rem;
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
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.2);
}

.status-dot.correct {
  background-color: #10b981;
  box-shadow: 0 0 0 2px rgba(16, 185, 129, 0.2);
}

.status-dot.wrong {
  background-color: #ef4444;
  box-shadow: 0 0 0 2px rgba(239, 68, 68, 0.2);
}

.answer-card-grid-container {
  position: relative;
  overflow: hidden;
  height: 240px;
  transition: height 0.3s ease;
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
  transform: translateY(-1px);
}

.question-number-btn.current {
  background: #3b82f6;
  color: white;
  border: none;
  transform: scale(1.1);
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.25);
  z-index: 1;
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
  transform: none;
}

/* 缩略模式的特殊样式 */
.answer-card-grid:not(.expanded) {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 0.75rem;
}

.answer-card-grid:not(.expanded) .question-number-btn {
  width: 36px;
  height: 36px;
  font-size: 0.95rem;
}

.answer-card-grid:not(.expanded) .question-number-btn.current {
  position: relative;
}

.answer-card-grid:not(.expanded) .question-number-btn.current::after {
  content: '';
  position: absolute;
  bottom: -4px;
  left: 50%;
  transform: translateX(-50%);
  width: 6px;
  height: 6px;
  background: #3b82f6;
  border-radius: 50%;
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.2);
}

@media (max-width: 1024px) {
  .answer-card-panel {
    width: 100%;
    position: static;
    margin-top: 2rem;
  }

  .answer-card-grid-container {
    height: auto;
    max-height: none;
  }
}

.footer-credit {
  text-align: center;
  margin-top: 3rem;
  padding-top: 1.5rem;
  border-top: 2px solid #e5e7eb;
  color: #6b7280;
  font-size: 0.9rem;
}

@media (max-width: 640px) {
  .practice-container {
    padding: 1rem;
    margin: 1rem;
  }

  .action-buttons {
    flex-direction: column;
  }

  .btn {
    width: 100%;
  }
}

.empty-state-message {
    padding: 1rem;
    text-align: center;
    color: #6b7280;
    background-color: #f3f4f6;
    border-radius: 8px;
    margin-top: 1rem;
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

.answer-item {
  background: white;
  padding: 1.5rem;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  transition: transform 0.2s ease;
}

.answer-item:hover {
  transform: translateY(-2px);
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
  transition: all 0.2s ease;
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

.option-review .option-key {
  font-weight: 600;
  margin-right: 1rem;
  min-width: 24px;
}

.option-review .option-text {
  flex: 1;
}

.session-info {
  background-color: #f8fafc;
  border-radius: 8px;
  padding: 1rem;
  margin-top: 1rem;
}

.session-info-content {
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
  box-shadow: 0 2px 8px rgba(251, 191, 36, 0.15);
}

.history-icon {
  font-size: 1.25rem;
}

.history-text {
  font-size: 1rem;
}

.history-navigation-tip {
  background: #f0f9ff;
  color: #0369a1;
  padding: 0.75rem 1rem;
  border-radius: 6px;
  margin-bottom: 1rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
  font-weight: 500;
  border-left: 3px solid #0ea5e9;
}

.tip-icon {
  font-size: 1rem;
}

.tip-text {
  flex: 1;
}

/* 内容切换过渡动画 */
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

.content-fade-enter-to,
.content-fade-leave-from {
  opacity: 1;
  transform: translateY(0);
}

.practice-container {
  /* Add any additional styles specific to the practice container */
}

/* 查看历史时的答题卡样式 */
.answer-card-panel.history-mode .question-number-btn:not(.current):not(:disabled) {
  cursor: pointer;
  border-color: #0ea5e9;
  transition: all 0.2s ease;
}

.answer-card-panel.history-mode .question-number-btn:not(.current):not(:disabled):hover {
  background: #f0f9ff;
  border-color: #0369a1;
  color: #0369a1;
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(3, 105, 161, 0.15);
}
</style>
