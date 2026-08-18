<script setup lang="ts">
const { uploadVideo } = useEngineApi()
const toast = useToast()

const uploadedFile = ref<File | null>(null)
const isUploading = ref(false)
const uploadProgress = ref(0)

const formState = reactive({
  productTitle: 'Mẫu áo chống nắng thế hệ mới hè 2026 - Giảm ngay 30% hôm nay! #sale #fashion',
  productCategory: 'ecommerce',
  targetMarket: 'VN'
})

const categories = [
  { label: 'E-Commerce / Bán lẻ', value: 'ecommerce' },
  { label: 'Công nghệ & Điện tử', value: 'tech' },
  { label: 'Thời trang & Làm đẹp', value: 'fashion' },
  { label: 'F&B Thực phẩm', value: 'fnb' },
  { label: 'Sức khỏe & Mỹ phẩm', value: 'beauty_health' }
]

const markets = [
  { label: 'Việt Nam (TikTok Shop / Shopee Video)', value: 'VN' },
  { label: 'Hoa Kỳ (Meta Reels / TikTok US)', value: 'US' },
  { label: 'Đông Nam Á - SEA', value: 'SEA' },
  { label: 'Toàn cầu (Global Shorts)', value: 'GLOBAL' }
]

const handleSubmit = async () => {
  if (!uploadedFile.value) {
    toast.add({
      title: 'Chưa chọn file',
      description: 'Vui lòng chọn video cần quét.',
      color: 'warning'
    })
    return
  }

  try {
    isUploading.value = true
    uploadProgress.value = 30

    const progressTimer = setInterval(() => {
      if (uploadProgress.value < 90) {
        uploadProgress.value += 15
      }
    }, 200)

    const payload: VideoUploadPayload = {
      videoFile: uploadedFile.value,
      productTitle: formState.productTitle,
      productCategory: formState.productCategory,
      targetMarket: formState.targetMarket
    }

    // Nhận response theo schema thực tế
    const response = await uploadVideo(payload)

    clearInterval(progressTimer)
    uploadProgress.value = 100

    toast.add({
      title: 'Tải lên thành công',
      description: response.message || `Mã phân tích: ${response.analysisId}`,
      color: 'success'
    })

    // Điều hướng theo analysisId
    setTimeout(() => {
      navigateTo(`/scan/${response.analysisId}`)
    }, 400)
  } catch (error: any) {
    toast.add({
      title: 'Lỗi tải lên',
      description: error?.message || 'Không thể kết nối máy chủ.',
      color: 'error'
    })
  } finally {
    isUploading.value = false
  }
}
</script>

<template>
  <div class="max-w-4xl mx-auto flex flex-col gap-6">
    <div>
      <h1 class="text-2xl font-bold text-highlighted tracking-tight">Video Scanning Studio</h1>
      <p class="text-sm text-muted mt-1">
        Tải video lên hệ thống phân tích Agentic AI để nhận diện vi phạm kiểm duyệt và tối ưu hóa tỷ lệ chuyển đổi.
      </p>
    </div>

    <UCard>
      <form class="flex flex-col gap-5" @submit.prevent="handleSubmit">
        <UFormField
          label="Video nguồn (videoFile)"
          name="videoFile"
          description="Hỗ trợ MP4, MOV (Tối đa 250MB, chuẩn dọc 9:16)"
          required
        >
          <UFileUpload
            v-if="!uploadedFile"
            v-model="uploadedFile"
            accept="video/mp4,video/quicktime"
            variant="area"
            icon="i-lucide-upload-cloud"
            label="Kéo & thả video vào đây hoặc bấm để chọn file"
            description="MP4 hoặc MOV (Tối đa 250MB)"
            :disabled="isUploading"
          >
            <template #file-leading>
              <div class="size-8 rounded bg-primary/10 text-primary flex items-center justify-center">
                <UIcon name="i-lucide-film" class="size-4" />
              </div>
            </template>
          </UFileUpload>
          <div v-else class="flex items-center gap-3 p-3 rounded-lg bg-muted/20 border border-muted">
            <UIcon name="i-lucide-film" class="size-6 text-primary" />
            <div class="flex flex-col gap-0.5">
              <span class="font-medium text-sm">{{ uploadedFile.name }}</span>
              <span class="text-xs text-muted">{{ (uploadedFile.size / (1024 * 1024)).toFixed(2) }} MB</span>
            </div>
            <UButton
              type="button"
              color="error"
              variant="ghost"
              size="sm"
              icon="i-lucide-x"
              label="Xóa"
              @click="uploadedFile = null"
              :disabled="isUploading"
            />
          </div>
        </UFormField>

        <!-- Loading & Status Bar -->
        <div v-if="isUploading" class="flex flex-col gap-1.5 p-3 rounded-lg bg-muted/20 border border-muted">
          <div class="flex justify-between text-xs font-medium">
            <span class="text-primary flex items-center gap-1.5">
              <UIcon name="i-lucide-loader-2" class="size-3.5 animate-spin" />
              Đang tải lên và đưa vào hàng đợi phân tích Agent...
            </span>
            <span class="font-mono font-bold">{{ uploadProgress }}%</span>
          </div>
          <div class="w-full bg-muted rounded-full h-2 overflow-hidden">
            <div
              class="bg-primary h-full transition-all duration-300 rounded-full"
              :style="{ width: `${uploadProgress}%` }"
            />
          </div>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <UFormField label="Ngành hàng sản phẩm (productCategory)" required>
            <select
              v-model="formState.productCategory"
              :disabled="isUploading"
              class="w-full rounded-lg border border-default bg-elevated px-3 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-primary"
            >
              <option v-for="cat in categories" :key="cat.value" :value="cat.value">
                {{ cat.label }}
              </option>
            </select>
          </UFormField>

          <UFormField label="Thị trường mục tiêu (targetMarket)" required>
            <select
              v-model="formState.targetMarket"
              :disabled="isUploading"
              class="w-full rounded-lg border border-default bg-elevated px-3 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-primary"
            >
              <option v-for="market in markets" :key="market.value" :value="market.value">
                {{ market.label }}
              </option>
            </select>
          </UFormField>
        </div>

        <UFormField
          label="Tiêu đề / Caption Sản phẩm (productTitle)"
          description="Nội dung mô tả chiến dịch để AI đối soát cùng âm thanh và text trong video"
          required
        >
          <textarea
            v-model="formState.productTitle"
            rows="3"
            :disabled="isUploading"
            class="w-full rounded-lg border border-default bg-elevated p-3 text-xs focus:outline-none focus:ring-2 focus:ring-primary"
          />
        </UFormField>

        <div class="flex items-center justify-end gap-3 pt-3 border-t border-muted">
          <UButton
            type="submit"
            color="primary"
            variant="solid"
            size="md"
            icon="i-lucide-scan"
            label="Tải lên & Khởi chạy Agent"
            :disabled="!uploadedFile"
            :loading="isUploading"
          />
        </div>
      </form>
    </UCard>
  </div>
</template>