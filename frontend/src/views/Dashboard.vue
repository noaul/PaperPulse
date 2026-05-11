<template>
  <div class="space-y-6">
    <!-- Stats Cards -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
      <div
        v-for="stat in statsCards"
        :key="stat.label"
        class="bg-white rounded-xl shadow-sm border border-gray-200 p-5 overflow-hidden relative"
      >
        <div class="absolute inset-x-0 top-0 h-1" :class="stat.accent"></div>
        <div class="flex items-center justify-between">
          <div>
            <p class="text-xs font-medium uppercase tracking-wide text-gray-500">{{ stat.label }}</p>
            <p class="text-3xl font-semibold mt-2" :class="stat.color">
              {{ statsLoading ? '-' : stat.value }}
            </p>
          </div>
          <div :class="['w-10 h-10 rounded-lg flex items-center justify-center', stat.bgColor]">
            <div class="w-5 h-5" v-html="stat.icon"></div>
          </div>
        </div>
      </div>
    </div>

    <!-- Quick Actions -->
    <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <div class="flex flex-col md:flex-row md:items-center md:justify-between gap-2 mb-4">
        <div>
          <h2 class="text-lg font-semibold text-gray-800">快速操作</h2>
          <p class="text-sm text-gray-500 mt-1">抓取、分析、发送报告和完整工作流入口</p>
        </div>
      </div>
      <div class="flex flex-wrap gap-3">
        <button
          @click="fetchAll"
          :disabled="actionLoading || analysisRunning"
          class="inline-flex items-center px-4 py-2.5 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          <svg class="w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          抓取全部订阅
        </button>
        <button
          @click="runAnalysis"
          :disabled="actionLoading || analysisRunning"
          class="inline-flex items-center px-4 py-2.5 bg-purple-600 text-white text-sm font-medium rounded-lg hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          <svg class="w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
          </svg>
          运行分析
        </button>
        <button
          @click="sendReport"
          :disabled="actionLoading"
          class="inline-flex items-center px-4 py-2.5 bg-green-600 text-white text-sm font-medium rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          <svg class="w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
          </svg>
          发送报告
        </button>
        <button
          @click="fetchAndAnalyze"
          :disabled="actionLoading || analysisRunning"
          class="inline-flex items-center px-4 py-2.5 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          <svg class="w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M13 10V3L4 14h7v7l9-11h-7z" />
          </svg>
          一键抓取并分析
        </button>
        <button
          @click="runDailyWorkflow"
          :disabled="actionLoading || analysisRunning"
          class="inline-flex items-center px-4 py-2.5 bg-slate-800 text-white text-sm font-medium rounded-lg hover:bg-slate-900 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          <svg class="w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l.928 2.856a2 2 0 001.265 1.265l2.856.928c.921.3.921 1.603 0 1.902l-2.856.928a2 2 0 00-1.265 1.265l-.928 2.856c-.3.921-1.603.921-1.902 0l-.928-2.856a2 2 0 00-1.265-1.265L6 9.878c-.921-.3-.921-1.603 0-1.902l2.856-.928a2 2 0 001.265-1.265l.928-2.856z" />
          </svg>
          运行完整工作流
        </button>
      </div>
    </div>

    <!-- Analysis Progress -->
    <div v-if="analysisProgressExecution" class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <div class="flex items-center justify-between gap-4 mb-4">
        <div>
          <h2 class="text-lg font-semibold text-gray-800">文献汇总分析进度</h2>
          <p class="text-sm text-gray-500 mt-1">
            {{ workflowLabel(analysisProgressExecution.workflow_name) }} · {{ statusText(analysisProgressExecution.status) }}
          </p>
        </div>
        <div class="flex items-center gap-2">
          <span :class="['px-3 py-1 rounded-full text-sm font-medium', statusBadgeClass(analysisProgressExecution.status)]">
            {{ analysisProgressPercent }}%
          </span>
          <button
            v-if="analysisProgressExecution.status === 'running'"
            @click="pauseAnalysisExecution"
            :disabled="controlLoading"
            class="px-3 py-1.5 rounded-lg text-sm font-medium bg-yellow-100 text-yellow-800 hover:bg-yellow-200 disabled:opacity-50"
          >
            暂停
          </button>
          <button
            v-if="analysisProgressExecution.status === 'paused'"
            @click="resumeAnalysisExecution"
            :disabled="controlLoading"
            class="px-3 py-1.5 rounded-lg text-sm font-medium bg-blue-100 text-blue-800 hover:bg-blue-200 disabled:opacity-50"
          >
            继续
          </button>
          <button
            v-if="['running', 'paused'].includes(analysisProgressExecution.status)"
            @click="cancelAnalysisExecution"
            :disabled="controlLoading"
            class="px-3 py-1.5 rounded-lg text-sm font-medium bg-red-100 text-red-800 hover:bg-red-200 disabled:opacity-50"
          >
            取消
          </button>
        </div>
      </div>

      <div class="h-3 bg-gray-100 rounded-full overflow-hidden">
        <div
          class="h-full bg-blue-600 transition-all duration-500"
          :style="{ width: `${analysisProgressPercent}%` }"
        ></div>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mt-4">
        <div class="rounded-lg bg-blue-50 p-4">
          <p class="text-xs text-blue-600">已分析 / 总数</p>
          <p class="text-2xl font-semibold text-blue-900 mt-1">
            {{ analysisProgress.analyzed }} / {{ analysisProgress.total }}
          </p>
        </div>
        <div class="rounded-lg bg-green-50 p-4">
          <p class="text-xs text-green-600">和主题词相关</p>
          <p class="text-2xl font-semibold text-green-900 mt-1">
            {{ analysisProgress.related }}
          </p>
        </div>
        <div class="rounded-lg bg-purple-50 p-4">
          <p class="text-xs text-purple-600">相关分析结果</p>
          <p class="text-2xl font-semibold text-purple-900 mt-1">
            {{ analysisProgress.results }}
          </p>
        </div>
      </div>

      <p v-if="analysisProgress.currentTitle && analysisProgressExecution.status === 'running'" class="text-sm text-gray-500 mt-4 truncate">
        正在分析：{{ analysisProgress.currentTitle }}
      </p>
      <p v-if="analysisProgress.summary" class="text-sm text-gray-700 mt-4 rounded-lg bg-gray-50 p-3">
        {{ analysisProgress.summary }}
      </p>
      <p v-if="analysisProgressExecution.error_message" class="text-sm text-red-600 mt-4 rounded-lg bg-red-50 p-3">
        {{ analysisProgressExecution.error_message }}
      </p>
    </div>

    <!-- Workflow Executions -->
    <div class="grid grid-cols-1 xl:grid-cols-3 gap-6">
      <div class="xl:col-span-2 bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <div class="flex items-center justify-between mb-4">
          <div>
            <h2 class="text-lg font-semibold text-gray-800">工作流执行记录</h2>
            <p class="text-sm text-gray-500 mt-1">抓取、AI 分析、邮件和 WebDAV 备份的可观测日志</p>
          </div>
          <button
            @click="loadExecutions(true)"
            :disabled="executionsLoading"
            class="text-sm text-blue-600 hover:text-blue-800 disabled:opacity-50"
          >
            刷新
          </button>
        </div>

        <div v-if="executionsLoading" class="flex justify-center py-8">
          <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        </div>

        <div v-else-if="executions.length === 0" class="text-center py-8 text-gray-500">
          暂无执行记录，点击上方快速操作后会生成日志
        </div>

        <div v-else class="space-y-3">
          <button
            v-for="execution in executions"
            :key="execution.id"
            @click="loadExecutionDetail(execution.id)"
            class="w-full text-left p-4 rounded-lg border transition-colors"
            :class="selectedExecution?.id === execution.id ? 'border-blue-300 bg-blue-50' : 'border-gray-100 hover:bg-gray-50'"
          >
            <div class="flex items-start justify-between gap-4">
              <div class="min-w-0">
                <div class="flex items-center gap-2">
                  <span class="text-sm font-semibold text-gray-800">{{ workflowLabel(execution.workflow_name) }}</span>
                  <span :class="['px-2 py-0.5 rounded-full text-xs font-medium', statusBadgeClass(execution.status)]">
                    {{ statusText(execution.status) }}
                  </span>
                </div>
                <p class="text-xs text-gray-500 mt-1">
                  #{{ execution.id }} · {{ formatDateTime(execution.started_at) }} · {{ formatDuration(execution.duration_ms) }}
                </p>
                <p class="text-xs text-gray-600 mt-2 truncate">
                  {{ summaryText(execution.summary) }}
                </p>
              </div>
              <span class="text-xs text-gray-400 flex-shrink-0">查看日志</span>
            </div>
          </button>
        </div>
      </div>

      <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <h2 class="text-lg font-semibold text-gray-800 mb-4">执行详情</h2>

        <div v-if="detailLoading" class="flex justify-center py-8">
          <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        </div>

        <div v-else-if="!selectedExecution" class="text-sm text-gray-500 py-8 text-center">
          选择一条执行记录查看节点日志
        </div>

        <div v-else class="space-y-4">
          <div class="rounded-lg bg-gray-50 p-4">
            <div class="flex items-center justify-between">
              <span class="font-medium text-gray-800">{{ workflowLabel(selectedExecution.workflow_name) }}</span>
              <span :class="['px-2 py-0.5 rounded-full text-xs font-medium', statusBadgeClass(selectedExecution.status)]">
                {{ statusText(selectedExecution.status) }}
              </span>
            </div>
            <p class="text-xs text-gray-500 mt-2">{{ formatDateTime(selectedExecution.started_at) }}</p>
            <p v-if="selectedExecution.error_message" class="text-xs text-red-600 mt-2">
              {{ selectedExecution.error_message }}
            </p>
          </div>

          <div>
            <h3 class="text-sm font-medium text-gray-700 mb-2">节点日志</h3>
            <div class="space-y-2 max-h-96 overflow-y-auto pr-1">
              <div
                v-for="log in selectedExecution.logs"
                :key="log.id"
                class="rounded-lg border border-gray-100 p-3"
              >
                <div class="flex items-center justify-between gap-2">
                  <span class="text-xs font-semibold text-gray-700">{{ log.node_name }}</span>
                  <span :class="['px-2 py-0.5 rounded-full text-[11px] font-medium', logLevelClass(log.level)]">
                    {{ log.level }}
                  </span>
                </div>
                <p class="text-sm text-gray-700 mt-1">{{ log.message }}</p>
                <p class="text-[11px] text-gray-400 mt-1">{{ formatDateTime(log.created_at) }}</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Recent High-Relevance Papers -->
    <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-lg font-semibold text-gray-800">近期高相关性论文</h2>
        <router-link to="/papers" class="text-sm text-blue-600 hover:text-blue-800">
          查看全部 →
        </router-link>
      </div>

      <div v-if="papersLoading" class="flex justify-center py-8">
        <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>

      <div v-else-if="recentPapers.length === 0" class="text-center py-8 text-gray-500">
        暂无高相关性论文
      </div>

      <div v-else class="space-y-3">
        <div
          v-for="paper in recentPapers"
          :key="paper.id"
          class="flex items-center justify-between p-4 rounded-lg border border-gray-100 hover:bg-gray-50 transition-colors"
        >
          <div class="flex-1 min-w-0 mr-4">
            <h3 class="text-sm font-medium text-gray-800 truncate">{{ paper.title }}</h3>
            <p class="text-xs text-gray-500 mt-1">
              {{ paper.journal }} · {{ paper.published_date }}
            </p>
          </div>
          <span
            :class="[
              'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium flex-shrink-0',
              scoreBadgeClass(paper.relevance_score),
            ]"
          >
            {{ paper.relevance_score.toFixed(1) }}
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { dashboardApi, analysisApi, executionApi, workflowApi } from '@/api'
import type { DashboardStats, RecentPaper, WorkflowExecution, WorkflowExecutionDetail } from '@/api'
import { useAppStore } from '@/stores/app'

