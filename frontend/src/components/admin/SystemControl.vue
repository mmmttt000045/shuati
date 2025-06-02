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
        <div class="stat-icon">
          <IconSubject :size="32" color="#3b82f6" />
        </div>
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
        <span class="tab-icon">
          <IconSubject v-if="tab.icon === 'subject'" :size="20" color="currentColor" />
          <span v-else>{{ tab.icon }}</span>
        </span>
        <span class="tab-text">{{ tab.label }}</span>
      </button>
    </div>

    <!-- 用户管理 -->
    <div v-if="activeTab === 'users'" class="control-section">
      <div class="section-header">
        <h2 class="section-title">👥 用户管理</h2>
        <div class="section-actions">
          <v-btn
            color="primary"
            prepend-icon="mdi-refresh"
            @click="() => loadUsers()"
            :loading="loading"
            variant="elevated"
          >
            刷新列表
          </v-btn>
        </div>
      </div>

      <v-data-table
        :headers="userHeaders"
        :items="filteredUsers"
        :loading="loading"
        :search="userSearch"
        :items-per-page="userItemsPerPage"
        :sort-by="userSortBy"
        :items-per-page-options="itemsPerPageOptions"
        :items-per-page-text="'每页显示：'"
        class="elevation-2"
        density="comfortable"
        :no-data-text="'暂无用户数据'"
        :no-results-text="'没有找到匹配的用户'"
        loading-text="加载用户数据中..."
        hover
        sticky
        fixed-header
      >
        <!-- 搜索槽 -->
        <template v-slot:top>
          <div class="pa-4">
            <v-text-field
              v-model="userSearch"
              label="搜索用户名..."
              prepend-inner-icon="mdi-magnify"
              variant="outlined"
              hide-details
              clearable
              density="compact"
            ></v-text-field>
          </div>
        </template>

        <!-- 用户名列 -->
        <template v-slot:item.username="{ item }">
          <div class="font-weight-bold">{{ (item as any).username }}</div>
        </template>

        <!-- 权限等级列 -->
        <template v-slot:item.model="{ item }">
          <v-select
            :model-value="(item as any).model"
            @update:model-value="updateUserModel((item as any).id, $event)"
            :items="modelOptions"
            variant="outlined"
            density="compact"
            hide-details
            :disabled="item.id === currentUserId"
          ></v-select>
        </template>

        <!-- 状态列 -->
        <template v-slot:item.is_enabled="{ item }">
          <v-chip
            :color="item.is_enabled ? 'success' : 'error'"
            size="small"
            variant="flat"
          >
            {{ item.is_enabled ? '启用' : '禁用' }}
          </v-chip>
        </template>

        <!-- 注册时间列 -->
        <template v-slot:item.created_at="{ item }">
          <span class="text-caption">{{ formatDate(item.created_at) }}</span>
        </template>

        <!-- 最后登录列 -->
        <template v-slot:item.last_time_login="{ item }">
          <v-chip
            :color="getLastLoginColor(item.last_time_login)"
            size="small"
            variant="outlined"
          >
            {{ formatLastLogin(item.last_time_login) }}
          </v-chip>
        </template>

        <!-- 邀请码列 -->
        <template v-slot:item.invitation_code="{ item }">
          <code class="text-caption">{{ item.invitation_code || 'N/A' }}</code>
        </template>

        <!-- 操作列 -->
        <template v-slot:item.actions="{ item }">
          <v-btn
            :color="item.is_enabled ? 'error' : 'success'"
            :disabled="item.id === currentUserId"
            @click="toggleUser(item.id)"
            size="small"
            variant="elevated"
          >
            {{ item.is_enabled ? '禁用' : '启用' }}
          </v-btn>
        </template>
      </v-data-table>
    </div>

    <!-- 邀请码管理 -->
    <div v-if="activeTab === 'invitations'" class="control-section">
      <div class="section-header">
        <h2 class="section-title">🎫 邀请码管理</h2>
        <div class="section-actions">
          <v-btn
            color="primary"
            prepend-icon="mdi-plus"
            @click="showCreateInvitationDialog = true"
            variant="elevated"
          >
            创建邀请码
          </v-btn>
          <v-btn
            color="secondary"
            prepend-icon="mdi-refresh"
            @click="() => loadInvitations()"
            :loading="loading"
            variant="elevated"
          >
            刷新列表
          </v-btn>
        </div>
      </div>

      <v-data-table
        :headers="invitationHeaders"
        :items="filteredInvitations"
        :loading="loading"
        :search="invitationSearch"
        :items-per-page="invitationItemsPerPage"
        :sort-by="invitationSortBy"
        :items-per-page-options="itemsPerPageOptions"
        :items-per-page-text="'每页显示：'"
        class="elevation-2"
        density="comfortable"
        :no-data-text="'暂无邀请码'"
        :no-results-text="'没有找到匹配的邀请码'"
      >
        <!-- 搜索槽 -->
        <template v-slot:top>
          <div class="pa-4">
            <v-text-field
              v-model="invitationSearch"
              label="搜索邀请码..."
              prepend-inner-icon="mdi-magnify"
              variant="outlined"
              hide-details
              clearable
              density="compact"
            ></v-text-field>
          </div>
        </template>

        <!-- 邀请码列 -->
        <template v-slot:item.code="{ item }">
          <div class="d-flex align-center">
            <code class="text-caption mr-2">{{ item.code }}</code>
            <v-btn
              icon="mdi-content-copy"
              size="x-small"
              variant="text"
              @click="copyInvitationCode(item.code)"
              title="复制邀请码"
            ></v-btn>
          </div>
        </template>

        <!-- 状态列 -->
        <template v-slot:item.is_used="{ item }">
          <v-chip
            :color="item.is_used ? 'warning' : 'success'"
            size="small"
            variant="flat"
          >
            {{ item.is_used ? '已使用' : '可用' }}
          </v-chip>
        </template>

        <!-- 使用者列 -->
        <template v-slot:item.used_by_username="{ item }">
          {{ item.used_by_username || '-' }}
        </template>

        <!-- 创建时间列 -->
        <template v-slot:item.created_at="{ item }">
          <span class="text-caption">{{ formatDate(item.created_at) }}</span>
        </template>

        <!-- 使用时间列 -->
        <template v-slot:item.used_time="{ item }">
          <span class="text-caption">{{ formatUsedTime(item.used_time) }}</span>
        </template>

        <!-- 过期时间列 -->
        <template v-slot:item.expires_at="{ item }">
          <span class="text-caption">{{ item.expires_at ? formatDate(item.expires_at) : '永不过期' }}</span>
        </template>
      </v-data-table>
    </div>

    <!-- 科目管理 -->
    <div v-if="activeTab === 'subjects'" class="control-section">
      <div class="section-header">
        <h2 class="section-title">
          <IconSubject :size="24" color="#3b82f6" class="title-icon" />
          科目管理
        </h2>
        <div class="section-actions">
          <v-btn
            color="primary"
            prepend-icon="mdi-plus"
            @click="openSubjectDialog('create')"
            variant="elevated"
          >
            创建科目
          </v-btn>
          <v-btn
            color="secondary"
            prepend-icon="mdi-refresh"
            @click="() => loadSubjects()"
            :loading="loading"
            variant="elevated"
          >
            刷新列表
          </v-btn>
        </div>
      </div>

      <v-data-table
        :headers="subjectHeaders"
        :items="filteredSubjects"
        :loading="loading"
        :search="subjectSearch"
        :items-per-page="subjectItemsPerPage"
        :sort-by="subjectSortBy"
        :items-per-page-options="itemsPerPageOptions"
        :items-per-page-text="'每页显示：'"
        class="elevation-2"
        density="comfortable"
        :no-data-text="'暂无科目'"
        :no-results-text="'没有找到匹配的科目'"
      >
        <!-- 搜索槽 -->
        <template v-slot:top>
          <div class="pa-4">
            <v-text-field
              v-model="subjectSearch"
              label="搜索科目名称..."
              prepend-inner-icon="mdi-magnify"
              variant="outlined"
              hide-details
              clearable
              density="compact"
            ></v-text-field>
          </div>
        </template>

        <!-- 科目名称列 -->
        <template v-slot:item.subject_name="{ item }">
          <div class="font-weight-bold">{{ item.subject_name }}</div>
        </template>

        <!-- 考试时间列 -->
        <template v-slot:item.exam_time="{ item }">
          <span class="text-caption">{{ formatDate(item.exam_time) }}</span>
        </template>

        <!-- 创建时间列 -->
        <template v-slot:item.created_at="{ item }">
          <span class="text-caption">{{ formatDate(item.created_at) }}</span>
        </template>

        <!-- 更新时间列 -->
        <template v-slot:item.updated_at="{ item }">
          <span class="text-caption">{{ formatDate(item.updated_at) }}</span>
        </template>

        <!-- 操作列 -->
        <template v-slot:item.actions="{ item }">
          <v-btn
            color="primary"
            size="small"
            variant="elevated"
            @click="openSubjectDialog('edit', item)"
            class="mr-2"
          >
            编辑
          </v-btn>
          <v-btn
            color="error"
            size="small"
            variant="elevated"
            @click="deleteSubject(item)"
          >
            删除
          </v-btn>
        </template>
      </v-data-table>
    </div>

    <!-- 题库管理 -->
    <div v-if="activeTab === 'tiku'" class="control-section">
      <div class="section-header">
        <h2 class="section-title">📖 题库管理</h2>
        <div class="section-actions">
          <v-btn
            color="primary"
            prepend-icon="mdi-upload"
            @click="openUploadDialog"
            variant="elevated"
          >
            上传题库
          </v-btn>
          <v-btn
            color="secondary"
            prepend-icon="mdi-refresh"
            @click="reloadBanks"
            :loading="loading"
            variant="elevated"
          >
            重新加载
          </v-btn>
        </div>
      </div>

      <!-- 科目选择器 -->
      <div v-if="subjects.length > 0" class="subject-selector pa-4">
        <v-chip-group
          v-model="selectedSubjectId"
          color="primary"
          selected-class="text-primary"
          @update:model-value="(value: number | null) => selectSubject(value || 0)"
        >
          <v-chip
            v-for="subject in subjects"
            :key="subject.subject_id"
            :value="subject.subject_id"
            variant="outlined"
          >
            {{ subject.subject_name }}
          </v-chip>
        </v-chip-group>
      </div>

      <div v-if="loading">
        <Loading />
      </div>

      <div v-else-if="!selectedSubjectId" class="empty-state">
        <div class="empty-icon">📖</div>
        <p>请选择一个科目查看题库</p>
      </div>

      <div v-else-if="tikuList.length === 0" class="empty-state">
        <div class="empty-icon">📖</div>
        <p>{{ tikuSearch ? '没有找到匹配的题库' : '该科目下暂无题库' }}</p>
      </div>

      <v-data-table
        v-else
        :headers="tikuHeaders"
        :items="filteredTiku"
        :loading="loading"
        :search="tikuSearch"
        :items-per-page="tikuItemsPerPage"
        :sort-by="tikuSortBy"
        :items-per-page-options="itemsPerPageOptions"
        :items-per-page-text="'每页显示：'"
        class="elevation-2"
        density="comfortable"
        :no-data-text="'该科目下暂无题库'"
        :no-results-text="'没有找到匹配的题库'"
      >
        <!-- 搜索槽 -->
        <template v-slot:top>
          <div class="pa-4">
            <v-text-field
              v-model="tikuSearch"
              label="搜索题库名称..."
              prepend-inner-icon="mdi-magnify"
              variant="outlined"
              hide-details
              clearable
              density="compact"
            ></v-text-field>
          </div>
        </template>

        <!-- 题库名称列 -->
        <template v-slot:item.tiku_name="{ item }">
          <div class="font-weight-bold">{{ (item as any).tiku_name }}</div>
        </template>

        <!-- 题目数量列 -->
        <template v-slot:item.tiku_nums="{ item }">
          <v-chip size="small" color="info">{{ item.tiku_nums }}</v-chip>
        </template>

        <!-- 文件大小列 -->
        <template v-slot:item.file_size="{ item }">
          {{ formatFileSize(item.file_size || 0) }}
        </template>

        <!-- 状态列 -->
        <template v-slot:item.is_active="{ item }">
          <v-chip
            :color="item.is_active ? 'success' : 'error'"
            size="small"
            variant="flat"
          >
            {{ item.is_active ? '启用' : '禁用' }}
          </v-chip>
        </template>

        <!-- 创建时间列 -->
        <template v-slot:item.created_at="{ item }">
          <span class="text-caption">{{ formatDate(item.created_at) }}</span>
        </template>

        <!-- 更新时间列 -->
        <template v-slot:item.updated_at="{ item }">
          <span class="text-caption">{{ formatDate(item.updated_at) }}</span>
        </template>

        <!-- 操作列 -->
        <template v-slot:item.actions="{ item }">
          <v-btn
            :color="item.is_active ? 'warning' : 'success'"
            size="small"
            variant="elevated"
            @click="toggleTiku(item)"
            class="mr-2"
          >
            {{ item.is_active ? '禁用' : '启用' }}
          </v-btn>
          <v-btn
            color="error"
            size="small"
            variant="elevated"
            @click="deleteTiku(item)"
          >
            删除
          </v-btn>
        </template>
      </v-data-table>
    </div>

    <!-- 使用统计 -->
    <div v-if="activeTab === 'stats'" class="control-section">
      <div class="section-header">
        <h2 class="section-title">📊 使用统计</h2>
        <div class="section-actions">
          <v-btn
            color="secondary"
            prepend-icon="mdi-sync"
            @click="syncUsageStats"
            :loading="loadingStats"
            variant="elevated"
          >
            手动同步
          </v-btn>
          <v-btn
            color="primary"
            prepend-icon="mdi-refresh"
            @click="loadUsageStats"
            :loading="loadingStats"
            variant="elevated"
          >
            刷新统计
          </v-btn>
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
          <v-data-table
            v-if="usageStats.subject_stats && usageStats.subject_stats.length > 0"
            :headers="subjectStatsHeaders"
            :items="usageStats.subject_stats"
            :items-per-page="10"
            :sort-by="[{ key: 'used_count', order: 'desc' }]"
            class="elevation-2"
            density="comfortable"
            :no-data-text="'暂无科目使用数据'"
          >
            <!-- 排名列 -->
            <template v-slot:item.rank="{ index }">
              <v-chip
                :color="(index as number) < 3 ? 'warning' : 'default'"
                size="small"
                variant="flat"
              >
                {{ (index as number) + 1 }}
              </v-chip>
            </template>

            <!-- 科目名称列 -->
            <template v-slot:item.subject_name="{ item }">
              <div class="font-weight-bold">{{ (item as any).subject_name }}</div>
            </template>

            <!-- 使用次数列 -->
            <template v-slot:item.used_count="{ item }">
              <v-chip
                v-if="(item as any).used_count === 0"
                color="grey"
                size="small"
                variant="outlined"
              >
                未使用
              </v-chip>
              <v-chip
                v-else
                color="success"
                size="small"
                variant="flat"
              >
                {{ (item as any).used_count }}
              </v-chip>
            </template>

            <!-- 使用率列 -->
            <template v-slot:item.usage_rate="{ item }">
              <div class="d-flex align-center" style="min-width: 120px;">
                <v-progress-linear
                  v-if="(item as any).used_count > 0"
                  :model-value="getUsagePercentage((item as any).used_count, usageStats.subject_stats)"
                  color="primary"
                  height="8"
                  class="mr-2"
                  style="width: 80px;"
                ></v-progress-linear>
                <span class="text-caption">
                  {{ (item as any).used_count > 0 ? getUsagePercentage((item as any).used_count, usageStats.subject_stats).toFixed(1) + '%' : '未使用' }}
                </span>
              </div>
            </template>
          </v-data-table>
          <div v-else class="empty-state">
            <p>暂无科目使用数据</p>
          </div>
        </div>

        <!-- 题库使用统计 -->
        <div class="stats-section">
          <h3 class="stats-title">📖 热门题库排行 (TOP 20)</h3>
          <v-data-table
            v-if="usageStats.tiku_stats && usageStats.tiku_stats.length > 0"
            :headers="tikuStatsHeaders"
            :items="usageStats.tiku_stats"
            :items-per-page="20"
            :sort-by="[{ key: 'used_count', order: 'desc' }]"
            class="elevation-2"
            density="comfortable"
            :no-data-text="'暂无题库使用数据'"
            :loading="loadingStats"
            loading-text="加载统计数据中..."
          >
            <!-- 排名列 -->
            <template v-slot:item.rank="{ index }">
              <v-chip
                :color="index < 3 ? 'warning' : 'default'"
                size="small"
                variant="flat"
              >
                {{ index + 1 }}
              </v-chip>
            </template>

            <!-- 题库名称列 -->
            <template v-slot:item.tiku_name="{ item }">
              <div class="font-weight-bold">{{ (item as any).tiku_name }}</div>
            </template>

            <!-- 所属科目列 -->
            <template v-slot:item.subject_name="{ item }">
              <v-chip
                color="info"
                size="small"
                variant="outlined"
              >
                {{ (item as any).subject_name }}
              </v-chip>
            </template>

            <!-- 使用次数列 -->
            <template v-slot:item.used_count="{ item }">
              <v-chip
                v-if="(item as any).used_count === 0"
                color="grey"
                size="small"
                variant="outlined"
              >
                未使用
              </v-chip>
              <v-chip
                v-else
                color="success"
                size="small"
                variant="flat"
              >
                {{ (item as any).used_count }}
              </v-chip>
            </template>

            <!-- 使用率列 -->
            <template v-slot:item.usage_rate="{ item }">
              <div class="d-flex align-center" style="min-width: 120px;">
                <v-progress-linear
                  v-if="(item as any).used_count > 0"
                  :model-value="getUsagePercentage((item as any).used_count, usageStats.tiku_stats)"
                  color="primary"
                  height="8"
                  class="mr-2"
                  style="width: 80px;"
                ></v-progress-linear>
                <span class="text-caption">
                  {{ (item as any).used_count > 0 ? getUsagePercentage((item as any).used_count, usageStats.tiku_stats).toFixed(1) + '%' : '未使用' }}
                </span>
              </div>
            </template>
          </v-data-table>
          <div v-else class="empty-state">
            <p>暂无题库使用数据</p>
          </div>
        </div>
      </div>
    </div>

    <!-- 创建邀请码对话框 -->
    <v-dialog v-model="showCreateInvitationDialog" max-width="500px">
      <v-card>
        <v-card-title>
          <span class="text-h5">创建新邀请码</span>
        </v-card-title>

        <v-card-text>
          <v-container>
            <v-row>
              <v-col cols="12">
                <v-text-field
                  v-model="newInvitationCode"
                  label="邀请码（可选）"
                  placeholder="留空自动生成"
                  maxlength="64"
                  variant="outlined"
                  hint="留空将自动生成12位随机邀请码"
                  persistent-hint
                ></v-text-field>
              </v-col>
              <v-col cols="12">
                <v-text-field
                  v-model="newInvitationExpireDays"
                  label="有效期（天）"
                  placeholder="留空表示永不过期"
                  type="number"
                  :min="1"
                  :max="365"
                  variant="outlined"
                  hint="留空表示永不过期"
                  persistent-hint
                ></v-text-field>
              </v-col>
            </v-row>
          </v-container>
        </v-card-text>

        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="grey" variant="text" @click="closeCreateDialog">
            取消
          </v-btn>
          <v-btn
            color="primary"
            variant="elevated"
            @click="createInvitation"
            :loading="creatingInvitation"
          >
            创建
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- 科目管理对话框 -->
    <v-dialog v-model="showSubjectDialog" max-width="500px">
      <v-card>
        <v-card-title>
          <span class="text-h5">{{ subjectDialogMode === 'create' ? '创建科目' : '编辑科目' }}</span>
        </v-card-title>

        <v-card-text>
          <v-container>
            <v-row>
              <v-col cols="12">
                <v-text-field
                  v-model="subjectName"
                  label="科目名称"
                  placeholder="请输入科目名称"
                  maxlength="50"
                  variant="outlined"
                  hint="科目名称不能超过50个字符"
                  persistent-hint
                  @keyup.enter="saveSubject"
                ></v-text-field>
              </v-col>
              <v-col cols="12">
                <v-text-field
                  v-model="subjectExamTime"
                  label="考试时间"
                  placeholder="请输入考试时间"
                  type="datetime-local"
                  variant="outlined"
                  hint="考试时间格式为YYYY-MM-DDTHH:MM"
                  persistent-hint
                ></v-text-field>
              </v-col>
            </v-row>
          </v-container>
        </v-card-text>

        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="grey" variant="text" @click="closeSubjectDialog">
            取消
          </v-btn>
          <v-btn
            color="primary"
            variant="elevated"
            @click="saveSubject"
            :loading="loading"
          >
            {{ subjectDialogMode === 'create' ? '创建' : '保存' }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- 题库上传对话框 -->
    <v-dialog v-model="showUploadDialog" max-width="500px">
      <v-card>
        <v-card-title>
          <span class="text-h5">上传题库文件</span>
        </v-card-title>

        <v-card-text>
          <v-container>
            <v-row>
              <v-col cols="12">
                <v-text-field
                  v-model="uploadTikuName"
                  label="题库名称"
                  placeholder="留空将使用文件名"
                  maxlength="50"
                  variant="outlined"
                  hint="题库名称不能超过50个字符"
                  persistent-hint
                ></v-text-field>
              </v-col>
              <v-col cols="12">
                <v-file-input
                  accept=".xlsx,.xls"
                  @change="handleFileSelect"
                  label="选择Excel文件"
                  variant="outlined"
                  prepend-icon="mdi-paperclip"
                  hint="支持 .xlsx 和 .xls 格式的Excel文件"
                  persistent-hint
                  show-size
                ></v-file-input>
              </v-col>
            </v-row>
          </v-container>
        </v-card-text>

        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="grey" variant="text" @click="closeUploadDialog">
            取消
          </v-btn>
          <v-btn
            color="primary"
            variant="elevated"
            @click="uploadTiku"
            :disabled="!uploadFile"
            :loading="uploading"
          >
            上传
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script lang="ts" setup>
import { ref, onMounted, computed, onUnmounted } from 'vue'
import { useToast } from 'vue-toastification'
import { useAuthStore } from '@/stores/auth'
import { apiService, type UserSearchParams, type Pagination, type SearchParams } from '@/services/api'
import Loading from '@/components/common/Loading.vue'
import { USER_MODEL } from '@/types'
import IconSubject from '@/components/icons/IconSubject.vue'

// 类型定义
interface User {
  id: number
  username: string
  model: number
  is_enabled: boolean
  created_at?: string
  last_time_login?: string
  invitation_code?: string
}

interface Invitation {
  id: number
  code: string
  is_used: boolean
  used_by_username?: string
  created_at?: string
  used_time?: string
  expires_at?: string
}

interface Subject {
  subject_id: number
  subject_name: string
  exam_time?: string
  created_at?: string
  updated_at?: string
}

interface Tiku {
  tiku_id: number
  tiku_name: string
  tiku_position: string
  tiku_nums: number
  file_size?: number
  is_active: boolean
  created_at?: string
  updated_at?: string
}

interface StatItem {
  used_count: number
  subject_name?: string
  tiku_name?: string
  [key: string]: any
}

interface UsageStats {
  subject_stats: StatItem[]
  tiku_stats: StatItem[]
}

// 全局类型声明，避免模板中的类型错误
declare global {
  interface VuetifySlotProps {
    item: any
    index: number
    value: any
  }
}

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
const subjectExamTime = ref('')

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
  { key: 'subjects', label: '科目管理', icon: 'subject' },
  { key: 'tiku', label: '题库管理', icon: '📖' }
]

