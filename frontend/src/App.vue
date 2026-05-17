<template>
  <router-view v-if="!appStore.isLoggedIn" />

  <div v-else class="paper-shell flex h-screen overflow-hidden">
    <aside :class="['paper-sidebar flex flex-col', appStore.sidebarCollapsed ? 'w-[72px]' : 'w-[240px]']">
      <div class="flex h-16 items-center gap-3 px-4">
        <router-link to="/dashboard" class="flex min-w-0 flex-1 items-center gap-3">
          <div class="paper-logo-mark flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-full">
            <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"
              />
            </svg>
          </div>
          <div v-if="!appStore.sidebarCollapsed" class="min-w-0">
            <div class="paper-brand-word truncate" aria-label="PaperPulse">
              <span class="paper-brand-accent">P</span>aper<span class="paper-brand-accent">P</span>ulse
            </div>
          </div>
        </router-link>
      </div>

      <div v-if="workspaceStore.currentWorkspace" class="px-3 pb-3">
        <div v-if="!appStore.sidebarCollapsed" class="paper-workspace rounded-lg p-2.5">
          <div class="mb-2 flex items-center gap-2 xai-eyebrow">
            <span
              class="h-2 w-2 rounded-full"
              :style="{ backgroundColor: workspaceStore.currentWorkspace.color || '#ffffff' }"
            ></span>
            WORKSPACE
          </div>
          <div class="flex gap-2">
            <select
              :value="workspaceStore.currentWorkspace.id"
              class="min-w-0 flex-1 rounded-lg border border-[var(--xai-hairline)] bg-[var(--xai-canvas-soft)] px-2.5 py-2 text-sm text-[var(--xai-ink)]"
              @change="switchWorkspace"
            >
              <option v-for="workspace in workspaceStore.workspaces" :key="workspace.id" :value="workspace.id">
                {{ workspace.name }}
              </option>
            </select>
            <button
              class="rounded-lg border border-[var(--xai-hairline)] px-3 py-2 text-sm text-[var(--xai-mute)] hover:text-[var(--xai-ink)] hover:border-white/25"
              title="新建工作区"
              @click="createWorkspace"
            >
              +
            </button>
            <button
              class="rounded-lg border border-[var(--xai-hairline)] px-2 py-2 text-xs text-[#fca5a5] hover:border-[rgba(239,68,68,0.4)]"
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
          class="paper-workspace-mini mx-auto flex h-9 w-9 items-center justify-center rounded-lg"
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
          <span :class="['paper-side-nav-mark', item.featured ? 'paper-side-nav-mark-featured' : '']">
            {{ item.mark }}
          </span>
          <span v-if="!appStore.sidebarCollapsed" class="truncate">{{ item.label }}</span>
        </router-link>
      </nav>

      <div class="relative space-y-2 border-t border-[var(--xai-hairline)] p-3">
        <div
          v-if="accountMenuOpen"
          :class="['paper-account-menu', appStore.sidebarCollapsed ? 'paper-account-menu-collapsed' : '']"
        >
          <router-link to="/settings" class="paper-account-menu-item" @click="closeAccountMenu">
            <span class="paper-account-menu-title">设置</span>
            <span class="paper-account-menu-desc">AI、邮件、同步和定时任务</span>
          </router-link>
          <button class="paper-account-menu-item" type="button" @click="openAbout">
            <span class="paper-account-menu-title">关于项目</span>
            <span class="paper-account-menu-desc">PaperPulse 版本与项目说明</span>
          </button>
          <button class="paper-account-menu-item paper-account-menu-danger" type="button" @click="handleLogout">
            <span class="paper-account-menu-title">退出登录</span>
            <span class="paper-account-menu-desc">结束当前会话</span>
          </button>
        </div>

        <button
          :class="['paper-account-button', accountMenuOpen ? 'paper-account-button-active' : '']"
          type="button"
          title="账户菜单"
          @click="toggleAccountMenu"
        >
          <span class="paper-account-avatar">{{ accountInitial }}</span>
          <span v-if="!appStore.sidebarCollapsed" class="min-w-0 flex-1 text-left">
            <span class="block truncate xai-eyebrow">ACCOUNT</span>
            <span class="mt-1 block truncate text-sm text-[var(--xai-ink)]">{{ appStore.authUsername }}</span>
          </span>
          <span v-if="!appStore.sidebarCollapsed" class="paper-account-chevron">⌄</span>
        </button>
        <button
          class="paper-side-action"
          title="收起侧边栏"
          @click="appStore.toggleSidebar"
        >
          <span class="paper-side-nav-mark">{{ appStore.sidebarCollapsed ? '›' : '‹' }}</span>
          <span v-if="!appStore.sidebarCollapsed">收起侧边栏</span>
        </button>
      </div>
    </aside>

    <main class="flex min-w-0 flex-1 flex-col overflow-hidden">
      <header class="paper-mainbar flex h-14 flex-shrink-0 items-center justify-between px-6">
        <div>
          <h1 class="text-base font-normal tracking-tight text-[var(--xai-ink)]">{{ currentTitle }}</h1>
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
          'toast-enter flex min-w-[280px] max-w-sm items-center rounded-lg border px-4 py-3',
          toastClasses[toast.type],
        ]"
      >
        <div class="flex-1 text-sm">{{ toast.message }}</div>
        <button class="ml-3 opacity-70 hover:opacity-100" @click="appStore.removeToast(toast.id)">
          <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
    </div>

    <div v-if="aboutOpen" class="paper-about-overlay" @click.self="closeAbout">
      <section class="paper-about-dialog" role="dialog" aria-modal="true" aria-labelledby="paper-about-title">
        <div class="flex items-start justify-between gap-4">
          <div>
            <p class="xai-eyebrow">ABOUT</p>
            <h2 id="paper-about-title" class="mt-2 text-xl font-semibold text-[var(--xai-ink)]">PaperPulse</h2>
          </div>
          <button class="paper-about-close" type="button" title="关闭" @click="closeAbout">×</button>
        </div>
        <p class="mt-4 text-sm leading-6 text-[var(--xai-body)]">
          PaperPulse 是一个学术论文追踪工具，用于订阅期刊 RSS、执行 AI 文献分析、整理分析报告并通过邮件推送。
        </p>
        <div class="mt-5 grid gap-3 text-sm sm:grid-cols-2">
          <div class="paper-about-meta">
            <span>版本</span>
            <strong>1.0.0</strong>
          </div>
          <div class="paper-about-meta">
            <span>项目</span>
            <strong>uovme/PaperPulse</strong>
          </div>
        </div>
      </section>
    </div>

    <ModalDialog
      :visible="createWsOpen"
      type="prompt"
      eyebrow="WORKSPACE"
      title="新建工作区"
      placeholder="请输入工作区名称"
      confirm-text="创建"
      @confirm="onCreateWsConfirm"
      @cancel="createWsOpen = false"
    />

    <ModalDialog
      :visible="deleteWsOpen"
      type="confirm"
      eyebrow="WORKSPACE"
      :title="`删除工作区「${workspaceStore.currentWorkspace?.name}」`"
      message="该操作不可恢复，工作区内的所有数据将被清除。"
      confirm-text="确认删除"
      :danger="true"
      @confirm="onDeleteWsConfirm"
      @cancel="deleteWsOpen = false"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { workspaceApi } from '@/api'
