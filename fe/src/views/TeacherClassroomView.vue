<script setup>
import { ref, reactive, onMounted, computed } from 'vue';
import QRCode from 'qrcode';
import { useAuthStore } from '@/stores/useAuthStore';
import { useRouter } from 'vue-router';
import {
  getClassroomDetail,
  deleteClassroom,
  removeStudentFromClassroom,
  removeTaskFromClassroom,
  updateClassroomTask,
  getClassroomAnalytics,
  getClassroomStudentDetail,
  getClassroomTaskHomeworkStats,
} from '@/api/apiClient';
import { dictionary } from '@/utils/dictionary';
import { useLanguageStore } from '@/stores/useLanguageStore';
import { useToastStore } from '@/stores/useToastStore';
import Spinner from '@/components/Spinner.vue';

const props = defineProps({ classroomId: [String, Number] });

const authStore = useAuthStore();
const router = useRouter();
const langStore = useLanguageStore();
const toastStore = useToastStore();
const d = dictionary[langStore.language];

const classroom = ref(null);
const analytics = ref(null);
const loading = ref(true);
const activeTab = ref('students');
const showDeleteConfirm = ref(false);
const showQr = ref(false);
const qrDataUrl = ref('');

// Student row expansion
const expandedStudents = reactive({});
const studentDetails = reactive({});
const studentDetailsLoading = reactive({});

// Homework task expansion
const expandedTaskStats = reactive({});
const taskHomeworkStats = reactive({});
const taskHomeworkLoading = reactive({});

const joinUrl = computed(() => {
  if (!classroom.value) return '';
  return `${window.location.origin}/join/${classroom.value.code}`;
});

const fetchData = async () => {
  loading.value = true;
  try {
    classroom.value = await getClassroomDetail(props.classroomId, { teacherId: authStore.id });
  } catch (e) {
    console.error('Error fetching classroom:', e);
  }
  loading.value = false;
};

const fetchAnalytics = async () => {
  try {
    analytics.value = await getClassroomAnalytics(props.classroomId, authStore.id);
  } catch (e) {
    console.error('Error fetching analytics:', e);
  }
};

const copyLink = () => {
  navigator.clipboard.writeText(joinUrl.value);
  toastStore.addToast({ message: d.linkCopied || 'Odkaz skopírovaný', type: 'success', visible: true });
};

const copyCode = () => {
  navigator.clipboard.writeText(classroom.value.code);
  toastStore.addToast({ message: d.codeCopied || 'Kód skopírovaný', type: 'success', visible: true });
};

const handleDeleteClassroom = async () => {
  try {
    await deleteClassroom(props.classroomId, authStore.id);
    toastStore.addToast({ message: d.classroomDeleted || 'Trieda vymazaná', type: 'info', visible: true });
    router.push({ name: 'teacher-dashboard' });
  } catch (e) {
    console.error('Error deleting classroom:', e);
  }
};

const handleRemoveStudent = async (studentId) => {
  try {
    await removeStudentFromClassroom(props.classroomId, authStore.id, studentId);
    classroom.value.students = classroom.value.students.filter(s => s.id !== studentId);
    toastStore.addToast({ message: d.studentRemoved || 'Študent odstránený', type: 'info', visible: true });
  } catch (e) {
    console.error('Error removing student:', e);
  }
};

const handleRemoveTask = async (taskId) => {
  try {
    await removeTaskFromClassroom(props.classroomId, taskId, authStore.id);
    classroom.value.task_assignments = classroom.value.task_assignments.filter(t => t.task_id !== taskId);
    toastStore.addToast({ message: d.taskRemoved || 'Úloha odstránená', type: 'info', visible: true });
  } catch (e) {
    console.error('Error removing task:', e);
  }
};

const toggleHomework = async (assignment) => {
  try {
    await updateClassroomTask(props.classroomId, assignment.task_id, authStore.id, {
      is_homework: !assignment.is_homework,
    });
    assignment.is_homework = !assignment.is_homework;
  } catch (e) {
    console.error('Error toggling homework:', e);
  }
};

