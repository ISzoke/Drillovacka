/**
 * ================================================================================
 * File: useLanguageStore.js
 * Description:
 *       Pinia store for managing the applications language.
 * Author: Dominik Horut (xhorut01)
 * ================================================================================
 */

import { defineStore } from 'pinia';
import { ref, watch } from 'vue';

export const useLanguageStore = defineStore('language', () => {
  const language = ref(localStorage.getItem('lang') || 'sk');

  watch(language, (val) => localStorage.setItem('lang', val));

  function setLanguage(lang) {
    const supported = ['cs', 'en', 'sk'];
    if (supported.includes(lang)) language.value = lang;
  }

  return { language, setLanguage };
});
