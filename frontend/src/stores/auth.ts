import { ref, computed } from 'vue';
import { defineStore } from 'pinia';
import { authService } from '@/services/auth';
import type { User } from '@/types';

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null);
  const isLoading = ref(false);
  const error = ref<string | null>(null);

  const isAuthenticated = computed(() => !!user.value);

  // 登录
  async function login(username: string, password: string): Promise<boolean> {
    isLoading.value = true;
    error.value = null;

    try {
      const result = await authService.login({ username, password });
      
      if (result.success && result.user) {
        user.value = result.user;
        return true;
      } else {
        error.value = result.error || '登录失败';
        return false;
      }
    } catch (err) {
      error.value = '登录过程中发生错误';
      return false;
    } finally {
      isLoading.value = false;
    }
  }

  // 注册
  async function register(username: string, password: string, invitationCode: string): Promise<boolean> {
    isLoading.value = true;
    error.value = null;

    try {
      const result = await authService.register({
        username,
        password,
        invitation_code: invitationCode
      });
      
      if (result.success) {
        return true;
      } else {
        error.value = result.error || '注册失败';
        return false;
      }
    } catch (err) {
      error.value = '注册过程中发生错误';
      return false;
    } finally {
      isLoading.value = false;
    }
  }

  // 登出
  async function logout(): Promise<void> {
    isLoading.value = true;
    
    try {
      await authService.logout();
    } catch (err) {
      // 保留错误日志，但可以考虑使用更简洁的方式
    } finally {
      user.value = null;
      error.value = null;
      isLoading.value = false;
    }
  }

  // 检查登录状态
  async function checkAuth(): Promise<void> {
    isLoading.value = true;
    
    try {
      const result = await authService.checkAuth();
      
      if (result.success && result.authenticated && result.user) {
        user.value = result.user;
      } else {
        user.value = null;
      }
    } catch (err) {
      user.value = null;
    } finally {
      isLoading.value = false;
    }
  }

  // 清除错误
  function clearError(): void {
    error.value = null;
  }

  // 处理认证失败
  function handleAuthFailure(): void {
    user.value = null;
    error.value = null;
    isLoading.value = false;
  }

  return {
    user,
    isLoading,
    error,
    isAuthenticated,
    login,
    register,
    logout,
    checkAuth,
    clearError,
    handleAuthFailure
  };
}); 