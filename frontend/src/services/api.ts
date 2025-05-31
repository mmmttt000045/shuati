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

export interface ApiService {
  getFileOptions(): Promise<SubjectsResponse>;
  startPractice(subject: string, fileName: string, forceRestart?: boolean, shuffleQuestions?: boolean): Promise<{ message: string; success: boolean; resumed?: boolean }>;
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
    active: boolean;
    completed?: boolean;
    message?: string;
    file_info?: {
      key: string;
      display: string;
      subject: string;
    };
    progress?: {
      current: number;
      total: number;
      round: number;
    };
    statistics?: {
      initial_total: number;
      correct_first_try: number;
      wrong_count: number;
    };
    question_statuses?: Array<QuestionStatus>;
  }>;
  getQuestionStatuses(): Promise<{
    statuses: Array<QuestionStatus>;
    success: boolean;
  }>;
  saveSession(): Promise<{
    success: boolean;
    message?: string;
  }>;
}

class ApiServiceImpl implements ApiService {
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
      throw new Error(error.message || 'An error occurred');
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

    const finalOptions: RequestInit = {
      ...defaultOptions,
      ...options,
      headers: {
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

  async startPractice(subject: string, fileName: string, forceRestart?: boolean, shuffleQuestions?: boolean): Promise<{ message: string; success: boolean; resumed?: boolean }> {
    const response = await this.fetchWithCredentials(`${API_BASE}/start_practice`, {
      method: 'POST',
      body: JSON.stringify({ subject, fileName, force_restart: forceRestart, shuffle_questions: shuffleQuestions })
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

  async getQuestionAnalysis(questionId: string) {
    try {
      const response = await this.fetchWithCredentials(`${API_BASE}/questions/${questionId}/analysis`);
      return await response.json();
    } catch (error) {
      return {
        success: false,
        message: 'Failed to fetch question analysis'
      };
    }
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
    active: boolean;
    completed?: boolean;
    message?: string;
    file_info?: {
      key: string;
      display: string;
      subject: string;
    };
    progress?: {
      current: number;
      total: number;
      round: number;
    };
    statistics?: {
      initial_total: number;
      correct_first_try: number;
      wrong_count: number;
    };
    question_statuses?: Array<QuestionStatus>;
  }> {
    const response = await this.fetchWithCredentials(`${API_BASE}/session/status`);
    return this.handleResponse<{
      active: boolean;
      completed?: boolean;
      message?: string;
      file_info?: {
        key: string;
        display: string;
        subject: string;
      };
      progress?: {
        current: number;
        total: number;
        round: number;
      };
      statistics?: {
        initial_total: number;
        correct_first_try: number;
        wrong_count: number;
      };
      question_statuses?: Array<QuestionStatus>;
    }>(response);
  }

  async getQuestionStatuses(): Promise<{
    statuses: Array<QuestionStatus>;
    success: boolean;
  }> {
    try {
      const sessionStatus = await this.checkSessionStatus();
      return {
        statuses: sessionStatus.question_statuses || [],
        success: sessionStatus.active
      };
    } catch (error) {
      return {
        statuses: [],
        success: false
      };
    }
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
}

export const apiService = new ApiServiceImpl();
