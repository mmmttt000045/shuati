export type QuestionType = '单选题' | '多选题' | '判断题' | '选择题';

// 题目状态常量定义 (与后端保持一致)
export const QUESTION_STATUS = {
  UNANSWERED: 0,  // 未作答
  CORRECT: 1,     // 答对
  WRONG: 2        // 答错/查看答案
} as const;

// 状态类型
export type QuestionStatus = typeof QUESTION_STATUS[keyof typeof QUESTION_STATUS];

// 状态名称映射 (用于显示和CSS类名)
export const STATUS_NAMES = {
  [QUESTION_STATUS.UNANSWERED]: 'unanswered',
  [QUESTION_STATUS.CORRECT]: 'correct',
  [QUESTION_STATUS.WRONG]: 'wrong'
} as const;

// 工具函数：将数字状态转换为字符串名称
export const getStatusName = (status: QuestionStatus): string => {
  return STATUS_NAMES[status] || 'unknown';
};

// 工具函数：检查状态类型
export const isCorrectStatus = (status: QuestionStatus): boolean => status === QUESTION_STATUS.CORRECT;
export const isWrongStatus = (status: QuestionStatus): boolean => status === QUESTION_STATUS.WRONG;
export const isUnansweredStatus = (status: QuestionStatus): boolean => status === QUESTION_STATUS.UNANSWERED;

export interface Question {
  id: string;
  type: string;
  question: string;
  options_for_practice?: Record<string, string>;
  answer: string;
  is_multiple_choice: boolean;
  analysis?: string;
  knowledge_points?: string[];
}

export interface Progress {
  round: number;
  current: number;
  total: number;
}

export interface PracticeProgress {
  current_question: number;
  total_questions: number;
  initial_total: number;
  correct_first_try: number;
  round_number: number;
  progress_percent: number;
}

export interface FlashMessage {
  category: string;
  text: string;
}

export interface Feedback {
  is_correct: boolean;
  user_answer_display: string;
  correct_answer_display: string;
  question_id: string;
  current_index: number;
  explanation?: string;
}

export interface QuestionResponse {
  success: boolean;
  message?: string;
  question: Question;
  progress: Progress;
  flash_messages: FlashMessage[];
  redirect_to_completed?: boolean;
}

export interface ApiResponse {
  success: boolean;
  message?: string;
  question?: Question;
  progress?: Progress;
  flash_messages?: FlashMessage[];
  redirect_to_completed?: boolean;
}

export interface SubjectFile {
  key: string;
  display: string;
  count: number;
  progress?: PracticeProgress | null;
}

export interface SubjectsResponse {
  subjects: Record<string, SubjectFile[]>;
  message?: string;
}

export interface CompletedSummary {
  initial_total: number;
  correct_first_try: number;
  score_percent: number;
  completed_filename: string;
}

export interface CompletedResponse {
  message: string;
  success: boolean;
  summary?: CompletedSummary;
  flash_messages?: FlashMessage[];
  stats?: {
    total_questions: number;
    correct_answers: number;
    accuracy: number;
    time_spent: string;
  };
}

export interface ApiError {
  message: string;
  success?: boolean;
} 