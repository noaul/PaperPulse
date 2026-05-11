<template>
  <div class="space-y-6">
    <!-- Search and Filters -->
    <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
      <div class="flex flex-wrap gap-4">
        <!-- Search -->
        <div class="flex-1 min-w-[200px]">
          <div class="relative">
            <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <input
              v-model="filters.search"
              type="text"
              placeholder="搜索论文标题、作者..."
              class="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none text-sm"
              @input="debouncedSearch"
            />
          </div>
        </div>

        <!-- Journal Filter -->
        <select
          v-model="filters.journal"
          @change="loadPapers(1)"
          class="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none text-sm"
        >
          <option value="">全部期刊</option>
          <option v-for="j in journals" :key="j" :value="j">{{ j }}</option>
        </select>

        <!-- Keyword Filter -->
        <input
          v-model="filters.keyword"
          type="text"
          placeholder="关键词筛选..."
          class="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none text-sm w-40"
          @input="debouncedSearch"
        />

        <!-- Min Relevance -->
        <select
          v-model.number="filters.min_relevance"
          @change="loadPapers(1)"
          class="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none text-sm"
        >
          <option :value="0">全部评分</option>
          <option :value="7">≥ 7 高相关</option>
          <option :value="5">≥ 5 中相关</option>
          <option :value="3">≥ 3 低相关</option>
        </select>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="flex justify-center py-12">
      <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
    </div>

    <!-- Paper List -->
    <div v-else-if="papers.length > 0" class="space-y-3">
      <div
        v-for="paper in papers"
        :key="paper.id"
        class="bg-white rounded-xl shadow-sm border border-gray-200 p-5 hover:shadow-md transition-shadow"
      >
        <div class="flex items-start justify-between gap-4">
          <div class="flex-1 min-w-0">
            <h3
              class="text-base font-semibold text-gray-900 cursor-pointer hover:text-blue-600 leading-6"
              @click="toggleExpand(paper)"
            >
              {{ paper.title }}
            </h3>
            <p class="text-sm text-gray-500 mt-1">
              {{ paper.authors }}
            </p>
            <div class="flex items-center gap-3 mt-2 text-xs text-gray-500">
              <span class="inline-flex items-center">
                <svg class="w-3.5 h-3.5 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 13a2 2 0 01-2-2V7m2 13a2 2 0 002-2V9a2 2 0 00-2-2h-2m-4-3H9M7 16h6M7 8h6v4H7V8z" />
                </svg>
                {{ paper.journal_name }}
              </span>
              <span class="inline-flex items-center">
                <svg class="w-3.5 h-3.5 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                </svg>
                {{ paper.published_at }}
              </span>
            </div>
            <p class="text-sm text-gray-600 mt-2 line-clamp-2">
              {{ paper.abstract }}
            </p>

            <!-- Expanded Detail -->
            <div v-if="expandedId === paper.id" class="mt-4 pt-4 border-t border-gray-100 space-y-3">
              <div>
                <h4 class="text-sm font-medium text-gray-700 mb-1">完整摘要</h4>
                <p class="text-sm text-gray-600">{{ paper.abstract }}</p>
              </div>
              <div v-if="paper.analysis_summary">
                <h4 class="text-sm font-medium text-gray-700 mb-1">AI 分析摘要</h4>
                <p class="text-sm text-gray-600">{{ paper.analysis_summary }}</p>
              </div>
              <div class="flex items-center gap-3">
                <a
                  v-if="paper.doi"
                  :href="`https://doi.org/${paper.doi}`"
                  target="_blank"
                  class="inline-flex items-center text-sm text-blue-600 hover:text-blue-800"
                >
                  <svg class="w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                  </svg>
                  DOI: {{ paper.doi }}
                </a>
                <a
                  v-if="paper.url"
                  :href="paper.url"
                  target="_blank"
                  class="inline-flex items-center text-sm text-gray-600 hover:text-gray-800"
                >
                  原文链接 →
                </a>
              </div>
            </div>
          </div>

          <!-- Score Badge -->
          <span
            :class="[
              'inline-flex items-center px-3 py-1 rounded-full text-sm font-medium flex-shrink-0',
              scoreBadgeClass(paper.relevance_score),
            ]"
          >
            {{ formatScore(paper.relevance_score) }}
          </span>
        </div>
      </div>
    </div>

    <!-- Empty State -->
    <div v-else class="bg-white rounded-xl shadow-sm border border-gray-200 p-12 text-center">
      <svg class="w-12 h-12 text-gray-400 mx-auto mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
          d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
      </svg>
      <p class="text-gray-500">暂无论文数据</p>
    </div>

    <!-- Pagination -->
    <div v-if="totalPages > 1" class="flex items-center justify-center space-x-2">
      <button
        @click="loadPapers(currentPage - 1)"
        :disabled="currentPage <= 1"
        class="px-3 py-1.5 text-sm rounded-lg border border-gray-300 text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        上一页
      </button>
      <template v-for="page in paginationRange" :key="page">
        <button
          v-if="page !== '...'"
          @click="loadPapers(page as number)"
          :class="[
            'px-3 py-1.5 text-sm rounded-lg border',
            page === currentPage
              ? 'bg-blue-600 text-white border-blue-600'
              : 'border-gray-300 text-gray-700 hover:bg-gray-50',
          ]"
        >
          {{ page }}
        </button>
        <span v-else class="px-2 text-gray-400">...</span>
      </template>
      <button
        @click="loadPapers(currentPage + 1)"
        :disabled="currentPage >= totalPages"
        class="px-3 py-1.5 text-sm rounded-lg border border-gray-300 text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        下一页
      </button>
      <span class="text-sm text-gray-500 ml-4">
        共 {{ totalPapers }} 篇
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { paperApi, feedApi } from '@/api'
import type { Paper } from '@/api'
import { useAppStore } from '@/stores/app'

