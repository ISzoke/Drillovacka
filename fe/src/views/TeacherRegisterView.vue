<script setup>
import { useI18n } from 'vue-i18n';
import { ref } from 'vue';
import { useAuthStore } from '@/stores/useAuthStore';
import { useRouter } from 'vue-router';
import { registerTeacher } from '@/api/apiClient';
import { useLanguageStore } from '@/stores/useLanguageStore';
import { useToastStore } from '@/stores/useToastStore';

const email = ref('');
const password = ref('');
const confirmPassword = ref('');
const firstName = ref('');
const lastName = ref('');
const errorMessage = ref('');

const authStore = useAuthStore();
const router = useRouter();
const langStore = useLanguageStore();
const toastStore = useToastStore();

const { t } = useI18n();

const handleRegister = async () => {
  errorMessage.value = '';

  if (!email.value.trim() || !password.value || !firstName.value.trim() || !lastName.value.trim()) {
    errorMessage.value = t('allFieldsRequired');
    return;
  }

  if (password.value !== confirmPassword.value) {
    errorMessage.value = t('passwordMismatch');
    return;
  }

  if (password.value.length < 6) {
    errorMessage.value = t('passwordTooShort');
    return;
  }

  const result = await registerTeacher(email.value, password.value, firstName.value, lastName.value);

  if (result?.error) {
    errorMessage.value = result.error;
    return;
  }

  if (result?.status === 201) {
    // Auto-login after registration
    await authStore.login(email.value, password.value, router, false, false, true);
  }
};
</script>

<template>
  <div class="pt-24 px-4">
    <div class="max-w-lg mx-auto p-6 bg-white dark:bg-slate-800 rounded-lg shadow-lg mb-4">
      <h2 class="text-2xl font-bold text-primary dark:text-slate-100 mb-8 text-center">
        {{ t('teacherRegister') }}
      </h2>

      <form @submit.prevent="handleRegister">
        <div class="grid grid-cols-2 gap-4 mb-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              {{ t('firstName') }}
            </label>
            <input type="text" v-model="firstName" :placeholder="t('firstName')"
                   class="w-full px-4 py-2 border border-gray-300 dark:border-slate-600 rounded-md
                          bg-white dark:bg-slate-700 text-slate-800 dark:text-slate-100
                          placeholder:text-slate-400 dark:placeholder:text-slate-500
                          focus:outline-none focus:ring-2 focus:ring-blue-500" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              {{ t('lastName') }}
            </label>
            <input type="text" v-model="lastName" :placeholder="t('lastName')"
                   class="w-full px-4 py-2 border border-gray-300 dark:border-slate-600 rounded-md
                          bg-white dark:bg-slate-700 text-slate-800 dark:text-slate-100
                          placeholder:text-slate-400 dark:placeholder:text-slate-500
                          focus:outline-none focus:ring-2 focus:ring-blue-500" />
          </div>
        </div>

        <div class="mb-4">
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">{{ t('emailLabel') }}</label>
          <input type="email" v-model="email" :placeholder="t('emailLabel')"
                 class="w-full px-4 py-2 border border-gray-300 dark:border-slate-600 rounded-md
                        bg-white dark:bg-slate-700 text-slate-800 dark:text-slate-100
                        placeholder:text-slate-400 dark:placeholder:text-slate-500
                        focus:outline-none focus:ring-2 focus:ring-blue-500" />
        </div>

        <div class="mb-4">
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            {{ t('password') }}
          </label>
          <input type="password" v-model="password" :placeholder="t('password')"
                 class="w-full px-4 py-2 border border-gray-300 dark:border-slate-600 rounded-md
                        bg-white dark:bg-slate-700 text-slate-800 dark:text-slate-100
                        placeholder:text-slate-400 dark:placeholder:text-slate-500
                        focus:outline-none focus:ring-2 focus:ring-blue-500" />
        </div>

        <div class="mb-6">
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            {{ t('confirmPassword') }}
          </label>
          <input type="password" v-model="confirmPassword" :placeholder="t('confirmPassword')"
                 class="w-full px-4 py-2 border border-gray-300 dark:border-slate-600 rounded-md
                        bg-white dark:bg-slate-700 text-slate-800 dark:text-slate-100
                        placeholder:text-slate-400 dark:placeholder:text-slate-500
                        focus:outline-none focus:ring-2 focus:ring-blue-500" />
        </div>

        <p v-if="errorMessage" class="text-red-600 text-sm text-center mb-4">{{ errorMessage }}</p>

        <button type="submit"
                class="w-full py-2 bg-secondary text-white font-semibold rounded-md
                       hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-500">
          {{ t('registerButton') }}
        </button>
      </form>

      <p class="text-center mt-4 text-sm text-gray-600 dark:text-gray-400">
        {{ t('alreadyHaveAccount') }}
        <router-link :to="{ name: 'teacher-login' }" class="text-secondary underline">
          {{ t('loginHere') }}
        </router-link>
      </p>
    </div>
  </div>
</template>
