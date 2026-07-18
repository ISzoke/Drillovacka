<script setup>
import { ref, onMounted } from 'vue';
import { useAuthStore } from '@/stores/useAuthStore';
import { useToastStore } from '@/stores/useToastStore';
import {
  teacherBulkCreateTask, teacherBulkAddToTask, getTeacherClassrooms, assignTaskToClassroom,
} from '@/api/apiClient';

const props = defineProps({
  exampleIds: { type: Array, required: true },
  myTasks: { type: Array, required: true },
  defaultHomework: { type: Boolean, default: false },
});
const emit = defineEmits(['close', 'success']);

const authStore = useAuthStore();
const toastStore = useToastStore();

const destination = ref('new'); // 'new' | 'existing'
const newTaskName = ref('');
const existingTaskId = ref(null);

const assignHomework = ref(props.defaultHomework);
const classrooms = ref([]);
const classroomsLoading = ref(true);
const classroomId = ref(null);
const dueDate = ref('');

const submitting = ref(false);

onMounted(async () => {
  try {
    classrooms.value = await getTeacherClassrooms(authStore.id);
    if (classrooms.value.length) classroomId.value = classrooms.value[0].id;
  } catch (e) {
    classrooms.value = [];
  }
  classroomsLoading.value = false;
});

const submit = async () => {
  if (destination.value === 'new' && !newTaskName.value.trim()) {
    toastStore.addToast({ message: 'Zadaj názov sady.', type: 'error', visible: true });
    return;
  }
  if (destination.value === 'existing' && !existingTaskId.value) {
    toastStore.addToast({ message: 'Vyber existujúcu sadu.', type: 'error', visible: true });
    return;
  }
  if (assignHomework.value && !classroomId.value) {
    toastStore.addToast({ message: 'Vyber triedu.', type: 'error', visible: true });
    return;
  }

  submitting.value = true;
  try {
    const taskResult = destination.value === 'new'
      ? await teacherBulkCreateTask(authStore.id, props.exampleIds, newTaskName.value.trim())
      : await teacherBulkAddToTask(authStore.id, props.exampleIds, existingTaskId.value);

    let homeworkFailed = false;
    if (assignHomework.value) {
      try {
        await assignTaskToClassroom(classroomId.value, authStore.id, taskResult.task_id, true, dueDate.value || null);
      } catch (e) {
        homeworkFailed = true;
      }
    }

    if (homeworkFailed) {
      toastStore.addToast({
        message: `Sada "${taskResult.task_name}" vytvorená, ale priradenie ako DÚ zlyhalo. Skús to znova v prehľade triedy.`,
        type: 'error', visible: true,
      });
    } else {
      toastStore.addToast({
        message: assignHomework.value
          ? `Sada "${taskResult.task_name}" vytvorená a priradená ako DÚ.`
          : `Príklady pridané do sady "${taskResult.task_name}".`,
        type: 'success', visible: true,
      });
    }
    emit('success', taskResult);
  } catch (e) {
    toastStore.addToast({ message: 'Chyba pri organizovaní príkladov.', type: 'error', visible: true });
  }
  submitting.value = false;
};
</script>

<template>
  <div class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" @click.self="emit('close')">
    <div class="bg-white dark:bg-slate-800 rounded-xl p-6 w-full max-w-sm shadow-xl">
      <h3 class="text-lg font-bold text-slate-800 dark:text-slate-100 mb-1">
        Organizovať {{ exampleIds.length }} príkladov
      </h3>
      <p class="text-sm text-gray-500 dark:text-gray-400 mb-4">Kam ich chceš zaradiť?</p>

      <div class="flex gap-2 mb-4">
        <button @click="destination = 'new'"
                :class="['flex-1 py-2 rounded-lg text-sm font-semibold transition-all',
                         destination === 'new' ? 'bg-secondary text-white' : 'bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300']">
          Nová sada
        </button>
        <button @click="destination = 'existing'" :disabled="!myTasks.length"
                :class="['flex-1 py-2 rounded-lg text-sm font-semibold transition-all disabled:opacity-40',
                         destination === 'existing' ? 'bg-secondary text-white' : 'bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300']">
          Existujúca sada
        </button>
      </div>

      <input v-if="destination === 'new'" v-model="newTaskName" type="text"
             :placeholder="`Sada z ${exampleIds.length} príkladov`"
             class="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-600
                    bg-white dark:bg-slate-700 text-slate-800 dark:text-slate-100 mb-4
                    focus:outline-none focus:ring-2 focus:ring-secondary" />
      <select v-else v-model="existingTaskId"
              class="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-600
                     bg-white dark:bg-slate-700 text-slate-800 dark:text-slate-100 mb-4
                     focus:outline-none focus:ring-2 focus:ring-secondary">
        <option :value="null" disabled>Vyber sadu…</option>
        <option v-for="t in myTasks" :key="t.id" :value="t.id">{{ t.name }}</option>
      </select>

      <label class="flex items-center gap-3 mb-3 cursor-pointer">
        <input type="checkbox" v-model="assignHomework" class="w-4 h-4 accent-secondary" />
        <span class="text-sm text-slate-700 dark:text-slate-300">Priradiť ako domácu úlohu triede</span>
      </label>

      <div v-if="assignHomework" class="space-y-3 mb-4 pl-1">
        <div v-if="classroomsLoading" class="text-xs text-gray-400">Načítavam triedy…</div>
        <div v-else-if="!classrooms.length" class="text-xs text-gray-400">Nemáš žiadne triedy.</div>
        <select v-else v-model="classroomId"
                class="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-600
                       bg-white dark:bg-slate-700 text-slate-800 dark:text-slate-100
                       focus:outline-none focus:ring-2 focus:ring-secondary">
          <option v-for="c in classrooms" :key="c.id" :value="c.id">{{ c.name }}</option>
        </select>
        <div>
          <label class="block text-sm text-slate-700 dark:text-slate-300 mb-1">Termín odovzdania</label>
          <input type="date" v-model="dueDate"
                 class="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-600
                        bg-white dark:bg-slate-700 text-slate-800 dark:text-slate-100
                        focus:outline-none focus:ring-2 focus:ring-secondary" />
        </div>
      </div>

      <div class="flex gap-3 justify-end">
        <button @click="emit('close')" class="px-4 py-2 rounded-md text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-slate-700">
          Zrušiť
        </button>
        <button @click="submit" :disabled="submitting"
                class="px-4 py-2 bg-secondary text-white rounded-md hover:bg-blue-600 font-semibold disabled:opacity-50">
          {{ submitting ? '...' : 'Potvrdiť' }}
        </button>
      </div>
    </div>
  </div>
</template>
