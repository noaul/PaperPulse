<template>
  <div class="topic-page space-y-6">
    <section class="topic-hero rounded-xl border border-gray-200 bg-white p-6">
      <div class="flex flex-col gap-5 xl:flex-row xl:items-center xl:justify-between">
        <div>
          <h1 class="text-2xl font-semibold text-gray-900">邮件主题管理</h1>
          <p class="mt-1 text-sm text-gray-500">像 Google Scholar 订阅一样，为每个研究主题设置检索条件和邮件提醒。</p>
        </div>
        <button
          class="inline-flex items-center justify-center rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-blue-700"
          @click="resetForm"
        >
          新建主题
        </button>
      </div>
    </section>

    <section class="grid gap-6 xl:grid-cols-[minmax(0,1.05fr)_minmax(340px,0.95fr)]">
      <div class="space-y-4">
        <div v-if="loading" class="rounded-xl border border-gray-200 bg-white p-10 text-center">
          <div class="mx-auto h-9 w-9 animate-spin rounded-full border-2 border-blue-100 border-b-blue-600"></div>
        </div>

        <div v-else-if="topics.length === 0" class="rounded-xl border border-gray-200 bg-white p-10 text-center">
          <p class="text-base font-medium text-gray-700">还没有邮件主题</p>
          <p class="mt-2 text-sm text-gray-500">先在右侧创建一个主题，例如“疲劳与蠕变”或“显微组织排除模拟”。</p>
        </div>

        <article
          v-for="topic in topics"
          v-else
          :key="topic.id"
          class="topic-card rounded-xl border border-gray-200 bg-white p-5"
        >
          <div class="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
            <div class="min-w-0">
              <div class="flex flex-wrap items-center gap-2">
                <h2 class="text-lg font-semibold text-gray-900">{{ topic.name }}</h2>
                <span :class="['rounded-md px-2 py-1 text-xs font-semibold', topic.enabled ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500']">
                  {{ topic.enabled ? '邮件发送中' : '邮件已暂停' }}
                </span>
                <span class="rounded-md bg-blue-100 px-2 py-1 text-xs font-semibold text-blue-700">
                  {{ ruleTypeLabel(topic.rule_type) }}
                </span>
              </div>
              <p class="mt-2 text-sm text-gray-500">{{ ruleTypeDescription(topic) }} · 最低评分 {{ topic.threshold.toFixed(1) }}</p>
            </div>

            <div class="flex flex-wrap gap-2">
              <button class="rounded-lg border px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-50" @click="toggleTopic(topic)">
                {{ topic.enabled ? '暂停邮件' : '启动邮件' }}
              </button>
              <button class="rounded-lg border px-3 py-1.5 text-sm text-blue-600 hover:bg-blue-50" @click="editTopic(topic)">
                编辑
              </button>
              <button class="rounded-lg border px-3 py-1.5 text-sm text-red-600 hover:bg-red-50" @click="deleteTopic(topic)">
                删除
              </button>
            </div>
          </div>

          <div class="mt-5 space-y-4">
            <div>
              <p class="mb-2 text-xs font-medium uppercase tracking-wide text-gray-400">包含关键词</p>
              <div class="flex flex-wrap gap-2">
                <span
                  v-for="id in topic.keyword_ids"
                  :key="id"
                  class="rounded-md bg-indigo-50 px-2.5 py-1 text-xs font-medium text-indigo-700"
                >
                  {{ keywordName(id) }}
                </span>
              </div>
            </div>

            <div v-if="topic.exclude_keyword_ids.length > 0">
              <p class="mb-2 text-xs font-medium uppercase tracking-wide text-gray-400">排除关键词</p>
              <div class="flex flex-wrap gap-2">
                <span
                  v-for="id in topic.exclude_keyword_ids"
                  :key="id"
                  class="rounded-md bg-red-50 px-2.5 py-1 text-xs font-medium text-red-700"
                >
                  {{ keywordName(id) }}
                </span>
              </div>
            </div>

            <p class="text-xs text-gray-500">
              收件人：{{ topic.recipients || '使用全局邮件配置' }}
            </p>
          </div>
        </article>
      </div>

      <aside class="topic-composer rounded-xl border border-gray-200 bg-white p-5">
        <div class="flex items-center justify-between gap-3">
          <div>
            <h2 class="text-lg font-semibold text-gray-900">{{ editingId ? '编辑主题' : '创建主题' }}</h2>
            <p class="mt-1 text-sm text-gray-500">{{ editingId ? '调整当前主题的订阅条件' : '为一个研究方向设置独立邮件提醒' }}</p>
          </div>
          <button v-if="editingId" class="rounded-lg border px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-50" @click="resetForm">
            取消编辑
          </button>
        </div>

        <form class="mt-5 space-y-5" @submit.prevent="saveTopic">
          <div>
            <label class="mb-1 block text-sm font-medium text-gray-700">主题名称</label>
            <input
              v-model="form.name"
              required
              class="w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm outline-none"
              placeholder="例如：疲劳与蠕变"
            />
          </div>

          <div>
            <label class="mb-2 block text-sm font-medium text-gray-700">论文满足条件</label>
            <div class="grid gap-2">
              <button
                v-for="option in ruleOptions"
                :key="option.value"
                type="button"
                :class="[
                  'rounded-lg border px-3 py-3 text-left text-sm',
                  form.rule_type === option.value ? 'border-blue-300 bg-blue-600 text-white' : 'border-gray-200 text-gray-600 hover:bg-gray-50',
                ]"
                @click="form.rule_type = option.value"
              >
                <span class="block font-semibold">{{ option.label }}</span>
                <span class="mt-1 block text-xs opacity-80">{{ option.description }}</span>
              </button>
            </div>
          </div>

          <div class="grid gap-3 sm:grid-cols-2">
            <div>
              <label class="mb-1 block text-sm font-medium text-gray-700">最低评分</label>
              <input
                v-model.number="form.threshold"
                type="number"
                min="0"
                max="10"
                step="0.5"
                class="w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm outline-none"
              />
            </div>
            <label class="topic-switch rounded-lg border border-gray-200 p-3">
              <span>
                <span class="block text-sm font-medium text-gray-700">邮件发送</span>
                <span class="block text-xs text-gray-500">{{ form.enabled ? '启用' : '暂停' }}</span>
              </span>
              <input v-model="form.enabled" type="checkbox" class="sr-only" />
              <span :class="['switch-track', form.enabled ? 'switch-track-on' : '']">
                <span :class="['switch-thumb', form.enabled ? 'switch-thumb-on' : '']"></span>
              </span>
            </label>
          </div>

          <div>
            <label class="mb-2 block text-sm font-medium text-gray-700">包含关键词</label>
            <KeywordPicker v-model="form.keyword_ids" :groups="groupedKeywords" tone="include" />
          </div>

          <div>
            <label class="mb-2 block text-sm font-medium text-gray-700">排除关键词</label>
            <KeywordPicker v-model="form.exclude_keyword_ids" :groups="groupedKeywords" tone="exclude" :disabled="form.rule_type !== 'NOT'" />
          </div>

          <div class="rounded-xl bg-gray-50 p-3">
            <label class="mb-2 block text-sm font-medium text-gray-700">快速新增关键词</label>
            <div class="grid gap-2 sm:grid-cols-[1fr_8rem_auto]">
              <input
                v-model="newKeyword.word"
                class="rounded-lg border border-gray-300 px-3 py-2 text-sm outline-none"
                placeholder="关键词"
              />
              <input
                v-model="newKeyword.category"
                class="rounded-lg border border-gray-300 px-3 py-2 text-sm outline-none"
                placeholder="分类"
              />
              <button
                type="button"
                class="rounded-lg bg-indigo-600 px-3 py-2 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-50"
                :disabled="addingKeyword || !newKeyword.word.trim()"
                @click="addKeyword"
              >
                添加
              </button>
            </div>
          </div>

          <div>
            <label class="mb-1 block text-sm font-medium text-gray-700">自定义收件人</label>
            <input
              v-model="form.recipients"
              class="w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm outline-none"
              placeholder="留空使用全局邮件配置"
            />
          </div>

          <button
            type="submit"
            :disabled="saving"
            class="w-full rounded-lg bg-green-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-green-700 disabled:opacity-50"
          >
            {{ editingId ? '保存主题' : '创建主题' }}
          </button>
        </form>
      </aside>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, defineComponent, h, onMounted, reactive, ref, type PropType } from 'vue'
