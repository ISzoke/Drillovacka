<!--
================================================================================
 Component: Login.vue
 Description:
        Displays user login form.
================================================================================
-->

<script setup>
import { ref } from 'vue';
import { useAuthStore } from '@/stores/useAuthStore';
import { useRouter } from 'vue-router';
import { dictionary } from '@/utils/dictionary';
import { useLanguageStore } from '@/stores/useLanguageStore';

const username = ref('');
const passphrasePart1 = ref('');
const passphrasePart2 = ref('');
const passphrasePart3 = ref('');
const usernameError = ref('');
const passphraseError = ref('');

const authStore = useAuthStore();
const router = useRouter();
const langStore = useLanguageStore();

const handleLogin = async () => {
  usernameError.value = '';
  passphraseError.value = '';
  authStore.errorMessage = '';

  const passphrase = `${passphrasePart1.value}-${passphrasePart2.value}-${passphrasePart3.value}`;

  if (username.value.trim() === '') usernameError.value = dictionary[langStore.language].usernameError;
  if (!passphrasePart1.value.trim() || !passphrasePart2.value.trim() || !passphrasePart3.value.trim()) {
    passphraseError.value = dictionary[langStore.language].passphraseError;
  }
  if (usernameError.value || passphraseError.value) return;

  await authStore.login(username.value, passphrase, router, true, false);
};
</script>

<template>
  <div class="max-w-lg mx-auto px-4">
    <div class="bg-white dark:bg-slate-800 rounded-3xl border-[3px] border-slate-200 dark:border-slate-700
                border-b-[8px] border-b-slate-300 dark:border-b-slate-600 p-8 shadow-sm">

      <h2 class="text-3xl font-black text-slate-800 dark:text-slate-100 mb-8 text-center">
        {{ dictionary[langStore.language].login }}
      </h2>

      <form @submit.prevent="handleLogin" class="space-y-5">

        <!-- Username -->
        <div>
          <label class="block text-sm font-black text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-2">
            {{ dictionary[langStore.language].nickname }}
          </label>
          <input
            type="text"
            v-model="username"
            :placeholder="dictionary[langStore.language].nicknamePlaceholder"
            class="w-full px-4 py-3 rounded-2xl border-[3px] border-slate-200 dark:border-slate-600
                   bg-slate-50 dark:bg-slate-700 text-slate-800 dark:text-slate-100
                   placeholder-slate-400 dark:placeholder-slate-500
                   focus:outline-none focus:border-violet-400 dark:focus:border-violet-500 transition font-semibold"
          />
          <p v-if="usernameError" class="text-red-500 text-sm mt-1.5 font-semibold">{{ usernameError }}</p>
        </div>

        <!-- Passphrase (3 parts) -->
        <div>
          <label class="block text-sm font-black text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-2">
            {{ dictionary[langStore.language].accessCode }}
          </label>
          <div class="grid grid-cols-[1fr_auto_1fr_auto_1fr] items-center gap-1.5">
            <input
              type="text"
              v-model="passphrasePart1"
              maxlength="20"
              :placeholder="dictionary[langStore.language].part1"
              class="min-w-0 w-full px-2 py-3 rounded-2xl border-[3px] border-slate-200 dark:border-slate-600
                     bg-slate-50 dark:bg-slate-700 text-slate-800 dark:text-slate-100
                     placeholder-slate-400 dark:placeholder-slate-500 text-sm
                     focus:outline-none focus:border-violet-400 dark:focus:border-violet-500 transition text-center font-semibold"
            />
            <span class="font-black text-slate-400 dark:text-slate-500 text-lg px-0.5">-</span>
            <input
              type="text"
              v-model="passphrasePart2"
              maxlength="20"
              :placeholder="dictionary[langStore.language].part2"
              class="min-w-0 w-full px-2 py-3 rounded-2xl border-[3px] border-slate-200 dark:border-slate-600
                     bg-slate-50 dark:bg-slate-700 text-slate-800 dark:text-slate-100
                     placeholder-slate-400 dark:placeholder-slate-500 text-sm
                     focus:outline-none focus:border-violet-400 dark:focus:border-violet-500 transition text-center font-semibold"
            />
            <span class="font-black text-slate-400 dark:text-slate-500 text-lg px-0.5">-</span>
            <input
              type="text"
              v-model="passphrasePart3"
              maxlength="20"
              :placeholder="dictionary[langStore.language].part3"
              class="min-w-0 w-full px-2 py-3 rounded-2xl border-[3px] border-slate-200 dark:border-slate-600
                     bg-slate-50 dark:bg-slate-700 text-slate-800 dark:text-slate-100
                     placeholder-slate-400 dark:placeholder-slate-500 text-sm
                     focus:outline-none focus:border-violet-400 dark:focus:border-violet-500 transition text-center font-semibold"
            />
          </div>
          <p v-if="passphraseError" class="text-red-500 text-sm mt-1.5 font-semibold">{{ passphraseError }}</p>
        </div>

        <!-- Auth error -->
        <p v-if="authStore.errorMessage"
           class="bg-red-50 dark:bg-red-900/30 border-2 border-red-200 dark:border-red-700 text-red-600 dark:text-red-400
                  rounded-2xl px-4 py-3 font-semibold text-center">
          {{ authStore.errorMessage }}
        </p>

        <!-- Submit -->
        <button
          type="submit"
          class="w-full py-4 rounded-2xl font-black text-lg text-white
                 bg-violet-500 border-[3px] border-violet-600 border-b-[8px] border-b-violet-700
                 hover:-translate-y-0.5 active:translate-y-1 active:border-b-[3px] transition-all"
        >
          {{ dictionary[langStore.language].login }}
        </button>
      </form>
    </div>
  </div>
</template>