import { useAppStore } from '@/stores/app'
import { useWorkspaceStore } from '@/stores/workspace'
import ModalDialog from '@/components/ModalDialog.vue'

const appStore = useAppStore()
const workspaceStore = useWorkspaceStore()
const route = useRoute()
const router = useRouter()
const accountMenuOpen = ref(false)
const aboutOpen = ref(false)
const createWsOpen = ref(false)
const deleteWsOpen = ref(false)

const currentTitle = computed(() => (route.meta.title as string) || 'PaperPulse')
const pageKey = computed(() => `${route.fullPath}:${workspaceStore.currentWorkspaceId || 'default'}`)
const accountInitial = computed(() => (appStore.authUsername || 'P').trim().slice(0, 1).toUpperCase())

const navItems = [
  { path: '/dashboard', label: '仪表盘', mark: 'D', featured: true },
  { path: '/papers', label: '论文', mark: 'P', featured: true },
  { path: '/analysis', label: '分析结果', mark: 'A', featured: true },
  { path: '/reports', label: '报告', mark: 'R', featured: true },
  { path: '/feeds', label: '订阅源', mark: 'F', featured: true },
  { path: '/email-topics', label: '邮件主题', mark: 'M', featured: true },
  { path: '/reading-queue', label: '阅读队列', mark: 'Q', featured: true },
]

function isActive(path: string): boolean {
  if (path === '/email-topics') return ['/email-topics', '/keywords', '/email-rules'].includes(route.path)
  return route.path === path
}

function handleLogout() {
  closeAccountMenu()
  appStore.logout()
  router.push('/login')
}

function toggleAccountMenu() {
  accountMenuOpen.value = !accountMenuOpen.value
}

function closeAccountMenu() {
  accountMenuOpen.value = false
}

function openAbout() {
  closeAccountMenu()
  aboutOpen.value = true
}

function closeAbout() {
  aboutOpen.value = false
}

function switchWorkspace(event: Event) {
  const value = Number((event.target as HTMLSelectElement).value)
  if (value) workspaceStore.switchWorkspace(value)
}

async function createWorkspace() {
  createWsOpen.value = true
}

async function onCreateWsConfirm(name: string) {
  createWsOpen.value = false
  if (!name) return
  try {
    const { data } = await workspaceApi.create({ name })
    await workspaceStore.load()
    workspaceStore.switchWorkspace(data.id)
  } catch (err: any) {
    appStore.error('创建工作区失败: ' + err.message)
  }
}

async function deleteWorkspace() {
  const ws = workspaceStore.currentWorkspace
  if (!ws || ws.is_default) return
  deleteWsOpen.value = true
}

async function onDeleteWsConfirm() {
  deleteWsOpen.value = false
  const ws = workspaceStore.currentWorkspace
  if (!ws) return
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
  success: 'bg-[var(--xai-canvas-card)] border-[rgba(34,197,94,0.4)] text-[#86efac]',
  error: 'bg-[var(--xai-canvas-card)] border-[rgba(239,68,68,0.4)] text-[#fca5a5]',
  info: 'bg-[var(--xai-canvas-card)] border-[rgba(160,195,236,0.4)] text-[var(--xai-accent-breeze)]',
  warning: 'bg-[var(--xai-canvas-card)] border-[rgba(245,158,11,0.4)] text-[#fcd34d]',
}
</script>
