<!--
================================================================================
 Component: ExampleRequestSheet.vue
 Description:
        Bottom sheet where a student can:
        1. Send a plain text/voice request (existing flow)
        2. Generate examples with AI (System 1: AI Free Hand)
           → navigates to /examples?task_id=X&batch_id=Y for real drill
        Props: grade (Number|null), open (Boolean)
        Emits: close
================================================================================
-->

<script setup>
import { ref, watch, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import apiClient from '@/api/apiClient'
import { generateExamples, getGenerationQuota } from '@/api/apiClient'
import { useAuthStore } from '@/stores/useAuthStore'
import { getSessionId } from '@/utils/sessionManager'

const props = defineProps({
  open: { type: Boolean, default: false },
  grade: { type: Number, default: null },
})
const emit = defineEmits(['close'])

const authStore = useAuthStore()
const router = useRouter()

// idle | generating | done
const phase = ref('idle')
const text      = ref('')
const error     = ref('')
const submitting = ref(false)

// Daily quota
const quota = ref({ used: 0, limit: 5, remaining: 5 })

async function fetchQuota() {
  if (!authStore.id) return
  try {
    quota.value = await getGenerationQuota(authStore.id)
  } catch { /* non-critical */ }
}

onMounted(fetchQuota)

// ── Voice via Web Speech API ──────────────────────────────────────────────────
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
  recognition.onstart  = () => { listening.value = true }
  recognition.onend    = () => { listening.value = false }
  recognition.onerror  = () => { listening.value = false }
  recognition.onresult = (e) => {
    const t = e.results[0][0].transcript
    text.value = text.value ? text.value + ' ' + t : t
  }
  recognition.start()
}

function stopVoice() { recognition?.stop() }

// ── Plain request (existing flow) ────────────────────────────────────────────
async function submitPlainRequest() {
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
    phase.value = 'done'
    text.value = ''
    setTimeout(() => { phase.value = 'idle'; emit('close') }, 1800)
  } catch {
    error.value = 'Niečo sa pokazilo, skús znova.'
  } finally {
    submitting.value = false
  }
}

// ── AI Generation ────────────────────────────────────────────────────────────
async function generate() {
  if (!authStore.id) {
    error.value = 'Na generovanie príkladov sa musíš prihlásiť.'
    return
  }
  if (quota.value.remaining <= 0) {
    error.value = `Denný limit ${quota.value.limit} generovaní bol dosiahnutý. Skús zajtra.`
    return
  }
  const trimmed = text.value.trim()
  if (!trimmed) { error.value = 'Prosím opíš, aké príklady chceš.'; return }
  error.value = ''
  phase.value = 'generating'

  try {
    const result = await generateExamples({
      student_id: authStore.id,
      description: trimmed,
    })
    text.value  = ''
    phase.value = 'idle'
    emit('close')
    router.push({ name: 'examples', query: { task_id: result.task_id, batch_id: result.batch_id } })
  } catch (e) {
    const msg = typeof e === 'string' ? e : 'Generovanie zlyhalo, skús znova.'
    error.value = msg
    phase.value = 'idle'
    // Refresh quota in case limit was hit
    fetchQuota()
  }
}

