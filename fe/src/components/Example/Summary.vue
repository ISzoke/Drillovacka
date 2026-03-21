<!--
================================================================================
 Component: Summary.vue
 Description:
        Displays summary of current practicing session.
 Author: Dominik Horut (xhorut01)
================================================================================
-->

<script setup>
import { defineProps, computed, ref, onMounted, onUnmounted } from 'vue';
import { sendSurveyAnswer } from '@/api/apiClient';
import { useRouter } from 'vue-router';
import { useLanguageStore } from '@/stores/useLanguageStore';
import { useRecorderStore } from '@/stores/useRecorderStore';
import { useAuthStore } from '@/stores/useAuthStore';
import { useGamificationStore } from '@/stores/useGamificationStore';
import { getSessionId } from '@/utils/sessionManager';
import {dictionary} from '@/utils/dictionary';

const props = defineProps({
    skipped: {
        type: Number,
        required: true
    },
    noMistakes: {
        type: Number,
        required: true
    },
    oneMistake: {
        type: Number,
        required: true
    },
    twoMistakes: {
        type: Number,
        required: true
    },
    threeMistakes: {
        type: Number,
        required: true
    },
    topics: {
    type: Array,
    required: true
    } 
})

const langStore = useLanguageStore();
const router = useRouter();
const recorderStore = useRecorderStore();
const authStore = useAuthStore();
const gamStore = useGamificationStore();

const student_id = authStore.id || 0;
const session_id = student_id === 0 ? getSessionId() : null;

// Total number of practiced examples   
const total = computed(() => {
    return props.skipped + props.noMistakes + props.oneMistake + props.twoMistakes + props.threeMistakes;
});

// Get the correct form of the word 'priklad' or 'example' depending on selected language
const getCorrectForm = computed(() => {
    if (langStore.language === 'en') {
        return total.value === 1 ? 'example' : 'examples';
    } else if (langStore.language === 'sk') {
        if (total.value === 1) return 'príklad';
        if (total.value >= 2 && total.value <= 4) return 'príklady';
        return 'príkladov';
    } else {
        if (total.value === 1) return 'příklad';
        if (total.value >= 2 && total.value <= 4) return 'příklady';
        return 'příkladů';
    }
});
// Calculate percentages for each category
const percentages = computed(() => {
    return {
        skipped: (props.skipped / total.value) * 100,
        noMistakes: (props.noMistakes / total.value) * 100,
        oneMistake: (props.oneMistake / total.value) * 100,
        twoMistakes: (props.twoMistakes / total.value) * 100,
        threeMistakes: (props.threeMistakes / total.value) * 100
    };
});


const feedbackText = ref('');

const feedbackPrompt = {
    cs: 'Napíš, alebo řekni, čo se ti líbilo nebo co by jsi změnil/a...  ',
    en: 'Do you have any feedback for us? ',
    sk: 'Napíš, alebo povedz, čo sa ti páčilo alebo čo by si zmenil/a...  '
};

const feedbackPlaceholder = {
    cs: 'Napíš, čo sa ti páčilo alebo čo by si zmenil/a... ',
    en: 'Write what you liked or what should be improved... ',
    sk: 'Napíš, čo sa ti páčilo alebo čo by si zmenil/a... '
};

const feedbackQuestionByLang = {
    cs: 'Máš pre nás nejaký feedback?',
    en: 'Do you have any feedback for us?',
    sk: 'Máš pre nás nejaký feedback?'
};

const BADGE_NAMES = {
    first_correct: 'Prvý gól', ten_correct: 'Rozbehnutý', hundred_correct: 'Stovkár',
    three_hundred_correct: 'Výpočtový stroj', five_hundred_correct: 'Päťstovkár', thousand_correct: 'Tisícnik',
    five_skills: 'Zvedavec', ten_skills: 'Všestranný', twenty_skills: 'Encyklopédia',
    comeback: 'Tvrdohlavý', ten_in_a_row: 'Bez zakopnutia', twenty_five_in_a_row: 'Neomylný',
    perfect_session: 'Čistý štít', accuracy_master: 'Ostreľovač', accuracy_legend: 'Snajper',
    mastery_skill: 'Zvládnuté!', fast_answer: 'Rýchlik', lightning: 'Bleskovka',
    speed_demon: 'Šíp', speed_session: 'Na plné obrátky',
    streak_3: 'Tri dni v rade', streak_7: 'Celý týždeň', streak_14: 'Dvojtýždenník', streak_30: 'Mesiac v rade',
    level_5: 'Level 5', level_10: 'Dvojciferný', level_20: 'Veterán',
    top10_leaderboard: 'Top 10', top3_leaderboard: 'Stupne víťazov',
}

const isSubmitting = ref(false);
const feedbackSubmitted = ref(false);

