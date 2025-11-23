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
import { updateSessionLanguage, updateStudentLanguage } from '@/api/apiClient';

export const useLanguageStore = defineStore('language', () => {
  const language = ref(localStorage.getItem('lang') || 'sk');

  watch(language, async (newVal, oldVal) => {
    localStorage.setItem('lang', newVal);
    
    // Don't make API call if value hasn't actually changed
    if (newVal === oldVal) {
      return;
    }
    
    try {
      // Get auth info from localStorage to avoid circular dependency
      const studentId = JSON.parse(localStorage.getItem('id') || 'null');
      const isAuthenticated = localStorage.getItem('role') !== null;
      
      if (isAuthenticated && studentId) {
        // Update language for authenticated student
        await updateStudentLanguage(studentId, newVal);
      } else {
        // Update language for anonymous session
        const sessionId = getSessionId();
        await updateSessionLanguage(sessionId, newVal);
      }
    } catch (error) {
      console.error('Failed to update language:', error);
    }
  });

  function setLanguage(lang) {
    const supported = ['cs', 'en', 'sk'];
    if (supported.includes(lang)) language.value = lang;
  }

  return { language, setLanguage };
});
