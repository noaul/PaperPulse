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
          <button
            type="submit"
            form="topic-form"
            :disabled="saving"
            class="rounded-lg bg-green-600 px-4 py-1.5 text-sm font-semibold text-white hover:bg-green-700 disabled:opacity-50"
          >
            {{ editingId ? '保存主题' : '创建主题' }}
          </button>
        </div>
      </div>

      <form id="topic-form" class="mt-5 space-y-5" @submit.prevent="saveTopic">
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
              <p class="mt-0.5 text-xs text-gray-500">第一行输入主题关键词，后续规则选择 AND / OR / NOT 继续组合。</p>
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

              <div
                v-if="index === 0"
                class="flex h-[42px] items-center rounded-lg border border-gray-200 bg-gray-50 px-3 text-sm font-semibold text-gray-500"
              >
                主题关键词
              </div>
              <label v-else class="block">
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
                <input
                  v-model="row.keywordText"
                  list="topic-keyword-options"
                  class="w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm outline-none"
                  placeholder="输入关键词，或选择已有关键词"
                />
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

          <datalist id="topic-keyword-options">
            <option v-for="keyword in keywords" :key="keyword.id" :value="keyword.word" :label="keyword.category" />
          </datalist>
        </div>
      </form>
    </section>

    <section class="rounded-xl border border-gray-200 bg-white p-5">
      <div class="mb-4 flex flex-col gap-2 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h2 class="text-lg font-semibold text-gray-900">关键词管理</h2>
          <p class="mt-1 text-sm text-gray-500">维护当前工作区可用于邮件主题的关键词，删除后会从相关主题规则中移除。</p>
        </div>
        <span class="text-sm font-medium text-gray-500">{{ keywords.length }} 个关键词</span>
      </div>

      <div v-if="keywords.length === 0" class="rounded-lg border border-dashed border-gray-200 bg-gray-50 p-6 text-center text-sm text-gray-500">
        还没有关键词，可以在上方规则里直接输入并创建主题。
      </div>

      <div v-else class="grid gap-4 xl:grid-cols-2">
        <div
          v-for="group in keywordManagementGroups"
          :key="group.category"
          class="rounded-lg border border-gray-200 bg-gray-50 p-4"
        >
          <div class="mb-3 flex items-center justify-between">
            <h3 class="text-sm font-semibold text-gray-800">{{ group.category }}</h3>
            <span class="rounded-md bg-white px-2 py-1 text-xs font-semibold text-gray-500">{{ group.keywords.length }} 个</span>
          </div>

          <div class="grid gap-2">
            <div
              v-for="keyword in group.keywords"
              :key="keyword.id"
              class="grid grid-cols-[minmax(0,1fr)_5.5rem_auto] items-center gap-2 rounded-lg border border-gray-200 bg-white px-3 py-2"
            >
              <span class="min-w-0 truncate text-sm font-medium text-gray-800">{{ keyword.word }}</span>
              <span class="text-right text-xs text-gray-500">使用 {{ keywordUsageCount(keyword.id) }}</span>
              <button
                type="button"
                class="rounded-md border border-red-100 px-2.5 py-1.5 text-xs font-semibold text-red-600 hover:bg-red-50 disabled:opacity-50"
                :disabled="deletingKeywordId === keyword.id"
                @click="deleteKeyword(keyword)"
              >
                删除
              </button>
            </div>
          </div>
        </div>
      </div>
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
                {{ index === 0 ? '主题关键词' : operatorLabel(rule.operator) }}
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
  keywordText: string
}

type SelectedTopicRuleRow = TopicRuleRow & {
  index: number
  keywordText: string
}