const toggleAudioFeedback = () => {
    if (recorderStore.isRecording) {
        recorderStore.stopRecording();
    } else {
        recorderStore.startRecording(true);
    }
};

const confirmFeedback = async () => {
    isSubmitting.value = true;
    
    // Stop recording if still active
    if (recorderStore.isRecording) {
        recorderStore.stopRecording();
        // Wait for WebSocket to close and transcription to be saved
        await new Promise(resolve => setTimeout(resolve, 500));
    }

    const trimmedFeedback = feedbackText.value.trim();
    if (trimmedFeedback.length > 0) {
        await sendSurveyAnswer('final-feedback-text', feedbackQuestionByLang[langStore.language], trimmedFeedback, props.topics, student_id, session_id, langStore.language);
    }

    feedbackSubmitted.value = true;
    isSubmitting.value = false;
};

const backToMenu = () => {
    if (langStore.language === 'en') {
        router.push({ path: '/en' });
    } else {
        router.push({ path: '/' });
    }
};

onMounted(() => {
    recorderStore.updateSurveyQuestionData(feedbackQuestionByLang[langStore.language], props.topics, student_id, session_id, 'final-feedback-voice');
    console.log('[DEBUG Summary.vue] onMounted - student_id:', student_id, 'session_id:', session_id);
});

onUnmounted(() => {
    if (recorderStore.isRecording) {
        recorderStore.stopRecording();
    }
});
</script>

