<script setup lang="ts">
const route = useRoute()
const { fetchApi } = useApi()

const renderId = computed(() => String(route.params.id))

const { data: result } = await useLazyAsyncData(`render-result-${renderId.value}`, () =>
  fetchApi<Record<string, any>>(`/renders/${renderId.value}/result`)
)

const openDownload = () => {
  if (result.value?.downloadUrl) {
    window.open(result.value.downloadUrl, '_blank')
  }
}
</script>

<template>
  <div v-if="result" class="space-y-6">
    <section class="rounded-3xl border border-white/10 bg-zinc-900/80 p-5">
      <div class="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <p class="text-sm uppercase tracking-[0.22em] text-indigo-300">Kết quả</p>
          <h1 class="mt-2 text-3xl font-semibold text-white">{{ result.title }}</h1>
        </div>

        <div class="flex items-center gap-2">
          <UButton @click="openDownload">Tải xuống</UButton>
          <UButton color="primary" to="/briefs">Tạo video mới</UButton>
        </div>
      </div>
    </section>

    <div class="grid gap-6 xl:grid-cols-[1.5fr_0.5fr]">
      <UCard class="border border-white/10 bg-white/5">
        <video
          :src="result.downloadUrl"
          controls
          class="h-[420px] w-full rounded-2xl bg-black object-cover"
        />
      </UCard>

      <UCard class="border border-white/10 bg-white/5">
        <template #header>
          <h2 class="text-lg font-semibold text-white">Báo cáo QA</h2>
        </template>

        <div class="space-y-3 text-sm text-zinc-300">
          <div class="flex items-center justify-between rounded-2xl border border-white/10 bg-zinc-900/70 p-3">
            <span>Tỷ lệ khung hình</span>
            <UBadge :color="result.qa.ratioMatch ? 'success' : 'error'" variant="soft">
              {{ result.qa.ratioMatch ? 'Khớp' : 'Không khớp' }}
            </UBadge>
          </div>
          <div class="flex items-center justify-between rounded-2xl border border-white/10 bg-zinc-900/70 p-3">
            <span>Thời lượng</span>
            <UBadge :color="result.qa.durationMatch ? 'success' : 'error'" variant="soft">
              {{ result.qa.durationMatch ? 'Khớp' : 'Không khớp' }}
            </UBadge>
          </div>
          <div class="flex items-center justify-between rounded-2xl border border-white/10 bg-zinc-900/70 p-3">
            <span>Độ hiển thị tài nguyên</span>
            <span class="font-medium text-white">{{ result.qa.assetVisibleRatio }}%</span>
          </div>
          <div class="flex items-center justify-between rounded-2xl border border-white/10 bg-zinc-900/70 p-3">
            <span>Nền tảng</span>
            <span class="font-medium text-white">{{ result.platform }}</span>
          </div>
        </div>
      </UCard>
    </div>
  </div>
</template>
