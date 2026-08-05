<!--
================================================================================
 Component: TopicView.vue
 Description:
      Displays selected skill, related skills and children to allow user to
      specify all skills they want to practice.
================================================================================
-->

<script setup>
import { useI18n } from 'vue-i18n';
import { ref, defineProps, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import Spinner from '@/components/Spinner.vue';
import OperationButton from '@/components/TopicSelector/OperationButton.vue';
import SubTopic from '@/components/TopicSelector/SubTopic.vue';
import { getSkillName } from '@/utils/contentNameMaps';
import { useLanguageStore } from '@/stores/useLanguageStore';
import { useSkillStore } from '@/stores/useSkillStore';

const props = defineProps({ id: { required: true } });

const topic = ref(null);
const subtopics = ref([]);
const operations = ref([]);
const selectedSubtopics = ref([]);
const loading = ref(true);
const langStore = useLanguageStore();
const { t } = useI18n();
const skillStore = useSkillStore();
const router = useRouter();

onMounted(async () => {
  try {
    topic.value = await skillStore.fetchSkill(props.id);
    // example_count is included in get_skills_by_grade response and stored in topic
    if (topic.value.skill_type === 'OPERATION') {
      subtopics.value = await skillStore.fetchRelatedSkillsTree(props.id);
    } else if (topic.value.skill_type === 'NUMBER_DOMAIN') {
      subtopics.value = await skillStore.fetchChildrenSkillsTree(props.id, false);
      operations.value = await skillStore.fetchOperationSkills(props.id);
    } else if (topic.value.skill_type === 'EQUATION') {
      subtopics.value = await skillStore.fetchChildrenSkillsTree(props.id, true);
    }
    selectedSubtopics.value.push(topic.value);
  } catch (error) {
    console.error("Failed to fetch skill data:", error);
  } finally {
    loading.value = false;
  }
});

function startPractice() {
  if (selectedSubtopics.value.length > 0) {
    router.push({
      name: 'examples',
      query: { topics: JSON.stringify(selectedSubtopics.value.map(s => s.id)) }
    });
  }
}

function goBack() {
  router.back();
}

const updateExampleCount = ({ relatedSkills, isSelected }) => {
  relatedSkills.forEach(({ related_id, examples }) => {
    const subtopic = subtopics.value.find(sub => sub.id === related_id);
    if (subtopic) subtopic.examples += isSelected ? examples : -examples;
  });
};
</script>

<template>
  <div class="min-h-screen pb-16">
    <div class="max-w-3xl mx-auto px-4 pt-8 flex flex-col items-center">

      <!-- Header with back button + title -->
      <div class="flex items-center w-full mb-8">
        <button
          @click="goBack"
          class="flex items-center gap-2 text-slate-500 dark:text-slate-400 hover:text-violet-600 dark:hover:text-violet-400
                 transition font-black text-sm bg-slate-100 dark:bg-slate-800 px-4 py-2 rounded-2xl
                 border-2 border-slate-200 dark:border-slate-700 border-b-[4px] border-b-slate-300 dark:border-b-slate-600
                 hover:-translate-y-0.5 active:translate-y-1 active:border-b-[2px] flex-shrink-0"
        >
          <i class="fa-solid fa-arrow-left"></i>
          {{ t('back') }}
        </button>

        <h1 v-if="topic" class="flex-1 text-2xl md:text-4xl font-black text-slate-800 dark:text-slate-100 text-center pr-16">
          {{ getSkillName(topic.name, langStore.language) }}
        </h1>
      </div>

      <Spinner v-if="loading" class="mt-24" />

      <template v-else>
        <!-- TASK type: no subtopic selection, just show example count + start -->
        <template v-if="topic && topic.skill_type === 'TASK'">
          <div class="w-full bg-white dark:bg-slate-800 rounded-3xl border-[3px] border-slate-200 dark:border-slate-700
                      border-b-[8px] border-b-slate-300 dark:border-b-slate-600 p-6 mb-8 text-center shadow-sm">
            <p class="text-slate-400 dark:text-slate-500 font-bold text-lg">
              {{ topic.example_count }} {{ t('examples') || 'príkladov' }}
            </p>
          </div>
        </template>

        <!-- Regular skill: Operations + Subtopics -->
        <template v-else>
          <!-- Operations section -->
          <div v-if="operations.length > 0" class="w-full mb-8">
            <p class="text-xs font-black text-slate-400 dark:text-slate-500 uppercase tracking-widest mb-4 text-center">
              {{ t('chooseOperation') }}
            </p>
            <div class="flex flex-wrap justify-center gap-3">
              <OperationButton
                v-for="operation in operations"
                :key="operation.id"
                :operation="operation"
                :selectedSubtopics="selectedSubtopics"
                @updateExampleCount="updateExampleCount"
              />
            </div>
          </div>

          <!-- Subtopics section -->
          <div v-if="subtopics.length > 0" class="w-full mb-8">
            <p class="text-xs font-black text-slate-400 dark:text-slate-500 uppercase tracking-widest mb-4 text-center">
              {{ t('chooseTopic') }}
            </p>
            <div class="bg-white dark:bg-slate-800 rounded-3xl border-[3px] border-slate-200 dark:border-slate-700
                        border-b-[8px] border-b-slate-300 dark:border-b-slate-600 p-5 shadow-sm">
              <SubTopic
                v-for="subtopic in subtopics"
                :key="subtopic.id"
                :subtopic="subtopic"
                :selectedSubtopics="selectedSubtopics"
              />
            </div>
          </div>
        </template>

        <!-- Start practice button -->
        <button
          @click="startPractice"
          class="w-full py-4 md:py-5 rounded-3xl font-black text-xl md:text-2xl text-white
                 bg-violet-500 border-[3px] border-violet-600 border-b-[8px] border-b-violet-700
                 hover:-translate-y-1 active:translate-y-1 active:border-b-[3px]
                 transition-all shadow-sm"
        >
          {{ t('startPractice') }}
        </button>
      </template>
    </div>
  </div>
</template>