const appStore = useAppStore()

const stats = ref<DashboardStats>({
  total_feeds: 0,
  total_papers: 0,
  today_papers: 0,
  today_analyses: 0,
  high_relevance_today: 0,
})
const recentPapers = ref<RecentPaper[]>([])
const executions = ref<WorkflowExecution[]>([])
const selectedExecution = ref<WorkflowExecutionDetail | null>(null)
const activeAnalysisExecution = ref<WorkflowExecutionDetail | null>(null)
const statsLoading = ref(true)
const papersLoading = ref(true)
const executionsLoading = ref(true)
const detailLoading = ref(false)
const actionLoading = ref(false)
const controlLoading = ref(false)
let progressTimer: ReturnType<typeof setInterval> | null = null

const statsCards = computed(() => [
  {
    label: '订阅源总数',
    value: stats.value.total_feeds,
    color: 'text-gray-900',
    bgColor: 'bg-blue-50',
    accent: 'bg-blue-500',
    icon: '<svg fill="none" viewBox="0 0 24 24" stroke="#2563eb"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 5c7.18 0 13 5.82 13 13M6 11a7 7 0 017 7m-6 0a1 1 0 11-2 0 1 1 0 012 0z" /></svg>',
  },
  {
    label: '论文总数',
    value: stats.value.total_papers,
    color: 'text-gray-900',
    bgColor: 'bg-purple-50',
    accent: 'bg-indigo-500',
    icon: '<svg fill="none" viewBox="0 0 24 24" stroke="#7c3aed"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>',
  },
  {
    label: '今日新论文',
    value: stats.value.today_papers,
    color: 'text-green-600',
    bgColor: 'bg-green-50',
    accent: 'bg-green-500',
    icon: '<svg fill="none" viewBox="0 0 24 24" stroke="#16a34a"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6" /></svg>',
  },
  {
    label: '今日分析',
    value: stats.value.today_analyses,
    color: 'text-orange-600',
    bgColor: 'bg-orange-50',
    accent: 'bg-amber-500',
    icon: '<svg fill="none" viewBox="0 0 24 24" stroke="#ea580c"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" /></svg>',
  },
  {
    label: '今日高相关',
    value: stats.value.high_relevance_today,
    color: 'text-red-600',
    bgColor: 'bg-red-50',
    accent: 'bg-red-500',
    icon: '<svg fill="none" viewBox="0 0 24 24" stroke="#dc2626"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z" /></svg>',
  },
])

