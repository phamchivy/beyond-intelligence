<script setup lang="ts">
import type { StoryboardPlan, StoryboardScene } from '../../../types/brief'

const route = useRoute()
const { reviewStoryboard } = usePipelineApi()

const taskId = computed(() => String(route.query.taskId || ''))
const storyboardId = computed(() => String(route.params.id || route.query.storyboardId || ''))
const reviewFeedback = ref('')
const isSubmitting = ref(false)
const revisionNumber = ref(1)

const defaultPlan: StoryboardPlan = {
  scenes: [
    {
      scene_number: 1,
      duration_ms: 3000,
      visual_description: 'Cận cảnh mở đầu ấn tượng với vấn đề nổi cộm. Chuyển cảnh nhanh với hiệu ứng zoom thu hút 3s đầu.',
      audio_script: 'Bạn có đang tìm kiếm giải pháp đột phá cho cuộc sống?',
      suggested_asset: 'hero'
    },
    {
      scene_number: 2,
      duration_ms: 4500,
      visual_description: 'Trải nghiệm thực tế sản phẩm. Xuất hiện icon nổi bật tính năng USP cốt lõi.',
      audio_script: 'Khám phá ngay giải pháp tối ưu với hiệu năng vượt trội.',
      suggested_asset: 'closeup'
    },
    {
      scene_number: 3,
      duration_ms: 4500,
      visual_description: 'Lifestyle shot: Người dùng tươi cười, hài lòng khi trải nghiệm sự khác biệt.',
      audio_script: 'Hiệu quả rõ rệt, tiết kiệm thời gian và tối ưu chi phí cho bạn.',
      suggested_asset: 'lifestyle'
    },
    {
      scene_number: 4,
      duration_ms: 3000,
      visual_description: 'Màn hình kết thúc với Logo thương hiệu, thông tin ưu đãi và nút CTA nổi bật.',
      audio_script: 'Bấm vào link bên dưới để nhận ưu đãi đặc quyền ngay hôm nay!',
      suggested_asset: 'logo'
    }
  ],
  soundtrack: 'Upbeat Tech Trending Beats (128 BPM)',
  voiceover_tone: 'Năng động, tự tin, truyền cảm hứng'
}

const currentPlan = ref<StoryboardPlan>(defaultPlan)

const submitDecision = async (decision: 'approved' | 'needs_revision' | 'rejected') => {
  isSubmitting.value = true
  try {
    const result = await reviewStoryboard({
      taskId: taskId.value || `task-${Date.now()}`,
      storyboardId: storyboardId.value || `story-${Date.now()}`,
      decision,
      feedback: reviewFeedback.value || undefined
    })

    if (decision === 'approved') {
      await navigateTo(`/renders/${result.render_job_id || 'render-001'}`)
    } else if (decision === 'needs_revision') {
      if (result.plan) {
        currentPlan.value = result.plan
        revisionNumber.value = result.revision_number || (revisionNumber.value + 1)
        reviewFeedback.value = ''
      }
    } else {
      await navigateTo('/briefs')
    }
  } catch (err) {
    console.error('Review decision error:', err)
  } finally {
    isSubmitting.value = false
  }
}
</script>

