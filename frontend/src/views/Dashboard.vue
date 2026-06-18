<template>
  <div class="space-y-6">
    <!-- Stats Cards -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
      <div v-for="stat in statsCards" :key="stat.label" class="xai-card">
        <p class="xai-eyebrow mb-3">{{ stat.label }}</p>
        <p class="xai-stat-value">{{ statsLoading ? '-' : stat.value }}</p>
      </div>
    </div>

    <!-- Quick Actions -->
    <div class="xai-card">
      <p class="xai-eyebrow mb-4">快捷操作</p>
      <div class="flex flex-wrap gap-3">
        <button @click="fetchAll" :disabled="actionLoading || analysisRunning" class="xai-btn">
          抓取全部订阅
        </button>
        <button @click="runAnalysis" :disabled="actionLoading || analysisRunning" class="xai-btn">
          运行分析
        </button>
        <button @click="sendReport" :disabled="actionLoading" class="xai-btn">
          发送报告
        </button>
        <button @click="fetchAndAnalyze" :disabled="actionLoading || analysisRunning" class="xai-btn-primary xai-btn">
          一键抓取并分析
        </button>
        <button @click="runDailyWorkflow" :disabled="actionLoading || analysisRunning" class="xai-btn">
          运行完整工作流
        </button>
      </div>
    </div>

    <!-- Analysis Progress -->
    <div v-if="analysisProgressExecution" class="xai-card">
      <div class="flex items-center justify-between gap-4 mb-4">
        <div>
          <p class="xai-eyebrow mb-1">分析进度</p>
          <p class="text-sm text-[var(--xai-mute)]">
            {{ workflowLabel(analysisProgressExecution.workflow_name) }} · {{ statusText(analysisProgressExecution.status) }}
          </p>
        </div>
        <div class="flex items-center gap-2">
          <span class="xai-badge">{{ analysisProgressPercent }}%</span>
          <button
            v-if="analysisProgressExecution.status === 'running'"
            @click="pauseAnalysisExecution"
            :disabled="controlLoading"
            class="xai-btn xai-badge-warning"
          >暂停</button>
          <button
            v-if="analysisProgressExecution.status === 'paused'"
            @click="resumeAnalysisExecution"
            :disabled="controlLoading"
            class="xai-btn xai-badge-info"
          >继续</button>
          <button
            v-if="['running', 'paused'].includes(analysisProgressExecution.status)"
            @click="cancelAnalysisExecution"
            :disabled="controlLoading"
            class="xai-btn xai-badge-danger"
          >取消</button>
        </div>
      </div>

      <div class="xai-progress-track">
        <div class="xai-progress-bar" :style="{ width: `${analysisProgressPercent}%` }"></div>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mt-4">
        <div class="rounded-lg border border-[var(--xai-hairline)] p-4">
          <p class="xai-eyebrow">已分析</p>
          <p class="text-2xl mt-1 tracking-tight">{{ analysisProgress.analyzed }} / {{ analysisProgress.total }}</p>
        </div>
        <div class="rounded-lg border border-[var(--xai-hairline)] p-4">
          <p class="xai-eyebrow">相关论文</p>
          <p class="text-2xl mt-1 tracking-tight">{{ analysisProgress.related }}</p>
        </div>
        <div class="rounded-lg border border-[var(--xai-hairline)] p-4">
          <p class="xai-eyebrow">分析结果</p>
          <p class="text-2xl mt-1 tracking-tight">{{ analysisProgress.results }}</p>
        </div>
      </div>

      <p v-if="analysisProgress.currentTitle && analysisProgressExecution.status === 'running'" class="text-sm text-[var(--xai-mute)] mt-4 truncate">
        正在分析：{{ analysisProgress.currentTitle }}
      </p>
      <p v-if="analysisProgress.summary" class="text-sm text-[var(--xai-body)] mt-4 rounded-lg border border-[var(--xai-hairline)] p-3">
        {{ analysisProgress.summary }}
      </p>
      <p v-if="analysisProgressExecution.error_message" class="text-sm text-[#fca5a5] mt-4 rounded-lg border border-[rgba(239,68,68,0.4)] p-3">
        {{ analysisProgressExecution.error_message }}
      </p>
    </div>

    <!-- Chart: Daily Stats -->
    <div class="xai-card">
      <div class="flex items-center justify-between mb-4">
        <p class="xai-eyebrow">趋势</p>
        <div class="flex items-center gap-2">
          <select v-model.number="reanalyzeDays" class="text-sm bg-[var(--xai-canvas-soft)] border-[var(--xai-hairline)] rounded-lg px-2 py-1">
            <option :value="1">1天</option>
            <option :value="3">3天</option>
            <option :value="7">7天</option>
            <option :value="14">14天</option>
          </select>
          <button @click="reanalyze" :disabled="actionLoading" class="xai-btn text-xs">重新分析</button>
        </div>
      </div>
      <div v-if="chartData" class="space-y-4">
        <div class="grid grid-cols-4 gap-3 text-center text-xs text-[var(--xai-mute)] mb-2">
          <span class="flex items-center gap-1"><span class="w-3 h-1 rounded bg-[var(--xai-primary)]"></span>每日新增</span>
          <span class="flex items-center gap-1"><span class="w-3 h-1 rounded bg-[#515bd8]"></span>每日分析</span>
          <span class="flex items-center gap-1"><span class="w-3 h-1 rounded bg-[#16805f]"></span>相关论文</span>
          <span class="flex items-center gap-1"><span class="w-3 h-1 rounded bg-[var(--xai-canvas-mid)]"></span>累计总量</span>
        </div>
        <div class="h-40 flex items-end gap-px">
          <div v-for="(d, i) in chartData.dates" :key="d" class="flex-1 flex flex-col items-center gap-0.5 group relative">
            <div class="w-full flex flex-col justify-end h-32 gap-px">
              <div class="bg-[var(--xai-primary)] rounded-t-sm" :style="{ height: barH(chartData.daily_new_papers[i], chartMax) }"></div>
              <div class="bg-[#515bd8]" :style="{ height: barH(chartData.daily_analyses[i], chartMax) }"></div>
              <div class="bg-[#16805f] rounded-b-sm" :style="{ height: barH(chartData.daily_related_papers[i], chartMax) }"></div>
            </div>
            <span class="text-[9px] text-[var(--xai-mute)] rotate-[-45deg] origin-top-left mt-1 hidden lg:block">{{ d.slice(5) }}</span>
            <div class="absolute bottom-full mb-1 hidden group-hover:block bg-[var(--xai-canvas-soft)] border border-[var(--xai-hairline)] text-[var(--xai-ink)] text-[10px] px-2 py-1 rounded whitespace-nowrap z-10">
              {{ d }}<br/>新增:{{ chartData.daily_new_papers[i] }} 分析:{{ chartData.daily_analyses[i] }} 相关:{{ chartData.daily_related_papers[i] }} 累计:{{ chartData.cumulative_papers[i] }}
            </div>
          </div>
        </div>
      </div>
      <div v-else class="text-center text-sm text-[var(--xai-mute)] py-8">加载中...</div>
    </div>

    <!-- Workflow Executions -->
    <div class="grid grid-cols-1 xl:grid-cols-3 gap-6">
      <div class="xl:col-span-2 xai-card">
        <div class="flex items-center justify-between gap-3 mb-4">
          <button
            type="button"
            @click="workflowLogExpanded = !workflowLogExpanded"
            class="min-w-0 flex items-center gap-3 text-left"
            :aria-expanded="workflowLogExpanded"
          >
            <span class="xai-eyebrow">工作流记录</span>
            <span class="text-xs text-[var(--xai-mute)]">
              {{ workflowLogExpanded ? '全部记录' : `最近 ${visibleExecutions.length} / ${executions.length}` }}
            </span>
            <span class="text-sm text-[var(--xai-mute)]" aria-hidden="true">{{ workflowLogExpanded ? '⌃' : '⌄' }}</span>
          </button>
          <button @click="loadExecutions(true)" :disabled="executionsLoading" class="xai-btn text-xs">刷新</button>
        </div>

        <div v-if="executionsLoading" class="flex justify-center py-8">
          <div class="animate-spin rounded-full h-6 w-6 border-b border-[var(--xai-primary)]"></div>
        </div>

        <div v-else-if="executions.length === 0" class="text-center py-8 text-[var(--xai-mute)]">
          暂无执行记录
        </div>

        <div v-else class="space-y-2 overflow-y-auto pr-1" :class="workflowLogExpanded ? 'max-h-[30rem]' : 'max-h-[16rem]'">
          <button
            v-for="execution in visibleExecutions"
            :key="execution.id"
            @click="selectExecution(execution.id)"
            class="w-full text-left p-3 rounded-lg border transition-colors"
            :class="selectedExecution?.id === execution.id ? 'border-[rgba(36,84,230,0.32)] bg-[var(--xai-primary-soft)]' : 'border-[var(--xai-hairline)] hover:border-[rgba(36,84,230,0.24)]'"
          >
            <div class="flex items-start justify-between gap-4">
              <div class="min-w-0">
                <div class="flex flex-wrap items-center gap-2">
                  <span class="text-sm text-[var(--xai-ink)] truncate">{{ workflowLabel(execution.workflow_name) }}</span>
                  <span :class="['xai-badge text-[11px]', statusBadgeClass(execution.status)]">
                    {{ statusText(execution.status) }}
                  </span>
                </div>
                <p class="text-xs text-[var(--xai-mute)] mt-1">
                  #{{ execution.id }} · {{ formatDateTime(execution.started_at) }} · {{ formatDuration(execution.duration_ms) }}
                </p>
                <p class="text-xs text-[var(--xai-body)] mt-2 truncate">
                  {{ summaryText(execution.summary) }}
                </p>
              </div>
            </div>
          </button>
          <button
            v-if="executions.length > visibleExecutions.length"
            type="button"
            @click="workflowLogExpanded = true"
            class="w-full text-center text-xs text-[var(--xai-mute)] hover:text-[var(--xai-ink)] py-2"
          >
            展开全部 {{ executions.length }} 条
          </button>
        </div>
      </div>

      <div class="xai-card">
        <button
          type="button"
          @click="workflowDetailExpanded = !workflowDetailExpanded"
          :disabled="!selectedExecution && !detailLoading"
          class="w-full flex items-center justify-between gap-3 text-left mb-4 disabled:cursor-default"
          :aria-expanded="workflowDetailExpanded"
        >
          <span class="xai-eyebrow">执行详情</span>
          <span class="flex items-center gap-2 text-xs text-[var(--xai-mute)]">
            <span v-if="selectedExecution">{{ workflowDetailExpanded ? '收起' : '展开' }}</span>
            <span aria-hidden="true">{{ workflowDetailExpanded ? '⌃' : '⌄' }}</span>
          </span>
        </button>

        <div v-if="detailLoading" class="flex justify-center py-8">
          <div class="animate-spin rounded-full h-6 w-6 border-b border-[var(--xai-primary)]"></div>
        </div>

        <div v-else-if="!selectedExecution" class="text-sm text-[var(--xai-mute)] py-8 text-center">
          选择一条执行记录查看节点日志
        </div>

        <div v-else class="space-y-4">
          <div class="rounded-lg border border-[var(--xai-hairline)] p-3">
            <div class="flex items-center justify-between gap-3">
              <span class="min-w-0 text-sm text-[var(--xai-ink)] truncate">{{ workflowLabel(selectedExecution.workflow_name) }}</span>
              <span :class="['xai-badge text-[11px]', statusBadgeClass(selectedExecution.status)]">
                {{ statusText(selectedExecution.status) }}
              </span>
            </div>
            <p class="text-xs text-[var(--xai-mute)] mt-2">{{ formatDateTime(selectedExecution.started_at) }}</p>
            <p class="text-xs text-[var(--xai-mute)] mt-1">
              {{ selectedExecutionLogCount }} 条节点日志 · {{ formatDuration(selectedExecution.duration_ms) }}
            </p>
            <p v-if="selectedExecution.error_message" class="text-xs text-[#fca5a5] mt-2 break-words">
              {{ selectedExecution.error_message }}
            </p>
          </div>

          <div v-if="workflowDetailExpanded">
            <div class="flex items-center justify-between gap-3 mb-2">
              <p class="xai-eyebrow">节点日志</p>
              <button
                v-if="selectedExecutionLogCount > collapsedNodeLogLimit"
                type="button"
                @click="nodeLogExpanded = !nodeLogExpanded"
                class="text-xs text-[var(--xai-mute)] hover:text-[var(--xai-ink)]"
              >
                {{ nodeLogExpanded ? '收起' : `最近 ${visibleNodeLogs.length} 条` }}
              </button>
            </div>
            <div v-if="selectedExecutionLogCount === 0" class="text-sm text-[var(--xai-mute)] py-4 text-center border border-[var(--xai-hairline)] rounded-lg">
              暂无节点日志
            </div>
            <div v-else class="space-y-2 overflow-y-auto pr-1" :class="nodeLogExpanded ? 'max-h-96' : 'max-h-64'">
              <div
                v-for="log in visibleNodeLogs"
                :key="log.id"
                class="rounded-lg border border-[var(--xai-hairline)] p-3"
              >
                <div class="flex items-center justify-between gap-2">
                  <span class="min-w-0 text-xs text-[var(--xai-ink)] truncate">{{ log.node_name }}</span>
                  <span :class="['xai-badge text-[11px]', logLevelClass(log.level)]">
                    {{ log.level }}
                  </span>
                </div>
                <p class="text-sm text-[var(--xai-body)] mt-1 break-words">{{ log.message }}</p>
                <p class="text-[11px] text-[var(--xai-mute)] mt-1">{{ formatDateTime(log.created_at) }}</p>
              </div>
            </div>
          </div>
          <button
            v-else
            type="button"
            @click="workflowDetailExpanded = true"
            class="w-full text-center text-xs text-[var(--xai-mute)] hover:text-[var(--xai-ink)] py-2"
          >
            展开查看节点日志
          </button>
        </div>
      </div>
    </div>

    <!-- Recent High-Relevance Papers -->
    <div class="xai-card">
      <div class="flex items-center justify-between mb-4">
        <p class="xai-eyebrow">高相关论文</p>
        <router-link to="/papers" class="xai-btn text-xs">查看全部 →</router-link>
      </div>

      <div v-if="papersLoading" class="flex justify-center py-8">
        <div class="animate-spin rounded-full h-6 w-6 border-b border-[var(--xai-primary)]"></div>
      </div>

      <div v-else-if="recentPapers.length === 0" class="text-center py-8 text-[var(--xai-mute)]">
        暂无高相关性论文
      </div>

      <div v-else class="space-y-2">
        <div
          v-for="paper in recentPapers"
          :key="paper.id"
          class="flex items-center justify-between p-4 rounded-lg border border-[var(--xai-hairline)] hover:border-[rgba(36,84,230,0.24)] transition-colors"
        >
          <div class="flex-1 min-w-0 mr-4">
            <h3 class="text-sm text-[var(--xai-ink)] truncate">{{ paper.title }}</h3>
            <p class="text-xs text-[var(--xai-mute)] mt-1">
              {{ paper.journal }} · {{ paper.published_date }}
            </p>
          </div>
          <span :class="['xai-badge', scoreBadgeClass(paper.relevance_score)]">
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
const chartData = ref<any>(null)
const reanalyzeDays = ref(1)
const workflowLogExpanded = ref(false)
const workflowDetailExpanded = ref(false)
const nodeLogExpanded = ref(false)
const collapsedExecutionLimit = 3
const collapsedNodeLogLimit = 4
let progressTimer: ReturnType<typeof setInterval> | null = null

