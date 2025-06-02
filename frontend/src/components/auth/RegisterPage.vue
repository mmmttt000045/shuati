<template>
  <div class="register-container">
    <div class="register-card">
      <div class="register-header">
        <h1 class="register-title">MT题库练习系统</h1>
        <p class="register-subtitle">创建新账户</p>
      </div>

      <form @submit.prevent="handleRegister" class="register-form">
        <div class="form-group">
          <label for="invitation_code" class="form-label">邀请码</label>
          <input
            id="invitation_code"
            v-model="formData.invitation_code"
            type="text"
            class="form-control"
            :class="{ 'form-control-error': invitationCodeError }"
            placeholder="请输入邀请码"
            required
            :disabled="authStore.isLoading"
          />
          <p v-if="invitationCodeError" class="error-text">{{ invitationCodeError }}</p>
          <div class="invitation-hint">
            <svg class="hint-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
            </svg>
            <span class="hint-text">没有邀请码请联系MT，否则不可注册</span>
          </div>
        </div>

        <div class="form-group">
          <label for="username" class="form-label">用户名</label>
          <input
            id="username"
            v-model="formData.username"
            type="text"
            class="form-control"
            :class="{ 'form-control-error': usernameError }"
            placeholder="请输入用户名 (3-20个字符)"
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
              placeholder="请输入密码 (至少6个字符)"
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

        <div class="form-group">
          <label for="confirm_password" class="form-label">确认密码</label>
          <div class="password-input-container">
            <input
              id="confirm_password"
              v-model="formData.confirm_password"
              :type="showConfirmPassword ? 'text' : 'password'"
              class="form-control"
              :class="{ 'form-control-error': confirmPasswordError }"
              placeholder="请再次输入密码"
              required
              :disabled="authStore.isLoading"
            />
            <button
              type="button"
              class="password-toggle"
              @click="showConfirmPassword = !showConfirmPassword"
              :disabled="authStore.isLoading"
            >
              <svg v-if="showConfirmPassword" class="icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path>
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"></path>
              </svg>
              <svg v-else class="icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.878 9.878L3 3m6.878 6.878L12 12m0 0l3.12 3.12"></path>
              </svg>
            </button>
          </div>
          <p v-if="confirmPasswordError" class="error-text">{{ confirmPasswordError }}</p>
        </div>

        <div v-if="authStore.error" class="error-banner">
          <svg class="error-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
          </svg>
          {{ authStore.error }}
        </div>

        <div v-if="successMessage" class="success-banner">
          <svg class="success-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
          </svg>
          {{ successMessage }}
        </div>

        <button
          type="submit"
          class="btn btn-primary btn-full"
          :disabled="authStore.isLoading || !isFormValid"
        >
          <svg v-if="authStore.isLoading" class="loading-spinner" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          <span v-if="!authStore.isLoading">注册</span>
          <span v-else>注册中...</span>
        </button>
      </form>

      <div class="register-footer">
        <p class="auth-link">
          已有账户？
          <router-link to="/login" class="link">立即登录</router-link>
        </p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue';
import { useRouter } from 'vue-router';
import { useAuthStore } from '@/stores/auth';
import { useToast } from 'vue-toastification'

const router = useRouter();
const authStore = useAuthStore();
const toast = useToast();

const showPassword = ref(false);
const showConfirmPassword = ref(false);
const successMessage = ref('');

const invitationCodeError = ref('');
const usernameError = ref('');
const passwordError = ref('');
const confirmPasswordError = ref('');

const formData = reactive({
  invitation_code: '',
  username: '',
  password: '',
  confirm_password: ''
});

const isFormValid = computed(() => {
  return formData.invitation_code.trim() &&
         formData.username.trim() &&
         formData.password &&
         formData.confirm_password &&
         formData.password === formData.confirm_password &&
         formData.username.length >= 3 &&
         formData.username.length <= 20 &&
         formData.password.length >= 6;
});

