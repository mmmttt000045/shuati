<template>
  <div class="container">
    <h1 class="page-title">题目练习</h1>

    <div v-if="messages.length > 0" class="messages">
      <div v-for="(message, index) in messages" :key="index" :class="['message', message.category]">
        {{ message.text }}
      </div>
    </div>

    <div v-if="loading" class="loading">加载中...</div>

    <div v-else-if="Object.keys(subjects).length === 0" class="empty-state">暂无可用的题目文件</div>

    <div v-else class="subjects-grid">
      <!-- 科目选择列表 -->
      <div v-if="!selectedSubject" class="subjects-list">
        <div
          v-for="(files, subject) in subjects"
          :key="subject"
          class="subject-card"
          @click="selectSubject(subject)"
        >
          <h2 class="subject-title">{{ subject }}</h2>
          <div class="subject-info">
            <span class="subject-count">{{ files.length }}个题库</span>
            <span class="subject-total">共{{ getTotalQuestions(files) }}题</span>
          </div>
        </div>
      </div>

      <!-- 题库选择列表 -->
      <div v-else class="files-container">
        <div class="back-button-container">
          <button class="back-button" @click="selectedSubject = ''">
            <span class="back-arrow">←</span> 返回科目列表
          </button>
        </div>

        <h2 class="selected-subject-title">{{ selectedSubject }}</h2>
        <div class="files-list">
          <button
            v-for="file in subjects[selectedSubject]"
            :key="file.key"
            class="file-button"
            @click="startPractice(selectedSubject, file.key)"
          >
            <div class="file-info">
              <span class="file-name">{{ file.display }}</span>
              <span class="file-count">({{ file.count }}题)</span>
            </div>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script lang="ts" setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { apiService } from '@/services/api'
import type { FlashMessage, SubjectFile } from '@/types'

const router = useRouter()
const subjects = ref<Record<string, SubjectFile[]>>({})
const selectedSubject = ref<string>('')
const messages = ref<FlashMessage[]>([])
const loading = ref(false)

const getTotalQuestions = (files: SubjectFile[]) => {
  return files.reduce((total, file) => total + file.count, 0)
}

const selectSubject = (subject: string) => {
  selectedSubject.value = subject
}

