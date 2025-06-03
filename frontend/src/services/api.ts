import type {
  ApiError,
  CompletedResponse,
  Feedback,
  Question,
  QuestionResponse,
  SubjectsResponse,
  QuestionStatus
} from '@/types';
import { API_BASE_URL, enableApiLogging } from '@/config/api';
import { useAuthStore } from '@/stores/auth';
import router from '@/router';

// 使用配置文件中的API基地址
const API_BASE = API_BASE_URL;

// 管理员API相关类型定义
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
  };
  subjects: {
    total_questions: number;
    total_files: number;
  };
}

export interface AdminUser {
  id: number;
  username: string;
  is_enabled: boolean;
  created_at?: string;
  last_time_login?: string;
  model: number;
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

export interface SubjectFile {
  subject: string;
  filename: string;
  display_name: string;
  file_path: string;
  question_count: number;
  file_size: number;
  modified_time?: string;
}

export interface Pagination {
  page: number;
  per_page: number;
  total: number;
  total_pages: number;
  has_prev: boolean;
  has_next: boolean;
}

export interface UserSearchParams {
  search?: string;
  order_by?: string;
  order_dir?: 'asc' | 'desc';
  page?: number;
  per_page?: number;
}

export interface SearchParams {
  search?: string;
  order_by?: string;
  order_dir?: 'asc' | 'desc';
  page?: number;
  per_page?: number;
}

export interface Subject {
  subject_id: number;
  subject_name: string;
  exam_time?: string;
  created_at?: string;
  updated_at?: string;
}

export interface TikuItem {
  tiku_id: number;
  subject_id: number;
  subject_name: string;
  tiku_name: string;
  tiku_position: string;
  tiku_nums: number;
  file_size?: number;
  file_hash?: string;
  is_active: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface UsageSubjectStat {
  subject_name: string;
  used_count: number;
}

export interface UsageTikuStat {
  tiku_name: string;
  subject_name: string;
  used_count: number;
  tiku_position: string;
}

export interface UsageStats {
  subject_stats: UsageSubjectStat[];
  tiku_stats: UsageTikuStat[];
}

export interface ApiService {
  getFileOptions(): Promise<SubjectsResponse>;
  startPractice(tikuid: string, forceRestart?: boolean, shuffleQuestions?: boolean): Promise<{ message: string; success: boolean; resumed?: boolean }>;
  getCurrentQuestion(): Promise<QuestionResponse>;
  submitAnswer(answer: string, questionId: string, isRevealed: boolean, isSkipped: boolean): Promise<Feedback>;
  jumpToQuestion(index: number): Promise<{ message: string; success: boolean }>;
  getCompletedSummary(): Promise<CompletedResponse>;
  getQuestionAnalysis(questionId: string): Promise<{
    success: boolean;
    analysis?: string;
    knowledge_points?: string[];
    message?: string;
  }>;
  getQuestionHistory(questionIndex: number): Promise<{
    success: boolean;
    question?: Question;
    feedback?: Feedback;
    message?: string;
  }>;
  checkSessionStatus(): Promise<{
    has_session: boolean;
    message?: string;
    file_name?: string;
    file_info?: {
      display: string;
      current_question: number;
      total_questions: number;
    };
  }>;
  getQuestionStatuses(): Promise<{
    statuses: Array<QuestionStatus>;
    success: boolean;
  }>;
  saveSession(): Promise<{
    success: boolean;
    message?: string;
  }>;
  // 管理员API
  admin: {
    getStats(): Promise<{ success: boolean; stats?: AdminStats; message?: string }>;
    getUsers(params?: UserSearchParams): Promise<{ success: boolean; users?: AdminUser[]; pagination?: Pagination; message?: string }>;
    toggleUser(userId: number): Promise<{ success: boolean; is_enabled?: boolean; message?: string }>;
    updateUserModel(userId: number, model: number): Promise<{ success: boolean; model?: number; message?: string }>;
    getInvitations(params?: SearchParams): Promise<{ success: boolean; invitations?: AdminInvitation[]; pagination?: Pagination; message?: string }>;
    createInvitation(code?: string, expireDays?: number): Promise<{ success: boolean; invitation_code?: string; message?: string }>;
    getSubjectFiles(): Promise<{ success: boolean; files?: SubjectFile[]; message?: string }>;
    
    // 科目管理
    getSubjects(params?: SearchParams): Promise<{ success: boolean; subjects?: Subject[]; pagination?: Pagination; message?: string }>;
    createSubject(subjectName: string, examTime?: string): Promise<{ success: boolean; subject_id?: number; message?: string }>;
    updateSubject(subjectId: number, subjectName: string, examTime?: string): Promise<{ success: boolean; message?: string }>;
    deleteSubject(subjectId: number): Promise<{ success: boolean; message?: string }>;
    
    // 题库管理
    getTiku(subjectId?: number, params?: SearchParams): Promise<{ success: boolean; tiku_list?: TikuItem[]; pagination?: Pagination; message?: string }>;
    uploadTiku(file: File, subjectId: number, tikuName?: string): Promise<{ success: boolean; tiku_id?: number; question_count?: number; message?: string }>;
    deleteTiku(tikuId: number): Promise<{ success: boolean; message?: string }>;
    toggleTiku(tikuId: number): Promise<{ success: boolean; is_active?: boolean; message?: string }>;
    
    // 系统管理
    syncFilesystem(): Promise<{ success: boolean; message?: string }>; // 已弃用 - 可能导致数据不一致
    reloadBanks(): Promise<{ success: boolean; message?: string }>;
    
    // 使用统计
    getUsageStats(): Promise<{ success: boolean; subject_stats?: UsageSubjectStat[]; tiku_stats?: UsageTikuStat[]; message?: string }>;
    syncUsageStats(): Promise<{ success: boolean; message?: string }>;
  };
}

class ApiServiceImpl implements ApiService {
  // 清理错误信息，移除HTTP状态码前缀
  private cleanErrorMessage(errorMessage: string): string {
    if (!errorMessage) return 'An error occurred';
    
    // 移除HTTP状态码前缀 (如 "400 Bad Request: ", "401 Unauthorized: " 等)
    const httpStatusRegex = /^\d{3}\s+[^:]+:\s*/;
    return errorMessage.replace(httpStatusRegex, '').trim();
  }

