<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
      <h2 class="text-lg font-semibold text-gray-800">RSS 订阅源管理</h2>
      <div class="flex flex-wrap gap-2">
        <button
          @click="fetchAllFeeds"
          :disabled="bulkLoading || feeds.length === 0"
          class="inline-flex items-center px-4 py-2.5 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 disabled:opacity-50 transition-colors"
        >
          <svg class="w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          {{ bulkLoading ? '刷新中...' : '全部刷新' }}
        </button>
        <button
          @click="deleteSelectedFeeds"
          :disabled="bulkLoading || selectedIds.size === 0"
          class="inline-flex items-center px-4 py-2.5 bg-red-600 text-white text-sm font-medium rounded-lg hover:bg-red-700 disabled:opacity-50 transition-colors"
        >
          删除所选
        </button>
        <button
          @click="showAddModal = true"
          class="inline-flex items-center px-4 py-2.5 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors"
        >
          <svg class="w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
          </svg>
          添加订阅源
        </button>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="flex justify-center py-12">
      <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
    </div>

    <!-- Feed List -->
    <div v-else-if="feeds.length > 0" class="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
      <table class="min-w-full divide-y divide-gray-200">
        <thead class="bg-gray-50">
          <tr>
            <th class="px-6 py-3 text-left">
              <input
                type="checkbox"
                :checked="allSelected"
                @change="toggleSelectAll"
                class="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
            </th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">名称</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">URL</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">期刊</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">论文数</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">上次抓取</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">状态</th>
            <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">操作</th>
          </tr>
        </thead>
        <tbody class="bg-white divide-y divide-gray-200">
          <tr v-for="feed in feeds" :key="feed.id" class="hover:bg-gray-50">
            <td class="px-6 py-4 whitespace-nowrap">
              <input
                type="checkbox"
                :checked="selectedIds.has(feed.id)"
                @change="toggleFeedSelection(feed.id)"
                class="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
            </td>
            <td class="px-6 py-4 whitespace-nowrap">
              <div class="text-sm font-medium text-gray-900">{{ feed.name }}</div>
            </td>
            <td class="px-6 py-4">
              <div class="text-sm text-gray-500 max-w-xs truncate" :title="feed.url">
                {{ feed.url }}
              </div>
            </td>
            <td class="px-6 py-4 whitespace-nowrap">
              <div class="text-sm text-gray-600">{{ feed.journal_name || '-' }}</div>
            </td>
            <td class="px-6 py-4 whitespace-nowrap">
              <div class="text-sm text-gray-900">{{ feed.paper_count }}</div>
            </td>
            <td class="px-6 py-4 whitespace-nowrap">
              <div class="text-sm text-gray-500">
                {{ feed.last_fetched ? formatDate(feed.last_fetched) : '从未' }}
              </div>
            </td>
            <td class="px-6 py-4 whitespace-nowrap">
              <button
                @click="toggleFeed(feed)"
                :class="[
                  'relative inline-flex h-5 w-9 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none',
                  feed.enabled ? 'bg-blue-600' : 'bg-gray-300',
                ]"
              >
                <span
                  :class="[
                    'pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out',
                    feed.enabled ? 'translate-x-4' : 'translate-x-0',
                  ]"
                ></span>
              </button>
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-right text-sm space-x-2">
              <button
                @click="fetchFeed(feed)"
                :disabled="fetchingIds.has(feed.id)"
                class="text-blue-600 hover:text-blue-800 disabled:opacity-50"
                title="抓取"
              >
                <svg class="w-4 h-4 inline" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                    d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
              </button>
              <button
                @click="editFeed(feed)"
                class="text-gray-600 hover:text-gray-800"
                title="编辑"
              >
                <svg class="w-4 h-4 inline" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                    d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                </svg>
              </button>
              <button
                @click="deleteFeed(feed)"
                class="text-red-600 hover:text-red-800"
                title="删除"
              >
                <svg class="w-4 h-4 inline" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                    d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Empty State -->
    <div v-else class="bg-white rounded-xl shadow-sm border border-gray-200 p-12 text-center">
      <svg class="w-12 h-12 text-gray-400 mx-auto mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
          d="M6 5c7.18 0 13 5.82 13 13M6 11a7 7 0 017 7m-6 0a1 1 0 11-2 0 1 1 0 012 0z" />
      </svg>
      <p class="text-gray-500 mb-4">还没有订阅源</p>
      <button
        @click="showAddModal = true"
        class="text-blue-600 hover:text-blue-800 text-sm font-medium"
      >
        添加第一个订阅源 →
      </button>
    </div>

    <!-- Add/Edit Modal -->
    <div v-if="showAddModal || showEditModal" class="fixed inset-0 z-50 flex items-center justify-center modal-backdrop">
      <div class="bg-white rounded-xl shadow-xl w-full max-w-lg mx-4 p-6">
        <h3 class="text-lg font-semibold text-gray-800 mb-4">
          {{ showEditModal ? '编辑订阅源' : '添加订阅源' }}
        </h3>
        <form @submit.prevent="submitFeed" class="space-y-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">名称</label>
            <input
              v-model="feedForm.name"
              type="text"
              required
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
              placeholder="如：Nature Materials"
            />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">RSS URL</label>
            <input
              v-model="feedForm.url"
              type="url"
              required
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
              placeholder="https://..."
            />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">期刊名称</label>
            <input
              v-model="feedForm.journal_name"
              type="text"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
              placeholder="如：Nature Materials"
            />
          </div>
          <div class="flex justify-end space-x-3 pt-2">
            <button
              type="button"
              @click="closeModal"
              class="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
            >
              取消
            </button>
            <button
              type="submit"
              :disabled="submitting"
              class="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
            >
              {{ submitting ? '保存中...' : '保存' }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted } from 'vue'