const analysisProgressExecution = computed(() => {
  if (activeAnalysisExecution.value) return activeAnalysisExecution.value
  if (selectedExecution.value && hasAnalysisProgress(selectedExecution.value.summary)) {
    return selectedExecution.value
  }
  return executions.value.find((item) => hasAnalysisProgress(item.summary)) || null
})

const analysisProgress = computed(() => {
  const summary = analysisProgressExecution.value?.summary || {}
  return {
    total: Number(summary.analysis_total || 0),
    analyzed: Number(summary.analysis_analyzed || summary.analyzed || 0),
    related: Number(summary.analysis_related || 0),
    results: Number(summary.analysis_results || summary.analyses || 0),
    currentTitle: String(summary.analysis_current_title || ''),
    summary: String(summary.literature_summary || ''),
  }
})

const analysisProgressPercent = computed(() => {
  const total = analysisProgress.value.total
  const analyzed = analysisProgress.value.analyzed
  if (total <= 0) {
    return analysisProgressExecution.value?.status === 'success' ? 100 : 0
  }
  return Math.min(100, Math.round((analyzed / total) * 100))
})

const analysisRunning = computed(() => {
  const status = analysisProgressExecution.value?.status
  return status === 'running' || status === 'paused'
})

function hasAnalysisProgress(summary: Record<string, unknown>): boolean {
  return Object.prototype.hasOwnProperty.call(summary, 'analysis_total')
}

