<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue';
import { useDarkStore } from '@/stores/useDarkStore';

const darkStore = useDarkStore();
const canvas = ref(null);
let running = false;
let stars = [];

const COLORS = [
  [255, 255, 255],   // white
  [200, 220, 255],   // cool blue-white
  [255, 245, 210],   // warm yellow-white
];

function initStars(w, h) {
  const count = w < 768 ? 80 : 200;
  stars = Array.from({ length: count }, () => ({
    x: Math.random() * w,
    y: Math.random() * h,
    r: Math.random() * 1.2 + 0.3,
    speed: Math.random() * 0.003 + 0.0007,
    phase: Math.random() * Math.PI * 2,
    color: COLORS[Math.floor(Math.random() * COLORS.length)],
  }));
}

function draw(t) {
  if (!running) return;
  const c = canvas.value;
  if (!c) return;
  const ctx = c.getContext('2d');
  ctx.clearRect(0, 0, c.width, c.height);
  for (const s of stars) {
    const alpha = 0.15 + 0.85 * (0.5 + 0.5 * Math.sin(t * s.speed + s.phase));
    ctx.beginPath();
    ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2);
    ctx.fillStyle = `rgba(${s.color[0]},${s.color[1]},${s.color[2]},${alpha.toFixed(3)})`;
    ctx.fill();
  }
  requestAnimationFrame(draw);
}

function resize() {
  if (!canvas.value) return;
  canvas.value.width  = window.innerWidth;
  canvas.value.height = window.innerHeight;
  initStars(canvas.value.width, canvas.value.height);
}

function start() {
  if (running) return;
  running = true;
  resize();
  requestAnimationFrame(draw);
}

function stop() {
  running = false;
  if (canvas.value)
    canvas.value.getContext('2d').clearRect(0, 0, canvas.value.width, canvas.value.height);
}

watch(() => darkStore.isDark, (dark) => dark ? start() : stop());

onMounted(() => {
  window.addEventListener('resize', resize);
  if (darkStore.isDark) start();
});

onUnmounted(() => {
  stop();
  window.removeEventListener('resize', resize);
});
</script>

<template>
  <canvas
    v-show="darkStore.isDark"
    ref="canvas"
    class="fixed inset-0 w-full h-full pointer-events-none"
    style="z-index: 9; mix-blend-mode: screen;"
  />
</template>
