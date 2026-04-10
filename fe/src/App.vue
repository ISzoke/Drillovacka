<!--
================================================================================
 Component: App.vue
 Description:
        Root component of the application.
 Author: Dominik Horut (xhorut01)
================================================================================
-->

<script setup>
import Navbar from '@/components/Navbar.vue';
import Footer from '@/components/Footer.vue';
import { RouterView } from 'vue-router';
import ToastManager from '@/components/Toast/ToastManager.vue';
import BadgePopup from '@/components/BadgePopup.vue';
import LevelUpToast from '@/components/LevelUpToast.vue';
import StarField from '@/components/StarField.vue';
import CloudField from '@/components/CloudField.vue';
import { onMounted, onBeforeUnmount, watch } from 'vue';
import { useAuthStore } from '@/stores/useAuthStore';
import { useDarkStore } from '@/stores/useDarkStore';
import { useRouter } from 'vue-router';
import { useLanguageStore } from './stores/useLanguageStore';
import { getSessionId } from '@/utils/sessionManager';
import { initSession, updateSessionLanguage } from '@/api/apiClient';


// Initialize stores and router instances
const authStore = useAuthStore();
useDarkStore(); // initialize dark mode (applies class to <html> immediately)
const langStore = useLanguageStore();
const router = useRouter();

// Initialize anonymous session on app load
const initializeSession = async () => {
  // Only for non-authenticated users - check both store and localStorage
  const hasAuth = authStore.isAuthenticated || localStorage.getItem('role') !== null;
  
  if (!hasAuth) {
    try {
      const sessionId = getSessionId();
      const sessionData = await initSession(sessionId);
      
      // Frontend language is the source of truth so old anonymous sessions
      // created before the Slovak default do not switch the UI back to Czech.
      if (sessionData.language && sessionData.language !== langStore.language) {
        await updateSessionLanguage(sessionId, langStore.language);
      }
    } catch (error) {
      console.error('Failed to initialize session:', error);
    }
  }
};

// Reset inactivity timer on user activity
const resetInactivity = () => {
  if (authStore.isAuthenticated && authStore.role === 'admin') {
    authStore.resetInactivityTimer(router);
  }
};

// Event listeners on component mount to track user activity
onMounted(() => {
  initializeSession();
  window.addEventListener('mousemove', resetInactivity);
  window.addEventListener('keydown', resetInactivity);
});

// Clean up event listeners on component unmount  
onBeforeUnmount(() => {
  window.removeEventListener('mousemove', resetInactivity);
  window.removeEventListener('keydown', resetInactivity);
});

// Change document title based on selected language 
watch(
   () => langStore.language,
  () => {
    document.title = 'aritmation';
  },
  { immediate: true }
);
</script>

<template>

  <StarField />
  <CloudField />
  <Navbar />

  <ToastManager />
  <BadgePopup />
  <LevelUpToast />

  <div class="bg-slate-50 dark:bg-slate-900 min-h-screen transition-colors duration-200">
    <RouterView />
  </div>

  <Footer />
  
</template>
