<script setup lang="ts">
const { fetchApi } = useApi()

const activeTab = ref('smart')
const isGenerating = ref(false)
const isScriptOpen = ref(false)
const briefText = ref('Aether Pro là chiếc laptop siêu nhẹ cho người làm việc di động, ưu tiên pin 32h và hiệu năng trong lúc di chuyển.')

const form = reactive({
  productName: '',
  productPrice: '',
  usp: '',
  features: '',
  targetAudience: '',
  positioning: '',
  channel: 'Reels',
  objective: 'Conversion',
  painPoint: '',
  negativePrompt: '',
  cta: '',
  duration: '18s',
  aspectRatio: '9:16'
})

const tabs = [
  { label: 'Smart Input', value: 'smart' },
  { label: 'Product & Assets', value: 'product' },
  { label: 'Strategy', value: 'strategy' },
  { label: 'Constraints', value: 'constraints' }
]

const constraintItems = [
  {
    label: 'Advanced constraints',
    defaultOpen: false,
    content: 'Tối ưu cho 9:16, tối đa 18s, mô tả CTA bắt buộc, và tránh các từ khóa không phù hợp với thương hiệu.'
  }
]

const generationSteps = ref([
  '[✓] Đang phân tích USP sản phẩm...',
  '[✓] Đang viết kịch bản Hook 3s...',
  '[⏳] Đang xử lý hình ảnh và khớp âm thanh...'
])

const result = ref<null | {
  title: string
  caption: string
  cta: string
  steps: string[]
}>(null)

const scriptLines = computed(() => [
  'Hook 0-3s: “Khả năng di chuyển không còn là rào cản.”',
  'Product setup: Trình bày Aether Pro với khung kim loại siêu nhẹ, pin 32h, và sạc nhanh.',
  'Benefit: Giải quyết tình trạng mệt mỏi khi làm việc khi đi lại và không có ổ cắm.',
  'CTA: “Tận dụng ưu đãi 20% hôm nay”'
])

const hydrateForm = async () => {
  const brief = await fetchApi<Record<string, string>>('/workspace/brief')

  Object.assign(form, {
    productName: brief.productName,
    productPrice: brief.productPrice,
    usp: brief.usp,
    features: brief.features,
    targetAudience: brief.targetAudience,
    positioning: brief.positioning,
    channel: brief.channel,
    objective: brief.objective,
    painPoint: brief.painPoint,
    negativePrompt: brief.negativePrompt,
    cta: brief.cta,
    duration: brief.duration,
    aspectRatio: brief.aspectRatio
  })

  briefText.value = `${brief.productName} — ${brief.usp}`
}

await hydrateForm()

const handleAutoFill = async () => {
  await hydrateForm()
  activeTab.value = 'product'
}

const handleGenerate = async () => {
  isGenerating.value = true
  generationSteps.value = [
    '[✓] Đang phân tích USP sản phẩm...',
    '[✓] Đang viết kịch bản Hook 3s...',
    '[✓] Đang xử lý hình ảnh và khớp âm thanh...',
    '[⏳] Đang render luồng video và tối ưu cô đọng CTA...'
  ]

  const generated = await fetchApi<{
    ok: boolean
    title?: string
    preview?: { title: string; caption: string; cta: string }
    steps: string[]
  }>('/workspace/generate', {
    method: 'POST',
    body: form
  })

  result.value = {
    title: generated.preview?.title || `${form.productName} — Launch Demo`,
    caption: generated.preview?.caption || 'Khả năng sáng tạo không ngừng. Thiết kế tối ưu cho mọi nơi.',
    cta: generated.preview?.cta || form.cta,
    steps: generated.steps || generationSteps.value
  }

  isGenerating.value = false
}
</script>

