/**
 * ================================================================================
 * File: useAuthStore.js
 * Description:
 *       Pinia store for managing authentication state, login/logout actions, and session handling.
 * Author: Dominik Horut (xhorut01)
 * ================================================================================
 */


import { defineStore } from 'pinia';
import { loginStudent, loginAdmin, loginTeacher } from '@/api/apiClient';
import { useToastStore } from '@/stores/useToastStore';
import { dictionary } from '@/utils/dictionary';
import { useLanguageStore } from './useLanguageStore';

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: null,
    id: null,
    role: null,
    isAuthenticated: false,
    errorMessage: '',
    inactivityTimeout: null,
    grade: null,
    grade_change_used: false,
    email: null,
    firstName: null,
    lastName: null,
  }),
  actions: {
    async login(username, passphrase, router, isLogin, isAdmin, isTeacher = false) {
      try {
        let result = null;

        if (isTeacher) {
          // Teacher tries to login (username = email, passphrase = password)
          result = await loginTeacher(username, passphrase);
        } else if (isAdmin) {
          // Admin tries to login
          result = await loginAdmin(username, passphrase);
        } else {
          // User tries to login
          result = await loginStudent(username, passphrase);
        }

        const langStore = useLanguageStore();

        // Successful login
        if (result.status === 200 || result.status === 201) {

          // Save data in the store
          this.name = isTeacher ? `${result.data.first_name} ${result.data.last_name}` : username;
          this.id = result.data.id;
          this.role = result.data.role;
          this.grade = result.data.grade ?? null;
          this.grade_change_used = result.data.grade_change_used ?? false;
          this.isAuthenticated = true;

          // Teacher-specific fields
          if (isTeacher) {
            this.email = result.data.email;
            this.firstName = result.data.first_name;
            this.lastName = result.data.last_name;
            localStorage.setItem('email', JSON.stringify(this.email));
            localStorage.setItem('firstName', JSON.stringify(this.firstName));
            localStorage.setItem('lastName', JSON.stringify(this.lastName));
          }

          localStorage.setItem('name', JSON.stringify(this.name));
          localStorage.setItem('id', JSON.stringify(this.id));
          localStorage.setItem('role', JSON.stringify(this.role));
          localStorage.setItem('grade', JSON.stringify(this.grade));
          localStorage.setItem('grade_change_used', JSON.stringify(this.grade_change_used));

          if (result.data.role === 'admin') this.startInactivityTimer(router);

          // Set language from profile if available
          if (result.data.language) {
            langStore.setLanguage(result.data.language);
          }

          const toastStore = useToastStore();

          toastStore.addToast({
            message: isLogin ? dictionary[langStore.language].loginSuccess : dictionary[langStore.language].registrationSuccess,
            type: 'success',
            visible: true,
          });

          // Check for pending classroom join code
          const pendingCode = sessionStorage.getItem('pendingJoinCode');
          if (pendingCode && result.data.role === 'student') {
            sessionStorage.removeItem('pendingJoinCode');
            router.push({ name: 'join-classroom', params: { code: pendingCode } });
          } else if (result.data.role === 'teacher') {
            router.push({ name: 'teacher-dashboard' });
          } else {
            router.push({ name: 'home' });
          }

        // Unsuccessful login
        } else {
          const langStore = useLanguageStore();
          this.errorMessage = langStore.language == 'cs' ? result.error : dictionary[langStore.language].invalidCredentials;
        }
      } catch (error) {
        const langStore = useLanguageStore();
        this.errorMessage = dictionary[langStore.language].somethingWentWrong;
      }
    },

    logout(router) {

      // Clear store data
      this.user = null;
      this.id = null;
      this.role = null;
      this.isAuthenticated = false;
      this.email = null;
      this.firstName = null;
      this.lastName = null;

      localStorage.removeItem('name');
      localStorage.removeItem('id');
      localStorage.removeItem('role');
      localStorage.removeItem('grade');
      localStorage.removeItem('grade_change_used');
      localStorage.removeItem('email');
      localStorage.removeItem('firstName');
      localStorage.removeItem('lastName');

      this.clearInactivityTimer();

      const toastStore = useToastStore();
      const langStore = useLanguageStore();

      toastStore.addToast({
        message: dictionary[langStore.language].logoutSuccess,
        type: 'info',
        visible: true,
      });

      // Redirect to home page and reload
      router.push({ name: 'home' }).then(() => {
        window.location.reload();
      });
    },

    // Load stored session data from localStorage
    loadStoredSession() {

      const storedName = localStorage.getItem('name');
      const storedId = localStorage.getItem('id');
      const storedRole = localStorage.getItem('role');

      if (storedName && storedId && storedRole) {
        this.name = JSON.parse(storedName);
        this.id = storedId;
        this.role = JSON.parse(storedRole);
        this.isAuthenticated = true;

        const storedGrade = localStorage.getItem('grade');
        const storedGradeChangeUsed = localStorage.getItem('grade_change_used');
        this.grade = storedGrade ? JSON.parse(storedGrade) : null;
        this.grade_change_used = storedGradeChangeUsed ? JSON.parse(storedGradeChangeUsed) : false;

        // Teacher-specific fields
        if (this.role === 'teacher') {
          const storedEmail = localStorage.getItem('email');
          const storedFirstName = localStorage.getItem('firstName');
          const storedLastName = localStorage.getItem('lastName');
          this.email = storedEmail ? JSON.parse(storedEmail) : null;
          this.firstName = storedFirstName ? JSON.parse(storedFirstName) : null;
          this.lastName = storedLastName ? JSON.parse(storedLastName) : null;
        }
      }
    },

    startInactivityTimer(router) {

      if (this.inactivityTimeout) {
        clearTimeout(this.inactivityTimeout);
      }
      
      // Log out user after 10 minutes of inactivity
      this.inactivityTimeout = setTimeout(() => {
        this.logout(router);
        
        const toastStore = useToastStore();
        const langStore = useLanguageStore();
        toastStore.addToast({
          message: dictionary[langStore.language].inactivityLogout, 
          type: 'info',
          visible: true,
        });
      }, 600000); // 10 minutes
    },
  
    // Reset the inactivity timer on user activity
    resetInactivityTimer(router) {
      this.startInactivityTimer(router);
    },
    
    // Clear the inactivity timer 
    clearInactivityTimer() {
      if (this.inactivityTimeout) {
        clearTimeout(this.inactivityTimeout);
        this.inactivityTimeout = null;
      }
    },
  },
});
