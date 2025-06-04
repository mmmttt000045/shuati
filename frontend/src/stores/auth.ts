import { ref, computed, watch } from 'vue';
import { defineStore } from 'pinia';
import { authService } from '@/services/auth';
import type { User, SessionInfo, LoginSuccessPayload, AuthCheckClientResponseData, ServiceResponse } from '@/types';

const SESSION_CHECK_INTERVAL = 60 * 1000; // Check session every 60 seconds

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null);
  const sessionInfo = ref<SessionInfo | null>(null);
  const isLoading = ref(false);
  const error = ref<string | null>(null);

  const isAuthenticated = computed(() => !!user.value && !!sessionInfo.value && sessionInfo.value.is_authenticated && sessionInfo.value.session_valid);
  const isSessionExpiringSoon = computed(() => sessionInfo.value?.warning_threshold_reached === true && sessionInfo.value?.warning_shown === false);
  const sessionTimeRemainingText = computed(() => {
    if (!sessionInfo.value?.time_remaining) return 'N/A';
    const totalSeconds = sessionInfo.value.time_remaining;
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = totalSeconds % 60;
    return `${minutes}m ${seconds}s`;
  });

  // Helper to set auth state
  function setAuthState(userData: User | null, sessionData: SessionInfo | null) {
    user.value = userData;
    sessionInfo.value = sessionData;
    if (!userData || !sessionData || !sessionData.is_authenticated) {
      // If unauthenticated, ensure both are null
      user.value = null;
      sessionInfo.value = null;
    }
  }

  // Helper to set error
  function setErrorState(serviceMessage?: string, serviceError?: string, defaultMessage: string = '操作失败') {
    error.value = serviceMessage || serviceError || defaultMessage;
    console.error('Auth Store Error:', serviceMessage, serviceError);
  }

  // 登录
  async function login(username: string, password: string): Promise<boolean> {
    isLoading.value = true;
    error.value = null;

    try {
      const result = await authService.login({ username, password });
      
      if (result.success && result.data) {
        setAuthState(result.data.user, result.data.session);
        return true;
      } else {
        setAuthState(null, null);
        setErrorState(result.message, result.error, '登录失败');
        return false;
      }
    } catch (err: any) {
      setAuthState(null, null);
      setErrorState(undefined, err.message, '登录过程中发生未知错误');
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
        setErrorState(result.message, result.error, '注册失败');
        return false;
      }
    } catch (err: any) {
      setErrorState(undefined, err.message, '注册过程中发生未知错误');
      return false;
    } finally {
      isLoading.value = false;
    }
  }

  // 登出
  async function logout(): Promise<void> {
    isLoading.value = true;
    
    try {
      const result = await authService.logout();
      if (!result.success) {
         // Even if server logout fails, client should clear state
         setErrorState(result.message, result.error, '登出操作在服务器端失败，但客户端已清理状态');
      }
    } catch (err: any) {
       setErrorState(undefined, err.message, '登出过程中发生未知错误，客户端已清理状态');
    } finally {
      setAuthState(null, null);
      // error.value can be set by setErrorState if server logout fails, so don't nullify it here unless intended.
      isLoading.value = false;
    }
  }

  // 检查登录状态
  async function checkAuth(): Promise<void> {
    isLoading.value = true;
    
    try {
      const result = await authService.checkAuth();
      
      if (result.success && result.data?.authenticated && result.data.user) {
        // If authenticated, fetch full session status for details like expiry
        await fetchSessionStatus(result.data.user); // Pass user to avoid race conditions if session has partial user info
      } else {
        setAuthState(null, null);
        if (!result.success) { // Only set error if the checkAuth call itself failed
            setErrorState(result.message, result.error, '检查登录状态失败');
        }
      }
    } catch (err: any) {
      setAuthState(null, null);
      setErrorState(undefined, err.message, '检查登录状态时发生未知错误');
    } finally {
      isLoading.value = false;
    }
  }

  // New session management actions
  async function fetchSessionStatus(currentUser?: User | null): Promise<void> {
    isLoading.value = true; 
    // error.value = null; // Decide if this should clear previous errors
    try {
      const result = await authService.getSessionStatus();
      if (result.success && result.data?.session) {
        // Use currentUser if provided and session doesn't have full user details,
        // or if session user_id matches. This assumes session user_id is reliable.
        const finalUser = result.data.session.user_id && currentUser && result.data.session.user_id === currentUser.user_id 
                          ? currentUser 
                          : (result.data.session.user_id ? { user_id: result.data.session.user_id, username: result.data.session.username || '', model: 0 } as User : null);
        
        setAuthState(finalUser, result.data.session);

        if (!result.data.session.is_authenticated || !result.data.session.session_valid) {
            // If session is not valid/authenticated, ensure user is logged out locally
            setAuthState(null, null);
        }

      } else {
        // If fetching session fails, consider it as unauthenticated.
        setAuthState(null, null);
        setErrorState(result.message, result.error, '获取会话状态失败');
      }
    } catch (err: any) {
      setAuthState(null, null);
      setErrorState(undefined, err.message, '获取会话状态时发生未知错误');
    } finally {
      isLoading.value = false;
    }
  }

  async function extendUserSession(): Promise<boolean> {
    isLoading.value = true;
    error.value = null;
    try {
      const result = await authService.extendSession();
      if (result.success && result.data?.session) {
        sessionInfo.value = result.data.session; // Update sessionInfo only
        // User state should remain as is, assuming it's still valid
        return true;
      } else {
        setErrorState(result.message, result.error, '延长会话失败');
        // Optionally, re-fetch session status if extension fails critically
        await fetchSessionStatus(user.value);
        return false;
      }
    } catch (err: any) {
      setErrorState(undefined, err.message, '延长会话时发生未知错误');
      // If extend session fails, we re-fetch status. user.value is User | null, which now matches the updated signature.
      await fetchSessionStatus(user.value);
      return false;
    } finally {
      isLoading.value = false;
    }
  }

  async function markSessionWarningAsShown(): Promise<void> {
    // No isLoading for this as it's a background update usually
    try {
      const result = await authService.markWarningShown();
      if (result.success && sessionInfo.value) {
        sessionInfo.value.warning_shown = true;
      } else if (!result.success) {
        setErrorState(result.message, result.error, '标记会话警告失败');
      }
    } catch (err: any) {
      setErrorState(undefined, err.message, '标记会话警告时发生未知错误');
    }
  }

  // 清除错误
  function clearError(): void {
    error.value = null;
  }

  return {
    user,
    sessionInfo,
    isLoading,
    error,
    isAuthenticated,
    isSessionExpiringSoon,
    sessionTimeRemainingText,
    login,
    register,
    logout,
    checkAuth,
    fetchSessionStatus,
    extendUserSession,
    markSessionWarningAsShown,
    clearError,
  };
}); 