function scoreBadgeClass(score: number): string {
  if (score >= 7) return 'bg-green-100 text-green-800'
  if (score >= 5) return 'bg-yellow-100 text-yellow-800'
  return 'bg-red-100 text-red-800'
}

function statusBadgeClass(status: string): string {
  if (status === 'success') return 'bg-green-100 text-green-800'
  if (status === 'failed') return 'bg-red-100 text-red-800'
  if (status === 'cancelled') return 'bg-gray-200 text-gray-700'
  if (status === 'paused') return 'bg-yellow-100 text-yellow-800'
  if (status === 'running') return 'bg-blue-100 text-blue-800'
  return 'bg-gray-100 text-gray-700'
}

function logLevelClass(level: string): string {
  if (level === 'error') return 'bg-red-100 text-red-800'
  if (level === 'warning') return 'bg-yellow-100 text-yellow-800'
  return 'bg-gray-100 text-gray-700'
}

function statusText(status: string): string {
  const labels: Record<string, string> = {
    pending: '等待中',
    running: '运行中',
    paused: '已暂停',
    cancelled: '已取消',
    success: '成功',
    failed: '失败',
  }
  return labels[status] || status
}

function workflowLabel(name: string): string {
  const labels: Record<string, string> = {
    'manual-analysis': '手动 AI 分析',
    'manual-fetch-analyze': '手动抓取并分析',
    'manual-send-report': '手动发送报告',
    'daily-paperpulse': '每日完整工作流',
  }
  return labels[name] || name
}

