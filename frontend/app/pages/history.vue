<script setup lang="ts">
const { fetchApi } = useApi()

const normalizeStatus = (status: string) => {
  const normalized = String(status || '').toLowerCase()
  if (['draft', 'saved', 'new'].includes(normalized)) {
    return 'draft'
  }
  if (['submitted', 'queued', 'processing', 'reviewing', 'awaiting_approval', 'storyboard_review', 'storyboard_reviewed', 'reasoning'].includes(normalized)) {
    return 'awaiting_approval'
  }
  if (['rendering', 'render', 'rendering_video', 'video_render'].includes(normalized)) {
    return 'rendering'
  }
  if (['done', 'completed', 'success'].includes(normalized)) {
    return 'done'
  }
  if (['failed', 'error'].includes(normalized)) {
    return 'failed'
  }
  return normalized || 'draft'
}

const { data: historyResponse, pending } = await useLazyAsyncData('video-history', () =>
  fetchApi<{ items: Array<Record<string, any>> }>('/briefs?page=1')
)

const videos = computed(() => {
  return (historyResponse.value?.items ?? []).map((brief: Record<string, any>) => ({
    id: brief.id,
    title: brief.title || brief.productName || 'Campaign',
    platform: brief.channel || 'Reels',
    status: normalizeStatus(brief.status),
    createdAt: brief.createdAt || new Date().toISOString(),
    hook: brief.keyMessage || brief.productUsp || 'Campaign đang được xử lý.',
    performance: brief.objective || 'Conversion'
  }))
})

const statusLabel = (status: string) => {
  const map: Record<string, string> = {
    draft: 'Bản nháp',
    reasoning: 'Đang suy luận',
    awaiting_approval: 'Chờ review',
    rendering: 'Đang render',
    done: 'Hoàn tất',
    failed: 'Thất bại'
  }

  return map[status] || status
}
</script>

<template>
  <div class="space-y-6">
    <section class="flex items-end justify-between gap-4 rounded-3xl border border-white/10 bg-gradient-to-r from-zinc-900 to-indigo-950/80 p-6">
      <div>
        <p class="text-xs uppercase tracking-[0.24em] text-indigo-300">Lịch sử</p>
        <h1 class="mt-3 text-3xl font-semibold text-white">Thư viện asset đã render</h1>
      </div>

      <UButton to="/briefs/new" color="primary">Tạo video khác</UButton>
    </section>

    <div v-if="pending" class="grid gap-4 md:grid-cols-3">
      <USkeleton v-for="index in 3" :key="index" class="h-60 w-full" />
    </div>

    <div v-else class="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
      <UCard v-for="video in videos" :key="video.id" class="border border-white/10 bg-white/5">
        <template #header>
          <div class="flex items-center justify-between">
            <span class="text-xs uppercase tracking-[0.2em] text-zinc-400">{{ video.platform }}</span>
            <UBadge :color="video.status === 'done' ? 'success' : 'warning'" variant="soft">
              {{ statusLabel(video.status) }}
            </UBadge>
          </div>
        </template>

        <div class="space-y-4">
          <div>
            <h2 class="text-xl font-semibold text-white">{{ video.title }}</h2>
            <p class="mt-2 text-sm text-zinc-400">{{ video.createdAt }}</p>
          </div>

          <div class="rounded-2xl border border-white/10 bg-zinc-900/80 p-4">
            <p class="text-xs uppercase tracking-[0.2em] text-zinc-500">Hook</p>
            <p class="mt-2 text-sm text-zinc-200">{{ video.hook }}</p>
          </div>

          <div class="flex items-center justify-between rounded-2xl border border-indigo-500/20 bg-indigo-500/10 p-3 text-sm">
            <span class="text-zinc-300">Mục tiêu</span>
            <span class="font-semibold text-indigo-200">{{ video.performance }}</span>
          </div>
        </div>

        <template #footer>
          <div class="flex items-center justify-between">
            <span class="text-xs uppercase tracking-[0.2em] text-zinc-500">{{ video.id }}</span>
            <UButton :to="`/briefs/${video.id}`" variant="ghost" color="neutral">Mở brief</UButton>
          </div>
        </template>
      </UCard>
    </div>
  </div>
</template>
