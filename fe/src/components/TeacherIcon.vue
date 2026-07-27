<script setup>
defineProps({
  name: { type: String, required: true },
  size: { type: [String, Number], default: 15 },
});

const PATHS = {
  edit: 'M16.5 3.5a2.12 2.12 0 013 3L7 19l-4 1 1-4L16.5 3.5z',
  delete: 'M4 7h16|M6 7l1 13a2 2 0 002 2h6a2 2 0 002-2l1-13|M9 7V4a1 1 0 011-1h4a1 1 0 011 1v3|M10 11v6M14 11v6',
  remove: 'M9 15l-5-5 5-5|M4 10h10a6 6 0 016 6v1',
  check: 'M5 12.5l4.5 4.5L19 7',
  calendar: 'M3.5 9.5h17|M8 3v4M16 3v4',
  lock: 'M8 11V7.5a4 4 0 018 0V11',
  person: 'M5 20c0-3.6 3.1-6.2 7-6.2s7 2.6 7 6.2',
  chevronDown: 'M6 9l6 6 6-6',
  plus: 'M12 5v14M5 12h14',
  sparkle: 'M12 2.5l1.9 5.6 5.6 1.9-5.6 1.9L12 17.5l-1.9-5.6-5.6-1.9 5.6-1.9L12 2.5z|M19.5 14l.9 2.6 2.6.9-2.6.9-.9 2.6-.9-2.6-2.6-.9 2.6-.9.9-2.6z',
  library: 'M4 5.5A2.5 2.5 0 016.5 3H20v15.5H6.5A2.5 2.5 0 004 21V5.5z|M4 21a2.5 2.5 0 012.5-2.5H20',
  print: 'M7 8V3.5h10V8|M7 17H4.5a1.5 1.5 0 01-1.5-1.5v-6A1.5 1.5 0 014.5 8h15a1.5 1.5 0 011.5 1.5v6a1.5 1.5 0 01-1.5 1.5H17|M7 13.5h10v7H7z',
  search: 'M16 16l4.5 4.5',
  minus: 'M5 12h14',
  close: 'M6 6l12 12M18 6L6 18',
  grip: 'M9 5.5h.01M9 12h.01M9 18.5h.01M15 5.5h.01M15 12h.01M15 18.5h.01',
  download: 'M12 3v12|M7 10.5l5 4.5 5-4.5|M4 20.5h16',
  settings: 'M4 6.5h10M18 6.5h2|M4 12h2M10 12h10|M4 17.5h10M18 17.5h2',
  eye: 'M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12z',
  book: 'M4 5.5A2.5 2.5 0 016.5 3H12v18H6.5A2.5 2.5 0 004 18.5V5.5z|M20 5.5A2.5 2.5 0 0017.5 3H12v18h5.5a2.5 2.5 0 002.5-2.5V5.5z',
  reset: 'M4 12a8 8 0 108-8 8.2 8.2 0 00-6 2.7L4 9|M4 4v5h5',
};

const RECTS = {
  delete: null,
  calendar: { x: 3.5, y: 5, width: 17, height: 15.5, rx: 2 },
  lock: { x: 5, y: 11, width: 14, height: 9, rx: 2 },
};

const CIRCLES = {
  person: { cx: 12, cy: 8, r: 3.4 },
  search: { cx: 10.5, cy: 10.5, r: 6.5 },
  settings: null,
  eye: { cx: 12, cy: 12, r: 2.8 },
};

const EXTRA_CIRCLES = {
  settings: [{ cx: 16, cy: 6.5, r: 2 }, { cx: 8, cy: 12, r: 2 }, { cx: 16, cy: 17.5, r: 2 }],
};
</script>

<template>
  <svg :width="size" :height="size" viewBox="0 0 24 24" fill="none" stroke="currentColor"
       stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round">
    <rect v-if="RECTS[name]" v-bind="RECTS[name]" />
    <circle v-if="CIRCLES[name]" v-bind="CIRCLES[name]" />
    <circle v-for="(c, i) in EXTRA_CIRCLES[name] || []" :key="'c' + i" v-bind="c" />
    <path v-for="(d, i) in PATHS[name]?.split('|')" :key="i" :d="d" />
  </svg>
</template>