function formatDateTime(value: string | null): string {
  if (!value) return '-'
  return new Date(value).toLocaleString('zh-CN', { hour12: false })
}

function formatDuration(value: number | null): string {
  if (value === null || value === undefined) return '-'
  if (value < 1000) return `${value}ms`
  return `${(value / 1000).toFixed(1)}s`
}

function summaryText(summary: Record<string, unknown>): string {
  const parts = [
    typeof summary.new_papers === 'number' ? `新增论文 ${summary.new_papers}` : '',
    typeof summary.analyses === 'number' ? `分析结果 ${summary.analyses}` : '',
    typeof summary.email_sent === 'boolean' ? `邮件${summary.email_sent ? '已发送' : '未发送'}` : '',
    typeof summary.webdav_exported === 'boolean' ? `WebDAV${summary.webdav_exported ? '已备份' : '未备份'}` : '',
  ].filter(Boolean)
  return parts.length ? parts.join(' · ') : '无摘要'
}

async function loadStats() {
  statsLoading.value = true
  try {
    const { data } = await dashboardApi.getStats()
    stats.value = data
  } catch (err: any) {
    appStore.error('加载统计数据失败: ' + err.message)
  } finally {
    statsLoading.value = false
  }
}

async function loadRecentPapers() {
  papersLoading.value = true
  try {
    const { data } = await dashboardApi.getRecentHighRelevance(10)
    recentPapers.value = data
  } catch (err: any) {
    appStore.error('加载近期论文失败: ' + err.message)
  } finally {
    papersLoading.value = false
  }
}

async function loadExecutions(selectFirst = false) {
  executionsLoading.value = true
  try {
    const { data } = await executionApi.list({ limit: 8 })
    executions.value = data
    if (selectFirst && data.length > 0) {
      await loadExecutionDetail(data[0].id)
    } else if (selectedExecution.value && !data.some((item) => item.id === selectedExecution.value?.id)) {
      selectedExecution.value = null
    }
  } catch (err: any) {
    appStore.error('加载执行记录失败: ' + err.message)
  } finally {
    executionsLoading.value = false
  }
}

async function loadExecutionDetail(id: number, silent = false) {
  if (!silent) detailLoading.value = true
  try {
    const { data } = await executionApi.get(id)
    selectedExecution.value = data
    if (hasAnalysisProgress(data.summary)) {
      activeAnalysisExecution.value = data
      if (data.status === 'running' || data.status === 'paused') {
        startProgressPolling(data.id)
      }
    }
  } catch (err: any) {
    appStore.error('加载执行日志失败: ' + err.message)
  } finally {
    if (!silent) detailLoading.value = false
  }
}

function stopProgressPolling() {
  if (progressTimer) {
    clearInterval(progressTimer)
    progressTimer = null
  }
}

