<!--
================================================================================
 Component: AdminLogin.vue
 Description:
        Displays admin login form.
 Author: Dominik Horut (xhorut01)
================================================================================
-->

<script setup>
import { ref } from 'vue';
import { useAuthStore } from '@/stores/useAuthStore';
import { useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n';

const { t } = useI18n();

const username = ref('');
const password = ref('');

const usernameError = ref('');
const passwordError = ref('');

const authStore = useAuthStore();
const router = useRouter();

// Handle login form submission
const handleLogin = async () => {
  // Reset errors
  usernameError.value = '';
  passwordError.value = '';
  authStore.errorMessage = '';

  // Validation
  if (username.value.trim() === '') {
    usernameError.value = t('usernameError');
  }
  if (password.value.trim() === '') {
    passwordError.value = t('adminPasswordError');
  }
  if (usernameError.value || passwordError.value) {
    return;
  }

  // Handle login with auth store
  await authStore.login(username.value, password.value, router, true, true);
};
</script>

<template>
    <div class="max-w-lg mx-auto p-6 bg-white rounded-lg shadow-lg mb-4">

      <h2 class="text-2xl font-bold text-primary mb-16 text-center">{{ t('adminLoginTitle') }}</h2>

      <!-- Login form -->
      <form @submit.prevent="handleLogin">
        <!-- Username field -->
        <div class="mb-4">
          <label for="username" class="block text-sm font-medium text-gray-700 mb-2">{{ t('adminUsernameLabel') }}</label>
          <input
            type="text"
            id="username"
            v-model="username"
            :placeholder="t('adminUsernameLabel')"
            class="w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <span class="text-red-600 ml-1">{{ usernameError ? usernameError : '' }}</span>
        </div>

        <!-- Password field -->
        <div class="mb-4">
          <label for="password" class="block text-sm font-medium text-gray-700 mb-2">{{ t('password') }}</label>
          <input
            type="password"
            id="password"
            v-model="password"
            :placeholder="t('password')"
            class="w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <span class="text-red-600 ml-1">{{ passwordError ? passwordError : '' }}</span>
        </div>

        <!-- Error from auth store -->
        <p v-if="authStore.errorMessage" class="text-red-600 text-sm text-center">{{ authStore.errorMessage }}</p>

        <!-- Submit button -->
        <button type="submit"
                class="w-full py-2 bg-secondary text-white font-semibold rounded-md hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-500">
          {{ t('login') }}
        </button>
      </form>
    </div>
  </template>
  