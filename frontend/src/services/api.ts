import type {
  CompletedResponse,
  Feedback,
  Question,
  QuestionResponse,
  SubjectsResponse,
  QuestionStatus,
  ServiceResponse,
  Pagination,
  SearchParams,
  AdminStats,
  AdminUser,
  AdminInvitation,
  AdminSubjectFile,
  AdminSubject,
  TikuItem,
  AdminQuestionItem,
  QuestionCreateData,
  QuestionUpdateData,
  UsageSubjectStat,
  UsageTikuStat,
  UsageStats,
  UsageSummary,
  RealtimeUsageStats,
  ApiError
} from '@/types';
import { API_BASE_URL, enableApiLogging } from '@/config/api';
import { useAuthStore } from '@/stores/auth';
import router from '@/router';

// Re-export types for component imports
export type {
  AdminInvitation,
  TikuItem,
  QuestionCreateData,
  QuestionUpdateData,
  AdminSubject as Subject, // Alias for compatibility
  AdminQuestionItem as QuestionItem, // Alias for compatibility
  UsageSummary,
  UsageSubjectStat,
  UsageTikuStat,
  UsageStats
} from '@/types';

// 使用配置文件中的API基地址
const API_BASE = API_BASE_URL;

// All local interface definitions for AdminStats, AdminUser, AdminInvitation, SubjectFile (now AdminSubjectFile),
// Pagination, UserSearchParams (check if same as SearchParams or distinct), Subject (now AdminSubject),
// TikuItem, QuestionItem (now AdminQuestionItem), QuestionCreateData, QuestionUpdateData, 
// UsageSubjectStat, UsageTikuStat, UsageStats, UsageSummary, RealtimeUsageStats
// ... should be REMOVED from here as they are now in types/index.ts

// The ApiService interface will be updated next to use ServiceResponse<T>
export interface ApiService {
  getFileOptions(): Promise<ServiceResponse<SubjectsResponse>>;
  startPractice(tikuid: string, forceRestart?: boolean, shuffleQuestions?: boolean, selectedTypes?: string[]): Promise<ServiceResponse<{ resumed?: boolean }>>;
  getCurrentQuestion(): Promise<ServiceResponse<QuestionResponse>>;
  submitAnswer(answer: string, questionId: string, isRevealed: boolean, isSkipped: boolean): Promise<ServiceResponse<Feedback>>;
  jumpToQuestion(index: number): Promise<ServiceResponse<null>>;
  getCompletedSummary(): Promise<ServiceResponse<CompletedResponse>>;
  getQuestionAnalysis(questionId: string): Promise<ServiceResponse<{
    analysis?: string;
    knowledge_points?: string[];
  }>>;
  getQuestionHistory(questionIndex: number): Promise<ServiceResponse<{
    question?: Question;
    feedback?: Feedback;
  }>>;
  checkSessionStatus(): Promise<ServiceResponse<{
    has_session: boolean;
    message?: string;
    file_name?: string;
    file_info?: {
      display: string;
      current_question: number;
      total_questions: number;
      round_number?: number;
    };
  }>>;
  getQuestionStatuses(): Promise<ServiceResponse<{ statuses: Array<QuestionStatus> }>>;
  saveSession(): Promise<ServiceResponse<null>>;

  // Profile API
  profile: {
    getUserProfile(): Promise<ServiceResponse<{
      user: {
        id: number;
        username: string;
        email?: string;
        student_id?: string;
        major?: string;
        grade?: number;
        is_enabled: boolean;
        created_at?: string;
        last_time_login?: string;
        model: number;
      };
    }>>;
    updateUserProfile(data: {
      username?: string;
      email?: string;
      student_id?: string;
      major?: string;
      grade?: number;
    }): Promise<ServiceResponse<null>>;
    changePassword(data: {
      currentPassword: string;
      newPassword: string;
      confirmPassword: string;
    }): Promise<ServiceResponse<null>>;
  };

