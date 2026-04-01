<script setup>
import { ref, onMounted, computed } from 'vue';
import { useAuthStore } from '@/stores/useAuthStore';
import { leaveClassroom, getClassroomDetail, getClassroomTasks } from '@/api/apiClient';
import { dictionary } from '@/utils/dictionary';
import { useLanguageStore } from '@/stores/useLanguageStore';
import { useToastStore } from '@/stores/useToastStore';
import { useRouter } from 'vue-router';
import Spinner from '@/components/Spinner.vue';

const props = defineProps({ classroomId: [String, Number] });

const authStore = useAuthStore();
const router = useRouter();
const langStore = useLanguageStore();
const toastStore = useToastStore();
const d = dictionary[langStore.language];

const classroom = ref(null);
const tasks = ref([]);
const loading = ref(true);
const showLeaveConfirm = ref(false);
const activeTab = ref('tasks');

const homeworkTasks = computed(() => tasks.value.filter(t => t.is_homework));
const regularTasks = computed(() => tasks.value.filter(t => !t.is_homework));

const tabs = computed(() => [
  { key: 'tasks', label: d.tasks || 'Úlohy', count: regularTasks.value.length, icon: '📚' },
  { key: 'homework', label: d.homework || 'Domáce úlohy', count: homeworkTasks.value.length, icon: '📝' },
  { key: 'classmates', label: d.classmates || 'Spolužiaci', count: classroom.value?.students?.length || 0, icon: '👥' },
]);

const fetchData = async () => {
  loading.value = true;
  try {
    const [classroomData, taskData] = await Promise.all([
      getClassroomDetail(props.classroomId, { studentId: authStore.id }),
      getClassroomTasks(props.classroomId, { studentId: authStore.id }),
    ]);
    classroom.value = classroomData;
    tasks.value = taskData || [];
  } catch (e) {
    console.error('Error fetching classroom:', e);
  }
  loading.value = false;
};

const handleLeave = async () => {
  try {
    await leaveClassroom(props.classroomId, authStore.id);
    toastStore.addToast({ message: d.leftClassroom || 'Opustil si triedu.', type: 'info', visible: true });
    router.push({ name: 'student-classrooms' });
  } catch (e) {
    console.error('Error leaving classroom:', e);
    toastStore.addToast({ message: d.leaveError || 'Chyba pri opúšťaní triedy.', type: 'error', visible: true });
  }
};

onMounted(fetchData);
</script>

