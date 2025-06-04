export type QuestionType = '单选题' | '多选题' | '判断题' | '选择题';

// 用户身份模型常量定义
export const USER_MODEL = {
  NORMAL: 0,    // 普通用户
  VIP: 5,       // VIP用户
  ROOT: 10      // 管理员
} as const;

// 用户身份类型
export type UserModel = typeof USER_MODEL[keyof typeof USER_MODEL];

// 用户身份名称映射
export const USER_MODEL_NAMES = {
  [USER_MODEL.NORMAL]: '普通用户',
  [USER_MODEL.VIP]: 'VIP用户',
  [USER_MODEL.ROOT]: '管理员'
} as const;

// 用户信息接口
export interface User {
  user_id: number;
  username: string;
  is_enabled?: boolean;
  created_at?: string;
  model: UserModel;
}

// 新增 SessionInfo 接口
export interface SessionInfo {
  session_id?: string; // session_id might not always be present depending on backend setup
  user_id: number | null;
  username: string | null;
  is_authenticated: boolean;
  session_valid: boolean;
  expires_at: string | null; // ISO date string
  time_remaining: number | null; // in seconds
  warning_threshold_reached?: boolean;
  warning_shown?: boolean;
}

// 新增 LoginSuccessPayload 接口
export interface LoginSuccessPayload {
  user: User;
  session: SessionInfo;
}

// 认证响应接口 (修改为泛型以支持不同data类型)
export interface AuthResponse<T = any> { // T can be LoginSuccessPayload or other specific data
  success: boolean;
  message?: string;
  data?: T; // Renamed from 'user' to 'data' for generality for other auth calls
  error?: string; // Optional error field, usually populated by frontend services
}

// Data structure for the /api/auth/check endpoint's successful response data field
export interface AuthCheckClientResponseData {
  authenticated: boolean;
  user?: User;
}

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
  round_number: number;
  current: number;
  total: number;
  correct_count?: number;
  initial_total?: number;
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
  tiku_id?: number;
  file_size?: number;
  updated_at?: string;
}

export interface SubjectData {
  files: SubjectFile[];
  exam_time?: string | null;
}

