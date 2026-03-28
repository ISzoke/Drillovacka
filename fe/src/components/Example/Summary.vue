<!--
================================================================================
 Component: Summary.vue
 Description:
        Displays summary of current practicing session.
 Author: Dominik Horut (xhorut01)
================================================================================
-->

<script setup>
import { defineProps, computed, ref, onMounted, onUnmounted, watch, nextTick } from 'vue';
import { getTaskHistory } from '@/api/apiClient';
import { useRouter } from 'vue-router';
import { useLanguageStore } from '@/stores/useLanguageStore';
import { useRecorderStore } from '@/stores/useRecorderStore';
import { useAuthStore } from '@/stores/useAuthStore';
import { useGamificationStore } from '@/stores/useGamificationStore';
import {dictionary} from '@/utils/dictionary';

const props = defineProps({
    skipped:       { type: Number, required: true },
    noMistakes:    { type: Number, required: true },
    oneMistake:    { type: Number, required: true },
    twoMistakes:   { type: Number, required: true },
    threeMistakes: { type: Number, required: true },
    topics:        { type: Array,  required: true },
    taskId:        { type: Number, default: null },
    practiceSessionKey: { type: String, default: null },
});

const langStore  = useLanguageStore();
const router     = useRouter();
const recorderStore = useRecorderStore();
const authStore  = useAuthStore();
const gamStore   = useGamificationStore();

// ── Existing stats ────────────────────────────────────────────────────────────

const total = computed(() =>
    props.skipped + props.noMistakes + props.oneMistake + props.twoMistakes + props.threeMistakes
);

const getCorrectForm = computed(() => {
    if (langStore.language === 'en') return total.value === 1 ? 'example' : 'examples';
    if (langStore.language === 'sk') {
        if (total.value === 1) return 'príklad';
        if (total.value >= 2 && total.value <= 4) return 'príklady';
        return 'príkladov';
    }
    if (total.value === 1) return 'příklad';
    if (total.value >= 2 && total.value <= 4) return 'příklady';
    return 'příkladů';
});

const percentages = computed(() => ({
    skipped:      (props.skipped      / total.value) * 100,
    noMistakes:   (props.noMistakes   / total.value) * 100,
    oneMistake:   (props.oneMistake   / total.value) * 100,
    twoMistakes:  (props.twoMistakes  / total.value) * 100,
    threeMistakes:(props.threeMistakes/ total.value) * 100,
}));

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
    voice_first: 'Prvý hlas', voice_10: 'Hlasitý žiak', voice_50: 'Rečník',
    voice_100: 'Hlasový majster', voice_250: 'Virtuóz reči',
    top10_leaderboard: 'Top 10', top3_leaderboard: 'Stupne víťazov',
};

// ── Session comparison ────────────────────────────────────────────────────────

const sessionHistory = ref(null);
const barVisible     = ref(false);

const fmtTime = (ms) => {
    if (!ms) return '—';
    const s = ms / 1000;
    if (s < 60) return `${s.toFixed(1)} s`;
    return `${Math.floor(s / 60)} min ${Math.round(s % 60)} s`;
};

const currSession = computed(() =>
    sessionHistory.value?.length > 0
        ? sessionHistory.value[sessionHistory.value.length - 1]
        : null
);
const prevSession = computed(() =>
    sessionHistory.value?.length >= 2
        ? sessionHistory.value[sessionHistory.value.length - 2]
        : null
);

// negative = faster (good), positive = slower (bad)
const timeDeltaMs = computed(() => {
    if (!currSession.value?.avg_time || !prevSession.value?.avg_time) return null;
    return currSession.value.avg_time - prevSession.value.avg_time;
});

const masteryDelta = computed(() => {
    if (currSession.value === null || prevSession.value === null) return null;
    return currSession.value.mastery - prevSession.value.mastery;
});

const improved = computed(() =>
    (timeDeltaMs.value !== null && timeDeltaMs.value < 0) ||
    (masteryDelta.value !== null && masteryDelta.value > 0)
);

const congratsMessage = computed(() => {
    const faster = timeDeltaMs.value !== null && timeDeltaMs.value < 0;
    const more   = masteryDelta.value !== null && masteryDelta.value > 0;
    if (faster && more) return 'Skvelý výkon! Rýchlejšie aj viac zvládnuté! 🏆';
    if (faster)         return 'Rýchlejšie ako minule! 🚀';
    if (more)           return 'Zvládnutie sady stúplo! 🎯';
    return '';
});

