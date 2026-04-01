<script setup>
import { ref, computed, onMounted } from 'vue';
import { useAuthStore } from '@/stores/useAuthStore';
import { getClassroomTasks, getClassroomDetail } from '@/api/apiClient';
import Spinner from '@/components/Spinner.vue';

const props = defineProps({ classroomId: [String, Number] });

const authStore = useAuthStore();

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
        &larr; Späť do triedy
      </router-link>
    </div>

    <div class="mb-6">
      <h1 class="text-2xl font-bold text-slate-800 dark:text-slate-100">Pohľad žiaka</h1>
      <p v-if="classroom" class="text-sm text-gray-500 dark:text-gray-400 mt-1">
        {{ classroom.name }} &mdash; toto vidia žiaci tejto triedy
      </p>
    </div>

    <Spinner v-if="loading" />

    <template v-else>

      <!-- No tasks -->
      <div v-if="tasks.length === 0"
           class="text-center py-16 text-gray-400">
        <div class="text-4xl mb-3">📭</div>
        Tejto triede nie sú priradené žiadne úlohy.
      </div>

      <template v-else>

        <!-- Regular tasks -->
        <div v-if="regularTasks.length" class="mb-8">
          <h2 class="text-lg font-bold text-slate-700 dark:text-slate-200 mb-3">Úlohy</h2>
          <div class="grid gap-3 sm:grid-cols-2">
            <router-link
              v-for="t in regularTasks" :key="t.id"
              :to="{ name: 'taskDetail', params: { taskId: t.task_id } }"
              class="block p-4 bg-white dark:bg-slate-800 rounded-xl border border-slate-200
                     dark:border-slate-700 hover:border-secondary/60 hover:shadow-sm transition-all"
            >
              <div class="font-semibold text-slate-800 dark:text-slate-100 mb-1">{{ t.task_name }}</div>
              <div class="text-xs text-gray-400 flex gap-3 flex-wrap">
                <span>{{ t.example_count }} príkladov</span>
                <span v-if="t.grade_levels?.length">
                  {{ t.grade_levels.map(g => g + '.').join(', ') }} roč.
                </span>
              </div>
            </router-link>
          </div>
        </div>

        <!-- Homework -->
        <div v-if="homeworkTasks.length">
          <h2 class="text-lg font-bold text-slate-700 dark:text-slate-200 mb-3">
            Domáce úlohy
            <span class="ml-2 text-sm font-normal text-amber-500">{{ homeworkTasks.length }}</span>
          </h2>
          <div class="grid gap-3 sm:grid-cols-2">
            <router-link
              v-for="t in homeworkTasks" :key="t.id"
              :to="{ name: 'taskDetail', params: { taskId: t.task_id } }"
              class="block p-4 bg-white dark:bg-slate-800 rounded-xl border-2 border-amber-200
                     dark:border-amber-700/60 hover:border-amber-400 hover:shadow-sm transition-all"
            >
              <div class="flex items-start justify-between gap-2 mb-1">
                <span class="font-semibold text-slate-800 dark:text-slate-100">{{ t.task_name }}</span>
                <span class="text-xs bg-amber-100 dark:bg-amber-900 text-amber-700 dark:text-amber-200
                             px-2 py-0.5 rounded-full font-medium flex-shrink-0">DÚ</span>
              </div>
              <div class="text-xs text-gray-400 flex gap-3 flex-wrap">
                <span>{{ t.example_count }} príkladov</span>
                <span v-if="t.due_date">
                  Termín: {{ new Date(t.due_date).toLocaleDateString('sk-SK') }}
                </span>
              </div>
            </router-link>
          </div>
        </div>

      </template>
    </template>

  </div>
</template>
