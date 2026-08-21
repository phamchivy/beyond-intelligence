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

const { data: briefsData, pending } = await useLazyAsyncData('home-briefs', () =>
  fetchApi<{ items: Array<Record<string, any>> }>('/briefs?page=1')
)

const briefs = computed(() => (briefsData.value?.items ?? []).map((item: Record<string, any>) => ({
  ...item,
  id: item.id || `campaign-${Math.random().toString(36).slice(2, 8)}`,
  status: normalizeStatus(item.status),
  title: item.title || item.productName || 'Campaign',
  channel: item.channel || 'Reels',
  objective: item.objective || 'Conversion'
})))

const summaryCards = computed(() => {
  const total = briefs.value.length
  const awaiting = briefs.value.filter(item => item.status === 'awaiting_approval').length
  const rendering = briefs.value.filter(item => item.status === 'rendering').length
  const done = briefs.value.filter(item => item.status === 'done').length

  return [
    { label: 'Campaign', value: total, detail: 'Tổng số chiến dịch đang hoạt động' },
    { label: 'Chờ review', value: awaiting, detail: 'Storyboard đang chờ duyệt' },
    { label: 'Đang render', value: rendering, detail: 'Video đang xử lý' },
    { label: 'Hoàn tất', value: done, detail: 'Sẵn sàng xuất file' }
  ]
})

const statusColor = (status: string): 'error' | 'primary' | 'secondary' | 'success' | 'info' | 'warning' | 'neutral' | undefined => {
  const map: Record<string, 'error' | 'primary' | 'secondary' | 'success' | 'info' | 'warning' | 'neutral'> = {
    draft: 'neutral',
    reasoning: 'info',
    awaiting_approval: 'warning',
    rendering: 'primary',
    done: 'success',
    failed: 'error'
  }

  return map[status] || 'neutral'
}

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
  <div class="space-y-8">
    <section class="flex flex-col gap-4 rounded-3xl border border-white/10 bg-gradient-to-br from-indigo-500/15 via-zinc-900 to-zinc-950 p-6 md:flex-row md:items-end md:justify-between">
      <div>
        <p class="text-sm uppercase tracking-[0.24em] text-indigo-300">Tổng quan</p>
        <h1 class="mt-3 text-3xl font-semibold text-white">Bảng điều khiển sản xuất brief sang video</h1>
      </div>

      <UButton to="/briefs/new" color="primary" size="lg">
        Tạo brief mới
      </UButton>
    </section>

    <div v-if="pending" class="grid gap-4 md:grid-cols-4">
      <USkeleton v-for="index in 4" :key="index" class="h-32 w-full" />
    </div>

    <div v-else class="space-y-8">
      <section class="grid gap-4 md:grid-cols-4">
        <UCard v-for="card in summaryCards" :key="card.label" class="border border-white/10 bg-white/5">
          <div class="space-y-3">
            <p class="text-sm text-zinc-400">{{ card.label }}</p>
            <p class="text-3xl font-semibold text-white">{{ card.value }}</p>
            <p class="text-xs text-primary-400">{{ card.detail }}</p>
          </div>
        </UCard>
      </section>

      <section class="grid gap-6 lg:grid-cols-[1.5fr_1fr]">
        <UCard class="border border-white/10 bg-white/5">
          <template #header>
            <div class="flex items-center justify-between">
              <h2 class="text-lg font-semibold text-white">Brief gần đây</h2>
              <UButton to="/briefs" variant="ghost" color="neutral" size="sm">Mở thư viện</UButton>
            </div>
          </template>

          <div class="space-y-3">
            <div
              v-for="brief in briefs.slice(0, 5)"
              :key="brief.id"
              class="flex flex-col gap-3 rounded-2xl border border-white/10 bg-zinc-900/70 p-4 md:flex-row md:items-center md:justify-between"
            >
              <div>
                <p class="text-base font-medium text-white">{{ brief.title }}</p>
                <div class="mt-1 flex flex-wrap gap-2 text-xs text-zinc-400">
                  <span>{{ brief.channel }}</span>
                  <span>•</span>
                  <span>{{ brief.objective }}</span>
                </div>
              </div>

              <div class="flex items-center gap-3">
                <UBadge :color="statusColor(brief.status)" variant="soft">{{ statusLabel(brief.status) }}</UBadge>
                <UButton :to="`/briefs/${brief.id}`" size="sm" variant="outline">Mở</UButton>
              </div>
            </div>
          </div>
        </UCard>

        <UCard class="border border-white/10 bg-white/5">
          <template #header>
            <h2 class="text-lg font-semibold text-white">Ghi chú sản xuất</h2>
          </template>

          <div class="space-y-4 text-sm text-zinc-300">
            <div class="rounded-2xl border border-emerald-500/30 bg-emerald-500/10 p-3">
              <p class="font-medium text-primary">Cổng kiểm tra tuân thủ</p>
              <p class="mt-1">Xem lại các khẳng định trước khi phê duyệt để giảm rủi ro bị chặn trên Meta/TikTok.</p>
            </div>
            <div class="rounded-2xl border border-indigo-500/30 bg-indigo-500/10 p-3">
              <p class="font-medium text-primary">Phê duyệt storyboard</p>
              <p class="mt-1">Hook và overlay của từng cảnh là điểm tác động mạnh nhất trong quy trình HITL review.</p>
            </div>
          </div>
        </UCard>
      </section>
    </div>
  </div>
</template>
