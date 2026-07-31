<script setup>
import { ref, computed, onMounted } from 'vue';
import { useAuthStore } from '@/stores/useAuthStore';
import { getMyTeacherTasks, getUnassignedExampleCount } from '@/api/apiClient';
import Spinner from '@/components/Spinner.vue';
import TeacherIcon from '@/components/TeacherIcon.vue';
import TeacherPageHeader from '@/components/TeacherPageHeader.vue';

const authStore = useAuthStore();

const loadingTasks = ref(true);
const myTasks = ref([]);
const unassignedCount = ref(0);

const searchQuery = ref('');
const gradeFilter = ref(null);

const loadTasks = async () => {
  loadingTasks.value = true;
  try {
    myTasks.value = await getMyTeacherTasks(authStore.id);
  } catch (e) {
    myTasks.value = [];
  }
  loadingTasks.value = false;
};

const loadUnassignedCount = async () => {
  try {
    const data = await getUnassignedExampleCount(authStore.id);
    unassignedCount.value = data.count;
  } catch (e) {
    unassignedCount.value = 0;
  }
};

onMounted(() => { loadTasks(); loadUnassignedCount(); });

const filteredTasks = computed(() => {
  const q = searchQuery.value.trim().toLowerCase();
  return myTasks.value.filter(t => {
    const matchesSearch = !q || t.name.toLowerCase().includes(q);
    const matchesGrade = !gradeFilter.value || t.grade_levels.includes(gradeFilter.value);
    return matchesSearch && matchesGrade;
  });
});
</script>

<template>
  <div class="pt-20 px-4 max-w-3xl mx-auto pb-16">

    <TeacherPageHeader
      title="Moja knižnica"
      subtitle="Vlastné sady, ktoré vieš voľne upravovať, mazať a preskladať.">
      <template #action>
        <router-link :to="{ name: 'teacher-create-task-standalone' }" title="Vytvoriť novú sadu"
                     class="w-9 h-9 rounded-full bg-secondary/10 text-secondary flex items-center justify-center hover:bg-secondary/20">
          <TeacherIcon name="plus" :size="18" />
        </router-link>
      </template>
    </TeacherPageHeader>

    <div class="flex items-center gap-2 mb-4">
      <input v-model="searchQuery" type="text" placeholder="Hľadať sadu..."
             class="flex-1 px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-600
                    bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 text-xs
                    focus:outline-none focus:ring-1 focus:ring-secondary" />
      <select v-model="gradeFilter"
              class="px-2 py-1.5 rounded-lg border border-slate-200 dark:border-slate-600
                     bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 text-xs
                     focus:outline-none focus:ring-1 focus:ring-secondary">
        <option :value="null">Všetky ročníky</option>
        <option v-for="g in [1,2,3,4,5,6,7,8,9]" :key="g" :value="g">{{ g }}. ročník</option>
      </select>
    </div>

    <div v-if="loadingTasks" class="flex justify-center py-6"><Spinner /></div>

    <div v-else-if="!myTasks.length" class="border-2 border-dashed border-slate-200 dark:border-slate-700 rounded-2xl p-8 text-center">
      <div class="w-11 h-11 rounded-full bg-secondary/10 text-secondary flex items-center justify-center mx-auto mb-3">
        <TeacherIcon name="library" :size="22" />
      </div>
      <p class="font-semibold text-sm text-slate-700 dark:text-slate-200">Zatiaľ nemáš žiadne vlastné sady</p>
      <p class="text-xs text-gray-400 mt-1">Vytvor si novú, alebo si skopíruj existujúcu z prehľadu sád v triede.</p>
    </div>

    <div v-else class="grid sm:grid-cols-2 gap-3">
      <router-link :to="{ name: 'teacher-library-unassigned' }"
                   class="block px-4 py-3.5 bg-white dark:bg-slate-800 rounded-2xl
                          border border-dashed border-slate-300 dark:border-slate-600 hover:border-secondary
                          hover:-translate-y-0.5 transition-all">
        <div class="flex items-center gap-2">
          <TeacherIcon name="library" :size="15" class="text-secondary" />
          <span class="font-semibold text-slate-800 dark:text-slate-100 text-sm">Nezaradené</span>
        </div>
        <div class="text-xs text-gray-400 mt-2">{{ unassignedCount }} príkladov mimo sady</div>
      </router-link>

      <router-link v-for="t in filteredTasks" :key="t.id"
                   :to="{ name: 'teacher-edit-task-standalone', params: { taskId: t.id } }"
                   class="block px-4 py-3.5 bg-white dark:bg-slate-800 rounded-2xl
                          border border-slate-200 dark:border-slate-700 hover:border-secondary
                          hover:-translate-y-0.5 transition-all shadow-sm">
        <span class="font-semibold text-slate-800 dark:text-slate-100 text-sm">{{ t.name }}</span>
        <div class="flex items-center gap-1.5 mt-2">
          <span v-if="t.grade_levels.length" class="text-[11px] font-semibold px-2.5 py-0.5 rounded-full bg-tertiary/50 text-primary dark:bg-tertiary/20 dark:text-tertiary">
            {{ t.grade_levels.join(', ') }}. roč.
          </span>
          <span class="text-xs text-gray-400">{{ t.example_count }} príkladov</span>
          <button @click.stop.prevent="$router.push({ name: 'teacher-print', query: { taskId: t.id } })"
                  title="Tlačiť ako písomku (PDF)"
                  class="ml-auto flex items-center gap-1 text-[11px] px-2 py-0.5 rounded-full
                         text-gray-400 hover:text-secondary hover:bg-secondary/10 font-medium">
            <TeacherIcon name="print" :size="11" /> Tlačiť
          </button>
        </div>
      </router-link>

      <div v-if="!filteredTasks.length" class="sm:col-span-2 text-sm text-gray-400 text-center py-6">
        Žiadne sady nezodpovedajú filtru.
      </div>
    </div>

  </div>
</template>
