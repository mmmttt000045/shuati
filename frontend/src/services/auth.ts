import { AUTH_API_BASE_URL } from '@/config/api';

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

    return fetch(url, finalOptions);
  }

  async register(data: RegisterData): Promise<AuthResponse> {
    try {
      const response = await this.makeRequest(`${this.baseURL}/register`, {
        method: 'POST',
        body: JSON.stringify(data),
      });

      return await response.json();
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

      return await response.json();
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
export type { AuthUser, AuthResponse, RegisterData, LoginData, AuthCheckResponse }; 