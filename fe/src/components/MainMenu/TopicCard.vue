<!--
================================================================================
 Component: TopicCard.vue
 Description:
        Displays landing page skill.
================================================================================
-->

<script setup>
import { defineProps } from 'vue'
import { useRouter } from 'vue-router'
import { useLanguageStore } from '@/stores/useLanguageStore'
import { getSkillName } from '@/utils/dictionary'

const props = defineProps({
  topic: { type: String, required: true },
  id:    { type: Number, required: true }
})

const router = useRouter()
const langStore = useLanguageStore()

function goToTopicDetail() {
  router.push({ name: 'topic', params: { id: Number(props.id) } })
}
</script>

<template>
  <div
    @click="goToTopicDetail"
    class="cursor-pointer rounded-3xl border-[3px] border-slate-200 dark:border-slate-700
           border-b-[8px] border-b-slate-300 dark:border-b-slate-600
           bg-white dark:bg-slate-800
           hover:-translate-y-1 active:translate-y-1 active:border-b-[3px]
           transition-all shadow-sm"
  >
    <h2 class="flex justify-center text-lg md:text-2xl text-center font-black
               text-slate-800 dark:text-slate-100 p-5">
      {{ getSkillName(topic, langStore.language) }}
    </h2>
  </div>
</template>