import { emailTopicRuleApi, keywordApi } from '@/api'
import type { EmailRuleType, EmailTopicRule, Keyword } from '@/api'
import { useAppStore } from '@/stores/app'

type KeywordGroup = {
  category: string
  keywords: Keyword[]
}

const KeywordPicker = defineComponent({
  name: 'KeywordPicker',
  props: {
    modelValue: {
      type: Array as PropType<number[]>,
      required: true,
    },
    groups: {
      type: Array as PropType<KeywordGroup[]>,
      required: true,
    },
    tone: {
      type: String as PropType<'include' | 'exclude'>,
      required: true,
    },
    disabled: {
      type: Boolean,
      default: false,
    },
  },
  emits: ['update:modelValue'],
  setup(props, { emit }) {
    function toggle(id: number) {
      if (props.disabled) return
      const selected = new Set(props.modelValue)
      if (selected.has(id)) selected.delete(id)
      else selected.add(id)
      emit('update:modelValue', Array.from(selected))
    }

    return () =>
      h(
        'div',
        {
          class: [
            'keyword-picker min-h-[120px] rounded-xl border border-gray-200 bg-gray-50 p-3',
            props.disabled ? 'opacity-50' : '',
          ],
        },
        props.disabled
          ? h('p', { class: 'text-sm text-gray-500' }, '选择“包含关键词，但排除以下关键词”后可设置排除条件')
          : props.groups.length === 0
            ? h('p', { class: 'text-sm text-gray-500' }, '还没有可选关键词')
            : props.groups.map((group) =>
                h('div', { class: 'mb-3 last:mb-0', key: group.category }, [
                  h('p', { class: 'mb-2 text-xs font-medium text-gray-500' }, group.category),
                  h(
                    'div',
                    { class: 'flex flex-wrap gap-2' },
                    group.keywords.map((keyword) => {
                      const selected = props.modelValue.includes(keyword.id)
                      const color =
                        props.tone === 'exclude'
                          ? selected
                            ? 'border-red-300 bg-red-100 text-red-700'
                            : 'border-gray-200 bg-white text-gray-600 hover:bg-red-50'
                          : selected
                            ? 'border-blue-300 bg-blue-100 text-blue-700'
                            : 'border-gray-200 bg-white text-gray-600 hover:bg-blue-50'
                      return h(
                        'button',
                        {
                          key: keyword.id,
                          type: 'button',
                          class: ['rounded-md border px-2.5 py-1 text-xs font-medium transition-colors', color],
                          onClick: () => toggle(keyword.id),
                        },
                        keyword.word
                      )
                    })
                  ),
                ])
              )
      )
  },
})

