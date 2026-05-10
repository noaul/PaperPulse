<template>
  <div class="space-y-6">
    <!-- Stats Cards -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
      <div
        v-for="stat in statsCards"
        :key="stat.label"
        class="bg-white rounded-xl shadow-sm border border-gray-200 p-5"
      >
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm text-gray-500">{{ stat.label }}</p>
            <p class="text-2xl font-bold mt-1" :class="stat.color">
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
      <h2 class="text-lg font-semibold text-gray-800 mb-4">快速操作</h2>
      <div class="flex flex-wrap gap-3">
        <button
          @click="fetchAll"
          :disabled="actionLoading"
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
          :disabled="actionLoading"
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
          :disabled="actionLoading"
          class="inline-flex items-center px-4 py-2.5 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          <svg class="w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M13 10V3L4 14h7v7l9-11h-7z" />
          </svg>
          一键抓取并分析
        </button>
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
import { ref, computed, onMounted } from 'vue'
import { dashboardApi, analysisApi } from '@/api'
import type { DashboardStats, RecentPaper } from '@/api'
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
const statsLoading = ref(true)
const papersLoading = ref(true)
const actionLoading = ref(false)

const statsCards = computed(() => [
  {
    label: '订阅源总数',
    value: stats.value.total_feeds,
    color: 'text-gray-900',
    bgColor: 'bg-blue-50',
    icon: '<svg fill="none" viewBox="0 0 24 24" stroke="#2563eb"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 5c7.18 0 13 5.82 13 13M6 11a7 7 0 017 7m-6 0a1 1 0 11-2 0 1 1 0 012 0z" /></svg>',
  },
  {
    label: '论文总数',
    value: stats.value.total_papers,
    color: 'text-gray-900',
    bgColor: 'bg-purple-50',
    icon: '<svg fill="none" viewBox="0 0 24 24" stroke="#7c3aed"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>',
  },
  {
    label: '今日新论文',
    value: stats.value.today_papers,
    color: 'text-green-600',
    bgColor: 'bg-green-50',
    icon: '<svg fill="none" viewBox="0 0 24 24" stroke="#16a34a"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6" /></svg>',
  },
  {
    label: '今日分析',
    value: stats.value.today_analyses,
    color: 'text-orange-600',
    bgColor: 'bg-orange-50',
    icon: '<svg fill="none" viewBox="0 0 24 24" stroke="#ea580c"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" /></svg>',
  },
  {
    label: '今日高相关',
    value: stats.value.high_relevance_today,
    color: 'text-red-600',
    bgColor: 'bg-red-50',
    icon: '<svg fill="none" viewBox="0 0 24 24" stroke="#dc2626"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z" /></svg>',
  },
])

function scoreBadgeClass(score: number): string {
  if (score >= 7) return 'bg-green-100 text-green-800'
  if (score >= 5) return 'bg-yellow-100 text-yellow-800'
  return 'bg-red-100 text-red-800'
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

async function fetchAll() {
  actionLoading.value = true
  try {
    await analysisApi.fetchAndAnalyze()
    appStore.success('抓取并分析完成')
    await loadStats()
    await loadRecentPapers()
  } catch (err: any) {
    appStore.error('操作失败: ' + err.message)
  } finally {
    actionLoading.value = false
  }
}

async function runAnalysis() {
  actionLoading.value = true
  try {
    await analysisApi.run()
    appStore.success('分析完成')
    await loadStats()
    await loadRecentPapers()
  } catch (err: any) {
    appStore.error('分析失败: ' + err.message)
  } finally {
    actionLoading.value = false
  }
}

async function sendReport() {
  actionLoading.value = true
  try {
    await analysisApi.sendReport()
    appStore.success('报告已发送')
  } catch (err: any) {
    appStore.error('发送报告失败: ' + err.message)
  } finally {
    actionLoading.value = false
  }
}

async function fetchAndAnalyze() {
  actionLoading.value = true
  try {
    await analysisApi.fetchAndAnalyze()
    appStore.success('抓取并分析完成')
    await loadStats()
    await loadRecentPapers()
  } catch (err: any) {
    appStore.error('操作失败: ' + err.message)
  } finally {
    actionLoading.value = false
  }
}

onMounted(() => {
  loadStats()
  loadRecentPapers()
})
</script>