const toggleStudentExpand = async (student) => {
  expandedStudents[student.id] = !expandedStudents[student.id];
  if (expandedStudents[student.id] && !studentDetails[student.id]) {
    studentDetailsLoading[student.id] = true;
    try {
      studentDetails[student.id] = await getClassroomStudentDetail(
        props.classroomId, student.id, authStore.id,
      );
    } catch (e) {
      studentDetails[student.id] = null;
    }
    studentDetailsLoading[student.id] = false;
  }
};

const toggleTaskStats = async (assignment) => {
  expandedTaskStats[assignment.task_id] = !expandedTaskStats[assignment.task_id];
  if (expandedTaskStats[assignment.task_id] && !taskHomeworkStats[assignment.task_id]) {
    taskHomeworkLoading[assignment.task_id] = true;
    try {
      taskHomeworkStats[assignment.task_id] = await getClassroomTaskHomeworkStats(
        props.classroomId, assignment.task_id, authStore.id,
      );
    } catch (e) {
      taskHomeworkStats[assignment.task_id] = null;
    }
    taskHomeworkLoading[assignment.task_id] = false;
  }
};

const fmtTime = (ms) => {
  if (!ms) return '—';
  return ms < 1000 ? `${ms}ms` : `${(ms / 1000).toFixed(1)}s`;
};

const openQr = async () => {
  if (!qrDataUrl.value) {
    qrDataUrl.value = await QRCode.toDataURL(joinUrl.value, { width: 400, margin: 2 });
  }
  showQr.value = true;
};

const switchTab = (tab) => {
  activeTab.value = tab;
  if (tab === 'analytics' && !analytics.value) {
    fetchAnalytics();
  }
};

onMounted(fetchData);
</script>

