<template>
  <div class="login-container">
    <div class="login-card">
      <div class="login-header">
        <h1 class="login-title">MT题库练习系统</h1>
        <p class="login-subtitle">登录您的账户</p>
      </div>

      <form @submit.prevent="handleLogin" class="login-form">
        <div class="form-group">
          <label for="username" class="form-label">用户名</label>
          <input
            id="username"
            v-model="formData.username"
            type="text"
            class="form-control"
            :class="{ 'form-control-error': usernameError }"
            placeholder="请输入用户名"
            required
            :disabled="authStore.isLoading"
          />
          <p v-if="usernameError" class="error-text">{{ usernameError }}</p>
        </div>

        <div class="form-group">
          <label for="password" class="form-label">密码</label>
          <div class="password-input-container">
            <input
              id="password"
              v-model="formData.password"
              :type="showPassword ? 'text' : 'password'"
              class="form-control"
              :class="{ 'form-control-error': passwordError }"
              placeholder="请输入密码"
              required
              :disabled="authStore.isLoading"
            />
            <button
              type="button"
              class="password-toggle"
              @click="showPassword = !showPassword"
              :disabled="authStore.isLoading"
            >
              <svg v-if="showPassword" class="icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path>
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"></path>
              </svg>
              <svg v-else class="icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.878 9.878L3 3m6.878 6.878L12 12m0 0l3.12 3.12"></path>
              </svg>
            </button>
          </div>
          <p v-if="passwordError" class="error-text">{{ passwordError }}</p>
        </div>

        <div v-if="authStore.error" class="error-banner">
          <svg class="error-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
          </svg>
          {{ authStore.error }}
        </div>

        <!-- 记住我选项 -->
        <div class="remember-me-group">
          <label class="remember-me-label">
            <input
              type="checkbox"
              v-model="rememberMe"
              class="remember-me-checkbox"
              :disabled="authStore.isLoading"
            />
            <span class="checkbox-custom"></span>
            <span class="remember-me-text">记住用户名</span>
          </label>
          <button
            v-if="hasSavedCredentials"
            type="button"
            class="clear-saved-btn"
            @click="clearSavedCredentials"
            :disabled="authStore.isLoading"
          >
            清除保存
          </button>
        </div>

        <button
          type="submit"
          class="btn btn-primary btn-full"
          :disabled="authStore.isLoading || !formData.username || !formData.password"
        >
          <svg v-if="authStore.isLoading" class="loading-spinner" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          <span v-if="!authStore.isLoading">登录</span>
          <span v-else>登录中...</span>
        </button>
      </form>

      <div class="login-footer">
        <p class="auth-link">
          还没有账户？
          <router-link to="/register" class="link">立即注册</router-link>
        </p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onUnmounted } from 'vue';
import { useRouter } from 'vue-router';
import { useAuthStore } from '@/stores/auth';
import { useToast } from 'vue-toastification'

const router = useRouter();
const authStore = useAuthStore();
const toast = useToast();

const showPassword = ref(false);
const usernameError = ref('');
const passwordError = ref('');
const rememberMe = ref(false);
const hasSavedCredentials = ref(false);

// 本地存储的key
const SAVED_USERNAME_KEY = 'mt_saved_username';

const formData = reactive({
  username: '',
  password: ''
});

// 检查是否有保存的用户名
function checkSavedCredentials() {
  const savedUsername = localStorage.getItem(SAVED_USERNAME_KEY);
  if (savedUsername) {
    formData.username = savedUsername;
    rememberMe.value = true;
    hasSavedCredentials.value = true;
  }
}

// 保存用户名到本地存储
function saveCredentials() {
  if (rememberMe.value && formData.username.trim()) {
    localStorage.setItem(SAVED_USERNAME_KEY, formData.username.trim());
    hasSavedCredentials.value = true;
  } else {
    localStorage.removeItem(SAVED_USERNAME_KEY);
    hasSavedCredentials.value = false;
  }
}

// 清除保存的凭据
function clearSavedCredentials() {
  localStorage.removeItem(SAVED_USERNAME_KEY);
  hasSavedCredentials.value = false;
  rememberMe.value = false;
  if (formData.username === localStorage.getItem(SAVED_USERNAME_KEY)) {
    formData.username = '';
  }
}

function validateForm(): boolean {
  usernameError.value = '';
  passwordError.value = '';

  if (!formData.username.trim()) {
    usernameError.value = '请输入用户名';
    return false;
  }

  if (formData.username.length < 3) {
    usernameError.value = '用户名至少3个字符';
    return false;
  }

  if (!formData.password) {
    passwordError.value = '请输入密码';
    return false;
  }

  if (formData.password.length < 6) {
    passwordError.value = '密码至少6个字符';
    return false;
  }

  return true;
}