<template>
  <div class="pt-20 px-4 max-w-4xl mx-auto pb-12">
    <Spinner v-if="loading" />

    <template v-else-if="classroom">

      <!-- Back link -->
      <router-link
        :to="{ name: 'student-classrooms' }"
        class="inline-flex items-center gap-1 text-secondary hover:underline text-sm mb-5"
      >
        ← {{ d.myClassrooms || 'Moje triedy' }}
      </router-link>

      <!-- Header card -->
      <div class="rounded-3xl border-2 border-slate-200 dark:border-slate-700
                  border-b-[8px] border-b-slate-300 dark:border-b-slate-600
                  bg-white dark:bg-slate-800 p-6 mb-6">
        <div class="flex items-start justify-between gap-4">
          <div class="flex items-center gap-4">
            <div class="w-14 h-14 rounded-2xl bg-secondary/10 dark:bg-secondary/20
                        flex items-center justify-center text-3xl flex-shrink-0">
              🏫
            </div>
            <div>
              <h1 class="text-2xl font-bold text-primary dark:text-white leading-tight">
                {{ classroom.name }}
              </h1>
              <p v-if="classroom.description" class="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
                {{ classroom.description }}
              </p>
              <p class="text-xs text-gray-400 mt-1">
                👤 {{ classroom.teacher_name }}
              </p>
            </div>
          </div>
          <button
            @click="showLeaveConfirm = true"
            class="text-xs text-gray-400 hover:text-accent transition-colors flex-shrink-0 mt-1
                   px-3 py-1.5 rounded-lg hover:bg-accent/10 border border-transparent
                   hover:border-accent/20"
          >
            {{ d.leaveClassroom || 'Opustiť' }}
          </button>
        </div>
      </div>

      <!-- Tabs -->
      <div class="flex gap-2 mb-5 overflow-x-auto pb-1">
        <button
          v-for="tab in tabs"
          :key="tab.key"
          @click="activeTab = tab.key"
          :class="[
            'flex items-center gap-1.5 px-4 py-2.5 rounded-2xl font-semibold text-sm transition-all whitespace-nowrap flex-shrink-0',
            activeTab === tab.key
              ? 'bg-primary text-white shadow-sm'
              : 'bg-white dark:bg-slate-800 text-gray-500 dark:text-gray-400 border border-slate-200 dark:border-slate-700 hover:border-secondary/50'
          ]"
        >
          <span>{{ tab.icon }}</span>
          <span>{{ tab.label }}</span>
          <span :class="[
            'text-xs px-1.5 py-0.5 rounded-full',
            activeTab === tab.key
              ? 'bg-white/20 text-white'
              : 'bg-slate-100 dark:bg-slate-700 text-gray-400'
          ]">{{ tab.count }}</span>
        </button>
      </div>

      <!-- Tasks tab -->
      <div v-if="activeTab === 'tasks'">
        <div v-if="regularTasks.length === 0"
             class="text-center py-16 rounded-3xl border-2 border-dashed
                    border-slate-200 dark:border-slate-700">
          <div class="text-4xl mb-3">📚</div>
          <p class="text-gray-400">{{ d.noTasksAssigned || 'Žiadne úlohy nie sú priradené.' }}</p>
        </div>
        <div v-else class="space-y-3">
          <router-link
            v-for="t in regularTasks"
            :key="t.task_id"
            :to="{ name: 'taskDetail', params: { taskId: t.task_id } }"
            class="flex items-center justify-between p-4
                   rounded-2xl border-2 border-slate-200 dark:border-slate-700
                   border-b-[6px] border-b-slate-300 dark:border-b-slate-600
                   bg-white dark:bg-slate-800
                   hover:-translate-y-0.5 active:translate-y-0.5 active:border-b-2 transition-all"
          >
            <div class="flex items-center gap-3">
              <div class="w-10 h-10 rounded-xl bg-secondary/10 dark:bg-secondary/20
                          flex items-center justify-center text-lg flex-shrink-0">
                📖
              </div>
              <div>
                <div class="font-semibold text-slate-800 dark:text-slate-100">{{ t.task_name }}</div>
                <div class="text-xs text-gray-400 mt-0.5">
                  {{ t.example_count }} {{ d.examples || 'príkladov' }}
                  <span v-if="t.grade_levels?.length">
                    &middot; {{ t.grade_levels.map(g => g + '.').join(', ') }}
                  </span>
                </div>
              </div>
            </div>
            <span class="text-secondary font-bold text-xl">›</span>
          </router-link>
        </div>
      </div>

      <!-- Homework tab -->
      <div v-if="activeTab === 'homework'">
        <div v-if="homeworkTasks.length === 0"
             class="text-center py-16 rounded-3xl border-2 border-dashed
                    border-slate-200 dark:border-slate-700">
          <div class="text-4xl mb-3">📝</div>
          <p class="text-gray-400">{{ d.noHomework || 'Žiadne domáce úlohy.' }}</p>
        </div>
        <div v-else class="space-y-3">
          <router-link
            v-for="t in homeworkTasks"
            :key="t.task_id"
            :to="{ name: 'taskDetail', params: { taskId: t.task_id } }"
            class="flex items-center justify-between p-4
                   rounded-2xl border-2 border-amber-200 dark:border-amber-800
                   border-b-[6px] border-b-amber-300 dark:border-b-amber-700
                   bg-amber-50 dark:bg-amber-900/20
                   hover:-translate-y-0.5 active:translate-y-0.5 active:border-b-2 transition-all"
          >
            <div class="flex items-center gap-3">
              <div class="w-10 h-10 rounded-xl bg-amber-100 dark:bg-amber-800/50
                          flex items-center justify-center text-lg flex-shrink-0">
                📝
              </div>
              <div>
                <div class="flex items-center gap-2">
                  <span class="font-semibold text-slate-800 dark:text-slate-100">{{ t.task_name }}</span>
                  <span class="text-xs bg-amber-200 dark:bg-amber-800 text-amber-800 dark:text-amber-200
                               px-2 py-0.5 rounded-full font-medium">DÚ</span>
                </div>
                <div class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                  {{ t.example_count }} {{ d.examples || 'príkladov' }}
                  <span v-if="t.due_date" class="text-amber-600 dark:text-amber-400 ml-1 font-medium">
                    · {{ d.dueDate || 'Termín' }}: {{ new Date(t.due_date).toLocaleDateString() }}
                  </span>
                </div>
              </div>
            </div>
            <span class="text-amber-500 font-bold text-xl">›</span>
          </router-link>
        </div>
      </div>

      <!-- Classmates tab -->
      <div v-if="activeTab === 'classmates'">
        <div v-if="!classroom.students?.length"
             class="text-center py-16 rounded-3xl border-2 border-dashed
                    border-slate-200 dark:border-slate-700">
          <div class="text-4xl mb-3">👥</div>
          <p class="text-gray-400">{{ d.noClassmatesYet || 'Zatiaľ žiadni spolužiaci.' }}</p>
        </div>
        <div v-else class="grid grid-cols-2 sm:grid-cols-3 gap-3">
          <div
            v-for="s in classroom.students"
            :key="s.id"
            class="flex items-center gap-3 p-3 rounded-2xl
                   border-2 border-slate-200 dark:border-slate-700
                   border-b-[5px] border-b-slate-300 dark:border-b-slate-600
                   bg-white dark:bg-slate-800"
          >
            <div class="w-10 h-10 rounded-full bg-secondary/20 dark:bg-secondary/30
                        flex items-center justify-center font-bold text-secondary flex-shrink-0">
              {{ s.username[0]?.toUpperCase() }}
            </div>
            <div class="min-w-0">
              <div class="text-sm font-semibold text-slate-800 dark:text-slate-100 truncate">
                {{ s.username }}
              </div>
              <div class="text-xs text-gray-400">{{ s.total_xp }} XP</div>
            </div>
          </div>
        </div>
      </div>

    </template>

    <!-- Leave confirmation modal -->
    <div v-if="showLeaveConfirm"
         class="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4"
         @click.self="showLeaveConfirm = false">
      <div class="bg-white dark:bg-slate-800 rounded-3xl border-2 border-slate-200 dark:border-slate-700
                  border-b-[8px] border-b-slate-300 dark:border-b-slate-600
                  p-6 w-full max-w-sm">
        <div class="text-3xl mb-3 text-center">⚠️</div>
        <h3 class="text-lg font-bold text-primary dark:text-white mb-2 text-center">
          {{ d.confirmLeave || 'Opustiť triedu?' }}
        </h3>
        <p class="text-sm text-gray-500 dark:text-gray-400 mb-5 text-center">
          {{ d.leaveClassroomWarning || 'Budeš odhlásený z tejto triedy. Tvoje dáta zostanú zachované.' }}
        </p>
        <div class="flex gap-3">
          <button
            @click="showLeaveConfirm = false"
            class="flex-1 px-4 py-2.5 rounded-2xl font-semibold text-sm
                   border-2 border-slate-200 dark:border-slate-700
                   text-gray-600 dark:text-gray-300
                   hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors"
          >
            {{ d.cancel || 'Zrušiť' }}
          </button>
          <button
            @click="handleLeave"
            class="flex-1 px-4 py-2.5 rounded-2xl font-semibold text-sm
                   bg-accent text-white border-b-4 border-red-700
                   hover:-translate-y-0.5 active:translate-y-0.5 active:border-b-2 transition-all"
          >
            {{ d.leave || 'Opustiť' }}
          </button>
        </div>
      </div>
    </div>

  </div>
</template>