// Bar gradient: violet for old portion, emerald for the new improvement
const barStyle = computed(() => {
    if (!currSession.value) return {};
    const w    = barVisible.value ? `${currSession.value.mastery}%` : '0%';
    const prev = prevSession.value?.mastery ?? 0;
    const curr = currSession.value.mastery;

    if (!prevSession.value || masteryDelta.value <= 0 || curr === 0) {
        return { width: w, backgroundColor: '#7c3aed', transition: 'width 1s ease-out' };
    }
    const splitPct = ((prev / curr) * 100).toFixed(2);
    return {
        width: w,
        background: `linear-gradient(to right, #7c3aed ${splitPct}%, #10b981 ${splitPct}%)`,
        transition: 'width 1.1s cubic-bezier(0.4,0,0.2,1)',
    };
});

// Trigger bar animation once data arrives
watch(sessionHistory, (val) => {
    if (val?.length > 0) {
        nextTick(() => setTimeout(() => { barVisible.value = true; }, 120));
    }
});

onMounted(async () => {
    if (props.taskId) {
        await new Promise(r => setTimeout(r, 650));
        try {
            const history = await getTaskHistory(props.taskId, authStore.id);
            if (history?.length > 0) sessionHistory.value = history;
        } catch (e) {}
    }
});

onUnmounted(() => {
    if (recorderStore.isRecording) recorderStore.stopRecording();
});

const backToMenu = () => {
    router.push({ path: langStore.language === 'en' ? '/en' : '/' });
};
</script>

