<!--
================================================================================
 Component: RegistrationPromptModal.vue
 Description:
        Popup shown to anonymous users when they click a grade.
        Pitches account registration with a list of benefits.
        Skippable — dismissal stored in localStorage so it doesn't repeat.
================================================================================
-->

<script setup>
import { useRouter } from 'vue-router';
import { useLanguageStore } from '@/stores/useLanguageStore';
import { dictionary } from '@/utils/dictionary';

const emit = defineEmits(['skip', 'register']);

const router = useRouter();
const langStore = useLanguageStore();

const t = () => dictionary[langStore.language];

const onRegister = () => {
  emit('register');
  router.push({ name: 'profile', query: { register: '1' } });
};

const onSkip = () => {
  localStorage.setItem('regPromptDismissed', '1');
  emit('skip');
};
</script>

<template>
  <Transition name="modal-fade">
    <div class="fixed inset-0 z-[9000] flex items-center justify-center px-4"
         @click.self="onSkip">

      <!-- Backdrop -->
      <div class="absolute inset-0 bg-black/40 dark:bg-black/60 backdrop-blur-sm" />

      <!-- Card -->
      <div class="relative w-full max-w-sm
                  bg-white dark:bg-slate-800
                  rounded-3xl border-[3px] border-b-[8px]
                  border-slate-200 dark:border-slate-700
                  border-b-slate-300 dark:border-b-slate-600
                  shadow-2xl p-7 flex flex-col items-center text-center">

        <!-- Icon -->
        <div class="w-16 h-16 rounded-2xl bg-violet-100 dark:bg-violet-900/40
                    flex items-center justify-center mb-4">
          <i class="fa-solid fa-user-plus text-3xl text-violet-600 dark:text-violet-400"></i>
        </div>

        <!-- Title -->
        <h2 class="text-xl font-black text-slate-800 dark:text-slate-100 mb-2 leading-tight">
          {{ t().regPromptTitle }}
        </h2>

        <!-- Subtitle -->
        <p class="text-sm text-slate-500 dark:text-slate-400 mb-5 leading-relaxed">
          {{ t().regPromptSubtitle }}
        </p>

        <!-- Benefits list -->
        <ul class="w-full text-left space-y-2 mb-6">
          <li v-for="benefit in t().regPromptBenefits" :key="benefit"
              class="flex items-start gap-2.5 text-sm text-slate-700 dark:text-slate-300">
            <i class="fa-solid fa-circle-check text-violet-500 dark:text-violet-400 mt-0.5 shrink-0"></i>
            <span>{{ benefit }}</span>
          </li>
        </ul>

        <!-- CTA button -->
        <button
          @click="onRegister"
          class="w-full py-3 rounded-2xl font-black text-white text-base
                 bg-violet-600 border-[3px] border-violet-700 border-b-[6px] border-b-violet-800
                 hover:brightness-110 active:translate-y-0.5 active:border-b-[3px]
                 transition-all select-none">
          {{ t().regPromptCta }}
        </button>

        <!-- Skip link -->
        <button
          @click="onSkip"
          class="mt-4 text-sm text-slate-400 dark:text-slate-500
                 hover:text-slate-600 dark:hover:text-slate-300
                 underline underline-offset-2 transition-colors">
          {{ t().regPromptSkip }}
        </button>

      </div>
    </div>
  </Transition>
</template>

<style scoped>
.modal-fade-enter-active {
  transition: opacity 0.2s ease, transform 0.2s cubic-bezier(0.175, 0.885, 0.32, 1.275);
}
.modal-fade-leave-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}
.modal-fade-enter-from {
  opacity: 0;
  transform: scale(0.92);
}
.modal-fade-leave-to {
  opacity: 0;
  transform: scale(0.95);
}
</style>
