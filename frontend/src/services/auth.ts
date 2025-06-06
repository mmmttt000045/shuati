import { AUTH_API_BASE_URL } from '@/config/api';
import type { User, LoginSuccessPayload, SessionInfo, AuthCheckClientResponseData, ServiceResponse } from '@/types';

interface RegisterData {
  username: string;
  password: string;
  invitation_code: string;
}

interface LoginData {
  username: string;
  password: string;
}

class AuthService {
  private baseURL = AUTH_API_BASE_URL;

  // 清理错误信息，移除HTTP状态码前缀
  private cleanErrorMessage(errorMessage: string): string {
    if (!errorMessage) return '';
    
    // 移除HTTP状态码前缀 (如 "400 Bad Request: ", "401 Unauthorized: " 等)
    const httpStatusRegex = /^\d{3}\s+[^:]+:\s*/;
    return errorMessage.replace(httpStatusRegex, '').trim();
  }

  private async makeRequest(url: string, options: RequestInit = {}): Promise<Response> {
    const defaultOptions: RequestInit = {
      credentials: 'include' as RequestCredentials,
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      mode: 'cors'
    };

    const finalOptions: RequestInit = {
      ...defaultOptions,
      ...options,
      headers: {
        ...defaultOptions.headers,
        ...(options.headers || {})
      }
    };

    // 添加session_id到请求头
    const sessionId = this.getSessionId();
    if (sessionId) {
      (finalOptions.headers as Record<string, string>)['X-Session-ID'] = sessionId;
    }

    return fetch(url, finalOptions);
  }

  private getSessionId(): string | null {
    // 优先从cookie获取
    const cookies = document.cookie.split(';');
    for (const cookie of cookies) {
      const [name, value] = cookie.trim().split('=');
      if (name === 'session_id') {
        return value;
      }
    }
    
    // 从localStorage获取（如果有的话）
    try {
      return localStorage.getItem('session_id');
    } catch {
      return null;
    }
  }

  async register(data: RegisterData): Promise<ServiceResponse<null>> {
    try {
      const response = await this.makeRequest(`${this.baseURL}/register`, {
        method: 'POST',
        body: JSON.stringify(data),
      });

      const result = await response.json();
      
      if (!response.ok || !result.success) {
        const rawError = result.message || (result.error ? String(result.error) : '注册失败，请重试');
        return {
          success: false,
          message: this.cleanErrorMessage(rawError),
          error: this.cleanErrorMessage(rawError)
        };
      }
      
      return { success: true, message: result.message };
    } catch (error: any) {
      console.error('Register API error:', error);
      return {
        success: false,
        message: '网络请求失败，请检查网络连接',
        error: error.message || '网络请求失败'
      };
    }
  }

  async login(data: LoginData): Promise<ServiceResponse<LoginSuccessPayload>> {
    try {
      const response = await this.makeRequest(`${this.baseURL}/login`, {
        method: 'POST',
        body: JSON.stringify(data),
      });

      const result = await response.json();
      
      if (!response.ok || !result.success) {
        const rawError = result.message || (result.error ? String(result.error) : '登录失败，请重试');
        return {
          success: false,
          message: this.cleanErrorMessage(rawError),
          error: this.cleanErrorMessage(rawError),
        };
      }
      
      // 后端的create_response将data直接合并到顶层
      const loginData = {
        user: result.user,
        session: result.session
      };
      
      return { success: true, message: result.message, data: loginData };
    } catch (error: any) {
      console.error('Login API error:', error);
      return {
        success: false,
        message: '网络请求失败，请检查网络连接',
        error: error.message || '网络请求失败',
        data: undefined
      };
    }
  }

  async logout(): Promise<ServiceResponse<null>> {
    try {
      const response = await this.makeRequest(`${this.baseURL}/logout`, {
        method: 'POST',
      });
      const result = await response.json();
      if (!response.ok || !result.success) {
         const rawError = result.message || (result.error ? String(result.error) : '登出失败');
         return { success: false, message: this.cleanErrorMessage(rawError), error: this.cleanErrorMessage(rawError) };
      }
      return result;
    } catch (error: any) {
      console.error('Logout API error:', error);
      return {
        success: false,
        message: '网络请求失败',
        error: error.message || '网络请求失败'
      };
    }
  }

