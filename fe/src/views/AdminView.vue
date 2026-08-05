<!--
================================================================================
 Component: AdminView.vue
 Description:
        Displays admin login page.
 Author: Dominik Horut (xhorut01)
================================================================================
-->

<script setup>
import AdminLogin from '@/components/Profile/AdminLogin.vue';
import { useI18n } from 'vue-i18n';
import { useAuthStore } from '@/stores/useAuthStore';

const authStore = useAuthStore();
const { t } = useI18n();
</script>

<template>
    <div class="pt-24">

        <!-- Placeholder if logged in -->
        <div v-if="authStore.isAuthenticated" class="text-2xl text-primary text-center font-bold pt-12">
            {{ t('adminWelcomeMessage', { name: authStore.name }) }}
        </div>
        
        <AdminLogin v-else></AdminLogin>

    </div>

</template>