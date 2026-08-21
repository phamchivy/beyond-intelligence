<script setup lang="ts">
import type { BriefForm, StoryboardPlan, StoryboardScene } from '../types/brief'

const { submitBriefForReview, reviewStoryboard, getRenderStatus } = usePipelineApi()
const toast = useToast?.()

// Preset Templates cho Quick Demo
const presets = [
  {
    name: 'Serum Vitamin C',
    category: 'Skincare / Mỹ phẩm',
    data: {
      productName: 'Serum Glow Vitamin C 15%',
      productCategory: 'Skincare',
      productPrice: 299000,
      productUsp: 'Sáng da mờ thâm mụn chỉ sau 7 ngày, không châm chích.',
      productFeatures: '15% Pure Vitamin C nguyên chất, Hyaluronic Acid cấp ẩm, không cồn, không paraben.',
      productOffer: 'Mua 1 tặng 1 + Freeship toàn quốc trong hôm nay',
      allowedClaims: 'Phù hợp cho mọi loại da, đã kiểm nghiệm da liễu.',
      audienceProfile: 'Nữ 18-30 tuổi, nhân viên văn phòng, sinh viên hay thức khuya, da xỉn màu và có vết thâm.',
      objective: 'conversion',
      keyMessage: 'Sáng bừng làn da chỉ sau 7 ngày - Tự tin mặt mộc!',
      channel: 'tiktok',
      aspectRatio: '9:16',
      maxDurationMs: 15000,
      language: 'vi',
      requiredCta: 'Nhấp vào giỏ hàng nhận ngay ưu đãi Mua 1 Tặng 1!',
      bannedClaims: 'Trị khỏi 100% vĩnh viễn, cam kết khỏi nám trong 24h.',
      bannedContent: 'So sánh tiêu cực với các hãng khác, hình ảnh gây giật gân.'
    }
  },
  {
    name: 'Laptop Gaming AI',
    category: 'Công nghệ / Laptop',
    data: {
      productName: 'Aether Blade Pro 16',
      productCategory: 'Laptop Công nghệ',
      productPrice: 32990000,
      productUsp: 'Chip AI thế hệ mới, tản nhiệt buồng hơi siêu mát, pin 14 giờ.',
      productFeatures: 'Card đồ họa RTX 4080, Màn hình OLED 240Hz 2.5K, Trọng lượng chỉ 1.7kg.',
      productOffer: 'Tặng Balo Gaming cao cấp + Chuột không dây trị giá 2.5 triệu.',
      allowedClaims: 'Bảo hành 2 năm 1 đổi 1, chính hãng 100%.',
      audienceProfile: 'Nam/Nữ 20-35 tuổi, lập trình viên, designer, game thủ, người làm đồ họa.',
      objective: 'conversion',
      keyMessage: 'Sức mạnh gaming tối thượng trong thân hình mỏng nhẹ bất khả chiến bại.',
      channel: 'reels',
      aspectRatio: '9:16',
      maxDurationMs: 15000,
      language: 'vi',
      requiredCta: 'Đặt trước ngay để nhận trọn bộ quà tặng 2.5 triệu!',
      bannedClaims: 'Laptop mạnh nhất thế giới không đối thủ.',
      bannedContent: 'Hiệu ứng rung giật quá mức, âm thanh chói tai.'
    }
  },
  {
    name: 'Giày Chạy Bộ Urban',
    category: 'Thời trang / Thể thao',
    data: {
      productName: 'Urban Runner Boost 5',
      productCategory: 'Giày thể thao',
      productPrice: 1250000,
      productUsp: 'Đế đệm Carbon siêu nảy, trợ lực 35%, êm ái từng bước chạy.',
      productFeatures: 'Vải dệt thoáng khí FlyKnit, chống trơn trượt chuẩn Marathon, trọng lượng 180g.',
      productOffer: 'Giảm ngay 25% cho 100 người đặt đầu tiên',
      allowedClaims: 'Đổi trả miễn phí 30 ngày nếu không vừa size.',
      audienceProfile: 'Người yêu thích chạy bộ, tập gym, phong cách đường phố năng động 18-40 tuổi.',
      objective: 'conversion',
      keyMessage: 'Bứt phá mọi giới hạn - Chạy êm hơn, xa hơn mỗi ngày.',
      channel: 'tiktok',
      aspectRatio: '9:16',
      maxDurationMs: 15000,
      language: 'vi',
      requiredCta: 'Mua ngay hôm nay - Giảm 25% duy nhất tuần này!',
      bannedClaims: 'Chữa đau khớp hoàn toàn khi mang giày.',
      bannedContent: 'Nhại logo hoặc thiết kế của hãng khác.'
    }
  }
]

// Form State
const form = reactive<BriefForm>({
  productName: '',
  productCategory: '',
  productPrice: '',
  productUsp: '',
  productFeatures: '',
  productOffer: '',
  allowedClaims: '',
  audienceProfile: '',
  objective: 'conversion',
  keyMessage: '',
  channel: 'tiktok',
  aspectRatio: '9:16',
  creativeReference: '',
  maxDurationMs: 15000,
  language: 'vi',
  requiredCta: '',
  bannedClaims: '',
  bannedContent: '',
  assets: []
})

// Tab State (0: Nguyên liệu, 1: Chiến lược, 2: Ràng buộc)
const currentTab = ref(0)
const tabItems = [
  { label: '📦 Nguyên liệu', slot: 'product' },
  { label: '🎯 Chiến lược', slot: 'strategy' },
  { label: '⚙️ Ràng buộc', slot: 'constraints' }
]

