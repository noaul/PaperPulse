<template>
  <div class="paper-login-scene min-h-screen flex items-center justify-center px-4">
    <div class="w-full max-w-md">
      <!-- Logo -->
      <div class="text-center mb-8">
        <div class="paper-logo-mark w-14 h-14 rounded-xl flex items-center justify-center mx-auto mb-4">
          <svg class="w-8 h-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
          </svg>
        </div>
        <h1 class="text-3xl font-semibold text-gray-900">PaperPulse</h1>
        <p class="text-sm text-gray-500 mt-2">{{ isRegister ? '创建管理员账户' : '登录到文献工作台' }}</p>
      </div>

      <!-- Form -->
      <div class="paper-login-panel rounded-xl p-7">
        <form @submit.prevent="handleSubmit">
          <!-- Username -->
          <div class="mb-4">
            <label class="block text-sm font-medium text-gray-700 mb-1.5">用户名</label>
            <input
              v-model="form.username"
              type="text"
              required
              placeholder="请输入用户名"
              class="w-full px-3 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none text-sm transition-colors"
            />
          </div>

          <!-- Password -->
          <div class="mb-5">
            <label class="block text-sm font-medium text-gray-700 mb-1.5">密码</label>
            <input
              v-model="form.password"
              type="password"
              required
              placeholder="请输入密码"
              class="w-full px-3 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none text-sm transition-colors"
            />
          </div>

          <!-- Error -->
          <div v-if="errorMsg" class="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
            <p class="text-sm text-red-600">{{ errorMsg }}</p>
          </div>

          <!-- Submit -->
          <button
            type="submit"
            :disabled="submitting"
            class="w-full py-2.5 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {{ submitting ? '处理中...' : (isRegister ? '注册' : '登录') }}
          </button>

          <!-- Toggle -->
          <p class="text-center text-sm text-gray-500 mt-4">
            <template v-if="isRegister">
              已有账户？
              <button type="button" @click="isRegister = false; errorMsg = ''" class="text-blue-600 hover:text-blue-800 font-medium">
                去登录
              </button>
            </template>
            <template v-else>
              首次使用？
              <button type="button" @click="isRegister = true; errorMsg = ''" class="text-blue-600 hover:text-blue-800 font-medium">
                注册账户
              </button>
            </template>
          </p>
        </form>
      </div>
    </div>
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
