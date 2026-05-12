<template>
  <!-- Login page: no sidebar -->
  <router-view v-if="!appStore.isLoggedIn" />

  <!-- Main app layout -->
  <div v-else class="paper-shell flex h-screen overflow-hidden">
    <!-- Sidebar -->
    <aside
      :class="[
        'paper-sidebar flex flex-col transition-all duration-300 ease-in-out',
        appStore.sidebarCollapsed ? 'w-16' : 'w-60',
      ]"
    >
      <!-- Logo -->
      <div class="flex items-center h-16 px-4 border-b">
        <div class="flex items-center space-x-3 overflow-hidden">
          <div class="paper-logo-mark w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0">
            <svg class="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
            </svg>
          </div>
          <span v-if="!appStore.sidebarCollapsed" class="font-semibold text-lg whitespace-nowrap text-gray-900">
            PaperPulse
          </span>
        </div>
      </div>

      <!-- Navigation -->
      <nav class="flex-1 py-4 space-y-1 px-2 overflow-y-auto">
        <router-link
          v-for="item in navItems"
          :key="item.path"
          :to="item.path"
          :class="[
            'flex items-center space-x-3 px-3 py-2.5 rounded-lg transition-colors duration-200',
            isActive(item.path)
              ? 'paper-nav-link-active'
              : 'paper-nav-link',
          ]"
        >
          <div class="w-5 h-5 flex-shrink-0" v-html="item.icon"></div>
          <span v-if="!appStore.sidebarCollapsed" class="whitespace-nowrap">
            {{ item.label }}
          </span>
        </router-link>
      </nav>

      <!-- User / Logout -->
      <div class="border-t p-2 space-y-1">
        <div v-if="!appStore.sidebarCollapsed" class="px-3 py-1.5 text-xs text-gray-500 truncate">
          {{ appStore.authUsername }}
        </div>
        <button
          @click="handleLogout"
          class="w-full flex items-center justify-center px-3 py-2 rounded-lg text-gray-500 hover:bg-white/70 hover:text-gray-900 transition-colors"
          title="退出登录"
        >
          <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
          </svg>
          <span v-if="!appStore.sidebarCollapsed" class="ml-2 text-sm">退出登录</span>
        </button>
        <button
          @click="appStore.toggleSidebar"
          class="w-full flex items-center justify-center px-3 py-2 rounded-lg text-gray-500 hover:bg-white/70 hover:text-gray-900 transition-colors"
        >
          <svg
            class="w-5 h-5 transition-transform duration-300"
            :class="{ 'rotate-180': appStore.sidebarCollapsed }"
            fill="none" viewBox="0 0 24 24" stroke="currentColor"
          >
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M11 19l-7-7 7-7m8 14l-7-7 7-7" />
          </svg>
        </button>
      </div>
    </aside>

    <!-- Main Content -->
    <main class="flex-1 flex flex-col overflow-hidden">
      <!-- Top Bar -->
      <header class="paper-topbar h-16 flex items-center justify-between px-6 flex-shrink-0">
        <div>
          <h1 class="text-xl font-semibold text-gray-900">
            {{ currentTitle }}
          </h1>
          <p class="text-xs text-gray-500 mt-0.5">论文监控、AI 分析与报告工作台</p>
        </div>
        <div class="hidden md:flex items-center gap-2 text-xs text-gray-500">
          <span class="h-2 w-2 rounded-full bg-green-500"></span>
          系统在线
        </div>
      </header>

      <!-- Page Content -->
      <div class="paper-content flex-1 overflow-y-auto p-6">
        <router-view />
      </div>
    </main>

    <!-- Toast Container -->
    <div class="fixed top-4 right-4 z-50 space-y-2">
      <div
        v-for="toast in appStore.toasts"
        :key="toast.id"
        :class="[
          'toast-enter flex items-center px-4 py-3 rounded-lg shadow-lg min-w-[280px] max-w-sm',
          toastClasses[toast.type],
        ]"
      >
        <div class="flex-1 text-sm font-medium">{{ toast.message }}</div>
        <button
          @click="appStore.removeToast(toast.id)"
          class="ml-3 opacity-70 hover:opacity-100"
        >
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAppStore } from '@/stores/app'

const appStore = useAppStore()
const route = useRoute()
const router = useRouter()

const currentTitle = computed(() => {
  return (route.meta.title as string) || 'PaperPulse'
})

function isActive(path: string): boolean {
  return route.path === path
}

function handleLogout() {
  appStore.logout()
  router.push('/login')
}

const navItems = [
  {
    path: '/dashboard',
    label: '仪表盘',
    icon: '<svg fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" /></svg>',
  },
  {
    path: '/feeds',
    label: '订阅源',
    icon: '<svg fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 5c7.18 0 13 5.82 13 13M6 11a7 7 0 017 7m-6 0a1 1 0 11-2 0 1 1 0 012 0z" /></svg>',
  },
  {
    path: '/papers',
    label: '论文',
    icon: '<svg fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>',
  },
  {
    path: '/reading-queue',
    label: '阅读队列',
    icon: '<svg fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-4-7 4V5z" /></svg>',
  },
  {
    path: '/analysis',
    label: '分析结果',
    icon: '<svg fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 17v-6a2 2 0 012-2h2a2 2 0 012 2v6m-6 0h6m-9 4h12a2 2 0 002-2V7a2 2 0 00-.586-1.414l-3-3A2 2 0 0017 2H7a2 2 0 00-2 2v15a2 2 0 002 2z" /></svg>',
  },
  {
    path: '/reports',
    label: '报告中心',
    icon: '<svg fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3M5 11h14M7 21h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v12a2 2 0 002 2zm3-6h4m-4 3h6" /></svg>',
  },
  {
    path: '/keywords',
    label: '关键词',
    icon: '<svg fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" /></svg>',
  },
  {
    path: '/settings',
    label: '设置',
    icon: '<svg fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" /><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" /></svg>',
  },
]

const toastClasses: Record<string, string> = {
  success: 'bg-green-500 text-white',
  error: 'bg-red-500 text-white',
  info: 'bg-blue-500 text-white',
  warning: 'bg-yellow-500 text-white',
}
</script>
