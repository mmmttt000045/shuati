import { AUTH_API_BASE_URL, enableApiLogging } from '@/config/api';

interface AuthUser {
  user_id: number;
  username: string;
}

interface AuthResponse {
  success: boolean;
  message?: string;
  error?: string;
  user?: AuthUser;
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
  user?: AuthUser;
  error?: string;
}

class AuthService {
  private baseURL = AUTH_API_BASE_URL;

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

    if (enableApiLogging) {
      console.log('Making auth request:', {
        url,
        method: finalOptions.method || 'GET',
        headers: finalOptions.headers,
        credentials: finalOptions.credentials,
        cookies: document.cookie
      });
    }

    return fetch(url, finalOptions);
  }

  async register(data: RegisterData): Promise<AuthResponse> {
    try {
      const response = await this.makeRequest(`${this.baseURL}/register`, {
        method: 'POST',
        body: JSON.stringify(data),
      });

      const result = await response.json();
      
      if (enableApiLogging) {
        console.log('注册响应:', result);
      }
      
      return result;
    } catch (error) {
      if (enableApiLogging) {
        console.error('注册请求失败:', error);
      }
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
      
      if (enableApiLogging) {
        console.log('登录响应:', result);
        console.log('登录后cookies:', document.cookie);
      }
      
      return result;
    } catch (error) {
      if (enableApiLogging) {
        console.error('登录请求失败:', error);
      }
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

      const result = await response.json();
      
      if (enableApiLogging) {
        console.log('登出响应:', result);
      }
      
      return result;
    } catch (error) {
      if (enableApiLogging) {
        console.error('登出请求失败:', error);
      }
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

      const result = await response.json();
      
      if (enableApiLogging) {
        console.log('认证检查响应:', result);
      }
      
      return result;
    } catch (error) {
      if (enableApiLogging) {
        console.error('检查登录状态失败:', error);
      }
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

      const result = await response.json();
      
      if (enableApiLogging) {
        console.log('用户信息响应:', result);
      }
      
      return result;
    } catch (error) {
      if (enableApiLogging) {
        console.error('获取用户信息失败:', error);
      }
      return {
        success: false,
        error: '网络请求失败'
      };
    }
  }
}

export const authService = new AuthService();
export type { AuthUser, AuthResponse, RegisterData, LoginData, AuthCheckResponse }; 