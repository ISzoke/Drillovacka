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
import { getSessionId } from '@/utils/sessionManager';
import { updateSessionLanguage } from '@/api/apiClient';
import { useAuthStore } from './useAuthStore';

export const useLanguageStore = defineStore('language', () => {
  const language = ref(localStorage.getItem('lang') || 'sk');

  watch(language, async (val) => {
    localStorage.setItem('lang', val);
    
    // Update session language for anonymous users
    const authStore = useAuthStore();
    if (!authStore.isAuthenticated) {
      try {
        const sessionId = getSessionId();
        await updateSessionLanguage(sessionId, val);
      } catch (error) {
        console.error('Failed to update session language:', error);
      }
    }
  });

  function setLanguage(lang) {
    const supported = ['cs', 'en', 'sk'];
    if (supported.includes(lang)) language.value = lang;
  }

  return { language, setLanguage };
});