<template>
  <div class="grid gap-6 xl:grid-cols-[0.95fr_1.45fr]">
    <section class="rounded-3xl border border-white/10 bg-zinc-900/70 p-4 md:p-5">
      <div class="mb-6 flex items-center justify-between">
        <div>
          <p class="text-xs uppercase tracking-[0.2em] text-indigo-300">Workspace</p>
          <h1 class="mt-2 text-2xl font-semibold text-white">Video campaign brief</h1>
        </div>
        <UBadge color="primary" variant="soft">{{ isGenerating ? 'Generating' : 'Ready' }}</UBadge>
      </div>

      <UTabs v-model="activeTab" :items="tabs" class="mb-6" />

      <div v-if="activeTab === 'smart'" class="space-y-4">
        <UTextarea v-model="briefText" :rows="7" placeholder="Dán brief từ khách hàng hoặc mô tả tính năng sản phẩm..." />
        <div class="flex items-center justify-between gap-3">
          <p class="text-xs text-zinc-400">AI will auto-populate the form below.</p>
          <UButton color="primary" @click="handleAutoFill">AI Auto-fill</UButton>
        </div>
      </div>

      <div v-else-if="activeTab === 'product'" class="space-y-4">
        <UInput v-model="form.productName" label="Product name" />
        <UInput v-model="form.productPrice" label="Price" />
        <UTextarea v-model="form.usp" label="USP" :rows="4" />
        <UTextarea v-model="form.features" label="Features" :rows="4" />

        <div class="rounded-2xl border border-dashed border-zinc-700 p-4">
          <p class="text-sm font-medium text-white">Asset upload</p>
          <p class="mt-2 text-sm text-zinc-400">Hero shot, product logo, and reference video can be dropped here.</p>
        </div>
      </div>

      <div v-else-if="activeTab === 'strategy'" class="space-y-4">
        <USelect v-model="form.channel" :items="['Meta', 'TikTok', 'Reels', 'YouTube Shorts']" label="Channel" />
        <USelect v-model="form.objective" :items="['Conversion', 'Traffic', 'Brand lift']" label="Objective" />
        <UInput v-model="form.targetAudience" label="Target audience" />
        <UTextarea v-model="form.positioning" label="Brand positioning" :rows="4" />
        <UTextarea v-model="form.painPoint" label="Customer pain point" :rows="3" />
      </div>

      <div v-else class="space-y-4">
        <UInput v-model="form.duration" label="Max duration" />
        <UInput v-model="form.aspectRatio" label="Aspect ratio" />
        <UTextarea v-model="form.negativePrompt" label="Negative prompt" :rows="3" />
        <UInput v-model="form.cta" label="Mandatory CTA" />

        <UAccordion :items="constraintItems" class="mt-3" />
      </div>

      <div class="mt-8 flex items-center justify-between border-t border-white/10 pt-5">
        <div class="text-xs text-zinc-400">Unsaved changes are tracked locally.</div>
        <UButton color="primary" size="lg" @click="handleGenerate">Create video ad</UButton>
      </div>
    </section>

    <section class="rounded-3xl border border-white/10 bg-zinc-900/70 p-4 md:p-5">
      <div v-if="!result && !isGenerating" class="flex min-h-[620px] flex-col items-center justify-center rounded-3xl border border-dashed border-zinc-700 bg-zinc-950/60 p-6 text-center">
        <div class="mb-5 flex h-16 w-16 items-center justify-center rounded-full bg-indigo-500/10 text-3xl">✨</div>
        <h2 class="text-xl font-semibold text-white">No output yet</h2>
        <p class="mt-2 max-w-md text-sm text-zinc-400">
          Enter information on the left or use AI Auto-fill to start building your ad storyboard.
        </p>
      </div>

      <div v-else-if="isGenerating" class="flex min-h-[620px] flex-col justify-between rounded-3xl border border-indigo-500/30 bg-zinc-950/60 p-5">
        <div>
          <div class="flex items-center justify-between">
            <p class="text-sm uppercase tracking-[0.2em] text-indigo-300">Generation</p>
            <UBadge color="primary" variant="soft">AI processing</UBadge>
          </div>
          <div class="mt-6">
            <UProgress :value="72" color="primary" size="md" />
          </div>
        </div>

        <div class="mt-8 space-y-3">
          <div v-for="(step, index) in generationSteps" :key="step" class="flex items-center gap-3 rounded-2xl border border-white/10 bg-white/5 p-3 text-sm text-zinc-200">
            <span class="flex h-6 w-6 items-center justify-center rounded-full bg-indigo-500/20 text-[10px] font-medium text-indigo-300">
              {{ index + 1 }}
            </span>
            {{ step }}
          </div>
        </div>
      </div>

      <div v-else class="space-y-5">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-xs uppercase tracking-[0.2em] text-emerald-300">Result</p>
            <h2 class="mt-2 text-2xl font-semibold text-white">{{ result?.title }}</h2>
          </div>
          <UButton color="primary" @click="isScriptOpen = true">View AI script</UButton>
        </div>

        <div class="flex justify-center pt-6">
          <div class="relative h-[640px] w-[320px] overflow-hidden rounded-[2.2rem] border border-zinc-700 bg-gradient-to-br from-zinc-900 via-zinc-800 to-zinc-950 shadow-2xl shadow-indigo-950/40">
            <div class="absolute inset-x-0 top-0 h-14 bg-zinc-950/80" />
            <div class="absolute right-3 top-4 flex gap-2">
              <span class="h-2.5 w-2.5 rounded-full bg-zinc-500" />
              <span class="h-2.5 w-2.5 rounded-full bg-zinc-500" />
              <span class="h-2.5 w-2.5 rounded-full bg-zinc-500" />
            </div>

            <div class="absolute inset-x-0 top-16 bottom-0 bg-[radial-gradient(circle_at_top,_rgba(99,102,241,0.35),transparent_35%),linear-gradient(180deg,rgba(17,24,39,0.5),rgba(9,9,11,0.7))]" />
            <div class="absolute inset-x-5 top-20 h-44 rounded-3xl bg-gradient-to-br from-indigo-500/40 via-violet-500/30 to-amber-300/20" />
            <div class="absolute inset-x-5 top-24 h-32 rounded-2xl border border-white/10 bg-white/5 backdrop-blur-sm" />
            <div class="absolute inset-x-0 bottom-0 bg-zinc-950/95 p-5">
              <div class="mb-4 flex items-center justify-between text-xs text-zinc-300">
                <span>❤ 24.8K</span>
                <span>💬 1.2K</span>
                <span>↗ Share</span>
              </div>
              <p class="text-lg font-semibold text-white">{{ result?.caption }}</p>
              <div class="mt-4 flex items-center justify-between rounded-2xl border border-indigo-500/30 bg-indigo-500/10 px-3 py-2 text-sm text-indigo-100">
                <span>{{ result?.cta }}</span>
                <span>→</span>
              </div>
            </div>
          </div>
        </div>

        <div class="flex flex-wrap gap-3">
          <UButton color="primary" size="lg">Download video</UButton>
          <UButton variant="soft" color="neutral" size="lg" @click="handleGenerate">Regenerate</UButton>
          <UButton variant="ghost" color="neutral" size="lg" @click="isScriptOpen = true">Open script</UButton>
        </div>
      </div>
    </section>
  </div>

  <UModal v-model:open="isScriptOpen">
    <template #content>
      <div class="space-y-4 p-5">
        <div>
          <p class="text-xs uppercase tracking-[0.2em] text-indigo-300">AI Script</p>
          <h3 class="mt-2 text-xl font-semibold text-white">Hook → Product → Benefit → CTA</h3>
        </div>

        <ol class="space-y-3 text-sm text-zinc-300">
          <li v-for="(line, index) in scriptLines" :key="line" class="rounded-2xl border border-white/10 bg-zinc-900/80 p-3">
            <span class="mr-2 text-indigo-300">{{ index + 1 }}.</span>
            {{ line }}
          </li>
        </ol>
      </div>
    </template>
  </UModal>
</template>