<template>
    <div class="flex flex-col items-center justify-center mt-12 md:mt-24 md:border-4 md:border-secondary rounded-xl px-12 md:px-24 py-4 max-w-full">

        <h1 class="text-5xl md:text-6xl font-bold text-primary">{{ dictionary[langStore.language].finish }}</h1>

        <!-- Total number of practiced examples -->
        <h2 class="text-lg md:text-2xl font-semibold text-primary text-center mt-4">
            {{dictionary[langStore.language].exampleCountText}} {{ total }} {{ getCorrectForm }}
        </h2>

        <!-- Bar indicating ratio of correctly answered examples, incorrect ones and skipped ones -->
        <div class="w-full md:max-w-3xl h-8 md:h-12 flex rounded-full overflow-hidden mt-8 md:mt-12">
            <!-- Skipped -->
            <div class="bg-gray-400 h-full" :style="{ width: percentages.skipped + '%' }"
                data-tooltip="Přeskočeno: {{ props.skipped }}"></div>

            <!-- No Mistakes -->
            <div class="bg-green-500 h-full" :style="{ width: percentages.noMistakes + '%' }"
                data-tooltip="Bez chyb: {{ props.noMistakes }}"></div>

            <!-- One Mistake -->
            <div class="bg-yellow-400 h-full" :style="{ width: percentages.oneMistake + '%' }"
                data-tooltip="Jedna chyba: {{ props.oneMistake }}"></div>

            <!-- Two Mistakes -->
            <div class="bg-orange-400 h-full " :style="{ width: percentages.twoMistakes + '%' }"
                data-tooltip="Dvě chyby: {{ props.twoMistakes }}"></div>

            <!-- Three Mistakes -->
            <div class="bg-red-500 h-full" :style="{ width: percentages.threeMistakes + '%' }"
                data-tooltip="Tři chyby: {{ props.threeMistakes }}"></div>
        </div>

        <!-- Legend -->
        <div class="grid grid-cols-1 md:flex md:justify-center md:space-x-4 mt-4 text-lg font-medium md:text-base">
            <div v-if="props.skipped > 0" class="flex items-center space-x-2">
                <span class="block w-3 h-3 md:w-4 md:h-4 bg-gray-400 rounded-full"></span>
                <span>{{ dictionary[langStore.language].skipped }} ({{ props.skipped }})</span>
            </div>
            <div v-if="props.noMistakes > 0" class="flex items-center space-x-2">
                <span class="block w-3 h-3 md:w-4 md:h-4 bg-green-500 rounded-full"></span>
                <span>{{ dictionary[langStore.language].noMistakes }} ({{ props.noMistakes }})</span>
            </div>
            <div v-if="props.oneMistake > 0" class="flex items-center space-x-2">
                <span class="block w-3 h-3 md:w-4 md:h-4 bg-yellow-400 rounded-full"></span>
                <span>{{ dictionary[langStore.language].oneMistake }} ({{ props.oneMistake }})</span>
            </div>
            <div v-if="props.twoMistakes > 0" class="flex items-center space-x-2">
                <span class="block w-3 h-3 md:w-4 md:h-4 bg-orange-400 rounded-full"></span>
                <span>{{ dictionary[langStore.language].twoMistakes }} ({{ props.twoMistakes }})</span>
            </div>
            <div v-if="props.threeMistakes > 0" class="flex items-center space-x-2">
                <span class="block w-3 h-3 md:w-4 md:h-4 bg-red-500 rounded-full"></span>
                <span>{{ dictionary[langStore.language].threeMistakes }} ({{ props.threeMistakes }})</span>
            </div>
        </div>

        <!-- Gamification: XP & badges earned this session -->
        <div v-if="authStore.isAuthenticated && authStore.role !== 'admin'" class="mt-6 mb-2 flex flex-col items-center gap-3 w-full">
            <!-- XP earned -->
            <div v-if="gamStore.xp > 0" class="flex items-center gap-3 bg-violet-50 border border-violet-300 rounded-2xl px-6 py-3">
                <span class="text-3xl">⭐</span>
                <div>
                    <div class="font-bold text-violet-700 text-lg">Level {{ gamStore.level }}</div>
                    <div class="text-sm text-violet-500">{{ gamStore.xp }} XP celkom · 🔥 {{ gamStore.streak }} dní</div>
                </div>
            </div>
            <!-- New badges earned during session -->
            <div v-if="gamStore.recentBadges.length > 0" class="flex flex-wrap justify-center gap-2">
                <div
                    v-for="bkey in gamStore.recentBadges"
                    :key="bkey"
                    class="flex items-center gap-1 bg-yellow-50 border border-yellow-300 rounded-xl px-3 py-1 text-sm font-semibold text-yellow-700">
                    🎖️ {{ BADGE_NAMES[bkey] || bkey }}
                </div>
            </div>
        </div>

        <!-- Final optional feedback section -->
        <div class="flex flex-col items-center my-8 md:my-12">
            <div class="flex justify-center text-center text-xl font-semibold mb-4">{{ feedbackPrompt[langStore.language] }}</div>

            <textarea
                v-model="feedbackText"
                :placeholder="feedbackPlaceholder[langStore.language]"
                :disabled="isSubmitting || feedbackSubmitted"
                rows="4"
                class="w-full md:w-[700px] max-w-full border-2 border-primary/40 rounded-xl px-4 py-3 text-lg focus:outline-none focus:border-primary disabled:opacity-50 disabled:cursor-not-allowed"
            />

            <div v-if="feedbackSubmitted" class="mt-4 text-green-600 font-semibold text-lg flex items-center justify-center">
                <i class="fas fa-check-circle mr-2"></i>
                {{ dictionary[langStore.language].feedbackSent }}
            </div>

            <div class="mt-6 flex flex-col items-center">
                <div class="text-md text-gray-700 mb-3">{{ dictionary[langStore.language].clickMicText }}</div>
                <button
                    @click="toggleAudioFeedback"
                    :disabled="isSubmitting || feedbackSubmitted"
                    :class="recorderStore.isRecording ? 'bg-red-500 hover:bg-red-600 border-red-600' : 'bg-green-500 hover:bg-green-600 border-green-600'"
                    class="w-16 h-16 flex items-center justify-center rounded-full border-4 text-white text-xl transition hover:scale-110 shadow-md focus:outline-none disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100"
                    :title="recorderStore.isRecording ? 'Stop Recording' : 'Start Recording'"
                >
                    <i :class="recorderStore.isRecording ? 'fas fa-stop' : 'fas fa-microphone'"></i>
                </button>
            </div>
            
            <!-- Confirm feedback button -->
            <div class="flex justify-center mt-6">
                <button
                    @click="confirmFeedback"
                    :disabled="isSubmitting || feedbackSubmitted || (feedbackText.trim().length === 0 && !recorderStore.isRecording)"
                    :class="(isSubmitting || feedbackSubmitted || (feedbackText.trim().length === 0 && !recorderStore.isRecording)) ? 'bg-gray-400 cursor-not-allowed opacity-75' : 'bg-primary hover:bg-primary/80'"
                    class="text-white text-lg md:text-xl font-semibold px-6 py-3 rounded-xl border-2 border-primary transition"
                >
                    <span v-if="isSubmitting">
                        <i class="fas fa-spinner fa-spin mr-2"></i>
                        {{ dictionary[langStore.language].saving }}
                    </span>
                    <span v-else-if="feedbackSubmitted">
                        <i class="fas fa-check mr-2"></i>
                        {{ dictionary[langStore.language].confirmed }}
                    </span>
                    <span v-else>
                        {{ dictionary[langStore.language].confirm }}
                    </span>
                </button>
            </div>
        </div>

        <!-- Button to go back to main menu -->
        <div class="flex justify-center mt-12 md:mt-16 mb-6 w-full">
            <button
                @click="backToMenu"
                class="text-center text-xl md:text-3xl bg-secondary hover:bg-white text-white hover:text-secondary border-4 border-secondary rounded-xl font-semibold px-3 py-2 md:px-4 md:py-2 transition"
            >
                {{ dictionary[langStore.language].backtoMainMenu }}
            </button>
        </div>

    </div>
</template>