  // 管理员API
  admin: {
    getStats(): Promise<ServiceResponse<{ stats: AdminStats }>>;
    getUsers(params?: SearchParams): Promise<ServiceResponse<{ users: AdminUser[]; pagination: Pagination }>>;
    toggleUser(userId: number): Promise<ServiceResponse<{ is_enabled?: boolean }>>;
    updateUserModel(userId: number, model: number): Promise<ServiceResponse<{ model?: number }>>;
    resetUserPassword(userId: number, newPassword: string): Promise<ServiceResponse<{ user_id?: number; username?: string }>>;
    getInvitations(params?: SearchParams): Promise<ServiceResponse<{ invitations: AdminInvitation[]; pagination?: Pagination }>>;
    createInvitation(code?: string, expireDays?: number): Promise<ServiceResponse<{ invitation_code?: string }>>;
    deleteInvitation(invitationId: number): Promise<ServiceResponse<null>>;
    getSubjects(params?: SearchParams): Promise<ServiceResponse<{ subjects: AdminSubject[]; pagination: Pagination }>>;
    createSubject(subjectName: string, examTime?: string): Promise<ServiceResponse<{ subject_id: number }>>;
    updateSubject(subjectId: number, subjectName: string, examTime?: string): Promise<ServiceResponse<null>>;
    deleteSubject(subjectId: number): Promise<ServiceResponse<null>>;
    getTiku(subjectId?: number, params?: SearchParams): Promise<ServiceResponse<{ tiku_list: TikuItem[]; pagination?: Pagination }>>;
    uploadTiku(file: File, subjectId: number, tikuName?: string): Promise<ServiceResponse<{ tiku_id?: number; question_count?: number }>>;
    deleteTiku(tikuId: number): Promise<ServiceResponse<null>>;
    toggleTiku(tikuId: number): Promise<ServiceResponse<{ is_active?: boolean }>>;
    getQuestions(tikuId?: number, params?: SearchParams): Promise<ServiceResponse<{ questions: AdminQuestionItem[]; pagination: Pagination }>>;
    getQuestionDetail(questionId: string | number): Promise<ServiceResponse<{ question: AdminQuestionItem }>>;
    createQuestion(data: QuestionCreateData): Promise<ServiceResponse<{ question_id: string | number }>>;
    updateQuestion(questionId: string | number, data: QuestionUpdateData): Promise<ServiceResponse<null>>;
    deleteQuestion(questionId: string | number): Promise<ServiceResponse<null>>;
    toggleQuestionStatus(questionId: string | number): Promise<ServiceResponse<{ status?: string }>>;
    reloadBanks(): Promise<ServiceResponse<null>>;
  };
  
  // 新的usage统计API
  usage: {
    getUsageStats(): Promise<ServiceResponse<UsageStats>>;
    getUsageSummary(): Promise<ServiceResponse<UsageSummary>>;
    getTopSubjects(limit?: number): Promise<ServiceResponse<{ top_subjects: UsageSubjectStat[]; total_subjects: number; limit: number }>>;
    getTopTikues(limit?: number): Promise<ServiceResponse<{ top_tikues: UsageTikuStat[]; total_tikues: number; limit: number }>>;
  };
}

class ApiServiceImpl implements ApiService {
  private cleanErrorMessage(errorMessage: string): string {
    if (!errorMessage) return '';
    const httpStatusRegex = /^\d{3}\s+[^:]+:\s*/;
    return errorMessage.replace(httpStatusRegex, '').trim();
  }

