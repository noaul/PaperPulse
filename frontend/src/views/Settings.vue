<template>
  <div class="space-y-6">
    <!-- Tab Navigation -->
    <div class="bg-white rounded-xl shadow-sm border border-gray-200">
      <div class="border-b border-gray-200">
        <nav class="flex -mb-px px-6">
          <button
            v-for="tab in tabs"
            :key="tab.id"
            @click="activeTab = tab.id"
            :class="[
              'py-4 px-6 text-sm font-medium border-b-2 transition-colors',
              activeTab === tab.id
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300',
            ]"
          >
            {{ tab.label }}
          </button>
        </nav>
      </div>

      <div class="p-6">
        <!-- AI Config Tab -->
        <div v-if="activeTab === 'ai'" class="space-y-4">
          <h3 class="text-base font-semibold text-gray-800">AI 配置</h3>
          <p class="text-sm text-gray-500">配置 AI 模型用于论文分析和相关性评估</p>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">API 地址</label>
              <input
                v-model="aiForm.api_base"
                type="text"
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none text-sm"
                placeholder="https://api.openai.com/v1"
              />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">API Key</label>
              <div class="relative">
                <input
                  v-model="aiForm.api_key"
                  :type="showApiKey ? 'text' : 'password'"
                  class="w-full px-3 py-2 pr-10 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none text-sm"
                  placeholder="sk-..."
                />
                <button
                  type="button"
                  @click="showApiKey = !showApiKey"
                  class="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                >
                  <svg v-if="!showApiKey" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                  </svg>
                  <svg v-else class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
                  </svg>
                </button>
              </div>
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">模型</label>
              <input
                v-model="aiForm.model"
                type="text"
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none text-sm"
                placeholder="gpt-4o-mini"
              />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">推理强度</label>
              <select
                v-model="aiForm.reasoning_effort"
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none text-sm"
              >
                <option value="xhigh">xhigh - 最深推理</option>
                <option value="high">high - 深度推理</option>
                <option value="medium">medium - 均衡模式</option>
                <option value="low">low - 快速响应</option>
                <option value="none">none - 不推理</option>
              </select>
            </div>
            <div class="flex items-center space-x-3 pt-6">
              <button
                @click="aiForm.enabled = !aiForm.enabled"
                :class="[
                  'relative inline-flex h-5 w-9 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none',
                  aiForm.enabled ? 'bg-blue-600' : 'bg-gray-300',
                ]"
              >
                <span
                  :class="[
                    'pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out',
                    aiForm.enabled ? 'translate-x-4' : 'translate-x-0',
                  ]"
                ></span>
              </button>
              <span class="text-sm text-gray-700">{{ aiForm.enabled ? '已启用' : '已禁用' }}</span>
            </div>
          </div>

          <div class="flex items-center space-x-3 pt-4">
            <button
              @click="saveAI"
              :disabled="savingAI"
              class="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
            >
              {{ savingAI ? '保存中...' : '保存配置' }}
            </button>
            <button
              @click="testAI"
              :disabled="testingAI"
              class="px-4 py-2 bg-gray-100 text-gray-700 text-sm font-medium rounded-lg hover:bg-gray-200 disabled:opacity-50 transition-colors"
            >
              {{ testingAI ? '测试中...' : '测试连接' }}
            </button>
          </div>
        </div>

        <!-- Email Config Tab -->
        <div v-if="activeTab === 'email'" class="space-y-4">
          <h3 class="text-base font-semibold text-gray-800">邮件配置</h3>
          <p class="text-sm text-gray-500">配置 SMTP 邮件服务，用于发送论文报告</p>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">SMTP 服务器</label>
              <input
                v-model="emailForm.smtp_server"
                type="text"
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none text-sm"
                placeholder="smtp.gmail.com"
              />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">端口</label>
              <input
                v-model.number="emailForm.smtp_port"
                type="number"
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none text-sm"
                placeholder="587"
              />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">用户名</label>
              <input
                v-model="emailForm.smtp_user"
                type="text"
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none text-sm"
                placeholder="your@email.com"
              />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">密码</label>
              <input
                v-model="emailForm.smtp_password"
                type="password"
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none text-sm"
                placeholder="******"
              />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">发件人名称</label>
              <input
                v-model="emailForm.sender_name"
                type="text"
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none text-sm"
                placeholder="PaperPulse"
              />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">收件人</label>
              <input
                v-model="emailForm.recipient"
                type="email"
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none text-sm"
                placeholder="recipient@email.com"
              />
            </div>
            <div class="flex items-center space-x-3 pt-2">
              <button
                @click="emailForm.enabled = !emailForm.enabled"
                :class="[
                  'relative inline-flex h-5 w-9 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none',
                  emailForm.enabled ? 'bg-blue-600' : 'bg-gray-300',
                ]"
              >
                <span
                  :class="[
                    'pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out',
                    emailForm.enabled ? 'translate-x-4' : 'translate-x-0',
                  ]"
                ></span>
              </button>
              <span class="text-sm text-gray-700">{{ emailForm.enabled ? '已启用' : '已禁用' }}</span>
            </div>
          </div>

          <div class="flex items-center space-x-3 pt-4">
            <button
              @click="saveEmail"
              :disabled="savingEmail"
              class="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
            >
              {{ savingEmail ? '保存中...' : '保存配置' }}
            </button>
            <button
              @click="testEmail"
              :disabled="testingEmail"
              class="px-4 py-2 bg-gray-100 text-gray-700 text-sm font-medium rounded-lg hover:bg-gray-200 disabled:opacity-50 transition-colors"
            >
              {{ testingEmail ? '测试中...' : '发送测试邮件' }}
            </button>
          </div>
        </div>

        <!-- WebDAV Config Tab -->
        <div v-if="activeTab === 'webdav'" class="space-y-4">
          <h3 class="text-base font-semibold text-gray-800">WebDAV 配置</h3>
          <p class="text-sm text-gray-500">配置 WebDAV 用于数据备份和同步</p>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div class="md:col-span-2">
              <label class="block text-sm font-medium text-gray-700 mb-1">WebDAV URL</label>
              <input
                v-model="webdavForm.url"
                type="text"
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none text-sm"
                placeholder="https://dav.example.com/dav/"
              />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">用户名</label>
              <input
                v-model="webdavForm.username"
                type="text"
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none text-sm"
                placeholder="username"
              />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">密码</label>
              <input
                v-model="webdavForm.password"
                type="password"
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none text-sm"
                placeholder="******"
              />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">远程路径</label>
              <input
                v-model="webdavForm.remote_path"
                type="text"
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none text-sm"
                placeholder="/paperpulse/"
              />
            </div>
          </div>

          <div class="flex items-center space-x-3 pt-4">
            <button
              @click="saveWebDAV"
              :disabled="savingWebDAV"
              class="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
            >
              {{ savingWebDAV ? '保存中...' : '保存配置' }}
            </button>
            <button
              @click="testWebDAV"
              :disabled="testingWebDAV"
              class="px-4 py-2 bg-gray-100 text-gray-700 text-sm font-medium rounded-lg hover:bg-gray-200 disabled:opacity-50 transition-colors"
            >
              {{ testingWebDAV ? '测试中...' : '测试连接' }}
            </button>
          </div>
        </div>

        <!-- Schedule Config Tab -->
        <div v-if="activeTab === 'schedule'" class="space-y-4">
          <h3 class="text-base font-semibold text-gray-800">定时任务配置</h3>
          <p class="text-sm text-gray-500">配置自动抓取和分析的定时任务</p>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">执行小时 (0-23)</label>
              <input
                v-model.number="scheduleForm.cron_hour"
                type="number"
                min="0"
                max="23"
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none text-sm"
                placeholder="8"
              />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">执行分钟 (0-59)</label>
              <input
                v-model.number="scheduleForm.cron_minute"
                type="number"
                min="0"
                max="59"
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none text-sm"
                placeholder="0"
              />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">相关性阈值</label>
              <input
                v-model.number="scheduleForm.relevance_threshold"
                type="number"
                min="0"
                max="10"
                step="0.5"
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none text-sm"
                placeholder="5.0"
              />
              <p class="text-xs text-gray-500 mt-1">低于此分数的论文将不被包含在报告中</p>
            </div>
          </div>

          <div class="flex items-center space-x-3 pt-4">
            <button
              @click="saveSchedule"
              :disabled="savingSchedule"
              class="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
            >
              {{ savingSchedule ? '保存中...' : '保存配置' }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { settingsApi } from '@/api'
import { useAppStore } from '@/stores/app'

const appStore = useAppStore()

const activeTab = ref('ai')
const showApiKey = ref(false)

const tabs = [
  { id: 'ai', label: 'AI 配置' },
  { id: 'email', label: '邮件配置' },
  { id: 'webdav', label: 'WebDAV 配置' },
  { id: 'schedule', label: '定时任务' },
]

// AI
const aiForm = reactive({
  api_base: '',
  api_key: '',
  model: '',
  reasoning_effort: 'xhigh',
  enabled: false,
})
const savingAI = ref(false)
const testingAI = ref(false)

// Email
const emailForm = reactive({
  smtp_server: '',
  smtp_port: 587,
  smtp_user: '',
  smtp_password: '',
  sender_name: '',
  recipient: '',
  enabled: false,
})
const savingEmail = ref(false)
const testingEmail = ref(false)

// WebDAV
const webdavForm = reactive({
  url: '',
  username: '',
  password: '',
  remote_path: '',
})
const savingWebDAV = ref(false)
const testingWebDAV = ref(false)

// Schedule
const scheduleForm = reactive({
  cron_hour: 8,
  cron_minute: 0,
  relevance_threshold: 5.0,
})
const savingSchedule = ref(false)

// Load functions
async function loadAI() {
  try {
    const { data } = await settingsApi.getAI()
    Object.assign(aiForm, data)
  } catch {
    // use defaults
  }
}

async function loadEmail() {
  try {
    const { data } = await settingsApi.getEmail()
    Object.assign(emailForm, data)
  } catch {
    // use defaults
  }
}

async function loadWebDAV() {
  try {
    const { data } = await settingsApi.getWebDAV()
    Object.assign(webdavForm, data)
  } catch {
    // use defaults
  }
}

async function loadSchedule() {
  try {
    const { data } = await settingsApi.getSchedule()
    Object.assign(scheduleForm, data)
  } catch {
    // use defaults
  }
}

// Save functions
async function saveAI() {
  savingAI.value = true
  try {
    await settingsApi.saveAI({ ...aiForm })
    appStore.success('AI 配置已保存')
  } catch (err: any) {
    appStore.error('保存失败: ' + err.message)
  } finally {
    savingAI.value = false
  }
}

async function saveEmail() {
  savingEmail.value = true
  try {
    await settingsApi.saveEmail({ ...emailForm })
    appStore.success('邮件配置已保存')
  } catch (err: any) {
    appStore.error('保存失败: ' + err.message)
  } finally {
    savingEmail.value = false
  }
}

async function saveWebDAV() {
  savingWebDAV.value = true
  try {
    await settingsApi.saveWebDAV({ ...webdavForm })
    appStore.success('WebDAV 配置已保存')
  } catch (err: any) {
    appStore.error('保存失败: ' + err.message)
  } finally {
    savingWebDAV.value = false
  }
}

async function saveSchedule() {
  savingSchedule.value = true
  try {
    await settingsApi.saveSchedule({ ...scheduleForm })
    appStore.success('定时任务配置已保存')
  } catch (err: any) {
    appStore.error('保存失败: ' + err.message)
  } finally {
    savingSchedule.value = false
  }
}

// Test functions
async function testAI() {
  testingAI.value = true
  try {
    await settingsApi.testAI({ ...aiForm })
    appStore.success('AI 连接测试成功')
  } catch (err: any) {
    appStore.error('连接测试失败: ' + err.message)
  } finally {
    testingAI.value = false
  }
}

async function testEmail() {
  testingEmail.value = true
  try {
    await settingsApi.testEmail({ ...emailForm })
    appStore.success('测试邮件已发送')
  } catch (err: any) {
    appStore.error('发送测试邮件失败: ' + err.message)
  } finally {
    testingEmail.value = false
  }
}

async function testWebDAV() {
  testingWebDAV.value = true
  try {
    await settingsApi.testWebDAV({ ...webdavForm })
    appStore.success('WebDAV 连接测试成功')
  } catch (err: any) {
    appStore.error('连接测试失败: ' + err.message)
  } finally {
    testingWebDAV.value = false
  }
}

onMounted(() => {
  loadAI()
  loadEmail()
  loadWebDAV()
  loadSchedule()
})
</script>
