<script setup>
import { ref, onMounted, reactive } from 'vue';
import { getAllTeachers, publishTeacherTask, getAdminTaskExamples, getAdminClassroomStudents } from '@/api/apiClient';
import Spinner from '@/components/Spinner.vue';

const teachers = ref([]);
const loading = ref(true);
const error = ref(null);
const expandedTeacher = ref({});
const expandedClassroom = ref({});

// Classroom students lazy load
const expandedStudents = reactive({});
const classroomStudents = reactive({});
const classroomStudentsLoading = reactive({});

const toggleStudentList = async (classroom) => {
  const id = classroom.id;
  expandedStudents[id] = !expandedStudents[id];
  if (expandedStudents[id] && classroomStudents[id] === undefined) {
    classroomStudentsLoading[id] = true;
    try {
      classroomStudents[id] = await getAdminClassroomStudents(id);
    } catch (e) {
      classroomStudents[id] = [];
    }
    classroomStudentsLoading[id] = false;
  }
};

// Task examples lazy load
const expandedTask = reactive({});
const taskExamples = reactive({});
const taskExamplesLoading = reactive({});

const toggleTaskPreview = async (task) => {
  const id = task.id;
  expandedTask[id] = !expandedTask[id];
  if (expandedTask[id] && taskExamples[id] === undefined) {
    taskExamplesLoading[id] = true;
    try {
      taskExamples[id] = await getAdminTaskExamples(id);
    } catch (e) {
      taskExamples[id] = [];
    }
    taskExamplesLoading[id] = false;
  }
};

// Publish modal
const publishModal = ref(null); // { task }
const publishGrades = ref([]);
const publishing = ref(false);
const publishedTasks = ref(new Set());

const openPublish = (task) => {
  publishModal.value = task;
  publishGrades.value = task.grade_levels?.length ? [...task.grade_levels] : [];
};

const confirmPublish = async () => {
  if (!publishModal.value) return;
  publishing.value = true;
  try {
    await publishTeacherTask(publishModal.value.id, publishGrades.value);
    publishedTasks.value.add(publishModal.value.id);
    publishModal.value = null;
  } catch (e) {
    console.error(e);
  }
  publishing.value = false;
};

const load = async () => {
  loading.value = true;
  error.value = null;
  try {
    teachers.value = await getAllTeachers();
  } catch (e) {
    error.value = String(e);
  }
  loading.value = false;
};

onMounted(load);

const fmt = (iso) => {
  if (!iso) return '—';
  return new Date(iso).toLocaleDateString('sk-SK');
};

const studentLabel = (n) => {
  if (n === 1) return '1 študent';
  if (n >= 2 && n <= 4) return `${n} študenti`;
  return `${n} študentov`;
};
</script>