// 当前用户ID
const currentUserId = computed(() => authStore.user?.user_id)

// 切换标签页
const switchTab = (tabKey: string) => {
  activeTab.value = tabKey
  toast.info(`已切换到${tabs.find(t => t.key === tabKey)?.label} 📌`)
}

// 加载统计信息
const loadStats = async () => {
  try {
    const response = await apiService.admin.getStats()
    if (response.success) {
      stats.value = response.stats
    } else {
      handleError(new Error(response.message), '获取统计信息')
    }
  } catch (error) {
    handleError(error, '获取统计信息')
  }
}

// 用户管理相关函数
const loadUsers = async () => {
  loading.value = true
  try {
    const response = await apiService.admin.getUsers({
      search: userSearch.value,
      order_by: userSortBy.value[0]?.key || 'id',
      order_dir: (userSortBy.value[0]?.order as 'asc' | 'desc') || 'desc',
      page: 1,
      per_page: 1000 // 加载所有数据，让Vuetify处理分页
    })
    if (response.success) {
      users.value = response.users || []
    } else {
      handleError(new Error(response.message), '获取用户列表')
    }
  } catch (error) {
    handleError(error, '获取用户列表')
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
      handleSuccess(response.message || '操作成功', () => loadStats())
    } else {
      handleError(new Error(response.message), '切换用户状态')
    }
  } catch (error) {
    handleError(error, '切换用户状态')
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
      handleSuccess(response.message || '权限更新成功', () => loadStats())
    } else {
      handleError(new Error(response.message), '更新用户权限')
      // 恢复原来的值
      loadUsers()
    }
  } catch (error) {
    handleError(error, '更新用户权限')
    // 恢复原来的值
    loadUsers()
  }
}

