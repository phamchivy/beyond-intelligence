<script setup lang="ts">
const route = useRoute()
const { fetchApi } = useApi()

const briefId = computed(() => String(route.params.id))

const { data: brief, pending } = await useLazyAsyncData(`brief-detail-${briefId.value}`, () =>
  fetchApi<Record<string, any>>(`/briefs/${briefId.value}`)
)

const generateStoryboard = async () => {
  const result = await fetchApi<Record<string, any>>(`/briefs/${briefId.value}/storyboard`, { method: 'POST' })
  await navigateTo(`/briefs/${briefId.value}/storyboard?storyboard=${result.id}`)
}

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
    awaiting_approval: 'Chờ phê duyệt',
    rendering: 'Đang render',
    done: 'Hoàn tất',
    failed: 'Thất bại'
  }

  return map[status] || status
}
</script>

<template>
  <div class="space-y-6">
    <div v-if="pending" class="space-y-4">
      <USkeleton class="h-10 w-48" />
      <USkeleton class="h-72 w-full" />
    </div>

    <div v-else-if="brief" class="space-y-6">
      <section class="flex flex-col gap-4 rounded-3xl border border-white/10 bg-zinc-900/80 p-5 md:flex-row md:items-center md:justify-between">
        <div>
          <p class="text-sm uppercase tracking-[0.22em] text-indigo-300">Chi tiết brief</p>
          <h1 class="mt-2 text-3xl font-semibold text-white">{{ brief.title }}</h1>
        </div>

        <div class="flex items-center gap-2">
          <UBadge :color="statusColor(brief.status)" variant="soft">{{ statusLabel(brief.status) }}</UBadge>
          <UButton :to="`/briefs/${brief.id}/storyboard`" color="primary">Storyboard</UButton>
        </div>
      </section>

      <div class="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
        <UCard class="border border-white/10 bg-white/5">
          <template #header>
            <h2 class="text-lg font-semibold text-white">Tóm tắt chiến dịch</h2>
          </template>

          <div class="grid gap-4 md:grid-cols-2">
            <div>
              <p class="text-sm text-zinc-400">Sản phẩm</p>
              <p class="mt-1 font-medium text-white">{{ brief.productName }}</p>
            </div>
            <div>
              <p class="text-sm text-zinc-400">Danh mục</p>
              <p class="mt-1 font-medium text-white">{{ brief.category }}</p>
            </div>
            <div>
              <p class="text-sm text-zinc-400">Kênh</p>
              <p class="mt-1 font-medium text-white">{{ brief.channel }}</p>
            </div>
            <div>
              <p class="text-sm text-zinc-400">Mục tiêu</p>
              <p class="mt-1 font-medium text-white">{{ brief.objective }}</p>
            </div>
            <div class="md:col-span-2">
              <p class="text-sm text-zinc-400">USP</p>
              <p class="mt-1 text-white">{{ brief.usp }}</p>
            </div>
            <div class="md:col-span-2">
              <p class="text-sm text-zinc-400">Thông điệp chính</p>
              <p class="mt-1 text-white">{{ brief.keyMessage }}</p>
            </div>
            <div class="md:col-span-2">
              <p class="text-sm text-zinc-400">CTA</p>
              <p class="mt-1 text-white">{{ brief.cta }}</p>
            </div>
          </div>
        </UCard>

        <UCard class="border border-white/10 bg-white/5">
          <template #header>
            <h2 class="text-lg font-semibold text-white">Hành động nhanh</h2>
          </template>

          <div class="space-y-3">
            <UButton block color="primary" @click="generateStoryboard">Tạo storyboard</UButton>
            <UButton block variant="outline" :to="`/briefs/${brief.id}/videos`">Xem sản phẩm</UButton>
            <UButton block variant="ghost" to="/briefs">Quay lại brief</UButton>
          </div>
        </UCard>
      </div>

      <UCard class="border border-white/10 bg-white/5">
        <template #header>
          <h2 class="text-lg font-semibold text-white">Asset</h2>
        </template>

        <div class="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
          <div v-for="asset in brief.assets" :key="asset.id" class="overflow-hidden rounded-2xl border border-white/10 bg-zinc-900">
            <img :src="asset.url" :alt="asset.name" class="h-36 w-full object-cover" />
            <div class="p-3">
              <p class="text-sm font-medium text-white capitalize">{{ asset.type }}</p>
              <p class="text-xs text-zinc-400">{{ asset.name }}</p>
            </div>
          </div>
        </div>
      </UCard>
    </div>
  </div>
</template>
