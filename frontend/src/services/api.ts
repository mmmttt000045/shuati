import type {
  ApiError,
  CompletedResponse,
  Feedback,
  QuestionResponse,
  SubjectsResponse
} from '@/types';

const API_BASE = 'http://14.103.133.62:5051/api';

export interface ApiService {
  getFileOptions(): Promise<SubjectsResponse>;
  startPractice(subject: string, fileName: string): Promise<{ message: string; success: boolean }>;
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
}

class ApiServiceImpl implements ApiService {
  private async handleResponse<T>(response: Response): Promise<T> {
    if (!response.ok) {
      console.error('API Error:', {
        status: response.status,
        statusText: response.statusText,
        url: response.url
      });
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

    console.log('Making API request:', {
      url,
      method: finalOptions.method || 'GET',
      headers: finalOptions.headers,
      credentials: finalOptions.credentials,
      cookies: document.cookie
    });

    try {
      const response = await fetch(url, finalOptions);

      // Log response details including cookies
      const responseDetails = {
        status: response.status,
        statusText: response.statusText,
        headers: Object.fromEntries(response.headers.entries()),
        cookies: document.cookie
      };
      console.log('API response:', responseDetails);

      // Check for CORS issues
      if (!response.ok && response.status === 0) {
        console.error('CORS error detected');
        throw new Error('CORS error - check browser console for details');
      }

      // Check for session-related issues
      if (response.status === 400 && responseDetails.cookies === '') {
        console.warn('Session may be invalid - no cookies present');
      }

      return response;
    } catch (error) {
      console.error('API request failed:', error);
      throw error;
    }
  }

  async getFileOptions(): Promise<SubjectsResponse> {
    const response = await this.fetchWithCredentials(`${API_BASE}/file_options`);
    return this.handleResponse<SubjectsResponse>(response);
  }

  async startPractice(subject: string, fileName: string): Promise<{ message: string; success: boolean }> {
    console.log('Starting practice:', { subject, fileName });
    const response = await this.fetchWithCredentials(`${API_BASE}/start_practice`, {
      method: 'POST',
      body: JSON.stringify({ subject, fileName })
    });
    const result = await this.handleResponse<{ message: string; success: boolean }>(response);
    console.log('Practice start result:', result);
    return result;
  }

  async getCurrentQuestion(): Promise<QuestionResponse> {
    console.log('Fetching current question');
    const response = await this.fetchWithCredentials(`${API_BASE}/practice/question`);
    const result = await this.handleResponse<QuestionResponse>(response);
    console.log('Current question result:', result);
    return result;
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
      console.error('Error fetching question analysis:', error);
      return {
        success: false,
        message: 'Failed to fetch question analysis'
      };
    }
  }
}

export const apiService = new ApiServiceImpl();