async function handleLogin() {
  if (!validateForm()) {
    return;
  }

  authStore.clearError();

  const success = await authStore.login(formData.username, formData.password);

  if (success) {
    // 登录成功后保存凭据
    saveCredentials();
    toast.success('登录成功！');
    router.push('/');
  } else {
    // 使用 toast 显示失败原因，格式化错误信息
    const errorReason = authStore.error || '请重试';
    toast.error(`登录失败：${errorReason}`);
  }
}

onMounted(() => {
  // 添加认证页面类到app元素
  const app = document.getElementById('app');
  if (app) {
    app.classList.add('auth-page');
  }

  // 检查保存的凭据
  checkSavedCredentials();

  // 如果已经登录，直接跳转到首页
  if (authStore.isAuthenticated) {
    router.push('/');
  }
});

onUnmounted(() => {
  // 移除认证页面类
  const app = document.getElementById('app');
  if (app) {
    app.classList.remove('auth-page');
  }
});
</script>

<style scoped>
/* 强制重置app容器的约束 */
:global(#app.auth-page) {
  max-width: none !important;
  padding: 0 !important;
  display: block !important;
  grid-template-columns: none !important;
}

.login-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 16px; /* 使用具体值代替CSS变量 */
  position: relative;
  box-sizing: border-box;
}

.login-card {
  background: white;
  border-radius: 8px;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
  padding: 32px;
  width: calc(100vw - 32px) !important;
  max-width: 1000px !important;
  min-width: 400px;
  position: relative;
  z-index: 1;
  backdrop-filter: blur(10px);
  box-sizing: border-box;
}

.login-header {
  text-align: center;
  margin-bottom: var(--space-8);
}

.login-title {
  font-size: 2rem;
  font-weight: var(--font-bold);
  color: var(--text-primary);
  margin-bottom: var(--space-2);
  line-height: 1.2;
}

.login-subtitle {
  color: var(--text-secondary);
  font-size: var(--text-base);
  line-height: 1.5;
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.form-label {
  font-weight: var(--font-medium);
  color: var(--text-primary);
  font-size: var(--text-sm);
}

.form-control {
  padding: var(--space-3);
  border: 3px solid #e2e8f0;
  border-radius: var(--radius-md);
  font-size: var(--text-base);
  transition: all var(--transition-fast);
  width: 100%;
  box-sizing: border-box;
  line-height: 1.5;
  background-color: #ffffff;
}

.form-control:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.15);
  background-color: #fafbff;
}

.form-control-error {
  border-color: #ef4444;
  background-color: #fef7f7;
  box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.1);
}

.password-input-container {
  position: relative;
}

.password-toggle {
  position: absolute;
  right: var(--space-3);
  top: 50%;
  transform: translateY(-50%);
  background: #f8fafc;
  border: 2px solid #e2e8f0;
  color: #475569;
  cursor: pointer;
  padding: var(--space-1);
  border-radius: var(--radius-md);
  transition: all var(--transition-fast);
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 40px;
  min-height: 40px;
}

.password-toggle:hover {
  background: #e2e8f0;
  border-color: #cbd5e1;
  color: #1e293b;
}

.password-toggle:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.icon {
  width: 1.25rem;
  height: 1.25rem;
}

.error-text {
  color: #dc2626;
  font-size: var(--text-sm);
  margin: 0;
  line-height: 1.4;
  font-weight: 500;
}

.error-banner {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-4);
  background: linear-gradient(135deg, #fef2f2, #fee2e2);
  border: 2px solid #fca5a5;
  border-radius: var(--radius-lg);
  color: #dc2626;
  font-size: var(--text-sm);
  line-height: 1.5;
  font-weight: 500;
  box-shadow: 0 4px 12px rgba(239, 68, 68, 0.15);
}

.error-icon {
  width: 1.25rem;
  height: 1.25rem;
  flex-shrink: 0;
}