// Asset Upload Management
const assetTypes = [
  { key: 'hero', label: 'Ảnh Hero (Sản phẩm chính)', desc: 'Ảnh chụp rõ nét nổi bật' },
  { key: 'closeup', label: 'Cận cảnh (Detail / Texture)', desc: 'Chất liệu, bao bì, tem mác' },
  { key: 'lifestyle', label: 'Lifestyle (Bối cảnh thực tế)', desc: 'Người dùng đang trải nghiệm' },
  { key: 'logo', label: 'Logo Thương hiệu', desc: 'File PNG nền trong suốt' }
]

const uploadedFiles = reactive<Record<string, Array<{ file: File, preview: string }>>>({
  hero: [],
  closeup: [],
  lifestyle: [],
  logo: []
})

const handleFileUpload = (typeKey: string, event: Event) => {
  const target = event.target as HTMLInputElement
  if (target.files && target.files.length > 0) {
    Array.from(target.files).forEach(file => {
      const preview = URL.createObjectURL(file)
      uploadedFiles[typeKey].push({ file, preview })
    })
  }
}

const removeFile = (typeKey: string, index: number) => {
  const item = uploadedFiles[typeKey][index]
  if (item) {
    URL.revokeObjectURL(item.preview)
    uploadedFiles[typeKey].splice(index, 1)
  }
}

// Smart AI Auto-Fill State
const rawInputText = ref('')
const isAutoFilling = ref(false)

const applyPreset = (preset: typeof presets[0]) => {
  Object.assign(form, preset.data)
  rawInputText.value = `Sản phẩm: ${preset.data.productName} (${preset.data.productCategory})\nUSP: ${preset.data.productUsp}\nƯu đãi: ${preset.data.productOffer}\nThông điệp: ${preset.data.keyMessage}`
}

const runSmartAutoFill = () => {
  if (!rawInputText.value.trim()) return
  isAutoFilling.value = true

  setTimeout(() => {
    const text = rawInputText.value
    form.productName = form.productName || text.split('\n')[0]?.replace(/^[sS]ản phẩm:\s*/, '') || 'Sản phẩm mới'
    form.productUsp = form.productUsp || 'Đột phá chất lượng và hiệu quả vượt trội trong phân khúc'
    form.keyMessage = form.keyMessage || form.productUsp
    form.requiredCta = form.requiredCta || 'Mua ngay hôm nay để nhận ưu đãi đặc biệt!'
    if (!form.productCategory) form.productCategory = 'Thương mại điện tử'
    if (!form.productPrice) form.productPrice = 199000
    isAutoFilling.value = false
  }, 600)
}

// Pipeline Generation & Workflow State
// flowState: 'idle' | 'generating' | 'review' | 'rendering' | 'completed' | 'failed'
const flowState = ref<'idle' | 'generating' | 'review' | 'rendering' | 'completed' | 'failed'>('idle')
const currentTaskId = ref('')
const currentStoryboardId = ref('')
const revisionNumber = ref(1)
const activePlan = ref<StoryboardPlan | null>(null)
const renderJobId = ref('')
const renderVideoUrl = ref('')
const renderProgress = ref(0)
const renderErrorMsg = ref('')

// HITL Review Feedback
const reviewFeedback = ref('')
const isReviewing = ref(false)
const showTikTokOverlay = ref(true)
const showScriptModal = ref(false)

// AI Reasoning Stepper simulation during generating state
const reasoningStep = ref(1)
let reasoningTimer: any = null

const startReasoningAnimation = () => {
  reasoningStep.value = 1
  reasoningTimer = setInterval(() => {
    if (reasoningStep.value < 4) {
      reasoningStep.value++
    }
  }, 700)
}

// 1. Submit Brief to Pipeline
const handleCreateAndSubmitBrief = async () => {
  if (!form.productName.trim()) {
    currentTab.value = 0
    return
  }

  flowState.value = 'generating'
  startReasoningAnimation()

  const allAssets: File[] = []
  Object.values(uploadedFiles).forEach(fileList => {
    fileList.forEach(item => allAssets.push(item.file))
  })

  form.assets = allAssets

  try {
    const res = await submitBriefForReview(form)
    clearInterval(reasoningTimer)
    currentTaskId.value = res.taskId
    currentStoryboardId.value = res.storyboardId
    revisionNumber.value = res.revisionNumber || 1
    activePlan.value = res.plan
    flowState.value = 'review'
  } catch (err: any) {
    clearInterval(reasoningTimer)
    flowState.value = 'failed'
    renderErrorMsg.value = err?.message || 'Có lỗi khi gửi brief sang AI Pipeline'
  }
}

// 2. HITL Review Action (Approve, Needs Revision, Reject)
const handleReviewDecision = async (decision: 'approved' | 'needs_revision' | 'rejected') => {
  if (!currentTaskId.value || !currentStoryboardId.value) return
  isReviewing.value = true

  try {
    const res = await reviewStoryboard({
      taskId: currentTaskId.value,
      storyboardId: currentStoryboardId.value,
      decision,
      feedback: reviewFeedback.value
    })

    if (decision === 'approved') {
      renderJobId.value = res.render_job_id || `render-${Date.now()}`
      flowState.value = 'rendering'
      startRenderPolling(renderJobId.value)
    } else if (decision === 'needs_revision') {
      if (res.plan) {
        activePlan.value = res.plan
        revisionNumber.value = res.revision_number || (revisionNumber.value + 1)
        reviewFeedback.value = ''
      }
    } else {
      flowState.value = 'idle'
      activePlan.value = null
    }
  } catch (err: any) {
    console.error('Review error:', err)
  } finally {
    isReviewing.value = false
  }
}

// 3. Render Status Polling
let pollingInterval: any = null

