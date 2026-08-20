<script setup lang="ts">
const { fetchApi } = useApi()

const { data: historyResponse, pending } = await useAsyncData('video-history', () =>
  fetchApi<{ items: Array<{ id: string; title: string; platform: string; performance: string; status: string; createdAt: string; hook: string }> }>('/history/list')
)

const videos = computed(() => historyResponse.value?.items ?? [])
</script>

<template>
  <div class="space-y-6">
    <section class="flex items-end justify-between gap-4 rounded-3xl border border-white/10 bg-gradient-to-r from-zinc-900 to-indigo-950/80 p-6">
      <div>
        <p class="text-xs uppercase tracking-[0.24em] text-indigo-300">History</p>
        <h1 class="mt-3 text-3xl font-semibold text-white">Rendered asset library</h1>
      </div>

      <UButton to="/workspace" color="primary">Create another video</UButton>
    </section>

    <div v-if="pending" class="grid gap-4 md:grid-cols-3">
      <USkeleton v-for="index in 3" :key="index" class="h-60 w-full" />
    </div>

    <div v-else class="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
      <UCard v-for="video in videos" :key="video.id" class="border border-white/10 bg-white/5">
        <template #header>
          <div class="flex items-center justify-between">
            <span class="text-xs uppercase tracking-[0.2em] text-zinc-400">{{ video.platform }}</span>
            <UBadge :color="video.status === 'Success' ? 'success' : 'warning'" variant="soft">
              {{ video.status }}
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
            <span class="text-zinc-300">Performance</span>
            <span class="font-semibold text-indigo-200">{{ video.performance }}</span>
          </div>
        </div>

        <template #footer>
          <div class="flex items-center justify-between">
            <span class="text-xs uppercase tracking-[0.2em] text-zinc-500">{{ video.id }}</span>
            <UButton variant="ghost" color="neutral">Reuse config</UButton>
          </div>
        </template>
      </UCard>
    </div>
  </div>
</template>
