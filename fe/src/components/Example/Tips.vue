<!--
================================================================================
 Component: Tips.vue
 Description:
        Displays tips how to enter answers by voice.
 Author: Dominik Horut (xhorut01)
================================================================================
-->

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue';
import { useI18n } from 'vue-i18n';
import { useLanguageStore } from "@/stores/useLanguageStore";

const langStore = useLanguageStore();
const { t } = useI18n();

const showTips = ref(false);

const isMobile = ref(false);

// Toggle tips visibility
const toggleShowTips = () => {
    showTips.value = !showTips.value;
};

// Check if the screen size is mobile to display close button of the tips
const checkIfMobile = () => {
    isMobile.value = window.matchMedia('(max-width: 768px)').matches;
};

// Listen for screen size changes
onMounted(() => {
    checkIfMobile();
    window.addEventListener('resize', checkIfMobile);
});

// Cleanup event listener
onBeforeUnmount(() => {
    window.removeEventListener('resize', checkIfMobile);
});
</script>

<template>
    <div class="relative z-40">

        <!-- Button to show tips -->
        <button 
            @click="isMobile ? toggleShowTips() : null" 
            @mouseenter="!isMobile ? showTips = true : null" 
            @mouseleave="!isMobile ? showTips = false : null"
            class="text-3xl font-black text-slate-600 dark:text-slate-300 bg-slate-100 dark:bg-slate-700 w-12 h-12
            flex items-center justify-center rounded-full border-[3px] border-slate-300 dark:border-slate-500 border-b-[5px] border-b-slate-400 dark:border-b-slate-600
            transition-all hover:-translate-y-0.5 active:translate-y-1 active:border-b-[3px] shadow-md relative md:z-50">
            ?
        </button>

        <div v-if="showTips" class="fixed top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2
            w-11/12 md:w-1/2 bg-white dark:bg-slate-800 border-[3px] border-slate-200 dark:border-slate-700 border-b-[8px] border-b-slate-300 dark:border-b-slate-600
            shadow-2xl rounded-3xl p-6 text-lg text-slate-800 dark:text-slate-100 transition-all duration-300 ease-in-out z-50">

            <h3 class="text-xl font-black text-center mb-4 text-violet-600 dark:text-violet-400">{{ t('tipsTitle') }}</h3>

            <!-- Close button for mobiles which cant use hover -->
            <button v-if="isMobile" @click="showTips = false" class="absolute top-4 right-4 text-4xl text-slate-400 dark:text-slate-500 hover:text-slate-600 dark:hover:text-slate-300">
                <i class="fas fa-times"></i>
            </button>

            <!-- Tips -->
            <ul class="list-disc pl-6 space-y-8">

                <li class="flex flex-col space-y-2 pb-2 border-b border-slate-200 dark:border-slate-700 text-[15px] md:text-lg">
                    <span class="flex items-center font-semibold">
                        {{ t('tipsStart') }}
                        <div class="w-8 h-8 rounded-full bg-emerald-500 flex justify-center items-center ml-2 shadow-md">
                            <i class="fas fa-microphone text-white"></i>
                        </div>
                    </span>
                </li>

                <li class="flex flex-col space-y-2 pb-2 border-b border-slate-200 dark:border-slate-700 text-[15px] md:text-lg">
                    <span class="flex items-center font-semibold">
                        {{ t('tipsStop') }}
                        <div class="w-8 h-8 rounded-full bg-red-500 flex justify-center items-center ml-2 shadow-md">
                            <i class="fas fa-stop text-white"></i>
                        </div>
                    </span>
                </li>

                <li class="flex flex-col space-y-2 text-[15px] md:text-lg">
                    <span class="font-semibold text-slate-500 dark:text-slate-400 text-sm">
                        {{ t('micConsentText') }}
                    </span>
                </li>

            </ul>

        </div>
        
    </div>
</template>
