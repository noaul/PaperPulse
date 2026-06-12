<template>
  <div class="space-y-6">
    <div class="paper-filter-panel">
      <div class="grid gap-3 lg:grid-cols-[minmax(220px,1fr)_11rem_10rem_10rem]">
        <label class="paper-field">
          <span class="paper-field-label">搜索</span>
          <div class="relative">
            <svg class="paper-input-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <input
              v-model="filters.search"
              type="text"
              placeholder="搜索论文标题、作者..."
              class="w-full pl-10 pr-4 py-2.5 text-sm"
              @input="debouncedSearch"
            />
          </div>
        </label>

        <label class="paper-field">
          <span class="paper-field-label">期刊</span>
          <select
            v-model="filters.journal"
            class="w-full px-3 py-2.5 text-sm"
            @change="loadPapers(1)"
          >
            <option value="">全部期刊</option>
            <option v-for="j in journals" :key="j" :value="j">{{ j }}</option>
          </select>
        </label>

        <label class="paper-field">
          <span class="paper-field-label">关键词</span>
          <input
            v-model="filters.keyword"
            type="text"
            placeholder="关键词筛选..."
            class="w-full px-3 py-2.5 text-sm"
            @input="debouncedSearch"
          />
        </label>

        <label class="paper-field">
          <span class="paper-field-label">评分</span>
          <select
            v-model.number="filters.min_relevance"
            class="w-full px-3 py-2.5 text-sm"
            @change="loadPapers(1)"
          >
            <option :value="0">全部评分</option>
            <option :value="7">≥ 7 高相关</option>
            <option :value="5">≥ 5 中相关</option>
            <option :value="3">≥ 3 低相关</option>
          </select>
        </label>
      </div>
    </div>

    <div v-if="loading" class="flex justify-center py-12">
      <div class="h-8 w-8 animate-spin rounded-full border-b-2 border-[var(--xai-accent-breeze)]"></div>
    </div>

    <div v-else-if="papers.length > 0" class="space-y-3">
      <article
        v-for="paper in papers"
        :key="paper.id"
        class="paper-list-card"
      >
        <div class="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div class="min-w-0 flex-1">
            <h3 class="paper-list-title cursor-pointer" @click="toggleExpand(paper)">
              {{ paper.title }}
            </h3>
            <p class="mt-1 text-sm text-[var(--xai-mute)]">
              {{ paper.authors }}
            </p>
            <div class="paper-meta-row mt-3">
              <span class="paper-meta-item">
                <svg class="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 13a2 2 0 01-2-2V7m2 13a2 2 0 002-2V9a2 2 0 00-2-2h-2m-4-3H9M7 16h6M7 8h6v4H7V8z" />
                </svg>
                {{ paper.journal_name }}
              </span>
              <span class="paper-meta-item">
                <svg class="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                </svg>
                {{ paper.published_at }}
              </span>
            </div>
            <p class="mt-3 line-clamp-2 text-sm leading-6 text-[var(--xai-body)]">
              {{ paper.abstract }}
            </p>

            <div v-if="expandedId === paper.id" class="paper-detail-panel space-y-3">
              <div>
                <h4 class="mb-1 text-sm font-medium text-[var(--xai-ink)]">完整摘要</h4>
                <p class="text-sm leading-6 text-[var(--xai-body)]">{{ paper.abstract }}</p>
              </div>
              <div v-if="paper.analysis_summary" class="paper-note-block">
                <h4 class="mb-1 text-sm font-medium text-[var(--xai-accent-breeze)]">AI 分析摘要</h4>
                <p class="text-sm leading-6 text-[var(--xai-body)]">{{ paper.analysis_summary }}</p>
              </div>
              <div class="flex flex-wrap items-center gap-3">
                <a
                  v-if="paper.doi"
                  :href="`https://doi.org/${paper.doi}`"
                  target="_blank"
                  class="inline-flex items-center text-sm text-[var(--xai-accent-breeze)] hover:text-[var(--xai-ink)]"
                >
                  <svg class="mr-1 h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                  </svg>
                  DOI: {{ paper.doi }}
                </a>
                <a
                  v-if="paper.url"
                  :href="paper.url"
                  target="_blank"
                  class="inline-flex items-center text-sm text-[var(--xai-body)] hover:text-[var(--xai-ink)]"
                >
                  原文链接 →
                </a>
              </div>
            </div>
          </div>

          <span
            :class="[
              'xai-badge flex-shrink-0 justify-center text-sm sm:min-w-[4.5rem]',
              scoreBadgeClass(paper.relevance_score),
            ]"
          >
            {{ formatScore(paper.relevance_score) }}
          </span>
        </div>
      </article>
    </div>

    <div v-else class="paper-empty-state">
      <svg class="mx-auto mb-4 h-12 w-12 text-[var(--xai-mute)]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
          d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
      </svg>
      <p class="text-sm text-[var(--xai-mute)]">暂无论文数据</p>
    </div>

    <div v-if="totalPages > 1" class="paper-pagination">
      <button
        class="paper-page-button disabled:cursor-not-allowed disabled:opacity-50"
        :disabled="currentPage <= 1"
        @click="loadPapers(currentPage - 1)"
      >
        上一页
      </button>
      <template v-for="page in paginationRange" :key="page">
        <button
          v-if="page !== '...'"
          :class="['paper-page-button', page === currentPage ? 'paper-page-button-active' : '']"
          @click="loadPapers(page as number)"
        >
          {{ page }}
        </button>
        <span v-else class="px-2 text-[var(--xai-mute)]">...</span>
      </template>
      <button
        class="paper-page-button disabled:cursor-not-allowed disabled:opacity-50"
        :disabled="currentPage >= totalPages"
        @click="loadPapers(currentPage + 1)"
      >
        下一页
      </button>
      <span class="ml-2 text-sm text-[var(--xai-mute)]">
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
