<script setup lang="ts">
const route = useRoute()
const { fetchApi } = useApi()

const renderId = computed(() => String(route.params.id || ''))
const render = ref<Record<string, any> | null>(null)

const statusLabel = (status: string) => ({
  processing: 'Đang xử lý',
  failed: 'Thất bại',
  completed: 'Hoàn tất'
}[status] || status)

const progressValue = computed(() => {
  if (!render.value) {
    return 10
  }

  if (render.value.status === 'completed') {
    return 100
  }

  if (render.value.status === 'failed') {
    return 100
  }

  return 65
})

const progressColor = computed(() => {
  if (!render.value) {
    return 'primary'
  }

  if (render.value.status === 'completed') {
    return 'success'
  }

  if (render.value.status === 'failed') {
    return 'error'
  }

  return 'primary'
})

const loadRenderStatus = async () => {
  if (!renderId.value) {
    return
  }

  render.value = await fetchApi<Record<string, any>>(`/renders/${renderId.value}`)
}

onMounted(async () => {
  await loadRenderStatus()

  const timer = setInterval(() => {
    if (render.value?.status === 'processing') {
      void loadRenderStatus()
    }
  }, 3000)

  onBeforeUnmount(() => {
    clearInterval(timer)
  })
})
</script>

<template>
  <div class="space-y-6">
    <section class="rounded-3xl border border-white/10 bg-zinc-900/80 p-5">
      <div class="flex items-center justify-between gap-4">
        <div>
          <p class="text-sm uppercase tracking-[0.22em] text-indigo-300">Tiến độ render</p>
          <h1 class="mt-2 text-3xl font-semibold text-white">Render video</h1>
        </div>

        <UBadge v-if="render" :color="render.status === 'completed' ? 'success' : render.status === 'failed' ? 'error' : 'primary'" variant="soft">
          {{ statusLabel(render.status) }}
        </UBadge>
      </div>

      <div v-if="render" class="mt-6 space-y-4">
        <UProgress :value="progressValue" :color="progressColor" size="lg" />
        <div class="flex items-center justify-between text-sm text-zinc-300">
          <span>
            {{ render.status === 'completed' ? 'Video đã sẵn sàng để xem.' : render.status === 'failed' ? 'Render đã thất bại.' : 'AI đang render video theo storyboard đã duyệt.' }}
          </span>
          <span>{{ progressValue }}%</span>
        </div>
      </div>
    </section>

    <div v-if="render" class="grid gap-6 lg:grid-cols-[1fr_0.8fr]">
      <UCard class="border border-white/10 bg-white/5">
        <template #header>
          <h2 class="text-lg font-semibold text-white">Trạng thái xử lý</h2>
        </template>

        <div class="space-y-4">
          <div class="flex items-center gap-3 rounded-2xl border border-white/10 bg-zinc-900/70 p-3">
            <span class="flex h-8 w-8 items-center justify-center rounded-full bg-indigo-500/20 text-xs font-medium text-indigo-300">1</span>
            <div>
              <p class="font-medium text-white">Nhận nhiệm vụ</p>
              <p class="text-sm text-zinc-400">Storyboard đã được phê duyệt và task render đã được tạo.</p>
            </div>
          </div>

          <div class="flex items-center gap-3 rounded-2xl border border-white/10 bg-zinc-900/70 p-3">
            <span class="flex h-8 w-8 items-center justify-center rounded-full bg-indigo-500/20 text-xs font-medium text-indigo-300">2</span>
            <div>
              <p class="font-medium text-white">Tạo video</p>
              <p class="text-sm text-zinc-400">AI đang render khung hình, âm thanh và overlay theo storyboard.</p>
            </div>
          </div>

          <div class="flex items-center gap-3 rounded-2xl border border-white/10 bg-zinc-900/70 p-3">
            <span class="flex h-8 w-8 items-center justify-center rounded-full bg-indigo-500/20 text-xs font-medium text-indigo-300">3</span>
            <div>
              <p class="font-medium text-white">Hoàn tất & QA</p>
              <p class="text-sm text-zinc-400">Video hoàn tất và sẵn sàng để xem, tải xuống hoặc đưa lên kênh.</p>
            </div>
          </div>
        </div>
      </UCard>

      <UCard class="border border-white/10 bg-white/5">
        <template #header>
          <h2 class="text-lg font-semibold text-white">Hành động</h2>
        </template>

        <div class="space-y-3">
          <UButton v-if="render.status === 'completed' && render.video_url" block color="primary" :href="render.video_url" target="_blank">
            Xem video
          </UButton>
          <UButton v-else block variant="outline" @click="loadRenderStatus">Làm mới trạng thái</UButton>
          <UButton block variant="ghost" to="/briefs">Quay lại brief</UButton>
        </div>
      </UCard>
    </div>

    <UCard v-if="render?.status === 'completed' && render.video_url" class="border border-white/10 bg-white/5">
      <template #header>
        <h2 class="text-lg font-semibold text-white">Video preview</h2>
      </template>

      <video :src="render.video_url" controls class="w-full rounded-2xl border border-white/10 bg-black" />
    </UCard>
  </div>
</template>
