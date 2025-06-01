<template>
  <div class="vip-collections-content">
    <Loading v-if="loading" text="正在加载错题集..." :fullScreen="true" />
    
    <div v-else class="container">
      <h1 class="page-title">错题集管理</h1>
      
      <div class="actions-bar">
        <button class="create-btn" @click="showCreateModal = true">
          ➕ 创建新错题集
        </button>
        <div class="search-box">
          <input 
            type="text" 
            v-model="searchQuery" 
            placeholder="搜索错题集..."
            class="search-input"
          />
          <span class="search-icon">🔍</span>
        </div>
      </div>
      
      <div class="collections-grid">
        <div 
          v-for="collection in filteredCollections" 
          :key="collection.id" 
          class="collection-card"
        >
          <div class="collection-header">
            <h3 class="collection-title">{{ collection.name }}</h3>
            <div class="collection-actions">
              <button class="action-btn edit-btn" @click="editCollection(collection)">
                ✏️
              </button>
              <button class="action-btn delete-btn" @click="deleteCollection(collection.id)">
                🗑️
              </button>
            </div>
          </div>
          
          <div class="collection-info">
            <div class="info-item">
              <span class="info-label">题目数量</span>
              <span class="info-value">{{ collection.questionCount }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">创建时间</span>
              <span class="info-value">{{ collection.createdAt }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">最后更新</span>
              <span class="info-value">{{ collection.updatedAt }}</span>
            </div>
          </div>
          
          <div class="collection-description">
            {{ collection.description || '暂无描述' }}
          </div>
          
          <div class="collection-tags">
            <span 
              v-for="tag in collection.tags" 
              :key="tag" 
              class="tag"
            >
              {{ tag }}
            </span>
          </div>
          
          <div class="collection-footer">
            <button class="view-btn" @click="viewCollection(collection.id)">
              📖 查看详情
            </button>
            <button class="practice-btn" @click="practiceCollection(collection.id)">
              🎯 开始练习
            </button>
          </div>
        </div>
        
        <div v-if="filteredCollections.length === 0" class="empty-state">
          <div class="empty-icon">📚</div>
          <h3>暂无错题集</h3>
          <p>创建您的第一个错题集，开始整理错题吧！</p>
          <button class="create-btn" @click="showCreateModal = true">
            创建错题集
          </button>
        </div>
      </div>
      
      <!-- 创建/编辑错题集模态框 -->
      <div v-if="showCreateModal" class="modal-overlay" @click="closeModal">
        <div class="modal-content" @click.stop>
          <div class="modal-header">
            <h2>{{ editingCollection ? '编辑错题集' : '创建新错题集' }}</h2>
            <button class="close-btn" @click="closeModal">✕</button>
          </div>
          
          <div class="modal-body">
            <div class="form-group">
              <label>错题集名称</label>
              <input 
                type="text" 
                v-model="formData.name" 
                placeholder="请输入错题集名称"
                class="form-input"
              />
            </div>
            
            <div class="form-group">
              <label>描述</label>
              <textarea 
                v-model="formData.description" 
                placeholder="请输入错题集描述（可选）"
                class="form-textarea"
                rows="3"
              ></textarea>
            </div>
            
            <div class="form-group">
              <label>标签</label>
              <input 
                type="text" 
                v-model="tagInput" 
                @keyup.enter="addTag"
                placeholder="输入标签后按回车添加"
                class="form-input"
              />
              <div class="tags-container">
                <span 
                  v-for="(tag, index) in formData.tags" 
                  :key="index" 
                  class="tag editable"
                >
                  {{ tag }}
                  <button @click="removeTag(index)" class="tag-remove">✕</button>
                </span>
              </div>
            </div>
          </div>
          
          <div class="modal-footer">
            <button class="cancel-btn" @click="closeModal">取消</button>
            <button class="save-btn" @click="saveCollection">
              {{ editingCollection ? '保存' : '创建' }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import Loading from '@/components/Loading.vue'

const searchQuery = ref('')
const showCreateModal = ref(false)
const editingCollection = ref<any>(null)
const tagInput = ref('')

const formData = ref({
  name: '',
  description: '',
  tags: [] as string[]
})

// 添加loading状态
const loading = ref(true)

// 模拟错题集数据
const collections = ref([
  {
    id: 1,
    name: '数学错题集',
    description: '高等数学相关的错题整理',
    questionCount: 25,
    createdAt: '2024-01-10',
    updatedAt: '2024-01-15',
    tags: ['数学', '高等数学', '微积分']
  },
  {
    id: 2,
    name: '物理力学专题',
    description: '力学部分的重点难题',
    questionCount: 18,
    createdAt: '2024-01-08',
    updatedAt: '2024-01-12',
    tags: ['物理', '力学', '牛顿定律']
  },
  {
    id: 3,
    name: '英语语法错题',
    description: '语法相关的错题收集',
    questionCount: 32,
    createdAt: '2024-01-05',
    updatedAt: '2024-01-14',
    tags: ['英语', '语法', '时态']
  },
  {
    id: 4,
    name: '化学反应方程式',
    description: '化学反应方程式配平和计算',
    questionCount: 15,
    createdAt: '2024-01-03',
    updatedAt: '2024-01-11',
    tags: ['化学', '反应方程式', '配平']
  }
])

const filteredCollections = computed(() => {
  if (!searchQuery.value) return collections.value
  
  return collections.value.filter(collection => 
    collection.name.toLowerCase().includes(searchQuery.value.toLowerCase()) ||
    collection.description.toLowerCase().includes(searchQuery.value.toLowerCase()) ||
    collection.tags.some(tag => tag.toLowerCase().includes(searchQuery.value.toLowerCase()))
  )
})

const editCollection = (collection: any) => {
  editingCollection.value = collection
  formData.value = {
    name: collection.name,
    description: collection.description,
    tags: [...collection.tags]
  }
  showCreateModal.value = true
}

const deleteCollection = (id: number) => {
  if (confirm('确定要删除这个错题集吗？')) {
    const index = collections.value.findIndex(c => c.id === id)
    if (index > -1) {
      collections.value.splice(index, 1)
    }
  }
}

const viewCollection = (id: number) => {
  // 这里可以跳转到错题集详情页面
  alert(`查看错题集 ${id} 的详情`)
}

const practiceCollection = (id: number) => {
  // 这里可以开始练习错题集
  alert(`开始练习错题集 ${id}`)
}

const addTag = () => {
  const tag = tagInput.value.trim()
  if (tag && !formData.value.tags.includes(tag)) {
    formData.value.tags.push(tag)
    tagInput.value = ''
  }
}

const removeTag = (index: number) => {
  formData.value.tags.splice(index, 1)
}

const saveCollection = () => {
  if (!formData.value.name.trim()) {
    alert('请输入错题集名称')
    return
  }
  
  if (editingCollection.value) {
    // 编辑现有错题集
    const index = collections.value.findIndex(c => c.id === editingCollection.value.id)
    if (index > -1) {
      collections.value[index] = {
        ...collections.value[index],
        name: formData.value.name,
        description: formData.value.description,
        tags: formData.value.tags,
        updatedAt: new Date().toISOString().split('T')[0]
      }
    }
  } else {
    // 创建新错题集
    const newCollection = {
      id: Date.now(),
      name: formData.value.name,
      description: formData.value.description,
      questionCount: 0,
      createdAt: new Date().toISOString().split('T')[0],
      updatedAt: new Date().toISOString().split('T')[0],
      tags: formData.value.tags
    }
    collections.value.unshift(newCollection)
  }
  
  closeModal()
}

const closeModal = () => {
  showCreateModal.value = false
  editingCollection.value = null
  formData.value = {
    name: '',
    description: '',
    tags: []
  }
  tagInput.value = ''
}

// 在onMounted中添加数据加载逻辑
onMounted(async () => {
  loading.value = true
  try {
    // 模拟API调用延迟
    await new Promise(resolve => setTimeout(resolve, 1200))
    // 这里可以调用API获取真实的错题集数据
    console.log('VIP Collections loaded')
  } catch (error) {
    console.error('加载错题集失败:', error)
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.vip-collections-content {
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

.actions-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
  gap: 1rem;
}

.create-btn {
  padding: 0.75rem 1.5rem;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 1rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.create-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 8px rgba(102, 126, 234, 0.3);
}

.search-box {
  position: relative;
  max-width: 300px;
  flex: 1;
}

.search-input {
  width: 100%;
  padding: 0.75rem 2.5rem 0.75rem 1rem;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-size: 0.9rem;
  background: white;
}

.search-input:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.search-icon {
  position: absolute;
  right: 0.75rem;
  top: 50%;
  transform: translateY(-50%);
  color: #718096;
}

.collections-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  gap: 1.5rem;
}

.collection-card {
  background: white;
  border-radius: 12px;
  padding: 1.5rem;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  transition: transform 0.2s, box-shadow 0.2s;
}

.collection-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 15px rgba(0, 0, 0, 0.15);
}

.collection-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1rem;
}

.collection-title {
  margin: 0;
  color: #2d3748;
  font-size: 1.2rem;
  font-weight: 600;
  flex: 1;
}

.collection-actions {
  display: flex;
  gap: 0.5rem;
}

.action-btn {
  width: 32px;
  height: 32px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.9rem;
  transition: all 0.2s;
}

.edit-btn {
  background: #e2e8f0;
  color: #4a5568;
}

.edit-btn:hover {
  background: #cbd5e0;
}

.delete-btn {
  background: #fed7d7;
  color: #c53030;
}

.delete-btn:hover {
  background: #fbb6ce;
}

.collection-info {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(100px, 1fr));
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.info-item {
  text-align: center;
  padding: 0.5rem;
  background: #f7fafc;
  border-radius: 6px;
}

.info-label {
  display: block;
  font-size: 0.75rem;
  color: #718096;
  margin-bottom: 0.25rem;
}

.info-value {
  display: block;
  font-size: 0.9rem;
  font-weight: 600;
  color: #2d3748;
}

.collection-description {
  color: #4a5568;
  font-size: 0.9rem;
  line-height: 1.5;
  margin-bottom: 1rem;
  min-height: 1.5rem;
}

.collection-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.tag {
  padding: 0.25rem 0.5rem;
  background: #e2e8f0;
  color: #4a5568;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 500;
}

.tag.editable {
  background: #667eea;
  color: white;
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

.tag-remove {
  background: none;
  border: none;
  color: white;
  cursor: pointer;
  font-size: 0.7rem;
  padding: 0;
  width: 14px;
  height: 14px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.tag-remove:hover {
  background: rgba(255, 255, 255, 0.2);
}

.collection-footer {
  display: flex;
  gap: 0.5rem;
}

.view-btn, .practice-btn {
  flex: 1;
  padding: 0.5rem;
  border: none;
  border-radius: 6px;
  font-size: 0.9rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.view-btn {
  background: #e2e8f0;
  color: #4a5568;
}

.view-btn:hover {
  background: #cbd5e0;
}

.practice-btn {
  background: linear-gradient(135deg, #26de81 0%, #20bf6b 100%);
  color: white;
}

.practice-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 2px 4px rgba(32, 191, 107, 0.3);
}

.empty-state {
  grid-column: 1 / -1;
  text-align: center;
  padding: 3rem;
  background: white;
  border-radius: 12px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.empty-icon {
  font-size: 4rem;
  margin-bottom: 1rem;
}

.empty-state h3 {
  margin: 0 0 0.5rem 0;
  color: #2d3748;
  font-size: 1.5rem;
}

.empty-state p {
  margin: 0 0 1.5rem 0;
  color: #718096;
}

/* 模态框样式 */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: white;
  border-radius: 12px;
  width: 90%;
  max-width: 500px;
  max-height: 90vh;
  overflow-y: auto;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.5rem;
  border-bottom: 1px solid #e2e8f0;
}

.modal-header h2 {
  margin: 0;
  color: #2d3748;
  font-size: 1.5rem;
}

.close-btn {
  background: none;
  border: none;
  font-size: 1.5rem;
  color: #718096;
  cursor: pointer;
  padding: 0;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.close-btn:hover {
  background: #f7fafc;
}

.modal-body {
  padding: 1.5rem;
}

.form-group {
  margin-bottom: 1.5rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  color: #4a5568;
  font-weight: 500;
}

.form-input, .form-textarea {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  font-size: 0.9rem;
  box-sizing: border-box;
}

.form-input:focus, .form-textarea:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.tags-container {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-top: 0.5rem;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 1rem;
  padding: 1.5rem;
  border-top: 1px solid #e2e8f0;
}

.cancel-btn, .save-btn {
  padding: 0.75rem 1.5rem;
  border: none;
  border-radius: 6px;
  font-size: 0.9rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.cancel-btn {
  background: #e2e8f0;
  color: #4a5568;
}

.cancel-btn:hover {
  background: #cbd5e0;
}

.save-btn {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.save-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 2px 4px rgba(102, 126, 234, 0.3);
}

@media (max-width: 768px) {
  .container {
    padding: 1rem;
  }
  
  .actions-bar {
    flex-direction: column;
    align-items: stretch;
  }
  
  .search-box {
    max-width: none;
  }
  
  .collections-grid {
    grid-template-columns: 1fr;
  }
  
  .collection-info {
    grid-template-columns: 1fr;
  }
  
  .collection-footer {
    flex-direction: column;
  }
}
</style> 