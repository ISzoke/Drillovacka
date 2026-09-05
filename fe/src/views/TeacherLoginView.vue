<script setup>
import { useI18n } from 'vue-i18n';
import { ref } from 'vue';
import { useAuthStore } from '@/stores/useAuthStore';
import { useRouter } from 'vue-router';
import { useLanguageStore } from '@/stores/useLanguageStore';

const email = ref('');
const password = ref('');
const emailError = ref('');
const passwordError = ref('');

const authStore = useAuthStore();
const router = useRouter();
const langStore = useLanguageStore();

const { t } = useI18n();

const handleLogin = async () => {
  emailError.value = '';
  passwordError.value = '';
  authStore.errorMessage = '';

  if (!email.value.trim()) {
    emailError.value = t('emailRequired') || 'Zadajte email.';
  }
  if (!password.value.trim()) {
    passwordError.value = t('passwordRequired') || 'Zadajte heslo.';
  }
  if (emailError.value || passwordError.value) return;

  await authStore.login(email.value, password.value, router, true, false, true);
};
</script>

<template>
  <div class="pt-24 px-4">
    <!-- If already logged in as teacher -->
    <div v-if="authStore.isAuthenticated && authStore.role === 'teacher'"
         class="text-2xl text-primary text-center font-bold pt-12">
      {{ t('teacherDashboardWelcome') || 'Vitajte' }}, {{ authStore.name }}
      <div class="mt-4">
        <router-link :to="{ name: 'teacher-dashboard' }"
                     class="text-base text-secondary underline">
          {{ t('goToDashboard') || 'Prejsť na dashboard' }}
        </router-link>
      </div>
    </div>

    <div v-else class="max-w-lg mx-auto p-6 bg-white dark:bg-slate-800 rounded-lg shadow-lg mb-4">
      <h2 class="text-2xl font-bold text-primary dark:text-slate-100 mb-8 text-center">
        {{ t('teacherLogin') || 'Prihlásenie učiteľa' }}
      </h2>

      <form @submit.prevent="handleLogin">
        <div class="mb-4">
          <label for="email" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            {{ t('email') }}
          </label>
          <input type="email" id="email" v-model="email" :placeholder="t('email')"
                 class="w-full px-4 py-2 border border-gray-300 dark:border-slate-600 rounded-md
                        bg-white dark:bg-slate-700 text-slate-800 dark:text-slate-100
                        placeholder:text-slate-400 dark:placeholder:text-slate-500
                        focus:outline-none focus:ring-2 focus:ring-blue-500" />
          <span class="text-red-600 text-sm ml-1">{{ emailError }}</span>
        </div>

        <div class="mb-4">
          <label for="password" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            {{ t('password') || 'Heslo' }}
          </label>
          <input type="password" id="password" v-model="password" :placeholder="t('password') || 'Heslo'"
                 class="w-full px-4 py-2 border border-gray-300 dark:border-slate-600 rounded-md
                        bg-white dark:bg-slate-700 text-slate-800 dark:text-slate-100
                        placeholder:text-slate-400 dark:placeholder:text-slate-500
                        focus:outline-none focus:ring-2 focus:ring-blue-500" />
          <span class="text-red-600 text-sm ml-1">{{ passwordError }}</span>
        </div>

        <p v-if="authStore.errorMessage" class="text-red-600 text-sm text-center mb-4">
          {{ authStore.errorMessage }}
        </p>

        <button type="submit"
                class="w-full py-2 bg-secondary text-white font-semibold rounded-md
                       hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-500">
          {{ t('loginButton') || 'Prihlásiť sa' }}
        </button>
      </form>

      <p class="text-center mt-4 text-sm text-gray-600 dark:text-gray-400">
        {{ t('noAccountYet') || 'Nemáte účet?' }}
        <router-link :to="{ name: 'teacher-register' }" class="text-secondary underline">
          {{ t('registerHere') || 'Zaregistrujte sa' }}
        </router-link>
      </p>

      <div class="mt-6 pt-6 border-t border-gray-200 dark:border-slate-700">
        <a href="/manual.pdf" target="_blank" rel="noopener noreferrer"
           class="w-full flex items-center justify-center gap-2 py-3 px-4
                  bg-amber-50 dark:bg-slate-700 text-amber-700 dark:text-amber-400
                  border-2 border-amber-400 dark:border-amber-500 rounded-md
                  hover:bg-amber-100 dark:hover:bg-slate-600 font-semibold transition-colors text-sm">
          📖 {{ t('teacherManual') || 'Manuál pre učiteľov' }}
        </a>
      </div>
    </div>
  </div>
</template>
