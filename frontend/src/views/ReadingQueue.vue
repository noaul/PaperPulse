<template>
  <div class="space-y-6">
    <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-5">
      <div class="flex flex-col xl:flex-row xl:items-end gap-4">
        <div class="flex-1 min-w-[220px]">
          <label class="block text-xs text-gray-500 mb-1">搜索</label>
          <input
            v-model="filters.search"
            type="text"
            placeholder="标题或摘要"
            class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none text-sm"
            @input="debouncedLoad"
          />
        </div>
        <div>
          <label class="block text-xs text-gray-500 mb-1">状态</label>
          <select
            v-model="filters.status"
            @change="loadItems(1)"
            class="w-36 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none text-sm"
          >
            <option value="">全部</option>
            <option value="unread">待读</option>
            <option value="read">已读</option>
          </select>
        </div>
        <div>
          <label class="block text-xs text-gray-500 mb-1">标签</label>
          <input
            v-model="filters.tag"
            type="text"
            placeholder="rag"
            class="w-40 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none text-sm"
            @input="debouncedLoad"
          />
        </div>
        <button
          @click="resetFilters"
          class="px-4 py-2 border border-gray-300 text-gray-700 text-sm font-medium rounded-lg hover:bg-gray-50"
        >
          重置
        </button>
        <button
          @click="startCreate"
          class="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700"
        >
          添加条目
        </button>
      </div>
    </div>

    <div class="grid grid-cols-1 xl:grid-cols-[1fr_380px] gap-6 items-start">
      <div class="space-y-3">
        <div v-if="loading" class="flex justify-center py-12">
          <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        </div>

        <div v-else-if="items.length === 0" class="bg-white rounded-xl shadow-sm border border-gray-200 p-12 text-center">
          <svg class="w-12 h-12 text-gray-400 mx-auto mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-4-7 4V5z" />
          </svg>
          <p class="text-gray-500">暂无阅读队列条目。</p>
        </div>

        <article
          v-for="item in items"
          v-else
          :key="item.id"
          class="bg-white rounded-xl shadow-sm border border-gray-200 p-5"
        >
          <div class="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-4">
            <div class="min-w-0 flex-1">
              <div class="flex flex-wrap items-center gap-2 mb-2">
                <button
                  :class="['px-2.5 py-0.5 rounded-full text-xs font-medium', statusBadgeClass(item.status)]"
                  @click="toggleStatus(item)"
                >
                  {{ statusText(item.status) }}
                </button>
                <span v-for="tag in item.tags" :key="tag" class="px-2 py-0.5 rounded-full text-xs bg-blue-100 text-blue-800">
                  {{ tag }}
                </span>
                <span class="text-xs text-gray-500">{{ formatDateTime(item.created_at) }}</span>
              </div>
              <h2 class="text-base font-semibold text-gray-900 leading-6">{{ item.title }}</h2>
              <a
                v-if="item.url"
                :href="item.url"
                target="_blank"
                class="inline-flex mt-1 text-sm text-blue-600 hover:text-blue-800 break-all"
              >
                {{ item.url }}
              </a>
              <p class="mt-3 text-sm text-gray-600 leading-6">
                {{ item.abstract || '没有摘要。' }}
              </p>
              <p v-if="item.notes" class="mt-3 rounded-lg bg-purple-50 p-3 text-sm text-purple-900">
                {{ item.notes }}
              </p>
            </div>
            <div class="flex lg:flex-col gap-2 flex-shrink-0">
              <button
                @click="startEdit(item)"
                class="px-3 py-1.5 border border-gray-300 text-gray-700 text-sm rounded-lg hover:bg-gray-50"
              >
                编辑
              </button>
              <button
                @click="removeItem(item)"
                class="px-3 py-1.5 bg-red-100 text-red-700 text-sm rounded-lg hover:bg-red-200"
              >
                删除
              </button>
            </div>
          </div>
        </article>

        <div v-if="totalPages > 1" class="flex items-center justify-center gap-3">
          <button
            @click="loadItems(currentPage - 1)"
            :disabled="currentPage <= 1"
            class="px-3 py-1.5 text-sm rounded-lg border border-gray-300 text-gray-700 hover:bg-gray-50 disabled:opacity-50"
          >
            上一页
          </button>
          <span class="text-sm text-gray-500">第 {{ currentPage }} / {{ totalPages }} 页，共 {{ totalItems }} 条</span>
          <button
            @click="loadItems(currentPage + 1)"
            :disabled="currentPage >= totalPages"
            class="px-3 py-1.5 text-sm rounded-lg border border-gray-300 text-gray-700 hover:bg-gray-50 disabled:opacity-50"
          >
            下一页
          </button>
        </div>
      </div>

      <aside class="bg-white rounded-xl shadow-sm border border-gray-200 p-5 sticky top-6">
        <div class="flex items-center justify-between gap-3 mb-4">
          <h2 class="text-lg font-semibold text-gray-800">{{ editingId ? '编辑条目' : '添加条目' }}</h2>
          <button
            v-if="editingId"
            @click="clearForm"
            class="text-sm text-gray-500 hover:text-gray-900"
          >
            取消编辑
          </button>
        </div>

        <div class="space-y-4">
          <label class="block">
            <span class="block text-xs text-gray-500 mb-1">标题</span>
            <input
              v-model="form.title"
              type="text"
              placeholder="论文或文章标题"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none text-sm"
            />
          </label>

          <label class="block">
            <span class="block text-xs text-gray-500 mb-1">URL</span>
            <input
              v-model="form.url"
              type="url"
              placeholder="https://..."
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none text-sm"
            />
          </label>

          <label class="block">
            <span class="block text-xs text-gray-500 mb-1">标签</span>
            <input
              v-model="tagText"
              type="text"
              placeholder="用逗号分隔，如 rag, graph"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none text-sm"
            />
          </label>

          <label class="block">
            <span class="block text-xs text-gray-500 mb-1">摘要</span>
            <textarea
              v-model="form.abstract"
              rows="6"
              placeholder="粘贴摘要或简短说明"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none text-sm resize-y"
            ></textarea>
          </label>

          <label class="block">
            <span class="block text-xs text-gray-500 mb-1">备注</span>
            <textarea
              v-model="form.notes"
              rows="4"
              placeholder="阅读理由、下一步动作或个人笔记"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none text-sm resize-y"
            ></textarea>
          </label>

          <div class="flex gap-2">
            <button
              @click="saveItem"
              :disabled="saving"
              class="flex-1 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50"
            >
              {{ saving ? '保存中...' : '保存' }}
            </button>
            <button
              @click="clearForm"
              class="px-4 py-2 border border-gray-300 text-gray-700 text-sm font-medium rounded-lg hover:bg-gray-50"
            >
              清空
            </button>
          </div>
        </div>
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { readingQueueApi } from '@/api'
import type { ReadingQueueItem, ReadingQueueStatus } from '@/api'
import { useAppStore } from '@/stores/app'

