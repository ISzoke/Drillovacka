import { defineStore } from 'pinia'
import { ref } from 'vue'
import axios from 'axios'

export const useGamificationStore = defineStore('gamification', () => {
  const xp = ref(0)
  const level = ref(1)
  const streak = ref(0)
  const longestStreak = ref(0)
  const badges = ref([])
  const rank = ref(null)
  const leaderboard = ref([])
  const solvedCount = ref(0)
  const levelXpStart = ref(0)
  const levelXpEnd = ref(50)

  // Transient per-answer state (cleared after showing animation)
  const lastXpAwarded = ref(0)
  const recentBadges = ref([])  // keys of badges just earned
  const xpBreakdown = ref(null) // { base, multiplier, voice_bonus, grade_comparison, example_grade, student_grade }

  async function fetchStats(studentId) {
    if (!studentId) return
    try {
      const res = await axios.get(`/api/gamification/student/${studentId}/stats/`)
      xp.value = res.data.total_xp
      level.value = res.data.level
      streak.value = res.data.current_streak
      longestStreak.value = res.data.longest_streak
      rank.value = res.data.rank
      badges.value = res.data.badges
      solvedCount.value = res.data.solved_count
      levelXpStart.value = res.data.level_xp_start
      levelXpEnd.value = res.data.level_xp_end
    } catch (e) {
      console.error('[gamificationStore] fetchStats error:', e)
    }
  }

  async function fetchLeaderboard() {
    try {
      const res = await axios.get('/api/gamification/leaderboard/')
      leaderboard.value = res.data
    } catch (e) {
      console.error('[gamificationStore] fetchLeaderboard error:', e)
    }
  }

  function handleXPUpdate(data) {
    if (data.xp_awarded === undefined) return
    xp.value = data.total_xp
    level.value = data.level
    streak.value = data.streak
    lastXpAwarded.value = data.xp_awarded
    recentBadges.value = data.new_badges || []
    xpBreakdown.value = data.xp_breakdown || null

    // Recalculate level thresholds
    const lvl = data.level
    levelXpStart.value = Math.pow(lvl - 1, 2) * 50
    levelXpEnd.value = Math.pow(lvl, 2) * 50
  }

  function clearTransient() {
    lastXpAwarded.value = 0
    recentBadges.value = []
    xpBreakdown.value = null
  }

  // Percentage progress within current level (0-100)
  function levelPercent() {
    const range = levelXpEnd.value - levelXpStart.value
    if (range <= 0) return 100
    return Math.min(100, Math.round(((xp.value - levelXpStart.value) / range) * 100))
  }

  return {
    xp, level, streak, longestStreak, badges, rank, leaderboard,
    solvedCount, levelXpStart, levelXpEnd, lastXpAwarded, recentBadges, xpBreakdown,
    fetchStats, fetchLeaderboard, handleXPUpdate, clearTransient, levelPercent,
  }
})
