<script setup>
const props = defineProps({
  modelValue: { type: Boolean, default: false },
});
const emit = defineEmits(['update:modelValue']);
const toggle = () => emit('update:modelValue', !props.modelValue);
</script>

<template>
  <button type="button" role="switch" :aria-checked="modelValue" @click="toggle"
          class="relative inline-flex h-5 w-9 flex-shrink-0 items-center rounded-full transition-colors
                 focus:outline-none focus:ring-2 focus:ring-secondary/40"
          :class="modelValue ? 'bg-secondary' : 'bg-slate-300 dark:bg-slate-600'">
    <span class="inline-block h-4 w-4 transform rounded-full bg-white shadow transition-transform"
          :class="modelValue ? 'translate-x-[18px]' : 'translate-x-0.5'" />
  </button>
</template>