  async checkAuth(): Promise<ServiceResponse<AuthCheckClientResponseData>> {
    try {
      const response = await this.makeRequest(`${this.baseURL}/check`, {
        method: 'GET',
      });
      
      const result = await response.json();

      if (!response.ok || !result.success) {
        const rawError = result.message || (result.error ? String(result.error) : '状态检查失败');
        return { 
          success: false,
          message: this.cleanErrorMessage(rawError),
          error: this.cleanErrorMessage(rawError),
          data: { authenticated: false }
        };
      }
      
      // 后端的create_response将data直接合并到顶层，所以authenticated和user直接在result中
      const authData = {
        authenticated: result.authenticated || false,
        user: result.user || null
      };
      
      return { success: true, data: authData };
    } catch (error: any) {
      console.error('[AuthService] CheckAuth API error:', error);
      return {
        success: false,
        message: '网络请求失败',
        error: error.message || '网络请求失败',
        data: { authenticated: false }
      };
    }
  }

  async getUserInfo(): Promise<ServiceResponse<{ user: User }>> {
    try {
      const response = await this.makeRequest(`${this.baseURL}/user`, {
        method: 'GET',
      });
      const result = await response.json();
      if (!response.ok || !result.success) {
        const rawError = result.message || (result.error ? String(result.error) : '获取用户信息失败');
        return { success: false, message: this.cleanErrorMessage(rawError), error: this.cleanErrorMessage(rawError) };
      }
      
      // 后端的create_response将data直接合并到顶层
      return { success: true, data: { user: result.user } };
    } catch (error: any) {
      console.error('GetUserInfo API error:', error);
      return {
        success: false,
        message: '网络请求失败',
        error: error.message || '网络请求失败'
      };
    }
  }

  async getSessionStatus(): Promise<ServiceResponse<{ session: SessionInfo, message?: string }>> {
    try {
      const response = await this.makeRequest(`${this.baseURL}/session/status`, {
        method: 'GET',
      });
      const result = await response.json();
      if (!response.ok || !result.success) {
        const rawError = result.message || (result.error ? String(result.error) : '获取会话状态失败');
        return { success: false, message: this.cleanErrorMessage(rawError), error: this.cleanErrorMessage(rawError) };
      }
      
      // 后端的create_response将data直接合并到顶层
      return { 
        success: true, 
        data: { 
          session: result.session, 
          message: result.message 
        } 
      };
    } catch (error: any) {
      console.error('GetSessionStatus API error:', error);
      return {
        success: false,
        message: '网络请求失败',
        error: error.message || '网络请求失败'
      };
    }
  }

  async extendSession(): Promise<ServiceResponse<{ session: SessionInfo }>> {
    try {
      const response = await this.makeRequest(`${this.baseURL}/session/extend`, {
        method: 'POST',
      });
      const result = await response.json();
      if (!response.ok || !result.success) {
        const rawError = result.message || (result.error ? String(result.error) : '延长会话失败');
        return { success: false, message: this.cleanErrorMessage(rawError), error: this.cleanErrorMessage(rawError) };
      }
      
      // 后端的create_response将data直接合并到顶层
      return { success: true, data: { session: result.session } };
    } catch (error: any) {
      console.error('ExtendSession API error:', error);
      return {
        success: false,
        message: '网络请求失败',
        error: error.message || '网络请求失败'
      };
    }
  }

  async markWarningShown(): Promise<ServiceResponse<null>> {
    try {
      const response = await this.makeRequest(`${this.baseURL}/session/warning-shown`, {
        method: 'POST',
      });
      const result = await response.json();
      if (!response.ok || !result.success) {
        const rawError = result.message || (result.error ? String(result.error) : '标记警告失败');
        return { success: false, message: this.cleanErrorMessage(rawError), error: this.cleanErrorMessage(rawError) };
      }
      return result;
    } catch (error: any) {
      console.error('MarkWarningShown API error:', error);
      return {
        success: false,
        message: '网络请求失败',
        error: error.message || '网络请求失败'
      };
    }
  }
}

export const authService = new AuthService();
export type { RegisterData, LoginData }; 