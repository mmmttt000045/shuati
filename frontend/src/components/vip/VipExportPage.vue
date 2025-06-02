<template>
  <div class="vip-export-content">
    <div class="container">
      <h1 class="page-title">错题导出</h1>
      
      <div class="export-options">
        <div class="option-card">
          <h3>📄 导出为 PDF</h3>
          <p>将错题整理成PDF格式，便于打印和离线学习</p>
          <div class="export-settings">
            <label class="checkbox-label">
              <input type="checkbox" v-model="exportOptions.includeAnswers" />
              <span>包含答案解析</span>
            </label>
            <label class="checkbox-label">
              <input type="checkbox" v-model="exportOptions.includeNotes" />
              <span>包含个人笔记</span>
            </label>
          </div>
          <button class="export-btn pdf-btn" @click="exportToPDF" :disabled="loading">
            <span v-if="loading">导出中...</span>
            <span v-else>📄 导出 PDF</span>
          </button>
        </div>
        
        <div class="option-card">
          <h3>📊 导出为 Excel</h3>
          <p>以表格形式导出错题数据，便于统计分析</p>
          <div class="export-settings">
            <label class="checkbox-label">
              <input type="checkbox" v-model="exportOptions.includeStatistics" />
              <span>包含统计信息</span>
            </label>
            <label class="checkbox-label">
              <input type="checkbox" v-model="exportOptions.groupBySubject" />
              <span>按科目分组</span>
            </label>
          </div>
          <button class="export-btn excel-btn" @click="exportToExcel" :disabled="loading">
            <span v-if="loading">导出中...</span>
            <span v-else">📊 导出 Excel</span>
          </button>
        </div>
        
        <div class="option-card">
          <h3>📝 导出为 Word</h3>
          <p>生成Word文档格式，便于编辑和分享</p>
          <div class="export-settings">
            <label class="checkbox-label">
              <input type="checkbox" v-model="exportOptions.includeImages" />
              <span>包含题目图片</span>
            </label>
            <label class="checkbox-label">
              <input type="checkbox" v-model="exportOptions.customTemplate" />
              <span>使用自定义模板</span>
            </label>
          </div>
          <button class="export-btn word-btn" @click="exportToWord" :disabled="loading">
            <span v-if="loading">导出中...</span>
            <span v-else>📝 导出 Word</span>
          </button>
        </div>
      </div>
      
      <div class="filter-section">
        <h2>筛选条件</h2>
        <div class="filter-grid">
          <div class="filter-item">
            <label>科目选择</label>
            <select v-model="filters.subject" class="filter-select">
              <option value="">全部科目</option>
              <option value="math">数学</option>
              <option value="physics">物理</option>
              <option value="chemistry">化学</option>
              <option value="english">英语</option>
            </select>
          </div>
          
          <div class="filter-item">
            <label>错误次数</label>
            <select v-model="filters.errorCount" class="filter-select">
              <option value="">不限</option>
              <option value="1">1次</option>
              <option value="2">2次</option>
              <option value="3+">3次以上</option>
            </select>
          </div>
          
          <div class="filter-item">
            <label>时间范围</label>
            <select v-model="filters.timeRange" class="filter-select">
              <option value="">全部时间</option>
              <option value="week">最近一周</option>
              <option value="month">最近一月</option>
              <option value="quarter">最近三月</option>
            </select>
          </div>
          
          <div class="filter-item">
            <label>难度等级</label>
            <select v-model="filters.difficulty" class="filter-select">
              <option value="">全部难度</option>
              <option value="easy">简单</option>
              <option value="medium">中等</option>
              <option value="hard">困难</option>
            </select>
          </div>
        </div>
      </div>
      
      <div class="preview-section">
        <h2>预览 ({{ filteredQuestions.length }} 道题)</h2>
        <div class="question-list">
          <div v-for="question in filteredQuestions.slice(0, 5)" :key="question.id" class="question-preview">
            <div class="question-header">
              <span class="question-number">{{ question.id }}</span>
              <span class="question-subject">{{ question.subject }}</span>
              <span class="error-count">错误 {{ question.errorCount }} 次</span>
            </div>
            <div class="question-content">
              {{ question.content.substring(0, 100) }}...
            </div>
          </div>
          
          <div v-if="filteredQuestions.length > 5" class="more-questions">
            还有 {{ filteredQuestions.length - 5 }} 道题...
          </div>
          
          <div v-if="filteredQuestions.length === 0" class="no-questions">
            没有符合条件的错题
          </div>
        </div>
      </div>
    </div>
    
    <!-- 全屏Loading -->
    <Loading v-if="loading" :text="exportStatus" :fullScreen="true" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import Loading from '@/components/common/Loading.vue'

const loading = ref(false)
const exportStatus = ref('正在导出...')

const exportOptions = ref({
  includeAnswers: true,
  includeNotes: false,
  includeStatistics: true,
  groupBySubject: true,
  includeImages: true,
  customTemplate: false
})

const filters = ref({
  subject: '',
  errorCount: '',
  timeRange: '',
  difficulty: ''
})

// 模拟错题数据
const allQuestions = ref([
  {
    id: 1,
    subject: '数学',
    content: '求函数 f(x) = x² + 2x + 1 的最小值',
    errorCount: 3,
    difficulty: 'medium',
    date: '2024-01-15'
  },
  {
    id: 2,
    subject: '物理',
    content: '一个质量为 2kg 的物体在水平面上受到 10N 的水平力作用',
    errorCount: 2,
    difficulty: 'hard',
    date: '2024-01-14'
  },
  {
    id: 3,
    subject: '化学',
    content: '计算 NaCl 在水中的溶解度',
    errorCount: 1,
    difficulty: 'easy',
    date: '2024-01-13'
  },
  {
    id: 4,
    subject: '英语',
    content: 'Choose the correct form of the verb in the following sentence',
    errorCount: 4,
    difficulty: 'medium',
    date: '2024-01-12'
  },
  {
    id: 5,
    subject: '数学',
    content: '证明：对于任意实数 a, b, c，有 a² + b² + c² ≥ ab + bc + ca',
    errorCount: 5,
    difficulty: 'hard',
    date: '2024-01-11'
  }
])

