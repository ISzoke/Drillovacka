<!--
================================================================================
 Component: VerticalAudioVisualizer.vue
 Description:
        Vertical audio level visualizer with draggable threshold line for filtering
 Author: Martin Eugen Minarčík (xminarm00)
================================================================================
-->

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue';
import { useRecorderStore } from "@/stores/useRecorderStore";

const props = defineProps({
  backgroundColor: {
    type: String,
    default: "#f1faee"
  },
  barColor: {
    type: String,
    default: "#4ade80"
  },
  height: {
    type: Number,
    default: 65
  },
  width: {
    type: Number,
    default: 60
  }
});

const recorderStore = useRecorderStore();
const canvasRef = ref(null);
const analyser = ref(null);
const dataArray = ref(null);
const animationId = ref(null);
const currentAudioLevel = ref(0); // Track current audio level for dynamic color

// Define draggable range - reduced upper limit for better sensitivity
const minThresholdY = props.height * 0.05; // 5% from top
const maxThresholdY = props.height * 0.95; // 95% from top (5% from bottom)
const thresholdY = ref(props.height * 0.20); // Start at 20% from top
const isDraggingThreshold = ref(false);

// Convert pixel position to percentage (0-100)
const pixelsToPercentage = (pixels) => {
  const range = maxThresholdY - minThresholdY;
  return Math.round((100 * (maxThresholdY - pixels)) / range);
};

// Watch for recording state changes
watch(() => recorderStore.isRecording, (isRecording) => {
  if (isRecording) {
    setupAnalyser();
  } else {
    stopVisualization();
  }
});

onMounted(() => {
  if (recorderStore.isRecording) {
    setupAnalyser();
  } else {
    drawEmptyState();
  }
});

onUnmounted(() => {
  stopVisualization();
});

// Draw an empty or idle state
const drawEmptyState = () => {
  if (!canvasRef.value) return;
  
  const canvas = canvasRef.value;
  const ctx = canvas.getContext('2d');
  const width = canvas.width;
  const height = canvas.height;
  
  ctx.fillStyle = props.backgroundColor;
  ctx.fillRect(0, 0, width, height);
  
  // Draw threshold line (black)
  ctx.strokeStyle = '#000000';
  ctx.lineWidth = 3;
  ctx.setLineDash([]);
  ctx.beginPath();
  ctx.moveTo(0, thresholdY.value);
  ctx.lineTo(width, thresholdY.value);
  ctx.stroke();
};

// Set up audio analyser
const setupAnalyser = async () => {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    
    const audioContext = new (window.AudioContext || window.webkitAudioContext)();
    const source = audioContext.createMediaStreamSource(stream);
    
    analyser.value = audioContext.createAnalyser();
    analyser.value.fftSize = 256;
    
    source.connect(analyser.value);
    
    const bufferLength = analyser.value.frequencyBinCount;
    dataArray.value = new Uint8Array(bufferLength);
    
    startVisualization();

  } catch (error) {
    console.error("Error setting up vertical audio visualizer:", error);
  }
};

