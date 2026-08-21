<script setup lang="ts">
const route = useRoute()
const { reviewStoryboard } = usePipelineApi()

const taskId = computed(() => String(route.query.taskId || ''))
const storyboardId = computed(() => String(route.params.id || route.query.storyboardId || ''))
const rawStoryboardText = computed(() => String(route.query.storyboardText || ''))
const reviewFeedback = ref('')

const parseStoryboardText = (text: string) => {
  const sections = text
    .split(/\n\s*\n/)
    .map(item => item.trim())
    .filter(Boolean)

  if (!sections.length) {
    return {
      id: storyboardId.value || 'storyboard-preview',
      briefId: storyboardId.value || 'brief-preview',
      hook: 'AI đang tạo hook cho chiến dịch này.',
      shots: [
        { id: 'shot-1', role: 'hook', asset: 'https://images.unsplash.com/photo-1496181133206-80ce9b88a853', overlayText: 'AI đang tạo hook cho chiến dịch này.', duration: 4 },
        { id: 'shot-2', role: 'product', asset: 'https://images.unsplash.com/photo-1517336714731-489689fd1ca8', overlayText: 'Sản phẩm đang được ánh xạ thành cảnh quảng cáo.', duration: 5 },
        { id: 'shot-3', role: 'benefit', asset: 'https://images.unsplash.com/photo-1522202176988-66273c2fd55f', overlayText: 'Lợi ích và điểm nổi bật sẽ xuất hiện ở đây.', duration: 6 },
        { id: 'shot-4', role: 'cta', asset: 'https://images.unsplash.com/photo-1545239351-1141bd82e8a6', overlayText: 'CTA: Mua ngay hôm nay', duration: 4 }
      ],
      complianceWarnings: [],
      status: 'awaiting_review',
      generatedAt: new Date().toISOString()
    }
  }

  const parsedShots = sections.map((section, index) => {
    const clean = section.replace(/^[-•]\s*/, '').trim()
    const match = clean.match(/^([A-Za-zÀ-ỹ0-9\s]+):\s*(.*)$/)
    const label = match?.[1]?.trim() ?? `Scene ${index + 1}`
    const content = match?.[2]?.trim() ?? clean

    const role = label.toLowerCase().includes('hook')
      ? 'hook'
      : label.toLowerCase().includes('cta')
        ? 'cta'
        : 'scene'

    return {
      id: `shot-${index + 1}`,
      role,
      asset: [
        'https://images.unsplash.com/photo-1496181133206-80ce9b88a853',
        'https://images.unsplash.com/photo-1517336714731-489689fd1ca8',
        'https://images.unsplash.com/photo-1522202176988-66273c2fd55f',
        'https://images.unsplash.com/photo-1545239351-1141bd82e8a6'
      ][index % 4],
      overlayText: content || label,
      duration: 4 + (index % 3)
    }
  })

  return {
    id: storyboardId.value || `storyboard-${Date.now()}`,
    briefId: storyboardId.value || 'brief-preview',
    hook: parsedShots.find(shot => shot.role === 'hook')?.overlayText || parsedShots[0]?.overlayText || 'AI storyboard đã sẵn sàng.',
    shots: parsedShots,
    complianceWarnings: [],
    status: 'awaiting_review',
    generatedAt: new Date().toISOString()
  }
}

const storyboard = ref<Record<string, any> | null>(rawStoryboardText.value ? parseStoryboardText(rawStoryboardText.value) : null)

watch(rawStoryboardText, (nextText) => {
  storyboard.value = nextText ? parseStoryboardText(nextText) : null
}, { immediate: true })

const draftHook = computed({
  get: () => storyboard.value?.hook || '',
  set: (value: string) => {
    if (storyboard.value) {
      storyboard.value.hook = value
    }
  }
})

const submitDecision = async (decision: 'approved' | 'revised' | 'rejected') => {
  if (!taskId.value || !storyboardId.value) {
    return
  }

  const result = await reviewStoryboard({
    taskId: taskId.value,
    storyboardId: storyboardId.value,
    decision,
    feedback: reviewFeedback.value || undefined
  })

  await navigateTo(`/renders/${result.render_job_id}`)
}