// 邀请码管理相关函数
const loadInvitations = async () => {
  loading.value = true
  try {
    const response = await apiService.admin.getInvitations({
      search: invitationSearch.value,
      order_by: invitationSortBy.value[0]?.key || 'id',
      order_dir: (invitationSortBy.value[0]?.order as 'asc' | 'desc') || 'desc',
      page: 1,
      per_page: 1000 // 加载所有数据，让Vuetify处理分页
    })
    if (response.success) {
      invitations.value = response.invitations || []
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
const loadSubjects = async () => {
  loading.value = true
  try {
    const response = await apiService.admin.getSubjects({
      search: subjectSearch.value,
      order_by: subjectSortBy.value[0]?.key || 'subject_id',
      order_dir: (subjectSortBy.value[0]?.order as 'asc' | 'desc') || 'desc',
      page: 1,
      per_page: 1000 // 加载所有数据，让Vuetify处理分页
    })
    if (response.success) {
      subjects.value = response.subjects || []
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
  subjectExamTime.value = mode === 'edit' ? subject?.exam_time || '' : ''
  showSubjectDialog.value = true
}

const closeSubjectDialog = () => {
  showSubjectDialog.value = false
  subjectName.value = ''
  subjectExamTime.value = ''
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
      const response = await apiService.admin.createSubject(subjectName.value.trim(), subjectExamTime.value)
      if (response.success) {
        toast.success('科目创建成功')
        closeSubjectDialog()
        loadSubjects()
        loadStats()
      } else {
        toast.error(response.message || '创建科目失败')
      }
    } else {
      const response = await apiService.admin.updateSubject(currentSubject.value.subject_id, subjectName.value.trim(), subjectExamTime.value)
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
const loadTiku = async (subjectId?: number) => {
  loading.value = true
  try {
    const response = await apiService.admin.getTiku(subjectId, {
      search: tikuSearch.value,
      order_by: tikuSortBy.value[0]?.key || 'tiku_id',
      order_dir: (tikuSortBy.value[0]?.order as 'asc' | 'desc') || 'desc',
      page: 1,
      per_page: 1000 // 加载所有数据，让Vuetify处理分页
    })
    if (response.success) {
      tikuList.value = response.tiku_list || []
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
  tikuSearch.value = ''
  if (subjectId) {
    loadTiku(subjectId)
  }
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
const formatDate = (dateString?: string) => {
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

// 新增：获取最后登录时间对应的Vuetify颜色
const getLastLoginColor = (dateString?: string) => {
  if (!dateString) return 'error'

  const loginDate = new Date(dateString)
  const now = new Date()
  const timeDiff = now.getTime() - loginDate.getTime()
  const days = Math.floor(timeDiff / (1000 * 60 * 60 * 24))

  if (days === 0) {
    return 'success' // 今天登录
  } else if (days <= 7) {
    return 'info' // 一周内登录
  } else if (days <= 30) {
    return 'warning' // 一月内登录
  } else {
    return 'grey' // 很久没登录
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
    loadUsers()
  }, 500) as unknown as number
}

const clearSearch = () => {
  userSearchParams.value.search = ''
  loadUsers()
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
  loadUsers()
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
  loadUsers()
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
  console.time('SystemControl初始化')
  try {
    await Promise.all([
      loadStats(),
      loadUsers(),
      loadInvitations(),
      loadSubjects()
    ])
    console.timeEnd('SystemControl初始化')
  } catch (error) {
    console.error('初始化失败:', error)
    console.timeEnd('SystemControl初始化')
  }
})

// 组件卸载时清理
onUnmounted(() => {
  // 清理定时器
  if (searchTimeout.value) {
    clearTimeout(searchTimeout.value)
  }
  if (invitationSearchTimeout.value) {
    clearTimeout(invitationSearchTimeout.value)
  }
  if (subjectSearchTimeout.value) {
    clearTimeout(subjectSearchTimeout.value)
  }
  if (tikuSearchTimeout.value) {
    clearTimeout(tikuSearchTimeout.value)
  }
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
    loadInvitations()
  }, 500) as unknown as number
}

const clearInvitationSearch = () => {
  invitationSearchParams.value.search = ''
  loadInvitations()
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
  loadInvitations()
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
  loadInvitations()
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
    loadSubjects()
  }, 500) as unknown as number
}

const clearSubjectSearch = () => {
  subjectSearchParams.value.search = ''
  loadSubjects()
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
  loadSubjects()
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
  loadSubjects()
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
    loadTiku(selectedSubjectId.value || undefined)
  }, 500) as unknown as number
}

const clearTikuSearch = () => {
  tikuSearchParams.value.search = ''
  loadTiku(selectedSubjectId.value || undefined)
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
  loadTiku(selectedSubjectId.value || undefined)
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
  loadTiku(selectedSubjectId.value || undefined)
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

// Vuetify Data Table 相关变量
// 用户管理表格
const userSearch = ref('')
const userItemsPerPage = ref(20)
const userSortBy = ref([{ key: 'id', order: 'desc' as const }])

// 邀请码管理表格
const invitationSearch = ref('')
const invitationItemsPerPage = ref(20)
const invitationSortBy = ref([{ key: 'id', order: 'desc' as const }])

// 科目管理表格
const subjectSearch = ref('')
const subjectItemsPerPage = ref(20)
const subjectSortBy = ref([{ key: 'subject_id', order: 'desc' as const }])

// 题库管理表格
const tikuSearch = ref('')
const tikuItemsPerPage = ref(20)
const tikuSortBy = ref([{ key: 'tiku_id', order: 'desc' as const }])

// 表格分页选项
const itemsPerPageOptions = [
  { value: 10, title: '10条/页' },
  { value: 20, title: '20条/页' },
  { value: 50, title: '50条/页' },
  { value: 100, title: '100条/页' },
  { value: -1, title: '全部显示' }
]

// 通用表格配置
const tableConfig = {
  density: 'comfortable' as const,
  hover: true,
  sticky: true,
  fixedHeader: true,
  height: '600px',
  loadingText: '数据加载中...',
  noDataText: '暂无数据',
  noResultsText: '没有找到匹配的数据',
  itemsPerPageText: '每页显示条数:',
  pageText: '{0}-{1} 共 {2} 条',
  class: 'elevation-2 data-table-enhanced'
}

// 用户表格表头
const userHeaders = [
  { title: 'ID', key: 'id', sortable: true, width: '80px' },
  { title: '用户名', key: 'username', sortable: true, width: '150px' },
  { title: '权限等级', key: 'model', sortable: true, width: '120px' },
  { title: '状态', key: 'is_enabled', sortable: false, width: '100px' },
  { title: '注册时间', key: 'created_at', sortable: true, width: '160px' },
  { title: '最后登录', key: 'last_time_login', sortable: true, width: '160px' },
  { title: '邀请码', key: 'invitation_code', sortable: false, width: '150px' },
  { title: '操作', key: 'actions', sortable: false, width: '120px', align: 'center' as const }
]

// 邀请码表格表头
const invitationHeaders = [
  { title: 'ID', key: 'id', sortable: true, width: '80px' },
  { title: '邀请码', key: 'code', sortable: false, width: '180px' },
  { title: '状态', key: 'is_used', sortable: false, width: '100px' },
  { title: '使用者', key: 'used_by_username', sortable: false, width: '120px' },
  { title: '创建时间', key: 'created_at', sortable: true, width: '160px' },
  { title: '使用时间', key: 'used_time', sortable: false, width: '160px' },
  { title: '过期时间', key: 'expires_at', sortable: false, width: '160px' }
]

// 科目表格表头
const subjectHeaders = [
  { title: 'ID', key: 'subject_id', sortable: true, width: '80px' },
  { title: '科目名称', key: 'subject_name', sortable: true, width: '200px' },
  { title: '考试时间', key: 'exam_time', sortable: true, width: '180px' },
  { title: '创建时间', key: 'created_at', sortable: true, width: '160px' },
  { title: '更新时间', key: 'updated_at', sortable: true, width: '160px' },
  { title: '操作', key: 'actions', sortable: false, width: '150px', align: 'center' as const }
]

// 题库表格表头
const tikuHeaders = [
  { title: '题库名称', key: 'tiku_name', sortable: true, width: '250px' },
  { title: '题目数量', key: 'tiku_nums', sortable: true, width: '120px', align: 'center' as const },
  { title: '文件大小', key: 'file_size', sortable: true, width: '120px', align: 'center' as const },
  { title: '状态', key: 'is_active', sortable: false, width: '100px', align: 'center' as const },
  { title: '创建时间', key: 'created_at', sortable: true, width: '160px' },
  { title: '更新时间', key: 'updated_at', sortable: true, width: '160px' },
  { title: '操作', key: 'actions', sortable: false, width: '150px', align: 'center' as const }
]

// 统计表格表头
const subjectStatsHeaders = [
  { title: '排名', key: 'rank', sortable: false, width: '80px', align: 'center' as const },
  { title: '科目名称', key: 'subject_name', sortable: false, width: '200px' },
  { title: '使用次数', key: 'used_count', sortable: true, width: '120px', align: 'center' as const },
  { title: '使用率', key: 'usage_rate', sortable: false, width: '150px', align: 'center' as const }
]

const tikuStatsHeaders = [
  { title: '排名', key: 'rank', sortable: false, width: '80px', align: 'center' as const },
  { title: '题库名称', key: 'tiku_name', sortable: false, width: '200px' },
  { title: '所属科目', key: 'subject_name', sortable: false, width: '150px', align: 'center' as const },
  { title: '使用次数', key: 'used_count', sortable: true, width: '120px', align: 'center' as const },
  { title: '使用率', key: 'usage_rate', sortable: false, width: '150px', align: 'center' as const }
]

// 权限等级选项
const modelOptions = [
  { title: '普通用户', value: 0 },
  { title: 'VIP用户', value: 5 },
  { title: 'ROOT用户', value: 10 }
]

// 计算属性优化
const filteredUsers = computed(() => {
  if (!userSearch.value) return users.value
  const searchTerm = userSearch.value.toLowerCase()
  return users.value.filter((user: any) => 
    user.username?.toLowerCase().includes(searchTerm) ||
    (user.invitation_code && user.invitation_code.toLowerCase().includes(searchTerm))
  )
})

const filteredInvitations = computed(() => {
  if (!invitationSearch.value) return invitations.value
  const searchTerm = invitationSearch.value.toLowerCase()
  return invitations.value.filter((invitation: any) => 
    invitation.code?.toLowerCase().includes(searchTerm) ||
    (invitation.used_by_username && invitation.used_by_username.toLowerCase().includes(searchTerm))
  )
})

const filteredSubjects = computed(() => {
  if (!subjectSearch.value) return subjects.value
  const searchTerm = subjectSearch.value.toLowerCase()
  return subjects.value.filter((subject: any) => 
    subject.subject_name?.toLowerCase().includes(searchTerm)
  )
})

const filteredTiku = computed(() => {
  if (!tikuSearch.value) return tikuList.value
  const searchTerm = tikuSearch.value.toLowerCase()
  return tikuList.value.filter((tiku: any) => 
    tiku.tiku_name?.toLowerCase().includes(searchTerm) ||
    tiku.tiku_position?.toLowerCase().includes(searchTerm)
  )
})

// 性能优化：缓存表格配置
const tableConfigMemo = computed(() => ({
  density: 'comfortable' as const,
  hover: true,
  sticky: true,
  fixedHeader: true,
  height: '600px',
  loadingText: '数据加载中...',
  noDataText: '暂无数据',
  noResultsText: '没有找到匹配的数据',
  itemsPerPageText: '每页显示条数:',
  pageText: '{0}-{1} 共 {2} 条',
  class: 'elevation-2 data-table-enhanced'
}))

// 新增：防抖搜索优化
const debouncedLoadUsers = (() => {
  let timeout: number | null = null
  return () => {
    if (timeout) clearTimeout(timeout)
    timeout = setTimeout(() => {
      loadUsers()
    }, 300) as unknown as number
  }
})()

const debouncedLoadInvitations = (() => {
  let timeout: number | null = null
  return () => {
    if (timeout) clearTimeout(timeout)
    timeout = setTimeout(() => {
      loadInvitations()
    }, 300) as unknown as number
  }
})()

const debouncedLoadSubjects = (() => {
  let timeout: number | null = null
  return () => {
    if (timeout) clearTimeout(timeout)
    timeout = setTimeout(() => {
      loadSubjects()
    }, 300) as unknown as number
  }
})()

const debouncedLoadTiku = (() => {
  let timeout: number | null = null
  return () => {
    if (timeout) clearTimeout(timeout)
    timeout = setTimeout(() => {
      loadTiku(selectedSubjectId.value || undefined)
    }, 300) as unknown as number
  }
})()

// 错误处理优化
const handleError = (error: any, operation: string) => {
  console.error(`${operation}失败:`, error)
  const message = error?.response?.data?.message || error?.message || `${operation}失败`
  toast.error(message)
}

// 成功处理优化
const handleSuccess = (message: string, callback?: () => void) => {
  toast.success(message)
  if (callback) callback()
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
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 2rem;
  margin-bottom: 0.75rem;
  filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.1));
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
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 0.5rem;
  font-size: 1.2rem;
  transition: all 0.3s ease;
}

.tab-button:hover .tab-icon {
  transform: scale(1.1);
}

.tab-button.active .tab-icon {
  color: #3b82f6;
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

/* Vuetify Data Table 优化样式 */
.data-table-enhanced {
  border-radius: 12px !important;
  overflow: hidden;
}

.data-table-enhanced .v-data-table__wrapper {
  border-radius: 12px;
}

.data-table-enhanced .v-data-table-header {
  background: #f8fafc !important;
}

.data-table-enhanced .v-data-table-header th {
  background: #f8fafc !important;
  color: #374151 !important;
  font-weight: 600 !important;
  border-bottom: 2px solid #e2e8f0 !important;
}

.data-table-enhanced .v-data-table__td {
  border-bottom: 1px solid #f1f5f9 !important;
}

.data-table-enhanced .v-data-table__tr:hover {
  background: #fafbfc !important;
}

.data-table-enhanced .v-data-table__tr.v-data-table__tr--disabled {
  opacity: 0.6;
  background: #fef2f2 !important;
}

/* 加载状态样式 */
.data-table-enhanced .v-data-table-progress {
  background: linear-gradient(90deg, #f3f4f6, #e5e7eb, #f3f4f6);
  background-size: 200% 100%;
  animation: loading-shimmer 1.5s infinite;
}

@keyframes loading-shimmer {
  0% {
    background-position: -200% 0;
  }
  100% {
    background-position: 200% 0;
  }
}

/* 搜索框优化 */
.v-text-field .v-field__input {
  padding: 8px 12px !important;
}

.v-text-field--variant-outlined .v-field__outline {
  --v-field-border-opacity: 0.38;
  border-radius: 8px;
}

.v-text-field--variant-outlined.v-field--focused .v-field__outline {
  --v-field-border-width: 2px;
  --v-field-border-opacity: 1;
}

/* 芯片样式优化 */
.v-chip--size-small {
  font-size: 0.75rem !important;
  height: 24px !important;
  padding: 0 8px !important;
}

/* 按钮样式优化 */
.v-btn--size-small {
  min-width: 64px !important;
  height: 32px !important;
  padding: 0 12px !important;
  font-size: 0.75rem !important;
}

/* 分页样式优化 */
.v-data-table-footer {
  padding: 16px !important;
  background: #f8fafc !important;
  border-top: 1px solid #e2e8f0 !important;
}

.v-data-table-footer__info {
  color: #6b7280 !important;
  font-size: 0.875rem !important;
}

.v-data-table-footer__pagination {
  color: #374151 !important;
}

/* 响应式优化 */
@media (max-width: 768px) {
  .data-table-enhanced {
    font-size: 0.875rem;
  }
  
  .data-table-enhanced .v-data-table__td {
    padding: 8px 4px !important;
  }
  
  .data-table-enhanced .v-data-table-header th {
    padding: 8px 4px !important;
  }
  
  .v-chip--size-small {
    font-size: 0.6875rem !important;
    height: 20px !important;
    padding: 0 6px !important;
  }
  
  .v-btn--size-small {
    min-width: 48px !important;
    height: 28px !important;
    padding: 0 8px !important;
    font-size: 0.6875rem !important;
  }

  /* 移动端每页条数选择框优化 */
  .v-data-table-footer__items-per-page .v-input,
  .v-data-table-footer__items-per-page .v-select {
    min-width: 120px !important; /* 增加移动端宽度 */
    max-width: 140px !important;
    width: 120px !important;
  }
  
  .v-data-table-footer__items-per-page .v-field__input {
    min-width: 100px !important; /* 增加移动端输入框宽度 */
    width: 100px !important;
    font-size: 0.875rem !important;
  }
  
  /* 移动端深层选择器 */
  :deep(.v-data-table-footer__items-per-page .v-input) {
    min-width: 120px !important;
    width: 120px !important;
  }
  
  :deep(.v-data-table-footer__items-per-page .v-field__input) {
    min-width: 100px !important;
    width: 100px !important;
  }
}

/* 空状态样式优化 */
.v-data-table__empty {
  padding: 64px 24px !important;
  text-align: center;
  color: #9ca3af !important;
}

.v-data-table__empty::before {
  content: "📊";
  display: block;
  font-size: 3rem;
  margin-bottom: 16px;
  opacity: 0.5;
}

/* 进度条样式 */
.v-progress-linear {
  border-radius: 4px !important;
  overflow: hidden !important;
}

.v-progress-linear__determinate {
  background: linear-gradient(90deg, #3b82f6, #2563eb) !important;
}

/* 对话框样式优化 */
.v-dialog .v-card {
  border-radius: 16px !important;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04) !important;
}

.v-card-title {
  padding: 24px 24px 16px !important;
  font-size: 1.25rem !important;
  font-weight: 600 !important;
  color: #1e293b !important;
}

.v-card-text {
  padding: 0 24px 16px !important;
}

.v-card-actions {
  padding: 16px 24px 24px !important;
  gap: 12px;
}

/* 文件上传组件样式 */
.v-file-input .v-field__input {
  cursor: pointer;
}

.v-file-input .v-field__overlay {
  background: linear-gradient(135deg, #f9fafb 0%, #f3f4f6 100%);
  border: 2px dashed #d1d5db;
  border-radius: 8px;
  transition: all 0.2s ease;
}

.v-file-input:hover .v-field__overlay {
  border-color: #9ca3af;
  background: linear-gradient(135deg, #f3f4f6 0%, #e5e7eb 100%);
}

.v-file-input.v-field--focused .v-field__overlay {
  border-color: #3b82f6;
  background: white;
}

/* 选择器样式优化 */
.v-select .v-field__input {
  cursor: pointer;
}

.v-select--variant-outlined .v-field__outline {
  border-radius: 6px;
}

/* 芯片组样式优化 */
.v-chip-group {
  padding: 8px 0;
}

.v-chip-group .v-chip {
  margin: 4px;
  transition: all 0.2s ease;
}

.v-chip-group .v-chip:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
}

.v-chip-group .v-chip--selected {
  background: linear-gradient(135deg, #3b82f6, #2563eb) !important;
  color: white !important;
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
}

/* 性能优化：使用GPU加速 */
.stat-card,
.tab-button,
.control-section,
.v-btn,
.v-chip {
  transform: translateZ(0);
  will-change: transform, opacity;
}

/* 减少重排和重绘 */
.system-control-content * {
  box-sizing: border-box;
}

/* 优化滚动性能 */
.system-control-content {
  -webkit-overflow-scrolling: touch;
  scroll-behavior: smooth;
}

/* 减少动画开销 */
@media (prefers-reduced-motion: reduce) {
  * {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}

/* 移动端优化 */
@media (max-width: 480px) {
  .system-control-content {
    padding: 0.5rem;
  }
  
  .stat-card {
    padding: 1rem;
    flex-direction: column;
    text-align: center;
  }
  
  .stat-icon {
    margin-bottom: 0.5rem;
  }
  
  .control-tabs {
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
  }
  
  .tab-button {
    white-space: nowrap;
    min-width: 120px;
  }
}

/* 打印样式优化 */
@media print {
  .system-control-content {
    background: white !important;
    box-shadow: none !important;
  }
  
  .control-tabs,
  .section-actions,
  .v-btn {
    display: none !important;
  }
  
  .control-section {
    break-inside: avoid;
    page-break-inside: avoid;
  }
}

/* 高对比度模式优化 */
@media (prefers-contrast: high) {
  .stat-card,
  .control-section {
    border: 2px solid #000;
  }
  
  .tab-button.active {
    background: #000 !important;
    color: #fff !important;
  }
}

/* 优化每页条数下拉选择框样式 */
.v-data-table-footer__items-per-page .v-input,
.v-data-table-footer__items-per-page .v-select {
  min-width: 100px !important; /* 增加最小宽度确保完整显示 */
  max-width: 120px !important; /* 设置最大宽度避免过宽 */
  flex-grow: 0 !important;    /* 防止在 flex 布局中被压缩 */
  flex-shrink: 0 !important;  /* 防止在 flex 布局中被压缩 */
}

.v-data-table-footer__items-per-page .v-field__input {
  min-width: 80px !important;
  text-align: center !important; /* 文本居中显示 */
  white-space: nowrap !important; /* 防止文本换行 */
  overflow: hidden !important;
  text-overflow: clip !important; /* 不显示省略号 */
}

.v-data-table-footer__items-per-page .v-select__selection {
  max-width: none !important; /* 移除选中项的最大宽度限制 */
  width: 100% !important;
}

.v-data-table-footer__items-per-page .v-field {
  min-width: 80px !important;
}

/* 确保下拉菜单选项完整显示 */
.v-data-table-footer__items-per-page .v-list-item {
  min-width: 80px !important;
  text-align: center !important;
}

.v-data-table-footer__items-per-page .v-list-item-title {
  white-space: nowrap !important;
  overflow: visible !important;
  text-overflow: clip !important;
}

/* 优化每页条数下拉选择框样式 */
.v-data-table-footer__items-per-page .v-input,
.v-data-table-footer__items-per-page .v-select {
  min-width: 130px !important; /* 大幅增加最小宽度 */
  max-width: 150px !important; /* 增加最大宽度 */
  flex-grow: 0 !important;
  flex-shrink: 0 !important;
  width: 130px !important; /* 强制设置固定宽度 */
}

.v-data-table-footer__items-per-page .v-field__input {
  min-width: 110px !important; /* 增加输入框宽度 */
  width: 110px !important;
  text-align: center !important;
  white-space: nowrap !important;
  overflow: visible !important; /* 改为visible确保内容显示 */
  text-overflow: clip !important;
}

.v-data-table-footer__items-per-page .v-select__selection {
  max-width: none !important;
  width: 100% !important;
  min-width: 110px !important;
}

.v-data-table-footer__items-per-page .v-field {
  min-width: 110px !important;
  width: 130px !important;
}

/* 更强力的样式覆盖 */
.v-data-table .v-data-table-footer .v-data-table-footer__items-per-page {
  min-width: 150px !important;
  flex-shrink: 0 !important;
}

.v-data-table .v-data-table-footer .v-data-table-footer__items-per-page .v-input__control {
  min-width: 130px !important;
  width: 130px !important;
}

.v-data-table .v-data-table-footer .v-data-table-footer__items-per-page .v-field__field {
  min-width: 110px !important;
  width: 110px !important;
}

/* 深层选择器覆盖 */
:deep(.v-data-table-footer__items-per-page .v-input) {
  min-width: 130px !important;
  width: 130px !important;
}

:deep(.v-data-table-footer__items-per-page .v-field__input) {
  min-width: 110px !important;
  width: 110px !important;
  text-align: center !important;
}

:deep(.v-data-table-footer__items-per-page .v-select__selection-text) {
  max-width: none !important;
  width: 100% !important;
  white-space: nowrap !important;
  overflow: visible !important;
}

/* 确保下拉菜单选项完整显示 */
.v-data-table-footer__items-per-page .v-list-item {
  min-width: 110px !important;
  text-align: center !important;
}

.v-data-table-footer__items-per-page .v-list-item-title {
  white-space: nowrap !important;
  overflow: visible !important;
  text-overflow: clip !important;
}

/* 全局强制样式 - 确保每页条数完整显示 */
.v-data-table-footer__items-per-page {
  min-width: 160px !important;
  width: auto !important;
}

.v-data-table-footer__items-per-page * {
  min-width: inherit !important;
  max-width: none !important;
  white-space: nowrap !important;
  overflow: visible !important;
  text-overflow: unset !important;
}

/* 最终兜底方案 */
.v-data-table-footer .v-data-table-footer__items-per-page .v-field__input,
.v-data-table-footer .v-data-table-footer__items-per-page .v-select__selection-text,
.v-data-table-footer .v-data-table-footer__items-per-page .v-input__control,
.v-data-table-footer .v-data-table-footer__items-per-page .v-field__field {
  width: auto !important;
  min-width: 120px !important;
  max-width: none !important;
  flex: none !important;
}

/* 标题图标样式 */
.section-title .title-icon {
  margin-right: 0.5rem;
  filter: drop-shadow(0 2px 4px rgba(59, 130, 246, 0.3));
  vertical-align: middle;
}
</style>