<template>
  <div class="pt-24 px-4 max-w-6xl mx-auto">
    <Spinner v-if="loading" />

    <template v-else-if="classroom">
      <!-- Header -->
      <div class="flex flex-col md:flex-row md:items-start justify-between gap-4 mb-6">
        <div>
          <div class="flex items-center gap-2 mb-1">
            <router-link :to="{ name: 'teacher-dashboard' }"
                         class="text-secondary hover:underline text-sm">
              &larr; {{ d.backToDashboard || 'Späť' }}
            </router-link>
          </div>
          <h1 class="text-3xl font-bold text-primary dark:text-white">{{ classroom.name }}</h1>
          <p v-if="classroom.description" class="text-gray-500 dark:text-gray-400 mt-1">
            {{ classroom.description }}
          </p>
        </div>

        <div class="flex flex-col items-end gap-2">
          <div class="flex items-center gap-2">
            <span class="font-mono text-2xl bg-slate-100 dark:bg-slate-700 px-4 py-2 rounded-lg
                         text-slate-800 dark:text-slate-100 tracking-widest select-all cursor-pointer"
                  @click="copyCode" :title="d.clickToCopy || 'Kliknutím skopírujete'">
              {{ classroom.code }}
            </span>
          </div>
          <div class="flex gap-2 text-sm flex-wrap justify-end">
            <button @click="copyLink"
                    class="px-3 py-1 bg-secondary text-white rounded hover:bg-blue-600 transition-colors">
              {{ d.copyLink || 'Kopírovať odkaz' }}
            </button>
            <button @click="openQr"
                    class="px-3 py-1 bg-slate-600 text-white rounded hover:bg-slate-700 transition-colors">
              QR kód
            </button>
            <button @click="showDeleteConfirm = true"
                    class="px-3 py-1 bg-red-500 text-white rounded hover:bg-red-600 transition-colors">
              {{ d.deleteClassroom || 'Vymazať triedu' }}
            </button>
          </div>
        </div>
      </div>

      <!-- Tabs -->
      <div class="flex gap-1 mb-6 border-b border-slate-200 dark:border-slate-700">
        <button v-for="tab in ['students', 'tasks', 'analytics']" :key="tab"
                @click="switchTab(tab)"
                :class="[
                  'px-4 py-2 font-medium text-sm rounded-t-lg transition-colors',
                  activeTab === tab
                    ? 'bg-white dark:bg-slate-800 text-primary dark:text-white border-2 border-b-0 border-slate-200 dark:border-slate-700'
                    : 'text-gray-500 dark:text-gray-400 hover:text-primary dark:hover:text-white'
                ]">
          {{ tab === 'students' ? (d.students || 'Študenti') + ` (${classroom.students.length})`
           : tab === 'tasks' ? (d.assignedTasks || 'Úlohy') + ` (${classroom.task_assignments.length})`
           : (d.analytics || 'Analytika') }}
        </button>
      </div>

      <!-- Students Tab -->
      <div v-if="activeTab === 'students'">
        <div v-if="classroom.students.length === 0"
             class="text-center py-12 text-gray-500 dark:text-gray-400">
          {{ d.noStudentsYet || 'Zatiaľ sa nepripojili žiadni študenti.' }}
        </div>

        <div class="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
          <table class="w-full text-left text-sm">
            <thead>
              <tr class="border-b border-slate-200 dark:border-slate-700 text-gray-500 dark:text-gray-400 text-xs">
                <th class="py-2 px-3 w-6"></th>
                <th class="py-2 px-3">Meno</th>
                <th class="py-2 px-3">Ročník</th>
                <th class="py-2 px-3">XP</th>
                <th class="py-2 px-3">Level</th>
                <th class="py-2 px-3"></th>
              </tr>
            </thead>
            <tbody>
              <template v-for="s in classroom.students" :key="s.id">
                <!-- Main row -->
                <tr class="border-b border-slate-100 dark:border-slate-700/50 hover:bg-slate-50 dark:hover:bg-slate-700/20 cursor-pointer"
                    @click="toggleStudentExpand(s)">
                  <td class="py-3 px-3">
                    <svg class="w-3 h-3 text-slate-400 transition-transform duration-150"
                         :class="expandedStudents[s.id] ? 'rotate-90' : ''"
                         viewBox="0 0 20 20" fill="currentColor">
                      <path fill-rule="evenodd" d="M8.22 5.22a.75.75 0 0 1 1.06 0l4.25 4.25a.75.75 0 0 1 0 1.06l-4.25 4.25a.75.75 0 0 1-1.06-1.06L11.94 10 8.22 6.28a.75.75 0 0 1 0-1.06z" clip-rule="evenodd" />
                    </svg>
                  </td>
                  <td class="py-3 px-3">
                    <router-link :to="{ name: 'teacher-student-detail', params: { classroomId: classroom.id, studentId: s.id } }"
                                 class="text-secondary dark:text-tertiary hover:underline font-medium"
                                 @click.stop>
                      {{ s.username }}
                    </router-link>
                  </td>
                  <td class="py-3 px-3 text-slate-600 dark:text-slate-300">{{ s.grade ? `${s.grade}.` : '-' }}</td>
                  <td class="py-3 px-3 text-slate-600 dark:text-slate-300">{{ s.total_xp }}</td>
                  <td class="py-3 px-3 text-slate-600 dark:text-slate-300">{{ s.level }}</td>
                  <td class="py-3 px-3 text-right" @click.stop>
                    <button @click="handleRemoveStudent(s.id)" class="text-red-500 hover:text-red-700 text-xs">
                      Odstrániť
                    </button>
                  </td>
                </tr>

                <!-- Expanded: per-task stats -->
                <tr v-if="expandedStudents[s.id]" class="border-b border-slate-100 dark:border-slate-700/50">
                  <td colspan="6" class="bg-slate-50 dark:bg-slate-900/40 px-4 py-3">
                    <div v-if="studentDetailsLoading[s.id]" class="flex justify-center py-4">
                      <Spinner />
                    </div>
                    <div v-else-if="!studentDetails[s.id]?.task_progress?.length"
                         class="text-xs text-gray-400 text-center py-2">
                      Žiadna aktivita v priradených úlohách.
                    </div>
                    <table v-else class="w-full text-xs">
                      <thead>
                        <tr class="text-gray-400 border-b border-slate-200 dark:border-slate-700">
                          <th class="py-1.5 pr-4 text-left font-medium">Úloha</th>
                          <th class="py-1.5 px-3 text-right font-medium">✓ Správne</th>
                          <th class="py-1.5 px-3 text-right font-medium">✗ Nesprávne</th>
                          <th class="py-1.5 px-3 text-right font-medium">Ø čas</th>
                          <th class="py-1.5 pl-3 text-right font-medium">Dokončenie</th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr v-for="t in studentDetails[s.id].task_progress" :key="t.task_id"
                            class="border-b border-slate-100 dark:border-slate-700/30 last:border-0">
                          <td class="py-1.5 pr-4 text-slate-700 dark:text-slate-300">{{ t.task_name }}</td>
                          <td class="py-1.5 px-3 text-right text-green-600 dark:text-green-400 font-medium">{{ t.correct }}</td>
                          <td class="py-1.5 px-3 text-right text-red-500 dark:text-red-400">{{ t.incorrect }}</td>
                          <td class="py-1.5 px-3 text-right text-slate-500 dark:text-slate-400">{{ fmtTime(t.avg_time_ms) }}</td>
                          <td class="py-1.5 pl-3 text-right font-medium"
                              :class="t.completion >= 100 ? 'text-green-600' : t.completion > 0 ? 'text-amber-500' : 'text-gray-400'">
                            {{ t.completion }}%
                          </td>
                        </tr>
                      </tbody>
                    </table>
                    <div class="mt-2 text-right">
                      <router-link :to="{ name: 'teacher-student-detail', params: { classroomId: classroom.id, studentId: s.id } }"
                                   class="text-xs text-secondary dark:text-tertiary hover:underline">
                        Zobraziť detail →
                      </router-link>
                    </div>
                  </td>
                </tr>
              </template>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Tasks Tab -->
      <div v-if="activeTab === 'tasks'">
        <div class="flex flex-wrap gap-2 justify-end mb-4">
          <router-link :to="{ name: 'teacher-task-sets', params: { classroomId: classroom.id } }"
                       class="px-4 py-2 bg-secondary text-white rounded-lg hover:bg-blue-600 font-semibold text-sm">
            + Príkladové sady
          </router-link>
          <router-link :to="{ name: 'teacher-classroom-student-view', params: { classroomId: classroom.id } }"
                       class="px-4 py-2 bg-slate-500 text-white rounded-lg hover:bg-slate-600 font-semibold text-sm">
            Pohľad žiaka
          </router-link>
        </div>

        <div v-if="classroom.task_assignments.length === 0"
             class="text-center py-12 text-gray-500 dark:text-gray-400">
          {{ d.noTasksAssigned || 'Žiadne úlohy nie sú priradené.' }}
        </div>

        <div v-else class="space-y-2">
          <div v-for="a in classroom.task_assignments" :key="a.id"
               class="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
            <!-- Task row -->
            <div class="flex items-center gap-3 p-4 cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-700/20"
                 @click="toggleTaskStats(a)">
              <svg class="w-3.5 h-3.5 text-slate-400 flex-shrink-0 transition-transform duration-150"
                   :class="expandedTaskStats[a.task_id] ? 'rotate-90' : ''"
                   viewBox="0 0 20 20" fill="currentColor">
                <path fill-rule="evenodd" d="M8.22 5.22a.75.75 0 0 1 1.06 0l4.25 4.25a.75.75 0 0 1 0 1.06l-4.25 4.25a.75.75 0 0 1-1.06-1.06L11.94 10 8.22 6.28a.75.75 0 0 1 0-1.06z" clip-rule="evenodd" />
              </svg>
              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2">
                  <router-link :to="{ name: 'taskDetail', params: { taskId: a.task_id } }"
                               class="font-medium text-slate-800 dark:text-slate-100 hover:text-secondary"
                               @click.stop>
                    {{ a.task_name }}
                  </router-link>
                  <span v-if="a.is_homework"
                        class="text-xs bg-amber-100 dark:bg-amber-900 text-amber-800 dark:text-amber-200
                               px-2 py-0.5 rounded-full font-medium">
                    DÚ
                  </span>
                </div>
                <div class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                  {{ a.example_count }} príkladov
                  <span v-if="a.grade_levels?.length">
                    &middot; {{ a.grade_levels.map(g => g + '.').join(', ') }} roč.
                  </span>
                  <span v-if="a.due_date">
                    &middot; Termín: {{ new Date(a.due_date).toLocaleDateString('sk-SK') }}
                  </span>
                </div>
              </div>
              <div class="flex items-center gap-2 flex-shrink-0" @click.stop>
                <button @click="toggleHomework(a)"
                        :class="[
                          'text-xs px-3 py-1 rounded border transition-colors',
                          a.is_homework
                            ? 'border-amber-400 text-amber-700 dark:text-amber-300 hover:bg-amber-50 dark:hover:bg-amber-900/30'
                            : 'border-slate-300 dark:border-slate-600 text-slate-500 hover:bg-slate-50 dark:hover:bg-slate-700'
                        ]">
                  {{ a.is_homework ? 'Zrušiť DÚ' : 'Označiť DÚ' }}
                </button>
                <button @click="handleRemoveTask(a.task_id)" class="text-red-500 hover:text-red-700 text-sm font-bold">
                  &times;
                </button>
              </div>
            </div>

            <!-- Expanded: student completion stats -->
            <div v-if="expandedTaskStats[a.task_id]"
                 class="border-t border-slate-100 dark:border-slate-700 bg-slate-50 dark:bg-slate-900/40 px-4 py-3">
              <div v-if="taskHomeworkLoading[a.task_id]" class="flex justify-center py-4">
                <Spinner />
              </div>
              <div v-else-if="!taskHomeworkStats[a.task_id]" class="text-xs text-gray-400 text-center py-2">
                Chyba pri načítaní.
              </div>
              <template v-else>
                <div class="flex items-center gap-4 mb-3 text-xs text-gray-500 dark:text-gray-400">
                  <span>{{ taskHomeworkStats[a.task_id].completed_count }}/{{ taskHomeworkStats[a.task_id].total_students }} dokončilo</span>
                  <span v-if="a.due_date">Termín: {{ new Date(a.due_date).toLocaleDateString('sk-SK') }}</span>
                </div>
                <div class="grid grid-cols-[1fr_auto_auto_auto] gap-x-4 text-xs text-gray-400 font-medium mb-1 px-1">
                  <span>Žiak</span>
                  <span class="text-right">Vyriešených</span>
                  <span class="text-right">Dokončil</span>
                  <span class="text-right">Načas</span>
                </div>
                <div v-for="st in taskHomeworkStats[a.task_id].students" :key="st.student_id"
                     class="grid grid-cols-[1fr_auto_auto_auto] gap-x-4 text-xs py-1.5 px-1
                            border-t border-slate-100 dark:border-slate-700/30 items-center">
                  <span class="text-slate-700 dark:text-slate-300">{{ st.username }}</span>
                  <span class="text-right text-slate-500 dark:text-slate-400">{{ st.solved }}/{{ st.total }}</span>
                  <span class="text-right font-medium" :class="st.completed ? 'text-green-500' : 'text-gray-400'">
                    {{ st.completed ? 'Áno' : 'Nie' }}
                  </span>
                  <span class="text-right font-medium"
                        :class="st.on_time === null ? 'text-gray-400' : st.on_time ? 'text-green-500' : 'text-red-400'">
                    {{ st.on_time === null ? '—' : st.on_time ? 'Načas' : 'Neskoro' }}
                  </span>
                </div>
              </template>
            </div>
          </div>
        </div>
      </div>

      <!-- Analytics Tab -->
      <div v-if="activeTab === 'analytics'">
        <Spinner v-if="!analytics" />

        <template v-else>
          <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
            <div class="bg-white dark:bg-slate-800 rounded-lg p-4 border border-slate-200 dark:border-slate-700 text-center">
              <div class="text-2xl font-bold text-primary dark:text-white">{{ analytics.total_students }}</div>
              <div class="text-xs text-gray-500 dark:text-gray-400">{{ d.totalStudents || 'Celkom študentov' }}</div>
            </div>
            <div class="bg-white dark:bg-slate-800 rounded-lg p-4 border border-slate-200 dark:border-slate-700 text-center">
              <div class="text-2xl font-bold text-green-600 dark:text-green-400">{{ analytics.active_students }}</div>
              <div class="text-xs text-gray-500 dark:text-gray-400">{{ d.activeStudents || 'Aktívnych (7 dní)' }}</div>
            </div>
            <div class="bg-white dark:bg-slate-800 rounded-lg p-4 border border-slate-200 dark:border-slate-700 text-center">
              <div class="text-2xl font-bold text-secondary">{{ analytics.total_examples }}</div>
              <div class="text-xs text-gray-500 dark:text-gray-400">{{ d.totalExamples || 'Riešených príkladov' }}</div>
            </div>
            <div class="bg-white dark:bg-slate-800 rounded-lg p-4 border border-slate-200 dark:border-slate-700 text-center">
              <div class="text-2xl font-bold text-amber-600 dark:text-amber-400">{{ analytics.avg_accuracy }}%</div>
              <div class="text-xs text-gray-500 dark:text-gray-400">{{ d.avgAccuracy || 'Priemerná úspešnosť' }}</div>
            </div>
          </div>

          <h3 class="text-lg font-semibold text-slate-800 dark:text-slate-100 mb-3">
            {{ d.studentRanking || 'Prehľad študentov' }}
          </h3>

          <div class="overflow-x-auto">
            <table class="w-full text-left text-sm">
              <thead>
                <tr class="border-b border-slate-200 dark:border-slate-700 text-gray-500 dark:text-gray-400">
                  <th class="py-2 px-3">{{ d.username || 'Meno' }}</th>
                  <th class="py-2 px-3">{{ d.examplesPracticed || 'Príkladov' }}</th>
                  <th class="py-2 px-3">{{ d.accuracy || 'Úspešnosť' }}</th>
                  <th class="py-2 px-3">{{ d.mastery || 'Mastery' }}</th>
                  <th class="py-2 px-3">XP</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="s in analytics.student_summaries" :key="s.id"
                    class="border-b border-slate-100 dark:border-slate-700/50">
                  <td class="py-2 px-3">
                    <router-link :to="{ name: 'teacher-student-detail', params: { classroomId, studentId: s.id } }"
                                 class="text-secondary dark:text-tertiary hover:underline">
                      {{ s.username }}
                    </router-link>
                  </td>
                  <td class="py-2 px-3 text-slate-700 dark:text-slate-300">{{ s.examples_practiced }}</td>
                  <td class="py-2 px-3 text-slate-700 dark:text-slate-300">{{ s.accuracy }}%</td>
                  <td class="py-2 px-3 text-slate-700 dark:text-slate-300">{{ s.avg_mastery }}%</td>
                  <td class="py-2 px-3 text-slate-700 dark:text-slate-300">{{ s.total_xp }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </template>
      </div>
    </template>

    <!-- QR Code fullscreen -->
    <div v-if="showQr"
         class="fixed inset-0 bg-black flex flex-col items-center justify-center z-50 cursor-pointer"
         @click="showQr = false">
      <img v-if="qrDataUrl" :src="qrDataUrl" class="w-72 h-72 sm:w-96 sm:h-96" alt="QR kód" />
      <p class="text-white text-xl font-bold mt-6 tracking-widest">{{ classroom?.code }}</p>
      <p class="text-slate-400 text-sm mt-2">Kliknutím zavriete</p>
    </div>

    <!-- Delete confirmation -->
    <div v-if="showDeleteConfirm"
         class="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
         @click.self="showDeleteConfirm = false">
      <div class="bg-white dark:bg-slate-800 rounded-xl p-6 w-full max-w-sm shadow-xl">
        <h3 class="text-lg font-bold text-red-600 mb-2">{{ d.confirmDelete || 'Naozaj vymazať?' }}</h3>
        <p class="text-sm text-gray-600 dark:text-gray-400 mb-4">
          {{ d.deleteClassroomWarning || 'Táto akcia vymaže triedu a všetky priradenia. Neodstráni úlohy ani študentov.' }}
        </p>
        <div class="flex gap-3 justify-end">
          <button @click="showDeleteConfirm = false"
                  class="px-4 py-2 rounded-md text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-slate-700">
            {{ d.cancel || 'Zrušiť' }}
          </button>
          <button @click="handleDeleteClassroom"
                  class="px-4 py-2 bg-red-500 text-white rounded-md hover:bg-red-600 font-semibold">
            {{ d.delete || 'Vymazať' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
