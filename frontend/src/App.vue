<template>
  <router-view v-if="!appStore.isLoggedIn" />

  <div v-else class="paper-shell flex h-screen flex-col overflow-hidden">
    <header class="paper-topbar flex h-16 flex-shrink-0 items-center gap-4 px-6">
      <div class="flex min-w-0 items-center gap-4">
        <router-link to="/dashboard" class="flex items-center gap-3">
          <div class="paper-logo-mark flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-lg">
            <svg class="h-5 w-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"
              />
            </svg>
          </div>
          <div class="hidden sm:block">
            <div class="text-base font-semibold text-gray-900">PaperPulse</div>
            <div class="text-xs text-gray-500">学术文献工作台</div>
          </div>
        </router-link>

        <div v-if="workspaceStore.currentWorkspace" class="hidden items-center gap-2 md:flex">
          <span
            class="h-2.5 w-2.5 rounded-full"
            :style="{ backgroundColor: workspaceStore.currentWorkspace.color || '#4F46E5' }"
          ></span>
          <select
            :value="workspaceStore.currentWorkspace.id"
            class="max-w-[180px] rounded-lg border px-3 py-1.5 text-sm"
            @change="switchWorkspace"
          >
            <option v-for="workspace in workspaceStore.workspaces" :key="workspace.id" :value="workspace.id">
              {{ workspace.name }}
            </option>
          </select>
          <button
            class="rounded-lg border px-2.5 py-1.5 text-sm text-gray-600 hover:bg-gray-50"
            title="新建工作区"
            @click="createWorkspace"
          >
            +
          </button>
        </div>
      </div>

      <nav class="paper-top-nav flex min-w-0 flex-1 items-center justify-center gap-1 overflow-x-auto">
        <router-link
          v-for="item in navItems"
          :key="item.path"
          :to="item.path"
          :class="['paper-top-nav-link', isActive(item.path) ? 'paper-top-nav-link-active' : '']"
        >
          {{ item.label }}
        </router-link>
      </nav>

      <div class="flex flex-shrink-0 items-center gap-2">
        <div class="hidden text-right md:block">
          <div class="text-xs text-gray-500">{{ currentTitle }}</div>
          <div class="text-xs text-gray-400">{{ appStore.authUsername }}</div>
        </div>
        <button
          class="rounded-lg border px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-50"
          title="退出登录"
          @click="handleLogout"
        >
          退出
        </button>
      </div>
    </header>

    <div class="paper-content flex-1 overflow-y-auto p-5 lg:p-6">
      <router-view :key="pageKey" />
    </div>

    <div class="fixed right-4 top-4 z-50 space-y-2">
      <div
        v-for="toast in appStore.toasts"
        :key="toast.id"
        :class="[
          'toast-enter flex min-w-[280px] max-w-sm items-center rounded-lg px-4 py-3 shadow-lg',
          toastClasses[toast.type],
        ]"
      >
        <div class="flex-1 text-sm font-medium">{{ toast.message }}</div>
        <button class="ml-3 opacity-70 hover:opacity-100" @click="appStore.removeToast(toast.id)">
          <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { workspaceApi } from '@/api'
import { useAppStore } from '@/stores/app'
import { useWorkspaceStore } from '@/stores/workspace'

const appStore = useAppStore()
const workspaceStore = useWorkspaceStore()
const route = useRoute()
const router = useRouter()

const currentTitle = computed(() => (route.meta.title as string) || 'PaperPulse')
const pageKey = computed(() => `${route.fullPath}:${workspaceStore.currentWorkspaceId || 'default'}`)

const navItems = [
  { path: '/dashboard', label: '仪表盘' },
  { path: '/papers', label: '论文' },
  { path: '/analysis', label: '分析结果' },
  { path: '/reports', label: '报告' },
  { path: '/feeds', label: '订阅源' },
  { path: '/email-topics', label: '邮件主题' },
  { path: '/reading-queue', label: '阅读队列' },
  { path: '/settings', label: '设置' },
]

function isActive(path: string): boolean {
  if (path === '/email-topics') return ['/email-topics', '/keywords', '/email-rules'].includes(route.path)
  return route.path === path
}

function handleLogout() {
  appStore.logout()
  router.push('/login')
}

function switchWorkspace(event: Event) {
  const value = Number((event.target as HTMLSelectElement).value)
  if (value) workspaceStore.switchWorkspace(value)
}

async function createWorkspace() {
  const name = window.prompt('请输入新工作区名称')
  if (!name?.trim()) return
  try {
    const { data } = await workspaceApi.create({ name: name.trim() })
    await workspaceStore.load()
    workspaceStore.switchWorkspace(data.id)
  } catch (err: any) {
    appStore.error('创建工作区失败: ' + err.message)
  }
}

onMounted(() => {
  if (appStore.isLoggedIn) workspaceStore.load()
})

const toastClasses: Record<string, string> = {
  success: 'bg-green-500 text-white',
  error: 'bg-red-500 text-white',
  info: 'bg-blue-500 text-white',
  warning: 'bg-yellow-500 text-white',
}
</script>
