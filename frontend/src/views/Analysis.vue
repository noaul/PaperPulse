<template>
  <div class="space-y-6">
    <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
      <div class="flex flex-wrap items-center gap-4">
        <div>
          <label class="block text-xs text-gray-500 mb-1">研究质量评分</label>
          <select
            v-model.number="filters.min_score"
            @change="loadAnalyses(1)"
            class="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none text-sm"
          >
            <option :value="0">全部评分</option>
            <option :value="3">≥ 3 一般</option>
            <option :value="5">≥ 5 良好</option>
            <option :value="7">≥ 7 优秀</option>
            <option :value="9">≥ 9 顶尖</option>
          </select>
        </div>
        <div>
          <label class="block text-xs text-gray-500 mb-1">按主题词/关键词筛选</label>
          <input
            v-model.trim="filters.keyword"
            @keyup.enter="loadAnalyses(1)"
            placeholder="输入关键词..."
            class="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none text-sm w-48"
          />
        </div>
        <button
          @click="loadAnalyses(1)"
          :disabled="loading"
          class="mt-5 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50"
        >
          筛选
        </button>
        <button
          @click="clearFilters"
          class="mt-5 px-4 py-2 text-gray-600 text-sm font-medium rounded-lg border border-gray-300 hover:bg-gray-50"
        >
          重置
        </button>
        <div class="mt-5 text-sm text-gray-500">
          共 {{ totalAnalyses }} 条分析结果
        </div>
      </div>
    </div>

    <div v-if="loading" class="flex justify-center py-12">
      <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
    </div>

    <div v-else-if="analyses.length === 0" class="bg-white rounded-xl shadow-sm border border-gray-200 p-12 text-center">
      <svg class="w-12 h-12 text-gray-400 mx-auto mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
          d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
      </svg>
      <p class="text-gray-500">暂无分析结果。请先在仪表盘运行文献分析。</p>
    </div>

    <div v-else class="space-y-4">
      <div
        v-for="item in analyses"
        :key="item.id"
        class="bg-white rounded-xl shadow-sm border border-gray-200 p-5"
      >
        <div class="flex items-start justify-between gap-4">
          <div class="min-w-0 flex-1">
            <div class="flex flex-wrap items-center gap-2 mb-2">
              <span :class="['px-2.5 py-0.5 rounded-full text-xs font-medium', scoreBadgeClass(item.relevance_score)]">
                {{ item.relevance_score.toFixed(1) }}
              </span>
              <span class="px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                {{ item.keyword_word }}
              </span>
              <span v-if="item.journal_name" class="text-xs text-gray-500">
                {{ item.journal_name }}
              </span>
              <span class="text-xs text-gray-400">
                {{ formatDateTime(item.analyzed_at) }}
              </span>
            </div>
            <h2 class="text-base font-semibold text-gray-900">
              {{ item.paper_title }}
            </h2>
            <p v-if="item.paper_authors" class="text-sm text-gray-500 mt-1">
              {{ item.paper_authors }}
            </p>
            <div class="mt-3 rounded-lg bg-purple-50 p-3">
              <h3 class="text-sm font-medium text-purple-900 mb-1">AI 分析摘要</h3>
              <p class="text-sm text-purple-900/80">{{ item.summary || '无摘要' }}</p>
            </div>
            <div class="mt-3 rounded-lg bg-gray-50 p-3">
              <h3 class="text-sm font-medium text-gray-700 mb-1">论文摘要</h3>
              <p class="text-sm text-gray-600 leading-6">
                {{ item.paper_abstract || '该订阅源未提供摘要' }}
              </p>
            </div>
          </div>
          <div class="flex flex-shrink-0 flex-col items-end gap-2">
            <button
              @click="addToReadingQueue(item)"
              :disabled="queueAddingIds.has(item.id)"
              class="px-3 py-1.5 rounded-lg text-sm font-medium bg-indigo-100 text-indigo-800 hover:bg-indigo-200 disabled:opacity-50"
            >
              {{ queueAddingIds.has(item.id) ? '添加中...' : '加入阅读队列' }}
            </button>
            <a
              v-if="item.paper_url"
              :href="item.paper_url"
              target="_blank"
              class="text-sm text-blue-600 hover:text-blue-800"
            >
              原文 →
            </a>
          </div>
        </div>
      </div>
    </div>

    <div v-if="totalPages > 1" class="flex items-center justify-center space-x-2">
      <button
        @click="loadAnalyses(currentPage - 1)"
        :disabled="currentPage <= 1"
        class="px-3 py-1.5 text-sm rounded-lg border border-gray-300 text-gray-700 hover:bg-gray-50 disabled:opacity-50"
      >
        上一页
      </button>
      <span class="text-sm text-gray-500">第 {{ currentPage }} / {{ totalPages }} 页</span>
      <button
        @click="loadAnalyses(currentPage + 1)"
        :disabled="currentPage >= totalPages"
        class="px-3 py-1.5 text-sm rounded-lg border border-gray-300 text-gray-700 hover:bg-gray-50 disabled:opacity-50"
      >
        下一页
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref, onMounted } from 'vue'
import { analysisApi } from '@/api'
import type { Analysis } from '@/api'
import { useAppStore } from '@/stores/app'

const appStore = useAppStore()
const analyses = ref<Analysis[]>([])
const loading = ref(true)
const currentPage = ref(1)
const totalPages = ref(1)
const totalAnalyses = ref(0)
const queueAddingIds = ref(new Set<number>())
const pageSize = 20

const filters = reactive({
  min_score: 0,
  keyword: '',
})

function scoreBadgeClass(score: number): string {
  if (score >= 7) return 'bg-green-100 text-green-800'
  if (score >= 5) return 'bg-yellow-100 text-yellow-800'
  return 'bg-red-100 text-red-800'
}

function formatDateTime(value: string): string {
  return value ? new Date(value).toLocaleString('zh-CN', { hour12: false }) : '-'
}

function clearFilters() {
  filters.min_score = 0
  filters.keyword = ''
  loadAnalyses(1)
}

async function loadAnalyses(page: number) {
  if (page < 1) return
  loading.value = true
  try {
    const params: { page: number; page_size: number; min_score?: number; keyword?: string } = {
      page,
      page_size: pageSize,
    }
    if (filters.min_score) params.min_score = filters.min_score
    if (filters.keyword) params.keyword = filters.keyword
    const { data } = await analysisApi.list(params)
    analyses.value = data.items
    currentPage.value = data.page
    totalPages.value = data.pages
    totalAnalyses.value = data.total
  } catch (err: any) {
    appStore.error('加载分析结果失败: ' + err.message)
  } finally {
    loading.value = false
  }
}

async function addToReadingQueue(item: Analysis) {
  const next = new Set(queueAddingIds.value)
  next.add(item.id)
  queueAddingIds.value = next
  try {
    await analysisApi.addToReadingQueue(item.id)
    appStore.success('已加入阅读队列')
  } catch (err: any) {
    appStore.error('加入阅读队列失败: ' + err.message)
  } finally {
    const done = new Set(queueAddingIds.value)
    done.delete(item.id)
    queueAddingIds.value = done
  }
}

onMounted(() => {
  loadAnalyses(1)
})
</script>