const chartMax = computed(() => {
  if (!chartData.value) return 1
  const all = [
    ...chartData.value.daily_new_papers,
    ...chartData.value.daily_analyses,
    ...chartData.value.daily_related_papers,
  ]
  return Math.max(1, ...all)
})

function barH(val: number, max: number) {
  if (!val || !max) return '0px'
  return Math.max(2, (val / max) * 100) + '%'
}

const statsCards = computed(() => [
  { label: '订阅源', value: stats.value.total_feeds },
  { label: '论文总数', value: stats.value.total_papers },
  { label: '今日新增', value: stats.value.today_papers },
  { label: '今日分析', value: stats.value.today_analyses },
  { label: '高相关', value: stats.value.high_relevance_today },
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

const visibleExecutions = computed(() => {
  if (workflowLogExpanded.value) return executions.value
  return executions.value.slice(0, collapsedExecutionLimit)
})

const selectedExecutionLogCount = computed(() => selectedExecution.value?.logs.length || 0)

const visibleNodeLogs = computed(() => {
  const logs = selectedExecution.value?.logs || []
  if (nodeLogExpanded.value) return logs
  return logs.slice(-collapsedNodeLogLimit)
})

const analysisRunning = computed(() => {
  const status = analysisProgressExecution.value?.status
  return status === 'running' || status === 'paused'
})

function hasAnalysisProgress(summary: Record<string, unknown>): boolean {
  return Object.prototype.hasOwnProperty.call(summary, 'analysis_total')
}

function scoreBadgeClass(score: number): string {
  if (score >= 7) return 'xai-badge-success'
  if (score >= 5) return 'xai-badge-warning'
  return 'xai-badge-danger'
}

function statusBadgeClass(status: string): string {
  if (status === 'success') return 'xai-badge-success'
  if (status === 'failed') return 'xai-badge-danger'
  if (status === 'cancelled') return ''
  if (status === 'paused') return 'xai-badge-warning'
  if (status === 'running') return 'xai-badge-info'
  return ''
}

function logLevelClass(level: string): string {
  if (level === 'error') return 'xai-badge-danger'
  if (level === 'warning') return 'xai-badge-warning'
  return ''
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
      await loadExecutionDetail(data[0].id, true, false)
    } else if (selectedExecution.value && !data.some((item) => item.id === selectedExecution.value?.id)) {
      selectedExecution.value = null
      workflowDetailExpanded.value = false
      nodeLogExpanded.value = false
    }
  } catch (err: any) {
    appStore.error('加载执行记录失败: ' + err.message)
  } finally {
    executionsLoading.value = false
  }
}

