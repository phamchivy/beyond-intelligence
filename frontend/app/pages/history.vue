<script setup lang="ts">
const { fetchApi } = useApi()

const normalizeStatus = (status: string) => {
  const normalized = String(status || '').toLowerCase()
  if (['draft', 'saved', 'new'].includes(normalized)) return 'draft'
  if (['submitted', 'queued', 'processing', 'reviewing', 'storyboard_review'].includes(normalized)) return 'storyboard_review'
  if (['rendering', 'render', 'render_processing'].includes(normalized)) return 'rendering'
  if (['done', 'completed', 'success'].includes(normalized)) return 'done'
  if (['failed', 'error'].includes(normalized)) return 'failed'
  return normalized || 'draft'
}

const { data: historyResponse, pending } = await useLazyAsyncData('video-history', () =>
  fetchApi<{ items: Array<Record<string, any>> }>('/briefs?page=1')
)

const videos = computed(() => {
  return (historyResponse.value?.items ?? []).map((brief: Record<string, any>) => ({
    id: brief.id,
    title: brief.title || brief.productName || 'Chiến dịch Video',
    platform: brief.channel || 'TikTok',
    status: normalizeStatus(brief.status),
    createdAt: brief.createdAt || new Date().toISOString(),
    hook: brief.keyMessage || brief.productUsp || 'Sản phẩm tối ưu cho cuộc sống hiện đại.',
    performance: brief.objective || 'Conversion',
    videoUrl: 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4'
  }))
})

const statusLabel = (status: string) => {
  const map: Record<string, string> = {
    draft: 'Bản nháp',
    storyboard_review: 'Chờ duyệt HITL',
    rendering: 'Đang render',
    done: 'Hoàn tất',
    failed: 'Thất bại'
  }
  return map[status] || status
}

const previewModalOpen = ref(false)
const selectedVideo = ref<any>(null)

const openPreview = (video: any) => {
  selectedVideo.value = video
  previewModalOpen.value = true
}
</script>

<template>
  <div class="space-y-6">
    <section class="flex flex-col gap-4 rounded-3xl border border-slate-200 bg-white p-6 shadow-xs dark:border-zinc-800 dark:bg-zinc-900 sm:flex-row sm:items-center sm:justify-between">
      <div>
        <p class="text-xs font-bold uppercase tracking-wider text-indigo-600 dark:text-indigo-400">Thư Viện Chiến Dịch</p>
        <h1 class="mt-1 text-2xl font-bold text-slate-900 dark:text-white">Lịch Sử Video & Assets Đã Tạo</h1>
      </div>

      <UButton to="/workspace" color="primary" icon="lucide:sparkles">
        Tạo Video Mới
      </UButton>
    </section>

    <div v-if="pending" class="grid gap-4 md:grid-cols-3">
      <USkeleton v-for="index in 3" :key="index" class="h-60 w-full rounded-2xl" />
    </div>

    <div v-else class="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
      <UCard v-for="video in videos" :key="video.id" class="flex flex-col justify-between">
        <template #header>
          <div class="flex items-center justify-between">
            <span class="text-xs font-bold uppercase tracking-wider text-indigo-600 dark:text-indigo-400">
              {{ video.platform }}
            </span>
            <UBadge :color="video.status === 'done' ? 'success' : 'warning'" size="xs" variant="subtle">
              {{ statusLabel(video.status) }}
            </UBadge>
          </div>
        </template>

        <div class="space-y-3">
          <div>
            <h2 class="text-base font-bold text-slate-900 dark:text-white">{{ video.title }}</h2>
            <p class="text-xs text-slate-500">{{ new Date(video.createdAt).toLocaleDateString('vi-VN') }}</p>
          </div>

          <div class="rounded-xl border border-slate-200 bg-slate-50/50 p-3 text-xs dark:border-zinc-800 dark:bg-zinc-900/50">
            <p class="font-bold uppercase text-[10px] text-slate-400">Key Hook</p>
            <p class="mt-0.5 text-slate-700 dark:text-zinc-200">{{ video.hook }}</p>
          </div>

          <div class="flex items-center justify-between text-xs text-slate-500">
            <span>Mục tiêu:</span>
            <span class="font-bold text-slate-800 dark:text-zinc-200">{{ video.performance }}</span>
          </div>
        </div>

        <template #footer>
          <div class="flex items-center justify-between gap-2">
            <UButton size="xs" variant="outline" color="neutral" icon="lucide:play" @click="openPreview(video)">
              Xem Video
            </UButton>
            <UButton size="xs" color="primary" variant="subtle" to="/workspace" icon="lucide:copy">
              Dùng Mẫu Này
            </UButton>
          </div>
        </template>
      </UCard>
    </div>

    <!-- Preview Modal -->
    <UModal v-model:open="previewModalOpen">
      <template #content>
        <div v-if="selectedVideo" class="p-6 space-y-4">
          <div class="flex items-center justify-between">
            <h3 class="text-base font-bold text-slate-900 dark:text-white">{{ selectedVideo.title }}</h3>
            <UBadge color="primary" size="xs">{{ selectedVideo.platform }} 9:16</UBadge>
          </div>

          <div class="flex justify-center">
            <div class="relative w-[260px] aspect-[9/16] overflow-hidden rounded-2xl bg-black shadow-xl">
              <video
                :src="selectedVideo.videoUrl"
                autoplay
                loop
                controls
                playsinline
                class="h-full w-full object-cover"
              />
            </div>
          </div>

          <div class="flex justify-between items-center pt-2">
            <UButton
              size="sm"
              color="primary"
              :href="selectedVideo.videoUrl"
              download="video.mp4"
              target="_blank"
              icon="lucide:download"
            >
              Tải Video
            </UButton>
            <UButton size="sm" variant="ghost" @click="previewModalOpen = false">Đóng</UButton>
          </div>
        </div>
      </template>
    </UModal>
  </div>
</template>

