<template>
  <div class="space-y-5">
    <section class="bg-white rounded-xl shadow-sm border border-gray-200 p-5 overflow-hidden relative">
      <div class="absolute inset-x-0 top-0 h-1 bg-gradient-to-r from-blue-500 via-green-500 to-amber-500"></div>
      <div class="flex flex-col lg:flex-row lg:items-end lg:justify-between gap-4">
        <div>
          <h2 class="text-lg font-semibold text-gray-800">生成报告</h2>
          <p class="text-sm text-gray-500 mt-1">保存今日正分分析结果，可预览、下载 Markdown 或重新发送邮件。</p>
        </div>
        <div class="flex flex-wrap items-end gap-3">
          <button
            @click="createReport"
            :disabled="actionLoading"
            class="inline-flex items-center px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            <svg class="w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
            </svg>
            生成报告
          </button>
        </div>
      </div>
    </section>

    <section class="bg-white rounded-xl shadow-sm border border-gray-200 p-5">
      <div class="flex items-center justify-between gap-3 mb-4">
        <div>
          <h2 class="text-lg font-semibold text-gray-800">历史报告</h2>
          <p class="text-sm text-gray-500">{{ reports.length }} 份报告，选择一份查看下方详情。</p>
        </div>
        <button
          @click="loadReports"
          :disabled="reportsLoading"
          class="px-4 py-2 border border-gray-300 text-gray-700 text-sm font-medium rounded-lg hover:bg-gray-50 disabled:opacity-50"
        >
          刷新
        </button>
      </div>

      <div v-if="reportsLoading" class="flex justify-center py-8">
        <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>

      <div v-else-if="reports.length === 0" class="text-sm text-gray-500 text-center py-8">
        暂无报告，先生成一份今日报告。
      </div>

      <div v-else class="grid gap-3 md:grid-cols-2 2xl:grid-cols-4 max-h-[240px] overflow-y-auto pr-1">
        <button
          v-for="report in reports"
          :key="report.id"
          @click="loadReportDetail(report.id)"
          class="w-full text-left p-3 rounded-lg border transition-colors"
          :class="selectedReport?.id === report.id ? 'border-blue-300 bg-blue-50 shadow-sm' : 'border-gray-100 hover:bg-gray-50'"
        >
          <div class="flex items-start justify-between gap-3">
            <div class="min-w-0">
              <h3 class="text-sm font-semibold text-gray-900 truncate">{{ report.title }}</h3>
              <p class="text-xs text-gray-500 mt-1">#{{ report.id }} · {{ formatDateTime(report.created_at) }}</p>
            </div>
            <span :class="['px-2 py-0.5 rounded-full text-xs font-medium flex-shrink-0', statusBadgeClass(report.status)]">
              {{ report.status }}
            </span>
          </div>
          <div class="mt-3 flex flex-wrap gap-2 text-xs text-gray-600">
            <span class="rounded bg-white/80 px-2 py-1">论文 {{ report.paper_count }}</span>
            <span class="rounded bg-white/80 px-2 py-1">0 分已排除</span>
          </div>
        </button>
      </div>
    </section>

    <section class="bg-white rounded-xl shadow-sm border border-gray-200 p-5">
      <div v-if="detailLoading" class="flex justify-center py-12">
        <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>

      <div v-else-if="!selectedReport" class="text-sm text-gray-500 text-center py-12">
        选择报告查看内容、投递记录和 Markdown 预览。
      </div>

      <div v-else class="space-y-5">
        <div class="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-4">
          <div class="min-w-0">
            <div class="flex flex-wrap items-center gap-2 mb-2">
              <span :class="['px-2.5 py-0.5 rounded-full text-xs font-medium', statusBadgeClass(selectedReport.status)]">
                {{ selectedReport.status }}
              </span>
              <span class="text-xs text-gray-500">来源：{{ sourceText(selectedReport.source) }}</span>
              <span class="text-xs text-gray-500">创建：{{ formatDateTime(selectedReport.created_at) }}</span>
            </div>
            <h2 class="text-xl font-semibold text-gray-900">{{ selectedReport.title }}</h2>
            <p class="text-sm text-gray-500 mt-1">
              {{ selectedReport.paper_count }} 篇正分论文 · 0 分不相关论文已排除
            </p>
          </div>
          <div class="flex flex-wrap gap-2">
            <button
              @click="sendSelectedReport"
              :disabled="actionLoading"
              class="px-4 py-2 bg-green-600 text-white text-sm font-medium rounded-lg hover:bg-green-700 disabled:opacity-50"
            >
              发送邮件
            </button>
            <button
              @click="downloadMarkdown"
              :disabled="actionLoading"
              class="px-4 py-2 border border-gray-300 text-gray-700 text-sm font-medium rounded-lg hover:bg-gray-50 disabled:opacity-50"
            >
              下载 Markdown
            </button>
            <button
              @click="deleteSelectedReport"
              :disabled="actionLoading"
              class="px-4 py-2 border border-red-300 text-red-600 text-sm font-medium rounded-lg hover:bg-red-50 disabled:opacity-50"
            >
              删除报告
            </button>
          </div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
          <div class="rounded-lg bg-blue-50 p-4">
            <p class="text-xs text-blue-600">报告论文</p>
            <p class="text-2xl font-semibold text-blue-900 mt-1">{{ selectedReport.paper_count }}</p>
          </div>
          <div class="rounded-lg bg-green-50 p-4">
            <p class="text-xs text-green-600">邮件投递</p>
            <p class="text-2xl font-semibold text-green-900 mt-1">{{ selectedReport.deliveries.length }}</p>
          </div>
          <div class="rounded-lg bg-purple-50 p-4">
            <p class="text-xs text-purple-600">最近发送</p>
            <p class="text-sm font-semibold text-purple-900 mt-2">{{ formatDateTime(selectedReport.sent_at) }}</p>
          </div>
        </div>

        <div>
          <div class="flex items-center justify-between mb-3">
            <h3 class="text-base font-semibold text-gray-800">报告条目</h3>
            <button
              @click="showMarkdown = !showMarkdown"
              class="text-sm text-blue-600 hover:text-blue-800"
            >
              {{ showMarkdown ? '查看条目' : '查看 Markdown' }}
            </button>
          </div>

          <pre
            v-if="showMarkdown"
            class="whitespace-pre-wrap rounded-lg bg-gray-900 text-gray-100 text-sm leading-6 p-4 max-h-[520px] overflow-y-auto"
          >{{ selectedReport.markdown }}</pre>

          <div v-else-if="selectedReport.items.length === 0" class="rounded-lg bg-gray-50 p-8 text-center text-sm text-gray-500">
            本报告没有正分论文。
          </div>

          <div v-else class="grid grid-cols-1 2xl:grid-cols-2 gap-4">
            <div
              v-for="item in selectedReport.items"
              :key="item.id"
              class="rounded-lg border border-gray-100 p-4"
            >
              <div class="flex items-start justify-between gap-3">
                <div class="min-w-0">
                  <div class="flex flex-wrap items-center gap-2 mb-2">
                    <span :class="['px-2.5 py-0.5 rounded-full text-xs font-medium', scoreBadgeClass(item.relevance_score)]">
                      {{ item.relevance_score.toFixed(1) }}
                    </span>
                    <span v-for="keyword in item.keywords" :key="keyword" class="px-2 py-0.5 rounded-full text-xs bg-blue-100 text-blue-800">
                      {{ keyword }}
                    </span>
                    <span v-if="item.journal_name" class="text-xs text-gray-500">{{ item.journal_name }}</span>
                  </div>
                  <h4 class="text-base font-semibold text-gray-900">{{ item.title }}</h4>
                  <p v-if="item.authors" class="text-sm text-gray-500 mt-1">{{ item.authors }}</p>
                </div>
                <a
                  v-if="item.url"
                  :href="item.url"
                  target="_blank"
                  class="text-sm text-blue-600 hover:text-blue-800 flex-shrink-0"
                >
                  原文
                </a>
              </div>
              <p v-if="item.summary" class="mt-3 rounded-lg bg-purple-50 p-3 text-sm text-purple-900">
                {{ item.summary }}
              </p>
              <p class="mt-3 text-sm text-gray-600 leading-6">
                {{ item.abstract || '该条目没有摘要。' }}
              </p>
            </div>
          </div>
        </div>

        <div>
          <h3 class="text-base font-semibold text-gray-800 mb-3">邮件投递记录</h3>
          <div v-if="selectedReport.deliveries.length === 0" class="rounded-lg bg-gray-50 p-6 text-center text-sm text-gray-500">
            暂无投递记录。
          </div>
          <div v-else class="grid gap-2 md:grid-cols-2">
            <div
              v-for="delivery in selectedReport.deliveries"
              :key="delivery.id"
              class="rounded-lg border border-gray-100 p-3"
            >
              <div class="flex flex-wrap items-center justify-between gap-3">
                <div class="min-w-0">
                  <div class="flex items-center gap-2">
                    <span :class="['px-2 py-0.5 rounded-full text-xs font-medium', deliveryBadgeClass(delivery.status)]">
                      {{ deliveryStatusText(delivery.status) }}
                    </span>
                    <span class="text-sm text-gray-700 truncate">{{ delivery.recipient || '未配置收件人' }}</span>
                  </div>
                  <p class="text-xs text-gray-500 mt-1">{{ delivery.subject || selectedReport.title }}</p>
                  <p v-if="delivery.error_message" class="text-xs text-red-600 mt-1">{{ delivery.error_message }}</p>
                </div>
                <span class="text-xs text-gray-500 flex-shrink-0">{{ formatDateTime(delivery.sent_at || delivery.created_at) }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { reportApi } from '@/api'
import type { Report, ReportDetail } from '@/api'
import { useAppStore } from '@/stores/app'

const appStore = useAppStore()
const reports = ref<Report[]>([])
const selectedReport = ref<ReportDetail | null>(null)
const reportsLoading = ref(true)
const detailLoading = ref(false)
const actionLoading = ref(false)
const showMarkdown = ref(false)

function formatDateTime(value: string | null): string {
  if (!value) return '-'
  return new Date(value).toLocaleString('zh-CN', { hour12: false })
}

function statusBadgeClass(status: string): string {
  if (status === 'ready') return 'bg-blue-100 text-blue-800'
  if (status === 'sent') return 'bg-green-100 text-green-800'
  if (status === 'failed') return 'bg-red-100 text-red-800'
  return 'bg-gray-100 text-gray-700'
}

function deliveryBadgeClass(status: string): string {
  if (status === 'sent') return 'bg-green-100 text-green-800'
  if (status === 'skipped') return 'bg-yellow-100 text-yellow-800'
  if (status === 'failed') return 'bg-red-100 text-red-800'
  return 'bg-gray-100 text-gray-700'
}

function deliveryStatusText(status: string): string {
  const labels: Record<string, string> = {
    pending: '等待中',
    sent: '已发送',
    skipped: '已跳过',
    failed: '失败',
  }
  return labels[status] || status
}

function scoreBadgeClass(score: number): string {
  if (score >= 7) return 'bg-green-100 text-green-800'
  if (score >= 5) return 'bg-yellow-100 text-yellow-800'
  return 'bg-red-100 text-red-800'
}

function sourceText(source: string | null): string {
  const labels: Record<string, string> = {
    manual: '手动生成',
    'daily-email': '每日邮件',
  }
  return labels[source || ''] || source || '-'
}

async function loadReports(selectFirst = false) {
  reportsLoading.value = true
  try {
    const { data } = await reportApi.list(50)
    reports.value = data
    if (selectFirst && data.length > 0) {
      await loadReportDetail(data[0].id)
    } else if (selectedReport.value && !data.some((item) => item.id === selectedReport.value?.id)) {
      selectedReport.value = null
    }
  } catch (err: any) {
    appStore.error('加载报告失败: ' + err.message)
  } finally {
    reportsLoading.value = false
  }
}

async function loadReportDetail(id: number) {
  detailLoading.value = true
  showMarkdown.value = false
  try {
    const { data } = await reportApi.get(id)
    selectedReport.value = data
  } catch (err: any) {
    appStore.error('加载报告详情失败: ' + err.message)
  } finally {
    detailLoading.value = false
  }
}

async function createReport() {
  actionLoading.value = true
  try {
    const { data } = await reportApi.create({ source: 'manual' })
    appStore.success(`报告已生成：${data.paper_count} 篇论文`)
    await loadReports()
    await loadReportDetail(data.id)
  } catch (err: any) {
    appStore.error('生成报告失败: ' + err.message)
  } finally {
    actionLoading.value = false
  }
}

async function sendSelectedReport() {
  if (!selectedReport.value) return
  actionLoading.value = true
  try {
    const { data } = await reportApi.send(selectedReport.value.id)
    if (data.status === 'sent') {
      appStore.success('报告邮件已发送')
    } else if (data.status === 'skipped') {
      appStore.warning(data.error_message || '邮件未发送，请检查邮件配置')
    } else {
      appStore.error(data.error_message || '邮件发送失败')
    }
    await loadReportDetail(selectedReport.value.id)
    await loadReports()
  } catch (err: any) {
    appStore.error('发送报告失败: ' + err.message)
  } finally {
    actionLoading.value = false
  }
}

async function deleteSelectedReport() {
  if (!selectedReport.value) return
  if (!confirm(`确定删除报告「${selectedReport.value.title}」？该操作不可恢复。`)) return
  actionLoading.value = true
  try {
    await reportApi.delete(selectedReport.value.id)
    appStore.success('报告已删除')
    selectedReport.value = null
    await loadReports(true)
  } catch (err: any) {
    appStore.error('删除报告失败: ' + err.message)
  } finally {
    actionLoading.value = false
  }
}

async function downloadMarkdown() {
  if (!selectedReport.value) return
  actionLoading.value = true
  try {
    const { data } = await reportApi.markdown(selectedReport.value.id)
    const blob = data instanceof Blob ? data : new Blob([data], { type: 'text/markdown;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `paperpulse-report-${selectedReport.value.id}.md`
    link.click()
    URL.revokeObjectURL(url)
  } catch (err: any) {
    appStore.error('下载 Markdown 失败: ' + err.message)
  } finally {
    actionLoading.value = false
  }
}

onMounted(() => {
  loadReports(true)
})
</script>
