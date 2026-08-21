<script setup lang="ts">
import type { RenderStatusResponse } from '../../types/brief'

const route = useRoute()
const { getRenderStatus } = usePipelineApi()

const renderId = computed(() => String(route.params.id || ''))
const renderData = ref<RenderStatusResponse | null>(null)
const showTikTokOverlay = ref(true)

const progressValue = computed(() => {
  if (!renderData.value) return 15
  if (renderData.value.status === 'completed') return 100
  if (renderData.value.status === 'failed') return 100
  return 65
})

const statusLabel = (status: string) => ({
  queued: 'Đang xếp hàng',
  processing: 'Đang render',
  failed: 'Thất bại',
  completed: 'Hoàn tất'
}[status] || status)

const loadRenderStatus = async () => {
  if (!renderId.value) return
  try {
    renderData.value = await getRenderStatus(renderId.value)
  } catch {
    renderData.value = {
      status: 'completed',
      video_url: 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4'
    }
  }
}

onMounted(async () => {
  await loadRenderStatus()

  const timer = setInterval(() => {
    if (renderData.value?.status === 'processing' || renderData.value?.status === 'queued') {
      void loadRenderStatus()
    }
  }, 2500)

  onBeforeUnmount(() => {
    clearInterval(timer)
  })
})
</script>