import { feedApi } from '@/api'
import type { Feed, FeedCreate } from '@/api'
import { useAppStore } from '@/stores/app'

const appStore = useAppStore()

const feeds = ref<Feed[]>([])
const loading = ref(true)
const showAddModal = ref(false)
const showEditModal = ref(false)
const submitting = ref(false)
const bulkLoading = ref(false)
const editingId = ref<number | null>(null)
const fetchingIds = ref(new Set<number>())
const selectedIds = ref(new Set<number>())

const feedForm = ref<FeedCreate>({
  name: '',
  url: '',
  journal_name: '',
})

const allSelected = computed(() => feeds.value.length > 0 && selectedIds.value.size === feeds.value.length)

function formatDate(dateStr: string): string {
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

async function loadFeeds() {
  loading.value = true
  try {
    const { data } = await feedApi.list()
    feeds.value = data
    selectedIds.value = new Set([...selectedIds.value].filter((id) => data.some((feed) => feed.id === id)))
  } catch (err: any) {
    appStore.error('加载订阅源失败: ' + err.message)
  } finally {
    loading.value = false
  }
}

function toggleFeedSelection(id: number) {
  const next = new Set(selectedIds.value)
  if (next.has(id)) {
    next.delete(id)
  } else {
    next.add(id)
  }
  selectedIds.value = next
}

function toggleSelectAll() {
  selectedIds.value = allSelected.value ? new Set() : new Set(feeds.value.map((feed) => feed.id))
}

function editFeed(feed: Feed) {
  editingId.value = feed.id
  feedForm.value = {
    name: feed.name,
    url: feed.url,
    journal_name: feed.journal_name || '',
  }
  showEditModal.value = true
}

function closeModal() {
  showAddModal.value = false
  showEditModal.value = false
  editingId.value = null
  feedForm.value = { name: '', url: '', journal_name: '' }
}

async function submitFeed() {
  submitting.value = true
  try {
    if (showEditModal.value && editingId.value !== null) {
      await feedApi.update(editingId.value, feedForm.value)
      appStore.success('订阅源已更新')
    } else {
      await feedApi.create(feedForm.value)
      appStore.success('订阅源已添加')
    }
    closeModal()
    await loadFeeds()
  } catch (err: any) {
    appStore.error('操作失败: ' + err.message)
  } finally {
    submitting.value = false
  }
}

async function deleteFeed(feed: Feed) {
  if (!confirm(`确定要删除订阅源 "${feed.name}" 吗？`)) return
  try {
    await feedApi.delete(feed.id)
    appStore.success('订阅源已删除')
    await loadFeeds()
  } catch (err: any) {
    appStore.error('删除失败: ' + err.message)
  }
}

async function deleteSelectedFeeds() {
  const ids = [...selectedIds.value]
  if (ids.length === 0) return
  if (!confirm(`确定要删除选中的 ${ids.length} 个订阅源吗？`)) return
  bulkLoading.value = true
  try {
    const { data } = await feedApi.bulkDelete(ids)
    appStore.success(`已删除 ${data.deleted_count} 个订阅源`)
    selectedIds.value = new Set()
    await loadFeeds()
  } catch (err: any) {
    appStore.error('批量删除失败: ' + err.message)
  } finally {
    bulkLoading.value = false
  }
}

async function toggleFeed(feed: Feed) {
  try {
    await feedApi.update(feed.id, { enabled: !feed.enabled })
    feed.enabled = !feed.enabled
    appStore.success(feed.enabled ? '已启用' : '已禁用')
  } catch (err: any) {
    appStore.error('操作失败: ' + err.message)
  }
}

async function fetchFeed(feed: Feed) {
  fetchingIds.value.add(feed.id)
  try {
    await feedApi.fetch(feed.id)
    appStore.success(`"${feed.name}" 抓取完成`)
    await loadFeeds()
  } catch (err: any) {
    appStore.error('抓取失败: ' + err.message)
  } finally {
    fetchingIds.value.delete(feed.id)
  }
}

async function fetchAllFeeds() {
  bulkLoading.value = true
  try {
    const { data } = await feedApi.fetchAll()
    appStore.success(`全部刷新完成：${data.feed_count} 个订阅源，新增 ${data.new_papers} 篇论文`)
    await loadFeeds()
  } catch (err: any) {
    appStore.error('全部刷新失败: ' + err.message)
  } finally {
    bulkLoading.value = false
  }
}

onMounted(loadFeeds)
</script>
