<template>
  <div class="topic-page space-y-5">
    <section class="topic-composer rounded-xl border border-gray-200 bg-white p-5">
      <div class="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h1 class="text-xl font-semibold text-gray-900">{{ editingId ? '编辑邮件主题' : '创建邮件主题' }}</h1>
          <p class="mt-1 text-sm text-gray-500">按规则行组合关键词，系统会按主题分别筛选论文并发送邮件。</p>
        </div>
        <div class="flex flex-wrap gap-2">
          <button
            v-if="editingId"
            type="button"
            class="rounded-lg border px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-50"
            @click="resetForm"
          >
            取消编辑
          </button>
          <button
            type="button"
            class="rounded-lg border border-blue-200 bg-blue-50 px-3 py-1.5 text-sm font-semibold text-blue-700 hover:bg-blue-100"
            @click="resetForm"
          >
            新主题
          </button>
        </div>
      </div>

      <form class="mt-5 space-y-5" @submit.prevent="saveTopic">
        <div class="grid gap-4 xl:grid-cols-[minmax(220px,1fr)_140px_180px_minmax(260px,1fr)] xl:items-end">
          <label class="block">
            <span class="mb-1 block text-sm font-medium text-gray-700">主题名称</span>
            <input
              v-model="form.name"
              required
              class="w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm outline-none"
              placeholder="例如：疲劳与蠕变"
            />
          </label>

          <label class="block">
            <span class="mb-1 block text-sm font-medium text-gray-700">最低评分</span>
            <input
              v-model.number="form.threshold"
              type="number"
              min="0"
              max="10"
              step="0.5"
              class="w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm outline-none"
            />
          </label>

          <label class="topic-switch h-[42px] rounded-lg border border-gray-200 px-3">
            <span>
              <span class="block text-sm font-medium text-gray-700">邮件发送</span>
              <span class="block text-xs text-gray-500">{{ form.enabled ? '启用' : '暂停' }}</span>
            </span>
            <input v-model="form.enabled" type="checkbox" class="sr-only" />
            <span :class="['switch-track', form.enabled ? 'switch-track-on' : '']">
              <span :class="['switch-thumb', form.enabled ? 'switch-thumb-on' : '']"></span>
            </span>
          </label>

          <label class="block">
            <span class="mb-1 block text-sm font-medium text-gray-700">自定义收件人</span>
            <input
              v-model="form.recipients"
              class="w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm outline-none"
              placeholder="留空使用全局邮件配置"
            />
          </label>
        </div>

        <div class="rounded-lg border border-gray-200 bg-gray-50 p-4">
          <div class="mb-3 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h2 class="text-sm font-semibold text-gray-900">主题规则</h2>
              <p class="mt-0.5 text-xs text-gray-500">每一行选择一个关系和一个关键词，可继续添加规则 2、3、4。</p>
            </div>
            <button
              type="button"
              class="rounded-lg bg-blue-600 px-3 py-2 text-sm font-semibold text-white hover:bg-blue-700"
              @click="addRuleRow"
            >
              添加规则
            </button>
          </div>

          <div class="space-y-3">
            <div
              v-for="(row, index) in ruleRows"
              :key="row.id"
              class="grid gap-3 rounded-lg border border-gray-200 bg-white p-3 xl:grid-cols-[5rem_13rem_minmax(240px,1fr)_2.75rem] xl:items-end"
            >
              <div class="flex h-[42px] items-center rounded-lg bg-gray-100 px-3 text-sm font-semibold text-gray-600">
                规则 {{ index + 1 }}
              </div>

              <label class="block">
                <span class="mb-1 block text-xs font-medium text-gray-500">关系</span>
                <select
                  v-model="row.operator"
                  class="w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm outline-none"
                >
                  <option v-for="option in ruleOperatorOptions" :key="option.value" :value="option.value">
                    {{ option.label }}
                  </option>
                </select>
              </label>

              <label class="block">
                <span class="mb-1 block text-xs font-medium text-gray-500">关键词</span>
                <select
                  v-model="row.keywordId"
                  class="w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm outline-none"
                >
                  <option :value="null" disabled>选择关键词</option>
                  <optgroup v-for="group in groupedKeywords" :key="group.category" :label="group.category">
                    <option v-for="keyword in group.keywords" :key="keyword.id" :value="keyword.id">
                      {{ keyword.word }}
                    </option>
                  </optgroup>
                </select>
              </label>

              <button
                type="button"
                class="h-[42px] rounded-lg border border-gray-300 text-sm font-semibold text-gray-500 hover:bg-red-50 hover:text-red-600"
                title="删除规则"
                @click="removeRuleRow(row.id)"
              >
                删除
              </button>
            </div>
          </div>

          <div class="mt-3 rounded-lg border border-blue-100 bg-blue-50 px-3 py-2 text-sm text-blue-800">
            {{ rulePreview }}
          </div>
        </div>

        <div class="grid gap-3 rounded-lg border border-gray-200 bg-white p-4 xl:grid-cols-[minmax(180px,1fr)_160px_auto_auto] xl:items-end">
          <label class="block">
            <span class="mb-1 block text-sm font-medium text-gray-700">快速新增关键词</span>
            <input
              v-model="newKeyword.word"
              class="w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm outline-none"
              placeholder="关键词"
            />
          </label>
          <label class="block">
            <span class="mb-1 block text-sm font-medium text-gray-700">分类</span>
            <input
              v-model="newKeyword.category"
              class="w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm outline-none"
              placeholder="分类"
            />
          </label>
          <button
            type="button"
            class="rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-50"
            :disabled="addingKeyword || !newKeyword.word.trim()"
            @click="addKeyword"
          >
            添加关键词
          </button>
          <button
            type="submit"
            :disabled="saving"
            class="rounded-lg bg-green-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-green-700 disabled:opacity-50"
          >
            {{ editingId ? '保存主题' : '创建主题' }}
          </button>
        </div>
      </form>
    </section>

    <section class="space-y-4">
      <div class="flex items-center justify-between">
        <h2 class="text-lg font-semibold text-gray-900">已创建主题</h2>
        <span class="text-sm text-gray-500">{{ topics.length }} 个主题</span>
      </div>

      <div v-if="loading" class="rounded-xl border border-gray-200 bg-white p-10 text-center">
        <div class="mx-auto h-9 w-9 animate-spin rounded-full border-2 border-blue-100 border-b-blue-600"></div>
      </div>

      <div v-else-if="topics.length === 0" class="rounded-xl border border-gray-200 bg-white p-10 text-center">
        <p class="text-base font-medium text-gray-700">还没有邮件主题</p>
        <p class="mt-2 text-sm text-gray-500">先在上方创建一个主题，例如“疲劳与蠕变”或“显微组织排除模拟”。</p>
      </div>

      <div v-else class="grid gap-4 xl:grid-cols-2">
        <article
          v-for="topic in topics"
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

          <div class="mt-5 space-y-2">
            <div
              v-for="(rule, index) in topicDisplayRules(topic)"
              :key="`${topic.id}-${rule.operator}-${rule.keyword}`"
              class="grid grid-cols-[4.5rem_8rem_minmax(0,1fr)] items-center gap-2 rounded-lg border border-gray-100 bg-gray-50 px-3 py-2 text-sm"
            >
              <span class="font-semibold text-gray-500">规则 {{ index + 1 }}</span>
              <span :class="['rounded-md px-2 py-1 text-center text-xs font-semibold', operatorPillClass(rule.operator)]">
                {{ operatorLabel(rule.operator) }}
              </span>
              <span class="min-w-0 truncate font-medium text-gray-800">{{ rule.keyword }}</span>
            </div>

            <p class="pt-2 text-xs text-gray-500">
              收件人：{{ topic.recipients || '使用全局邮件配置' }}
            </p>
          </div>
        </article>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { emailTopicRuleApi, keywordApi } from '@/api'
