/**
 * API 配置管理
 */

// API 配置
export const isDevelopment = import.meta.env.MODE === 'development';

// 配置API基地址
let baseUrl = import.meta.env.VITE_API_BASE_URL;

if (!baseUrl) {
  // 没有设置环境变量，使用默认值
  if (isDevelopment) {
    baseUrl = 'http://127.0.0.1:5051';
  } else {
    // 生产环境使用相对路径
    baseUrl = '';
  }
}

// 确保URL不以斜杠结尾
if (baseUrl.endsWith('/')) {
  baseUrl = baseUrl.slice(0, -1);
}

export const API_BASE_URL = `${baseUrl}`;
export const AUTH_API_BASE_URL = `${baseUrl}/auth`;

// 开发环境启用API日志
export const enableApiLogging = isDevelopment;

// 验证API配置
try {
  new URL(API_BASE_URL, window.location.origin);
} catch (error) {
  console.error('❌ API基地址格式错误:', API_BASE_URL);
}

// 环境检查
export const isProduction = import.meta.env.PROD;

// API配置对象
export const apiConfig = {
  baseUrl: API_BASE_URL,
  authUrl: AUTH_API_BASE_URL,
  timeout: 10000,
  enableLogging: enableApiLogging
};