function validateForm(): boolean {
  invitationCodeError.value = '';
  usernameError.value = '';
  passwordError.value = '';
  confirmPasswordError.value = '';

  let isValid = true;

  if (!formData.invitation_code.trim()) {
    invitationCodeError.value = '请输入邀请码';
    isValid = false;
  }

  if (!formData.username.trim()) {
    usernameError.value = '请输入用户名';
    isValid = false;
  } else if (formData.username.length < 3) {
    usernameError.value = '用户名至少3个字符';
    isValid = false;
  } else if (formData.username.length > 20) {
    usernameError.value = '用户名最多20个字符';
    isValid = false;
  }

  if (!formData.password) {
    passwordError.value = '请输入密码';
    isValid = false;
  } else if (formData.password.length < 6) {
    passwordError.value = '密码至少6个字符';
    isValid = false;
  }

  if (!formData.confirm_password) {
    confirmPasswordError.value = '请确认密码';
    isValid = false;
  } else if (formData.password !== formData.confirm_password) {
    confirmPasswordError.value = '两次密码输入不一致';
    isValid = false;
  }

  return isValid;
}

async function handleRegister() {
  if (!validateForm()) {
    return;
  }

  authStore.clearError();
  successMessage.value = '';
  
  const success = await authStore.register(
    formData.username,
    formData.password,
    formData.invitation_code
  );
  
  if (success) {
    successMessage.value = '注册成功！正在跳转到登录页面...';
    toast.success('注册成功！正在跳转到登录页面...');
    setTimeout(() => {
      router.push('/login');
    }, 2000);
  } else {
    // 使用 toast 显示失败原因，格式化错误信息
    const errorReason = authStore.error || '请重试';
    toast.error(`注册失败：${errorReason}`);
  }
}