<template>
  <div class="pt-24 px-4 max-w-5xl mx-auto">
    <div class="flex items-center justify-between mb-6">
      <h1 class="text-2xl font-bold text-slate-800 dark:text-slate-100">
        Učiteľské účty
        <span v-if="!loading" class="text-base font-normal text-slate-400 ml-2">({{ teachers.length }})</span>
      </h1>
      <button @click="load"
              class="px-4 py-1.5 bg-secondary text-white rounded-lg text-sm hover:bg-blue-600">
        Obnoviť
      </button>
    </div>

    <Spinner v-if="loading" />
    <p v-else-if="error" class="text-red-500">{{ error }}</p>

    <div v-else class="space-y-3">
      <div v-for="t in teachers" :key="t.id"
           class="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">

        <!-- Teacher row -->
        <div class="flex items-center gap-4 px-5 py-4 cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-700/30"
             @click="expandedTeacher[t.id] = !expandedTeacher[t.id]">
          <svg class="w-3.5 h-3.5 text-slate-400 flex-shrink-0 transition-transform duration-150"
               :class="expandedTeacher[t.id] ? 'rotate-90' : ''"
               viewBox="0 0 20 20" fill="currentColor">
            <path fill-rule="evenodd" d="M8.22 5.22a.75.75 0 0 1 1.06 0l4.25 4.25a.75.75 0 0 1 0 1.06l-4.25 4.25a.75.75 0 0 1-1.06-1.06L11.94 10 8.22 6.28a.75.75 0 0 1 0-1.06z" clip-rule="evenodd" />
          </svg>
          <div class="flex-1 min-w-0">
            <p class="font-semibold text-slate-800 dark:text-slate-100">
              {{ t.first_name }} {{ t.last_name }}
            </p>
            <p class="text-sm text-slate-500 dark:text-slate-400">{{ t.email }}</p>
          </div>
          <div class="flex items-center gap-6 text-sm flex-shrink-0">
            <div class="text-center">
              <div class="font-bold text-slate-700 dark:text-slate-200">{{ t.classroom_count }}</div>
              <div class="text-xs text-slate-400">tried</div>
            </div>
            <div class="text-center">
              <div class="font-bold text-slate-700 dark:text-slate-200">{{ t.student_count }}</div>
              <div class="text-xs text-slate-400">žiakov</div>
            </div>
            <div class="text-xs text-slate-400">{{ fmt(t.created_at) }}</div>
          </div>
        </div>

        <!-- Classrooms -->
        <div v-if="expandedTeacher[t.id]"
             class="border-t border-slate-100 dark:border-slate-700">

          <div v-if="!t.classrooms?.length"
               class="px-5 py-3 text-sm text-slate-400">
            Žiadne triedy.
          </div>

          <div v-for="c in (t.classrooms || [])" :key="c.id"
               class="border-b border-slate-100 dark:border-slate-700 last:border-b-0">

            <!-- Classroom row -->
            <div class="flex items-center gap-3 px-6 py-3 cursor-pointer
                        bg-slate-50 dark:bg-slate-900/30
                        hover:bg-slate-100 dark:hover:bg-slate-700/40"
                 @click="expandedClassroom[c.id] = !expandedClassroom[c.id]">
              <svg class="w-3 h-3 text-slate-400 flex-shrink-0 transition-transform duration-150"
                   :class="expandedClassroom[c.id] ? 'rotate-90' : ''"
                   viewBox="0 0 20 20" fill="currentColor">
                <path fill-rule="evenodd" d="M8.22 5.22a.75.75 0 0 1 1.06 0l4.25 4.25a.75.75 0 0 1 0 1.06l-4.25 4.25a.75.75 0 0 1-1.06-1.06L11.94 10 8.22 6.28a.75.75 0 0 1 0-1.06z" clip-rule="evenodd" />
              </svg>
              <span class="font-medium text-slate-700 dark:text-slate-200 flex-1">{{ c.name }}</span>
              <button class="text-xs text-secondary hover:underline flex-shrink-0"
                      @click.stop="toggleStudentList(c)">
                {{ studentLabel(c.student_count) }}
                <span class="ml-0.5">{{ expandedStudents[c.id] ? '▲' : '▼' }}</span>
              </button>
              <span class="text-xs text-slate-400 ml-3">{{ c.tasks?.length ?? 0 }} sád</span>
            </div>

            <!-- Student list -->
            <div v-if="expandedStudents[c.id]"
                 class="px-10 py-2 bg-slate-50 dark:bg-slate-900/50 border-t border-slate-100 dark:border-slate-700">
              <div v-if="classroomStudentsLoading[c.id]" class="text-xs text-slate-400 py-1">Načítavam...</div>
              <div v-else-if="!classroomStudents[c.id]?.length" class="text-xs text-slate-400 py-1">Žiadni študenti.</div>
              <div v-else class="flex flex-wrap gap-2 py-1">
                <span v-for="s in classroomStudents[c.id]" :key="s.id"
                      class="text-xs bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600
                             text-slate-700 dark:text-slate-300 px-2 py-1 rounded-lg">
                  {{ s.username }}
                </span>
              </div>
            </div>

            <!-- Tasks -->
            <div v-if="expandedClassroom[c.id]" class="px-8 py-2 bg-white dark:bg-slate-800">
              <div v-if="!c.tasks?.length" class="text-sm text-slate-400 py-2">
                Žiadne priradené sady.
              </div>
              <div v-else class="divide-y divide-slate-100 dark:divide-slate-700">
                <div v-for="task in (c.tasks || [])" :key="task.id">
                  <!-- Task header row -->
                  <div class="flex items-center justify-between py-2 cursor-pointer"
                       @click="toggleTaskPreview(task)">
                    <div class="flex items-center gap-2 min-w-0">
                      <svg class="w-3 h-3 text-slate-400 flex-shrink-0 transition-transform duration-150"
                           :class="expandedTask[task.id] ? 'rotate-90' : ''"
                           viewBox="0 0 20 20" fill="currentColor">
                        <path fill-rule="evenodd" d="M8.22 5.22a.75.75 0 0 1 1.06 0l4.25 4.25a.75.75 0 0 1 0 1.06l-4.25 4.25a.75.75 0 0 1-1.06-1.06L11.94 10 8.22 6.28a.75.75 0 0 1 0-1.06z" clip-rule="evenodd" />
                      </svg>
                      <span class="text-sm text-slate-700 dark:text-slate-300 truncate">{{ task.name }}</span>
                      <span v-if="task.is_homework"
                            class="text-xs bg-amber-100 dark:bg-amber-900 text-amber-700 dark:text-amber-300
                                   px-1.5 py-0.5 rounded-full flex-shrink-0">DÚ</span>
                      <span v-if="publishedTasks.has(task.id)"
                            class="text-xs bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-300
                                   px-1.5 py-0.5 rounded-full flex-shrink-0">✓ Zverejnená</span>
                    </div>
                    <div class="flex items-center gap-3 flex-shrink-0 ml-3" @click.stop>
                      <span class="text-xs text-slate-400">{{ fmt(task.assigned_at) }}</span>
                      <button v-if="!publishedTasks.has(task.id)"
                              @click="openPublish(task)"
                              class="text-xs px-2 py-1 bg-secondary text-white rounded hover:bg-blue-600 whitespace-nowrap">
                        + Do okruhov
                      </button>
                    </div>
                  </div>

                  <!-- Task detail (prompt + examples) -->
                  <div v-if="expandedTask[task.id]"
                       class="ml-5 mb-2 space-y-2">

                    <!-- AI generation prompt block -->
                    <div v-if="task.generation_prompt"
                         class="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-700
                                rounded-lg p-3">
                      <p class="text-xs font-semibold text-amber-700 dark:text-amber-400 mb-1">
                        Prompt učiteľa (AI generovanie)
                      </p>
                      <p class="text-sm text-slate-800 dark:text-slate-200 whitespace-pre-wrap">{{ task.generation_prompt }}</p>
                      <div v-if="task.generation_params" class="mt-2 flex flex-wrap gap-2">
                        <template v-if="task.generation_params.is_mix">
                          <span class="text-xs bg-amber-100 dark:bg-amber-800 text-amber-700 dark:text-amber-300
                                       px-2 py-0.5 rounded-full">Mix</span>
                          <span v-for="(seg, si) in task.generation_params.segments" :key="si"
                                class="text-xs bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300
                                       px-2 py-0.5 rounded-full">
                            {{ seg.type }} × {{ seg.count }}
                          </span>
                        </template>
                        <template v-else>
                          <span class="text-xs bg-amber-100 dark:bg-amber-800 text-amber-700 dark:text-amber-300
                                       px-2 py-0.5 rounded-full">{{ task.generation_params.type }}</span>
                          <span class="text-xs bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300
                                       px-2 py-0.5 rounded-full">{{ task.generation_params.count }} príkladov</span>
                        </template>
                      </div>
                    </div>

                    <!-- Examples list -->
                    <div class="bg-slate-50 dark:bg-slate-900/50 rounded-lg p-3">
                      <div v-if="taskExamplesLoading[task.id]" class="text-xs text-slate-400 py-1">
                        Načítavam...
                      </div>
                      <div v-else-if="!taskExamples[task.id]?.length" class="text-xs text-slate-400 py-1">
                        Žiadne príklady.
                      </div>
                      <div v-else class="space-y-1.5">
                        <div v-for="ex in taskExamples[task.id]" :key="ex.id"
                             class="flex items-baseline gap-2 text-sm">
                          <span class="text-slate-700 dark:text-slate-300 font-mono">{{ ex.example }}</span>
                          <span class="text-slate-400 text-xs">→</span>
                          <span class="text-green-700 dark:text-green-400 font-semibold font-mono">
                            {{ ex.answers.join(' / ') }}
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

          </div>
        </div>

      </div>

      <p v-if="teachers.length === 0" class="text-center py-12 text-slate-400">
        Žiadni učitelia.
      </p>
    </div>

    <!-- Publish modal -->
    <div v-if="publishModal"
         class="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
         @click.self="publishModal = null">
      <div class="bg-white dark:bg-slate-800 rounded-xl p-6 w-full max-w-sm shadow-xl">
        <h3 class="text-lg font-bold text-slate-800 dark:text-slate-100 mb-1">Zverejniť sadu</h3>
        <p class="text-sm text-slate-500 dark:text-slate-400 mb-4">
          {{ publishModal.name }}
        </p>

        <p class="text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">Vyber ročníky:</p>
        <div class="grid grid-cols-5 gap-2 mb-5">
          <label v-for="g in [1,2,3,4,5,6,7,8,9]" :key="g"
                 class="flex flex-col items-center gap-1 cursor-pointer">
            <input type="checkbox" :value="g" v-model="publishGrades"
                   class="w-4 h-4 accent-secondary" />
            <span class="text-xs text-slate-600 dark:text-slate-400">{{ g }}.</span>
          </label>
        </div>

        <div class="flex gap-3 justify-end">
          <button @click="publishModal = null"
                  class="px-4 py-2 rounded-md text-gray-600 dark:text-gray-300
                         hover:bg-gray-100 dark:hover:bg-slate-700">
            Zrušiť
          </button>
          <button @click="confirmPublish" :disabled="publishing || publishGrades.length === 0"
                  class="px-4 py-2 bg-secondary text-white rounded-md hover:bg-blue-600
                         font-semibold disabled:opacity-50">
            {{ publishing ? '...' : 'Zverejniť' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