type ResolvedTopicRuleRow = SelectedTopicRuleRow & {
  keywordId: number
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
const deletingKeywordId = ref<number | null>(null)
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

function createRuleRow(operator: RuleOperator = 'OR', keywordText = ''): TopicRuleRow {
  return {
    id: nextRuleRowId++,
    operator,
    keywordText,
  }
}

const keywordManagementGroups = computed(() => {
  const groups = new Map<string, Keyword[]>()
  for (const keyword of keywords.value) {
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
  const includeRows = rows.filter((row) => effectiveOperator(row) !== 'NOT')
  const excludeRows = rows.filter((row) => effectiveOperator(row) === 'NOT')
  const includeWords = includeRows.map((row) => row.keywordText).join('、')
  const excludeWords = excludeRows.map((row) => row.keywordText).join('、')

  if (includeRows.length === 0) return '至少添加一个 OR 或 AND 规则作为主题关键词。'
  if (excludeRows.length > 0) {
    return `当前主题会匹配：${includeWords || '未选择'}；并排除：${excludeWords || '未选择'}。`
  }
  if (shouldUseAndRule(rows)) {
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

function keywordUsageCount(id: number): number {
  return topics.value.filter((topic) => topic.keyword_ids.includes(id) || topic.exclude_keyword_ids.includes(id)).length
}

function normalizeKeywordWord(word: string): string {
  return word.trim().toLowerCase()
}

function effectiveOperator(row: Pick<TopicRuleRow, 'operator'> & { index: number }): RuleOperator {
  return row.index === 0 ? 'OR' : row.operator
}

function selectedRuleRows(): SelectedTopicRuleRow[] {
  return ruleRows.value
    .map((row, index) => ({
      ...row,
      index,
      keywordText: row.keywordText.trim(),
    }))
    .filter((row) => row.keywordText.length > 0)
}

function shouldUseAndRule(rows: SelectedTopicRuleRow[]): boolean {
  const includeRows = rows.filter((row) => effectiveOperator(row) !== 'NOT')
  return includeRows.length > 1 && includeRows.slice(1).every((row) => effectiveOperator(row) === 'AND')
}

function addRuleRow() {
  ruleRows.value.push(createRuleRow('AND'))
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
  const includeRows = topic.keyword_ids.map((id) => createRuleRow(includeOperator, keywordName(id)))
  const excludeRows = topic.exclude_keyword_ids.map((id) => createRuleRow('NOT', keywordName(id)))
  ruleRows.value = [...includeRows, ...excludeRows]
  if (ruleRows.value.length === 0) ruleRows.value = [createRuleRow()]
}

async function deleteKeyword(keyword: Keyword) {
  const usageCount = keywordUsageCount(keyword.id)
  const message =
    usageCount > 0
      ? `确定删除关键词 "${keyword.word}" 吗？它会同时从 ${usageCount} 个邮件主题规则中移除。`
      : `确定删除关键词 "${keyword.word}" 吗？`
  if (!confirm(message)) return

  deletingKeywordId.value = keyword.id
  try {
    const affectedTopics = topics.value.filter(
      (topic) => topic.keyword_ids.includes(keyword.id) || topic.exclude_keyword_ids.includes(keyword.id)
    )

    for (const topic of affectedTopics) {
      const keywordIds = topic.keyword_ids.filter((id) => id !== keyword.id)
      const excludeKeywordIds = topic.exclude_keyword_ids.filter((id) => id !== keyword.id)
      await emailTopicRuleApi.update(topic.id, {
        keyword_ids: keywordIds,
        exclude_keyword_ids: excludeKeywordIds,
        enabled: keywordIds.length > 0 ? topic.enabled : false,
      })
    }

    await keywordApi.delete(keyword.id)
    ruleRows.value = ruleRows.value.map((row) =>
      normalizeKeywordWord(row.keywordText) === normalizeKeywordWord(keyword.word) ? { ...row, keywordText: '' } : row
    )
    appStore.success('关键词已删除')
    await loadData()
  } catch (err: any) {
    appStore.error('删除关键词失败: ' + err.message)
  } finally {
    deletingKeywordId.value = null
  }
}

async function resolveKeywordId(word: string): Promise<number> {
  const normalized = normalizeKeywordWord(word)
  const existing = keywords.value.find((keyword) => normalizeKeywordWord(keyword.word) === normalized)
  if (existing) return existing.id

  const { data } = await keywordApi.create({
    word: word.trim(),
    category: 'default',
  })
  keywords.value.push(data)
  return data.id
}

async function resolveRuleRows(rows: SelectedTopicRuleRow[]): Promise<ResolvedTopicRuleRow[]> {
  const resolved: ResolvedTopicRuleRow[] = []
  for (const row of rows) {
    const keywordId = await resolveKeywordId(row.keywordText)
    resolved.push({ ...row, keywordId })
  }
  return resolved
}

async function saveTopic() {
  const rows = selectedRuleRows()
  const includeRows = rows.filter((row) => effectiveOperator(row) !== 'NOT')
  if (includeRows.length === 0) {
    appStore.warning('请至少添加一个 OR 或 AND 关键词规则')
    return
  }

  saving.value = true
  try {
    const resolvedRows = await resolveRuleRows(rows)
    const resolvedIncludeRows = resolvedRows.filter((row) => effectiveOperator(row) !== 'NOT')
    const resolvedExcludeRows = resolvedRows.filter((row) => effectiveOperator(row) === 'NOT')
    const keywordIds = Array.from(new Set(resolvedIncludeRows.map((row) => Number(row.keywordId))))
    const excludeKeywordIds = Array.from(new Set(resolvedExcludeRows.map((row) => Number(row.keywordId))))
    const ruleType: EmailRuleType =
      excludeKeywordIds.length > 0
        ? 'NOT'
        : shouldUseAndRule(resolvedRows)
          ? 'AND'
          : 'OR'
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
