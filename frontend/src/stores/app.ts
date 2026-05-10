import { defineStore } from 'pinia'
import { ref } from 'vue'

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