const appStore = useAppStore()

const papers = ref<Paper[]>([])
const loading = ref(true)
const currentPage = ref(1)
const totalPages = ref(1)
const totalPapers = ref(0)
const expandedId = ref<number | null>(null)
const pageSize = 15

const filters = reactive({
  search: '',
  journal: '',
  keyword: '',
  min_relevance: 0,
})

const journals = ref<string[]>([])

let searchTimeout: ReturnType<typeof setTimeout> | null = null

function debouncedSearch() {
  if (searchTimeout) clearTimeout(searchTimeout)
  searchTimeout = setTimeout(() => {
    loadPapers(1)
  }, 400)
}

function scoreBadgeClass(score: number | null): string {
  if (typeof score !== 'number') return 'bg-gray-100 text-gray-600'
  if (score >= 7) return 'bg-green-100 text-green-800'
  if (score >= 5) return 'bg-yellow-100 text-yellow-800'
  return 'bg-red-100 text-red-800'
}

function formatScore(score: number | null): string {
  return typeof score === 'number' ? score.toFixed(1) : '未分析'
}

const paginationRange = computed(() => {
  const range: (number | string)[] = []
  const total = totalPages.value
  const current = currentPage.value

  if (total <= 7) {
    for (let i = 1; i <= total; i++) range.push(i)
  } else {
    range.push(1)
    if (current > 3) range.push('...')
    for (let i = Math.max(2, current - 1); i <= Math.min(total - 1, current + 1); i++) {
      range.push(i)
    }
    if (current < total - 2) range.push('...')
    range.push(total)
  }
  return range
})

function toggleExpand(paper: Paper) {
  expandedId.value = expandedId.value === paper.id ? null : paper.id
}

async function loadPapers(page: number) {
  if (page < 1) return
  loading.value = true
  try {
    const params: any = {
      page,
      page_size: pageSize,
    }
    if (filters.search) params.search = filters.search
    if (filters.journal) params.journal = filters.journal
    if (filters.keyword) params.keyword = filters.keyword
    if (filters.min_relevance) params.min_score = filters.min_relevance

    const { data } = await paperApi.list(params)
    papers.value = data.items
    currentPage.value = data.page
    totalPages.value = data.pages
    totalPapers.value = data.total
  } catch (err: any) {
    appStore.error('加载论文失败: ' + err.message)
  } finally {
    loading.value = false
  }
}

async function loadJournals() {
  try {
    const { data } = await feedApi.list()
    journals.value = [...new Set(data.map((f) => f.journal_name).filter(Boolean))]
  } catch {
    // silently ignore
  }
}

onMounted(() => {
  loadPapers(1)
  loadJournals()
})
</script>
