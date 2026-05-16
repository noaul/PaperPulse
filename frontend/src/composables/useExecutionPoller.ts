import { ref, onUnmounted } from 'vue'
import { executionApi } from '@/api'

export interface ExecutionProgress {
  id: number
  status: string
  summary: Record<string, any>
}

export function useExecutionPoller(intervalMs = 2000) {
  const execution = ref<ExecutionProgress | null>(null)
  const polling = ref(false)
  let timer: ReturnType<typeof setInterval> | null = null

  async function startPolling(executionId: number) {
    stopPolling()
    polling.value = true
    const poll = async () => {
      try {
        const res = await executionApi.get(executionId)
        execution.value = {
          id: res.data.id,
          status: res.data.status,
          summary: res.data.summary || {},
        }
        if (!['running', 'pending'].includes(res.data.status)) {
          stopPolling()
        }
      } catch {
        stopPolling()
      }
    }
    await poll()
    if (polling.value) {
      timer = setInterval(poll, intervalMs)
    }
  }

  function stopPolling() {
    polling.value = false
    if (timer) {
      clearInterval(timer)
      timer = null
    }
  }

  onUnmounted(stopPolling)

  return { execution, polling, startPolling, stopPolling }
}
