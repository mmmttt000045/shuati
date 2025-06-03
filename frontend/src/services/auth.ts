import { AUTH_API_BASE_URL } from '@/config/api';
import type { User, AuthResponse as BaseAuthResponse } from '@/types';

interface AuthResponse extends BaseAuthResponse {
  error?: string;
}

interface RegisterData {
  username: string;
  password: string;
  invitation_code: string;
}

interface LoginData {
  username: string;
  password: string;
}

interface AuthCheckResponse {
  success: boolean;
  authenticated: boolean;
  user?: User;
  error?: string;
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

    return fetch(url, finalOptions);
  }

  async register(data: RegisterData): Promise<AuthResponse> {
    try {
      const response = await this.makeRequest(`${this.baseURL}/register`, {
        method: 'POST',
        body: JSON.stringify(data),
      });

      const result = await response.json();
      
      if (!response.ok || !result.success) {
        const rawError = result.message || result.error || '注册失败，请重试';
        return {
          success: false,
          error: this.cleanErrorMessage(rawError)
        };
      }
      
      return result;
    } catch (error) {
      return {
        success: false,
        error: '网络请求失败，请检查网络连接'
      };
    }
  }

  async login(data: LoginData): Promise<AuthResponse> {
    try {
      const response = await this.makeRequest(`${this.baseURL}/login`, {
        method: 'POST',
        body: JSON.stringify(data),
      });

      const result = await response.json();
      
      if (!response.ok || !result.success) {
        const rawError = result.message || result.error || '登录失败，请重试';
        return {
          success: false,
          error: this.cleanErrorMessage(rawError)
        };
      }
      
      return result;
    } catch (error) {
      return {
        success: false,
        error: '网络请求失败，请检查网络连接'
      };
    }
  }

  async logout(): Promise<AuthResponse> {
    try {
      const response = await this.makeRequest(`${this.baseURL}/logout`, {
        method: 'POST',
      });

      return await response.json();
    } catch (error) {
      return {
        success: false,
        error: '网络请求失败'
      };
    }
  }

  async checkAuth(): Promise<AuthCheckResponse> {
    try {
      const response = await this.makeRequest(`${this.baseURL}/check`, {
        method: 'GET',
      });

      return await response.json();
    } catch (error) {
      return {
        success: false,
        authenticated: false,
        error: '网络请求失败'
      };
    }
  }

  async getUserInfo(): Promise<AuthResponse> {
    try {
      const response = await this.makeRequest(`${this.baseURL}/user`, {
        method: 'GET',
      });

      return await response.json();
    } catch (error) {
      return {
        success: false,
        error: '网络请求失败'
      };
    }
  }
}

export const authService = new AuthService();
export type { AuthResponse, RegisterData, LoginData, AuthCheckResponse }; 