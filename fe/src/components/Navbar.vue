<!--
================================================================================
 Component: Navbar.vue
 Description:
        Displays navigation bar in application.
 Author: Dominik Horut (xhorut01)
================================================================================
-->

<script setup>
import { useI18n } from 'vue-i18n';
import { RouterLink } from 'vue-router';
import { useAuthStore } from '@/stores/useAuthStore';
import { computed, ref } from 'vue';
import { useRouter } from 'vue-router';
import { useLanguageStore } from '@/stores/useLanguageStore';
import { useRecorderStore } from '@/stores/useRecorderStore';
import csFlag from '@/assets/img/cs-flag.png';
import enFlag from '@/assets/img/en-flag.png';
import skFlag from '@/assets/img/sk-flag.png';
import { useDarkStore } from '@/stores/useDarkStore';
import TeacherIcon from '@/components/TeacherIcon.vue';

// Stores
const authStore = useAuthStore();
const langStore = useLanguageStore();
const { t } = useI18n();
const recorderStore = useRecorderStore();

const router = useRouter();
const darkStore = useDarkStore();

const isAuthenticated = computed(() => authStore.isAuthenticated);

// Mobile menu state
const isMenuOpen = ref(false);

// Zmena jazyka + ASR mapovanie
const ASR_BY_LANG = { en: 'en-US', cs: 'cs-CZ', sk: 'sk-SK' };
function changeLanguage(lang) {
  langStore.setLanguage(lang);
  recorderStore.changeASRLanguage(ASR_BY_LANG[lang] || 'sk-SK');
  
  // Navigate to appropriate language route
  if (lang === 'en') {
    router.push({ path: '/en' });
  } else if (lang === 'cs') {
    router.push({ path: '/cs' });
  } else {
    router.push({ path: '/' });
  }
}

// Redirect to home page based on language
const handleLogoClick = () => {
  if (langStore.language === 'en') {
    router.push({ path: '/en' });
  } else if (langStore.language === 'cs') {
    router.push({ path: '/cs' });
  } else {
    router.push({ path: '/' });
  }
};
</script>