  private async fetchWithCredentials(url: string, options: RequestInit = {}): Promise<Response> {
    const defaultOptions: RequestInit = {
      credentials: 'include' as RequestCredentials,
      headers: {
        'Accept': 'application/json',
      },
      mode: 'cors'
    };

    const finalOptions: RequestInit = {
      ...defaultOptions,
      ...options,
      headers: {
        ...defaultOptions.headers,
        ...(options.headers || {}),
      }
    };

    const method = (options.method || 'GET').toUpperCase();
    if (method !== 'GET' && method !== 'HEAD' && !(options.body instanceof FormData)) {
      (finalOptions.headers as Record<string, string>)['Content-Type'] = 'application/json';
    }
    if (options.body instanceof FormData) {
      delete (finalOptions.headers as Record<string, string>)['Content-Type'];
    }



    try {
      const response = await fetch(url, finalOptions);
      return response;
    } catch (networkError: any) {
      console.error('[API Network Error]:', url, networkError);
      const errorResponsePayload = {
        success: false,
        message: '网络连接失败，请检查您的网络设置。',
        error: networkError.message || 'Network connection failed',
        data: undefined
      };
      return new Response(JSON.stringify(errorResponsePayload), {
        status: 503,
        statusText: 'Network Error',
        headers: { 'Content-Type': 'application/json' }
      });
    }
  }

  private async handleResponse<T>(response: Response): Promise<ServiceResponse<T>> {
    let responseText = '';
    try {
      responseText = await response.text();
    } catch (textError: any) {
      console.error('API response .text() error:', response.url, textError);
      return {
        success: false,
        message: this.cleanErrorMessage(`读取响应失败: ${response.statusText || '未知服务器错误'}`),
        error: textError.message || 'Failed to read response text',
      };
    }

    let parsedResult: any;
    try {
      parsedResult = JSON.parse(responseText);
    } catch (e: any) {
      console.error('API response JSON parsing error:', response.url, responseText, e);
      const message = response.ok ? '服务器响应格式错误' : `服务器错误: ${response.status}`;
      const errorDetail = response.ok ? `无法解析服务器响应。内容: ${responseText.substring(0, 100)}` : `${response.statusText || 'Unknown server error'}`;
      return {
        success: false,
        message: this.cleanErrorMessage(message),
        error: this.cleanErrorMessage(errorDetail),
      };
    }

    
    if (response.status === 401) {
      const authStore = useAuthStore();
      if (router.currentRoute.value.name !== 'Login') {
        await authStore.logout(); 
        router.push('/login').catch(err => console.error("Router push to login failed:", err));
      }
      return {
        success: false,
        message: '会话已过期或未授权，请重新登录。',
        error: 'Unauthorized'
      };
    }

    if (parsedResult.success === false) {
        const errorMessage = parsedResult.message || (response.ok ? '服务器报告操作失败' : response.statusText);
        return {
            success: false,
            message: this.cleanErrorMessage(String(errorMessage)),
            error: this.cleanErrorMessage(String(parsedResult.error || errorMessage)),
            data: parsedResult.data
        };
    }

    if (!response.ok) {
        const errorMessage = parsedResult.message || response.statusText || '未知服务器错误';
        return {
            success: false,
            message: this.cleanErrorMessage(String(errorMessage)),
            error: this.cleanErrorMessage(String(parsedResult.error || errorMessage)),
            data: parsedResult.data
        };
    }
    
    return {
      success: true,
      message: parsedResult.message, 
      data: parsedResult.data !== undefined ? parsedResult.data as T : parsedResult as T,
      error: undefined
    };
  }

  async getFileOptions(): Promise<ServiceResponse<SubjectsResponse>> {
    const response = await this.fetchWithCredentials(`${API_BASE}/file_options`);
    return this.handleResponse<SubjectsResponse>(response);
  }

  async startPractice(tikuid: string, forceRestart?: boolean, shuffleQuestions?: boolean, selectedTypes?: string[]): Promise<ServiceResponse<{ resumed?: boolean }>> {
    const body: any = { 
      tikuid, 
      force_restart: forceRestart, 
      shuffle_questions: shuffleQuestions 
    };
    
    if (selectedTypes && selectedTypes.length > 0) {
      body.selected_types = selectedTypes;
    }
    
    const response = await this.fetchWithCredentials(`${API_BASE}/start_practice`, {
      method: 'POST',
      body: JSON.stringify(body)
    });
    return this.handleResponse<{ resumed?: boolean }>(response);
  }

