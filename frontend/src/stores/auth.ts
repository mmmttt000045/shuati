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
  const isInitialized = ref(false); // 添加初始化状态标志

  const isAuthenticated = computed(() => {
    // 只要有用户信息就认为是已认证状态
    // sessionInfo 是可选的，用于提供额外的session状态信息
    return !!user.value && (
      !sessionInfo.value || // 如果没有sessionInfo，只要有user就认为已认证
      (sessionInfo.value.is_authenticated && sessionInfo.value.session_valid)
    );
  });
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
    
    // 只有在明确需要清空状态时才清空（userData为null，或者sessionData明确表示未认证）
    if (!userData || (sessionData && (!sessionData.is_authenticated || !sessionData.session_valid))) {
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
        isInitialized.value = true; // 登录成功后标记为已初始化
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
      isInitialized.value = false; // 登出时重置初始化状态
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
        // 直接设置用户状态，不等待session信息
        setAuthState(result.data.user, null);
        
        // 在后台获取完整的session状态信息（不阻塞路由）
        fetchSessionStatus(result.data.user).catch(err => {
          console.warn('Failed to fetch session status:', err);
          // 即使获取session状态失败，也不影响已认证状态
        });
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
      isInitialized.value = true; // 标记初始化完成
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
        // 如果获取session状态失败，保持用户状态不变，只更新session信息
        if (currentUser) {
          setAuthState(currentUser, null);
        } else {
          setAuthState(null, null);
        }
        setErrorState(result.message, result.error, '获取会话状态失败');
      }
    } catch (err: any) {
      // 发生异常时，如果有传入的用户信息，保持用户状态
      if (currentUser) {
        setAuthState(currentUser, null);
      } else {
        setAuthState(null, null);
      }
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
    isInitialized,
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