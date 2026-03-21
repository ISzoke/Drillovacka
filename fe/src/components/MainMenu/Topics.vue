<!--
================================================================================
 Component: Topics.vue
 Description:
        Displays landing page skills and search bar to filter them by name.
================================================================================
-->

<script setup>
import { onMounted, ref, computed } from 'vue';
import { useTopicStore } from '@/stores/useMainpageTopicStore';
import TopicCard from '@/components/MainMenu/TopicCard.vue';
import GradeView from '@/components/MainMenu/GradeView.vue';
import PersonalizedGradeHome from '@/components/MainMenu/PersonalizedGradeHome.vue';
import Spinner from '../Spinner.vue';
import { useLanguageStore } from '@/stores/useLanguageStore';
import { useAuthStore } from '@/stores/useAuthStore';
import { dictionary } from '@/utils/dictionary';

const topicStore = useTopicStore();
const langStore = useLanguageStore();
const authStore = useAuthStore();
const searchQuery = ref('');

const filteredTopics = computed(() => {
  if (!searchQuery.value) return topicStore.topics;
  return topicStore.topics.filter(topic =>
    topic.name.toLowerCase().includes(searchQuery.value.toLowerCase())
  );
});

onMounted(() => { topicStore.fetchTopics(); });
</script>

<template>
  <div>
    <Spinner v-if="topicStore.loading" class="pt-48" />

    <div v-else>
      <!-- Personalized view for students with a grade set -->
      <PersonalizedGradeHome v-if="authStore.isAuthenticated && authStore.role !== 'admin' && authStore.grade" />

      <!-- Generic grade grid for guests / students without a grade -->
      <template v-else>
        <div class="flex justify-center pt-10 px-4">
          <h2 class="text-3xl md:text-4xl font-black text-slate-800 dark:text-slate-100 text-center">
            {{ dictionary[langStore.language].selectGrades }}
          </h2>
        </div>
        <GradeView />
      </template>

      <!-- Legacy topics (collapsible) -->
      <div v-if="!(authStore.isAuthenticated && authStore.role !== 'admin' && authStore.grade)"
           class="max-w-5xl mx-auto px-4 pb-16">
        <details class="rounded-3xl border-[3px] border-slate-200 dark:border-slate-700
                        border-b-[6px] border-b-slate-300 dark:border-b-slate-600
                        bg-white dark:bg-slate-800 shadow-sm">
          <summary class="cursor-pointer list-none px-6 py-5 flex items-center justify-between
                          text-lg md:text-xl font-black text-slate-600 dark:text-slate-300
                          hover:text-slate-800 dark:hover:text-slate-100 transition">
            <span>
              <i class="fa-solid fa-clock-rotate-left mr-2 text-slate-400 dark:text-slate-500"></i>
              {{ dictionary[langStore.language].legacyOperations }}
            </span>
            <i class="fa-solid fa-chevron-down text-slate-400 dark:text-slate-500"></i>
          </summary>

          <div class="px-6 pb-6 border-t border-slate-100 dark:border-slate-700 pt-4">
            <h3 class="text-lg font-black text-slate-600 dark:text-slate-300 text-center mb-4">
              {{ dictionary[langStore.language].chooseTopic }}
            </h3>

            <!-- Search bar -->
            <div class="flex justify-center mb-6">
              <div class="relative w-full max-w-lg">
                <div class="absolute inset-y-0 left-0 flex items-center pl-4 pointer-events-none text-slate-400 dark:text-slate-500">
                  <i class="fa-solid fa-magnifying-glass"></i>
                </div>
                <input
                  v-model="searchQuery"
                  type="text"
                  :placeholder="dictionary[langStore.language].searchPlaceholderText"
                  class="w-full pl-11 pr-4 py-3 rounded-2xl border-[3px] border-slate-200 dark:border-slate-600
                         bg-slate-50 dark:bg-slate-700 text-slate-800 dark:text-slate-100
                         placeholder-slate-400 dark:placeholder-slate-500
                         focus:outline-none focus:border-violet-400 dark:focus:border-violet-500 transition font-semibold"
                />
              </div>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              <TopicCard
                v-for="(topic, index) in filteredTopics"
                :key="index"
                :topic="topic.name"
                :id="Number(topic.id)"
              />
            </div>
          </div>
        </details>
      </div>
    </div>
  </div>
</template>
