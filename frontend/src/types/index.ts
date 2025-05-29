export type QuestionType = '单选题' | '多选题' | '判断题' | '选择题';

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