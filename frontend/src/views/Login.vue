<template>
  <div class="paper-login-scene grid min-h-[100dvh] text-[var(--xai-ink)] lg:grid-cols-[0.95fr_1.05fr]">
    <section class="paper-login-story hidden border-r border-[var(--xai-hairline)] px-10 py-8 lg:flex lg:flex-col lg:justify-between">
      <div class="flex items-center gap-3">
        <div class="paper-logo-mark flex h-9 w-9 items-center justify-center rounded-xl">
          <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
          </svg>
        </div>
        <div>
          <div class="text-sm font-semibold tracking-tight">PaperPulse</div>
          <div class="font-mono text-[11px] text-[var(--xai-subtle)]">literature operations</div>
        </div>
      </div>

      <div class="max-w-md">
        <div class="paper-login-security mb-5 flex h-11 w-11 items-center justify-center rounded-xl">
          <svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12.75 11.25 15 15 9.75M12 3 4.5 6v5.25c0 4.557 3.183 8.456 7.5 9.75 4.317-1.294 7.5-5.193 7.5-9.75V6L12 3Z" />
          </svg>
        </div>
        <h1 class="text-3xl font-semibold tracking-tight">抓取、分析和报告，放在一个稳定的研究工作台里。</h1>
        <p class="mt-4 text-sm leading-6 text-[var(--xai-mute)]">
          面向单用户部署的文献监控系统，集中处理 RSS、AI 相关性分析、邮件报告、WebDAV 备份和工作区隔离。
        </p>
      </div>

      <div class="font-mono text-xs text-[var(--xai-subtle)]">Dark-first research workspace</div>
    </section>

    <section class="flex min-h-[100dvh] items-center justify-center px-4 py-10">
      <div class="w-full max-w-sm">
        <div class="mb-6">
          <div class="paper-login-lock mb-4 flex h-10 w-10 items-center justify-center rounded-xl">
            <svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16.5 10.5V7.75a4.5 4.5 0 0 0-9 0v2.75m-.75 0h10.5A1.75 1.75 0 0 1 19 12.25v6A1.75 1.75 0 0 1 17.25 20H6.75A1.75 1.75 0 0 1 5 18.25v-6a1.75 1.75 0 0 1 1.75-1.75Z" />
            </svg>
          </div>
          <h1 class="text-2xl font-semibold tracking-tight">{{ isRegister ? '初始化账户' : '登录 PaperPulse' }}</h1>
          <p class="mt-1 text-sm text-[var(--xai-mute)]">{{ isRegister ? '创建唯一管理员，开始管理你的文献工作流。' : '进入你的文献监控与分析工作台。' }}</p>
        </div>

        <div class="paper-login-panel rounded-xl p-7">
        <form @submit.prevent="handleSubmit">
          <div class="mb-4">
            <label class="block text-xs font-medium text-[var(--xai-mute)] mb-1.5">用户名</label>
            <input
              v-model="form.username"
              type="text"
              required
              placeholder="请输入用户名"
              class="w-full px-3.5 py-2.5 text-sm"
            />
          </div>

          <div class="mb-5">
            <label class="block text-xs font-medium text-[var(--xai-mute)] mb-1.5">密码</label>
            <input
              v-model="form.password"
              type="password"
              required
              placeholder="请输入密码"
              class="w-full px-3.5 py-2.5 text-sm"
            />
          </div>

          <div v-if="errorMsg" class="mb-4 rounded-xl border border-[rgba(244,63,94,0.24)] bg-[rgba(244,63,94,0.10)] p-3">
            <p class="text-sm text-[var(--xai-danger)]">{{ errorMsg }}</p>
          </div>

          <button
            type="submit"
            :disabled="submitting"
            class="xai-btn xai-btn-primary w-full"
          >
            {{ submitting ? '处理中...' : (isRegister ? '注册' : '登录') }}
          </button>

          <p class="text-center text-sm text-[var(--xai-mute)] mt-4">
            <template v-if="isRegister">
              已有账户？
              <button type="button" @click="isRegister = false; errorMsg = ''" class="font-medium text-[var(--xai-primary)] hover:text-[var(--xai-primary-strong)]">
                去登录
              </button>
            </template>
            <template v-else>
              首次使用？
              <button type="button" @click="isRegister = true; errorMsg = ''" class="font-medium text-[var(--xai-primary)] hover:text-[var(--xai-primary-strong)]">
                注册账户
              </button>
            </template>
          </p>
        </form>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { authApi } from '@/api'
import { useAppStore } from '@/stores/app'

const router = useRouter()
const appStore = useAppStore()

const isRegister = ref(false)
const submitting = ref(false)
const errorMsg = ref('')

const form = reactive({
  username: '',
  password: '',
})

async function handleSubmit() {
  errorMsg.value = ''
  submitting.value = true
  try {
    const apiFn = isRegister.value ? authApi.register : authApi.login
    const { data } = await apiFn(form.username, form.password)
    appStore.setAuth(data.token, data.username)
    router.push('/dashboard')
  } catch (err: any) {
    errorMsg.value = err.message || '操作失败'
  } finally {
    submitting.value = false
  }
}

onMounted(async () => {
  // Check if admin exists, default to register if not
  try {
    const { data } = await authApi.check()
    isRegister.value = !data.registered
  } catch {
    // If check fails, default to login
    isRegister.value = false
  }
})
</script>
