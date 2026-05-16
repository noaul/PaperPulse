import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { workspaceApi } from '@/api'
import type { Workspace } from '@/api'

const STORAGE_KEY = 'paperpulse:workspace-id'

export const useWorkspaceStore = defineStore('workspace', () => {
  const workspaces = ref<Workspace[]>([])
  const currentWorkspaceId = ref<number | null>(
    Number(localStorage.getItem(STORAGE_KEY)) || null
  )
  const loading = ref(false)

  const currentWorkspace = computed(() => {
    return workspaces.value.find((workspace) => workspace.id === currentWorkspaceId.value) || null
  })

  async function load() {
    loading.value = true
    try {
      const { data } = await workspaceApi.list()
      workspaces.value = data.filter((workspace) => workspace.enabled)
      const saved = currentWorkspaceId.value
      const selected =
        workspaces.value.find((workspace) => workspace.id === saved) ||
        workspaces.value.find((workspace) => workspace.is_default) ||
        workspaces.value[0] ||
        null
      if (selected) switchWorkspace(selected.id, false)
    } finally {
      loading.value = false
    }
  }

  function switchWorkspace(id: number, reload = false) {
    currentWorkspaceId.value = id
    localStorage.setItem(STORAGE_KEY, String(id))
    if (reload) window.location.reload()
  }

  return {
    workspaces,
    currentWorkspaceId,
    currentWorkspace,
    loading,
    load,
    switchWorkspace,
  }
})
