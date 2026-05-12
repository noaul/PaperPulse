<template>
  <div class="space-y-6">
    <!-- Header with Add Form -->
    <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <h2 class="text-lg font-semibold text-gray-800 mb-4">添加关键词</h2>
      <div class="grid gap-5 lg:grid-cols-[1fr_1.2fr]">
        <form @submit.prevent="addKeyword" class="flex flex-wrap gap-3 items-end">
          <div class="flex-1 min-w-[200px]">
            <label class="block text-sm font-medium text-gray-700 mb-1">关键词</label>
            <input
              v-model="newKeyword.word"
              type="text"
              required
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none text-sm"
              placeholder="输入关键词..."
            />
          </div>
          <div class="w-48">
            <label class="block text-sm font-medium text-gray-700 mb-1">分类</label>
            <input
              v-model="newKeyword.category"
              type="text"
              required
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none text-sm"
              placeholder="如：研究方向"
              list="category-suggestions"
            />
            <datalist id="category-suggestions">
              <option v-for="cat in existingCategories" :key="cat" :value="cat" />
            </datalist>
          </div>
          <button
            type="submit"
            :disabled="adding"
            class="px-5 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            {{ adding ? '添加中...' : '添加' }}
          </button>
        </form>

        <form @submit.prevent="addKeywordsBulk" class="space-y-3">
          <div class="grid gap-3 md:grid-cols-[1fr_12rem]">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">批量关键词</label>
              <textarea
                v-model="bulkText"
                rows="3"
                required
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none text-sm resize-y"
                placeholder="每行一个，也可用逗号或分号分隔"
              ></textarea>
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">批量分类</label>
              <input
                v-model="bulkCategory"
                type="text"
                required
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none text-sm"
                placeholder="如：研究方向"
                list="category-suggestions"
              />
              <button
                type="submit"
                :disabled="bulkAdding"
                class="mt-3 w-full px-5 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 disabled:opacity-50 transition-colors"
              >
                {{ bulkAdding ? '批量添加中...' : '批量添加' }}
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="flex justify-center py-12">
      <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
    </div>

    <!-- Keywords by Category -->
    <div v-else-if="groupedKeywords.length > 0" class="space-y-4">
      <div
        v-for="group in groupedKeywords"
        :key="group.category"
        class="bg-white rounded-xl shadow-sm border border-gray-200 p-6"
      >
        <div class="flex items-center justify-between mb-4">
          <h3 class="text-base font-semibold text-gray-800">
            {{ group.category }}
            <span class="text-sm font-normal text-gray-500 ml-2">
              ({{ group.keywords.length }})
            </span>
          </h3>
        </div>

        <div class="space-y-2">
          <div
            v-for="kw in group.keywords"
            :key="kw.id"
            class="flex items-center justify-between p-3 rounded-lg border border-gray-100 hover:bg-gray-50 transition-colors"
          >
            <div class="flex items-center space-x-3 flex-1">
              <!-- Enable/Disable Toggle -->
              <button
                @click="toggleKeyword(kw)"
                :class="[
                  'relative inline-flex h-5 w-9 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none',
                  kw.enabled ? 'bg-blue-600' : 'bg-gray-300',
                ]"
              >
                <span
                  :class="[
                    'pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out',
                    kw.enabled ? 'translate-x-4' : 'translate-x-0',
                  ]"
                ></span>
              </button>

              <!-- Word Display/Edit -->
              <template v-if="editingId === kw.id">
                <input
                  v-model="editForm.word"
                  type="text"
                  class="px-2 py-1 border border-gray-300 rounded text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                  @keyup.enter="saveEdit(kw)"
                  @keyup.escape="cancelEdit"
                />
                <input
                  v-model="editForm.category"
                  type="text"
                  class="px-2 py-1 border border-gray-300 rounded text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none w-32"
                  @keyup.enter="saveEdit(kw)"
                  @keyup.escape="cancelEdit"
                />
              </template>
              <template v-else>
                <span
                  :class="[
                    'text-sm font-medium',
                    kw.enabled ? 'text-gray-900' : 'text-gray-400',
                  ]"
                >
                  {{ kw.word }}
                </span>
              </template>
            </div>

            <!-- Actions -->
            <div class="flex items-center space-x-2">
              <template v-if="editingId === kw.id">
                <button
                  @click="saveEdit(kw)"
                  class="text-green-600 hover:text-green-800 text-sm"
                >
                  保存
                </button>
                <button
                  @click="cancelEdit"
                  class="text-gray-500 hover:text-gray-700 text-sm"
                >
                  取消
                </button>
              </template>
              <template v-else>
                <button
                  @click="startEdit(kw)"
                  class="text-gray-500 hover:text-gray-700"
                  title="编辑"
                >
                  <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                      d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                  </svg>
                </button>
                <button
                  @click="deleteKeyword(kw)"
                  class="text-red-500 hover:text-red-700"
                  title="删除"
                >
                  <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                      d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                </button>
              </template>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Empty State -->
    <div v-else class="bg-white rounded-xl shadow-sm border border-gray-200 p-12 text-center">
      <svg class="w-12 h-12 text-gray-400 mx-auto mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
          d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" />
      </svg>
      <p class="text-gray-500 mb-4">还没有关键词</p>
      <p class="text-sm text-gray-400">添加关键词以帮助系统识别相关论文</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { keywordApi } from '@/api'
