<template>
  <router-view v-if="!appStore.isLoggedIn" />

  <div v-else class="paper-shell flex h-screen overflow-hidden">
    <aside :class="['paper-sidebar flex flex-col', appStore.sidebarCollapsed ? 'w-[84px]' : 'w-[264px]']">
      <div class="flex h-16 items-center gap-3 px-4">
        <router-link to="/dashboard" class="flex min-w-0 flex-1 items-center gap-3">
          <div class="paper-logo-mark flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg">
            <svg class="h-5 w-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"
              />
            </svg>
          </div>
          <div v-if="!appStore.sidebarCollapsed" class="min-w-0">
            <div class="truncate text-base font-bold text-gray-900">PaperPulse</div>
            <div class="truncate text-xs text-gray-500">智能论文追踪</div>
          </div>
        </router-link>
      </div>

      <div v-if="workspaceStore.currentWorkspace" class="px-3 pb-3">
        <div v-if="!appStore.sidebarCollapsed" class="paper-workspace rounded-lg p-2.5">
          <div class="mb-2 flex items-center gap-2 text-xs font-medium text-gray-500">
            <span
              class="h-2 w-2 rounded-full"
              :style="{ backgroundColor: workspaceStore.currentWorkspace.color || '#5265ff' }"
            ></span>
            当前工作区
          </div>
          <div class="flex gap-2">
            <select
              :value="workspaceStore.currentWorkspace.id"
              class="min-w-0 flex-1 rounded-lg border px-2.5 py-2 text-sm font-semibold"
              @change="switchWorkspace"
            >
              <option v-for="workspace in workspaceStore.workspaces" :key="workspace.id" :value="workspace.id">
                {{ workspace.name }}
              </option>
            </select>
            <button
              class="rounded-lg border px-3 py-2 text-sm font-semibold text-gray-600 hover:bg-gray-50"
              title="新建工作区"
              @click="createWorkspace"
            >
              +
            </button>
            <button
              class="rounded-lg border px-2 py-2 text-xs font-semibold text-red-500 hover:bg-red-50"
              title="删除当前工作区"
              @click="deleteWorkspace"
              v-if="workspaceStore.currentWorkspace && !workspaceStore.currentWorkspace.is_default"
            >
              ✕
            </button>
          </div>
        </div>
        <button
          v-else
          class="paper-workspace-mini mx-auto flex h-10 w-10 items-center justify-center rounded-lg"
          title="新建工作区"
          @click="createWorkspace"
        >
          +
        </button>
      </div>

      <nav class="flex-1 space-y-1 overflow-y-auto px-3 py-2">
        <router-link
          v-for="item in navItems"
          :key="item.path"
          :to="item.path"
          :class="['paper-side-nav-link', isActive(item.path) ? 'paper-side-nav-link-active' : '']"
          :title="item.label"
        >
          <span class="paper-side-nav-mark">{{ item.mark }}</span>
          <span v-if="!appStore.sidebarCollapsed" class="truncate">{{ item.label }}</span>
        </router-link>
      </nav>

      <div class="space-y-2 border-t border-gray-100 p-3">
        <div v-if="!appStore.sidebarCollapsed" class="rounded-lg bg-white/70 px-3 py-2">
          <div class="truncate text-xs text-gray-500">当前账号</div>
          <div class="truncate text-sm font-semibold text-gray-800">{{ appStore.authUsername }}</div>
        </div>
        <button
          class="paper-side-action"
          title="收起侧边栏"
          @click="appStore.toggleSidebar"
        >
          <span class="paper-side-nav-mark">{{ appStore.sidebarCollapsed ? '>' : '<' }}</span>
          <span v-if="!appStore.sidebarCollapsed">收起侧边栏</span>
        </button>
        <button class="paper-side-action" title="退出登录" @click="handleLogout">
          <span class="paper-side-nav-mark">X</span>
          <span v-if="!appStore.sidebarCollapsed">退出登录</span>
        </button>
      </div>
    </aside>

    <main class="flex min-w-0 flex-1 flex-col overflow-hidden">
      <header class="paper-mainbar flex h-16 flex-shrink-0 items-center justify-between px-6">
        <div>
          <h1 class="text-xl font-semibold text-gray-900">{{ currentTitle }}</h1>
          <p class="mt-0.5 text-xs text-gray-500">工作区内数据独立筛选、分析与推送</p>
        </div>
      </header>

      <div class="paper-content flex-1 overflow-y-auto p-5 lg:p-6">
        <router-view :key="pageKey" />
      </div>
    </main>

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
  { path: '/dashboard', label: '仪表盘', mark: 'D' },
  { path: '/papers', label: '论文', mark: 'P' },
  { path: '/analysis', label: '分析结果', mark: 'A' },
  { path: '/reports', label: '报告', mark: 'R' },
  { path: '/feeds', label: '订阅源', mark: 'F' },
  { path: '/email-topics', label: '邮件主题', mark: 'M' },
  { path: '/reading-queue', label: '阅读队列', mark: 'Q' },
  { path: '/settings', label: '设置', mark: 'S' },
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

async function deleteWorkspace() {
  const ws = workspaceStore.currentWorkspace
  if (!ws || ws.is_default) return
  if (!window.confirm(`确定删除工作区「${ws.name}」？该操作不可恢复。`)) return
  try {
    await workspaceApi.delete(ws.id)
    await workspaceStore.load()
    const def = workspaceStore.workspaces.find(w => w.is_default) || workspaceStore.workspaces[0]
    if (def) workspaceStore.switchWorkspace(def.id)
    appStore.success('工作区已删除')
  } catch (err: any) {
    appStore.error('删除失败: ' + (err.response?.data?.detail || err.message))
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
