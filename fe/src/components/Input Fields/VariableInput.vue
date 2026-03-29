<!--
================================================================================
 Component: VariableInput.vue
 Description:
        Input field for variable answers.
 Author: Dominik Horut (xhorut01)
================================================================================
-->

<script setup>
import { defineProps, ref, watch, defineEmits } from 'vue';
import { useRecorderStore } from '@/stores/useRecorderStore';

const props = defineProps({
    variableKeys: {
        type: Array,
        default: () => [],
    }
});
const variables = ref([]);
const recorderStore = useRecorderStore();

const emits = defineEmits(['answerSent']);

// Return input fields value to parent component - Example
function getAnswer() {
    emits('answerSent', variables.value);
}

// Clear input fields
const clearInput = () => {
    variables.value.forEach(variable => {
        variable.answer = '';
    });
}

// Build variable input fields from key names
function getVariables() {
    variables.value = props.variableKeys.map(key => ({ key, answer: '' }));
}

defineExpose({getAnswer, clearInput});

// Rebuild variables when keys change
watch(() => props.variableKeys, getVariables, { immediate: true });

// Display users answer by voice if any
watch(
    () => [recorderStore.isRecording, recorderStore.student_answer],
    ([isRecording, studentAnswer]) => {
        if (isRecording && Array.isArray(studentAnswer) && studentAnswer.length) {
            
            studentAnswer.forEach((val, index) => {
                if (variables.value[index]) {
                    variables.value[index].answer = val;
                }
            });

            setTimeout(() => {
                variables.value.forEach(variable => {
                    variable.answer = '';
                });
            }, 1500);
        }
    }
);
</script>

<template>
    <div class="flex flex-col items-end">

        <div v-for="(variable, index) in variables" :key="index" class="flex">

            <!-- Name of variable -->
            <p class="flex items-center">\({{ variable.key }}\) = </p>

            <!-- Input field for variable -->
            <input
                type="text"
                v-model="variable.answer"
                class="text-start w-64 text-6xl md:text-8xl border-none self-end p-0 bg-transparent text-slate-800 dark:text-slate-100 focus:outline-none"
                placeholder="?"
                inputmode="numeric"
                autofocus
            />

        </div>
        
    </div>
</template>