export interface SubjectsResponse {
  success: boolean;
  subjects: Record<string, SubjectData>;
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

// Added from api.ts for admin and other API responses

// General
export interface Pagination {
  page: number;
  per_page: number;
  total: number;
  total_pages: number;
  has_prev: boolean;
  has_next: boolean;
}

export interface SearchParams {
  search?: string;
  order_by?: string;
  order_dir?: 'asc' | 'desc';
  page?: number;
  per_page?: number;
}

// Admin specific types
export interface AdminStats {
  users: {
    total: number;
    active: number;
    admins: number;
    vips: number;
  };
  invitations: {
    total: number;
    unused: number;
    used: number;
  };
  subjects: { // This was subjects in AdminStats, might refer to tiku/question counts within subjects
    total_questions: number;
    total_files: number; // tiku files
  };
}

export interface AdminUser { // Extends User or has specific admin view fields
  id: number; // Overlaps with User.user_id
  username: string; // Overlaps
  is_enabled: boolean;
  created_at?: string;
  last_time_login?: string;
  model: UserModel; // Use existing UserModel
  invitation_code?: string;
}

export interface AdminInvitation {
  id: number;
  code: string;
  is_used: boolean;
  created_at?: string;
  expires_at?: string;
  used_by_username?: string;
}

export interface AdminSubjectFile { // Was SubjectFile in api.ts, renamed to avoid conflict
  subject: string; // Subject name
  filename: string; // Original Excel filename perhaps
  display_name: string; // Tiku name
  file_path: string; // Path on server
  question_count: number;
  file_size: number;
  modified_time?: string;
}

export interface AdminSubject { // Was Subject in api.ts
  subject_id: number;
  subject_name: string;
  exam_time?: string | null; // Matching backend which can be null
  created_at?: string;
  updated_at?: string;
  question_count?: number; // From some backend DTOs
  tiku_count?: number;    // From some backend DTOs
}

export interface TikuItem {
  tiku_id: number;
  subject_id: number;
  subject_name: string;
  tiku_name: string;
  tiku_position: string; // Unique key for the tiku file within its subject
  tiku_nums: number;     // Number of questions
  file_size?: number;
  file_hash?: string;
  is_active: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface AdminQuestionItem { // Was QuestionItem in api.ts
  id: string; // Question ID can be string (ObjectID from mongo) or number (if SQL)
              // Backend admin.py uses <int:question_id> in routes but create_question_and_update_tiku_count returns string id
              // connectDB.py uses question_id (string) and id (int, auto-increment primary key)
              // For consistency with practice.py Question.id (string), using string here.
  question_db_id?: number; // Actual database integer PK, if different from display/operational ID
  subject_id?: number; // Optional, as might be contextually known
  tiku_id: number;
  question_type: string; // Changed from number to string to match Question.type, map on backend/frontend
  stem: string;
  options?: Record<string, string>; // To match Question.options_for_practice
  option_a?: string; // Keep for direct mapping if needed, or transform to options
  option_b?: string;
  option_c?: string;
  option_d?: string;
  answer: string;
  explanation?: string;
  difficulty?: number; // 0-5 or similar scale
  status?: string; // e.g., 'active', 'inactive', 'draft' - specific values TBD
  created_at?: string;
  updated_at?: string;
  subject_name?: string; // Denormalized
  tiku_name?: string;    // Denormalized
  is_multiple_choice?: boolean; // To align with Question
}

export interface QuestionCreateData {
  tiku_id: number;
  question_type: string; // e.g., '单选题', '多选题', '判断题'
  stem: string;
  options?: Record<string, string>; // Use this for flexibility
  answer: string; // Correct answer key(s), e.g., "A" or "A,B"
  explanation?: string;
  difficulty?: number;
  status?: string;
  is_multiple_choice: boolean; // Derived from question_type or set explicitly
}

export interface QuestionUpdateData {
  question_type?: string;
  stem?: string;
  options?: Record<string, string>;
  answer?: string;
  explanation?: string;
  difficulty?: number;
  status?: string;
  is_multiple_choice?: boolean;
}


// Usage Statistics Types
export interface UsageSubjectStat {
  subject_id?: number; // Added for better linking
  subject_name: string;
  used_count: number;
  rank?: number;
  usage_percentage?: number;
}

export interface UsageTikuStat {
  tiku_id?: number; // Added for better linking
  tiku_name: string;
  subject_name: string; // Or subject_id
  used_count: number;
  tiku_position?: string; // From TikuItem
  rank?: number;
  usage_percentage?: number;
}

export interface UsageStats {
  subject_stats: UsageSubjectStat[];
  tiku_stats: UsageTikuStat[];
}

export interface UsageSummary {
  total_subject_usage: number;
  total_tiku_usage: number;
  active_subjects_count: number;
  active_tikues_count: number;
  most_popular_subject?: UsageSubjectStat;
  most_popular_tiku?: UsageTikuStat;
  total_subjects: number;
  total_tikues: number;
}

// This was defined in api.ts, seems specific, maybe for realtime dashboard?
export interface RealtimeUsageStats {
  pending_usage_count: number; // Unclear what this represents
  total_pending_usages: number;
  pending_stats: Array<{
    tiku_id: number;
    pending_count: number;
  }>;
}


// Potentially rename AuthResponse to ServiceResponse for global use
// export interface AuthResponse<T = any> { ... }
// could become:
export interface ServiceResponse<T = any> {
  success: boolean;
  message?: string;
  data?: T;
  error?: string; // Optional error field, usually populated by frontend services
}
// And update imports in auth.ts and other places using AuthResponse as BaseAuthResponse

// Existing types below...
// export type QuestionType = ...
// ... 