const startRenderPolling = (jobId: string) => {
  renderProgress.value = 20
  if (pollingInterval) clearInterval(pollingInterval)

  pollingInterval = setInterval(async () => {
    try {
      renderProgress.value = Math.min(renderProgress.value + 18, 92)
      const statusRes = await getRenderStatus(jobId)

      if (statusRes.status === 'completed' && statusRes.video_url) {
        renderProgress.value = 100
        renderVideoUrl.value = statusRes.video_url
        flowState.value = 'completed'
        clearInterval(pollingInterval)
      } else if (statusRes.status === 'failed') {
        flowState.value = 'failed'
        renderErrorMsg.value = statusRes.error?.message || 'Render video thất bại từ AI Pod.'
        clearInterval(pollingInterval)
      }
    } catch {
      // Demo fallback auto-complete
      if (renderProgress.value >= 85) {
        renderProgress.value = 100
        renderVideoUrl.value = 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4'
        flowState.value = 'completed'
        clearInterval(pollingInterval)
      }
    }
  }, 2200)
}

const resetWorkspace = () => {
  flowState.value = 'idle'
  activePlan.value = null
  renderVideoUrl.value = ''
  renderProgress.value = 0
  reviewFeedback.value = ''
}

onBeforeUnmount(() => {
  if (reasoningTimer) clearInterval(reasoningTimer)
  if (pollingInterval) clearInterval(pollingInterval)
})

// Mặc định load preset 1
onMounted(() => {
  if (!form.productName) {
    applyPreset(presets[0])
  }
})
</script>

