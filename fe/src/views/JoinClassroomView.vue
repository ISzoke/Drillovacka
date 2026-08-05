<script setup>
import { useI18n } from 'vue-i18n';
import { ref, onMounted } from 'vue';
import { useAuthStore } from '@/stores/useAuthStore';
import { useRouter } from 'vue-router';
import { getClassroomByCode, joinClassroom } from '@/api/apiClient';
import { useLanguageStore } from '@/stores/useLanguageStore';
import { useToastStore } from '@/stores/useToastStore';
import Spinner from '@/components/Spinner.vue';

const props = defineProps({ code: String });

const authStore = useAuthStore();
const router = useRouter();
const langStore = useLanguageStore();
const toastStore = useToastStore();
const { t } = useI18n();

const classroom = ref(null);
const loading = ref(true);
const joining = ref(false);
const error = ref('');
const manualCode = ref(props.code || '');

const fetchClassroom = async (code) => {
  loading.value = true;
  error.value = '';
  classroom.value = null;
  try {
    classroom.value = await getClassroomByCode(code);
  } catch (e) {
    error.value = t('classroomNotFound');
  }
  loading.value = false;
};

const handleJoin = async () => {
  if (!authStore.isAuthenticated || authStore.role !== 'student' || !authStore.id) {
    sessionStorage.setItem('pendingJoinCode', classroom.value?.code || manualCode.value);
    router.push({ name: 'profile' });
    return;
  }
  joining.value = true;
  try {
    await joinClassroom(authStore.id, classroom.value.code || props.code || manualCode.value);
    toastStore.addToast({ message: t('joinedClassroom'), type: 'success', visible: true });
    router.push({ name: 'student-classrooms' });
  } catch (e) {
    const msg = e?.response?.data?.error;
    if (msg === 'already_member') {
      toastStore.addToast({ message: t('alreadyMember'), type: 'info', visible: true });
      router.push({ name: 'student-classrooms' });
    } else {
      toastStore.addToast({ message: t('joinError'), type: 'error', visible: true });
    }
  }
  joining.value = false;
};

const handleCodeSubmit = () => {
  if (manualCode.value.trim()) {
    fetchClassroom(manualCode.value.trim().toUpperCase());
  }
};

onMounted(async () => {
  if (props.code) {
    await fetchClassroom(props.code);
    if (authStore.isAuthenticated && authStore.role === 'student' && classroom.value) {
      handleJoin();
    }
  } else {
    loading.value = false;
  }
});
</script>

<template>
  <div class="pt-20 px-4 max-w-md mx-auto pb-12">

    <!-- Header -->
    <div class="text-center mb-8">
      <div class="inline-flex items-center justify-center w-16 h-16 rounded-2xl
                  bg-secondary/10 dark:bg-secondary/20 mb-4">
        <span class="text-3xl">🏫</span>
      </div>
      <h1 class="text-3xl font-bold text-primary dark:text-white mb-2">
        {{ t('joinClassroom') }}
      </h1>
      <p class="text-gray-500 dark:text-gray-400 text-sm">
        {{ t('joinClassroomDesc') }}
      </p>
    </div>

    <!-- Manual code entry -->
    <div v-if="!props.code" class="mb-6">
      <div class="flex gap-2">
        <input
          v-model="manualCode"
          type="text"
          maxlength="8"
          :placeholder="t('enterCode')"
          class="flex-1 px-4 py-3 text-center text-xl font-mono uppercase tracking-widest
                 rounded-2xl border-2 border-slate-200 dark:border-slate-600
                 bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-100
                 focus:outline-none focus:border-secondary transition-colors"
          @keyup.enter="handleCodeSubmit"
        />
        <button
          @click="handleCodeSubmit"
          class="px-5 py-3 bg-secondary text-white rounded-2xl font-semibold
                 border-b-4 border-blue-700 hover:-translate-y-0.5 active:translate-y-0.5
                 active:border-b-2 transition-all"
        >
          {{ t('search') }}
        </button>
      </div>
    </div>

    <Spinner v-if="loading" />

    <!-- Error state -->
    <div v-else-if="error"
         class="rounded-2xl border-2 border-accent/30 bg-accent/5 dark:bg-accent/10
                p-6 text-center">
      <div class="text-3xl mb-2">🔍</div>
      <p class="text-accent font-medium">{{ error }}</p>
    </div>

    <!-- Classroom preview -->
    <div v-else-if="classroom"
         class="rounded-3xl border-2 border-slate-200 dark:border-slate-700
                border-b-[8px] border-b-slate-300 dark:border-b-slate-600
                bg-white dark:bg-slate-800 p-6">

      <!-- Classroom info -->
      <div class="text-center mb-6">
        <h2 class="text-2xl font-bold text-primary dark:text-white mb-1">
          {{ classroom.name }}
        </h2>
        <p v-if="classroom.description" class="text-gray-500 dark:text-gray-400 text-sm mb-3">
          {{ classroom.description }}
        </p>
        <div class="flex items-center justify-center gap-4 text-sm text-gray-400">
          <span class="flex items-center gap-1">
            👤 {{ classroom.teacher_name }}
          </span>
          <span class="flex items-center gap-1">
            👥 {{ classroom.student_count }} {{ t('students') }}
          </span>
        </div>
      </div>

      <!-- Login warning -->
      <div v-if="!authStore.isAuthenticated || authStore.role !== 'student'"
           class="mb-4 p-3 rounded-xl bg-amber-50 dark:bg-amber-900/30
                  border border-amber-200 dark:border-amber-700
                  text-amber-700 dark:text-amber-300 text-sm text-center">
        {{ t('loginToJoin') }}
      </div>

      <button
        @click="handleJoin"
        :disabled="joining"
        class="w-full py-3 font-bold text-lg rounded-2xl transition-all
               border-b-[6px] active:border-b-[2px] active:translate-y-1 disabled:opacity-50 disabled:pointer-events-none"
        :class="authStore.isAuthenticated && authStore.role === 'student'
          ? 'bg-secondary text-white border-blue-700 hover:-translate-y-0.5'
          : 'bg-amber-400 text-white border-amber-600 hover:-translate-y-0.5'"
      >
        <span v-if="joining">...</span>
        <span v-else-if="!authStore.isAuthenticated || authStore.role !== 'student'">
          {{ t('loginAndJoin') }}
        </span>
        <span v-else>
          {{ t('joinNow') }}
        </span>
      </button>
    </div>

    <!-- Empty state -->
    <div v-else-if="!props.code && !manualCode" class="text-center py-12 text-gray-400 text-sm">
      {{ t('enterCodeAbove') }}
    </div>

  </div>
</template>