  async getCurrentQuestion(): Promise<ServiceResponse<QuestionResponse>> {
    const response = await this.fetchWithCredentials(`${API_BASE}/practice/question`);
    return this.handleResponse<QuestionResponse>(response);
  }

  async submitAnswer(answer: string, questionId: string, isRevealed: boolean, isSkipped: boolean): Promise<ServiceResponse<Feedback>> {
    const response = await this.fetchWithCredentials(`${API_BASE}/practice/submit`, {
      method: 'POST',
      body: JSON.stringify({ 
        answer, 
        question_id: questionId,
        is_revealed: isRevealed,
        is_skipped: isSkipped,
      }),
    });
    return this.handleResponse<Feedback>(response);
  }

  async jumpToQuestion(index: number): Promise<ServiceResponse<null>> {
    const response = await this.fetchWithCredentials(`${API_BASE}/practice/jump?index=${index}`, {
      method: 'GET'
    });
    return this.handleResponse<null>(response);
  }

  async getCompletedSummary(): Promise<ServiceResponse<CompletedResponse>> {
    const response = await this.fetchWithCredentials(`${API_BASE}/completed_summary`);
    return this.handleResponse<CompletedResponse>(response);
  }

  async getQuestionAnalysis(questionId: string): Promise<ServiceResponse<{
    analysis?: string;
    knowledge_points?: string[];
  }>> {
    const response = await this.fetchWithCredentials(`${API_BASE}/practice/question/${questionId}/analysis`);
    return this.handleResponse<{
      analysis?: string;
      knowledge_points?: string[];
    }>(response);
  }

  async getQuestionHistory(questionIndex: number): Promise<ServiceResponse<{
    question?: Question;
    feedback?: Feedback;
  }>> {
    const response = await this.fetchWithCredentials(`${API_BASE}/practice/history/${questionIndex}`);
    return this.handleResponse<{
      question?: Question;
      feedback?: Feedback;
    }>(response);
  }

  async checkSessionStatus(): Promise<ServiceResponse<{
    has_session: boolean;
    message?: string;
    file_name?: string;
    file_info?: {
      display: string;
      current_question: number;
      total_questions: number;
      round_number?: number;
    };
  }>> {
    const response = await this.fetchWithCredentials(`${API_BASE}/session/status`);
    return this.handleResponse<{
      has_session: boolean;
      message?: string;
      file_name?: string;
      file_info?: {
        display: string;
        current_question: number;
        total_questions: number;
        round_number?: number;
      };
    }>(response);
  }

  async getQuestionStatuses(): Promise<ServiceResponse<{ statuses: Array<QuestionStatus> }>> {
    const response = await this.fetchWithCredentials(`${API_BASE}/practice/statuses`);
    return this.handleResponse<{ statuses: Array<QuestionStatus> }>(response);
  }

  async saveSession(): Promise<ServiceResponse<null>> {
    const response = await this.fetchWithCredentials(`${API_BASE}/session/save`, { method: 'GET' });
    return this.handleResponse<null>(response);
  }

  // Profile API
  profile = {
    getUserProfile: async (): Promise<ServiceResponse<{
      user: {
        id: number;
        username: string;
        email?: string;
        student_id?: string;
        major?: string;
        grade?: number;
        is_enabled: boolean;
        created_at?: string;
        last_time_login?: string;
        model: number;
      };
    }>> => {
      const response = await this.fetchWithCredentials(`${API_BASE}/profile/info`);
      return this.handleResponse<{
        user: {
          id: number;
          username: string;
          email?: string;
          student_id?: string;
          major?: string;
          grade?: number;
          is_enabled: boolean;
          created_at?: string;
          last_time_login?: string;
          model: number;
        };
      }>(response);
    },
    updateUserProfile: async (data: {
      username?: string;
      email?: string;
      student_id?: string;
      major?: string;
      grade?: number;
    }): Promise<ServiceResponse<null>> => {
      const response = await this.fetchWithCredentials(`${API_BASE}/profile/info`, {
        method: 'PUT',
        body: JSON.stringify(data),
      });
      return this.handleResponse<null>(response);
    },
    changePassword: async (data: {
      currentPassword: string;
      newPassword: string;
      confirmPassword: string;
    }): Promise<ServiceResponse<null>> => {
      const response = await this.fetchWithCredentials(`${API_BASE}/profile/password`, {
        method: 'PUT',
        body: JSON.stringify(data),
      });
      return this.handleResponse<null>(response);
    },
  };