onMounted(() => {
  // 添加认证页面类到app元素
  const app = document.getElementById('app');
  if (app) {
    app.classList.add('auth-page');
  }
  
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
.register-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: var(--space-4);
  position: relative;
}

.register-card {
  background: white;
  border-radius: var(--radius-lg);
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
  padding: var(--space-8);
  width: 100%;
  max-width: 1000px;
  position: relative;
  z-index: 1;
  backdrop-filter: blur(10px);
}

.register-header {
  text-align: center;
  margin-bottom: var(--space-8);
}

.register-title {
  font-size: 2rem;
  font-weight: var(--font-bold);
  color: var(--text-primary);
  margin-bottom: var(--space-2);
  line-height: 1.2;
}

.register-subtitle {
  color: var(--text-secondary);
  font-size: var(--text-base);
  line-height: 1.5;
}

.register-form {
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

/* 邀请码提示样式 */
.invitation-hint {
  display: flex;
  align-items: flex-start;
  gap: var(--space-2);
  margin-top: var(--space-2);
  padding: var(--space-3);
  background: linear-gradient(135deg, #eff6ff, #dbeafe);
  border: 1px solid #93c5fd;
  border-radius: var(--radius-md);
  color: #1e40af;
  font-size: var(--text-sm);
  line-height: 1.5;
}

.hint-icon {
  width: 1rem;
  height: 1rem;
  flex-shrink: 0;
  margin-top: 0.125rem;
}

.hint-text {
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

.success-banner {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-4);
  background: linear-gradient(135deg, #f0fdf4, #dcfce7);
  border: 2px solid #86efac;
  border-radius: var(--radius-lg);
  color: #16a34a;
  font-size: var(--text-sm);
  line-height: 1.5;
  font-weight: 500;
  box-shadow: 0 4px 12px rgba(22, 163, 74, 0.15);
}

.error-icon,
.success-icon {
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

.register-footer {
  margin-top: var(--space-5);
  text-align: center;
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

/* 超大屏幕 (1600px+) - 双列布局 */
@media (min-width: 1600px) {
  .register-card {
    max-width: 1400px;
    padding: var(--space-12);
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: var(--space-10);
    align-items: start;
  }
  
  .register-header {
    grid-column: 1 / -1;
    margin-bottom: var(--space-8);
  }
  
  .register-title {
    font-size: 3rem;
  }
  
  .register-subtitle {
    font-size: 1.25rem;
  }
  
  .register-form {
    grid-column: 1 / -1;
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: var(--space-6) var(--space-8);
  }
  
  /* 邀请码和用户名放在第一行 */
  .register-form .form-group:nth-child(1) {
    grid-column: 1;
  }
  
  .register-form .form-group:nth-child(2) {
    grid-column: 2;
  }
  
  /* 密码和确认密码放在第二行 */
  .register-form .form-group:nth-child(3) {
    grid-column: 1;
  }
  
  .register-form .form-group:nth-child(4) {
    grid-column: 2;
  }
  
  /* 错误/成功消息跨越两列 */
  .error-banner,
  .success-banner {
    grid-column: 1 / -1;
  }
  
  /* 按钮跨越两列 */
  .btn-full {
    grid-column: 1 / -1;
    max-width: 400px;
    justify-self: center;
  }
  
  .register-footer {
    grid-column: 1 / -1;
    margin-top: var(--space-6);
  }
  
  .form-control {
    padding: var(--space-4);
    font-size: 1.125rem;
  }
  
  .btn {
    padding: var(--space-4) var(--space-8);
    font-size: 1.125rem;
    min-height: 56px;
  }
}

/* 大屏幕 (1200px - 1599px) */
@media (min-width: 1200px) and (max-width: 1599px) {
  .register-container {
    padding: var(--space-6);
  }
  
  .register-card {
    max-width: 1200px;
    padding: var(--space-10);
  }
  
  .register-title {
    font-size: 2.5rem;
  }
  
  .register-subtitle {
    font-size: 1.125rem;
  }
  
  .form-control {
    padding: var(--space-4);
    font-size: 1.125rem;
  }
  
  .password-toggle {
    min-width: 44px;
    min-height: 44px;
  }
  
  .btn {
    padding: var(--space-4) var(--space-6);
    font-size: 1.125rem;
    min-height: 52px;
  }
  
  .register-form {
    gap: var(--space-7);
  }
}

/* 中等屏幕 (768px - 1199px) */
@media (min-width: 768px) and (max-width: 1199px) {
  .register-container {
    padding: var(--space-5);
  }
  
  .register-card {
    max-width: 800px;
    padding: var(--space-8);
  }
  
  .register-title {
    font-size: 2.25rem;
  }
  
  .form-control {
    padding: var(--space-3) var(--space-4);
  }
  
  .btn {
    min-height: 50px;
  }
  
  .register-form {
    gap: var(--space-6);
  }
}

/* 小屏幕平板 (640px - 767px) */
@media (min-width: 640px) and (max-width: 767px) {
  .register-container {
    padding: var(--space-4);
  }
  
  .register-card {
    max-width: 550px;
    padding: var(--space-6);
  }
  
  .register-title {
    font-size: 1.875rem;
  }
  
  .register-header {
    margin-bottom: var(--space-6);
  }
  
  .form-control {
    padding: var(--space-3);
  }
  
  .btn {
    min-height: 48px;
  }
  
  .register-form {
    gap: var(--space-5);
  }
}

/* 手机端 (320px - 639px) */
@media (max-width: 639px) {
  .register-container {
    padding: var(--space-3);
    min-height: 100vh;
    min-height: 100dvh; /* 支持动态视口 */
  }
  
  .register-card {
    max-width: 100%;
    width: 100%;
    padding: var(--space-6);
    margin: 0;
    box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1);
  }
  
  .register-header {
    margin-bottom: var(--space-6);
  }
  
  .register-title {
    font-size: 1.75rem;
    line-height: 1.3;
  }
  
  .register-subtitle {
    font-size: var(--text-sm);
  }
  
  .register-form {
    gap: var(--space-4);
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
  
  .error-banner,
  .success-banner {
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
  
  .register-footer {
    margin-top: var(--space-5);
  }
  
  .invitation-hint {
    padding: var(--space-2);
    font-size: 0.8rem;
  }
  
  .hint-icon {
    width: 0.8rem;
    height: 0.8rem;
  }
}

/* 超小屏幕 (最小320px) */
@media (max-width: 379px) {
  .register-container {
    padding: var(--space-2);
  }
  
  .register-card {
    padding: var(--space-4);
    border-radius: var(--radius-md);
  }
  
  .register-title {
    font-size: 1.5rem;
  }
  
  .register-subtitle {
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
  
  .register-form {
    gap: var(--space-4);
  }
  
  .invitation-hint {
    padding: var(--space-2);
    font-size: 0.8rem;
  }
  
  .hint-icon {
    width: 0.8rem;
    height: 0.8rem;
  }
}

/* 横屏模式优化 */
@media (max-height: 650px) and (orientation: landscape) {
  .register-container {
    padding: var(--space-2) var(--space-4);
    align-items: flex-start;
  }
  
  .register-card {
    padding: var(--space-4) var(--space-6);
    max-height: 95vh;
    overflow-y: auto;
    margin-top: var(--space-2);
    margin-bottom: var(--space-2);
  }
  
  .register-header {
    margin-bottom: var(--space-3);
  }
  
  .register-title {
    font-size: 1.5rem;
    margin-bottom: var(--space-1);
  }
  
  .register-subtitle {
    font-size: 0.875rem;
  }
  
  .register-form {
    gap: var(--space-3);
  }
  
  .form-group {
    gap: var(--space-1);
  }
  
  .register-footer {
    margin-top: var(--space-3);
  }
}

/* 极低高度优化 (手机横屏等) */
@media (max-height: 480px) and (orientation: landscape) {
  .register-container {
    align-items: flex-start;
    padding: var(--space-1) var(--space-3);
  }
  
  .register-card {
    padding: var(--space-3) var(--space-4);
    max-height: 98vh;
    overflow-y: auto;
    margin: var(--space-1) 0;
  }
  
  .register-header {
    margin-bottom: var(--space-2);
  }
  
  .register-title {
    font-size: 1.25rem;
    margin-bottom: 0;
  }
  
  .register-subtitle {
    font-size: 0.8rem;
  }
  
  .register-form {
    gap: var(--space-2);
  }
  
  .form-control {
    padding: var(--space-2);
    min-height: 40px;
  }
  
  .btn {
    min-height: 40px;
    padding: var(--space-2) var(--space-3);
  }
  
  .register-footer {
    margin-top: var(--space-2);
  }
}

/* 高分辨率屏幕优化 */
@media (-webkit-min-device-pixel-ratio: 2), (min-resolution: 192dpi) {
  .register-card {
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
  .register-card,
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
  .register-container {
    background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
  }
  
  .register-card {
    background: #1e293b;
    color: #e2e8f0;
    box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.4);
  }
  
  .register-title {
    color: #f8fafc;
  }
  
  .register-subtitle {
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
  
  .success-banner {
    background-color: #064e3b;
    border-color: #047857;
    color: #6ee7b7;
  }
  
  .error-banner {
    background-color: #7f1d1d;
    border-color: #dc2626;
    color: #fca5a5;
  }
}

/* 打印样式 */
@media print {
  .register-container {
    background: white;
    padding: 0;
  }
  
  .register-card {
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
  
  .success-banner,
  .error-banner {
    border: 1px solid #000;
    background: transparent;
    color: #000;
  }
}

/* 表单验证状态视觉增强 */
.form-control:valid:not(:placeholder-shown) {
  border-color: #10b981;
}

.form-control:invalid:not(:placeholder-shown) {
  border-color: var(--error-color);
}

/* Focus-visible for better keyboard navigation */
.btn:focus-visible,
.password-toggle:focus-visible,
.link:focus-visible {
  outline: 2px solid var(--primary-color);
  outline-offset: 2px;
}

/* 触摸设备优化 */
@media (hover: none) and (pointer: coarse) {
  .btn {
    min-height: 48px;
  }
  
  .password-toggle {
    min-width: 48px;
    min-height: 48px;
  }
  
  .form-control {
    min-height: 48px;
    font-size: 16px; /* 防止iOS Safari自动缩放 */
  }
}
</style> 