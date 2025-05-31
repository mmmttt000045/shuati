/**
 * API 配置管理
 */

// 获取API基地址，优先使用环境变量，否则使用默认值
const getApiBaseUrl = (): string => {
  // Vite 环境变量必须以 VITE_ 开头才能在客户端使用
  const envBaseUrl = import.meta.env.VITE_API_BASE_URL;
  
  if (envBaseUrl) {
    // 确保移除末尾的斜杠
    return envBaseUrl.replace(/\/$/, '');
  }
  
  // 默认基地址（开发环境）
  return 'http://127.0.0.1:5051/api';
};

// 导出API基地址
export const API_BASE_URL = getApiBaseUrl();

// 导出认证API基地址 - 确保正确拼接
export const AUTH_API_BASE_URL = `${API_BASE_URL}/auth`;

// API配置对象
export const apiConfig = {
  baseUrl: API_BASE_URL,
  authBaseUrl: AUTH_API_BASE_URL,
  timeout: 30000, // 30秒超时
  retryAttempts: 3,
  retryDelay: 1000, // 1秒重试延迟
};

// 环境检查
export const isDevelopment = import.meta.env.DEV;
export const isProduction = import.meta.env.PROD;

// 日志配置
export const enableApiLogging = isDevelopment;

// 详细的配置日志
console.log('=== API配置详情 ===');
console.log('环境变量 VITE_API_BASE_URL:', import.meta.env.VITE_API_BASE_URL || '未设置');
console.log('计算后的API基地址:', API_BASE_URL);
console.log('认证API基地址:', AUTH_API_BASE_URL);
console.log('当前环境:', isDevelopment ? 'development' : 'production');
console.log('日志开启:', enableApiLogging);
console.log('==================');

// 验证URL格式
try {
  new URL(API_BASE_URL);
  console.log('✅ API基地址格式验证通过');
} catch (error) {
  console.error('❌ API基地址格式错误:', API_BASE_URL);
} 