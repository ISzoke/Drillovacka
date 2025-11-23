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
import { onMounted, onBeforeUnmount, watch } from 'vue';
import { useAuthStore } from '@/stores/useAuthStore';
import { useRouter } from 'vue-router';
import { useLanguageStore } from './stores/useLanguageStore';
import { getSessionId } from '@/utils/sessionManager';
import { initSession } from '@/api/apiClient';


// Initialize stores and router instances
const authStore = useAuthStore();
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
      
      // Set language from session if different from current
      if (sessionData.language && sessionData.language !== langStore.language) {
        langStore.setLanguage(sessionData.language);
      }
    } catch (error) {
      console.error('Failed to initialize session:', error);
    }
  }
};

// Reset inactivity timer on user activity
const resetInactivity = () => {
  if (authStore.isAuthenticated) {
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
    if (langStore.language === 'en') {
      document.title = 'Drillapp';
    } else {
      document.title = 'Drillovačka';
    }
  },
  { immediate: true }
);
</script>

<template>

  <Navbar />

  <ToastManager />

  <div class="bg-white min-h-screen">
    <RouterView />
  </div>

  <Footer />
  
</template>