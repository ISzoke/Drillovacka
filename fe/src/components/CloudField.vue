<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue';
import { useDarkStore } from '@/stores/useDarkStore';

const darkStore = useDarkStore();
const canvas = ref(null);
let running = false;
let clouds = [];

const CLOUD_W = 175;

function makeCloud(w, h, spread = true) {
  const scale = Math.random() * 0.9 + 0.4;
  return {
    x: spread ? Math.random() * (w + CLOUD_W * scale) - CLOUD_W * scale : -CLOUD_W * scale,
    y: Math.random() * h * 0.65 + 40,
    scale,
    speed: Math.random() * 0.15 + 0.05,
    opacity: Math.random() * 0.2 + 0.55,
  };
}

function initClouds(w, h) {
  const count = w < 768 ? 4 : 7;
  clouds = Array.from({ length: count }, () => makeCloud(w, h, true));
}

function drawCloudAt(ctx, x, y, scale, opacity) {
  ctx.save();
  ctx.globalAlpha = opacity;
  ctx.fillStyle = 'rgb(205, 220, 240)';
  ctx.translate(x, y);
  ctx.scale(scale, scale);
  ctx.beginPath();
  ctx.arc(25,  0,  25, 0, Math.PI * 2);
  ctx.arc(65, -15, 35, 0, Math.PI * 2);
  ctx.arc(110, -5, 30, 0, Math.PI * 2);
  ctx.arc(85,  15, 22, 0, Math.PI * 2);
  ctx.arc(45,  15, 22, 0, Math.PI * 2);
  ctx.fill();
  ctx.restore();
}

function draw() {
  if (!running) return;
  const c = canvas.value;
  if (!c) return;
  const ctx = c.getContext('2d');
  ctx.clearRect(0, 0, c.width, c.height);
  for (const cl of clouds) {
    drawCloudAt(ctx, cl.x, cl.y, cl.scale, cl.opacity);
    cl.x += cl.speed;
    if (cl.x > c.width + CLOUD_W * cl.scale) {
      cl.x = -CLOUD_W * cl.scale;
      cl.y = Math.random() * c.height * 0.65 + 40;
    }
  }
  requestAnimationFrame(draw);
}

function resize() {
  if (!canvas.value) return;
  canvas.value.width = window.innerWidth;
  canvas.value.height = window.innerHeight;
  initClouds(canvas.value.width, canvas.value.height);
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

watch(() => darkStore.isDark, (dark) => dark ? stop() : start());

onMounted(() => {
  window.addEventListener('resize', resize);
  if (!darkStore.isDark) start();
});

onUnmounted(() => {
  stop();
  window.removeEventListener('resize', resize);
});
</script>

<template>
  <canvas
    v-show="!darkStore.isDark"
    ref="canvas"
    class="fixed inset-0 w-full h-full pointer-events-none"
    style="z-index: 8; mix-blend-mode: multiply;"
  />
</template>
