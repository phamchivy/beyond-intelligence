<script setup lang="ts">
const route = useRoute()
const { fetchApi } = useApi()

const briefId = computed(() => String(route.params.id))
const { data } = await useLazyAsyncData(`brief-videos-${briefId.value}`, () =>
  fetchApi<{ items: Array<Record<string, any>> }>(`/briefs/${briefId.value}/videos`)
)
</script>

<template>
  <div class="space-y-6">
    <section class="flex items-center justify-between">
      <div>
        <p class="text-sm uppercase tracking-[0.22em] text-indigo-300">Thư viện đầu ra</p>
        <h1 class="mt-2 text-3xl font-semibold text-white">Video cho brief này</h1>
      </div>

      <UButton to="/briefs" variant="outline">Quay lại brief</UButton>
    </section>

    <div class="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
      <UCard v-for="video in data?.items ?? []" :key="video.id" class="border border-white/10 bg-zinc-900/80">
        <img :src="video.previewUrl" :alt="video.title" class="h-44 w-full rounded-2xl object-cover" />

        <div class="mt-4 space-y-3">
          <div class="flex items-center justify-between gap-2">
            <h2 class="text-lg font-semibold text-white">{{ video.title }}</h2>
            <UBadge :color="video.status === 'done' ? 'success' : 'primary'" variant="soft">{{ video.status }}</UBadge>
          </div>

          <div class="flex flex-wrap gap-2 text-xs text-zinc-400">
            <span>{{ video.platform }}</span>
            <span>•</span>
            <span>{{ video.duration }}</span>
            <span>•</span>
            <span>{{ video.ratio }}</span>
          </div>

          <div class="flex gap-2">
            <UButton v-if="video.downloadUrl" :to="`/renders/${video.id}`" size="sm" variant="outline">Mở</UButton>
            <UButton v-if="video.downloadUrl" :href="video.downloadUrl" target="_blank" size="sm" color="primary">Tải xuống</UButton>
          </div>
        </div>
      </UCard>
    </div>
  </div>
</template>
