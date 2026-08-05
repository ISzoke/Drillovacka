<!--
================================================================================
 Component: HomeView.vue
 Description:
        Displays landing page for user and admin.
 Author: Dominik Horut (xhorut01)
================================================================================
-->

<script setup>
import { useI18n } from 'vue-i18n';
import Topics from '@/components/MainMenu/Topics.vue';
import { useAuthStore } from '@/stores/useAuthStore';
import { onMounted } from 'vue';
import { useRoute} from 'vue-router';
import { useRecorderStore } from '@/stores/useRecorderStore';
import { useLanguageStore } from '@/stores/useLanguageStore';
// Stores
const authStore = useAuthStore();
const route = useRoute();
const langStore = useLanguageStore();
const { t } = useI18n();
const recorderStore = useRecorderStore();

onMounted(() => {
  // Set ASR language based on the selected language
  if(langStore.language === 'en') {
    recorderStore.changeASRLanguage('en-US');
  } else if(langStore.language === 'cs') {
    recorderStore.changeASRLanguage('cs-CZ');
  } else {
    recorderStore.changeASRLanguage('sk-SK');
  }
});
</script>

<template>
  
  <!-- View for user - skills -->
  <Topics v-if="authStore.role != 'admin'"></Topics>
  
  <!-- View for admin - tasks and skills management -->
  <div v-else>
    <p class="text-4xl text-primary flex justify-center font-bold pt-16">
      {{ t('adminHomeTitle') }}
    </p>

    <div class="flex flex-col items-center justify-center gap-5 pt-16">

      <RouterLink to="/tasks"
        class="w-80 cursor-pointer rounded-3xl border-[3px] border-slate-200 dark:border-slate-700
               border-b-[8px] border-b-slate-300 dark:border-b-slate-600
               bg-white dark:bg-slate-800 flex items-center justify-center
               text-2xl text-center font-black text-slate-800 dark:text-slate-100 p-6
               hover:-translate-y-1 active:translate-y-1 active:border-b-[3px] transition-all shadow-sm">
        {{ t('tasks') }}
      </RouterLink>

      <RouterLink to="/skill-creator"
        class="w-80 cursor-pointer rounded-3xl border-[3px] border-slate-200 dark:border-slate-700
               border-b-[8px] border-b-slate-300 dark:border-b-slate-600
               bg-white dark:bg-slate-800 flex items-center justify-center
               text-2xl text-center font-black text-slate-800 dark:text-slate-100 p-6
               hover:-translate-y-1 active:translate-y-1 active:border-b-[3px] transition-all shadow-sm">
        {{ t('skills') }}
      </RouterLink>
      
    </div>
    
  </div>

</template>