  // 管理员API
  admin = {
    getStats: async (): Promise<ServiceResponse<{ stats: AdminStats }>> => {
      const response = await (this as ApiServiceImpl).fetchWithCredentials(`${API_BASE}/admin/stats`);
      return (this as ApiServiceImpl).handleResponse<{ stats: AdminStats }>(response);
    },

    getUsers: async (params?: SearchParams): Promise<ServiceResponse<{ users: AdminUser[]; pagination: Pagination }>> => {
      const query = params ? new URLSearchParams(params as any).toString() : '';
      const response = await (this as ApiServiceImpl).fetchWithCredentials(`${API_BASE}/admin/users?${query}`);
      return (this as ApiServiceImpl).handleResponse<{ users: AdminUser[]; pagination: Pagination }>(response);
    },

    toggleUser: async (userId: number): Promise<ServiceResponse<{ is_enabled?: boolean }>> => {
      const response = await (this as ApiServiceImpl).fetchWithCredentials(`${API_BASE}/admin/users/${userId}/toggle`, { method: 'POST' });
      return (this as ApiServiceImpl).handleResponse<{ is_enabled?: boolean }>(response);
    },

    updateUserModel: async (userId: number, model: number): Promise<ServiceResponse<{ model?: number }>> => {
      const response = await (this as ApiServiceImpl).fetchWithCredentials(`${API_BASE}/admin/users/${userId}/model`, { 
        method: 'PUT',
        body: JSON.stringify({ model }),
      });
      return (this as ApiServiceImpl).handleResponse<{ model?: number }>(response);
    },

    resetUserPassword: async (userId: number, newPassword: string): Promise<ServiceResponse<{ user_id?: number; username?: string }>> => {
      const response = await (this as ApiServiceImpl).fetchWithCredentials(`${API_BASE}/admin/users/${userId}/reset-password`, { 
        method: 'POST',
        body: JSON.stringify({ new_password: newPassword }),
      });
      return (this as ApiServiceImpl).handleResponse<{ user_id?: number; username?: string }>(response);
    },

    getInvitations: async (params?: SearchParams): Promise<ServiceResponse<{ invitations: AdminInvitation[]; pagination?: Pagination }>> => {
      const query = params ? new URLSearchParams(params as any).toString() : '';
      const response = await (this as ApiServiceImpl).fetchWithCredentials(`${API_BASE}/admin/invitations?${query}`);
      return (this as ApiServiceImpl).handleResponse<{ invitations: AdminInvitation[]; pagination?: Pagination }>(response);
    },

    createInvitation: async (code?: string, expireDays?: number): Promise<ServiceResponse<{ invitation_code?: string }>> => {
      const body: any = {};
      if (code) body.code = code;
      if (expireDays) body.expire_days = expireDays;
      const response = await (this as ApiServiceImpl).fetchWithCredentials(`${API_BASE}/admin/invitations`, { 
        method: 'POST',
        body: JSON.stringify(body),
      });
      return (this as ApiServiceImpl).handleResponse<{ invitation_code?: string }>(response);
    },

    deleteInvitation: async (invitationId: number): Promise<ServiceResponse<null>> => {
      const response = await (this as ApiServiceImpl).fetchWithCredentials(`${API_BASE}/admin/invitations/${invitationId}`, { method: 'DELETE' });
      return (this as ApiServiceImpl).handleResponse<null>(response);
    },

    getSubjects: async (params?: SearchParams): Promise<ServiceResponse<{ subjects: AdminSubject[]; pagination: Pagination }>> => {
      const query = params ? new URLSearchParams(params as any).toString() : '';
      const response = await (this as ApiServiceImpl).fetchWithCredentials(`${API_BASE}/admin/subjects?${query}`);
      return (this as ApiServiceImpl).handleResponse<{ subjects: AdminSubject[]; pagination: Pagination }>(response);
    },
    createSubject: async (subjectName: string, examTime?: string): Promise<ServiceResponse<{ subject_id: number }>> => {
      const response = await (this as ApiServiceImpl).fetchWithCredentials(`${API_BASE}/admin/subjects`, {
        method: 'POST',
        body: JSON.stringify({ subject_name: subjectName, exam_time: examTime }),
      });
      return (this as ApiServiceImpl).handleResponse<{ subject_id: number }>(response);
    },
    updateSubject: async (subjectId: number, subjectName: string, examTime?: string): Promise<ServiceResponse<null>> => {
      const response = await (this as ApiServiceImpl).fetchWithCredentials(`${API_BASE}/admin/subjects/${subjectId}`, {
        method: 'PUT',
        body: JSON.stringify({ subject_name: subjectName, exam_time: examTime }),
      });
      return (this as ApiServiceImpl).handleResponse<null>(response);
    },
    deleteSubject: async (subjectId: number): Promise<ServiceResponse<null>> => {
      const response = await (this as ApiServiceImpl).fetchWithCredentials(`${API_BASE}/admin/subjects/${subjectId}`, { method: 'DELETE' });
      return (this as ApiServiceImpl).handleResponse<null>(response);
    },
    
    // 题库管理
    getTiku: async (subjectId?: number, params?: SearchParams): Promise<ServiceResponse<{ tiku_list: TikuItem[]; pagination?: Pagination }>> => {
      let url = `${API_BASE}/admin/tiku`;
      const queryParams = new URLSearchParams(params as any);
      if (subjectId) {
        queryParams.append('subject_id', subjectId.toString());
      }
      const query = queryParams.toString();
      if (query) {
        url += `?${query}`;
      }
      const response = await (this as ApiServiceImpl).fetchWithCredentials(url);
      return (this as ApiServiceImpl).handleResponse<{ tiku_list: TikuItem[]; pagination?: Pagination }>(response);
    },
    uploadTiku: async (file: File, subjectId: number, tikuName?: string): Promise<ServiceResponse<{ tiku_id?: number; question_count?: number }>> => {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('subject_id', subjectId.toString());
      if (tikuName) {
        formData.append('tiku_name', tikuName);
      }
      const response = await (this as ApiServiceImpl).fetchWithCredentials(`${API_BASE}/admin/tiku/upload`, {
        method: 'POST',
        body: formData,
      });
      return (this as ApiServiceImpl).handleResponse<{ tiku_id?: number; question_count?: number }>(response);
    },
    deleteTiku: async (tikuId: number): Promise<ServiceResponse<null>> => {
      const response = await (this as ApiServiceImpl).fetchWithCredentials(`${API_BASE}/admin/tiku/${tikuId}`, { method: 'DELETE' });
      return (this as ApiServiceImpl).handleResponse<null>(response);
    },
    toggleTiku: async (tikuId: number): Promise<ServiceResponse<{ is_active?: boolean }>> => {
      const response = await (this as ApiServiceImpl).fetchWithCredentials(`${API_BASE}/admin/tiku/${tikuId}/toggle`, { method: 'POST' });
      return (this as ApiServiceImpl).handleResponse<{ is_active?: boolean }>(response);
    },
    
    // 题目管理
    getQuestions: async (tikuId?: number, params?: SearchParams): Promise<ServiceResponse<{ questions: AdminQuestionItem[]; pagination: Pagination }>> => {
      let url = `${API_BASE}/admin/questions`;
      const queryParams = new URLSearchParams(params as any);
      if (tikuId) {
        queryParams.append('tiku_id', tikuId.toString());
      }
      const query = queryParams.toString();
      if (query) {
        url += `?${query}`;
      }
      const response = await (this as ApiServiceImpl).fetchWithCredentials(url);
      return (this as ApiServiceImpl).handleResponse<{ questions: AdminQuestionItem[]; pagination: Pagination }>(response);
    },
    getQuestionDetail: async (questionId: string | number): Promise<ServiceResponse<{ question: AdminQuestionItem }>> => {
      const response = await (this as ApiServiceImpl).fetchWithCredentials(`${API_BASE}/admin/questions/${questionId}`);
      return (this as ApiServiceImpl).handleResponse<{ question: AdminQuestionItem }>(response);
    },
    createQuestion: async (data: QuestionCreateData): Promise<ServiceResponse<{ question_id: string | number }>> => {
      const response = await (this as ApiServiceImpl).fetchWithCredentials(`${API_BASE}/admin/questions`, {
        method: 'POST',
        body: JSON.stringify(data),
      });
      return (this as ApiServiceImpl).handleResponse<{ question_id: string | number }>(response);
    },
    updateQuestion: async (questionId: string | number, data: QuestionUpdateData): Promise<ServiceResponse<null>> => {
      const response = await (this as ApiServiceImpl).fetchWithCredentials(`${API_BASE}/admin/questions/${questionId}`, {
        method: 'PUT',
        body: JSON.stringify(data),
      });
      return (this as ApiServiceImpl).handleResponse<null>(response);
    },
    deleteQuestion: async (questionId: string | number): Promise<ServiceResponse<null>> => {
      const response = await (this as ApiServiceImpl).fetchWithCredentials(`${API_BASE}/admin/questions/${questionId}`, { method: 'DELETE' });
      return (this as ApiServiceImpl).handleResponse<null>(response);
    },
    toggleQuestionStatus: async (questionId: string | number): Promise<ServiceResponse<{ status?: string }>> => {
      const response = await (this as ApiServiceImpl).fetchWithCredentials(`${API_BASE}/admin/questions/${questionId}/toggle`, { method: 'POST' });
      return (this as ApiServiceImpl).handleResponse<{ status?: string }>(response);
    },
    
    // 系统管理
    reloadBanks: async (): Promise<ServiceResponse<null>> => {
      const response = await (this as ApiServiceImpl).fetchWithCredentials(`${API_BASE}/admin/reload-banks`, { method: 'POST' });
      return (this as ApiServiceImpl).handleResponse<null>(response);
    }
  };
  
