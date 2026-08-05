<!--
================================================================================
 Component: OperationButton.vue
 Description:
        Display operation skill and allow user to select it.
================================================================================
-->

<script setup>
import { defineProps, ref, computed, defineEmits } from 'vue';
import { useLanguageStore } from '@/stores/useLanguageStore';
import { getSkillName } from '@/utils/contentNameMaps';

const props = defineProps({
  operation: { type: Object, required: true },
  selectedSubtopics: { type: Array, required: true }
});

const isSelected = ref(false);
const emit = defineEmits(['updateExampleCount']);
const langStore = useLanguageStore();

const select = () => {
  isSelected.value = !isSelected.value;
  if (isSelected.value) {
    if (!props.selectedSubtopics.some(s => s.id === props.operation.id)) {
      props.selectedSubtopics.push(props.operation);
    }
  } else {
    const index = props.selectedSubtopics.findIndex(s => s.id === props.operation.id);
    if (index !== -1) props.selectedSubtopics.splice(index, 1);
  }
  emit('updateExampleCount', { relatedSkills: props.operation.related_skills, isSelected: isSelected.value });
};
</script>

<template>
  <button
    @click="select"
    class="px-5 py-3 rounded-2xl font-black text-lg transition-all border-[3px] border-b-[6px]
           hover:-translate-y-0.5 active:translate-y-1 active:border-b-[3px]"
    :class="isSelected
      ? 'bg-violet-500 text-white border-violet-600 border-b-violet-700'
      : 'bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-200 border-slate-200 dark:border-slate-600 border-b-slate-300 dark:border-b-slate-500 hover:bg-slate-200 dark:hover:bg-slate-600'"
  >
    {{ getSkillName(operation.name, langStore.language) }}
  </button>
</template>