<template>
    <div class="flex flex-col items-center justify-center mt-8 md:mt-16 rounded-3xl
                border-[3px] border-slate-200 dark:border-slate-700
                border-b-[8px] border-b-slate-300 dark:border-b-slate-600
                bg-white dark:bg-slate-800
                px-4 md:px-8 lg:px-16 py-8 max-w-full mx-4 shadow-sm">

        <h1 class="text-3xl md:text-5xl lg:text-6xl font-black text-slate-800 dark:text-slate-100">
            {{ dictionary[langStore.language].finish }}
        </h1>

        <h2 class="text-lg md:text-2xl font-bold text-slate-600 dark:text-slate-300 text-center mt-4">
            {{ dictionary[langStore.language].exampleCountText }} {{ total }} {{ getCorrectForm }}
        </h2>

        <!-- Ratio bar -->
        <div class="w-full md:max-w-3xl h-8 md:h-12 flex rounded-full overflow-hidden mt-8 md:mt-12">
            <div class="bg-gray-400  h-full" :style="{ width: percentages.skipped      + '%' }"></div>
            <div class="bg-green-500 h-full" :style="{ width: percentages.noMistakes   + '%' }"></div>
            <div class="bg-yellow-400 h-full":style="{ width: percentages.oneMistake   + '%' }"></div>
            <div class="bg-orange-400 h-full":style="{ width: percentages.twoMistakes  + '%' }"></div>
            <div class="bg-red-500   h-full" :style="{ width: percentages.threeMistakes+ '%' }"></div>
        </div>

        <!-- Legend -->
        <div class="grid grid-cols-1 md:flex md:justify-center md:space-x-4 mt-4 text-base font-medium md:text-sm">
            <div v-if="props.skipped      > 0" class="flex items-center space-x-2">
                <span class="block w-3 h-3 md:w-4 md:h-4 bg-gray-400   rounded-full"></span>
                <span>{{ dictionary[langStore.language].skipped      }} ({{ props.skipped }})</span>
            </div>
            <div v-if="props.noMistakes   > 0" class="flex items-center space-x-2">
                <span class="block w-3 h-3 md:w-4 md:h-4 bg-green-500  rounded-full"></span>
                <span>{{ dictionary[langStore.language].noMistakes   }} ({{ props.noMistakes }})</span>
            </div>
            <div v-if="props.oneMistake   > 0" class="flex items-center space-x-2">
                <span class="block w-3 h-3 md:w-4 md:h-4 bg-yellow-400 rounded-full"></span>
                <span>{{ dictionary[langStore.language].oneMistake   }} ({{ props.oneMistake }})</span>
            </div>
            <div v-if="props.twoMistakes  > 0" class="flex items-center space-x-2">
                <span class="block w-3 h-3 md:w-4 md:h-4 bg-orange-400 rounded-full"></span>
                <span>{{ dictionary[langStore.language].twoMistakes  }} ({{ props.twoMistakes }})</span>
            </div>
            <div v-if="props.threeMistakes> 0" class="flex items-center space-x-2">
                <span class="block w-3 h-3 md:w-4 md:h-4 bg-red-500    rounded-full"></span>
                <span>{{ dictionary[langStore.language].threeMistakes}} ({{ props.threeMistakes }})</span>
            </div>
        </div>

        <!-- ── Session comparison ──────────────────────────────────────────── -->
        <div v-if="currSession" class="w-full md:max-w-lg mt-8 flex flex-col gap-3">

            <!-- Congratulation banner -->
            <Transition name="congrats">
                <div v-if="improved"
                     class="w-full rounded-2xl px-5 py-4
                            bg-emerald-50 dark:bg-emerald-900/30
                            border-2 border-emerald-300 dark:border-emerald-600
                            flex items-center gap-3 shadow-sm">
                    <span class="text-3xl">🎉</span>
                    <div>
                        <div class="font-black text-emerald-700 dark:text-emerald-300 text-base leading-tight">
                            {{ congratsMessage }}
                        </div>
                        <div v-if="timeDeltaMs !== null && timeDeltaMs < 0"
                             class="text-xs font-semibold text-emerald-600 dark:text-emerald-400 mt-0.5">
                            Minulé sedenie: {{ fmtTime(prevSession.avg_time) }}
                        </div>
                    </div>
                </div>
            </Transition>

            <!-- Metric tiles -->
            <div class="grid grid-cols-2 gap-3">

                <!-- Avg time tile -->
                <div class="bg-slate-50 dark:bg-slate-900 rounded-2xl px-4 py-4 flex flex-col justify-between min-h-[100px]">
                    <div class="text-xs font-bold text-slate-400 dark:text-slate-500 mb-1">⏱ Priem. čas</div>
                    <div class="text-2xl font-black text-slate-800 dark:text-slate-100 leading-tight">
                        {{ fmtTime(currSession.avg_time) }}
                    </div>
                    <div v-if="timeDeltaMs !== null"
                         class="flex items-center gap-1 text-xs font-black mt-2"
                         :class="timeDeltaMs < 0
                             ? 'text-emerald-600 dark:text-emerald-400'
                             : 'text-red-500 dark:text-red-400'">
                        <span class="text-sm leading-none">{{ timeDeltaMs < 0 ? '▲' : '▼' }}</span>
                        {{ fmtTime(Math.abs(timeDeltaMs)) }}
                        <span class="font-semibold opacity-70">
                            {{ timeDeltaMs < 0 ? 'rýchlejšie' : 'pomalšie' }}
                        </span>
                    </div>
                    <div v-else class="text-xs text-slate-300 dark:text-slate-600 mt-2">prvé sedenie</div>
                </div>

                <!-- Mastery tile -->
                <div class="bg-slate-50 dark:bg-slate-900 rounded-2xl px-4 py-4 flex flex-col justify-between min-h-[100px]">
                    <div class="text-xs font-bold text-slate-400 dark:text-slate-500 mb-1">📈 Zvládnutie</div>
                    <div class="text-2xl font-black leading-tight"
                         :class="masteryDelta > 0 ? 'text-emerald-600 dark:text-emerald-400'
                               : masteryDelta < 0 ? 'text-red-500'
                               : 'text-violet-600 dark:text-violet-400'">
                        {{ currSession.mastery }}%
                    </div>
                    <div v-if="masteryDelta !== null"
                         class="flex items-center gap-1 text-xs font-black mt-2"
                         :class="masteryDelta > 0 ? 'text-emerald-600 dark:text-emerald-400'
                               : masteryDelta < 0 ? 'text-red-500'
                               : 'text-slate-400'">
                        <span v-if="masteryDelta !== 0" class="text-sm leading-none">
                            {{ masteryDelta > 0 ? '▲' : '▼' }}
                        </span>
                        <span v-if="masteryDelta !== 0">
                            {{ masteryDelta > 0 ? '+' : '' }}{{ masteryDelta }}%
                        </span>
                        <span v-else class="font-semibold opacity-70">nezmenené</span>
                    </div>
                    <div v-else class="text-xs text-slate-300 dark:text-slate-600 mt-2">prvé sedenie</div>
                </div>
            </div>

            <!-- Mastery progress bar -->
            <div class="bg-slate-50 dark:bg-slate-900 rounded-2xl px-4 pt-4 pb-3">
                <div class="flex justify-between text-xs font-bold text-slate-400 dark:text-slate-500 mb-3">
                    <span>Zvládnutie sady</span>
                    <span class="font-black"
                          :class="masteryDelta > 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-slate-500'">
                        {{ currSession.mastery }}%
                    </span>
                </div>

                <!-- Bar track -->
                <div class="relative w-full h-7 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden shadow-inner">
                    <!-- Main fill (violet = old, emerald = new improvement) -->
                    <div class="h-full rounded-full" :style="barStyle"></div>

                    <!-- Shimmer overlay on the new portion -->
                    <div v-if="masteryDelta > 0 && barVisible"
                         class="absolute top-0 h-full pointer-events-none bar-shimmer"
                         :style="{
                             left: (prevSession?.mastery || 0) + '%',
                             width: masteryDelta + '%',
                             borderRadius: '0 9999px 9999px 0',
                         }">
                    </div>
                </div>

                <!-- Labels below bar -->
                <div class="flex justify-between text-xs font-semibold mt-2">
                    <span v-if="prevSession" class="text-slate-400 dark:text-slate-500">
                        predtým {{ prevSession.mastery }}%
                    </span>
                    <span v-else></span>
                    <span v-if="masteryDelta > 0" class="text-emerald-600 dark:text-emerald-400 font-black">
                        +{{ masteryDelta }}% nové ✨
                    </span>
                </div>
            </div>
        </div>

        <!-- ── Gamification ────────────────────────────────────────────────── -->
        <div v-if="authStore.isAuthenticated && authStore.role !== 'admin'"
             class="mt-6 mb-2 flex flex-col items-center gap-3 w-full">
            <div v-if="gamStore.xp > 0"
                 class="flex items-center gap-3 bg-violet-50 dark:bg-violet-900/30
                        border border-violet-300 dark:border-violet-700 rounded-2xl px-6 py-3">
                <span class="text-3xl">⭐</span>
                <div>
                    <div class="font-bold text-violet-700 text-lg">Level {{ gamStore.level }}</div>
                    <div class="text-sm text-violet-500">{{ gamStore.xp }} XP celkom · 🔥 {{ gamStore.streak }} dní</div>
                </div>
            </div>
            <div v-if="gamStore.recentBadges.length > 0" class="flex flex-wrap justify-center gap-2">
                <div v-for="bkey in gamStore.recentBadges" :key="bkey"
                     class="flex items-center gap-1 bg-amber-50 dark:bg-amber-900/30
                            border border-amber-300 dark:border-amber-700
                            rounded-xl px-3 py-1 text-sm font-semibold text-amber-700 dark:text-amber-300">
                    🎖️ {{ BADGE_NAMES[bkey] || bkey }}
                </div>
            </div>
        </div>

        <!-- Back to menu -->
        <div class="flex justify-center mt-12 md:mt-16 mb-6 w-full">
            <button @click="backToMenu"
                class="text-center text-xl md:text-2xl font-black text-white
                       bg-violet-500 border-[3px] border-violet-600 border-b-[8px] border-b-violet-700
                       rounded-2xl px-8 py-4
                       hover:-translate-y-1 active:translate-y-1 active:border-b-[3px] transition-all">
                {{ dictionary[langStore.language].backtoMainMenu }}
            </button>
        </div>

    </div>
</template>

<style scoped>
/* Congratulation card drop-in */
.congrats-enter-from  { opacity: 0; transform: translateY(-10px) scale(0.97); }
.congrats-enter-active { transition: all 0.5s cubic-bezier(0.34, 1.56, 0.64, 1); }

/* Shimmer on the new mastery portion */
@keyframes shimmer {
    0%   { background: rgba(255, 255, 255, 0); }
    50%  { background: rgba(255, 255, 255, 0.22); }
    100% { background: rgba(255, 255, 255, 0); }
}
.bar-shimmer {
    animation: shimmer 2s ease-in-out infinite;
}
</style>