  // 新的usage统计API
  usage = {
    getUsageStats: async (): Promise<ServiceResponse<UsageStats>> => {
      const response = await (this as ApiServiceImpl).fetchWithCredentials(`${API_BASE}/usage-stats`);
      return (this as ApiServiceImpl).handleResponse<UsageStats>(response);
    },
    getUsageSummary: async (): Promise<ServiceResponse<UsageSummary>> => {
      const response = await (this as ApiServiceImpl).fetchWithCredentials(`${API_BASE}/usage-stats/summary`);
      return (this as ApiServiceImpl).handleResponse<UsageSummary>(response);
    },
    getTopSubjects: async (limit?: number): Promise<ServiceResponse<{ top_subjects: UsageSubjectStat[]; total_subjects: number; limit: number }>> => {
      const query = limit ? `?limit=${limit}` : '';
      const response = await (this as ApiServiceImpl).fetchWithCredentials(`${API_BASE}/usage-stats/top-subjects${query}`);
      return (this as ApiServiceImpl).handleResponse<{ top_subjects: UsageSubjectStat[]; total_subjects: number; limit: number }>(response);
    },
    getTopTikues: async (limit?: number): Promise<ServiceResponse<{ top_tikues: UsageTikuStat[]; total_tikues: number; limit: number }>> => {
      const query = limit ? `?limit=${limit}` : '';
      const response = await (this as ApiServiceImpl).fetchWithCredentials(`${API_BASE}/usage-stats/top-tikues${query}`);
      return (this as ApiServiceImpl).handleResponse<{ top_tikues: UsageTikuStat[]; total_tikues: number; limit: number }>(response);
    }
  };
}

export const apiService: ApiService = new ApiServiceImpl();