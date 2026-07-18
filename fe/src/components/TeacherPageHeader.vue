<script setup>
defineProps({
  crumbs: { type: Array, default: () => [] }, // [{ label, to }]
  current: { type: String, default: '' },
  title: { type: String, required: true },
  subtitle: { type: String, default: '' },
});
</script>

<template>
  <div class="mb-6">
    <div v-if="crumbs.length || current" class="flex items-center gap-1.5 text-xs text-gray-400 mb-2.5">
      <template v-for="(c, i) in crumbs" :key="i">
        <router-link :to="c.to" class="text-slate-500 dark:text-slate-400 hover:text-secondary hover:underline">{{ c.label }}</router-link>
        <span>/</span>
      </template>
      <span v-if="current">{{ current }}</span>
    </div>
    <div class="flex items-start justify-between gap-4">
      <div>
        <h1 class="text-2xl font-bold text-primary dark:text-white tracking-tight">{{ title }}</h1>
        <p v-if="subtitle" class="text-sm text-gray-500 dark:text-gray-400 mt-1">{{ subtitle }}</p>
      </div>
      <div class="flex-shrink-0"><slot name="action" /></div>
    </div>
  </div>
</template>