async function loadExecutionDetail(id: number, silent = false, openDetail = true) {
  if (!silent) detailLoading.value = true
  try {
    const { data } = await executionApi.get(id)
    const previousId = selectedExecution.value?.id
    selectedExecution.value = data
    if (previousId !== data.id) {
      nodeLogExpanded.value = false
    }
    if (openDetail) {
      workflowDetailExpanded.value = true
    }
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

async function selectExecution(id: number) {
  await loadExecutionDetail(id, false, true)
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

function pauseAnalysisExecution() { controlAnalysisExecution('pause') }
function resumeAnalysisExecution() { controlAnalysisExecution('resume') }
function cancelAnalysisExecution() { controlAnalysisExecution('cancel') }

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

async function loadChartData() {
  try {
    const { data } = await dashboardApi.getChartData(14)
    chartData.value = data
  } catch {}
}

async function reanalyze() {
  actionLoading.value = true
  try {
    const { data } = await analysisApi.reanalyze(reanalyzeDays.value)
    appStore.success(data.message || `正在重新分析过去${reanalyzeDays.value}天的论文`)
    if (data.execution_id) {
      startProgressPolling(data.execution_id)
    }
  } catch (err: any) {
    appStore.error('重新分析失败: ' + (err.response?.data?.detail || err.message))
  } finally {
    actionLoading.value = false
  }
}

onMounted(() => {
  loadStats()
  loadRecentPapers()
  loadExecutions(true)
  loadChartData()
})

onUnmounted(() => {
  stopProgressPolling()
})
</script>
