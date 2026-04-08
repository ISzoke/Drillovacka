<script setup>
import { ref } from 'vue';
import { useAuthStore } from '@/stores/useAuthStore';
import { useRouter } from 'vue-router';
import { dictionary } from '@/utils/dictionary';
import { useLanguageStore } from '@/stores/useLanguageStore';

const email = ref('');
const password = ref('');
const emailError = ref('');
const passwordError = ref('');

const authStore = useAuthStore();
const router = useRouter();
const langStore = useLanguageStore();

const d = dictionary[langStore.language];

const handleLogin = async () => {
  emailError.value = '';
  passwordError.value = '';
  authStore.errorMessage = '';

  if (!email.value.trim()) {
    emailError.value = d.emailRequired || 'Zadajte email.';
  }
  if (!password.value.trim()) {
    passwordError.value = d.passwordRequired || 'Zadajte heslo.';
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
      {{ d.teacherDashboardWelcome || 'Vitajte' }}, {{ authStore.name }}
      <div class="mt-4">
        <router-link :to="{ name: 'teacher-dashboard' }"
                     class="text-base text-secondary underline">
          {{ d.goToDashboard || 'Prejsť na dashboard' }}
        </router-link>
      </div>
    </div>

    <div v-else class="max-w-lg mx-auto p-6 bg-white dark:bg-slate-800 rounded-lg shadow-lg mb-4">
      <h2 class="text-2xl font-bold text-primary dark:text-slate-100 mb-8 text-center">
        {{ d.teacherLogin || 'Prihlásenie učiteľa' }}
      </h2>

      <form @submit.prevent="handleLogin">
        <div class="mb-4">
          <label for="email" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Email
          </label>
          <input type="email" id="email" v-model="email" placeholder="Email"
                 class="w-full px-4 py-2 border border-gray-300 dark:border-slate-600 rounded-md
                        bg-white dark:bg-slate-700 text-slate-800 dark:text-slate-100
                        placeholder:text-slate-400 dark:placeholder:text-slate-500
                        focus:outline-none focus:ring-2 focus:ring-blue-500" />
          <span class="text-red-600 text-sm ml-1">{{ emailError }}</span>
        </div>

        <div class="mb-4">
          <label for="password" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            {{ d.password || 'Heslo' }}
          </label>
          <input type="password" id="password" v-model="password" :placeholder="d.password || 'Heslo'"
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
          {{ d.loginButton || 'Prihlásiť sa' }}
        </button>
      </form>

      <p class="text-center mt-4 text-sm text-gray-600 dark:text-gray-400">
        {{ d.noAccountYet || 'Nemáte účet?' }}
        <router-link :to="{ name: 'teacher-register' }" class="text-secondary underline">
          {{ d.registerHere || 'Zaregistrujte sa' }}
        </router-link>
      </p>
    </div>
  </div>
</template>
