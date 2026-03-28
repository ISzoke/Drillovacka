<script setup>
import { useLanguageStore } from '@/stores/useLanguageStore';
import { dictionary } from '@/utils/dictionary';
const langStore = useLanguageStore();
const t = () => dictionary[langStore.language];
</script>

<template>
  <div class="flex justify-center px-4 py-12">
    <div class="w-full max-w-lg">

      <div class="bg-white dark:bg-slate-800
                  rounded-3xl border-[3px] border-b-[8px]
                  border-slate-200 dark:border-slate-700
                  border-b-slate-300 dark:border-b-slate-600
                  shadow-sm p-8 flex flex-col items-center text-center">

        <!-- Icon -->
        <div class="w-16 h-16 rounded-2xl bg-violet-100 dark:bg-violet-900/40
                    flex items-center justify-center mb-5">
          <i class="fa-solid fa-envelope text-3xl text-violet-600 dark:text-violet-400"></i>
        </div>

        <!-- Title -->
        <h1 class="text-3xl font-black text-slate-800 dark:text-slate-100 mb-4">
          {{ t().contactTitle }}
        </h1>

        <!-- Description -->
        <p class="text-slate-500 dark:text-slate-400 leading-relaxed mb-8">
          {{ t().contactDesc }}
        </p>

        <!-- Email card -->
        <a href="mailto:martin.it2442@gmail.com"
           class="w-full flex items-center gap-4 px-5 py-4
                  rounded-2xl border-[3px] border-violet-200 dark:border-violet-800
                  bg-violet-50 dark:bg-violet-900/20
                  hover:bg-violet-100 dark:hover:bg-violet-900/40
                  transition-colors group">
          <i class="fa-solid fa-paper-plane text-xl text-violet-500 dark:text-violet-400 group-hover:translate-x-0.5 transition-transform"></i>
          <span class="font-black text-violet-700 dark:text-violet-300 text-lg">
            martin.it2442@gmail.com
          </span>
        </a>

      </div>
    </div>
  </div>
</template>
