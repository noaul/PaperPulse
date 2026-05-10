import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export interface Toast {
  id: number
  message: string
  type: 'success' | 'error' | 'info' | 'warning'
  duration?: number
}

export const useAppStore = defineStore('app', () => {
  const sidebarCollapsed = ref(false)
  const toasts = ref<Toast[]>([])
  const loading = ref(false)
  let toastId = 0

  // Auth state
  const authToken = ref<string | null>(localStorage.getItem('auth_token'))
  const authUsername = ref<string | null>(localStorage.getItem('auth_username'))
  const isLoggedIn = computed(() => !!authToken.value)

  function setAuth(token: string, username: string) {
    authToken.value = token
    authUsername.value = username
    localStorage.setItem('auth_token', token)
    localStorage.setItem('auth_username', username)
  }

  function logout() {
    authToken.value = null
    authUsername.value = null
    localStorage.removeItem('auth_token')
    localStorage.removeItem('auth_username')
  }

  function toggleSidebar() {
    sidebarCollapsed.value = !sidebarCollapsed.value
  }

  function showLoading() {
    loading.value = true
  }

  function hideLoading() {
    loading.value = false
  }

  function addToast(message: string, type: Toast['type'] = 'info', duration = 3000) {
    const id = ++toastId
    toasts.value.push({ id, message, type, duration })
    if (duration > 0) {
      setTimeout(() => {
        removeToast(id)
      }, duration)
    }
  }

  function removeToast(id: number) {
    const index = toasts.value.findIndex((t) => t.id === id)
    if (index > -1) {
      toasts.value.splice(index, 1)
    }
  }

  function success(message: string) {
    addToast(message, 'success')
  }

  function error(message: string) {
    addToast(message, 'error', 5000)
  }

  function info(message: string) {
    addToast(message, 'info')
  }

  function warning(message: string) {
    addToast(message, 'warning', 4000)
  }

  return {
    sidebarCollapsed,
    toasts,
    loading,
    authToken,
    authUsername,
    isLoggedIn,
    setAuth,
    logout,
    toggleSidebar,
    showLoading,
    hideLoading,
    addToast,
    removeToast,
    success,
    error,
    info,
    warning,
  }
})
