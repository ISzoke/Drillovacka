<!--
================================================================================
 Component: ExampleRequestSheet.vue
 Description:
        Bottom sheet where a student can request new examples to be added.
        Supports both typed text and voice input via the Web Speech API.
        Props: grade (Number|null), open (Boolean)
        Emits: close
================================================================================
-->

<script setup>
import { ref, watch, onUnmounted } from 'vue'
import apiClient from '@/api/apiClient'
import { useAuthStore } from '@/stores/useAuthStore'
import { getSessionId } from '@/utils/sessionManager'

const props = defineProps({
  open: { type: Boolean, default: false },
  grade: { type: Number, default: null },
})
const emit = defineEmits(['close'])

const authStore = useAuthStore()
const text = ref('')
const submitting = ref(false)
const submitted = ref(false)
const error = ref('')

// ── Voice via Web Speech API ─────────────────────────────────────────────────
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
const voiceSupported = !!SpeechRecognition
const listening = ref(false)
let recognition = null

function startVoice() {
  if (!voiceSupported || listening.value) return
  recognition = new SpeechRecognition()
  recognition.lang = 'sk-SK'
  recognition.interimResults = false
  recognition.maxAlternatives = 1

  recognition.onstart = () => { listening.value = true }
  recognition.onend   = () => { listening.value = false }
  recognition.onerror = () => { listening.value = false }
  recognition.onresult = (e) => {
    const transcript = e.results[0][0].transcript
    text.value = text.value ? text.value + ' ' + transcript : transcript
  }
  recognition.start()
}

function stopVoice() {
  recognition?.stop()
}

// ── Submit ───────────────────────────────────────────────────────────────────
async function submit() {
  const trimmed = text.value.trim()
  if (!trimmed) { error.value = 'Prosím napíš alebo nadiktuj svoju požiadavku.'; return }
  error.value = ''
  submitting.value = true
  try {
    const identity = authStore.id
      ? { student_id: authStore.id, session_id: null }
      : { student_id: null, session_id: getSessionId() }
    await apiClient.post('example-requests/', {
      ...identity,
      grade: props.grade,
      text: trimmed,
      source: 'text',
    })
    submitted.value = true
    text.value = ''
    setTimeout(() => { submitted.value = false; emit('close') }, 1800)
  } catch (e) {
    error.value = 'Niečo sa pokazilo, skús znova.'
  } finally {
    submitting.value = false
  }
}

function close() {
  if (listening.value) stopVoice()
  text.value = ''
  error.value = ''
  submitted.value = false
  emit('close')
}

watch(() => props.open, (v) => { if (!v) close() })

onUnmounted(() => { if (listening.value) recognition?.stop() })
</script>

<template>
  <!-- Backdrop -->
  <Transition name="backdrop-fade">
    <div v-if="open" class="fixed inset-0 bg-black/40 z-40" @click="close" />
  </Transition>

  <!-- Sheet -->
  <Transition name="sheet-slide">
    <div
      v-if="open"
      class="fixed bottom-0 left-0 right-0 z-50 bg-white dark:bg-slate-800 rounded-t-3xl shadow-2xl px-5 pt-4 pb-10"
    >
      <!-- Handle -->
      <div class="w-12 h-1.5 bg-slate-300 dark:bg-slate-600 rounded-full mx-auto mb-5" />

      <!-- Success state -->
      <div v-if="submitted" class="text-center py-8">
        <div class="text-5xl mb-3">🙏</div>
        <p class="font-black text-xl text-slate-800 dark:text-slate-100">Ďakujeme!</p>
        <p class="text-slate-500 dark:text-slate-400 text-sm mt-1">Tvoja požiadavka bola odoslaná.</p>
      </div>

      <template v-else>
        <h2 class="text-2xl font-black text-slate-800 dark:text-slate-100 mb-1">Chceš viac príkladov?</h2>
        <p class="text-sm text-slate-400 dark:text-slate-500 mb-4">
          Napíš (alebo nadiktuj), aké príklady by si chcel/a pridať
          <span v-if="grade" class="font-semibold text-violet-600 dark:text-violet-400">pre {{ grade }}. ročník</span>.
        </p>

        <!-- Text area -->
        <textarea
          v-model="text"
          rows="4"
          placeholder="Napr. slovné úlohy na zlomky, obvod trojuholníka, násobilka 7..."
          class="w-full border-[3px] border-slate-200 dark:border-slate-600 rounded-2xl p-3 text-sm
                 bg-slate-50 dark:bg-slate-700 text-slate-800 dark:text-slate-100
                 placeholder-slate-400 dark:placeholder-slate-500
                 resize-none focus:outline-none focus:border-violet-400 dark:focus:border-violet-500 transition"
          :disabled="submitting"
        />

        <!-- Error -->
        <p v-if="error" class="text-red-500 text-xs mt-1">{{ error }}</p>

        <!-- Actions row -->
        <div class="flex gap-3 mt-3">
          <!-- Voice button -->
          <button
            v-if="voiceSupported"
            @click="listening ? stopVoice() : startVoice()"
            :disabled="submitting"
            class="flex items-center gap-2 px-4 py-2.5 rounded-2xl font-bold text-sm border-[3px] transition"
            :class="listening
              ? 'bg-red-50 dark:bg-red-900/20 border-red-300 dark:border-red-700 text-red-600 dark:text-red-400 animate-pulse'
              : 'bg-slate-100 dark:bg-slate-700 border-slate-200 dark:border-slate-600 text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-600'"
          >
            🎤 {{ listening ? 'Nahrávam…' : 'Hlas' }}
          </button>

          <!-- Submit -->
          <button
            @click="submit"
            :disabled="submitting || !text.trim()"
            class="flex-1 py-2.5 rounded-2xl font-black text-sm text-white
                   bg-violet-500 border-[3px] border-violet-600 border-b-[6px] border-b-violet-700
                   hover:-translate-y-0.5 active:translate-y-1 active:border-b-[3px] transition-all
                   disabled:opacity-40 disabled:cursor-not-allowed disabled:translate-y-0 disabled:border-b-[6px]"
          >
            {{ submitting ? 'Odosielam…' : 'Odoslať požiadavku' }}
          </button>
        </div>
      </template>
    </div>
  </Transition>
</template>

<style scoped>
.backdrop-fade-enter-active, .backdrop-fade-leave-active { transition: opacity 0.25s ease; }
.backdrop-fade-enter-from, .backdrop-fade-leave-to       { opacity: 0; }

.sheet-slide-enter-active, .sheet-slide-leave-active { transition: transform 0.3s cubic-bezier(0.32, 0.72, 0, 1); }
.sheet-slide-enter-from, .sheet-slide-leave-to       { transform: translateY(100%); }
</style>