<template>
  <div class="space-y-6">
    <!-- Header -->
    <section class="flex flex-col gap-4 rounded-3xl border border-slate-200 bg-white p-5 shadow-xs dark:border-zinc-800 dark:bg-zinc-900 md:flex-row md:items-center md:justify-between">
      <div>
        <div class="flex items-center gap-2">
          <UBadge color="primary" variant="solid">
            Revision {{ revisionNumber }} / 3
          </UBadge>
          <UBadge color="success" variant="subtle">
            Độ tin cậy AI: 92%
          </UBadge>
        </div>
        <h1 class="mt-1.5 text-2xl font-bold text-slate-900 dark:text-white">
          Đánh Giá Storyboard (HITL Review)
        </h1>
        <p class="text-xs text-slate-500">
          Task ID: {{ taskId || 'task-demo' }} • Storyboard ID: {{ storyboardId }}
        </p>
      </div>

      <div class="flex flex-wrap items-center gap-2">
        <UButton
          variant="outline"
          color="neutral"
          :disabled="isSubmitting"
          @click="submitDecision('rejected')"
        >
          Hủy bỏ
        </UButton>
        <UButton
          variant="outline"
          color="secondary"
          :loading="isSubmitting"
          icon="lucide:refresh-cw"
          :disabled="!reviewFeedback.trim()"
          @click="submitDecision('needs_revision')"
        >
          Yêu cầu sửa
        </UButton>
        <UButton
          color="primary"
          :loading="isSubmitting"
          icon="lucide:check-circle"
          @click="submitDecision('approved')"
        >
          Phê duyệt & Render
        </UButton>
      </div>
    </section>

    <!-- Grid -->
    <div class="grid gap-6 xl:grid-cols-12">
      <!-- Left: Scene List (8 / 12) -->
      <div class="space-y-4 xl:col-span-8">
        <UCard>
          <template #header>
            <div class="flex items-center justify-between">
              <h2 class="text-sm font-bold uppercase tracking-wider text-slate-800 dark:text-zinc-200">
                Danh Sách Phân Cảnh (Scenes)
              </h2>
              <span class="text-xs text-slate-500">{{ currentPlan.scenes.length }} cảnh quay 9:16</span>
            </div>
          </template>

          <div class="space-y-3">
            <div
              v-for="(scene, idx) in currentPlan.scenes"
              :key="idx"
              class="rounded-xl border border-slate-200 bg-slate-50/50 p-4 transition dark:border-zinc-800 dark:bg-zinc-900/50"
            >
              <div class="flex items-center justify-between border-b border-slate-200 pb-2 dark:border-zinc-800">
                <div class="flex items-center gap-2">
                  <span class="flex h-6 w-6 items-center justify-center rounded-md bg-indigo-600 text-xs font-bold text-white">
                    #{{ scene.scene_number || (idx + 1) }}
                  </span>
                  <span class="text-xs font-bold text-slate-800 dark:text-zinc-200">
                    Cảnh {{ scene.scene_number || (idx + 1) }} ({{ (scene.duration_ms / 1000).toFixed(1) }}s)
                  </span>
                </div>
                <UBadge size="xs" color="secondary" variant="subtle">
                  Role: {{ scene.suggested_asset || 'hero' }}
                </UBadge>
              </div>

              <div class="mt-3 grid gap-3 md:grid-cols-2">
                <div>
                  <p class="text-[11px] font-semibold uppercase tracking-wider text-slate-500">Mô tả hình ảnh</p>
                  <p class="mt-1 text-xs text-slate-800 dark:text-zinc-200">{{ scene.visual_description }}</p>
                </div>
                <div>
                  <p class="text-[11px] font-semibold uppercase tracking-wider text-slate-500">Lời thoại / Voiceover</p>
                  <p class="mt-1 text-xs font-medium text-indigo-600 dark:text-indigo-400">"{{ scene.audio_script }}"</p>
                </div>
              </div>
            </div>
          </div>
        </UCard>
      </div>

      <!-- Right: Settings & Feedback (4 / 12) -->
      <div class="space-y-4 xl:col-span-4">
        <UCard>
          <template #header>
            <h2 class="text-sm font-bold uppercase tracking-wider text-slate-800 dark:text-zinc-200">
              Âm Nhạc & Giọng Đọc
            </h2>
          </template>

          <div class="space-y-3 text-xs">
            <div>
              <span class="text-slate-500">Soundtrack:</span>
              <p class="font-semibold text-slate-800 dark:text-zinc-200">{{ currentPlan.soundtrack }}</p>
            </div>
            <div>
              <span class="text-slate-500">Voiceover Tone:</span>
              <p class="font-semibold text-slate-800 dark:text-zinc-200">{{ currentPlan.voiceover_tone }}</p>
            </div>
          </div>
        </UCard>

        <UCard>
          <template #header>
            <h2 class="text-sm font-bold uppercase tracking-wider text-slate-800 dark:text-zinc-200">
              Phản Hồi Chỉnh Sửa
            </h2>
          </template>

          <div class="space-y-3">
            <UTextarea
              v-model="reviewFeedback"
              :rows="4"
              placeholder="Nhập yêu cầu sửa kịch bản nếu cần AI tạo lại revision mới..."
              class="text-xs"
            />
            <UButton
              block
              size="sm"
              variant="outline"
              color="secondary"
              icon="lucide:refresh-cw"
              :disabled="!reviewFeedback.trim()"
              @click="submitDecision('needs_revision')"
            >
              Gửi Yêu Cầu Sửa
            </UButton>
          </div>
        </UCard>
      </div>
    </div>
  </div>
</template>