const filteredQuestions = computed(() => {
  return allQuestions.value.filter(question => {
    if (filters.value.subject && question.subject !== filters.value.subject) return false
    if (filters.value.errorCount) {
      if (filters.value.errorCount === '3+' && question.errorCount < 3) return false
      if (filters.value.errorCount !== '3+' && question.errorCount !== parseInt(filters.value.errorCount)) return false
    }
    if (filters.value.difficulty && question.difficulty !== filters.value.difficulty) return false
    return true
  })
})

const exportToPDF = async () => {
  loading.value = true
  exportStatus.value = '正在生成PDF文档...'
  try {
    // 模拟导出过程
    await new Promise(resolve => setTimeout(resolve, 2000))
    // 这里应该是实际的导出逻辑
    console.log('导出PDF')
  } catch (error) {
    console.error('导出失败:', error)
  } finally {
    loading.value = false
  }
}

const exportToExcel = async () => {
  loading.value = true
  exportStatus.value = '正在生成Excel表格...'
  try {
    // 模拟导出过程
    await new Promise(resolve => setTimeout(resolve, 2000))
    // 这里应该是实际的导出逻辑
    console.log('导出Excel')
  } catch (error) {
    console.error('导出失败:', error)
  } finally {
    loading.value = false
  }
}

const exportToWord = async () => {
  loading.value = true
  exportStatus.value = '正在生成Word文档...'
  try {
    // 模拟导出过程
    await new Promise(resolve => setTimeout(resolve, 2000))
    // 这里应该是实际的导出逻辑
    console.log('导出Word')
  } catch (error) {
    console.error('导出失败:', error)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.vip-export-content {
  width: 100%;
  min-height: calc(100vh - 64px);
  background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
  padding: 2rem 0;
  overflow-y: auto;
}

.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 2rem;
}

.page-title {
  text-align: center;
  margin-bottom: 2rem;
  color: #2c3e50;
  font-size: 2rem;
  font-weight: 600;
}

.export-options {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 1.5rem;
  margin-bottom: 3rem;
}

.option-card {
  background: white;
  border-radius: 12px;
  padding: 1.5rem;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  transition: transform 0.2s, box-shadow 0.2s;
}

.option-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 15px rgba(0, 0, 0, 0.15);
}

.option-card h3 {
  margin: 0 0 0.5rem 0;
  color: #2d3748;
  font-size: 1.2rem;
  font-weight: 600;
}

.option-card p {
  margin: 0 0 1rem 0;
  color: #4a5568;
  font-size: 0.9rem;
  line-height: 1.5;
}

.export-settings {
  margin-bottom: 1.5rem;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
  cursor: pointer;
  font-size: 0.9rem;
  color: #4a5568;
}

.checkbox-label input[type="checkbox"] {
  width: 16px;
  height: 16px;
}

.export-btn {
  width: 100%;
  padding: 0.75rem 1rem;
  border: none;
  border-radius: 8px;
  font-size: 1rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.export-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.pdf-btn {
  background: linear-gradient(135deg, #ff6b6b 0%, #ee5a24 100%);
  color: white;
}

.pdf-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 8px rgba(238, 90, 36, 0.3);
}

.excel-btn {
  background: linear-gradient(135deg, #26de81 0%, #20bf6b 100%);
  color: white;
}

.excel-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 8px rgba(32, 191, 107, 0.3);
}

.word-btn {
  background: linear-gradient(135deg, #4834d4 0%, #686de0 100%);
  color: white;
}

.word-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 8px rgba(104, 109, 224, 0.3);
}

.filter-section, .preview-section {
  background: white;
  border-radius: 12px;
  padding: 2rem;
  margin-bottom: 2rem;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.filter-section h2, .preview-section h2 {
  margin: 0 0 1.5rem 0;
  color: #2d3748;
  font-size: 1.5rem;
  font-weight: 600;
}

.filter-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
}

.filter-item {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.filter-item label {
  font-size: 0.9rem;
  font-weight: 500;
  color: #4a5568;
}

.filter-select {
  padding: 0.5rem;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  font-size: 0.9rem;
  background: white;
}

.filter-select:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.question-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.question-preview {
  padding: 1rem;
  background: #f7fafc;
  border-radius: 8px;
  border-left: 4px solid #667eea;
}

.question-header {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 0.5rem;
}

.question-number {
  background: #667eea;
  color: white;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-size: 0.8rem;
  font-weight: 600;
}

.question-subject {
  background: #e2e8f0;
  color: #4a5568;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-size: 0.8rem;
}

.error-count {
  background: #fed7d7;
  color: #c53030;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-size: 0.8rem;
}

.question-content {
  color: #4a5568;
  font-size: 0.9rem;
  line-height: 1.5;
}

.more-questions {
  text-align: center;
  padding: 1rem;
  color: #718096;
  font-style: italic;
}

.no-questions {
  text-align: center;
  padding: 2rem;
  color: #718096;
  font-style: italic;
}

@media (max-width: 768px) {
  .container {
    padding: 1rem;
  }
  
  .export-options {
    grid-template-columns: 1fr;
  }
  
  .filter-grid {
    grid-template-columns: 1fr;
  }
  
  .question-header {
    flex-wrap: wrap;
  }
}
</style> 