  private async handleResponse<T>(response: Response): Promise<T> {
    if (!response.ok) {
      // 特殊处理401认证失败错误
      if (response.status === 401) {
        // 获取auth store并清除用户状态
        const authStore = useAuthStore();
        authStore.handleAuthFailure();
        
        // 重定向到登录页面
        if (router.currentRoute.value.name !== 'login') {
          router.push('/login');
        }
        
        throw new Error('登录已过期，请重新登录');
      }
      
      const error = await response.json() as ApiError;
      const cleanedMessage = this.cleanErrorMessage(error.message || 'An error occurred');
      throw new Error(cleanedMessage);
    }
    return response.json() as Promise<T>;
  }

  private async fetchWithCredentials(url: string, options: RequestInit = {}): Promise<Response> {
    const defaultOptions: RequestInit = {
      credentials: 'include' as RequestCredentials,
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'X-Requested-With': 'XMLHttpRequest',
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache'
      },
      mode: 'cors'
    };

    // 如果请求体是FormData，不设置Content-Type头让浏览器自动设置
    const isFormData = options.body instanceof FormData;
    
    const finalOptions: RequestInit = {
      ...defaultOptions,
      ...options,
      headers: isFormData 
        ? {
            // 对于FormData，只保留非Content-Type的头
            'Accept': 'application/json',
            'X-Requested-With': 'XMLHttpRequest',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
            ...(options.headers || {})
          }
        : {
            ...defaultOptions.headers,
            ...(options.headers || {})
          },
      credentials: 'include' as RequestCredentials
    };

