<script setup>
import { ref, onMounted } from 'vue';
import { useAuthStore } from '@/stores/useAuthStore';
import { getTeacherClassrooms, createClassroom } from '@/api/apiClient';
import { dictionary } from '@/utils/dictionary';
import { useLanguageStore } from '@/stores/useLanguageStore';
import { useToastStore } from '@/stores/useToastStore';
import Spinner from '@/components/Spinner.vue';
import TeacherIcon from '@/components/TeacherIcon.vue';

const authStore = useAuthStore();
const langStore = useLanguageStore();
const toastStore = useToastStore();
const d = dictionary[langStore.language];

const classrooms = ref([]);
const loading = ref(true);

// Create classroom modal
const showCreateModal = ref(false);
const newName = ref('');
const newDescription = ref('');
const creating = ref(false);

const fetchClassrooms = async () => {
  loading.value = true;
  try {
    classrooms.value = await getTeacherClassrooms(authStore.id);
  } catch (e) {
    console.error('Error fetching classrooms:', e);
  }
  loading.value = false;
};

const handleCreate = async () => {
  if (!newName.value.trim()) return;
  creating.value = true;
  try {
    const created = await createClassroom(authStore.id, newName.value.trim(), newDescription.value.trim());
    classrooms.value.unshift(created);
    showCreateModal.value = false;
    newName.value = '';
    newDescription.value = '';
    toastStore.addToast({ message: d.classroomCreated || 'Trieda vytvorená', type: 'success', visible: true });
  } catch (e) {
    console.error('Error creating classroom:', e);
  }
  creating.value = false;
};

onMounted(fetchClassrooms);

const studentLabel = (count) => {
  if (count === 1) return '1 študent';
  if (count >= 2 && count <= 4) return `${count} študenti`;
  return `${count} študentov`;
};
</script>

<template>
  <div class="pt-24 px-4 max-w-5xl mx-auto">
    <div class="flex items-start justify-between mb-8 gap-4">
      <div>
        <h1 class="text-3xl font-bold text-primary dark:text-slate-100">
          {{ d.teacherDashboard || 'Vaše triedy' }}
        </h1>
        <p class="text-sm text-gray-500 dark:text-gray-400 mt-1">
          Knižnicu vlastných sád a príkladov nájdeš v navigácii hore.
        </p>
      </div>
      <button @click="showCreateModal = true"
              class="flex items-center gap-1.5 px-4 py-2 bg-secondary text-white rounded-full hover:bg-blue-600
                     font-semibold transition-colors flex-shrink-0">
        <TeacherIcon name="plus" :size="14" /> {{ d.createClassroom || 'Vytvoriť triedu' }}
      </button>
    </div>

    <Spinner v-if="loading" />

    <div v-else-if="classrooms.length === 0"
         class="text-center text-gray-500 dark:text-gray-400 py-16 text-lg">
      {{ d.noClassrooms || 'Zatiaľ nemáte žiadne triedy. Vytvorte prvú!' }}
    </div>

    <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      <router-link v-for="c in classrooms" :key="c.id"
                   :to="{ name: 'teacher-classroom', params: { classroomId: c.id } }"
                   class="block p-6 bg-white dark:bg-slate-800 rounded-xl shadow-md
                          border-2 border-slate-200 dark:border-slate-700
                          hover:border-secondary dark:hover:border-secondary transition-colors">
        <h3 class="text-xl font-bold text-slate-800 dark:text-slate-100 mb-2">{{ c.name }}</h3>
        <p v-if="c.description" class="text-sm text-gray-500 dark:text-gray-400 mb-3 line-clamp-2">
          {{ c.description }}
        </p>
        <div class="flex items-center justify-between text-sm text-gray-600 dark:text-gray-400">
          <span class="font-mono bg-tertiary/50 dark:bg-tertiary/20 text-primary dark:text-tertiary px-2 py-1 rounded-md text-xs font-semibold">
            {{ c.code }}
          </span>
          <span class="flex items-center gap-1 text-xs">
            <TeacherIcon name="person" :size="12" /> {{ studentLabel(c.student_count) }}
          </span>
        </div>
      </router-link>
    </div>

    <!-- Create modal -->
    <div v-if="showCreateModal"
         class="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
         @click.self="showCreateModal = false">
      <div class="bg-white dark:bg-slate-800 rounded-xl p-6 w-full max-w-md shadow-xl">
        <h2 class="text-xl font-bold text-primary dark:text-slate-100 mb-4">
          {{ d.createClassroom || 'Vytvoriť triedu' }}
        </h2>

        <div class="mb-4">
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            {{ d.classroomName || 'Názov triedy' }} *
          </label>
          <input v-model="newName" type="text"
                 :placeholder="d.classroomNamePlaceholder || 'napr. 5.A Matematika'"
                 class="w-full px-4 py-2 border border-gray-300 dark:border-slate-600 rounded-md
                        bg-white dark:bg-slate-700 text-slate-800 dark:text-slate-100
                        focus:outline-none focus:ring-2 focus:ring-blue-500" />
        </div>

        <div class="mb-6">
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            {{ d.classroomDescription || 'Popis' }}
          </label>
          <textarea v-model="newDescription" rows="2"
                    :placeholder="d.classroomDescPlaceholder || 'Voliteľný popis triedy...'"
                    class="w-full px-4 py-2 border border-gray-300 dark:border-slate-600 rounded-md
                           bg-white dark:bg-slate-700 text-slate-800 dark:text-slate-100
                           focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none" />
        </div>

        <div class="flex gap-3 justify-end">
          <button @click="showCreateModal = false"
                  class="px-4 py-2 rounded-md text-gray-600 dark:text-gray-300
                         hover:bg-gray-100 dark:hover:bg-slate-700">
            {{ d.cancel || 'Zrušiť' }}
          </button>
          <button @click="handleCreate" :disabled="creating || !newName.trim()"
                  class="px-4 py-2 bg-secondary text-white rounded-md hover:bg-blue-600
                         disabled:opacity-50 font-semibold">
            {{ creating ? '...' : (d.create || 'Vytvoriť') }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
