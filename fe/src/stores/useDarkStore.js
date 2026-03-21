import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

export const useDarkStore = defineStore('dark', () => {
  const stored = localStorage.getItem('darkMode')
  const isDark = ref(stored !== null ? stored === 'true' : true)

  watch(isDark, (val) => {
    localStorage.setItem('darkMode', String(val))
    document.documentElement.classList.toggle('dark', val)
  }, { immediate: true })

  function toggle() { isDark.value = !isDark.value }

  return { isDark, toggle }
})