import type { EmailRuleType, EmailTopicRule, Keyword } from '@/api'
import { useAppStore } from '@/stores/app'

type KeywordGroup = {
  category: string
  keywords: Keyword[]
}

type RuleOperator = EmailRuleType

type TopicRuleRow = {
  id: number
  operator: RuleOperator
  keywordId: number | null
}

type TopicDisplayRule = {
  operator: RuleOperator
  keyword: string
}

const appStore = useAppStore()
const keywords = ref<Keyword[]>([])
const topics = ref<EmailTopicRule[]>([])
const loading = ref(true)
const saving = ref(false)
const addingKeyword = ref(false)
const editingId = ref<number | null>(null)

let nextRuleRowId = 1
const ruleRows = ref<TopicRuleRow[]>([createRuleRow()])

const ruleOperatorOptions: Array<{ value: RuleOperator; label: string }> = [
  { value: 'OR', label: 'OR 其中一个命中' },
  { value: 'AND', label: 'AND 必须同时命中' },
  { value: 'NOT', label: 'NOT 排除该关键词' },
]

const form = reactive({
  name: '',
  threshold: 6,
  enabled: true,
  recipients: '',
})

const newKeyword = reactive({
  word: '',
  category: 'default',
})

function createRuleRow(operator: RuleOperator = 'OR', keywordId: number | null = null): TopicRuleRow {
  return {
    id: nextRuleRowId++,
    operator,
    keywordId,
  }
}

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