const appStore = useAppStore()
const keywords = ref<Keyword[]>([])
const topics = ref<EmailTopicRule[]>([])
const loading = ref(true)
const saving = ref(false)
const addingKeyword = ref(false)
const editingId = ref<number | null>(null)

const ruleOptions: Array<{ value: EmailRuleType; label: string; description: string }> = [
  { value: 'OR', label: '包含任一关键词', description: '适合宽泛跟踪：命中其中一个关键词就进入这个主题。' },
  { value: 'AND', label: '同时包含全部关键词', description: '适合精确主题：必须同时命中所选关键词。' },
  { value: 'NOT', label: '包含关键词，但排除以下关键词', description: '适合降噪：先命中主题词，再过滤掉不想看的方向。' },
]

const form = reactive({
  name: '',
  rule_type: 'OR' as EmailRuleType,
  keyword_ids: [] as number[],
  exclude_keyword_ids: [] as number[],
  threshold: 6,
  enabled: true,
  recipients: '',
})

const newKeyword = reactive({
  word: '',
  category: 'default',
})

const groupedKeywords = computed(() => {
  const groups = new Map<string, Keyword[]>()
  for (const keyword of keywords.value.filter((item) => item.enabled)) {
    const category = keyword.category || '未分类'
    if (!groups.has(category)) groups.set(category, [])
    groups.get(category)!.push(keyword)
  }
  return Array.from(groups.entries()).map(([category, items]) => ({
    category,
    keywords: items,
  }))
})