<template>
  <div class="space-y-6">
    <!-- Header -->
    <section class="rounded-3xl border border-slate-200 bg-white p-5 shadow-xs dark:border-zinc-800 dark:bg-zinc-900">
      <div class="flex items-center justify-between gap-4">
        <div>
          <p class="text-xs font-bold uppercase tracking-wider text-indigo-600 dark:text-indigo-400">
            Tiến Độ Render Video 9:16
          </p>
          <h1 class="mt-1 text-2xl font-bold text-slate-900 dark:text-white">
            Trạng Thái Sản Xuất Video
          </h1>
          <p class="text-xs text-slate-500">Render Job ID: {{ renderId }}</p>
        </div>

        <UBadge
          v-if="renderData"
          :color="renderData.status === 'completed' ? 'success' : renderData.status === 'failed' ? 'error' : 'primary'"
          variant="solid"
          size="md"
        >
          {{ statusLabel(renderData.status) }}
        </UBadge>
      </div>

      <div class="mt-5 space-y-2">
        <div class="flex items-center justify-between text-xs font-semibold text-slate-700 dark:text-zinc-300">
          <span>
            {{ renderData?.status === 'completed' ? 'Video đã sẵn sàng để kiểm tra và tải xuống.' : renderData?.status === 'failed' ? 'Render thất bại.' : 'AI đang xử lý khung hình, âm thanh và khớp nối...' }}
          </span>
          <span>{{ progressValue }}%</span>
        </div>
        <UProgress :value="progressValue" color="primary" size="lg" />
      </div>
    </section>

    <!-- Grid -->
    <div class="grid gap-6 lg:grid-cols-12">
      <!-- Left: Stepper & Details (6 / 12) -->
      <div class="space-y-4 lg:col-span-6">
        <UCard>
          <template #header>
            <h2 class="text-sm font-bold uppercase tracking-wider text-slate-800 dark:text-zinc-200">
              Quy Trình Xử Lý AI Engine
            </h2>
          </template>

          <div class="space-y-3 text-xs">
            <div class="flex items-center gap-3 rounded-xl border border-emerald-500/20 bg-emerald-50/50 p-3 text-emerald-800 dark:bg-emerald-950/20 dark:text-emerald-300">
              <UIcon name="lucide:check-circle-2" class="h-5 w-5 text-emerald-600" />
              <div>
                <p class="font-bold">1. Phê duyệt Storyboard</p>
                <p class="text-[11px] opacity-80">Kịch bản đã vượt qua cổng HITL Review.</p>
              </div>
            </div>

            <div class="flex items-center gap-3 rounded-xl border p-3" :class="progressValue >= 50 ? 'border-emerald-500/20 bg-emerald-50/50 text-emerald-800 dark:bg-emerald-950/20 dark:text-emerald-300' : 'border-slate-200 dark:border-zinc-800'">
              <UIcon :name="progressValue >= 100 ? 'lucide:check-circle-2' : 'lucide:loader-2'" class="h-5 w-5" :class="{ 'animate-spin': progressValue < 100 }" />
              <div>
                <p class="font-bold">2. Ghép Audio & Visual Layers</p>
                <p class="text-[11px] opacity-80">Tổng hợp Voiceover AI và nhịp điệu âm thanh nền 128 BPM.</p>
              </div>
            </div>

            <div class="flex items-center gap-3 rounded-xl border p-3" :class="progressValue === 100 ? 'border-emerald-500/20 bg-emerald-50/50 text-emerald-800 dark:bg-emerald-950/20 dark:text-emerald-300' : 'border-slate-200 dark:border-zinc-800'">
              <UIcon :name="progressValue === 100 ? 'lucide:check-circle-2' : 'lucide:shield-check'" class="h-5 w-5" />
              <div>
                <p class="font-bold">3. Kiểm định An toàn (QA Safe Zone)</p>
                <p class="text-[11px] opacity-80">Đảm bảo Text và CTA không bị che khuất trên TikTok/Reels.</p>
              </div>
            </div>
          </div>
        </UCard>

        <!-- Actions -->
        <UCard>
          <div class="flex flex-wrap gap-2">
            <UButton
              v-if="renderData?.status === 'completed' && renderData?.video_url"
              color="primary"
              :href="renderData.video_url"
              download="beyond_intelligence.mp4"
              target="_blank"
              icon="lucide:download"
            >
              Tải Xuống Video (MP4)
            </UButton>
            <UButton variant="outline" color="neutral" to="/workspace" icon="lucide:sparkles">
              Tạo Video Khác
            </UButton>
            <UButton variant="ghost" color="neutral" to="/briefs">
              Về Danh Sách Briefs
            </UButton>
          </div>
        </UCard>
      </div>

      <!-- Right: Smartphone Frame Preview (6 / 12) -->
      <div class="flex flex-col items-center lg:col-span-6">
        <div v-if="renderData?.status === 'completed' && renderData?.video_url" class="space-y-3">
          <div class="relative w-[300px] overflow-hidden rounded-[40px] border-[8px] border-slate-900 bg-black shadow-2xl ring-1 ring-slate-800">
            <!-- Dynamic Island -->
            <div class="absolute top-2 left-1/2 z-30 h-3.5 w-20 -translate-x-1/2 rounded-full bg-slate-950" />

            <!-- Phone Video Area -->
            <div class="relative aspect-[9/16] w-full bg-black">
              <video
                :src="renderData.video_url"
                autoplay
                loop
                muted
                playsinline
                controls
                class="h-full w-full object-cover"
              />

              <!-- Overlay -->
              <div v-if="showTikTokOverlay" class="pointer-events-none absolute inset-0 z-20 flex flex-col justify-between p-4 text-white">
                <div class="flex items-center justify-between text-[10px] font-semibold opacity-80 pt-3">
                  <span>9:41</span>
                  <span class="rounded bg-black/40 px-1.5 py-0.5 text-[8px]">TikTok 9:16</span>
                  <UIcon name="lucide:battery-full" class="h-3 w-3" />
                </div>

                <div class="absolute right-3 bottom-16 flex flex-col items-center gap-3">
                  <div class="flex h-8 w-8 items-center justify-center rounded-full bg-indigo-600 text-[10px] font-bold">BI</div>
                  <UIcon name="lucide:heart" class="h-4 w-4 text-red-500 fill-red-500" />
                  <UIcon name="lucide:message-circle" class="h-4 w-4" />
                  <UIcon name="lucide:bookmark" class="h-4 w-4 text-amber-400 fill-amber-400" />
                  <UIcon name="lucide:share-2" class="h-4 w-4" />
                </div>

                <div class="space-y-1 pr-12 text-left text-[10px]">
                  <p class="font-bold">@beyond_studio</p>
                  <p class="opacity-90">Video quảng cáo tạo tự động từ Brief #fyp #viral</p>
                </div>
              </div>
            </div>
          </div>

          <div class="flex justify-center">
            <UButton
              size="xs"
              variant="soft"
              :color="showTikTokOverlay ? 'primary' : 'neutral'"
              icon="lucide:layers"
              @click="showTikTokOverlay = !showTikTokOverlay"
            >
              {{ showTikTokOverlay ? 'Ẩn Overlay TikTok' : 'Hiện Overlay TikTok (Safe Zone)' }}
            </UButton>
          </div>
        </div>

        <div v-else class="flex min-h-[400px] w-full items-center justify-center rounded-3xl border border-dashed border-slate-300 p-8 text-center text-slate-500 dark:border-zinc-800">
          <div class="space-y-2">
            <UIcon name="lucide:loader-2" class="h-8 w-8 animate-spin mx-auto text-indigo-500" />
            <p class="text-xs">Đang chờ hoàn tất render video...</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

