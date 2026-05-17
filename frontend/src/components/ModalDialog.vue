<template>
  <Teleport to="body">
    <div v-if="visible" class="paper-about-overlay" @click.self="onCancel">
      <section class="paper-about-dialog" role="dialog" aria-modal="true">
        <div class="flex items-start justify-between gap-4">
          <div>
            <p class="xai-eyebrow">{{ eyebrow }}</p>
            <h2 class="mt-2 text-lg font-semibold text-[var(--xai-ink)]">{{ title }}</h2>
          </div>
          <button class="paper-about-close" type="button" title="关闭" @click="onCancel">×</button>
        </div>
        <p v-if="message" class="mt-3 text-sm leading-6 text-[var(--xai-body)]">{{ message }}</p>
        <div v-if="type === 'prompt'" class="mt-4">
          <input
            ref="inputRef"
            v-model="inputValue"
            class="w-full rounded-lg border border-[var(--xai-hairline)] bg-[var(--xai-canvas-soft)] px-3 py-2.5 text-sm text-[var(--xai-ink)] placeholder:text-[var(--xai-mute)] focus:border-[var(--xai-accent-breeze)] focus:outline-none"
            :placeholder="placeholder"
            @keydown.enter="onConfirm"
          />
        </div>
        <div class="mt-5 flex justify-end gap-3">
          <button
            class="rounded-lg border border-[var(--xai-hairline)] px-4 py-2 text-sm text-[var(--xai-mute)] hover:text-[var(--xai-ink)] hover:border-white/25"
            @click="onCancel"
          >
            取消
          </button>
          <button
            :class="[
              'rounded-lg px-4 py-2 text-sm font-medium',
              danger
                ? 'bg-red-600/20 border border-red-500/40 text-[#fca5a5] hover:bg-red-600/30'
                : 'bg-[var(--xai-accent-breeze)]/15 border border-[var(--xai-accent-breeze)]/40 text-[var(--xai-accent-breeze)] hover:bg-[var(--xai-accent-breeze)]/25'
            ]"
            @click="onConfirm"
          >
            {{ confirmText }}
          </button>
        </div>
      </section>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'

const props = withDefaults(defineProps<{
  visible: boolean
  type?: 'confirm' | 'prompt'
  eyebrow?: string
  title: string
  message?: string
  placeholder?: string
  confirmText?: string
  danger?: boolean
  defaultValue?: string
}>(), {
  type: 'confirm',
  eyebrow: '',
  message: '',
  placeholder: '',
  confirmText: '确定',
  danger: false,
  defaultValue: '',
})

const emit = defineEmits<{
  confirm: [value: string]
  cancel: []
}>()

const inputValue = ref(props.defaultValue)
const inputRef = ref<HTMLInputElement>()

watch(() => props.visible, (val) => {
  if (val) {
    inputValue.value = props.defaultValue
    if (props.type === 'prompt') {
      nextTick(() => inputRef.value?.focus())
    }
  }
})

function onConfirm() {
  if (props.type === 'prompt' && !inputValue.value.trim()) return
  emit('confirm', inputValue.value.trim())
}

function onCancel() {
  emit('cancel')
}
</script>