function ruleTypeLabel(type: EmailRuleType): string {
  if (type === 'AND') return '同时包含全部关键词'
  if (type === 'NOT') return '包含但排除'
  return '包含任一关键词'
}

function ruleTypeDescription(topic: EmailTopicRule): string {
  const include = topic.keyword_ids.map(keywordName).join('、') || '未选择关键词'
  const exclude = topic.exclude_keyword_ids.map(keywordName).join('、')
  if (topic.rule_type === 'AND') return `论文需要同时包含：${include}`
  if (topic.rule_type === 'NOT') return `论文包含：${include}${exclude ? `；排除：${exclude}` : ''}`
  return `论文包含任意一个：${include}`
}

function keywordName(id: number): string {
  return keywords.value.find((keyword) => keyword.id === id)?.word || `#${id}`
}

function resetForm() {
  editingId.value = null
  form.name = ''
  form.rule_type = 'OR'
  form.keyword_ids = []
  form.exclude_keyword_ids = []
  form.threshold = 6
  form.enabled = true
  form.recipients = ''
}

async function loadData() {
  loading.value = true
  try {
    const [keywordResponse, topicResponse] = await Promise.all([
      keywordApi.list(),
      emailTopicRuleApi.list(),
    ])
    keywords.value = keywordResponse.data
    topics.value = topicResponse.data
  } catch (err: any) {
    appStore.error('加载邮件主题失败: ' + err.message)
  } finally {
    loading.value = false
  }
}

function editTopic(topic: EmailTopicRule) {
  editingId.value = topic.id
  form.name = topic.name
  form.rule_type = topic.rule_type
  form.keyword_ids = [...topic.keyword_ids]
  form.exclude_keyword_ids = [...topic.exclude_keyword_ids]
  form.threshold = topic.threshold
  form.enabled = topic.enabled
  form.recipients = topic.recipients || ''
}

async function addKeyword() {
  addingKeyword.value = true
  try {
    const { data } = await keywordApi.create({
      word: newKeyword.word.trim(),
      category: newKeyword.category.trim() || 'default',
    })
    keywords.value.push(data)
    if (!form.keyword_ids.includes(data.id)) form.keyword_ids.push(data.id)
    newKeyword.word = ''
    appStore.success('关键词已添加到当前主题')
  } catch (err: any) {
    appStore.error('添加关键词失败: ' + err.message)
  } finally {
    addingKeyword.value = false
  }
}

async function saveTopic() {
  if (form.keyword_ids.length === 0) {
    appStore.warning('请至少选择一个包含关键词')
    return
  }

  saving.value = true
  try {
    const payload = {
      name: form.name.trim(),
      rule_type: form.rule_type,
      keyword_ids: form.keyword_ids.map(Number),
      exclude_keyword_ids: form.rule_type === 'NOT' ? form.exclude_keyword_ids.map(Number) : [],
      threshold: Number(form.threshold),
      enabled: form.enabled,
      recipients: form.recipients.trim() || null,
    }
    if (editingId.value) {
      await emailTopicRuleApi.update(editingId.value, payload)
      appStore.success('邮件主题已更新')
    } else {
      await emailTopicRuleApi.create(payload)
      appStore.success('邮件主题已创建')
    }
    resetForm()
    await loadData()
  } catch (err: any) {
    appStore.error('保存邮件主题失败: ' + err.message)
  } finally {
    saving.value = false
  }
}

async function toggleTopic(topic: EmailTopicRule) {
  try {
    await emailTopicRuleApi.update(topic.id, { enabled: !topic.enabled })
    topic.enabled = !topic.enabled
    appStore.success(topic.enabled ? '主题邮件已启动' : '主题邮件已暂停')
  } catch (err: any) {
    appStore.error('更新邮件主题失败: ' + err.message)
  }
}

async function deleteTopic(topic: EmailTopicRule) {
  if (!confirm(`确定要删除邮件主题 "${topic.name}" 吗？`)) return
  try {
    await emailTopicRuleApi.delete(topic.id)
    appStore.success('邮件主题已删除')
    await loadData()
  } catch (err: any) {
    appStore.error('删除邮件主题失败: ' + err.message)
  }
}

onMounted(loadData)
</script>
