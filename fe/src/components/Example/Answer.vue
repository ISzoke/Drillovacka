<!--
================================================================================
 Component: Answer.vue
 Description:
        Displays correct answer of the example.
 Author: Dominik Horut (xhorut01)
================================================================================
-->

<script setup>
import { defineProps, computed, onMounted, watch, nextTick } from 'vue';
import correctIcon from '@/assets/img/correct.png';
import { useLanguageStore } from '@/stores/useLanguageStore';
import { dictionary } from '@/utils/dictionary';

const props = defineProps({
    answer: {
        type: String,
    }
});

const langStore = useLanguageStore();

// Render the answer in LaTeX format
const renderedAnswer = computed(() => `\\(${props.answer}\\)`);

const renderMath = () => {
  nextTick(() => {
      window.MathJax.typeset();
  });
};

onMounted(() => {
  renderMath();
});

// Rerender on change
watch(() => props.answer, () => {
  renderMath();
});
</script>

<template>
    <div class="flex flex-col items-center justify-center bg-white dark:bg-slate-800 border-[3px] border-slate-200 dark:border-slate-700 border-b-[8px] border-b-slate-300 dark:border-b-slate-600 p-8 md:p-12 rounded-3xl shadow-lg">

        <h1 class="text-4xl md:text-5xl font-black text-violet-600 dark:text-violet-400 mb-8">{{dictionary[langStore.language].correctAnswer}}</h1>

        <div class="flex items-center justify-center">
            <!--Just placeholder for answer to be centered -->
            <img :src="correctIcon" class="w-12 h-12 invisible">

            <p class="text-5xl md:text-7xl">{{ renderedAnswer }}</p>
            
            <!--Actual correct icon -->
            <img :src="correctIcon" class="w-12 h-12 ml-2">

        </div>
    </div>
</template>