const rulePreview = computed(() => {
  const rows = selectedRuleRows()
  const includeRows = rows.filter((row) => row.operator !== 'NOT')
  const excludeRows = rows.filter((row) => row.operator === 'NOT')
  const includeWords = includeRows.map((row) => keywordName(row.keywordId)).join('、')
  const excludeWords = excludeRows.map((row) => keywordName(row.keywordId)).join('、')

  if (includeRows.length === 0) return '至少添加一个 OR 或 AND 规则作为主题关键词。'
  if (excludeRows.length > 0) {
    return `当前主题会匹配：${includeWords || '未选择'}；并排除：${excludeWords || '未选择'}。`
  }
  if (includeRows.length > 1 && includeRows.every((row) => row.operator === 'AND')) {
    return `当前主题要求论文同时命中：${includeWords}。`
  }
  return `当前主题会匹配任一关键词：${includeWords}。`
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

function operatorLabel(type: RuleOperator): string {
  if (type === 'AND') return 'AND'
  if (type === 'NOT') return 'NOT'
  return 'OR'
}

function operatorPillClass(type: RuleOperator): string {
  if (type === 'AND') return 'bg-green-100 text-green-700'
  if (type === 'NOT') return 'bg-red-100 text-red-700'
  return 'bg-blue-100 text-blue-700'
}

function keywordName(id: number): string {
  return keywords.value.find((keyword) => keyword.id === id)?.word || `#${id}`
}

function selectedRuleRows(): Array<TopicRuleRow & { keywordId: number }> {
  return ruleRows.value.filter((row): row is TopicRuleRow & { keywordId: number } => typeof row.keywordId === 'number')
}

function addRuleRow() {
  const defaultOperator = ruleRows.value.length === 0 ? 'OR' : 'AND'
  ruleRows.value.push(createRuleRow(defaultOperator))
}

function removeRuleRow(id: number) {
  ruleRows.value = ruleRows.value.filter((row) => row.id !== id)
  if (ruleRows.value.length === 0) ruleRows.value = [createRuleRow()]
}

function resetForm() {
  editingId.value = null
  form.name = ''
  form.threshold = 6
  form.enabled = true
  form.recipients = ''
  ruleRows.value = [createRuleRow()]
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
  form.threshold = topic.threshold
  form.enabled = topic.enabled
  form.recipients = topic.recipients || ''
  const includeOperator: RuleOperator = topic.rule_type === 'AND' ? 'AND' : 'OR'
  const includeRows = topic.keyword_ids.map((id) => createRuleRow(includeOperator, id))
  const excludeRows = topic.exclude_keyword_ids.map((id) => createRuleRow('NOT', id))
  ruleRows.value = [...includeRows, ...excludeRows]
  if (ruleRows.value.length === 0) ruleRows.value = [createRuleRow()]
}

async function addKeyword() {
  addingKeyword.value = true
  try {
    const { data } = await keywordApi.create({
      word: newKeyword.word.trim(),
      category: newKeyword.category.trim() || 'default',
    })
    keywords.value.push(data)
    const emptyRow = ruleRows.value.find((row) => row.keywordId === null)
    if (emptyRow) emptyRow.keywordId = data.id
    else ruleRows.value.push(createRuleRow('OR', data.id))
    newKeyword.word = ''
    appStore.success('关键词已添加到当前主题')
  } catch (err: any) {
    appStore.error('添加关键词失败: ' + err.message)
  } finally {
    addingKeyword.value = false
  }
}

async function saveTopic() {
  const rows = selectedRuleRows()
  const includeRows = rows.filter((row) => row.operator !== 'NOT')
  const excludeRows = rows.filter((row) => row.operator === 'NOT')
  if (includeRows.length === 0) {
    appStore.warning('请至少添加一个 OR 或 AND 关键词规则')
    return
  }

  const keywordIds = Array.from(new Set(includeRows.map((row) => Number(row.keywordId))))
  const excludeKeywordIds = Array.from(new Set(excludeRows.map((row) => Number(row.keywordId))))
  const ruleType: EmailRuleType =
    excludeKeywordIds.length > 0
      ? 'NOT'
      : includeRows.length > 1 && includeRows.every((row) => row.operator === 'AND')
        ? 'AND'
        : 'OR'

  saving.value = true
  try {
    const payload = {
      name: form.name.trim(),
      rule_type: ruleType,
      keyword_ids: keywordIds,
      exclude_keyword_ids: ruleType === 'NOT' ? excludeKeywordIds : [],
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

function topicDisplayRules(topic: EmailTopicRule): TopicDisplayRule[] {
  const includeOperator: RuleOperator = topic.rule_type === 'AND' ? 'AND' : 'OR'
  return [
    ...topic.keyword_ids.map((id) => ({
      operator: includeOperator,
      keyword: keywordName(id),
    })),
    ...topic.exclude_keyword_ids.map((id) => ({
      operator: 'NOT' as RuleOperator,
      keyword: keywordName(id),
    })),
  ]
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