const startPractice = async (subject: string, fileName: string) => {
  loading.value = true
  
  try {
    // 检查是否已有同一文件的活跃会话
    const sessionStatus = await apiService.checkSessionStatus()
    
    if (sessionStatus.active && 
        sessionStatus.file_info && 
        sessionStatus.file_info.key === fileName && 
        !sessionStatus.completed) {
      
      // 询问用户是否要继续之前的进度还是重新开始
      const shouldContinue = confirm(
        `检测到你之前正在练习《${sessionStatus.file_info.display}》(第${sessionStatus.progress?.current}/${sessionStatus.progress?.total}题)。\n\n点击"确定"继续之前的进度，点击"取消"重新开始。`
      )
      
      if (shouldContinue) {
        // 继续之前的练习
        router.push({
          name: 'practice',
          query: { subject, file: fileName }
        })
        return
      } else {
        // 重新开始练习
        const startResponse = await apiService.startPractice(subject, fileName, true)
        if (!startResponse.success) {
          throw new Error(startResponse.message)
        }
      }
    }
    
    // 正常启动练习
    router.push({
      name: 'practice',
      query: { subject, file: fileName }
    })
    
  } catch (error) {
    console.error('Error starting practice:', error)
    messages.value.push({
      category: 'error',
      text: error instanceof Error ? error.message : '启动练习失败'
    })
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  loading.value = true
  try {
    const response = await apiService.getFileOptions()
    subjects.value = response.subjects
    if (response.message) {
      messages.value.push({
        category: 'info',
        text: response.message,
      })
    }
  } catch (error) {
    console.error('Error fetching subjects:', error)
    messages.value.push({
      category: 'error',
      text: error instanceof Error ? error.message : '获取科目列表失败',
    })
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem;
  min-height: 100vh;
  background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
}

.page-title {
  text-align: center;
  margin-bottom: 4rem;
  color: #1e293b;
  font-size: 2.75rem;
  font-weight: 800;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  position: relative;
  letter-spacing: -0.5px;
}

.page-title::after {
  content: '';
  position: absolute;
  bottom: -1rem;
  left: 50%;
  transform: translateX(-50%);
  width: 80px;
  height: 4px;
  background: linear-gradient(to right, #3b82f6, #2563eb);
  border-radius: 2px;
}

.messages {
  margin-bottom: 2rem;
  max-width: 800px;
  margin-left: auto;
  margin-right: auto;
}

.message {
  padding: 1.25rem 1.75rem;
  margin-bottom: 1rem;
  border-radius: 12px;
  font-weight: 500;
  animation: slideIn 0.3s ease-out;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

@keyframes slideIn {
  from {
    transform: translateY(-10px);
    opacity: 0;
  }
  to {
    transform: translateY(0);
    opacity: 1;
  }
}

.message.error {
  background-color: #fef2f2;
  color: #dc2626;
  border-left: 4px solid #dc2626;
}

.message.info {
  background-color: #f0f9ff;
  color: #0369a1;
  border-left: 4px solid #0369a1;
}

.loading {
  text-align: center;
  padding: 4rem;
  color: #64748b;
  font-size: 1.2rem;
  font-weight: 500;
}

.empty-state {
  text-align: center;
  padding: 4rem 2rem;
  background-color: white;
  border-radius: 16px;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
  color: #64748b;
  font-size: 1.1rem;
  max-width: 600px;
  margin: 0 auto;
}

.subjects-grid {
  animation: fadeIn 0.4s ease-out;
}

.subjects-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 2rem;
  width: 100%;
  padding: 1rem;
}

.subject-card {
  background-color: white;
  border-radius: 16px;
  padding: 2rem;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
  cursor: pointer;
  transition: all 0.3s ease;
  border: 2px solid transparent;
  position: relative;
  overflow: hidden;
}

.subject-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
  background: linear-gradient(to right, #3b82f6, #2563eb);
  opacity: 0;
  transition: opacity 0.3s ease;
}

.subject-card:hover {
  transform: translateY(-6px);
  box-shadow:
    0 20px 25px -5px rgba(0, 0, 0, 0.1),
    0 10px 10px -5px rgba(0, 0, 0, 0.04);
}

.subject-card:hover::before {
  opacity: 1;
}

.subject-info {
  display: flex;
  justify-content: space-between;
  margin-top: 1.5rem;
  padding-top: 1rem;
  border-top: 1px solid #e2e8f0;
}

.subject-count,
.subject-total {
  background-color: #f8fafc;
  padding: 0.5rem 1rem;
  border-radius: 999px;
  color: #475569;
  font-size: 0.9rem;
  font-weight: 500;
  transition: all 0.2s ease;
}

.subject-card:hover .subject-count,
.subject-card:hover .subject-total {
  background-color: #f1f5f9;
  color: #3b82f6;
}

.subject-title {
  font-size: 1.5rem;
  font-weight: 600;
  color: #1e293b;
  margin-bottom: 0.5rem;
}

.files-container {
  width: 100%;
  max-width: 800px;
  margin: 0 auto;
  padding: 2rem;
  background-color: white;
  border-radius: 20px;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
}

.back-button-container {
  margin-bottom: 2.5rem;
}

.back-button {
  display: flex;
  align-items: center;
  padding: 0.875rem 1.75rem;
  background-color: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  color: #334155;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  font-size: 1.1rem;
}

.back-button:hover {
  background-color: #f1f5f9;
  transform: translateX(-4px);
  color: #3b82f6;
  border-color: #3b82f6;
}

.back-arrow {
  margin-right: 0.75rem;
  font-size: 1.3rem;
  transition: transform 0.2s ease;
}

.back-button:hover .back-arrow {
  transform: translateX(-4px);
}

.selected-subject-title {
  font-size: 2.25rem;
  color: #1e293b;
  margin-bottom: 2.5rem;
  padding-bottom: 1rem;
  border-bottom: 2px solid #e2e8f0;
  font-weight: 700;
}

.files-list {
  display: grid;
  gap: 1rem;
}

.file-button {
  width: 100%;
  padding: 1.25rem 1.75rem;
  background-color: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  cursor: pointer;
  text-align: left;
  transition: all 0.2s ease;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.file-button:hover {
  background-color: #f8fafc;
  border-color: #3b82f6;
  transform: translateY(-2px);
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
}

.file-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.file-name {
  font-weight: 500;
  color: #334155;
  font-size: 1.1rem;
}

.file-count {
  color: #64748b;
  font-size: 0.95rem;
  font-weight: 500;
  background-color: #f1f5f9;
  padding: 0.5rem 1rem;
  border-radius: 999px;
  transition: all 0.2s ease;
}

.file-button:hover .file-count {
  background-color: #e0f2fe;
  color: #0284c7;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@media (max-width: 768px) {
  .container {
    padding: 1rem;
  }

  .page-title {
    font-size: 2rem;
    margin-bottom: 3rem;
  }

  .subjects-list {
    grid-template-columns: 1fr;
    gap: 1.5rem;
    padding: 0.5rem;
  }

  .files-container {
    padding: 1.5rem;
  }

  .selected-subject-title {
    font-size: 1.75rem;
  }

  .file-button {
    padding: 1rem 1.25rem;
  }

  .subject-card {
    padding: 1.5rem;
  }
}
</style>