// ── Shared ────────────────────────────────────────────────────────────────────
function close() {
  if (listening.value) stopVoice()
  text.value  = ''
  error.value = ''
  phase.value = 'idle'
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
      class="fixed bottom-0 left-0 right-0 z-50 bg-white dark:bg-slate-800 rounded-t-3xl shadow-2xl px-5 pt-4 pb-10 max-h-[90vh] overflow-y-auto"
    >
      <!-- Handle -->
      <div class="w-12 h-1.5 bg-slate-300 dark:bg-slate-600 rounded-full mx-auto mb-5" />

      <!-- ── DONE ── -->
      <div v-if="phase === 'done'" class="text-center py-8">
        <div class="text-5xl mb-3">🙏</div>
        <p class="font-black text-xl text-slate-800 dark:text-slate-100">Ďakujeme!</p>
        <p class="text-slate-500 dark:text-slate-400 text-sm mt-1">Tvoja požiadavka bola odoslaná.</p>
      </div>

      <!-- ── GENERATING ── -->
      <div v-else-if="phase === 'generating'" class="text-center py-12">
        <div class="text-5xl mb-4 animate-bounce">🤖</div>
        <p class="font-black text-xl text-slate-800 dark:text-slate-100 mb-2">Generujem príklady…</p>
        <p class="text-slate-400 dark:text-slate-500 text-sm">AI pracuje, chvíľku počkaj</p>
        <div class="mt-6 flex justify-center gap-1.5">
          <span v-for="i in 3" :key="i"
            class="w-2 h-2 rounded-full bg-violet-400 animate-bounce"
            :style="{ animationDelay: `${(i-1)*0.15}s` }"
          />
        </div>
      </div>

      <!-- ── IDLE ── -->
      <template v-else>
        <h2 class="text-2xl font-black text-slate-800 dark:text-slate-100 mb-1">Chceš viac príkladov?</h2>
        <p class="text-sm text-slate-400 dark:text-slate-500 mb-4">
          Napíš (alebo nadiktuj), aké príklady by si chcel/a
          <span v-if="grade" class="font-semibold text-violet-600 dark:text-violet-400">pre {{ grade }}. ročník</span>.
        </p>

        <!-- Login notice for generation -->
        <div v-if="!authStore.id" class="mb-3 px-3 py-2 rounded-xl bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-700 text-xs text-amber-700 dark:text-amber-400">
          💡 Na <strong>generovanie príkladov</strong> sa musíš prihlásiť. Môžeš však odoslať textovú požiadavku.
        </div>

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

        <!-- Actions -->
        <div class="flex gap-2 mt-3">
          <!-- Voice -->
          <button
            v-if="voiceSupported"
            @click="listening ? stopVoice() : startVoice()"
            :disabled="submitting"
            class="flex items-center gap-1.5 px-3 py-2.5 rounded-2xl font-bold text-sm border-[3px] transition flex-shrink-0"
            :class="listening
              ? 'bg-red-50 dark:bg-red-900/20 border-red-300 dark:border-red-700 text-red-600 animate-pulse'
              : 'bg-slate-100 dark:bg-slate-700 border-slate-200 dark:border-slate-600 text-slate-700 dark:text-slate-300'"
          >
            🎤 {{ listening ? 'Nahrávam…' : '' }}
          </button>

          <!-- Plain request -->
          <button
            @click="submitPlainRequest"
            :disabled="submitting || !text.trim()"
            class="flex-1 py-2.5 rounded-2xl font-black text-sm text-white
                   bg-slate-500 border-[3px] border-slate-600 border-b-[6px] border-b-slate-700
                   hover:-translate-y-0.5 active:translate-y-1 active:border-b-[3px] transition-all
                   disabled:opacity-40 disabled:cursor-not-allowed disabled:translate-y-0 disabled:border-b-[6px]"
          >
            {{ submitting ? 'Odosielam…' : 'Odoslať' }}
          </button>

          <!-- AI Generate (only for logged-in) -->
          <button
            v-if="authStore.id"
            @click="generate"
            :disabled="submitting || !text.trim() || quota.remaining <= 0"
            class="flex-1 py-2.5 rounded-2xl font-black text-sm text-white
                   bg-violet-500 border-[3px] border-violet-600 border-b-[6px] border-b-violet-700
                   hover:-translate-y-0.5 active:translate-y-1 active:border-b-[3px] transition-all
                   disabled:opacity-40 disabled:cursor-not-allowed disabled:translate-y-0 disabled:border-b-[6px]"
          >
            ✨ Generovať
          </button>
        </div>

        <!-- Daily quota indicator (logged-in only) -->
        <div v-if="authStore.id" class="mt-3 text-center">
          <span
            class="text-xs font-semibold"
            :class="quota.remaining === 0
              ? 'text-red-500 dark:text-red-400'
              : quota.remaining <= 2
                ? 'text-amber-500 dark:text-amber-400'
                : 'text-slate-400 dark:text-slate-500'"
          >
            <span v-if="quota.remaining === 0">Denný limit dosiahnutý ({{ quota.limit }}/{{ quota.limit }}). Skús zajtra.</span>
            <span v-else>Ešte môžeš vygenerovať: <strong>{{ quota.remaining }}</strong> / {{ quota.limit }}</span>
          </span>
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