    try {
      const response = await fetch(url, finalOptions);

      // Check for CORS issues
      if (!response.ok && response.status === 0) {
        throw new Error('CORS error - check browser console for details');
      }

      return response;
    } catch (error) {
      throw error;
    }
  }

  async getFileOptions(): Promise<SubjectsResponse> {
    const response = await this.fetchWithCredentials(`${API_BASE}/file_options`);
    return this.handleResponse<SubjectsResponse>(response);
  }

  async startPractice(tikuid: string, forceRestart?: boolean, shuffleQuestions?: boolean): Promise<{ message: string; success: boolean; resumed?: boolean }> {
    const response = await this.fetchWithCredentials(`${API_BASE}/start_practice`, {
      method: 'POST',
      body: JSON.stringify({ tikuid, force_restart: forceRestart, shuffle_questions: shuffleQuestions })
    });
    return this.handleResponse<{ message: string; success: boolean; resumed?: boolean }>(response);
  }

  async getCurrentQuestion(): Promise<QuestionResponse> {
    const response = await this.fetchWithCredentials(`${API_BASE}/practice/question`);
    return this.handleResponse<QuestionResponse>(response);
  }

  async submitAnswer(answer: string, questionId: string, isRevealed: boolean, isSkipped: boolean): Promise<Feedback> {
    const response = await this.fetchWithCredentials(`${API_BASE}/practice/submit`, {
      method: 'POST',
      body: JSON.stringify({
        answer,
        question_id: questionId,
        peeked: isRevealed,
        is_skipped: isSkipped
      })
    });
    return this.handleResponse<Feedback>(response);
  }

  async jumpToQuestion(index: number): Promise<{ message: string; success: boolean }> {
    const response = await this.fetchWithCredentials(`${API_BASE}/practice/jump?index=${index}`);
    return this.handleResponse<{ message: string; success: boolean }>(response);
  }

  async getCompletedSummary(): Promise<CompletedResponse> {
    const response = await this.fetchWithCredentials(`${API_BASE}/completed_summary`);
    return this.handleResponse<CompletedResponse>(response);
  }

  async getQuestionAnalysis(questionId: string): Promise<{
    success: boolean;
    analysis?: string;
    knowledge_points?: string[];
    message?: string;
  }> {
    const response = await this.fetchWithCredentials(`${API_BASE}/practice/question/${questionId}/analysis`);
    return this.handleResponse<{
      success: boolean;
      analysis?: string;
      knowledge_points?: string[];
      message?: string;
    }>(response);
  }

  async getQuestionHistory(questionIndex: number): Promise<{
    success: boolean;
    question?: Question;
    feedback?: Feedback;
    message?: string;
  }> {
    const response = await this.fetchWithCredentials(`${API_BASE}/practice/history/${questionIndex}`);
    return this.handleResponse<{
      success: boolean;
      question?: Question;
      feedback?: Feedback;
      message?: string;
    }>(response);
  }

  async checkSessionStatus(): Promise<{
    has_session: boolean;
    message?: string;
    file_name?: string;
    file_info?: {
      display: string;
      current_question: number;
      total_questions: number;
    };
  }> {
    const response = await this.fetchWithCredentials(`${API_BASE}/session/status`);
    return this.handleResponse<{
      has_session: boolean;
      message?: string;
      file_name?: string;
      file_info?: {
        display: string;
        current_question: number;
        total_questions: number;
      };
    }>(response);
  }

  async getQuestionStatuses(): Promise<{
    statuses: Array<QuestionStatus>;
    success: boolean;
  }> {
    const response = await this.fetchWithCredentials(`${API_BASE}/practice/statuses`);
    return this.handleResponse<{
      statuses: Array<QuestionStatus>;
      success: boolean;
    }>(response);
  }

