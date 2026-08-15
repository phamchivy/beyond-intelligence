<script setup lang="ts">
interface Props {
  src: string
  timestamps: ViolationTimestamp[]
  loading?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  loading: false
})

const emit = defineEmits<{
  (e: 'select-timestamp', item: ViolationTimestamp): void
}>()

const videoRef = useTemplateRef<HTMLVideoElement>('videoRef')
const isPlaying = ref(false)
const currentTime = ref(0)
const duration = ref(0)
const selectedTimestamp = ref<ViolationTimestamp | null>(null)

const togglePlay = () => {
  if (!videoRef.value) return
  if (videoRef.value.paused) {
    videoRef.value.play()
    isPlaying.value = true
  } else {
    videoRef.value.pause()
    isPlaying.value = false
  }
}

const onTimeUpdate = () => {
  if (!videoRef.value) return
  currentTime.value = videoRef.value.currentTime
}

const onLoadedMetadata = () => {
  if (!videoRef.value) return
  duration.value = videoRef.value.duration
}

const jumpTo = (item: ViolationTimestamp) => {
  if (!videoRef.value) return
  videoRef.value.currentTime = item.timeInSeconds
  selectedTimestamp.value = item
  emit('select-timestamp', item)
}

const formatTime = (seconds: number) => {
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
}

const getSeverityBadgeColor = (severity: string) => {
  switch (severity) {
    case 'critical': return 'error'
    case 'warning': return 'warning'
    default: return 'info'
  }
}
</script>

<template>
  <UCard :ui="{ body: 'p-0 sm:p-0 overflow-hidden' }">
    <div v-if="loading" class="aspect-video w-full flex items-center justify-center bg-muted/30">
      <div class="flex flex-col items-center gap-2">
        <UIcon name="i-lucide-loader-2" class="size-8 animate-spin text-primary" />
        <span class="text-xs text-muted">Đang giải mã khung hình Video AI...</span>
      </div>
    </div>

    <div v-else class="flex flex-col">
      <!-- Video Frame & Marker Overlay -->
      <div class="relative aspect-video bg-black flex items-center justify-center group overflow-hidden">
        <video
          ref="videoRef"
          :src="src"
          class="w-full h-full object-contain"
          @timeupdate="onTimeUpdate"
          @loadedmetadata="onLoadedMetadata"
          @play="isPlaying = true"
          @pause="isPlaying = false"
        />

        <!-- Center Big Play Button Overlay -->
        <button
          class="absolute inset-0 flex items-center justify-center bg-black/20 group-hover:bg-black/40 transition-colors"
          @click="togglePlay"
        >
          <div
            v-if="!isPlaying"
            class="size-14 rounded-full bg-elevated/90 text-highlighted flex items-center justify-center shadow-lg transform transition group-hover:scale-110"
          >
            <UIcon name="i-lucide-play" class="size-7 translate-x-0.5" />
          </div>
        </button>

        <!-- Dynamic AI Risk Warning Pill at Timestamp -->
        <div
          v-if="selectedTimestamp"
          class="absolute top-3 left-3 bg-elevated/90 backdrop-blur-md px-3 py-1.5 rounded-lg border border-default shadow-md flex items-center gap-2 animate-fade-in"
        >
          <UBadge :color="getSeverityBadgeColor(selectedTimestamp.severity)" variant="solid" size="xs">
            {{ selectedTimestamp.ruleCode }}
          </UBadge>
          <span class="text-xs font-medium text-highlighted">{{ selectedTimestamp.label }}</span>
        </div>
      </div>

      <!-- Interactive Timeline with Violation Ticks -->
      <div class="p-4 bg-elevated border-t border-muted flex flex-col gap-3">
        <!-- Progress Bar with Marker Pointers -->
        <div class="relative w-full h-3 bg-muted/60 rounded-full flex items-center cursor-pointer">
          <div
            class="h-full bg-primary rounded-full relative"
            :style="{ width: `${duration ? (currentTime / duration) * 100 : 0}%` }"
          />

          <!-- Render Violation Pins on Timeline -->
          <button
            v-for="item in timestamps"
            :key="item.id"
            class="absolute -top-1 size-5 -ml-2.5 rounded-full border-2 border-elevated flex items-center justify-center shadow-xs transition transform hover:scale-125 z-10"
            :class="[
              item.severity === 'critical' ? 'bg-red-500' :
              item.severity === 'warning' ? 'bg-amber-500' : 'bg-sky-500'
            ]"
            :style="{ left: `${duration ? (item.timeInSeconds / duration) * 100 : 0}%` }"
            :title="`${item.timestampFormatted} - ${item.label}`"
            @click.stop="jumpTo(item)"
          >
            <span class="size-1.5 rounded-full bg-white" />
          </button>
        </div>

        <!-- Controls Bar -->
        <div class="flex items-center justify-between text-xs text-muted">
          <div class="flex items-center gap-2">
            <UButton
              :icon="isPlaying ? 'i-lucide-pause' : 'i-lucide-play'"
              variant="ghost"
              color="neutral"
              size="xs"
              @click="togglePlay"
            />
            <span class="font-mono text-highlighted">
              {{ formatTime(currentTime) }} / {{ formatTime(duration) }}
            </span>
          </div>

          <div class="flex items-center gap-1.5">
            <span class="text-muted">Vi phạm phát hiện:</span>
            <UBadge color="error" variant="subtle" size="xs">
              {{ timestamps.length }} điểm neo
            </UBadge>
          </div>
        </div>

        <!-- Timestamps Quick-Jump Ribbon -->
        <div class="pt-2 border-t border-muted/50 flex items-center gap-2 overflow-x-auto pb-1">
          <span class="text-xs text-muted shrink-0 font-medium">Tua nhanh:</span>
          <button
            v-for="item in timestamps"
            :key="item.id"
            class="shrink-0 text-xs px-2.5 py-1 rounded-md border flex items-center gap-1.5 transition-all"
            :class="[
              selectedTimestamp?.id === item.id
                ? 'bg-primary/10 border-primary text-primary font-medium'
                : 'bg-muted/30 border-muted text-muted hover:text-default hover:bg-muted/60'
            ]"
            @click="jumpTo(item)"
          >
            <span
              class="size-2 rounded-full"
              :class="[
                item.severity === 'critical' ? 'bg-red-500' :
                item.severity === 'warning' ? 'bg-amber-500' : 'bg-sky-500'
              ]"
            />
            <span class="font-mono font-bold">{{ item.timestampFormatted }}</span>
            <span class="truncate max-w-27.5">{{ item.label }}</span>
          </button>
        </div>
      </div>
    </div>
  </UCard>
</template>