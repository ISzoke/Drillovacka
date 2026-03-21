<!--
================================================================================
 Component: ProgressBar.vue
 Description:
        Displays how many examples user has finished out of total count.
 Author: Dominik Horut (xhorut01)
================================================================================
-->

<script setup>
import { defineProps, computed } from "vue";

const props = defineProps({
  finishedExamples: {
    type: Number,
    required: true
  },
  totalExamples: {
    type: Number,
    required: true
  }
});

// Calculate the progress percentage
const progress = computed(() => {
  return props.totalExamples > 0 ? (props.finishedExamples / props.totalExamples) * 100 : 0;
});

</script>

<template>

    <div class="  w-5/6 md:w-full max-w-md mx-auto pt-20">

      <!-- Progress Bar -->
      <div class="bg-slate-200 dark:bg-slate-700 rounded-full h-6">
        <div
          class="bg-violet-500 h-6 rounded-full transition-all duration-300"
          :style="{ width: progress + '%' }"
        ></div>
      </div>

      <!-- Progress label -->
      <div class="flex justify-center text-xl md:text-3xl font-semibold mt-2 text-slate-700 dark:text-slate-200">
        <span>{{ finishedExamples }} / {{ totalExamples }}</span>
      </div>
    
    </div>
    
  </template>  