  async saveSession(): Promise<{
    success: boolean;
    message?: string;
  }> {
    const response = await this.fetchWithCredentials(`${API_BASE}/session/save`);
    return this.handleResponse<{
      success: boolean;
      message?: string;
    }>(response);
  }

  // 管理员API
  admin = {
    getStats: async (): Promise<{ success: boolean; stats?: AdminStats; message?: string }> => {
      const response = await this.fetchWithCredentials(`${API_BASE}/admin/stats`);
      return this.handleResponse<{ success: boolean; stats?: AdminStats; message?: string }>(response);
    },

    getUsers: async (params?: UserSearchParams): Promise<{ success: boolean; users?: AdminUser[]; pagination?: Pagination; message?: string }> => {
      const queryParams = new URLSearchParams(params as any).toString();
      const response = await this.fetchWithCredentials(`${API_BASE}/admin/users?${queryParams}`);
      return this.handleResponse<{ success: boolean; users?: AdminUser[]; pagination?: Pagination; message?: string }>(response);
    },

    toggleUser: async (userId: number): Promise<{ success: boolean; is_enabled?: boolean; message?: string }> => {
      const response = await this.fetchWithCredentials(`${API_BASE}/admin/users/${userId}/toggle`, {
        method: 'POST'
      });
      return this.handleResponse<{ success: boolean; is_enabled?: boolean; message?: string }>(response);
    },

    updateUserModel: async (userId: number, model: number): Promise<{ success: boolean; model?: number; message?: string }> => {
      const response = await this.fetchWithCredentials(`${API_BASE}/admin/users/${userId}/model`, {
        method: 'PUT',
        body: JSON.stringify({ model })
      });
      return this.handleResponse<{ success: boolean; model?: number; message?: string }>(response);
    },

    getInvitations: async (params?: SearchParams): Promise<{ success: boolean; invitations?: AdminInvitation[]; pagination?: Pagination; message?: string }> => {
      const queryParams = new URLSearchParams(params as any).toString();
      const response = await this.fetchWithCredentials(`${API_BASE}/admin/invitations?${queryParams}`);
      return this.handleResponse<{ success: boolean; invitations?: AdminInvitation[]; pagination?: Pagination; message?: string }>(response);
    },

    createInvitation: async (code?: string, expireDays?: number): Promise<{ success: boolean; invitation_code?: string; message?: string }> => {
      const body: any = {};
      if (code) body.code = code;
      if (expireDays) body.expire_days = expireDays;

      const response = await this.fetchWithCredentials(`${API_BASE}/admin/invitations`, {
        method: 'POST',
        body: JSON.stringify(body)
      });
      return this.handleResponse<{ success: boolean; invitation_code?: string; message?: string }>(response);
    },

    getSubjectFiles: async (): Promise<{ success: boolean; files?: SubjectFile[]; message?: string }> => {
      const response = await this.fetchWithCredentials(`${API_BASE}/admin/subject-files`);
      return this.handleResponse<{ success: boolean; files?: SubjectFile[]; message?: string }>(response);
    },
    
    // 科目管理
    getSubjects: async (params?: SearchParams): Promise<{ success: boolean; subjects?: Subject[]; pagination?: Pagination; message?: string }> => {
      const queryParams = new URLSearchParams(params as any).toString();
      const response = await this.fetchWithCredentials(`${API_BASE}/admin/subjects?${queryParams}`);
      return this.handleResponse<{ success: boolean; subjects?: Subject[]; pagination?: Pagination; message?: string }>(response);
    },
    createSubject: async (subjectName: string, examTime?: string): Promise<{ success: boolean; subject_id?: number; message?: string }> => {
      const body: any = { subject_name: subjectName };
      if (examTime) body.exam_time = examTime;

      const response = await this.fetchWithCredentials(`${API_BASE}/admin/subjects`, {
        method: 'POST',
        body: JSON.stringify(body)
      });
      return this.handleResponse<{ success: boolean; subject_id?: number; message?: string }>(response);
    },
    updateSubject: async (subjectId: number, subjectName: string, examTime?: string): Promise<{ success: boolean; message?: string }> => {
      const body: any = { subject_name: subjectName };
      if (examTime) body.exam_time = examTime;

      const response = await this.fetchWithCredentials(`${API_BASE}/admin/subjects/${subjectId}`, {
        method: 'PUT',
        body: JSON.stringify(body)
      });
      return this.handleResponse<{ success: boolean; message?: string }>(response);
    },
    deleteSubject: async (subjectId: number): Promise<{ success: boolean; message?: string }> => {
      const response = await this.fetchWithCredentials(`${API_BASE}/admin/subjects/${subjectId}`, {
        method: 'DELETE'
      });
      return this.handleResponse<{ success: boolean; message?: string }>(response);
    },
    
    // 题库管理
    getTiku: async (subjectId?: number, params?: SearchParams): Promise<{ success: boolean; tiku_list?: TikuItem[]; pagination?: Pagination; message?: string }> => {
      const queryParams = new URLSearchParams(params as any).toString();
      const response = await this.fetchWithCredentials(`${API_BASE}/admin/tiku?subject_id=${subjectId || ''}&${queryParams}`);
      return this.handleResponse<{ success: boolean; tiku_list?: TikuItem[]; pagination?: Pagination; message?: string }>(response);
    },
    uploadTiku: async (file: File, subjectId: number, tikuName?: string): Promise<{ success: boolean; tiku_id?: number; question_count?: number; message?: string }> => {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('subject_id', subjectId.toString());
      if (tikuName) formData.append('tiku_name', tikuName);

      const response = await this.fetchWithCredentials(`${API_BASE}/admin/tiku/upload`, {
        method: 'POST',
        body: formData
      });
      return this.handleResponse<{ success: boolean; tiku_id?: number; question_count?: number; message?: string }>(response);
    },
    deleteTiku: async (tikuId: number): Promise<{ success: boolean; message?: string }> => {
      const response = await this.fetchWithCredentials(`${API_BASE}/admin/tiku/${tikuId}`, {
        method: 'DELETE'
      });
      return this.handleResponse<{ success: boolean; message?: string }>(response);
    },
    toggleTiku: async (tikuId: number): Promise<{ success: boolean; is_active?: boolean; message?: string }> => {
      const response = await this.fetchWithCredentials(`${API_BASE}/admin/tiku/${tikuId}/toggle`, {
        method: 'POST'
      });
      return this.handleResponse<{ success: boolean; is_active?: boolean; message?: string }>(response);
    },
    
    // 系统管理
    syncFilesystem: async (): Promise<{ success: boolean; message?: string }> => {
      const response = await this.fetchWithCredentials(`${API_BASE}/admin/sync-filesystem`, {
        method: 'POST'
      });
      return this.handleResponse<{ success: boolean; message?: string }>(response);
    },
    reloadBanks: async (): Promise<{ success: boolean; message?: string }> => {
      const response = await this.fetchWithCredentials(`${API_BASE}/admin/reload-banks`, {
        method: 'POST'
      });
      return this.handleResponse<{ success: boolean; message?: string }>(response);
    },
    
    // 使用统计
    getUsageStats: async (): Promise<{ success: boolean; subject_stats?: UsageSubjectStat[]; tiku_stats?: UsageTikuStat[]; message?: string }> => {
      const response = await this.fetchWithCredentials(`${API_BASE}/admin/usage-stats`);
      return this.handleResponse<{ success: boolean; subject_stats?: UsageSubjectStat[]; tiku_stats?: UsageTikuStat[]; message?: string }>(response);
    },
    syncUsageStats: async (): Promise<{ success: boolean; message?: string }> => {
      const response = await this.fetchWithCredentials(`${API_BASE}/admin/sync-usage`, {
        method: 'POST'
      });
      return this.handleResponse<{ success: boolean; message?: string }>(response);
    }
  };
}

export const apiService = new ApiServiceImpl();