<template>

  <nav class="bg-primary shadow relative z-50">

    <div class="px-4 sm:px-6 lg:px-9">

      <div class="flex h-20 items-center justify-between">

        <!-- Logo -->
        <div class="flex items-center">

          <RouterLink to="/" @click="handleLogoClick">
            <img src="/logo.png" alt="aritmation" style="height: 200px; width: auto;" />
          </RouterLink>

        </div>

        <!-- Dark mode toggle (mobile) -->
        <button @click="darkStore.toggle()"
          class="md:hidden text-white hover:text-yellow-300 transition text-2xl mr-2 focus:outline-none">
          <i :class="darkStore.isDark ? 'fa-solid fa-sun' : 'fa-solid fa-moon'"></i>
        </button>

        <!-- Button to open menu on smaller screensizes -->
        <button @click="isMenuOpen = !isMenuOpen"
          class="md:hidden text-white text-5xl focus:outline-none transition-transform duration-300"
          :class="isMenuOpen ? 'rotate-180' : 'rotate-0'">

          <i class="fa-solid transition-transform duration-300" 
            :class="isMenuOpen ? 'fa-times scale-110' : 'fa-bars scale-100'">
          </i>

        </button>

        <!-- Desktop Menu -->
        <div class="hidden md:flex items-center space-x-8 text-2xl font-semibold">

          <!-- Dark mode toggle (desktop) -->
          <button @click="darkStore.toggle()"
            class="text-white hover:text-yellow-300 transition focus:outline-none"
            :title="darkStore.isDark ? t('lightMode') : t('darkMode')">
            <i :class="darkStore.isDark ? 'fa-solid fa-sun' : 'fa-solid fa-moon'"></i>
          </button>

          <!-- Unauthenticated user menu -->
          <template v-if="!isAuthenticated">
            <RouterLink to="/kontakt" class="text-white hover:text-gray-200 border-b-2 border-primary hover:border-white transition">
              {{ t('contact') }}
            </RouterLink>
            <RouterLink to="/teacher" class="text-white hover:text-gray-200 border-b-2 border-primary hover:border-white transition">
              🏫 {{ t('teacherLogin') || 'Pre učiteľov' }}
            </RouterLink>
            <RouterLink to="/profile" class="text-white hover:text-gray-200 border-b-2 border-primary hover:border-white transition">
              {{ t('login') }}
            </RouterLink>
            <RouterLink to="/profile?register=1" class="text-white hover:text-gray-200 border-b-2 border-primary hover:border-white transition">
              {{ t('register') }}
            </RouterLink>
            <div class="flex items-center gap-2">
              <button @click="changeLanguage('cs')"><img :src="csFlag" :alt="t('languageCzech')" class="w-8 h-8 ml-2" /></button>
              <button @click="changeLanguage('en')"><img :src="enFlag" :alt="t('languageEnglish')" class="w-8 h-8 ml-2" /></button>
              <button @click="changeLanguage('sk')"><img :src="skFlag" :alt="t('languageSlovak')" class="w-8 h-8 ml-2 rounded-full object-cover" style="object-position: 33% center" /></button>
            </div>
          </template>

          <!-- Admin menu -->
          <template v-else-if="authStore.role == 'admin'">
            <RouterLink to="/tasks" class="text-white hover:text-gray-200 border-b-2 border-primary hover:border-white transition">{{ t('tasks') }}</RouterLink>
            <RouterLink to="/tasks/grades" class="text-white hover:text-gray-200 border-b-2 border-primary hover:border-white transition">{{ t('tasksByGrade') }}</RouterLink>
            <RouterLink to="/skill-creator" class="text-white hover:text-gray-200 border-b-2 border-primary hover:border-white transition">{{ t('skills') }}</RouterLink>
            <RouterLink to="/analytics/activity" class="text-white hover:text-gray-200 border-b-2 border-primary hover:border-white transition">{{ t('navActivity') }}</RouterLink>
            <RouterLink to="/admin/teachers" class="text-white hover:text-gray-200 border-b-2 border-primary hover:border-white transition">{{ t('navTeachers') }}</RouterLink>
            <RouterLink to="/analytics/my-data" class="text-white hover:text-gray-200 border-b-2 border-primary hover:border-white transition">{{ t('myData') }}</RouterLink>
            <RouterLink to="/kontakt" class="text-white hover:text-gray-200 border-b-2 border-primary hover:border-white transition">{{ t('contact') }}</RouterLink>
            <button @click="authStore.logout(router)" class="text-white hover:text-gray-200 border-b-2 border-primary hover:border-white transition">{{ t('logout') }}</button>
            <div class="flex items-center gap-2">
              <button @click="changeLanguage('cs')"><img :src="csFlag" :alt="t('languageCzech')" class="w-8 h-8 ml-2" /></button>
              <button @click="changeLanguage('en')"><img :src="enFlag" :alt="t('languageEnglish')" class="w-8 h-8 ml-2" /></button>
              <button @click="changeLanguage('sk')"><img :src="skFlag" :alt="t('languageSlovak')" class="w-8 h-8 ml-2 rounded-full object-cover" style="object-position: 33% center" /></button>
            </div>
          </template>

          <!-- Teacher menu -->
          <template v-else-if="authStore.role == 'teacher'">
            <RouterLink to="/teacher/dashboard" active-class="border-white"
              class="text-white hover:text-gray-200 border-b-2 border-primary hover:border-white transition">
              {{ t('myClassrooms') || 'Moje triedy' }}
            </RouterLink>
            <RouterLink to="/teacher/library" active-class="border-white"
              class="flex items-center gap-1.5 text-white hover:text-gray-200 border-b-2 border-primary hover:border-white transition">
              <TeacherIcon name="library" :size="14" /> {{ t('myLibrary') }}
            </RouterLink>
            <RouterLink to="/teacher/print" active-class="border-white"
              class="flex items-center gap-1.5 text-white hover:text-gray-200 border-b-2 border-primary hover:border-white transition">
              <TeacherIcon name="print" :size="14" /> {{ t('printExamNav') }}
            </RouterLink>
            <RouterLink to="/kontakt" class="text-white hover:text-gray-200 border-b-2 border-primary hover:border-white transition">{{ t('contact') }}</RouterLink>
            <button @click="authStore.logout(router)" class="text-white hover:text-gray-200 border-b-2 border-primary hover:border-white transition">{{ t('logout') }}</button>
            <div class="flex items-center gap-2">
              <button @click="changeLanguage('cs')"><img :src="csFlag" :alt="t('languageCzech')" class="w-8 h-8 ml-2" /></button>
              <button @click="changeLanguage('en')"><img :src="enFlag" :alt="t('languageEnglish')" class="w-8 h-8 ml-2" /></button>
              <button @click="changeLanguage('sk')"><img :src="skFlag" :alt="t('languageSlovak')" class="w-8 h-8 ml-2 rounded-full object-cover" style="object-position: 33% center" /></button>
            </div>
          </template>

          <!-- Logged in user (student) -->
          <template v-else>
            <RouterLink to="/" @click="handleLogoClick" class="text-white hover:text-gray-200 border-b-2 border-primary hover:border-white transition">
              📚 {{ t('examples') }}
            </RouterLink>
            <RouterLink to="/progress" class="text-white hover:text-gray-200 border-b-2 border-primary hover:border-white transition">
              <i class="fa-solid fa-chart-line mr-1"></i>{{ t('progress') }}
            </RouterLink>
            <RouterLink to="/my-classrooms" class="text-white hover:text-gray-200 border-b-2 border-primary hover:border-white transition">
              🏫 {{ t('myClassrooms') || 'Triedy' }}
            </RouterLink>
            <RouterLink to="/leaderboard" class="text-white hover:text-gray-200 border-b-2 border-primary hover:border-white transition">
              🏆 {{ t('leaderboard') }}
            </RouterLink>
            <RouterLink to="/profile" class="text-white hover:text-gray-200 border-b-2 border-primary hover:border-white transition">
              👤 {{ t('profile') }}
            </RouterLink>
            <RouterLink to="/kontakt" class="text-white hover:text-gray-200 border-b-2 border-primary hover:border-white transition">
              {{ t('contact') }}
            </RouterLink>
            <button @click="authStore.logout(router)" class="text-white hover:text-gray-200 border-b-2 border-primary hover:border-white transition">
              {{ t('logout') }}
            </button>
            <div class="flex items-center gap-2">
              <button @click="changeLanguage('cs')"><img :src="csFlag" :alt="t('languageCzech')" class="w-8 h-8 ml-2" /></button>
              <button @click="changeLanguage('en')"><img :src="enFlag" :alt="t('languageEnglish')" class="w-8 h-8 ml-2" /></button>
              <button @click="changeLanguage('sk')"><img :src="skFlag" :alt="t('languageSlovak')" class="w-8 h-8 ml-2 rounded-full object-cover" style="object-position: 33% center" /></button>
            </div>
          </template>

        </div>
      </div>

      <!-- Mobile Menu (Dropdown) -->
      <transition name="fade">

        <div v-if="isMenuOpen" class="md:hidden flex flex-col items-center bg-primary text-white py-4 space-y-4 text-xl">

          <!-- Unauthenticated user menu -->
          <template v-if="!isAuthenticated">
            <RouterLink to="/kontakt" class="text-white hover:text-gray-200 border-b-2 border-primary hover:border-white transition" @click="isMenuOpen = false">
              {{ t('contact') }}
            </RouterLink>
            <RouterLink to="/teacher" class="text-white text-xl font-semibold" @click="isMenuOpen = false">
              🏫 {{ t('teacherLogin') || 'Pre učiteľov' }}
            </RouterLink>
            <RouterLink to="/profile" class="text-white hover:text-gray-200 border-b-2 border-primary hover:border-white transition">
              {{ t('login') }}
            </RouterLink>
            <RouterLink to="/profile?register=1" class="text-white hover:text-gray-200 border-b-2 border-primary hover:border-white transition">
              {{ t('register') }}
            </RouterLink>
            <div class="flex items-center gap-2">
              <button @click="changeLanguage('cs')"><img :src="csFlag" :alt="t('languageCzech')" class="w-8 h-8 ml-2" /></button>
              <button @click="changeLanguage('en')"><img :src="enFlag" :alt="t('languageEnglish')" class="w-8 h-8 ml-2" /></button>
              <button @click="changeLanguage('sk')"><img :src="skFlag" :alt="t('languageSlovak')" class="w-8 h-8 ml-2 rounded-full object-cover" style="object-position: 33% center" /></button>
            </div>
          </template>

          <!-- Admin menu -->
          <template v-else-if="authStore.role == 'admin'">
            <RouterLink to="/tasks" class="text-white text-xl font-semibold" @click="isMenuOpen = false">{{ t('tasks') }}</RouterLink>
            <RouterLink to="/tasks/grades" class="text-white text-xl font-semibold" @click="isMenuOpen = false">{{ t('tasksByGrade') }}</RouterLink>
            <RouterLink to="/skill-creator" class="text-white text-xl font-semibold" @click="isMenuOpen = false">{{ t('skills') }}</RouterLink>
            <RouterLink to="/analytics/activity" class="text-white text-xl font-semibold" @click="isMenuOpen = false">{{ t('navActivity') }}</RouterLink>
            <RouterLink to="/admin/teachers" class="text-white text-xl font-semibold" @click="isMenuOpen = false">{{ t('navTeachers') }}</RouterLink>
            <RouterLink to="/analytics/my-data" class="text-white text-xl font-semibold" @click="isMenuOpen = false">{{ t('myData') }}</RouterLink>
            <RouterLink to="/kontakt" class="text-white text-xl font-semibold" @click="isMenuOpen = false">{{ t('contact') }}</RouterLink>
            <button @click="authStore.logout(router); isMenuOpen = false" class="text-white text-xl font-semibold">{{ t('logout') }}</button>
            <div class="flex items-center gap-2">
              <button @click="changeLanguage('cs')"><img :src="csFlag" :alt="t('languageCzech')" class="w-8 h-8 ml-2" /></button>
              <button @click="changeLanguage('en')"><img :src="enFlag" :alt="t('languageEnglish')" class="w-8 h-8 ml-2" /></button>
              <button @click="changeLanguage('sk')"><img :src="skFlag" :alt="t('languageSlovak')" class="w-8 h-8 ml-2 rounded-full object-cover" style="object-position: 33% center" /></button>
            </div>
          </template>

          <!-- Teacher menu (mobile) -->
          <template v-else-if="authStore.role == 'teacher'">
            <RouterLink to="/teacher/dashboard" class="text-white text-xl font-semibold" @click="isMenuOpen = false">
              {{ t('myClassrooms') || 'Moje triedy' }}
            </RouterLink>
            <RouterLink to="/teacher/library" class="text-white text-xl font-semibold" @click="isMenuOpen = false">
              {{ t('myLibrary') }}
            </RouterLink>
            <RouterLink to="/teacher/print" class="text-white text-xl font-semibold" @click="isMenuOpen = false">
              {{ t('printExamNav') }}
            </RouterLink>
            <RouterLink to="/kontakt" class="text-white text-xl font-semibold" @click="isMenuOpen = false">{{ t('contact') }}</RouterLink>
            <button @click="authStore.logout(router); isMenuOpen = false" class="text-white text-xl font-semibold">{{ t('logout') }}</button>
            <div class="flex items-center gap-2">
              <button @click="changeLanguage('cs')"><img :src="csFlag" :alt="t('languageCzech')" class="w-8 h-8 ml-2" /></button>
              <button @click="changeLanguage('en')"><img :src="enFlag" :alt="t('languageEnglish')" class="w-8 h-8 ml-2" /></button>
              <button @click="changeLanguage('sk')"><img :src="skFlag" :alt="t('languageSlovak')" class="w-8 h-8 ml-2 rounded-full object-cover" style="object-position: 33% center" /></button>
            </div>
          </template>

          <!-- Logged in user (student) -->
          <template v-else>
            <RouterLink to="/" class="text-white text-xl font-semibold" @click="handleLogoClick; isMenuOpen = false">
              📚 {{ t('examples') }}
            </RouterLink>
            <RouterLink to="/progress" class="text-white text-xl font-semibold" @click="isMenuOpen = false">
              <i class="fa-solid fa-chart-line mr-2"></i>{{ t('progress') }}
            </RouterLink>
            <RouterLink to="/my-classrooms" class="text-white text-xl font-semibold" @click="isMenuOpen = false">
              🏫 {{ t('myClassrooms') || 'Triedy' }}
            </RouterLink>
            <RouterLink to="/leaderboard" class="text-white text-xl font-semibold" @click="isMenuOpen = false">
              🏆 {{ t('leaderboard') }}
            </RouterLink>
            <RouterLink to="/profile" class="text-white text-xl font-semibold" @click="isMenuOpen = false">
              👤 {{ t('profile') }}
            </RouterLink>
            <RouterLink to="/kontakt" class="text-white text-xl font-semibold" @click="isMenuOpen = false">
              {{ t('contact') }}
            </RouterLink>
            <button @click="authStore.logout(router); isMenuOpen = false" class="text-white text-xl font-semibold">
              {{ t('logout') }}
            </button>
            <div class="flex items-center gap-2">
              <button @click="changeLanguage('cs')"><img :src="csFlag" :alt="t('languageCzech')" class="w-8 h-8 ml-2" /></button>
              <button @click="changeLanguage('en')"><img :src="enFlag" :alt="t('languageEnglish')" class="w-8 h-8 ml-2" /></button>
              <button @click="changeLanguage('sk')"><img :src="skFlag" :alt="t('languageSlovak')" class="w-8 h-8 ml-2 rounded-full object-cover" style="object-position: 33% center" /></button>
            </div>
          </template>

        </div>

      </transition>

    </div>
  </nav>

</template>