const approveStoryboard = () => submitDecision('approved')
const requestRevision = () => submitDecision('revised')
const rejectStoryboard = () => submitDecision('rejected')
</script>

<template>
  <div class="space-y-6">
    <div v-if="!storyboard" class="rounded-3xl border border-white/10 bg-zinc-900/80 p-12 text-center text-zinc-300">
      Đang tải storyboard...
    </div>

    <div v-else class="space-y-6">
      <section class="flex flex-col gap-4 rounded-3xl border border-white/10 bg-zinc-900/80 p-5 md:flex-row md:items-center md:justify-between">
        <div>
          <p class="text-sm uppercase tracking-[0.22em] text-indigo-300">Đánh giá storyboard</p>
          <h1 class="mt-2 text-3xl font-semibold text-white">Review AI storyboard</h1>
          <p class="mt-2 text-sm text-zinc-400">Task ID: {{ taskId || 'N/A' }} • Storyboard ID: {{ storyboardId }}</p>
        </div>

        <div class="flex flex-wrap items-center gap-2">
          <UButton variant="outline" @click="requestRevision">Yêu cầu chỉnh sửa</UButton>
          <UButton variant="soft" color="neutral" @click="rejectStoryboard">Từ chối</UButton>
          <UButton color="primary" @click="approveStoryboard">Phê duyệt & render</UButton>
        </div>
      </section>

      <div class="grid gap-6 xl:grid-cols-[1.3fr_0.7fr]">
        <div class="space-y-6">
          <UCard class="border border-white/10 bg-white/5">
            <template #header>
              <h2 class="text-lg font-semibold text-white">Nội dung hook</h2>
            </template>

            <UTextarea v-model="draftHook" :rows="3" />
          </UCard>

          <UCard class="border border-white/10 bg-white/5">
            <template #header>
              <h2 class="text-lg font-semibold text-white">Danh sách cảnh</h2>
            </template>

            <div class="space-y-4">
              <div v-for="shot in storyboard.shots" :key="shot.id" class="overflow-hidden rounded-2xl border border-white/10 bg-zinc-900/70">
                <div class="flex flex-col gap-4 md:flex-row">
                  <img :src="shot.asset" :alt="shot.role" class="h-36 w-full object-cover md:w-44" />
                  <div class="flex-1 p-4">
                    <div class="flex items-center justify-between gap-2">
                      <UBadge color="primary" variant="soft">{{ shot.role }}</UBadge>
                      <span class="text-xs text-zinc-400">{{ shot.duration }}s</span>
                    </div>
                    <p class="mt-3 text-base font-medium text-white">{{ shot.overlayText }}</p>
                  </div>
                </div>
              </div>
            </div>
          </UCard>
        </div>

        <div class="space-y-6">
          <UCard class="border border-white/10 bg-white/5">
            <template #header>
              <h2 class="text-lg font-semibold text-white">Phản hồi cho AI</h2>
            </template>

            <UTextarea v-model="reviewFeedback" :rows="6" placeholder="Ví dụ: Tăng độ rõ CTA, bỏ cảnh đầu dài, thêm mô tả về lợi ích chính..." />
          </UCard>

          <UCard class="border border-white/10 bg-white/5">
            <template #header>
              <h2 class="text-lg font-semibold text-white">Kiểm tra tuân thủ</h2>
            </template>

            <div v-if="storyboard.complianceWarnings?.length" class="space-y-3">
              <UAlert
                v-for="warning in storyboard.complianceWarnings"
                :key="warning.id"
                :title="warning.title"
                :description="warning.message"
                color="warning"
                variant="subtle"
              />
            </div>
            <div v-else class="rounded-2xl border border-emerald-500/30 bg-emerald-500/10 p-3 text-sm text-emerald-300">
              Không phát hiện khẳng định bị chặn.
            </div>
          </UCard>
        </div>
      </div>
    </div>
  </div>
</template>
