<script setup lang="ts">
const isUploading = ref(false)
const uploadProgress = ref(0)

const formState = reactive({
  category: 'ecommerce',
  targetPlatform: 'tiktok',
  caption: 'Mẫu áo chống nắng thế hệ mới hè 2026 - Giảm ngay 30% hôm nay! #sale #fashion',
  autoMitigate: true
})

const categories = [
  { label: 'E-Commerce / Bán lẻ', value: 'ecommerce' },
  { label: 'Công nghệ & Điện tử', value: 'tech' },
  { label: 'Thời trang & Làm đẹp', value: 'fashion' },
  { label: 'F&B Thực phẩm', value: 'fnb' }
]

const platforms = [
  { label: 'TikTok Ads / Shop', value: 'tiktok' },
  { label: 'Meta Reels & Stories', value: 'meta' },
  { label: 'YouTube Shorts', value: 'youtube' }
]

const startScan = async () => {
  isUploading.value = true
  uploadProgress.value = 15

  // Mô phỏng tiến trình tải lên và khởi chạy Agent
  const interval = setInterval(() => {
    uploadProgress.value += 20
    if (uploadProgress.value >= 100) {
      clearInterval(interval)
      setTimeout(() => {
        navigateTo('/scan/VID-9021')
      }, 500)
    }
  }, 400)
}
</script>

<template>
  <div class="max-w-4xl mx-auto flex flex-col gap-6">
    <div>
      <h1 class="text-2xl font-bold text-highlighted tracking-tight">Video Scanning Studio</h1>
      <p class="text-sm text-muted mt-1">
        Tải lên video để quét tự động các vi phạm chính sách kiểm duyệt và nhận đề xuất tăng trưởng CVR.
      </p>
    </div>

    <UCard>
      <form class="flex flex-col gap-5" @submit.prevent="startScan">
        <!-- Drag & Drop Upload Box -->
        <div class="border-2 border-dashed border-muted hover:border-primary/60 rounded-xl p-8 flex flex-col items-center justify-center gap-3 bg-muted/10 transition-colors cursor-pointer">
          <div class="size-12 rounded-full bg-primary/10 text-primary flex items-center justify-center">
            <UIcon name="i-lucide-upload-cloud" class="size-6" />
          </div>
          <div class="text-center">
            <p class="text-sm font-semibold text-highlighted">Kéo và thả file video của bạn vào đây</p>
            <p class="text-xs text-muted mt-0.5">Hỗ trợ MP4, MOV (Tối đa 250MB, chuẩn dọc 9:16)</p>
          </div>
          <UBadge color="neutral" variant="outline" size="xs">
            TikTok_Summer_Sale_Campaign_v2.mp4 (48.2 MB)
          </UBadge>
        </div>

        <!-- Progress Bar when uploading -->
        <div v-if="isUploading" class="flex flex-col gap-1.5">
          <div class="flex justify-between text-xs font-medium">
            <span class="text-primary flex items-center gap-1.5">
              <UIcon name="i-lucide-loader-2" class="size-3.5 animate-spin" />
              Đang phân tích khung hình & trích xuất vector vi phạm...
            </span>
            <span class="font-mono">{{ uploadProgress }}%</span>
          </div>
          <div class="w-full bg-muted rounded-full h-2 overflow-hidden">
            <div class="bg-primary h-full transition-all duration-300" :style="{ width: `${uploadProgress}%` }" />
          </div>
        </div>

        <!-- Metadata Form -->
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <UFormField label="Ngành hàng / Category">
            <select
              v-model="formState.category"
              class="w-full rounded-lg border border-default bg-elevated px-3 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-primary"
            >
              <option v-for="cat in categories" :key="cat.value" :value="cat.value">{{ cat.label }}</option>
            </select>
          </UFormField>

          <UFormField label="Nền tảng mục tiêu">
            <select
              v-model="formState.targetPlatform"
              class="w-full rounded-lg border border-default bg-elevated px-3 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-primary"
            >
              <option v-for="plat in platforms" :key="plat.value" :value="plat.value">{{ plat.label }}</option>
            </select>
          </UFormField>
        </div>

        <UFormField label="Caption / Tiêu đề Quảng cáo" description="AI sẽ quét cả text trong video và phần mô tả">
          <textarea
            v-model="formState.caption"
            rows="3"
            class="w-full rounded-lg border border-default bg-elevated p-3 text-xs focus:outline-none focus:ring-2 focus:ring-primary"
          />
        </UFormField>

        <!-- Submit Button -->
        <div class="flex items-center justify-end gap-3 pt-3 border-t border-muted">
          <UButton
            type="submit"
            color="primary"
            variant="solid"
            size="md"
            icon="i-lucide-scan"
            label="Kích hoạt Phân tích AI"
            :loading="isUploading"
          />
        </div>
      </form>
    </UCard>
  </div>
</template>