<script setup>
import { ref, computed, onMounted } from 'vue';
import { useAuthStore } from '@/stores/useAuthStore';
import { getClassroomTasks, getClassroomDetail } from '@/api/apiClient';
import { useI18n } from 'vue-i18n';
import Spinner from '@/components/Spinner.vue';

const props = defineProps({ classroomId: [String, Number] });

const authStore = useAuthStore();
const { t } = useI18n();

const classroom = ref(null);
const tasks = ref([]);
const loading = ref(true);

const homeworkTasks = computed(() => tasks.value.filter(t => t.is_homework));
const regularTasks = computed(() => tasks.value.filter(t => !t.is_homework));

const fetchData = async () => {
  loading.value = true;
  try {
    const [classroomData, taskData] = await Promise.all([
      getClassroomDetail(props.classroomId, { teacherId: authStore.id }),
      getClassroomTasks(props.classroomId, { teacherId: authStore.id }),
    ]);
    classroom.value = classroomData;
    tasks.value = taskData || [];
  } catch (e) {
    console.error(e);
  }
  loading.value = false;
};

onMounted(fetchData);
</script>

<template>
  <div class="pt-24 px-4 max-w-4xl mx-auto">

    <div class="flex items-center gap-2 mb-4">
      <router-link :to="{ name: 'teacher-classroom', params: { classroomId } }"
                   class="text-secondary hover:underline text-sm">
        &larr; {{ t('backToClassroom') }}
      </router-link>
    </div>

    <div class="mb-6">
      <h1 class="text-2xl font-bold text-slate-800 dark:text-slate-100">{{ t('studentView') }}</h1>
      <p v-if="classroom" class="text-sm text-gray-500 dark:text-gray-400 mt-1">
        {{ classroom.name }} {{ t('studentViewSuffix') }}
      </p>
    </div>

    <Spinner v-if="loading" />

    <template v-else>

      <!-- No tasks -->
      <div v-if="tasks.length === 0"
           class="text-center py-16 text-gray-400">
        <div class="text-4xl mb-3">📭</div>
        {{ t('noTasksAssignedToClassroom') }}
      </div>

      <template v-else>

        <!-- Regular tasks -->
        <div v-if="regularTasks.length" class="mb-8">
          <h2 class="text-lg font-bold text-slate-700 dark:text-slate-200 mb-3">{{ t('tasksSectionHeading') }}</h2>
          <div class="grid gap-3 sm:grid-cols-2">
            <router-link
              v-for="task in regularTasks" :key="task.id"
              :to="{ name: 'taskDetail', params: { taskId: task.task_id } }"
              class="block p-4 bg-white dark:bg-slate-800 rounded-xl border border-slate-200
                     dark:border-slate-700 hover:border-secondary/60 hover:shadow-sm transition-all"
            >
              <div class="font-semibold text-slate-800 dark:text-slate-100 mb-1">{{ task.task_name }}</div>
              <div class="text-xs text-gray-400 flex gap-3 flex-wrap">
                <span>{{ task.example_count }} {{ t('examplesCount') }}</span>
                <span v-if="task.grade_levels?.length">
                  {{ task.grade_levels.map(g => g + '.').join(', ') }} {{ t('gradeShortSuffix') }}
                </span>
              </div>
            </router-link>
          </div>
        </div>

        <!-- Homework -->
        <div v-if="homeworkTasks.length">
          <h2 class="text-lg font-bold text-slate-700 dark:text-slate-200 mb-3">
            {{ t('homeworkHeading') }}
            <span class="ml-2 text-sm font-normal text-amber-500">{{ homeworkTasks.length }}</span>
          </h2>
          <div class="grid gap-3 sm:grid-cols-2">
            <router-link
              v-for="task in homeworkTasks" :key="task.id"
              :to="{ name: 'taskDetail', params: { taskId: task.task_id } }"
              class="block p-4 bg-white dark:bg-slate-800 rounded-xl border-2 border-amber-200
                     dark:border-amber-700/60 hover:border-amber-400 hover:shadow-sm transition-all"
            >
              <div class="flex items-start justify-between gap-2 mb-1">
                <span class="font-semibold text-slate-800 dark:text-slate-100">{{ task.task_name }}</span>
                <span class="text-xs bg-amber-100 dark:bg-amber-900 text-amber-700 dark:text-amber-200
                             px-2 py-0.5 rounded-full font-medium flex-shrink-0">{{ t('homeworkAbbrev') }}</span>
              </div>
              <div class="text-xs text-gray-400 flex gap-3 flex-wrap">
                <span>{{ task.example_count }} {{ t('examplesCount') }}</span>
                <span v-if="task.due_date">
                  {{ t('dueDateColon') }} {{ new Date(task.due_date).toLocaleDateString('sk-SK') }}
                </span>
              </div>
            </router-link>
          </div>
        </div>

      </template>
    </template>

  </div>
</template>