import type { Keyword } from '@/api'
import { useAppStore } from '@/stores/app'

const appStore = useAppStore()

const keywords = ref<Keyword[]>([])
const loading = ref(true)
const adding = ref(false)
const bulkAdding = ref(false)
const editingId = ref<number | null>(null)

const newKeyword = ref({ word: '', category: '' })
const bulkText = ref('')
const bulkCategory = ref('default')
const editForm = ref({ word: '', category: '' })

const existingCategories = computed(() => {
  return [...new Set(keywords.value.map((k) => k.category).filter(Boolean))]
})

const groupedKeywords = computed(() => {
  const groups = new Map<string, Keyword[]>()
  for (const kw of keywords.value) {
    const cat = kw.category || '未分类'
    if (!groups.has(cat)) groups.set(cat, [])
    groups.get(cat)!.push(kw)
  }
  return Array.from(groups.entries()).map(([category, kws]) => ({
    category,
    keywords: kws,
  }))
})

async function loadKeywords() {
  loading.value = true
  try {
    const { data } = await keywordApi.list()
    keywords.value = data
  } catch (err: any) {
    appStore.error('加载关键词失败: ' + err.message)
  } finally {
    loading.value = false
  }
}

async function addKeyword() {
  adding.value = true
  try {
    await keywordApi.create(newKeyword.value)
    appStore.success('关键词已添加')
    newKeyword.value = { word: '', category: '' }
    await loadKeywords()
  } catch (err: any) {
    appStore.error('添加失败: ' + err.message)
  } finally {
    adding.value = false
  }
}

async function addKeywordsBulk() {
  bulkAdding.value = true
  try {
    const { data } = await keywordApi.bulkCreate({
      text: bulkText.value,
      category: bulkCategory.value,
      enabled: true,
    })
    const skipped = data.skipped_count ? `，跳过 ${data.skipped_count} 个重复项` : ''
    appStore.success(`已添加 ${data.created_count} 个关键词${skipped}`)
    bulkText.value = ''
    await loadKeywords()
  } catch (err: any) {
    appStore.error('批量添加失败: ' + err.message)
  } finally {
    bulkAdding.value = false
  }
}

function startEdit(kw: Keyword) {
  editingId.value = kw.id
  editForm.value = { word: kw.word, category: kw.category }
}

function cancelEdit() {
  editingId.value = null
  editForm.value = { word: '', category: '' }
}

async function saveEdit(kw: Keyword) {
  try {
    await keywordApi.update(kw.id, editForm.value)
    appStore.success('关键词已更新')
    cancelEdit()
    await loadKeywords()
  } catch (err: any) {
    appStore.error('更新失败: ' + err.message)
  }
}

async function toggleKeyword(kw: Keyword) {
  try {
    await keywordApi.update(kw.id, { enabled: !kw.enabled })
    kw.enabled = !kw.enabled
    appStore.success(kw.enabled ? '已启用' : '已禁用')
  } catch (err: any) {
    appStore.error('操作失败: ' + err.message)
  }
}

async function deleteKeyword(kw: Keyword) {
  if (!confirm(`确定要删除关键词 "${kw.word}" 吗？`)) return
  try {
    await keywordApi.delete(kw.id)
    appStore.success('关键词已删除')
    await loadKeywords()
  } catch (err: any) {
    appStore.error('删除失败: ' + err.message)
  }
}

onMounted(loadKeywords)
</script>
