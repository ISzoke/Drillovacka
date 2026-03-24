<!--
================================================================================
 Component: InlineInput.vue
 Description:
        Input field for answers in inline form.
 Author: Dominik Horut (xhorut01)
================================================================================
-->

<script setup>
import { defineEmits, defineExpose, ref, onMounted, watch } from 'vue';
import { useRecorderStore } from '@/stores/useRecorderStore';

const emits = defineEmits(['answerSent']);
const recorderStore = useRecorderStore();

//
const answer = ref('');
const answerInput = ref(null);

// Return input field value to parent component - Example
function getAnswer() {
    emits('answerSent', answer.value);
}

// Focus on the input field when the component is mounted
onMounted(() => {
    if (answerInput.value && !recorderStore.isRecording) {
        answerInput.value.focus();
    }
});

// Focus on the input field when mouse is over it
function handleMouseOver() {
    answerInput.value.focus();
}

// Clear input field
const clearInput = () => {
    answer.value = '';
}

defineExpose({ getAnswer, clearInput });

// Display users answer by voice if any
watch(
    () => [recorderStore.isRecording, recorderStore.student_answer],
    ([isRecording, studentAnswer]) => {
        if (isRecording && studentAnswer) {
            answer.value = studentAnswer;

            setTimeout(() => {
                answer.value = '';
            }, 1500);
        }
    }
);
</script>

<template>
    <div class="flex items-center justify-center gap-3">

        <input v-model="answer" class="text-start w-44 md:w-96 text-6xl md:text-8xl border-none self-end p-0 bg-transparent text-slate-800 dark:text-slate-100 focus:outline-none"
            ref="answerInput" @mouseover="handleMouseOver" placeholder="?" inputmode="numeric" />

        <button @click="getAnswer"
            class="md:hidden flex-shrink-0 flex items-center justify-center px-4 py-3 bg-emerald-500 border-[3px] border-emerald-600 border-b-[6px] border-b-emerald-700 rounded-2xl active:translate-y-1 active:border-b-[3px] transition-all">
            <svg xmlns="http://www.w3.org/2000/svg" class="w-8 h-8 text-white" viewBox="0 0 24 24" fill="none"
                stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="20 6 9 17 4 12"/>
            </svg>
        </button>
    </div>
</template>