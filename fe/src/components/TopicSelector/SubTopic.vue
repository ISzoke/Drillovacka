<!--
================================================================================
 Component: SubTopic.vue
 Description:
        Display subskill for main skill with example count.
================================================================================
-->

<script setup>
import { ref, defineProps, watch } from 'vue';
import { useLanguageStore } from '@/stores/useLanguageStore';
import { getSkillName } from '@/utils/dictionary';

const props = defineProps({
  subtopic: { required: true },
  selectedSubtopics: { type: Array, required: true }
});

const isSelected = ref(false);
const langStore = useLanguageStore();

watch(isSelected, (newValue) => {
  if (newValue) {
    if (!props.selectedSubtopics.some(s => s.id === props.subtopic.id)) {
      props.selectedSubtopics.push(props.subtopic);
    }
  } else {
    removeFromSelection(props.subtopic);
    removeChildrenFromSelection(props.subtopic.subskills);
  }
});

const removeFromSelection = (subtopic) => {
  const index = props.selectedSubtopics.findIndex(s => s.id === subtopic.id);
  if (index !== -1) props.selectedSubtopics.splice(index, 1);
};

const removeChildrenFromSelection = (subskills) => {
  subskills.forEach(subskill => {
    removeFromSelection(subskill);
    if (subskill.subskills.length > 0) removeChildrenFromSelection(subskill.subskills);
  });
};

const getCorrectForm = (count) => {
  if (langStore.language === 'en') return count === 1 ? 'example' : 'examples';
  if (langStore.language === 'sk') {
    if (count === 1) return 'príklad';
    if (count > 1 && count < 5) return 'príklady';
    return 'príkladov';
  }
  if (count === 1) return 'příklad';
  if (count > 1 && count < 5) return 'příklady';
  return 'příkladů';
};
</script>

<template>
  <div v-if="subtopic" class="pl-2 my-3">
    <label class="flex items-center gap-3 cursor-pointer group">
      <input
        type="checkbox"
        v-model="isSelected"
        class="w-6 h-6 rounded-lg text-violet-500 border-2 border-slate-300 dark:border-slate-600
               focus:ring-2 focus:ring-violet-500 dark:bg-slate-700 cursor-pointer"
      />
      <span class="font-black text-xl text-slate-800 dark:text-slate-100 group-hover:text-violet-600 dark:group-hover:text-violet-400 transition">
        {{ getSkillName(subtopic.name, langStore.language) }}
      </span>
      <span class="text-sm font-bold text-slate-400 dark:text-slate-500">
        ({{ subtopic.examples }} {{ getCorrectForm(subtopic.examples) }})
      </span>
    </label>

    <div v-if="subtopic.subskills.length > 0 && isSelected" class="ml-8 mt-2 border-l-2 border-slate-200 dark:border-slate-700 pl-4">
      <SubTopic
        v-for="(subskill, index) in subtopic.subskills"
        :key="index"
        :subtopic="subskill"
        :selectedSubtopics="selectedSubtopics"
      />
    </div>
  </div>
</template>
