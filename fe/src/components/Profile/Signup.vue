<!--
================================================================================
 Component: Signup.vue
 Description:
        Displays user signup form.
================================================================================
-->

<script setup>
import { useI18n } from 'vue-i18n';
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import generatePassphrase from '@/utils/passphraseGenerator';
import { registerStudent } from '@/api/apiClient';
import { useAuthStore } from '@/stores/useAuthStore';
import { useLanguageStore } from '@/stores/useLanguageStore';

const username = ref('');
const passphrase = ref('');
const grade = ref(null);
const usernameError = ref('');
const passphraseError = ref('');
const showPassphrase = ref(false);
const errorMessage = ref('');
const copied = ref(false);
const credentialsSaved = ref(false);
const isLoading = ref(false);

const authStore = useAuthStore();
const router = useRouter();
const langStore = useLanguageStore();
const { t } = useI18n();

const handleSubmit = async () => {
  if (isLoading.value) return;

  usernameError.value = '';
  passphraseError.value = '';
  errorMessage.value = '';

  if (username.value.trim() === '') usernameError.value = t('usernameForgot');
  if (passphrase.value.trim() === '') passphraseError.value = t('passphraseForgot');
  if (usernameError.value || passphraseError.value) return;

  isLoading.value = true;
  try {
    const result = await registerStudent(username.value, passphrase.value, grade.value);
    if (result.status === 201) {
      await authStore.login(username.value, passphrase.value, router, false, false);
    } else {
      usernameError.value = result.error;
    }
  } finally {
    isLoading.value = false;
  }
};

const getPassphrase = () => {
  try {
    passphrase.value = generatePassphrase(langStore.language);
    showPassphrase.value = true;
    copied.value = false;
  } catch (error) {
    console.error("Passphrase generation error:", error);
  }
};

const copyToClipboard = () => {
  navigator.clipboard.writeText(passphrase.value)
    .then(() => { copied.value = true; setTimeout(() => { copied.value = false; }, 1500); })
    .catch(err => console.error('Failed to copy:', err));
};
</script>

<template>
  <div class="max-w-lg mx-auto px-4">
    <div class="bg-white dark:bg-slate-800 rounded-3xl border-[3px] border-slate-200 dark:border-slate-700
                border-b-[8px] border-b-slate-300 dark:border-b-slate-600 p-8 shadow-sm">

      <h2 class="text-3xl font-black text-slate-800 dark:text-slate-100 mb-8 text-center">
        {{ t('register') }}
      </h2>

      <form @submit.prevent="handleSubmit" class="space-y-5">

        <!-- Username -->
        <div>
          <label class="block text-sm font-black text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-2">
            {{ t('nickname') }}
          </label>
          <input
            type="text"
            v-model="username"
            :placeholder="t('nicknamePlaceholder')"
            class="w-full px-4 py-3 rounded-2xl border-[3px] border-slate-200 dark:border-slate-600
                   bg-slate-50 dark:bg-slate-700 text-slate-800 dark:text-slate-100
                   placeholder-slate-400 dark:placeholder-slate-500
                   focus:outline-none focus:border-violet-400 dark:focus:border-violet-500 transition font-semibold"
          />
          <p v-if="usernameError" class="text-red-500 text-sm mt-1.5 font-semibold">{{ usernameError }}</p>
        </div>

        <!-- Passphrase -->
        <div>
          <label class="block text-sm font-black text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-2">
            {{ t('accessCode') }}
          </label>

          <!-- Passphrase display area -->
          <div class="w-full bg-slate-50 dark:bg-slate-700 border-[3px] border-slate-200 dark:border-slate-600
                      rounded-2xl px-4 py-3 flex items-center justify-between min-h-[52px]">
            <span class="font-black text-slate-800 dark:text-slate-100 text-center flex-1"
                  :class="passphrase ? '' : 'text-slate-400 dark:text-slate-500 font-semibold'">
              {{ passphrase || t('generatePassphrasePlaceholder') }}
            </span>
            <button
              @click="copyToClipboard"
              type="button"
              class="text-slate-400 hover:text-violet-500 transition ml-2 focus:outline-none"
              :class="showPassphrase ? 'visible' : 'invisible'">
              <i class="fa-solid fa-copy text-lg"></i>
            </button>
          </div>

          <p class="text-xs font-bold text-violet-500 dark:text-violet-400 text-center mt-1.5 h-4">
            {{ copied ? t('copied') : '' }}
          </p>
          <p v-if="passphraseError" class="text-red-500 text-sm font-semibold">{{ passphraseError }}</p>
        </div>

        <!-- Generate passphrase button -->
        <button
          type="button"
          @click="getPassphrase"
          class="w-full py-3 rounded-2xl font-black text-base text-white
                 bg-emerald-500 border-[3px] border-emerald-600 border-b-[6px] border-b-emerald-700
                 hover:-translate-y-0.5 active:translate-y-1 active:border-b-[3px] transition-all"
        >
          {{ t('generatePassphrase') }}
        </button>

        <!-- Grade selector -->
        <div>
          <label class="block text-sm font-black text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-2">
            {{ t('gradeLevel') }}
            <span class="normal-case font-semibold text-slate-400">{{ t('optionalParenthetical') }}</span>
          </label>
          <div class="grid grid-cols-5 sm:grid-cols-9 gap-1.5">
            <button
              v-for="g in 9"
              :key="g"
              type="button"
              @click="grade = grade === g ? null : g"
              class="py-2.5 rounded-2xl text-sm font-black border-[3px] border-b-[4px] transition-all
                     hover:-translate-y-0.5 active:translate-y-1 active:border-b-[3px]"
              :class="grade === g
                ? 'bg-violet-500 border-violet-600 border-b-violet-700 text-white'
                : 'bg-slate-100 dark:bg-slate-700 border-slate-200 dark:border-slate-600 border-b-slate-300 dark:border-b-slate-500 text-slate-600 dark:text-slate-300'"
            >
              {{ g }}
            </button>
          </div>
          <p class="text-xs font-bold text-slate-400 dark:text-slate-500 mt-2 text-center">{{ t('whatGradeAreYouIn') }}</p>
        </div>

        <!-- Error message -->
        <p v-if="errorMessage" class="text-red-500 text-sm font-semibold text-center">{{ errorMessage }}</p>

        <!-- Credentials confirmation checkbox -->
        <label class="flex items-start gap-3 cursor-pointer select-none">
          <div class="mt-0.5 flex-shrink-0">
            <input
              type="checkbox"
              v-model="credentialsSaved"
              class="w-5 h-5 rounded-lg border-2 border-slate-300 dark:border-slate-500 accent-violet-500 cursor-pointer"
            />
          </div>
          <span class="text-sm font-semibold text-slate-600 dark:text-slate-300 leading-snug">
            {{ t('credentialsSavedConfirmation') }}
          </span>
        </label>

        <!-- Submit -->
        <button
          type="submit"
          :disabled="!credentialsSaved || isLoading"
          class="w-full py-4 rounded-2xl font-black text-lg text-white
                 bg-violet-500 border-[3px] border-violet-600 border-b-[8px] border-b-violet-700
                 hover:-translate-y-0.5 active:translate-y-1 active:border-b-[3px] transition-all
                 disabled:opacity-40 disabled:cursor-not-allowed disabled:translate-y-0 disabled:border-b-[8px]"
        >
          <span v-if="isLoading">
            <i class="fas fa-spinner fa-spin mr-2"></i>{{ t('saving') }}
          </span>
          <span v-else>{{ t('register') }}</span>
        </button>
      </form>
    </div>
  </div>
</template>