.btn {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-4) var(--space-6);
  border: 3px solid transparent;
  border-radius: var(--radius-lg);
  font-weight: 600;
  cursor: pointer;
  transition: all var(--transition-fast);
  font-size: var(--text-lg);
  line-height: 1.5;
  text-decoration: none;
  box-sizing: border-box;
  min-height: 56px;
  gap: var(--space-2);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.btn-primary {
  background: linear-gradient(135deg, #3b82f6, #1d4ed8);
  color: white;
  border-color: #2563eb;
}

.btn-primary:hover:not(:disabled) {
  background: linear-gradient(135deg, #2563eb, #1e40af);
  border-color: #1d4ed8;
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(59, 130, 246, 0.35);
}

.btn-primary:active:not(:disabled) {
  transform: translateY(0);
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.25);
}

.btn-primary:disabled {
  background: linear-gradient(135deg, #9ca3af, #6b7280);
  border-color: #9ca3af;
  color: rgba(255, 255, 255, 0.8);
  cursor: not-allowed;
  transform: none;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.btn-full {
  width: 100%;
}

.loading-spinner {
  width: 1.25rem;
  height: 1.25rem;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.login-footer {
  margin-top: var(--space-5);
}

.auth-link {
  color: var(--text-secondary);
  font-size: var(--text-base);
  line-height: 1.5;
  font-weight: 500;
}

.link {
  color: #3b82f6;
  text-decoration: none;
  font-weight: 600;
  transition: all var(--transition-fast);
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-sm);
}

.link:hover {
  color: #1d4ed8;
  background-color: rgba(59, 130, 246, 0.1);
  text-decoration: underline;
}

/* 超大屏幕 (1600px+) */
@media (min-width: 1600px) {
  .login-card {
    max-width: 1400px !important;
    padding: 48px;
  }

  .login-title {
    font-size: 3rem;
  }

  .login-subtitle {
    font-size: 1.25rem;
  }

  .form-control {
    padding: 16px;
    font-size: 1.25rem;
  }

  .password-toggle {
    min-width: 48px;
    min-height: 48px;
  }

  .btn {
    padding: 16px 32px;
    font-size: 1.25rem;
    min-height: 56px;
  }

  .login-form {
    gap: 32px;
  }
}

/* 大屏幕 (1200px - 1599px) */
@media (min-width: 1200px) and (max-width: 1599px) {
  .login-container {
    padding: 24px;
  }

  .login-card {
    max-width: 1200px !important;
    padding: 40px;
  }

  .login-title {
    font-size: 2.5rem;
  }

  .login-subtitle {
    font-size: 1.125rem;
  }

  .form-control {
    padding: 16px;
    font-size: 1.125rem;
  }

  .password-toggle {
    min-width: 44px;
    min-height: 44px;
  }

  .btn {
    padding: 16px 24px;
    font-size: 1.125rem;
    min-height: 52px;
  }
}

/* 中等屏幕 (768px - 1199px) */
@media (min-width: 768px) and (max-width: 1199px) {
  .login-container {
    padding: 20px;
  }

  .login-card {
    max-width: 800px !important;
    padding: 32px;
  }

  .login-title {
    font-size: 2.25rem;
  }

  .form-control {
    padding: 12px 16px;
  }

  .btn {
    min-height: 50px;
  }
}

/* 小屏幕平板 (640px - 767px) */
@media (min-width: 640px) and (max-width: 767px) {
  .login-container {
    padding: 16px;
  }

  .login-card {
    max-width: 550px !important;
    padding: 24px;
  }

  .login-title {
    font-size: 1.875rem;
  }

  .login-header {
    margin-bottom: 24px;
  }

  .form-control {
    padding: 12px;
  }

  .btn {
    min-height: 48px;
  }
}

/* 手机端 (320px - 639px) */
@media (max-width: 639px) {
  .login-container {
    padding: var(--space-3);
    min-height: 100vh;
    min-height: 100dvh; /* 支持动态视口 */
  }

  .login-card {
    max-width: 100%;
    width: 100%;
    padding: var(--space-6);
    margin: 0;
    box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1);
  }

  .login-header {
    margin-bottom: var(--space-6);
  }

  .login-title {
    font-size: 1.75rem;
    line-height: 1.3;
  }

  .login-subtitle {
    font-size: var(--text-sm);
  }

  .login-form {
    gap: var(--space-5);
  }

  .form-control {
    padding: var(--space-3);
    font-size: 1rem;
    min-height: 44px; /* 保证触摸友好 */
  }

  .password-toggle {
    min-width: 44px;
    min-height: 44px;
    right: var(--space-2);
  }

  .icon {
    width: 1.125rem;
    height: 1.125rem;
  }

  .btn {
    padding: var(--space-3) var(--space-4);
    min-height: 48px;
    font-size: 1.125rem;
    border-radius: var(--radius-lg);
  }

  .error-banner {
    padding: var(--space-3);
    flex-direction: row;
    align-items: flex-start;
    gap: var(--space-2);
  }

  .error-text {
    font-size: 0.875rem;
  }

  .auth-link {
    font-size: 0.875rem;
  }

  .login-footer {
    margin-top: var(--space-5);
  }

  .remember-me-group {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--space-2);
  }
  
  .clear-saved-btn {
    align-self: flex-end;
    font-size: 0.75rem;
    padding: var(--space-1) var(--space-2);
  }
}

/* 超小屏幕 (最小320px) */
@media (max-width: 379px) {
  .login-container {
    padding: var(--space-2);
  }

  .login-card {
    padding: var(--space-4);
    border-radius: var(--radius-md);
  }

  .login-title {
    font-size: 1.5rem;
  }

  .login-subtitle {
    font-size: 0.875rem;
  }

  .form-control {
    padding: var(--space-2) var(--space-3);
  }

  .password-toggle {
    min-width: 40px;
    min-height: 40px;
  }

  .btn {
    min-height: 44px;
    font-size: 1rem;
  }
  
  .remember-me-text {
    font-size: 0.8rem;
  }
  
  .checkbox-custom {
    width: 1.125rem;
    height: 1.125rem;
  }
}

/* 横屏模式优化 */
@media (max-height: 600px) and (orientation: landscape) {
  .login-container {
    padding: var(--space-2) var(--space-4);
  }

  .login-card {
    padding: var(--space-4) var(--space-6);
    max-height: 90vh;
    overflow-y: auto;
  }

  .login-header {
    margin-bottom: var(--space-4);
  }

  .login-title {
    font-size: 1.5rem;
    margin-bottom: var(--space-1);
  }

  .login-subtitle {
    font-size: 0.875rem;
  }

  .login-form {
    gap: var(--space-4);
  }

  .login-footer {
    margin-top: var(--space-4);
  }
}

/* 高分辨率屏幕优化 */
@media (-webkit-min-device-pixel-ratio: 2), (min-resolution: 192dpi) {
  .login-card {
    border: 0.5px solid rgba(255, 255, 255, 0.1);
  }

  .form-control {
    border-width: 1px;
  }

  .form-control:focus {
    border-width: 2px;
  }
}

/* 无障碍访问优化 */
@media (prefers-reduced-motion: reduce) {
  .login-card,
  .form-control,
  .btn,
  .password-toggle,
  .link,
  .loading-spinner {
    transition: none;
    animation: none;
  }
}

/* 暗色模式支持 */
@media (prefers-color-scheme: dark) {
  .login-container {
    background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
  }

  .login-card {
    background: #1e293b;
    color: #e2e8f0;
    box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.4);
  }

  .login-title {
    color: #f8fafc;
  }

  .login-subtitle {
    color: #cbd5e1;
  }

  .form-label {
    color: #f1f5f9;
  }

  .form-control {
    background: #334155;
    border-color: #475569;
    color: #f1f5f9;
  }

  .form-control:focus {
    border-color: var(--primary-color);
    background: #3f4a5c;
  }

  .form-control::placeholder {
    color: #94a3b8;
  }

  .password-toggle {
    color: #94a3b8;
  }

  .password-toggle:hover {
    color: #f1f5f9;
  }

  .auth-link {
    color: #cbd5e1;
  }
}

