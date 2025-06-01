<template>
  <div class="system-control-content">
    <!-- 统计概览 -->
    <div class="stats-overview" v-if="stats">
      <div class="stat-card">
        <div class="stat-icon">👥</div>
        <div class="stat-content">
          <div class="stat-number">{{ stats.users.total }}</div>
          <div class="stat-label">总用户数</div>
          <div class="stat-detail">活跃: {{ stats.users.active }}</div>
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-icon">🎫</div>
        <div class="stat-content">
          <div class="stat-number">{{ stats.invitations.unused }}</div>
          <div class="stat-label">可用邀请码</div>
          <div class="stat-detail">已用: {{ stats.invitations.used || 0 }} / 总计: {{ stats.invitations.total }}</div>
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-icon">📚</div>
        <div class="stat-content">
          <div class="stat-number">{{ stats.subjects.total_questions }}</div>
          <div class="stat-label">题目总数</div>
          <div class="stat-detail">{{ stats.subjects.total_files }}个文件</div>
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-icon">🛡️</div>
        <div class="stat-content">
          <div class="stat-number">{{ stats.users.admins }}</div>
          <div class="stat-label">管理员</div>
          <div class="stat-detail">VIP: {{ stats.users.vips }}</div>
        </div>
      </div>
    </div>

    <!-- 功能选项卡 -->
    <div class="control-tabs">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        :class="['tab-button', { active: activeTab === tab.key }]"
        @click="switchTab(tab.key)"
      >
        <span class="tab-icon">{{ tab.icon }}</span>
        <span class="tab-text">{{ tab.label }}</span>
      </button>
    </div>

    <!-- 用户管理 -->
    <div v-if="activeTab === 'users'" class="control-section">
      <div class="section-header">
        <h2 class="section-title">👥 用户管理</h2>
        <div class="section-actions">
          <button class="refresh-btn" @click="() => loadUsers()" :disabled="loading">
            <span class="btn-icon">🔄</span>
            刷新列表
          </button>
        </div>
      </div>

      <!-- 搜索和筛选区域 -->
      <div class="search-controls">
        <div class="search-group">
          <div class="search-input-wrapper">
            <input
              type="text"
              class="search-input"
              placeholder="搜索用户名..."
              :value="userSearchParams.search"
              @input="handleSearch(($event.target as HTMLInputElement).value)"
            >
            <button 
              v-if="userSearchParams.search"
              class="clear-search-btn"
              @click="clearSearch"
              title="清除搜索"
            >
              ✕
            </button>
          </div>
        </div>
        
        <div class="filter-group">
          <label class="filter-label">每页显示:</label>
          <select 
            class="page-size-select" 
            :value="userSearchParams.per_page"
            @change="changePageSize(parseInt(($event.target as HTMLSelectElement).value))"
          >
            <option value="10">10条</option>
            <option value="20">20条</option>
            <option value="50">50条</option>
            <option value="100">100条</option>
          </select>
        </div>
      </div>

      <Loading v-if="loading" />

      <div v-else-if="users.length === 0" class="empty-state">
        <div class="empty-icon">👤</div>
        <p>{{ userSearchParams.search ? '没有找到匹配的用户' : '暂无用户数据' }}</p>
      </div>

      <div v-else class="users-table-container">
        <table class="users-table">
          <thead>
            <tr>
              <th class="sortable-header" @click="handleSort('id')">
                ID
                <span class="sort-indicator" v-if="userSearchParams.order_by === 'id'">
                  {{ userSearchParams.order_dir === 'asc' ? '↑' : '↓' }}
                </span>
              </th>
              <th class="sortable-header" @click="handleSort('username')">
                用户名
                <span class="sort-indicator" v-if="userSearchParams.order_by === 'username'">
                  {{ userSearchParams.order_dir === 'asc' ? '↑' : '↓' }}
                </span>
              </th>
              <th class="sortable-header" @click="handleSort('model')">
                权限等级
                <span class="sort-indicator" v-if="userSearchParams.order_by === 'model'">
                  {{ userSearchParams.order_dir === 'asc' ? '↑' : '↓' }}
                </span>
              </th>
              <th>状态</th>
              <th class="sortable-header" @click="handleSort('created_at')">
                注册时间
                <span class="sort-indicator" v-if="userSearchParams.order_by === 'created_at'">
                  {{ userSearchParams.order_dir === 'asc' ? '↑' : '↓' }}
                </span>
              </th>
              <th class="sortable-header" @click="handleSort('last_time_login')">
                最后登录
                <span class="sort-indicator" v-if="userSearchParams.order_by === 'last_time_login'">
                  {{ userSearchParams.order_dir === 'asc' ? '↑' : '↓' }}
                </span>
              </th>
              <th>邀请码</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="user in users" :key="user.id" :class="{ disabled: !user.is_enabled }">
              <td>{{ user.id }}</td>
              <td class="username-cell">
                <span class="username">{{ user.username }}</span>
              </td>
              <td>
                <select
                  :value="user.model"
                  @change="updateUserModel(user.id, parseInt(($event.target as HTMLSelectElement).value))"
                  class="model-select"
                  :disabled="user.id === currentUserId"
                >
                  <option value="0">普通用户</option>
                  <option value="5">VIP用户</option>
                  <option value="10">ROOT用户</option>
                </select>
              </td>
              <td>
                <span :class="['status-badge', user.is_enabled ? 'status-active' : 'status-disabled']">
                  {{ user.is_enabled ? '启用' : '禁用' }}
                </span>
              </td>
              <td class="date-cell">{{ formatDate(user.created_at) }}</td>
              <td class="date-cell">
                <span :class="['last-login', getLastLoginClass(user.last_time_login)]">
                  {{ formatLastLogin(user.last_time_login) }}
                </span>
              </td>
              <td class="invitation-cell">
                <code class="invitation-code">{{ user.invitation_code || 'N/A' }}</code>
              </td>
              <td class="actions-cell">
                <button
                  @click="toggleUser(user.id)"
                  :class="['action-btn', user.is_enabled ? 'btn-disable' : 'btn-enable']"
                  :disabled="user.id === currentUserId"
                >
                  {{ user.is_enabled ? '禁用' : '启用' }}
                </button>
              </td>
            </tr>
          </tbody>
        </table>

        <!-- 分页控件 -->
        <div v-if="userPagination" class="pagination-container">
          <div class="pagination-info">
            显示第 {{ (userPagination.page - 1) * userPagination.per_page + 1 }} - 
            {{ Math.min(userPagination.page * userPagination.per_page, userPagination.total) }} 条，
            共 {{ userPagination.total }} 条记录
          </div>
          
          <div class="pagination-controls">
            <button 
              class="pagination-btn"
              @click="goToPage(1)"
              :disabled="!userPagination.has_prev"
            >
              首页
            </button>
            <button 
              class="pagination-btn"
              @click="goToPage(userPagination.page - 1)"
              :disabled="!userPagination.has_prev"
            >
              上一页
            </button>
            
            <div class="page-numbers">
              <button
                v-for="page in getPageNumbers()"
                :key="page"
                :class="['page-number', { active: page === userPagination.page }]"
                @click="goToPage(page)"
              >
                {{ page }}
              </button>
            </div>
            
            <button 
              class="pagination-btn"
              @click="goToPage(userPagination.page + 1)"
              :disabled="!userPagination.has_next"
            >
              下一页
            </button>
            <button 
              class="pagination-btn"
              @click="goToPage(userPagination.total_pages)"
              :disabled="!userPagination.has_next"
            >
              末页
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 邀请码管理 -->
    <div v-if="activeTab === 'invitations'" class="control-section">
      <div class="section-header">
        <h2 class="section-title">🎫 邀请码管理</h2>
        <div class="section-actions">
          <button class="primary-btn" @click="showCreateInvitationDialog = true">
            <span class="btn-icon">➕</span>
            创建邀请码
          </button>
          <button class="refresh-btn" @click="() => loadInvitations()" :disabled="loading">
            <span class="btn-icon">🔄</span>
            刷新列表
          </button>
        </div>
      </div>

      <!-- 搜索和筛选区域 -->
      <div class="search-controls">
        <div class="search-group">
          <div class="search-input-wrapper">
            <input
              type="text"
              class="search-input"
              placeholder="搜索邀请码..."
              :value="invitationSearchParams.search"
              @input="handleInvitationSearch(($event.target as HTMLInputElement).value)"
            >
            <button 
              v-if="invitationSearchParams.search"
              class="clear-search-btn"
              @click="clearInvitationSearch"
              title="清除搜索"
            >
              ✕
            </button>
          </div>
        </div>
        
        <div class="filter-group">
          <label class="filter-label">每页显示:</label>
          <select 
            class="page-size-select" 
            :value="invitationSearchParams.per_page"
            @change="changeInvitationPageSize(parseInt(($event.target as HTMLSelectElement).value))"
          >
            <option value="10">10条</option>
            <option value="20">20条</option>
            <option value="50">50条</option>
            <option value="100">100条</option>
          </select>
        </div>
      </div>

      <Loading v-if="loading" />

      <div v-else-if="invitations.length === 0" class="empty-state">
        <div class="empty-icon">🎫</div>
        <p>{{ invitationSearchParams.search ? '没有找到匹配的邀请码' : '暂无邀请码' }}</p>
      </div>

      <div v-else class="invitations-table-container">
        <table class="invitations-table">
          <thead>
            <tr>
              <th class="sortable-header" @click="handleInvitationSort('id')">
                ID
                <span class="sort-indicator" v-if="invitationSearchParams.order_by === 'id'">
                  {{ invitationSearchParams.order_dir === 'asc' ? '↑' : '↓' }}
                </span>
              </th>
              <th>邀请码</th>
              <th>状态</th>
              <th>使用者</th>
              <th class="sortable-header" @click="handleInvitationSort('created_at')">
                创建时间
                <span class="sort-indicator" v-if="invitationSearchParams.order_by === 'created_at'">
                  {{ invitationSearchParams.order_dir === 'asc' ? '↑' : '↓' }}
                </span>
              </th>
              <th>使用时间</th>
              <th>过期时间</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="invitation in invitations" :key="invitation.id" :class="{ used: invitation.is_used }">
              <td>{{ invitation.id }}</td>
              <td class="code-cell">
                <code class="invitation-code-display">{{ invitation.code }}</code>
                <button
                  class="copy-btn"
                  @click="copyInvitationCode(invitation.code)"
                  title="复制邀请码"
                >
                  📋
                </button>
              </td>
              <td>
                <span :class="['status-badge', invitation.is_used ? 'status-used' : 'status-available']">
                  {{ invitation.is_used ? '已使用' : '可用' }}
                </span>
              </td>
              <td>{{ invitation.used_by_username || '-' }}</td>
              <td class="date-cell">{{ formatDate(invitation.created_at) }}</td>
              <td class="date-cell">
                <span :class="['used-time', getUsedTimeClass(invitation.used_time)]">
                  {{ formatUsedTime(invitation.used_time) }}
                </span>
              </td>
              <td class="date-cell">{{ invitation.expires_at ? formatDate(invitation.expires_at) : '永不过期' }}</td>
            </tr>
          </tbody>
        </table>

        <!-- 分页控件 -->
        <div v-if="invitationPagination" class="pagination-container">
          <div class="pagination-info">
            显示第 {{ (invitationPagination.page - 1) * invitationPagination.per_page + 1 }} - 
            {{ Math.min(invitationPagination.page * invitationPagination.per_page, invitationPagination.total) }} 条，
            共 {{ invitationPagination.total }} 条记录
          </div>
          
          <div class="pagination-controls">
            <button 
              class="pagination-btn"
              @click="goToInvitationPage(1)"
              :disabled="!invitationPagination.has_prev"
            >
              首页
            </button>
            <button 
              class="pagination-btn"
              @click="goToInvitationPage(invitationPagination.page - 1)"
              :disabled="!invitationPagination.has_prev"
            >
              上一页
            </button>
            
            <div class="page-numbers">
              <button
                v-for="page in getInvitationPageNumbers()"
                :key="page"
                :class="['page-number', { active: page === invitationPagination.page }]"
                @click="goToInvitationPage(page)"
              >
                {{ page }}
              </button>
            </div>
            
            <button 
              class="pagination-btn"
              @click="goToInvitationPage(invitationPagination.page + 1)"
              :disabled="!invitationPagination.has_next"
            >
              下一页
            </button>
            <button 
              class="pagination-btn"
              @click="goToInvitationPage(invitationPagination.total_pages)"
              :disabled="!invitationPagination.has_next"
            >
              末页
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 科目管理 -->
    <div v-if="activeTab === 'subjects'" class="control-section">
      <div class="section-header">
        <h2 class="section-title">📚 科目管理</h2>
        <div class="section-actions">
          <button class="primary-btn" @click="openSubjectDialog('create')">
            <span class="btn-icon">➕</span>
            创建科目
          </button>
          <button class="refresh-btn" @click="() => loadSubjects()" :disabled="loading">
            <span class="btn-icon">🔄</span>
            刷新列表
          </button>
        </div>
      </div>

      <!-- 搜索和筛选区域 -->
      <div class="search-controls">
        <div class="search-group">
          <div class="search-input-wrapper">
            <input
              type="text"
              class="search-input"
              placeholder="搜索科目名称..."
              :value="subjectSearchParams.search"
              @input="handleSubjectSearch(($event.target as HTMLInputElement).value)"
            >
            <button 
              v-if="subjectSearchParams.search"
              class="clear-search-btn"
              @click="clearSubjectSearch"
              title="清除搜索"
            >
              ✕
            </button>
          </div>
        </div>
        
        <div class="filter-group">
          <label class="filter-label">每页显示:</label>
          <select 
            class="page-size-select" 
            :value="subjectSearchParams.per_page"
            @change="changeSubjectPageSize(parseInt(($event.target as HTMLSelectElement).value))"
          >
            <option value="10">10条</option>
            <option value="20">20条</option>
            <option value="50">50条</option>
            <option value="100">100条</option>
          </select>
        </div>
      </div>

      <Loading v-if="loading" />

      <div v-else-if="subjects.length === 0" class="empty-state">
        <div class="empty-icon">📚</div>
        <p>{{ subjectSearchParams.search ? '没有找到匹配的科目' : '暂无科目' }}</p>
      </div>

      <div v-else class="subjects-table-container">
        <table class="subjects-table">
          <thead>
            <tr>
              <th class="sortable-header" @click="handleSubjectSort('subject_id')">
                ID
                <span class="sort-indicator" v-if="subjectSearchParams.order_by === 'subject_id'">
                  {{ subjectSearchParams.order_dir === 'asc' ? '↑' : '↓' }}
                </span>
              </th>
              <th class="sortable-header" @click="handleSubjectSort('subject_name')">
                科目名称
                <span class="sort-indicator" v-if="subjectSearchParams.order_by === 'subject_name'">
                  {{ subjectSearchParams.order_dir === 'asc' ? '↑' : '↓' }}
                </span>
              </th>
              <th class="sortable-header" @click="handleSubjectSort('created_at')">
                创建时间
                <span class="sort-indicator" v-if="subjectSearchParams.order_by === 'created_at'">
                  {{ subjectSearchParams.order_dir === 'asc' ? '↑' : '↓' }}
                </span>
              </th>
              <th class="sortable-header" @click="handleSubjectSort('updated_at')">
                更新时间
                <span class="sort-indicator" v-if="subjectSearchParams.order_by === 'updated_at'">
                  {{ subjectSearchParams.order_dir === 'asc' ? '↑' : '↓' }}
                </span>
              </th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="subject in subjects" :key="subject.subject_id">
              <td>{{ subject.subject_id }}</td>
              <td class="subject-name-cell">
                <span class="subject-name">{{ subject.subject_name }}</span>
              </td>
              <td class="date-cell">{{ formatDate(subject.created_at) }}</td>
              <td class="date-cell">{{ formatDate(subject.updated_at) }}</td>
              <td class="actions-cell">
                <button
                  @click="openSubjectDialog('edit', subject)"
                  class="action-btn btn-edit"
                >
                  编辑
                </button>
                <button
                  @click="deleteSubject(subject)"
                  class="action-btn btn-delete"
                >
                  删除
                </button>
              </td>
            </tr>
          </tbody>
        </table>

        <!-- 分页控件 -->
        <div v-if="subjectPagination" class="pagination-container">
          <div class="pagination-info">
            显示第 {{ (subjectPagination.page - 1) * subjectPagination.per_page + 1 }} - 
            {{ Math.min(subjectPagination.page * subjectPagination.per_page, subjectPagination.total) }} 条，
            共 {{ subjectPagination.total }} 条记录
          </div>
          
          <div class="pagination-controls">
            <button 
              class="pagination-btn"
              @click="goToSubjectPage(1)"
              :disabled="!subjectPagination.has_prev"
            >
              首页
            </button>
            <button 
              class="pagination-btn"
              @click="goToSubjectPage(subjectPagination.page - 1)"
              :disabled="!subjectPagination.has_prev"
            >
              上一页
            </button>
            
            <div class="page-numbers">
              <button
                v-for="page in getSubjectPageNumbers()"
                :key="page"
                :class="['page-number', { active: page === subjectPagination.page }]"
                @click="goToSubjectPage(page)"
              >
                {{ page }}
              </button>
            </div>
            
            <button 
              class="pagination-btn"
              @click="goToSubjectPage(subjectPagination.page + 1)"
              :disabled="!subjectPagination.has_next"
            >
              下一页
            </button>
            <button 
              class="pagination-btn"
              @click="goToSubjectPage(subjectPagination.total_pages)"
              :disabled="!subjectPagination.has_next"
            >
              末页
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 题库管理 -->
    <div v-if="activeTab === 'tiku'" class="control-section">
      <div class="section-header">
        <h2 class="section-title">📖 题库管理</h2>
        <div class="section-actions">
          <button class="primary-btn" @click="openUploadDialog">
            <span class="btn-icon">📤</span>
            上传题库
          </button>
          <button class="secondary-btn" @click="reloadBanks" :disabled="loading">
            <span class="btn-icon">♻️</span>
            重新加载
          </button>
        </div>
      </div>

      <!-- 科目选择器 -->
      <div v-if="subjects.length > 0" class="subject-selector">
        <label class="selector-label">选择科目：</label>
        <div class="subject-chips">
          <button
            v-for="subject in subjects"
            :key="subject.subject_id"
            :class="['subject-chip', { active: selectedSubjectId === subject.subject_id }]"
            @click="selectSubject(subject.subject_id)"
          >
            {{ subject.subject_name }}
          </button>
        </div>
      </div>

      <Loading v-if="loading" />

      <div v-else-if="!selectedSubjectId" class="empty-state">
        <div class="empty-icon">📖</div>
        <p>请选择一个科目查看题库</p>
      </div>

      <div v-else-if="tikuList.length === 0" class="empty-state">
        <div class="empty-icon">📖</div>
        <p>{{ tikuSearchParams.search ? '没有找到匹配的题库' : '该科目下暂无题库' }}</p>
      </div>

      <div v-else>
        <!-- 搜索和筛选区域 -->
        <div class="search-controls">
          <div class="search-group">
            <div class="search-input-wrapper">
              <input
                type="text"
                class="search-input"
                placeholder="搜索题库名称..."
                :value="tikuSearchParams.search"
                @input="handleTikuSearch(($event.target as HTMLInputElement).value)"
              >
              <button 
                v-if="tikuSearchParams.search"
                class="clear-search-btn"
                @click="clearTikuSearch"
                title="清除搜索"
              >
                ✕
              </button>
            </div>
          </div>
          
          <div class="filter-group">
            <label class="filter-label">每页显示:</label>
            <select 
              class="page-size-select" 
              :value="tikuSearchParams.per_page"
              @change="changeTikuPageSize(parseInt(($event.target as HTMLSelectElement).value))"
            >
              <option value="10">10条</option>
              <option value="20">20条</option>
              <option value="50">50条</option>
              <option value="100">100条</option>
            </select>
          </div>
        </div>

        <div class="tiku-table-container">
          <table class="tiku-table">
            <thead>
              <tr>
                <th class="sortable-header" @click="handleTikuSort('tiku_name')">
                  题库名称
                  <span class="sort-indicator" v-if="tikuSearchParams.order_by === 'tiku_name'">
                    {{ tikuSearchParams.order_dir === 'asc' ? '↑' : '↓' }}
                  </span>
                </th>
                <th class="sortable-header" @click="handleTikuSort('tiku_nums')">
                  题目数量
                  <span class="sort-indicator" v-if="tikuSearchParams.order_by === 'tiku_nums'">
                    {{ tikuSearchParams.order_dir === 'asc' ? '↑' : '↓' }}
                  </span>
                </th>
                <th class="sortable-header" @click="handleTikuSort('file_size')">
                  文件大小
                  <span class="sort-indicator" v-if="tikuSearchParams.order_by === 'file_size'">
                    {{ tikuSearchParams.order_dir === 'asc' ? '↑' : '↓' }}
                  </span>
                </th>
                <th>状态</th>
                <th class="sortable-header" @click="handleTikuSort('created_at')">
                  创建时间
                  <span class="sort-indicator" v-if="tikuSearchParams.order_by === 'created_at'">
                    {{ tikuSearchParams.order_dir === 'asc' ? '↑' : '↓' }}
                  </span>
                </th>
                <th class="sortable-header" @click="handleTikuSort('updated_at')">
                  更新时间
                  <span class="sort-indicator" v-if="tikuSearchParams.order_by === 'updated_at'">
                    {{ tikuSearchParams.order_dir === 'asc' ? '↑' : '↓' }}
                  </span>
                </th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="tiku in tikuList" :key="tiku.tiku_id" :class="{ disabled: !tiku.is_active }">
                <td class="tiku-name-cell">
                  <span class="tiku-name">{{ tiku.tiku_name }}</span>
                  <div class="tiku-path">{{ tiku.tiku_position }}</div>
                </td>
                <td class="number-cell">{{ tiku.tiku_nums }}</td>
                <td class="size-cell">{{ formatFileSize(tiku.file_size || 0) }}</td>
                <td>
                  <span :class="['status-badge', tiku.is_active ? 'status-active' : 'status-disabled']">
                    {{ tiku.is_active ? '启用' : '禁用' }}
                  </span>
                </td>
                <td class="date-cell">{{ formatDate(tiku.created_at) }}</td>
                <td class="date-cell">{{ formatDate(tiku.updated_at) }}</td>
                <td class="actions-cell">
                  <button
                    @click="toggleTiku(tiku)"
                    :class="['action-btn', tiku.is_active ? 'btn-disable' : 'btn-enable']"
                  >
                    {{ tiku.is_active ? '禁用' : '启用' }}
                  </button>
                  <button
                    @click="deleteTiku(tiku)"
                    class="action-btn btn-delete"
                  >
                    删除
                  </button>
                </td>
              </tr>
            </tbody>
          </table>

          <!-- 分页控件 -->
          <div v-if="tikuPagination" class="pagination-container">
            <div class="pagination-info">
              显示第 {{ (tikuPagination.page - 1) * tikuPagination.per_page + 1 }} - 
              {{ Math.min(tikuPagination.page * tikuPagination.per_page, tikuPagination.total) }} 条，
              共 {{ tikuPagination.total }} 条记录
            </div>
            
            <div class="pagination-controls">
              <button 
                class="pagination-btn"
                @click="goToTikuPage(1)"
                :disabled="!tikuPagination.has_prev"
              >
                首页
              </button>
              <button 
                class="pagination-btn"
                @click="goToTikuPage(tikuPagination.page - 1)"
                :disabled="!tikuPagination.has_prev"
              >
                上一页
              </button>
              
              <div class="page-numbers">
                <button
                  v-for="page in getTikuPageNumbers()"
                  :key="page"
                  :class="['page-number', { active: page === tikuPagination.page }]"
                  @click="goToTikuPage(page)"
                >
                  {{ page }}
                </button>
              </div>
              
              <button 
                class="pagination-btn"
                @click="goToTikuPage(tikuPagination.page + 1)"
                :disabled="!tikuPagination.has_next"
              >
                下一页
              </button>
              <button 
                class="pagination-btn"
                @click="goToTikuPage(tikuPagination.total_pages)"
                :disabled="!tikuPagination.has_next"
              >
                末页
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 使用统计 -->
    <div v-if="activeTab === 'stats'" class="control-section">
      <div class="section-header">
        <h2 class="section-title">📊 使用统计</h2>
        <div class="section-actions">
          <button class="secondary-btn" @click="syncUsageStats" :disabled="loading">
            <span class="btn-icon">♻️</span>
            手动同步
          </button>
          <button class="refresh-btn" @click="loadUsageStats" :disabled="loadingStats">
            <span class="btn-icon">🔄</span>
            刷新统计
          </button>
        </div>
      </div>

      <Loading v-if="loadingStats" />

      <div v-else-if="!usageStats" class="empty-state">
        <div class="empty-icon">📊</div>
        <p>暂无统计数据</p>
      </div>

      <div v-else class="stats-container">
        <!-- 科目使用统计 -->
        <div class="stats-section">
          <h3 class="stats-title">📚 科目使用排行</h3>
          <div v-if="usageStats.subject_stats && usageStats.subject_stats.length > 0" class="stats-table-container">
            <table class="stats-table">
              <thead>
                <tr>
                  <th>排名</th>
                  <th>科目名称</th>
                  <th>使用次数</th>
                  <th>使用率</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(subject, index) in usageStats.subject_stats" :key="subject.subject_name">
                  <td class="rank-cell">
                    <span :class="['rank-badge', getRankClass(index)]">{{ index + 1 }}</span>
                  </td>
                  <td class="subject-name-cell">
                    <span class="subject-name">{{ subject.subject_name }}</span>
                  </td>
                  <td class="usage-count-cell">
                    <span :class="['usage-count', { 'unused': subject.used_count === 0 }]">
                      {{ formatUsageCount(subject.used_count) }}
                    </span>
                  </td>
                  <td class="usage-rate-cell">
                    <div class="usage-bar" v-if="subject.used_count > 0">
                      <div 
                        class="usage-fill" 
                        :style="{ width: getUsagePercentage(subject.used_count, usageStats.subject_stats) + '%' }"
                      ></div>
                      <span class="usage-text">{{ getUsagePercentage(subject.used_count, usageStats.subject_stats).toFixed(1) }}%</span>
                    </div>
                    <span v-else class="usage-unused">未使用</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <div v-else class="empty-state">
            <p>暂无科目使用数据</p>
          </div>
        </div>

        <!-- 题库使用统计 -->
        <div class="stats-section">
          <h3 class="stats-title">📖 热门题库排行 (TOP 20)</h3>
          <div v-if="usageStats.tiku_stats && usageStats.tiku_stats.length > 0" class="stats-table-container">
            <table class="stats-table">
              <thead>
                <tr>
                  <th>排名</th>
                  <th>题库名称</th>
                  <th>所属科目</th>
                  <th>使用次数</th>
                  <th>使用率</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(tiku, index) in usageStats.tiku_stats" :key="tiku.tiku_position">
                  <td class="rank-cell">
                    <span :class="['rank-badge', getRankClass(index)]">{{ index + 1 }}</span>
                  </td>
                  <td class="tiku-name-cell">
                    <span class="tiku-name">{{ tiku.tiku_name }}</span>
                  </td>
                  <td class="subject-tag-cell">
                    <span class="subject-tag">{{ tiku.subject_name }}</span>
                  </td>
                  <td class="usage-count-cell">
                    <span :class="['usage-count', { 'unused': tiku.used_count === 0 }]">
                      {{ formatUsageCount(tiku.used_count) }}
                    </span>
                  </td>
                  <td class="usage-rate-cell">
                    <div class="usage-bar" v-if="tiku.used_count > 0">
                      <div 
                        class="usage-fill" 
                        :style="{ width: getUsagePercentage(tiku.used_count, usageStats.tiku_stats) + '%' }"
                      ></div>
                      <span class="usage-text">{{ getUsagePercentage(tiku.used_count, usageStats.tiku_stats).toFixed(1) }}%</span>
                    </div>
                    <span v-else class="usage-unused">未使用</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <div v-else class="empty-state">
            <p>暂无题库使用数据</p>
          </div>
        </div>
      </div>
    </div>

    <!-- 创建邀请码对话框 -->
    <div v-if="showCreateInvitationDialog" class="dialog-overlay" @click="closeCreateDialog">
      <div class="dialog" @click.stop>
        <div class="dialog-header">
          <h3 class="dialog-title">创建新邀请码</h3>
          <button class="dialog-close" @click="closeCreateDialog">✕</button>
        </div>

        <div class="dialog-content">
          <div class="form-group">
            <label class="form-label">邀请码（可选）</label>
            <input
              v-model="newInvitationCode"
              type="text"
              class="form-input"
              placeholder="留空自动生成"
              maxlength="64"
            >
            <div class="form-hint">留空将自动生成12位随机邀请码</div>
          </div>

          <div class="form-group">
            <label class="form-label">有效期（天）</label>
            <input
              v-model.number="newInvitationExpireDays"
              type="number"
              class="form-input"
              placeholder="留空表示永不过期"
              min="1"
              max="365"
            >
            <div class="form-hint">留空表示永不过期</div>
          </div>
        </div>

        <div class="dialog-actions">
          <button class="dialog-btn dialog-btn-cancel" @click="closeCreateDialog">
            取消
          </button>
          <button class="dialog-btn dialog-btn-confirm" @click="createInvitation" :disabled="creatingInvitation">
            {{ creatingInvitation ? '创建中...' : '创建' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 科目管理对话框 -->
    <div v-if="showSubjectDialog" class="dialog-overlay" @click="closeSubjectDialog">
      <div class="dialog" @click.stop>
        <div class="dialog-header">
          <h3 class="dialog-title">{{ subjectDialogMode === 'create' ? '创建科目' : '编辑科目' }}</h3>
          <button class="dialog-close" @click="closeSubjectDialog">✕</button>
        </div>

        <div class="dialog-content">
          <div class="form-group">
            <label class="form-label">科目名称</label>
            <input
              v-model="subjectName"
              type="text"
              class="form-input"
              placeholder="请输入科目名称"
              maxlength="50"
              @keyup.enter="saveSubject"
            >
            <div class="form-hint">科目名称不能超过50个字符</div>
          </div>
        </div>

        <div class="dialog-actions">
          <button class="dialog-btn dialog-btn-cancel" @click="closeSubjectDialog">
            取消
          </button>
          <button class="dialog-btn dialog-btn-confirm" @click="saveSubject" :disabled="loading">
            {{ loading ? '保存中...' : (subjectDialogMode === 'create' ? '创建' : '保存') }}
          </button>
        </div>
      </div>
    </div>

    <!-- 题库上传对话框 -->
    <div v-if="showUploadDialog" class="dialog-overlay" @click="closeUploadDialog">
      <div class="dialog" @click.stop>
        <div class="dialog-header">
          <h3 class="dialog-title">上传题库文件</h3>
          <button class="dialog-close" @click="closeUploadDialog">✕</button>
        </div>

        <div class="dialog-content">
          <div class="form-group">
            <label class="form-label">题库名称</label>
            <input
              v-model="uploadTikuName"
              type="text"
              class="form-input"
              placeholder="留空将使用文件名"
              maxlength="50"
            >
            <div class="form-hint">题库名称不能超过50个字符</div>
          </div>

          <div class="form-group">
            <label class="form-label">选择Excel文件</label>
            <input
              type="file"
              accept=".xlsx,.xls"
              @change="handleFileSelect"
              class="form-file-input"
            >
            <div class="form-hint">支持 .xlsx 和 .xls 格式的Excel文件</div>
            <div v-if="uploadFile" class="file-info">
              <span class="file-name">{{ uploadFile.name }}</span>
              <span class="file-size">({{ formatFileSize(uploadFile.size) }})</span>
            </div>
          </div>
        </div>

        <div class="dialog-actions">
          <button class="dialog-btn dialog-btn-cancel" @click="closeUploadDialog">
            取消
          </button>
          <button 
            class="dialog-btn dialog-btn-confirm" 
            @click="uploadTiku" 
            :disabled="!uploadFile || uploading"
          >
            {{ uploading ? '上传中...' : '上传' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script lang="ts" setup>
import { ref, onMounted, computed } from 'vue'
import { useToast } from 'vue-toastification'
import { useAuthStore } from '@/stores/auth'
import { apiService, type UserSearchParams, type Pagination, type SearchParams } from '@/services/api'
import Loading from '@/components/Loading.vue'

const toast = useToast()
const authStore = useAuthStore()

// 响应式数据
const loading = ref(false)
const activeTab = ref('users')
const stats = ref<any>(null)
const users = ref<any[]>([])
const invitations = ref<any[]>([])
const subjectFiles = ref<any[]>([])

// 新增：科目和题库管理相关状态
const subjects = ref<any[]>([])
const tikuList = ref<any[]>([])
const selectedSubjectId = ref<number | null>(null)

// 用户搜索和分页参数
const userSearchParams = ref<UserSearchParams>({
  search: '',
  order_by: 'id',
  order_dir: 'desc',
  page: 1,
  per_page: 20
})
const userPagination = ref<Pagination | null>(null)
const searchTimeout = ref<number | null>(null)

// 邀请码搜索和分页参数
const invitationSearchParams = ref<SearchParams>({
  search: '',
  order_by: 'id',
  order_dir: 'desc',
  page: 1,
  per_page: 20
})
const invitationPagination = ref<Pagination | null>(null)
const invitationSearchTimeout = ref<number | null>(null)

// 科目搜索和分页参数
const subjectSearchParams = ref<SearchParams>({
  search: '',
  order_by: 'subject_id',
  order_dir: 'desc',
  page: 1,
  per_page: 20
})
const subjectPagination = ref<Pagination | null>(null)
const subjectSearchTimeout = ref<number | null>(null)

// 题库搜索和分页参数
const tikuSearchParams = ref<SearchParams>({
  search: '',
  order_by: 'tiku_id',
  order_dir: 'desc',
  page: 1,
  per_page: 20
})
const tikuPagination = ref<Pagination | null>(null)
const tikuSearchTimeout = ref<number | null>(null)

// 创建邀请码对话框
const showCreateInvitationDialog = ref(false)
const newInvitationCode = ref('')
const newInvitationExpireDays = ref<number | null>(null)
const creatingInvitation = ref(false)

// 新增：科目管理对话框
const showSubjectDialog = ref(false)
const subjectDialogMode = ref<'create' | 'edit'>('create')
const currentSubject = ref<any>(null)
const subjectName = ref('')

// 新增：题库管理状态
const showUploadDialog = ref(false)
const uploadFile = ref<File | null>(null)
const uploadSubjectId = ref<number | null>(null)
const uploadTikuName = ref('')
const uploading = ref(false)

// 新增：使用统计状态
const usageStats = ref<any>(null)
const loadingStats = ref(false)

// 标签页配置
const tabs = [
  { key: 'users', label: '用户管理', icon: '👥' },
  { key: 'invitations', label: '邀请码管理', icon: '🎫' },
  { key: 'subjects', label: '科目管理', icon: '📚' },
  { key: 'tiku', label: '题库管理', icon: '📖' },
  { key: 'stats', label: '使用统计', icon: '📊' }
]

// 当前用户ID
const currentUserId = computed(() => authStore.user?.user_id)

// 切换标签页
const switchTab = (tabKey: string) => {
  activeTab.value = tabKey
  toast.info(`已切换到${tabs.find(t => t.key === tabKey)?.label} 📌`)
  
  // 如果切换到使用统计标签页，自动加载数据
  if (tabKey === 'stats' && !usageStats.value) {
    loadUsageStats()
  }
}

// 加载统计信息
const loadStats = async () => {
  try {
    const response = await apiService.admin.getStats()
    if (response.success) {
      stats.value = response.stats
    } else {
      toast.error(response.message || '获取统计信息失败')
    }
  } catch (error) {
    console.error('获取统计信息失败:', error)
    toast.error('获取统计信息失败')
  }
}

// 用户管理相关函数
const loadUsers = async (resetPage = false) => {
  if (resetPage) {
    userSearchParams.value.page = 1
  }
  
  loading.value = true
  try {
    const response = await apiService.admin.getUsers(userSearchParams.value)
    if (response.success) {
      users.value = response.users || []
      userPagination.value = response.pagination || null
    } else {
      toast.error(response.message || '获取用户列表失败')
    }
  } catch (error) {
    console.error('获取用户列表失败:', error)
    toast.error('获取用户列表失败')
  } finally {
    loading.value = false
  }
}

const toggleUser = async (userId: number) => {
  try {
    const response = await apiService.admin.toggleUser(userId)
    if (response.success) {
      // 更新本地数据
      const user = users.value.find(u => u.id === userId)
      if (user) {
        user.is_enabled = response.is_enabled
      }
      toast.success(response.message || '操作成功')
      // 重新加载统计信息
      loadStats()
    } else {
      toast.error(response.message || '操作失败')
    }
  } catch (error) {
    console.error('切换用户状态失败:', error)
    toast.error('操作失败')
  }
}

const updateUserModel = async (userId: number, model: number) => {
  try {
    const response = await apiService.admin.updateUserModel(userId, model)
    if (response.success) {
      // 更新本地数据
      const user = users.value.find(u => u.id === userId)
      if (user) {
        user.model = response.model
      }
      toast.success(response.message || '权限更新成功')
      // 重新加载统计信息
      loadStats()
    } else {
      toast.error(response.message || '权限更新失败')
      // 恢复原来的值
      loadUsers()
    }
  } catch (error) {
    console.error('更新用户权限失败:', error)
    toast.error('权限更新失败')
    // 恢复原来的值
    loadUsers()
  }
}

// 邀请码管理相关函数
const loadInvitations = async (resetPage = false) => {
  if (resetPage) {
    invitationSearchParams.value.page = 1
  }
  
  loading.value = true
  try {
    const response = await apiService.admin.getInvitations(invitationSearchParams.value)
    if (response.success) {
      invitations.value = response.invitations || []
      invitationPagination.value = response.pagination || null
    } else {
      toast.error(response.message || '获取邀请码列表失败')
    }
  } catch (error) {
    console.error('获取邀请码列表失败:', error)
    toast.error('获取邀请码列表失败')
  } finally {
    loading.value = false
  }
}

const createInvitation = async () => {
  if (creatingInvitation.value) return

  creatingInvitation.value = true
  try {
    const response = await apiService.admin.createInvitation(
      newInvitationCode.value || undefined,
      newInvitationExpireDays.value || undefined
    )

    if (response.success) {
      toast.success('邀请码创建成功！')
      closeCreateDialog()
      loadInvitations()
      loadStats()
    } else {
      toast.error(response.message || '创建邀请码失败')
    }
  } catch (error) {
    console.error('创建邀请码失败:', error)
    toast.error('创建邀请码失败')
  } finally {
    creatingInvitation.value = false
  }
}

const copyInvitationCode = async (code: string) => {
  try {
    await navigator.clipboard.writeText(code)
    toast.success('邀请码已复制到剪贴板')
  } catch (error) {
    console.error('复制失败:', error)
    toast.error('复制失败')
  }
}

const closeCreateDialog = () => {
  showCreateInvitationDialog.value = false
  newInvitationCode.value = ''
  newInvitationExpireDays.value = null
}

// 题库管理相关函数
const loadSubjectFiles = async () => {
  loading.value = true
  try {
    const response = await apiService.admin.getSubjectFiles()
    if (response.success) {
      subjectFiles.value = response.files || []
    } else {
      toast.error(response.message || '获取题库文件失败')
    }
  } catch (error) {
    console.error('获取题库文件失败:', error)
    toast.error('获取题库文件失败')
  } finally {
    loading.value = false
  }
}

// 新增：科目管理相关函数
const loadSubjects = async (resetPage = false) => {
  if (resetPage) {
    subjectSearchParams.value.page = 1
  }
  
  loading.value = true
  try {
    const response = await apiService.admin.getSubjects(subjectSearchParams.value)
    if (response.success) {
      subjects.value = response.subjects || []
      subjectPagination.value = response.pagination || null
    } else {
      toast.error(response.message || '获取科目列表失败')
    }
  } catch (error) {
    console.error('获取科目列表失败:', error)
    toast.error('获取科目列表失败')
  } finally {
    loading.value = false
  }
}

const openSubjectDialog = (mode: 'create' | 'edit', subject?: any) => {
  subjectDialogMode.value = mode
  currentSubject.value = subject
  subjectName.value = mode === 'edit' ? subject?.subject_name || '' : ''
  showSubjectDialog.value = true
}

const closeSubjectDialog = () => {
  showSubjectDialog.value = false
  subjectName.value = ''
  currentSubject.value = null
}

const saveSubject = async () => {
  if (!subjectName.value.trim()) {
    toast.error('科目名称不能为空')
    return
  }

  loading.value = true
  try {
    if (subjectDialogMode.value === 'create') {
      const response = await apiService.admin.createSubject(subjectName.value.trim())
      if (response.success) {
        toast.success('科目创建成功')
        closeSubjectDialog()
        loadSubjects()
        loadStats()
      } else {
        toast.error(response.message || '创建科目失败')
      }
    } else {
      const response = await apiService.admin.updateSubject(currentSubject.value.subject_id, subjectName.value.trim())
      if (response.success) {
        toast.success('科目更新成功')
        closeSubjectDialog()
        loadSubjects()
      } else {
        toast.error(response.message || '更新科目失败')
      }
    }
  } catch (error) {
    console.error('保存科目失败:', error)
    toast.error('保存科目失败')
  } finally {
    loading.value = false
  }
}

const deleteSubject = async (subject: any) => {
  if (!confirm(`确定要删除科目"${subject.subject_name}"吗？这将同时删除该科目下的所有题库文件！`)) {
    return
  }

  loading.value = true
  try {
    const response = await apiService.admin.deleteSubject(subject.subject_id)
    if (response.success) {
      toast.success('科目删除成功')
      loadSubjects()
      loadStats()
      // 如果当前选中的科目被删除，清除选择
      if (selectedSubjectId.value === subject.subject_id) {
        selectedSubjectId.value = null
        tikuList.value = []
      }
    } else {
      toast.error(response.message || '删除科目失败')
    }
  } catch (error) {
    console.error('删除科目失败:', error)
    toast.error('删除科目失败')
  } finally {
    loading.value = false
  }
}

// 新增：题库管理相关函数
const loadTiku = async (subjectId?: number, resetPage = false) => {
  if (resetPage) {
    tikuSearchParams.value.page = 1
  }
  
  loading.value = true
  try {
    const response = await apiService.admin.getTiku(subjectId, tikuSearchParams.value)
    if (response.success) {
      tikuList.value = response.tiku_list || []
      tikuPagination.value = response.pagination || null
    } else {
      toast.error(response.message || '获取题库列表失败')
    }
  } catch (error) {
    console.error('获取题库列表失败:', error)
    toast.error('获取题库列表失败')
  } finally {
    loading.value = false
  }
}

const selectSubject = (subjectId: number) => {
  selectedSubjectId.value = subjectId
  // 重置搜索参数
  tikuSearchParams.value.search = ''
  tikuSearchParams.value.page = 1
  loadTiku(subjectId, true)
}

const openUploadDialog = () => {
  if (!selectedSubjectId.value) {
    toast.error('请先选择一个科目')
    return
  }
  uploadSubjectId.value = selectedSubjectId.value
  showUploadDialog.value = true
}

const closeUploadDialog = () => {
  showUploadDialog.value = false
  uploadFile.value = null
  uploadSubjectId.value = null
  uploadTikuName.value = ''
}

const handleFileSelect = (event: Event) => {
  const target = event.target as HTMLInputElement
  if (target.files && target.files.length > 0) {
    const selectedFile = target.files[0]
    
    // 验证文件类型
    if (!selectedFile.name.match(/\.(xlsx?|xls)$/i)) {
      toast.error('请选择Excel文件（.xlsx 或 .xls）')
      target.value = '' // 清除选择
      return
    }
    
    // 验证文件大小（限制为50MB）
    if (selectedFile.size > 50 * 1024 * 1024) {
      toast.error('文件大小不能超过50MB')
      target.value = '' // 清除选择
      return
    }
    
    uploadFile.value = selectedFile
    console.log('Selected file:', selectedFile.name, 'Size:', selectedFile.size)
    
    // 如果没有输入题库名称，使用文件名（去掉扩展名）
    if (!uploadTikuName.value) {
      const fileName = selectedFile.name
      uploadTikuName.value = fileName.replace(/\.(xlsx?|xls)$/i, '')
    }
  } else {
    uploadFile.value = null
  }
}

const uploadTiku = async () => {
  if (!uploadFile.value || !uploadSubjectId.value) {
    toast.error('请选择文件和科目')
    return
  }

  console.log('Starting upload:', {
    fileName: uploadFile.value.name,
    fileSize: uploadFile.value.size,
    subjectId: uploadSubjectId.value,
    tikuName: uploadTikuName.value
  })

  uploading.value = true
  try {
    const response = await apiService.admin.uploadTiku(
      uploadFile.value,
      uploadSubjectId.value,
      uploadTikuName.value || undefined
    )
    
    console.log('Upload response:', response)
    
    if (response.success) {
      toast.success(`题库上传成功！共${response.question_count}道题目`)
      closeUploadDialog()
      loadTiku(selectedSubjectId.value || undefined)
      loadStats()
    } else {
      toast.error(response.message || '上传题库失败')
    }
  } catch (error) {
    console.error('上传题库失败:', error)
    toast.error(`上传题库失败: ${error instanceof Error ? error.message : '未知错误'}`)
  } finally {
    uploading.value = false
  }
}

const deleteTiku = async (tiku: any) => {
  if (!confirm(`确定要删除题库"${tiku.tiku_name}"吗？`)) {
    return
  }

  loading.value = true
  try {
    const response = await apiService.admin.deleteTiku(tiku.tiku_id)
    if (response.success) {
      toast.success('题库删除成功')
      loadTiku(selectedSubjectId.value || undefined)
      loadStats()
    } else {
      toast.error(response.message || '删除题库失败')
    }
  } catch (error) {
    console.error('删除题库失败:', error)
    toast.error('删除题库失败')
  } finally {
    loading.value = false
  }
}

const toggleTiku = async (tiku: any) => {
  loading.value = true
  try {
    const response = await apiService.admin.toggleTiku(tiku.tiku_id)
    if (response.success) {
      // 更新本地状态
      tiku.is_active = response.is_active
      toast.success(response.message || '操作成功')
    } else {
      toast.error(response.message || '操作失败')
    }
  } catch (error) {
    console.error('切换题库状态失败:', error)
    toast.error('操作失败')
  } finally {
    loading.value = false
  }
}

// 系统管理函数
const reloadBanks = async () => {
  if (!confirm('确定要重新加载所有题库吗？这可能需要一些时间。')) {
    return
  }

  loading.value = true
  try {
    const response = await apiService.admin.reloadBanks()
    if (response.success) {
      toast.success('题库重新加载完成')
      loadSubjects()
      loadTiku(selectedSubjectId.value || undefined)
      loadStats()
    } else {
      toast.error(response.message || '重新加载失败')
    }
  } catch (error) {
    console.error('重新加载失败:', error)
    toast.error('重新加载失败')
  } finally {
    loading.value = false
  }
}

// 工具函数
const formatDate = (dateString: string) => {
  if (!dateString) return '-'
  return new Date(dateString).toLocaleString('zh-CN')
}

const formatLastLogin = (dateString?: string) => {
  if (!dateString) return '从未登录'

  const loginDate = new Date(dateString)
  const now = new Date()
  const timeDiff = now.getTime() - loginDate.getTime()

  // 计算时间差
  const minutes = Math.floor(timeDiff / (1000 * 60))
  const hours = Math.floor(timeDiff / (1000 * 60 * 60))
  const days = Math.floor(timeDiff / (1000 * 60 * 60 * 24))

  if (minutes < 1) {
    return '刚刚'
  } else if (minutes < 60) {
    return `${minutes}分钟前`
  } else if (hours < 24) {
    return `${hours}小时前`
  } else if (days < 7) {
    return `${days}天前`
  } else {
    return loginDate.toLocaleString('zh-CN')
  }
}

const getLastLoginClass = (dateString?: string) => {
  if (!dateString) return 'never-login'

  const loginDate = new Date(dateString)
  const now = new Date()
  const timeDiff = now.getTime() - loginDate.getTime()
  const days = Math.floor(timeDiff / (1000 * 60 * 60 * 24))

  if (days === 0) {
    return 'recent-login' // 今天登录
  } else if (days <= 7) {
    return 'week-login' // 一周内登录
  } else if (days <= 30) {
    return 'month-login' // 一月内登录
  } else {
    return 'old-login' // 很久没登录
  }
}

const formatFileSize = (bytes: number) => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

const formatUsedTime = (dateString?: string) => {
  if (!dateString) return '未使用'
  
  // 直接返回格式化的日期时间
  return new Date(dateString).toLocaleString('zh-CN')
}

const getUsedTimeClass = (dateString?: string) => {
  return dateString ? 'used' : 'available'
}

// 搜索相关方法
const handleSearch = (searchTerm: string) => {
  userSearchParams.value.search = searchTerm
  
  // 清除之前的定时器
  if (searchTimeout.value) {
    clearTimeout(searchTimeout.value)
  }
  
  // 设置新的定时器，延迟搜索
  searchTimeout.value = setTimeout(() => {
    loadUsers(true)
  }, 500) as unknown as number
}

const clearSearch = () => {
  userSearchParams.value.search = ''
  loadUsers(true)
}

// 排序相关方法
const handleSort = (field: string) => {
  if (userSearchParams.value.order_by === field) {
    // 如果是同一个字段，切换排序方向
    userSearchParams.value.order_dir = userSearchParams.value.order_dir === 'asc' ? 'desc' : 'asc'
  } else {
    // 如果是新字段，默认降序
    userSearchParams.value.order_by = field
    userSearchParams.value.order_dir = 'desc'
  }
  loadUsers(true)
}

// 分页相关方法
const goToPage = (page: number) => {
  if (page >= 1 && userPagination.value && page <= userPagination.value.total_pages) {
    userSearchParams.value.page = page
    loadUsers()
  }
}

const changePageSize = (size: number) => {
  userSearchParams.value.per_page = size
  loadUsers(true)
}

// 计算分页显示的页码
const getPageNumbers = () => {
  if (!userPagination.value) return []
  
  const { page, total_pages } = userPagination.value
  const pages: number[] = []
  
  // 显示当前页前后2页
  const start = Math.max(1, page - 2)
  const end = Math.min(total_pages, page + 2)
  
  for (let i = start; i <= end; i++) {
    pages.push(i)
  }
  
  return pages
}

// 组件挂载时加载数据
onMounted(async () => {
  await loadStats()
  await loadUsers()
  await loadInvitations()
  await loadSubjects()
})

// 使用统计相关函数
const syncUsageStats = async () => {
  loadingStats.value = true
  try {
    const response = await apiService.admin.syncUsageStats()
    if (response.success) {
      toast.success('使用统计数据同步成功')
      loadUsageStats()
    } else {
      toast.error(response.message || '同步使用统计数据失败')
    }
  } catch (error) {
    console.error('同步使用统计数据失败:', error)
    toast.error('同步使用统计数据失败')
  } finally {
    loadingStats.value = false
  }
}

const loadUsageStats = async () => {
  loadingStats.value = true
  try {
    const response = await apiService.admin.getUsageStats()
    if (response.success) {
      // 修复：API返回的数据结构中，统计数据直接在根级别
      const stats = {
        subject_stats: response.subject_stats || [],
        tiku_stats: response.tiku_stats || []
      }
      usageStats.value = stats
    } else {
      toast.error(response.message || '获取使用统计数据失败')
    }
  } catch (error) {
    console.error('获取使用统计数据失败:', error)
    toast.error('获取使用统计数据失败')
  } finally {
    loadingStats.value = false
  }
}

const getRankClass = (index: number) => {
  if (index < 3) return 'top-rank'
  return 'other-rank'
}

const getUsagePercentage = (usedCount: number, totalStats: any[]) => {
  if (!totalStats || totalStats.length === 0 || usedCount === 0) return 0
  const maxCount = Math.max(...totalStats.map(item => item.used_count))
  return maxCount > 0 ? (usedCount / maxCount) * 100 : 0
}

// 新增：格式化使用次数显示
const formatUsageCount = (count: number) => {
  return count === 0 ? '未使用' : count.toString()
}

// 新增：格式化使用率显示
const formatUsageRate = (count: number, totalStats: any[]) => {
  if (count === 0) return '未使用'
  const percentage = getUsagePercentage(count, totalStats)
  return `${percentage.toFixed(1)}%`
}

// 邀请码搜索相关方法
const handleInvitationSearch = (searchTerm: string) => {
  invitationSearchParams.value.search = searchTerm
  
  // 清除之前的定时器
  if (invitationSearchTimeout.value) {
    clearTimeout(invitationSearchTimeout.value)
  }
  
  // 设置新的定时器，延迟搜索
  invitationSearchTimeout.value = setTimeout(() => {
    loadInvitations(true)
  }, 500) as unknown as number
}

const clearInvitationSearch = () => {
  invitationSearchParams.value.search = ''
  loadInvitations(true)
}

// 邀请码排序相关方法
const handleInvitationSort = (field: string) => {
  if (invitationSearchParams.value.order_by === field) {
    // 如果是同一个字段，切换排序方向
    invitationSearchParams.value.order_dir = invitationSearchParams.value.order_dir === 'asc' ? 'desc' : 'asc'
  } else {
    // 如果是新字段，默认降序
    invitationSearchParams.value.order_by = field
    invitationSearchParams.value.order_dir = 'desc'
  }
  loadInvitations(true)
}

// 邀请码分页相关方法
const goToInvitationPage = (page: number) => {
  if (page >= 1 && invitationPagination.value && page <= invitationPagination.value.total_pages) {
    invitationSearchParams.value.page = page
    loadInvitations()
  }
}

const changeInvitationPageSize = (size: number) => {
  invitationSearchParams.value.per_page = size
  loadInvitations(true)
}

// 计算邀请码分页显示的页码
const getInvitationPageNumbers = () => {
  if (!invitationPagination.value) return []
  
  const { page, total_pages } = invitationPagination.value
  const pages: number[] = []
  
  // 显示当前页前后2页
  const start = Math.max(1, page - 2)
  const end = Math.min(total_pages, page + 2)
  
  for (let i = start; i <= end; i++) {
    pages.push(i)
  }
  
  return pages
}

// 科目搜索相关方法
const handleSubjectSearch = (searchTerm: string) => {
  subjectSearchParams.value.search = searchTerm
  
  // 清除之前的定时器
  if (subjectSearchTimeout.value) {
    clearTimeout(subjectSearchTimeout.value)
  }
  
  // 设置新的定时器，延迟搜索
  subjectSearchTimeout.value = setTimeout(() => {
    loadSubjects(true)
  }, 500) as unknown as number
}

const clearSubjectSearch = () => {
  subjectSearchParams.value.search = ''
  loadSubjects(true)
}

// 科目排序相关方法
const handleSubjectSort = (field: string) => {
  if (subjectSearchParams.value.order_by === field) {
    // 如果是同一个字段，切换排序方向
    subjectSearchParams.value.order_dir = subjectSearchParams.value.order_dir === 'asc' ? 'desc' : 'asc'
  } else {
    // 如果是新字段，默认降序
    subjectSearchParams.value.order_by = field
    subjectSearchParams.value.order_dir = 'desc'
  }
  loadSubjects(true)
}

// 科目分页相关方法
const goToSubjectPage = (page: number) => {
  if (page >= 1 && subjectPagination.value && page <= subjectPagination.value.total_pages) {
    subjectSearchParams.value.page = page
    loadSubjects()
  }
}

const changeSubjectPageSize = (size: number) => {
  subjectSearchParams.value.per_page = size
  loadSubjects(true)
}

// 计算科目分页显示的页码
const getSubjectPageNumbers = () => {
  if (!subjectPagination.value) return []
  
  const { page, total_pages } = subjectPagination.value
  const pages: number[] = []
  
  // 显示当前页前后2页
  const start = Math.max(1, page - 2)
  const end = Math.min(total_pages, page + 2)
  
  for (let i = start; i <= end; i++) {
    pages.push(i)
  }
  
  return pages
}

// 题库搜索相关方法
const handleTikuSearch = (searchTerm: string) => {
  tikuSearchParams.value.search = searchTerm
  
  // 清除之前的定时器
  if (tikuSearchTimeout.value) {
    clearTimeout(tikuSearchTimeout.value)
  }
  
  // 设置新的定时器，延迟搜索
  tikuSearchTimeout.value = setTimeout(() => {
    loadTiku(selectedSubjectId.value || undefined, true)
  }, 500) as unknown as number
}

const clearTikuSearch = () => {
  tikuSearchParams.value.search = ''
  loadTiku(selectedSubjectId.value || undefined, true)
}

// 题库排序相关方法
const handleTikuSort = (field: string) => {
  if (tikuSearchParams.value.order_by === field) {
    // 如果是同一个字段，切换排序方向
    tikuSearchParams.value.order_dir = tikuSearchParams.value.order_dir === 'asc' ? 'desc' : 'asc'
  } else {
    // 如果是新字段，默认降序
    tikuSearchParams.value.order_by = field
    tikuSearchParams.value.order_dir = 'desc'
  }
  loadTiku(selectedSubjectId.value || undefined, true)
}

// 题库分页相关方法
const goToTikuPage = (page: number) => {
  if (page >= 1 && tikuPagination.value && page <= tikuPagination.value.total_pages) {
    tikuSearchParams.value.page = page
    loadTiku(selectedSubjectId.value || undefined)
  }
}

const changeTikuPageSize = (size: number) => {
  tikuSearchParams.value.per_page = size
  loadTiku(selectedSubjectId.value || undefined, true)
}

// 计算题库分页显示的页码
const getTikuPageNumbers = () => {
  if (!tikuPagination.value) return []
  
  const { page, total_pages } = tikuPagination.value
  const pages: number[] = []
  
  // 显示当前页前后2页
  const start = Math.max(1, page - 2)
  const end = Math.min(total_pages, page + 2)
  
  for (let i = start; i <= end; i++) {
    pages.push(i)
  }
  
  return pages
}
</script>

<style scoped>
.system-control-content {
  width: 100%;
  min-height: calc(100vh - 64px);
  background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
  padding: 2rem;
  max-width: 1600px;
  margin: 0 auto;
  overflow-y: auto;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* 统计概览样式 */
.stats-overview {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1.5rem;
  margin-bottom: 3rem;
}

.stat-card {
  background: white;
  border-radius: 16px;
  padding: 2rem;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
  border: 2px solid transparent;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  gap: 1.5rem;
}

.stat-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1);
  border-color: #e2e8f0;
}

.stat-icon {
  font-size: 3rem;
  background: linear-gradient(135deg, #f8fafc, #e2e8f0);
  border-radius: 12px;
  width: 4rem;
  height: 4rem;
  display: flex;
  align-items: center;
  justify-content: center;
}

.stat-content {
  flex: 1;
}

.stat-number {
  font-size: 2rem;
  font-weight: 700;
  color: #1e293b;
  margin-bottom: 0.5rem;
}

.stat-label {
  font-size: 1rem;
  color: #64748b;
  font-weight: 500;
  margin-bottom: 0.25rem;
}

.stat-detail {
  font-size: 0.9rem;
  color: #94a3b8;
}

/* 标签页样式 */
.control-tabs {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 2rem;
  background: #f8fafc;
  padding: 0.5rem;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
}

.tab-button {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.5rem;
  background: transparent;
  border: 1px solid transparent;
  border-radius: 8px;
  color: #64748b;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s ease;
  flex: 1;
  justify-content: center;
}

.tab-button:hover {
  background: white;
  color: #3b82f6;
  border-color: #bfdbfe;
  transform: translateY(-1px);
}

.tab-button.active {
  background: linear-gradient(135deg, #3b82f6, #2563eb);
  color: white;
  border-color: #2563eb;
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
}

.tab-icon {
  font-size: 1.2rem;
}

.tab-text {
  font-weight: 600;
}

/* 控制区块样式 */
.control-section {
  background: white;
  border-radius: 20px;
  padding: 2rem;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
  animation: slideIn 0.3s ease-out;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateX(-20px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
  padding-bottom: 1rem;
  border-bottom: 2px solid #f1f5f9;
}

.section-title {
  font-size: 1.5rem;
  font-weight: 600;
  color: #1e293b;
  margin: 0;
}

.section-actions {
  display: flex;
  gap: 1rem;
}

/* 按钮样式 */
.primary-btn, .refresh-btn, .action-btn {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.25rem;
  border: none;
  border-radius: 8px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  font-size: 0.9rem;
}

.primary-btn {
  background: linear-gradient(135deg, #10b981, #34d399);
  color: white;
}

.primary-btn:hover {
  background: linear-gradient(135deg, #059669, #10b981);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
}

.refresh-btn {
  background: #f8fafc;
  color: #64748b;
  border: 1px solid #e2e8f0;
}

.refresh-btn:hover {
  background: #f1f5f9;
  color: #475569;
  border-color: #cbd5e1;
}

.refresh-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.action-btn {
  padding: 0.5rem 1rem;
  font-size: 0.8rem;
}

.btn-enable {
  background: linear-gradient(135deg, #10b981, #34d399);
  color: white;
}

.btn-enable:hover {
  background: linear-gradient(135deg, #059669, #10b981);
}

.btn-disable {
  background: linear-gradient(135deg, #ef4444, #f87171);
  color: white;
}

.btn-disable:hover {
  background: linear-gradient(135deg, #dc2626, #ef4444);
}

.action-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none;
}

.btn-icon {
  font-size: 1rem;
}

/* 空状态样式 */
.empty-state {
  text-align: center;
  padding: 4rem 2rem;
  color: #64748b;
}

.empty-icon {
  font-size: 4rem;
  margin-bottom: 1rem;
  opacity: 0.5;
}

/* 搜索和筛选控件样式 */
.search-controls {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
  margin-bottom: 1.5rem;
  padding: 1.5rem;
  background: #f8fafc;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
}

.search-group {
  flex: 1;
  max-width: 400px;
}

.search-input-wrapper {
  position: relative;
  display: flex;
  align-items: center;
}

.search-input {
  width: 100%;
  padding: 0.75rem 1rem;
  padding-right: 2.5rem;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  font-size: 0.9rem;
  transition: all 0.2s ease;
  background: white;
}

.search-input:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.clear-search-btn {
  position: absolute;
  right: 0.5rem;
  background: none;
  border: none;
  color: #6b7280;
  cursor: pointer;
  font-size: 1rem;
  padding: 0.25rem;
  border-radius: 4px;
  transition: all 0.2s ease;
}

.clear-search-btn:hover {
  background: #f3f4f6;
  color: #374151;
}

.filter-group {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.filter-label {
  font-size: 0.9rem;
  color: #374151;
  font-weight: 500;
  white-space: nowrap;
}

.page-size-select {
  padding: 0.5rem 0.75rem;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  background: white;
  font-size: 0.9rem;
  cursor: pointer;
}

/* 表格样式 */
.users-table-container, .invitations-table-container, .files-table-container {
  overflow-x: auto;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
}

.users-table, .invitations-table, .files-table {
  width: 100%;
  border-collapse: collapse;
  background: white;
}

.users-table th, .invitations-table th, .files-table th {
  background: #f8fafc;
  color: #374151;
  font-weight: 600;
  padding: 1rem;
  text-align: left;
  border-bottom: 2px solid #e2e8f0;
  white-space: nowrap;
}

/* 可排序表头样式 */
.sortable-header {
  cursor: pointer;
  user-select: none;
  position: relative;
  transition: all 0.2s ease;
}

.sortable-header:hover {
  background: #f1f5f9;
  color: #1e293b;
}

.sort-indicator {
  margin-left: 0.5rem;
  font-size: 0.8rem;
  color: #3b82f6;
  font-weight: bold;
}

/* 分页样式 */
.pagination-container {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.5rem;
  background: #f8fafc;
  border-top: 1px solid #e2e8f0;
  border-radius: 0 0 12px 12px;
  gap: 1rem;
}

.pagination-info {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.9rem;
  color: #374151;
  background: white;
  padding: 0.75rem 1rem;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  font-weight: 500;
  white-space: nowrap;
}

.pagination-info::before {
  content: "📊";
  font-size: 1rem;
  opacity: 0.8;
}

.pagination-controls {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.pagination-btn {
  padding: 0.5rem 0.75rem;
  border: 1px solid #d1d5db;
  background: white;
  color: #374151;
  border-radius: 6px;
  font-size: 0.85rem;
  cursor: pointer;
  transition: all 0.2s ease;
  font-weight: 500;
}

.pagination-btn:hover:not(:disabled) {
  background: #f3f4f6;
  border-color: #9ca3af;
  transform: translateY(-1px);
}

.pagination-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  color: #9ca3af;
}

.page-numbers {
  display: flex;
  gap: 0.25rem;
}

.page-number {
  min-width: 2rem;
  height: 2rem;
  padding: 0.25rem;
  border: 1px solid #d1d5db;
  background: white;
  color: #374151;
  border-radius: 6px;
  font-size: 0.85rem;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 500;
}

.page-number:hover {
  background: #f3f4f6;
  border-color: #9ca3af;
  transform: translateY(-1px);
}

.page-number.active {
  background: linear-gradient(135deg, #3b82f6, #2563eb);
  color: white;
  border-color: #2563eb;
  box-shadow: 0 2px 8px rgba(59, 130, 246, 0.3);
}

/* 响应式优化 */
@media (max-width: 768px) {
  .pagination-container {
    flex-direction: column;
    gap: 1rem;
    padding: 1rem;
  }
  
  .pagination-info {
    order: 2;
    align-self: center;
    font-size: 0.8rem;
  }
  
  .pagination-controls {
    order: 1;
    flex-wrap: wrap;
    justify-content: center;
  }
  
  .pagination-btn {
    font-size: 0.8rem;
    padding: 0.4rem 0.6rem;
  }
  
  .page-number {
    min-width: 1.8rem;
    height: 1.8rem;
    font-size: 0.8rem;
  }
}

.users-table td, .invitations-table td, .files-table td {
  padding: 1rem;
  border-bottom: 1px solid #f1f5f9;
  vertical-align: middle;
}

.users-table tr:hover, .invitations-table tr:hover, .files-table tr:hover {
  background: #fafbfc;
}

.users-table tr.disabled {
  opacity: 0.6;
  background: #fef2f2;
}

.invitations-table tr.used {
  opacity: 0.7;
  background: #f9fafb;
}

/* 表格单元格特殊样式 */
.username-cell .username {
  font-weight: 600;
  color: #1e293b;
}

.model-select {
  padding: 0.5rem;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  background: white;
  font-size: 0.9rem;
}

.model-select:disabled {
  background: #f9fafb;
  color: #6b7280;
  cursor: not-allowed;
}

.status-badge {
  display: inline-block;
  padding: 0.25rem 0.75rem;
  border-radius: 999px;
  font-size: 0.8rem;
  font-weight: 500;
  white-space: nowrap;
}

.status-active {
  background: #d1fae5;
  color: #065f46;
}

.status-disabled {
  background: #fee2e2;
  color: #991b1b;
}

.status-available {
  background: #dbeafe;
  color: #1e40af;
}

.status-used {
  background: #e5e7eb;
  color: #374151;
}

.date-cell {
  font-size: 0.9rem;
  color: #6b7280;
  white-space: nowrap;
}

.invitation-cell {
  max-width: 150px;
}

.invitation-code {
  background: #f3f4f6;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-family: 'Courier New', monospace;
  font-size: 0.85rem;
  word-break: break-all;
}

.code-cell {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.invitation-code-display {
  background: #f3f4f6;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-family: 'Courier New', monospace;
  font-size: 0.9rem;
  flex: 1;
}

.copy-btn {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 1rem;
  padding: 0.25rem;
  border-radius: 4px;
  transition: background 0.2s ease;
}

.copy-btn:hover {
  background: #f3f4f6;
}

.subject-cell .subject-tag {
  background: linear-gradient(135deg, #eff6ff, #dbeafe);
  color: #1e40af;
  padding: 0.25rem 0.75rem;
  border-radius: 999px;
  font-size: 0.8rem;
  font-weight: 500;
  border: 1px solid #bfdbfe;
}

.filename-cell code {
  background: #f8fafc;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-size: 0.85rem;
}

.number-cell, .size-cell {
  text-align: right;
  font-weight: 500;
}

.actions-cell {
  white-space: nowrap;
}

/* 对话框样式 */
.dialog-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(4px);
}

.dialog {
  background: white;
  border-radius: 20px;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
  max-width: 500px;
  width: 90%;
  max-height: 80vh;
  overflow-y: auto;
}

.dialog-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 2rem 2rem 0;
}

.dialog-title {
  font-size: 1.5rem;
  font-weight: 600;
  color: #1e293b;
  margin: 0;
}

.dialog-close {
  background: none;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  color: #6b7280;
  width: 2rem;
  height: 2rem;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  transition: all 0.2s ease;
}

.dialog-close:hover {
  background: #f3f4f6;
  color: #374151;
}

.dialog-content {
  padding: 2rem;
}

.form-group {
  margin-bottom: 1.5rem;
}

.form-label {
  display: block;
  font-weight: 500;
  color: #374151;
  margin-bottom: 0.5rem;
}

.form-input {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  font-size: 1rem;
  transition: border-color 0.2s ease;
}

.form-input:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.form-hint {
  font-size: 0.85rem;
  color: #6b7280;
  margin-top: 0.25rem;
}

.dialog-actions {
  display: flex;
  gap: 1rem;
  padding: 0 2rem 2rem;
  justify-content: flex-end;
}

.dialog-btn {
  padding: 0.75rem 1.5rem;
  border-radius: 8px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  border: none;
}

.dialog-btn-cancel {
  background: #f8fafc;
  color: #64748b;
  border: 1px solid #e2e8f0;
}

.dialog-btn-cancel:hover {
  background: #f1f5f9;
  color: #475569;
}

.dialog-btn-confirm {
  background: linear-gradient(135deg, #10b981, #34d399);
  color: white;
}

.dialog-btn-confirm:hover {
  background: linear-gradient(135deg, #059669, #10b981);
}

.dialog-btn-confirm:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .system-control-content {
    padding: 1rem;
  }

  .control-title {
    font-size: 2rem;
  }

  .stats-overview {
    grid-template-columns: 1fr;
    gap: 1rem;
  }

  .stat-card {
    padding: 1.5rem;
  }

  .control-tabs {
    flex-direction: column;
  }

  .tab-button {
    flex: none;
  }

  .section-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 1rem;
  }

  .section-actions {
    width: 100%;
    justify-content: flex-end;
  }

  .users-table-container, .invitations-table-container, .files-table-container {
    font-size: 0.9rem;
  }

  .users-table th, .invitations-table th, .files-table th,
  .users-table td, .invitations-table td, .files-table td {
    padding: 0.75rem 0.5rem;
  }

  /* 在移动端隐藏一些不重要的列 */
  .users-table th:nth-child(1),
  .users-table td:nth-child(1),
  .users-table th:nth-child(5),
  .users-table td:nth-child(5),
  .users-table th:nth-child(7),
  .users-table td:nth-child(7) {
    display: none;
  }

  .dialog {
    width: 95%;
    margin: 1rem;
  }

  .dialog-content {
    padding: 1.5rem;
  }

  .dialog-actions {
    flex-direction: column;
    padding: 0 1.5rem 1.5rem;
  }
}

/* 最后登录时间样式 */
.last-login {
  padding: 0.25rem 0.5rem;
  border-radius: 6px;
  font-size: 0.8rem;
  font-weight: 500;
  white-space: nowrap;
}

.never-login {
  background: #fee2e2;
  color: #991b1b;
}

.recent-login {
  background: #d1fae5;
  color: #065f46;
}

.week-login {
  background: #dbeafe;
  color: #1e40af;
}

.month-login {
  background: #fef3c7;
  color: #92400e;
}

.old-login {
  background: #f3f4f6;
  color: #6b7280;
}

/* 新添加的 used-time 样式 */
.used-time {
  padding: 0.25rem 0.5rem;
  border-radius: 6px;
  font-size: 0.8rem;
  font-weight: 500;
  white-space: nowrap;
}

.used-time.used {
  background: #f9fafb;
  color: #374151;
}

.used-time.available {
  background: #dbeafe;
  color: #1e40af;
}

/* 新增：科目管理样式 */
.subjects-table-container {
  overflow-x: auto;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
}

.subjects-table {
  width: 100%;
  border-collapse: collapse;
  background: white;
}

.subjects-table th,
.subjects-table td {
  padding: 1rem;
  border-bottom: 1px solid #f1f5f9;
  vertical-align: middle;
}

.subjects-table th {
  background: #f8fafc;
  color: #374151;
  font-weight: 600;
  text-align: left;
  border-bottom: 2px solid #e2e8f0;
  white-space: nowrap;
}

.subjects-table tr:hover {
  background: #fafbfc;
}

.subject-name-cell .subject-name {
  font-weight: 600;
  color: #1e293b;
}

.btn-edit {
  background: linear-gradient(135deg, #3b82f6, #2563eb);
  color: white;
  margin-right: 0.5rem;
}

.btn-edit:hover {
  background: linear-gradient(135deg, #2563eb, #1d4ed8);
}

.btn-delete {
  background: linear-gradient(135deg, #ef4444, #dc2626);
  color: white;
}

.btn-delete:hover {
  background: linear-gradient(135deg, #dc2626, #b91c1c);
}

/* 新增：题库管理样式 */
.subject-selector {
  margin-bottom: 2rem;
  padding: 1.5rem;
  background: #f8fafc;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
}

.selector-label {
  display: block;
  font-weight: 500;
  color: #374151;
  margin-bottom: 1rem;
}

.subject-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
}

.subject-chip {
  padding: 0.5rem 1rem;
  background: white;
  border: 2px solid #e2e8f0;
  border-radius: 8px;
  color: #64748b;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.subject-chip:hover {
  border-color: #cbd5e1;
  color: #475569;
}

.subject-chip.active {
  background: linear-gradient(135deg, #3b82f6, #2563eb);
  color: white;
  border-color: #2563eb;
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
}

.tiku-table-container {
  overflow-x: auto;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
}

.tiku-table {
  width: 100%;
  border-collapse: collapse;
  background: white;
}

.tiku-table th,
.tiku-table td {
  padding: 1rem;
  border-bottom: 1px solid #f1f5f9;
  vertical-align: middle;
}

.tiku-table th {
  background: #f8fafc;
  color: #374151;
  font-weight: 600;
  text-align: left;
  border-bottom: 2px solid #e2e8f0;
  white-space: nowrap;
}

.tiku-table tr:hover {
  background: #fafbfc;
}

.tiku-table tr.disabled {
  opacity: 0.6;
  background: #fef2f2;
}

.tiku-name-cell {
  max-width: 300px;
}

.tiku-name {
  font-weight: 600;
  color: #1e293b;
  display: block;
}

.tiku-path {
  font-size: 0.8rem;
  color: #6b7280;
  margin-top: 0.25rem;
  font-family: 'Courier New', monospace;
  word-break: break-all;
}

.secondary-btn {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.25rem;
  background: #f1f5f9;
  color: #475569;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  font-size: 0.9rem;
}

.secondary-btn:hover {
  background: #e2e8f0;
  color: #334155;
  border-color: #94a3b8;
}

.secondary-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* 新增：文件上传样式 */
.form-file-input {
  width: 100%;
  padding: 0.75rem;
  border: 2px dashed #d1d5db;
  border-radius: 8px;
  background: #f9fafb;
  font-size: 1rem;
  transition: border-color 0.2s ease;
  cursor: pointer;
}

.form-file-input:hover {
  border-color: #9ca3af;
}

.form-file-input:focus {
  outline: none;
  border-color: #3b82f6;
  background: white;
}

.file-info {
  margin-top: 0.5rem;
  padding: 0.5rem;
  background: #f0f9ff;
  border: 1px solid #bae6fd;
  border-radius: 6px;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.file-name {
  font-weight: 500;
  color: #0369a1;
}

.file-size {
  color: #64748b;
  font-size: 0.9rem;
}

/* 响应式优化 */
@media (max-width: 768px) {
  .subject-chips {
    flex-direction: column;
  }
  
  .subject-chip {
    text-align: center;
  }
  
  .tiku-name-cell {
    max-width: 200px;
  }
  
  .tiku-path {
    font-size: 0.7rem;
  }
  
  .section-actions {
    flex-direction: column;
    gap: 0.5rem;
  }
  
  .secondary-btn {
    justify-content: center;
  }
}

/* 使用统计样式 */
.stats-container {
  display: flex;
  flex-wrap: wrap;
  gap: 2rem;
  justify-content: space-between;
}

.stats-section {
  flex: 1;
  min-width: 300px;
}

.stats-title {
  font-size: 1.5rem;
  font-weight: 600;
  color: #1e293b;
  margin-bottom: 1rem;
}

.stats-table-container {
  overflow-x: auto;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
}

.stats-table {
  width: 100%;
  border-collapse: collapse;
  background: white;
}

.stats-table th,
.stats-table td {
  padding: 1rem;
  border-bottom: 1px solid #f1f5f9;
  vertical-align: middle;
}

.stats-table th {
  background: #f8fafc;
  color: #374151;
  font-weight: 600;
  text-align: left;
  border-bottom: 2px solid #e2e8f0;
  white-space: nowrap;
}

.rank-cell {
  width: 50px;
}

.rank-badge {
  display: inline-block;
  padding: 0.25rem 0.5rem;
  border-radius: 12px;
  font-size: 0.8rem;
  font-weight: 600;
  text-align: center;
  min-width: 2rem;
}

.rank-badge.top-rank {
  background: linear-gradient(135deg, #fbbf24, #f59e0b);
  color: white;
}

.rank-badge.other-rank {
  background: #f3f4f6;
  color: #6b7280;
}

.subject-name-cell, .subject-tag-cell {
  flex: 1;
}

.usage-count-cell, .usage-rate-cell {
  text-align: right;
  font-weight: 500;
}

.usage-bar {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  min-width: 120px;
}

.usage-fill {
  height: 8px;
  background: linear-gradient(135deg, #3b82f6, #2563eb);
  border-radius: 4px;
  transition: width 0.3s ease;
}

.usage-text {
  font-size: 0.85rem;
  color: #6b7280;
  white-space: nowrap;
  min-width: 40px;
}

.top-rank {
  background: #d1fae5;
  color: #065f46;
}

.other-rank {
  background: #fef3c7;
  color: #92400e;
}

.usage-unused {
  color: #9ca3af;
  font-style: italic;
}

/* 新增：使用统计中未使用项目的样式 */
.usage-count.unused {
  color: #9ca3af;
  font-style: italic;
  background: #f9fafb;
  padding: 0.25rem 0.5rem;
  border-radius: 6px;
  border: 1px dashed #e5e7eb;
}

.usage-unused {
  color: #9ca3af;
  font-style: italic;
  background: #f9fafb;
  padding: 0.25rem 0.5rem;
  border-radius: 6px;
  border: 1px dashed #e5e7eb;
  display: inline-block;
  min-width: 60px;
  text-align: center;
}

/* 为未使用的行添加特殊样式 */
.stats-table tr:has(.unused) {
  background: #fafbfc !important;
  opacity: 0.8;
}

.stats-table tr:has(.usage-unused) {
  background: #fafbfc !important;
  opacity: 0.8;
}
</style>