const appStore = useAppStore()
const items = ref<ReadingQueueItem[]>([])
const loading = ref(true)
const saving = ref(false)
const currentPage = ref(1)
const totalPages = ref(1)
const totalItems = ref(0)
const editingId = ref<number | null>(null)
const tagText = ref('')
const pageSize = 20

const filters = reactive({
  search: '',
  status: '' as ReadingQueueStatus | '',
  tag: '',
})

const form = reactive({
  title: '',
  url: '',
  abstract: '',
  notes: '',
})

let searchTimeout: ReturnType<typeof setTimeout> | null = null

function debouncedLoad() {
  if (searchTimeout) clearTimeout(searchTimeout)
  searchTimeout = setTimeout(() => loadItems(1), 350)
}

function parseTags(value: string): string[] {
  return value
    .split(',')
    .map((tag) => tag.trim())
    .filter((tag, index, all) => tag.length > 0 && all.indexOf(tag) === index)
}

function formatDateTime(value: string | null): string {
  return value ? new Date(value).toLocaleString('zh-CN', { hour12: false }) : '-'
}

function statusText(status: ReadingQueueStatus): string {
  return status === 'read' ? '已读' : '待读'
}

function statusBadgeClass(status: ReadingQueueStatus): string {
  return status === 'read' ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'
}

function startCreate() {
  clearForm()
}

function startEdit(item: ReadingQueueItem) {
  editingId.value = item.id
  form.title = item.title
  form.url = item.url
  form.abstract = item.abstract
  form.notes = item.notes
  tagText.value = item.tags.join(', ')
}

function clearForm() {
  editingId.value = null
  form.title = ''
  form.url = ''
  form.abstract = ''
  form.notes = ''
  tagText.value = ''
}

function resetFilters() {
  filters.search = ''
  filters.status = ''
  filters.tag = ''
  loadItems(1)
}

async function loadItems(page: number) {
  if (page < 1) return
  loading.value = true
  try {
    const { data } = await readingQueueApi.list({
      page,
      page_size: pageSize,
      search: filters.search.trim() || undefined,
      status: filters.status || undefined,
      tag: filters.tag.trim() || undefined,
    })
    items.value = data.items
    currentPage.value = data.page
    totalPages.value = data.pages
    totalItems.value = data.total
  } catch (err: any) {
    appStore.error('加载阅读队列失败: ' + err.message)
  } finally {
    loading.value = false
  }
}

async function saveItem() {
  if (!form.title.trim()) {
    appStore.warning('标题不能为空')
    return
  }
  saving.value = true
  const payload = {
    title: form.title,
    url: form.url,
    abstract: form.abstract,
    tags: parseTags(tagText.value),
    notes: form.notes,
  }
  try {
    if (editingId.value) {
      await readingQueueApi.update(editingId.value, payload)
      appStore.success('条目已更新')
    } else {
      await readingQueueApi.create(payload)
      appStore.success('条目已添加')
    }
    clearForm()
    await loadItems(currentPage.value)
  } catch (err: any) {
    appStore.error('保存阅读队列失败: ' + err.message)
  } finally {
    saving.value = false
  }
}

async function toggleStatus(item: ReadingQueueItem) {
  try {
    await readingQueueApi.update(item.id, { status: item.status === 'read' ? 'unread' : 'read' })
    await loadItems(currentPage.value)
  } catch (err: any) {
    appStore.error('更新状态失败: ' + err.message)
  }
}

async function removeItem(item: ReadingQueueItem) {
  if (!confirm(`删除「${item.title}」？`)) return
  try {
    await readingQueueApi.delete(item.id)
    appStore.success('条目已删除')
    await loadItems(currentPage.value)
  } catch (err: any) {
    appStore.error('删除阅读队列失败: ' + err.message)
  }
}

onMounted(() => {
  loadItems(1)
})
</script>