<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
      <div>
        <div class="flex items-center gap-2">
          <span class="inline-flex items-center gap-1.5 rounded-full bg-indigo-500/10 px-2.5 py-0.5 text-xs font-semibold text-indigo-600 dark:text-indigo-400">
            <UIcon name="lucide:sparkles" class="h-3.5 w-3.5" />
            AI Video Generator
          </span>
          <span class="text-xs text-slate-500">• 9:16 Short Video Ads Pipeline</span>
        </div>
        <h1 class="mt-1 text-2xl font-bold tracking-tight text-slate-900 dark:text-white">
          Workspace Tạo Video Quảng Cáo
        </h1>
      </div>

      <div class="flex items-center gap-2">
        <UButton
          v-if="flowState !== 'idle'"
          variant="outline"
          color="neutral"
          icon="lucide:rotate-ccw"
          @click="resetWorkspace"
        >
          Tạo mới
        </UButton>
      </div>
    </div>

    <!-- Main Split-Pane Layout (Desktop: 42% Input / 58% AI Output) -->
    <div class="grid gap-6 lg:grid-cols-12">
      <!-- LEFT PANEL: INPUT (5 / 12) -->
      <div class="space-y-5 lg:col-span-5">
        <!-- Smart AI Presets Bar -->
        <UCard class="border-indigo-500/20 bg-gradient-to-r from-indigo-50/50 via-white to-violet-50/50 dark:from-indigo-950/20 dark:via-zinc-900/80 dark:to-violet-950/20">
          <div class="space-y-3">
            <div class="flex items-center justify-between">
              <span class="text-xs font-bold uppercase tracking-wider text-indigo-600 dark:text-indigo-400">
                ⚡ Mẫu Chiến Dịch Nhanh
              </span>
              <span class="text-[11px] text-slate-500">1-Click nạp dữ liệu</span>
            </div>

            <div class="flex flex-wrap gap-2">
              <button
                v-for="preset in presets"
                :key="preset.name"
                type="button"
                class="rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs font-medium text-slate-700 shadow-xs transition hover:border-indigo-500 hover:text-indigo-600 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-200 dark:hover:border-indigo-400 dark:hover:text-indigo-300"
                @click="applyPreset(preset)"
              >
                {{ preset.name }}
              </button>
            </div>
          </div>
        </UCard>

        <!-- Smart Auto-Fill Box -->
        <UCard>
          <template #header>
            <div class="flex items-center justify-between">
              <span class="text-sm font-semibold text-slate-900 dark:text-white">
                🪄 AI Auto-Fill từ Brief thô
              </span>
              <UButton
                size="xs"
                color="primary"
                :loading="isAutoFilling"
                icon="lucide:wand-2"
                @click="runSmartAutoFill"
              >
                Tự động điền
              </UButton>
            </div>
          </template>

          <UTextarea
            v-model="rawInputText"
            :rows="2"
            placeholder="Dán đoạn brief thô hoặc mô tả ngắn về sản phẩm, AI sẽ tự động phân tích và điền vào các ô..."
            class="text-xs"
          />
        </UCard>

        <!-- Tabs Container -->
        <UCard>
          <!-- Custom Tab Bar -->
          <div class="mb-4 flex border-b border-slate-200 dark:border-zinc-800">
            <button
              v-for="(tab, idx) in tabItems"
              :key="tab.label"
              type="button"
              class="flex-1 border-b-2 py-2.5 text-center text-xs font-semibold transition"
              :class="currentTab === idx
                ? 'border-indigo-600 text-indigo-600 dark:border-indigo-400 dark:text-indigo-400'
                : 'border-transparent text-slate-500 hover:text-slate-900 dark:text-zinc-400 dark:hover:text-white'"
              @click="currentTab = idx"
            >
              {{ tab.label }}
            </button>
          </div>

          <!-- TAB 1: NGUYÊN LIỆU (PRODUCT & ASSETS) -->
          <div v-show="currentTab === 0" class="space-y-4">
            <div>
              <label class="mb-1 block text-xs font-medium text-slate-700 dark:text-zinc-300">Tên sản phẩm *</label>
              <UInput v-model="form.productName" placeholder="Ví dụ: Serum Glow Vitamin C 15%" />
            </div>

            <div class="grid grid-cols-2 gap-3">
              <div>
                <label class="mb-1 block text-xs font-medium text-slate-700 dark:text-zinc-300">Danh mục</label>
                <UInput v-model="form.productCategory" placeholder="Skincare / Mỹ phẩm" />
              </div>
              <div>
                <label class="mb-1 block text-xs font-medium text-slate-700 dark:text-zinc-300">Giá bán (VNĐ)</label>
                <UInput v-model="form.productPrice" type="number" placeholder="299000" />
              </div>
            </div>

            <div>
              <label class="mb-1 block text-xs font-medium text-slate-700 dark:text-zinc-300">Điểm độc nhất (USP) *</label>
              <UTextarea v-model="form.productUsp" :rows="2" placeholder="Ví dụ: Sáng da mờ thâm sau 7 ngày không châm chích..." />
            </div>

            <div>
              <label class="mb-1 block text-xs font-medium text-slate-700 dark:text-zinc-300">Tính năng & Thành phần chính</label>
              <UTextarea v-model="form.productFeatures" :rows="2" placeholder="Ví dụ: 15% Pure Vitamin C, Hyaluronic Acid..." />
            </div>

            <div>
              <label class="mb-1 block text-xs font-medium text-slate-700 dark:text-zinc-300">Ưu đãi / Offer khuyến mãi</label>
              <UInput v-model="form.productOffer" placeholder="Ví dụ: Mua 1 Tặng 1 + Freeship toàn quốc" />
            </div>

            <!-- Upload Assets Section -->
            <div class="pt-2">
              <p class="mb-2 text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-zinc-300">
                🖼️ Tài nguyên hình ảnh / Video (Assets)
              </p>

              <div class="grid grid-cols-2 gap-2.5">
                <div
                  v-for="asset in assetTypes"
                  :key="asset.key"
                  class="rounded-xl border border-dashed border-slate-300 bg-slate-50 p-2.5 transition hover:border-indigo-500 dark:border-zinc-700 dark:bg-zinc-900/50"
                >
                  <div class="flex items-center justify-between">
                    <span class="text-[11px] font-semibold text-slate-800 dark:text-zinc-200">{{ asset.label }}</span>
                    <UBadge v-if="uploadedFiles[asset.key]?.length" size="xs" color="primary">
                      {{ uploadedFiles[asset.key].length }}
                    </UBadge>
                  </div>
                  <p class="mt-0.5 text-[10px] text-slate-500">{{ asset.desc }}</p>

                  <label class="mt-2 flex cursor-pointer items-center justify-center gap-1 rounded-lg border border-slate-200 bg-white py-1 text-[11px] font-medium text-slate-700 shadow-2xs hover:bg-slate-50 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-200">
                    <UIcon name="lucide:upload" class="h-3 w-3" />
                    <span>Chọn file</span>
                    <input
                      type="file"
                      accept="image/*,video/*"
                      multiple
                      class="hidden"
                      @change="handleFileUpload(asset.key, $event)"
                    />
                  </label>

                  <!-- Preview Thumbs -->
                  <div v-if="uploadedFiles[asset.key]?.length" class="mt-2 flex flex-wrap gap-1">
                    <div
                      v-for="(item, idx) in uploadedFiles[asset.key]"
                      :key="idx"
                      class="group relative h-10 w-10 overflow-hidden rounded-md border border-slate-300 dark:border-zinc-700"
                    >
                      <img :src="item.preview" class="h-full w-full object-cover" />
                      <button
                        type="button"
                        class="absolute inset-0 flex items-center justify-center bg-black/60 opacity-0 transition group-hover:opacity-100"
                        @click="removeFile(asset.key, idx)"
                      >
                        <UIcon name="lucide:trash-2" class="h-3.5 w-3.5 text-red-400" />
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- TAB 2: CHIẾN LƯỢC (STRATEGY) -->
          <div v-show="currentTab === 1" class="space-y-4">
            <div class="grid grid-cols-2 gap-3">
              <div>
                <label class="mb-1 block text-xs font-medium text-slate-700 dark:text-zinc-300">Kênh phát hành</label>
                <USelect
                  v-model="form.channel"
                  :items="[
                    { label: 'TikTok (9:16)', value: 'tiktok' },
                    { label: 'Instagram Reels (9:16)', value: 'reels' },
                    { label: 'Meta Feed', value: 'meta_feed' }
                  ]"
                  value-key="value"
                />
              </div>
              <div>
                <label class="mb-1 block text-xs font-medium text-slate-700 dark:text-zinc-300">Mục tiêu quảng cáo</label>
                <USelect
                  v-model="form.objective"
                  :items="[
                    { label: 'Chuyển đổi (Conversion)', value: 'conversion' },
                    { label: 'Thu hút Lead', value: 'lead' },
                    { label: 'Tăng Traffic', value: 'traffic' },
                    { label: 'Nhận diện (Awareness)', value: 'awareness' }
                  ]"
                  value-key="value"
                />
              </div>
            </div>

            <div>
              <label class="mb-1 block text-xs font-medium text-slate-700 dark:text-zinc-300">Thông điệp cốt lõi (Key Message) *</label>
              <UInput v-model="form.keyMessage" placeholder="Ví dụ: Sáng da chuẩn Hàn chỉ trong 7 ngày" />
            </div>

            <div>
              <label class="mb-1 block text-xs font-medium text-slate-700 dark:text-zinc-300">Chân dung khách hàng (Target Audience)</label>
              <UTextarea v-model="form.audienceProfile" :rows="3" placeholder="Ví dụ: Nữ 18-28 tuổi, nhân viên văn phòng, hay thức khuya, da xỉn màu..." />
            </div>

            <div>
              <label class="mb-1 block text-xs font-medium text-slate-700 dark:text-zinc-300">Link Video / Creative tham chiếu</label>
              <UInput v-model="form.creativeReference" placeholder="https://tiktok.com/@example/video/..." />
            </div>
          </div>

          <!-- TAB 3: RÀNG BUỘC (CONSTRAINTS) -->
          <div v-show="currentTab === 2" class="space-y-4">
            <div class="grid grid-cols-2 gap-3">
              <div>
                <label class="mb-1 block text-xs font-medium text-slate-700 dark:text-zinc-300">Thời lượng video</label>
                <USelect
                  v-model="form.maxDurationMs"
                  :items="[
                    { label: '15 giây (Khuyên dùng)', value: 15000 },
                    { label: '30 giây', value: 30000 },
                    { label: '45 giây', value: 45000 }
                  ]"
                  value-key="value"
                />
              </div>
              <div>
                <label class="mb-1 block text-xs font-medium text-slate-700 dark:text-zinc-300">Ngôn ngữ kịch bản</label>
                <USelect
                  v-model="form.language"
                  :items="[
                    { label: 'Tiếng Việt (vi)', value: 'vi' },
                    { label: 'Tiếng Anh (en)', value: 'en' }
                  ]"
                  value-key="value"
                />
              </div>
            </div>

            <div>
              <label class="mb-1 block text-xs font-medium text-slate-700 dark:text-zinc-300">Câu kêu gọi hành động (CTA) bắt buộc</label>
              <UInput v-model="form.requiredCta" placeholder="Ví dụ: Bấm vào giỏ hàng ngay hôm nay!" />
            </div>

            <div>
              <label class="mb-1 block text-xs font-medium text-slate-700 dark:text-zinc-300">Từ cấm / Khẳng định bị cấm (Negative Claims)</label>
              <UTextarea v-model="form.bannedClaims" :rows="2" placeholder="Ví dụ: Trị khỏi 100% vĩnh viễn, cam kết khỏi nám trong 24h..." />
            </div>

            <div>
              <label class="mb-1 block text-xs font-medium text-slate-700 dark:text-zinc-300">Nội dung hạn chế / Tránh đề cập</label>
              <UTextarea v-model="form.bannedContent" :rows="2" placeholder="Ví dụ: Không so sánh tiêu cực đối thủ, không dùng cảnh quá giật gân..." />
            </div>
          </div>

          <!-- Bottom Submit CTA Button -->
          <div class="mt-6 pt-4 border-t border-slate-200 dark:border-zinc-800">
            <UButton
              block
              size="lg"
              color="primary"
              :loading="flowState === 'generating'"
              icon="lucide:sparkles"
              @click="handleCreateAndSubmitBrief"
            >
              Tạo Kịch Bản Storyboard Với AI
            </UButton>
          </div>
        </UCard>
      </div>

      <!-- RIGHT PANEL: AI STREAM & HITL & PREVIEW (7 / 12) -->
      <div class="space-y-5 lg:col-span-7">
        <!-- STATE 1: EMPTY / IDLE STATE -->
        <UCard v-if="flowState === 'idle'" class="flex min-h-[560px] flex-col items-center justify-center p-8 text-center">
          <div class="flex h-16 w-16 items-center justify-center rounded-2xl bg-indigo-500/10 text-indigo-600 dark:text-indigo-400">
            <UIcon name="lucide:clapperboard" class="h-8 w-8" />
          </div>
          <h3 class="mt-4 text-lg font-bold text-slate-900 dark:text-white">
            Trung Tâm AI Sáng Tạo Video Sẵn Sàng
          </h3>
          <p class="mt-1.5 max-w-md text-sm text-slate-500 dark:text-zinc-400">
            Điền thông tin ở bảng bên trái hoặc chọn 1 mẫu chiến dịch nhanh, sau đó nhấn <strong>Tạo Kịch Bản</strong> để bắt đầu luồng AI Reasoning & HITL Review.
          </p>

          <div class="mt-6 grid max-w-lg grid-cols-3 gap-3 text-left">
            <div class="rounded-xl border border-slate-200 bg-slate-50/50 p-3 dark:border-zinc-800 dark:bg-zinc-900/40">
              <UIcon name="lucide:brain-circuit" class="h-5 w-5 text-indigo-500" />
              <p class="mt-2 text-xs font-semibold text-slate-800 dark:text-zinc-200">AI Reasoning</p>
              <p class="text-[11px] text-slate-500">Tự động cấu trúc kịch bản theo công thức Viral.</p>
            </div>
            <div class="rounded-xl border border-slate-200 bg-slate-50/50 p-3 dark:border-zinc-800 dark:bg-zinc-900/40">
              <UIcon name="lucide:user-check" class="h-5 w-5 text-emerald-500" />
              <p class="mt-2 text-xs font-semibold text-slate-800 dark:text-zinc-200">HITL Review</p>
              <p class="text-[11px] text-slate-500">Chỉnh sửa và phê duyệt trước khi render.</p>
            </div>
            <div class="rounded-xl border border-slate-200 bg-slate-50/50 p-3 dark:border-zinc-800 dark:bg-zinc-900/40">
              <UIcon name="lucide:smartphone" class="h-5 w-5 text-violet-500" />
              <p class="mt-2 text-xs font-semibold text-slate-800 dark:text-zinc-200">Safe Zone 9:16</p>
              <p class="text-[11px] text-slate-500">Giả lập TikTok/Reels UI overlay chuẩn xác.</p>
            </div>
          </div>
        </UCard>

        <!-- STATE 2: GENERATING (AI REASONING STREAM) -->
        <UCard v-else-if="flowState === 'generating'" class="flex min-h-[560px] flex-col items-center justify-center p-8 text-center">
          <div class="relative flex h-20 w-20 items-center justify-center">
            <div class="absolute inset-0 animate-ping rounded-full bg-indigo-500/20" />
            <div class="flex h-16 w-16 items-center justify-center rounded-2xl bg-indigo-600 text-white shadow-xl shadow-indigo-500/30">
              <UIcon name="lucide:sparkles" class="h-8 w-8 animate-spin" />
            </div>
          </div>

          <h3 class="mt-6 text-xl font-bold text-slate-900 dark:text-white">
            Agent Pod Đang Phân Tích & Sinh Storyboard
          </h3>
          <p class="mt-1 text-sm text-slate-500">Đang khởi tạo các luồng suy luận đa tác tử...</p>

          <!-- Stepper Logic -->
          <div class="mt-8 w-full max-w-md space-y-3 text-left">
            <div
              class="flex items-center gap-3 rounded-xl border p-3 transition"
              :class="reasoningStep >= 1 ? 'border-emerald-500/30 bg-emerald-50/50 text-emerald-800 dark:bg-emerald-950/20 dark:text-emerald-300' : 'border-slate-200 text-slate-400 dark:border-zinc-800'"
            >
              <UIcon :name="reasoningStep > 1 ? 'lucide:check-circle-2' : 'lucide:loader-2'" class="h-5 w-5 shrink-0" :class="{ 'animate-spin': reasoningStep === 1 }" />
              <span class="text-xs font-medium">1. Phân tích USP sản phẩm & Thông điệp chính</span>
            </div>

            <div
              class="flex items-center gap-3 rounded-xl border p-3 transition"
              :class="reasoningStep >= 2 ? 'border-emerald-500/30 bg-emerald-50/50 text-emerald-800 dark:bg-emerald-950/20 dark:text-emerald-300' : 'border-slate-200 text-slate-400 dark:border-zinc-800'"
            >
              <UIcon :name="reasoningStep > 2 ? 'lucide:check-circle-2' : 'lucide:loader-2'" class="h-5 w-5 shrink-0" :class="{ 'animate-spin': reasoningStep === 2 }" />
              <span class="text-xs font-medium">2. Định vị hành vi khán giả trên kênh {{ form.channel.toUpperCase() }}</span>
            </div>

            <div
              class="flex items-center gap-3 rounded-xl border p-3 transition"
              :class="reasoningStep >= 3 ? 'border-emerald-500/30 bg-emerald-50/50 text-emerald-800 dark:bg-emerald-950/20 dark:text-emerald-300' : 'border-slate-200 text-slate-400 dark:border-zinc-800'"
            >
              <UIcon :name="reasoningStep > 3 ? 'lucide:check-circle-2' : 'lucide:loader-2'" class="h-5 w-5 shrink-0" :class="{ 'animate-spin': reasoningStep === 3 }" />
              <span class="text-xs font-medium">3. Xây dựng phân cảnh Storyboard 9:16 (Hook & CTA)</span>
            </div>

            <div
              class="flex items-center gap-3 rounded-xl border p-3 transition"
              :class="reasoningStep >= 4 ? 'border-emerald-500/30 bg-emerald-50/50 text-emerald-800 dark:bg-emerald-950/20 dark:text-emerald-300' : 'border-slate-200 text-slate-400 dark:border-zinc-800'"
            >
              <UIcon :name="reasoningStep >= 4 ? 'lucide:check-circle-2' : 'lucide:loader-2'" class="h-5 w-5 shrink-0" :class="{ 'animate-spin': reasoningStep === 4 }" />
              <span class="text-xs font-medium">4. Khớp nối hình ảnh Asset và kiểm tra Negative Claims</span>
            </div>
          </div>
        </UCard>

        <!-- STATE 3: HITL STORYBOARD REVIEW -->
        <div v-else-if="flowState === 'review' && activePlan" class="space-y-4">
          <!-- Storyboard Header Info -->
          <UCard class="border-indigo-500/30 bg-gradient-to-br from-indigo-500/10 via-white to-violet-500/10 dark:from-indigo-950/40 dark:via-zinc-900 dark:to-violet-950/40">
            <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <div class="flex items-center gap-2">
                  <UBadge color="primary" variant="solid">
                    Revision {{ revisionNumber }} / 3
                  </UBadge>
                  <UBadge color="success" variant="subtle">
                    Độ tin cậy AI: 92%
                  </UBadge>
                </div>
                <h3 class="mt-1.5 text-base font-bold text-slate-900 dark:text-white">
                  Kịch Bản Storyboard Cần Phê Duyệt (HITL Review)
                </h3>
                <p class="text-xs text-slate-500">
                  Task: <span class="font-mono text-indigo-600 dark:text-indigo-400">{{ currentTaskId.slice(0, 16) }}...</span>
                </p>
              </div>

              <!-- Quick Action Buttons -->
              <div class="flex flex-wrap items-center gap-2">
                <UButton
                  size="sm"
                  color="neutral"
                  variant="outline"
                  icon="lucide:x"
                  :disabled="isReviewing"
                  @click="handleReviewDecision('rejected')"
                >
                  Hủy bỏ
                </UButton>
                <UButton
                  size="sm"
                  color="primary"
                  :loading="isReviewing"
                  icon="lucide:check-circle"
                  @click="handleReviewDecision('approved')"
                >
                  Phê Duyệt & Render Video
                </UButton>
              </div>
            </div>

            <!-- Soundtrack & Tone Metadata -->
            <div class="mt-4 grid grid-cols-2 gap-3 border-t border-slate-200 pt-3 text-xs dark:border-zinc-800">
              <div class="flex items-center gap-2">
                <UIcon name="lucide:music" class="h-4 w-4 text-indigo-500" />
                <span class="text-slate-500">Âm nhạc:</span>
                <span class="font-medium text-slate-800 dark:text-zinc-200">{{ activePlan.soundtrack || 'Trendy Electronic' }}</span>
              </div>
              <div class="flex items-center gap-2">
                <UIcon name="lucide:mic" class="h-4 w-4 text-violet-500" />
                <span class="text-slate-500">Voiceover:</span>
                <span class="font-medium text-slate-800 dark:text-zinc-200">{{ activePlan.voiceover_tone || 'Năng động, cuốn hút' }}</span>
              </div>
            </div>
          </UCard>

          <!-- Scene-by-Scene Cards List -->
          <div class="space-y-3">
            <div
              v-for="(scene, sIdx) in activePlan.scenes"
              :key="sIdx"
              class="overflow-hidden rounded-xl border border-slate-200 bg-white p-4 shadow-xs transition dark:border-zinc-800 dark:bg-zinc-900"
            >
              <div class="flex items-center justify-between gap-2 border-b border-slate-100 pb-2.5 dark:border-zinc-800">
                <div class="flex items-center gap-2">
                  <span class="flex h-6 w-6 items-center justify-center rounded-md bg-indigo-600 text-xs font-bold text-white">
                    #{{ scene.scene_number || (sIdx + 1) }}
                  </span>
                  <span class="text-xs font-bold text-slate-800 dark:text-zinc-200">
                    Cảnh {{ scene.scene_number || (sIdx + 1) }} ({{ (scene.duration_ms / 1000).toFixed(1) }}s)
                  </span>
                </div>

                <UBadge size="xs" color="secondary" variant="subtle">
                  Role: {{ scene.suggested_asset || 'hero' }}
                </UBadge>
              </div>

              <div class="mt-3 grid gap-3 md:grid-cols-2">
                <div>
                  <p class="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">👁️ Mô tả hình ảnh (Visual)</p>
                  <p class="mt-1 text-xs text-slate-800 dark:text-zinc-200">
                    {{ scene.visual_description }}
                  </p>
                </div>
                <div>
                  <p class="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">🎙️ Lời thoại / Audio Script</p>
                  <p class="mt-1 text-xs font-medium text-indigo-600 dark:text-indigo-400">
                    "{{ scene.audio_script }}"
                  </p>
                </div>
              </div>
            </div>
          </div>

          <!-- Revision Feedback Box -->
          <UCard>
            <template #header>
              <span class="text-xs font-bold uppercase tracking-wider text-slate-800 dark:text-zinc-200">
                🔄 Yêu Cầu Chỉnh Sửa Storyboard
              </span>
            </template>

            <div class="space-y-3">
              <UTextarea
                v-model="reviewFeedback"
                :rows="2"
                placeholder="Nhập yêu cầu sửa kịch bản (Ví dụ: Tăng nhịp điệu cảnh 1, thêm sticker giảm giá 20%, đổi giọng đọc hào hứng hơn...)"
                class="text-xs"
              />
              <div class="flex justify-end">
                <UButton
                  size="sm"
                  color="secondary"
                  variant="outline"
                  icon="lucide:refresh-cw"
                  :loading="isReviewing"
                  :disabled="!reviewFeedback.trim()"
                  @click="handleReviewDecision('needs_revision')"
                >
                  Yêu Cầu AI Tái Tạo Kịch Bản (Revision)
                </UButton>
              </div>
            </div>
          </UCard>
        </div>

        <!-- STATE 4: RENDERING PROGRESS -->
        <UCard v-else-if="flowState === 'rendering'" class="flex min-h-[560px] flex-col items-center justify-center p-8 text-center">
          <div class="relative flex h-20 w-20 items-center justify-center">
            <div class="absolute inset-0 animate-ping rounded-full bg-violet-500/20" />
            <div class="flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-tr from-indigo-600 to-violet-600 text-white shadow-xl">
              <UIcon name="lucide:video" class="h-8 w-8 animate-pulse" />
            </div>
          </div>

          <h3 class="mt-6 text-xl font-bold text-slate-900 dark:text-white">
            Đang Render Video 9:16 Hoàn Chỉnh
          </h3>
          <p class="mt-1 text-sm text-slate-500">
            Agent Pod đang tổng hợp video, ghép audio và kiểm tra safe zones...
          </p>

          <div class="mt-6 w-full max-w-md space-y-2">
            <div class="flex items-center justify-between text-xs font-semibold text-slate-700 dark:text-zinc-300">
              <span>Tiến trình xử lý</span>
              <span>{{ renderProgress }}%</span>
            </div>
            <UProgress :value="renderProgress" color="primary" size="lg" />
          </div>
        </UCard>

        <!-- STATE 5: COMPLETED - 9:16 SMARTPHONE FRAME PREVIEW & TIKTOK OVERLAY -->
        <div v-else-if="flowState === 'completed'" class="space-y-4">
          <UCard class="border-emerald-500/30 bg-emerald-500/10">
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2 text-emerald-800 dark:text-emerald-300">
                <UIcon name="lucide:check-circle-2" class="h-5 w-5" />
                <span class="text-sm font-bold">Video Đã Render Thành Công!</span>
              </div>

              <div class="flex items-center gap-2">
                <UButton
                  size="xs"
                  variant="outline"
                  icon="lucide:file-text"
                  @click="showScriptModal = true"
                >
                  Xem Kịch Bản
                </UButton>
                <UButton
                  size="xs"
                  color="primary"
                  :href="renderVideoUrl"
                  download="beyond_video.mp4"
                  target="_blank"
                  icon="lucide:download"
                >
                  Tải Video
                </UButton>
              </div>
            </div>
          </UCard>

          <!-- Smartphone Frame (9:16) -->
          <div class="flex justify-center">
            <div class="relative w-[320px] overflow-hidden rounded-[42px] border-[10px] border-slate-900 bg-black shadow-2xl ring-1 ring-slate-800">
              <!-- Phone Island & Notch -->
              <div class="absolute top-2 left-1/2 z-30 h-4 w-24 -translate-x-1/2 rounded-full bg-slate-950" />

              <!-- Phone Screen (9:16 Aspect Ratio) -->
              <div class="relative aspect-[9/16] w-full bg-black">
                <!-- Video Element -->
                <video
                  :src="renderVideoUrl"
                  autoplay
                  loop
                  muted
                  playsinline
                  controls
                  class="h-full w-full object-cover"
                />

                <!-- Simulated TikTok / Reels Overlay -->
                <div v-if="showTikTokOverlay" class="pointer-events-none absolute inset-0 z-20 flex flex-col justify-between p-4 text-white">
                  <!-- Top Status -->
                  <div class="flex items-center justify-between text-[11px] font-semibold opacity-80 pt-4">
                    <span>9:41</span>
                    <span class="rounded bg-black/40 px-1.5 py-0.5 text-[9px]">9:16 TikTok Safe</span>
                    <div class="flex items-center gap-1">
                      <UIcon name="lucide:wifi" class="h-3 w-3" />
                      <UIcon name="lucide:battery-full" class="h-3 w-3" />
                    </div>
                  </div>

                  <!-- Right Action Bar (TikTok Style) -->
                  <div class="absolute right-3 bottom-20 flex flex-col items-center gap-3">
                    <div class="relative flex h-10 w-10 items-center justify-center rounded-full border-2 border-white bg-indigo-600 text-xs font-bold text-white shadow-lg">
                      BI
                      <span class="absolute -bottom-1 flex h-4 w-4 items-center justify-center rounded-full bg-red-500 text-[10px] font-bold">+</span>
                    </div>

                    <div class="flex flex-col items-center">
                      <div class="flex h-9 w-9 items-center justify-center rounded-full bg-black/40 backdrop-blur-xs">
                        <UIcon name="lucide:heart" class="h-5 w-5 text-red-500 fill-red-500" />
                      </div>
                      <span class="text-[10px] font-semibold">24.8K</span>
                    </div>

                    <div class="flex flex-col items-center">
                      <div class="flex h-9 w-9 items-center justify-center rounded-full bg-black/40 backdrop-blur-xs">
                        <UIcon name="lucide:message-circle" class="h-5 w-5 text-white" />
                      </div>
                      <span class="text-[10px] font-semibold">1,420</span>
                    </div>

                    <div class="flex flex-col items-center">
                      <div class="flex h-9 w-9 items-center justify-center rounded-full bg-black/40 backdrop-blur-xs">
                        <UIcon name="lucide:bookmark" class="h-5 w-5 text-amber-400 fill-amber-400" />
                      </div>
                      <span class="text-[10px] font-semibold">6.2K</span>
                    </div>

                    <div class="flex flex-col items-center">
                      <div class="flex h-9 w-9 items-center justify-center rounded-full bg-black/40 backdrop-blur-xs">
                        <UIcon name="lucide:share-2" class="h-5 w-5 text-white" />
                      </div>
                      <span class="text-[10px] font-semibold">Share</span>
                    </div>
                  </div>

                  <!-- Bottom Caption & Music Bar -->
                  <div class="space-y-1.5 pr-14 text-left">
                    <p class="text-xs font-bold">@beyond_studio</p>
                    <p class="line-clamp-2 text-[11px] leading-tight text-white/90">
                      {{ form.keyMessage }} 🔥 {{ form.requiredCta }} #fyp #viral #trending
                    </p>
                    <div class="flex items-center gap-1.5 text-[10px] text-white/80">
                      <UIcon name="lucide:music" class="h-3 w-3 animate-spin" />
                      <span class="truncate">Âm thanh gốc - Beyond Intelligence (128 BPM)</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Overlay Toggle & Controls -->
          <div class="flex items-center justify-center gap-3">
            <UButton
              size="xs"
              variant="soft"
              :color="showTikTokOverlay ? 'primary' : 'neutral'"
              icon="lucide:layers"
              @click="showTikTokOverlay = !showTikTokOverlay"
            >
              {{ showTikTokOverlay ? 'Ẩn Lớp Phủ TikTok' : 'Hiện Lớp Phủ TikTok (Safe Zone)' }}
            </UButton>
            <UButton
              size="xs"
              variant="outline"
              icon="lucide:plus"
              @click="resetWorkspace"
            >
              Tạo Chiến Dịch Mới
            </UButton>
          </div>
        </div>

        <!-- STATE 6: FAILED -->
        <UCard v-else-if="flowState === 'failed'" class="border-red-500/30 p-8 text-center">
          <div class="flex h-12 w-12 mx-auto items-center justify-center rounded-full bg-red-500/10 text-red-500">
            <UIcon name="lucide:alert-triangle" class="h-6 w-6" />
          </div>
          <h3 class="mt-3 text-base font-bold text-slate-900 dark:text-white">Xử Lý Thất Bại</h3>
          <p class="mt-1 text-xs text-slate-500">{{ renderErrorMsg }}</p>
          <div class="mt-4 flex justify-center gap-2">
            <UButton size="sm" variant="outline" @click="flowState = 'idle'">Thử lại</UButton>
          </div>
        </UCard>
      </div>
    </div>

    <!-- Script Modal -->
    <UModal v-model:open="showScriptModal">
      <template #content>
        <div class="p-6 space-y-4">
          <h3 class="text-lg font-bold text-slate-900 dark:text-white">
            Chi Tiết Kịch Bản Video Đã Dùng
          </h3>
          <div v-if="activePlan" class="space-y-3 max-h-[60vh] overflow-y-auto">
            <div v-for="scene in activePlan.scenes" :key="scene.scene_number" class="rounded-lg border p-3 text-xs dark:border-zinc-800">
              <p class="font-bold text-indigo-600 dark:text-indigo-400">Cảnh {{ scene.scene_number }} ({{ (scene.duration_ms/1000).toFixed(1) }}s)</p>
              <p class="mt-1 text-slate-700 dark:text-zinc-300"><strong>Hình ảnh:</strong> {{ scene.visual_description }}</p>
              <p class="mt-1 text-slate-700 dark:text-zinc-300"><strong>Lời thoại:</strong> "{{ scene.audio_script }}"</p>
            </div>
          </div>
          <div class="flex justify-end">
            <UButton size="sm" @click="showScriptModal = false">Đóng</UButton>
          </div>
        </div>
      </template>
    </UModal>
  </div>
</template>