function startProgressPolling(executionId: number) {
  stopProgressPolling()
  progressTimer = setInterval(async () => {
    try {
      const { data } = await executionApi.get(executionId)
      selectedExecution.value = data
      activeAnalysisExecution.value = data
      if (data.status !== 'running' && data.status !== 'paused') {
        stopProgressPolling()
        await loadStats()
        await loadRecentPapers()
        await loadExecutions(false)
        if (data.status === 'failed') {
          appStore.error(data.error_message || '分析失败')
        } else if (data.status === 'cancelled') {
          appStore.warning('文献汇总分析已取消')
        } else {
          appStore.success('文献汇总分析完成')
        }
      }
    } catch (err: any) {
      stopProgressPolling()
      appStore.error('刷新分析进度失败: ' + err.message)
    }
  }, 2000)
}

async function controlAnalysisExecution(action: 'pause' | 'resume' | 'cancel') {
  const id = analysisProgressExecution.value?.id
  if (!id) return
  controlLoading.value = true
  try {
    if (action === 'pause') {
      await executionApi.pause(id)
      appStore.warning('已发送暂停请求，当前论文处理完后暂停')
    } else if (action === 'resume') {
      await executionApi.resume(id)
      appStore.success('文献汇总分析已继续')
      startProgressPolling(id)
    } else {
      await executionApi.cancel(id)
      appStore.warning('已发送取消请求')
    }
    await loadExecutionDetail(id, true)
    await loadExecutions(false)
  } catch (err: any) {
    appStore.error('控制分析任务失败: ' + err.message)
  } finally {
    controlLoading.value = false
  }
}

function pauseAnalysisExecution() {
  controlAnalysisExecution('pause')
}

function resumeAnalysisExecution() {
  controlAnalysisExecution('resume')
}

function cancelAnalysisExecution() {
  controlAnalysisExecution('cancel')
}

async function fetchAll() {
  actionLoading.value = true
  try {
    const { data } = await analysisApi.fetchAndAnalyzeBackground()
    appStore.success('抓取并分析已开始')
    await loadExecutions(true)
    if (data.execution_id) {
      await loadExecutionDetail(data.execution_id)
      startProgressPolling(data.execution_id)
    }
  } catch (err: any) {
    appStore.error('操作失败: ' + err.message)
  } finally {
    actionLoading.value = false
  }
}

async function runAnalysis() {
  actionLoading.value = true
  try {
    const { data } = await analysisApi.runBackground()
    appStore.success('文献汇总分析已开始')
    await loadExecutions(true)
    if (data.execution_id) {
      await loadExecutionDetail(data.execution_id)
      startProgressPolling(data.execution_id)
    }
  } catch (err: any) {
    appStore.error('分析失败: ' + err.message)
  } finally {
    actionLoading.value = false
  }
}

async function sendReport() {
  actionLoading.value = true
  try {
    const { data } = await analysisApi.sendReport()
    if (data.success) {
      appStore.success('报告已发送')
    } else {
      appStore.warning(data.message || '报告未发送：请检查邮件配置或是否有符合条件的论文')
    }
    await loadExecutions(true)
  } catch (err: any) {
    appStore.error('发送报告失败: ' + err.message)
  } finally {
    actionLoading.value = false
  }
}

async function fetchAndAnalyze() {
  actionLoading.value = true
  try {
    const { data } = await analysisApi.fetchAndAnalyzeBackground()
    appStore.success('抓取并分析已开始')
    await loadExecutions(true)
    if (data.execution_id) {
      await loadExecutionDetail(data.execution_id)
      startProgressPolling(data.execution_id)
    }
  } catch (err: any) {
    appStore.error('操作失败: ' + err.message)
  } finally {
    actionLoading.value = false
  }
}

async function runDailyWorkflow() {
  actionLoading.value = true
  try {
    const { data } = await workflowApi.runDaily()
    appStore.success(data.success ? '完整工作流运行完成' : '完整工作流运行失败')
    await loadStats()
    await loadRecentPapers()
    await loadExecutions(true)
    if (data.execution_id) {
      await loadExecutionDetail(data.execution_id)
    }
  } catch (err: any) {
    appStore.error('完整工作流失败: ' + err.message)
  } finally {
    actionLoading.value = false
  }
}

onMounted(() => {
  loadStats()
  loadRecentPapers()
  loadExecutions(true)
})

onUnmounted(() => {
  stopProgressPolling()
})
</script>