// Start visualization with vertical display
const startVisualization = () => {
  if (!canvasRef.value || !analyser.value || !dataArray.value) return;
  
  const canvas = canvasRef.value;
  const ctx = canvas.getContext('2d');
  const width = canvas.width;
  const height = canvas.height;
  
  const draw = () => {
    if (!recorderStore.isRecording) {
      cancelAnimationFrame(animationId.value);
      drawEmptyState();
      return;
    }
    
    animationId.value = requestAnimationFrame(draw);
    
    analyser.value.getByteFrequencyData(dataArray.value);
    
    // Background
    ctx.fillStyle = props.backgroundColor;
    ctx.fillRect(0, 0, width, height);
    
    // Calculate average audio level (0-255)
    let sum = 0;
    for (let i = 0; i < dataArray.value.length; i++) {
      sum += dataArray.value[i];
    }
    const averageLevel = Math.round(sum / dataArray.value.length);
    const normalizedLevel = (averageLevel / 255) * height;
    currentAudioLevel.value = normalizedLevel; // Update current audio level for dynamic colors
    
    // Draw audio level bar from bottom
    ctx.fillStyle = props.barColor;
    ctx.fillRect(0, height - normalizedLevel, width, normalizedLevel);
    
    // Draw threshold line: black normally, green when audio level reaches/exceeds threshold
    // Convert threshold Y (from top) to threshold from bottom for proper comparison
    const thresholdFromBottom = height - thresholdY.value;
    const isAudioAboveThreshold = normalizedLevel >= thresholdFromBottom;
    ctx.strokeStyle = isAudioAboveThreshold ? '#22c55e' : '#000000'; // Green if above, black if below
    ctx.lineWidth = isDraggingThreshold.value ? 4 : 3;
    ctx.setLineDash([]);
    ctx.beginPath();
    ctx.moveTo(0, thresholdY.value);
    ctx.lineTo(width, thresholdY.value);
    ctx.stroke();
    
    // Draw top labels
    ctx.fillStyle = '#64748b';
    ctx.font = '10px sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText('Max', width / 2, 10);
    ctx.fillText('0', width / 2, height - 5);
  };
  
  draw();
};

// Stop visualization
const stopVisualization = () => {
  if (animationId.value) {
    cancelAnimationFrame(animationId.value);
    animationId.value = null;
  }
  
  drawEmptyState();
};

// Handle threshold line dragging
const handleMouseDown = () => {
  isDraggingThreshold.value = true;
};

const handleMouseUp = () => {
  isDraggingThreshold.value = false;
};

const handleMouseMove = (event) => {
  if (!isDraggingThreshold.value) return;
  
  updateThresholdFromEvent(event);
};

const handleTouchMove = (event) => {
  if (!isDraggingThreshold.value) return;
  
  updateThresholdFromEvent(event.touches[0]);
};

const updateThresholdFromEvent = (event) => {
  if (!canvasRef.value) return;
  
  const rect = canvasRef.value.getBoundingClientRect();
  const y = event.clientY - rect.top;
  
  // Clamp to draggable range (70% of canvas = 15%-85%)
  thresholdY.value = Math.max(minThresholdY, Math.min(maxThresholdY, y));
  
  // Calculate percentage within constrained range (0-100)
  const percentage = Math.round(((maxThresholdY - thresholdY.value) / (maxThresholdY - minThresholdY)) * 100);
  recorderStore.setAudioThreshold(percentage);
};

const handleCanvasClick = (event) => {
  if (!canvasRef.value) return;
  
  const rect = canvasRef.value.getBoundingClientRect();
  const y = event.clientY - rect.top;
  
  // Clamp to draggable range (70% of canvas = 15%-85%)
  thresholdY.value = Math.max(minThresholdY, Math.min(maxThresholdY, y));
  
  // Calculate percentage within constrained range (0-100)
  const percentage = Math.round(((maxThresholdY - thresholdY.value) / (maxThresholdY - minThresholdY)) * 100);
  recorderStore.setAudioThreshold(percentage);
};
</script>

<template>
  <div class="relative inline-block" @mouseup="handleMouseUp" @mouseleave="handleMouseUp" @touchend="handleMouseUp">
    <canvas 
      ref="canvasRef" 
      :width="width" 
      :height="height"
      @click="handleCanvasClick"
      @mousedown="handleMouseDown"
      @mousemove="handleMouseMove"
      @touchstart="handleMouseDown"
      @touchmove="handleTouchMove"
      :style="{ cursor: isDraggingThreshold ? 'grabbing' : 'grab' }"
      class="border border-gray-300 rounded"
    ></canvas>
    
    <!-- Threshold indicator label -->
    <div class="absolute -right-20 text-xs font-semibold text-gray-800 whitespace-nowrap" :style="{ top: thresholdY + 'px', transform: 'translateY(-50%)' }">
      {{ Math.round(100 - ((thresholdY / height) * 100)) }}%
    </div>
  </div>
</template>
