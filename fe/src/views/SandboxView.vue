<!--
================================================================================
 Component: SandboxView.vue
 Description:
        Displays interface for creating and editing tasks and their examples.
================================================================================
-->

<script setup>
import { ref, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import ExamplesList from '@/components/TaskCreator/ExamplesList.vue';
import LatexToolbar from '@/components/TaskCreator/LatexToolbar.vue';

const { t } = useI18n();

const taskName = ref('');
const examplesType = ref(null);
const selectedGradeLevelIds = ref([]);

const GRADES = [1, 2, 3, 4, 5, 6, 7, 8, 9];

const toggleGrade = (grade) => {
  const idx = selectedGradeLevelIds.value.indexOf(grade);
  if (idx === -1) selectedGradeLevelIds.value.push(grade);
  else selectedGradeLevelIds.value.splice(idx, 1);
};

const applyImport = (name, _skills, form, gradeLevelIds) => {
  taskName.value = name;
  examplesType.value = form;
  selectedGradeLevelIds.value = gradeLevelIds || [];
};

const clearInput = () => {
  taskName.value = '';
  selectedGradeLevelIds.value = [];
};

onMounted(() => {
  examplesType.value = examplesType.value ?? 'classic';
});
</script>

<template>
  <div class="flex justify-center">
    <LatexToolbar v-if="examplesType == 'classic'"></LatexToolbar>

    <div class="flex justify-center flex-col items-center">

      <!-- Task name input -->
      <div class="flex w-full items-center my-2">
        <h2 class="text-2xl font-bold text-primary mr-8">{{ t('exerciseNameLabel') }}</h2>
        <input v-model="taskName" type="text" class="p-1 text-2xl border border-tertiary rounded-md">
      </div>

      <!-- Grade level picker -->
      <div class="flex w-full items-center flex-wrap gap-2 my-2">
        <h2 class="text-2xl font-bold text-primary mr-4">{{ t('gradeLevel') }}:</h2>
        <button
          v-for="grade in GRADES"
          :key="grade"
          @click="toggleGrade(grade)"
          :class="[
            'w-10 h-10 rounded-xl font-black text-sm border-2 border-b-4 transition-all',
            selectedGradeLevelIds.includes(grade)
              ? 'bg-violet-600 text-white border-violet-700 border-b-violet-900'
              : 'bg-white text-slate-600 border-slate-300 border-b-slate-400 hover:border-violet-400'
          ]"
        >
          {{ grade }}
        </button>
      </div>

      <!-- Examples form selector -->
      <div class="flex w-full justify-start items-center mt-4 space-x-8">
        <h1 class="text-primary font-bold text-2xl">{{ t('formOfAssignmentLabel') }}</h1>
        <label class="flex items-center space-x-2 cursor-pointer text-lg font-medium">
          <input type="radio" v-model="examplesType" value="classic"
            class="h-5 w-5 text-primary bg-transparent border-gray-500 checked:bg-primary checked:border-primary focus:ring-primary" />
          <span class="text-primary text-2xl font-semibold">{{ t('classicExamplesLabel') }}</span>
        </label>
        <label class="flex items-center space-x-2 cursor-pointer text-lg font-medium">
          <input type="radio" v-model="examplesType" value="word-problem"
            class="h-5 w-5 text-primary bg-transparent border-gray-500 checked:bg-primary checked:border-primary focus:ring-primary" />
          <span class="text-primary text-2xl font-semibold">{{ t('wordProblemsLabel') }}</span>
        </label>
      </div>

      <!-- Examples -->
      <ExamplesList
        :selectedGradeLevelIds="selectedGradeLevelIds"
        :taskName="taskName"
        :examplesType="examplesType"
        @importTask="applyImport"
        @submit="clearInput"
      />

    </div>
  </div>
</template>