/* 打印样式 */
@media print {
  .login-container {
    background: white;
    padding: 0;
  }

  .login-card {
    box-shadow: none;
    border: 1px solid #000;
  }

  .btn,
  .password-toggle {
    display: none;
  }

  .form-control {
    border: 1px solid #000;
  }
}

/* 记住我选项样式 */
.remember-me-group {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin: var(--space-2) 0;
}

.remember-me-label {
  display: flex;
  align-items: center;
  cursor: pointer;
  user-select: none;
  gap: var(--space-2);
}

.remember-me-checkbox {
  opacity: 0;
  position: absolute;
  width: 1px;
  height: 1px;
}

.checkbox-custom {
  width: 1.25rem;
  height: 1.25rem;
  border: 2px solid #e2e8f0;
  border-radius: var(--radius-sm);
  position: relative;
  transition: all var(--transition-fast);
  background-color: white;
  flex-shrink: 0;
}

.remember-me-checkbox:checked + .checkbox-custom {
  background-color: #3b82f6;
  border-color: #3b82f6;
}

.remember-me-checkbox:checked + .checkbox-custom::after {
  content: '';
  position: absolute;
  top: 2px;
  left: 5px;
  width: 6px;
  height: 10px;
  border: 2px solid white;
  border-top: none;
  border-left: none;
  transform: rotate(45deg);
}

.remember-me-checkbox:focus + .checkbox-custom {
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.remember-me-label:hover .checkbox-custom {
  border-color: #3b82f6;
}

.remember-me-text {
  color: var(--text-secondary);
  font-size: var(--text-sm);
  font-weight: 500;
}

.clear-saved-btn {
  background: none;
  border: 1px solid #e2e8f0;
  color: #64748b;
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
  cursor: pointer;
  transition: all var(--transition-fast);
  font-weight: 500;
}

.clear-saved-btn:hover:not(:disabled) {
  background-color: #f8fafc;
  border-color: #cbd5e1;
  color: #475569;
}

.clear-saved-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
