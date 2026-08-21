<script setup lang="ts">
const { createBrief, submitBriefForReview } = usePipelineApi()

const form = reactive({
  title: '',
  productName: '',
  productCategory: '',
  productPrice: '',
  productUsp: '',
  productFeatures: '',
  productOffer: '',
  allowedClaims: '',
  audienceProfile: '',
  objective: 'Conversion',
  keyMessage: '',
  channel: 'Reels',
  aspectRatio: '9:16',
  creativeReference: '',
  maxDurationMs: '8',
  language: 'vi',
  requiredCta: '',
  bannedClaims: '',
  bannedContent: '',
  productCategoryText: ''
})

const assetTypes = ['hero', 'detail', 'lifestyle', 'variant', 'logo']
const assetFiles = reactive<Record<string, File[]>>({
  hero: [],
  detail: [],
  lifestyle: [],
  variant: [],
  logo: []
})

const toStringArray = (raw: string) => raw
  .split(/[\n,]+/)
  .map(item => item.trim())
  .filter(Boolean)

const saveDraft = async () => {
  const payload = {
   title: form.title || form.productName || 'Campaign draft',
   productName: form.productName,
   productCategory: form.productCategory || form.productCategoryText,
   productPrice: Number(form.productPrice || 0),
   productUsp: form.productUsp,
   productFeatures: toStringArray(form.productFeatures),
   productOffer: form.productOffer,
   allowedClaims: toStringArray(form.allowedClaims),
   audienceProfile: form.audienceProfile,
   objective: form.objective,
   keyMessage: form.keyMessage,
   channel: form.channel,
   aspectRatio: form.aspectRatio,
   creativeReference: form.creativeReference,
   maxDurationMs: Number(form.maxDurationMs || 18000),
   language: form.language,
   requiredCta: form.requiredCta,
   bannedClaims: toStringArray(form.bannedClaims),
   bannedContent: toStringArray(form.bannedContent)
  }

  const response = await createBrief(payload)
  await navigateTo(`/briefs/${response.id}`)
}

const submitForAiReview = async () => {
  const payload = {
   productName: form.productName,
   productCategory: form.productCategory || form.productCategoryText,
   productPrice: Number(form.productPrice || 0),
   productUsp: form.productUsp,
   productFeatures: toStringArray(form.productFeatures),
   productOffer: form.productOffer,
   allowedClaims: toStringArray(form.allowedClaims),
   audienceProfile: form.audienceProfile,
   objective: form.objective,
   keyMessage: form.keyMessage,
   channel: form.channel,
   aspectRatio: form.aspectRatio,
   creativeReference: form.creativeReference,
   maxDurationMs: Number(form.maxDurationMs || 18000),
   language: form.language,
   requiredCta: form.requiredCta,
   bannedClaims: toStringArray(form.bannedClaims),
   bannedContent: toStringArray(form.bannedContent),
   assets: Object.values(assetFiles).flat()
  }

  const response = await submitBriefForReview(payload)
  const storyboardUrl = `/briefs/${response.storyboardId}/storyboard?taskId=${encodeURIComponent(response.taskId)}&storyboardText=${encodeURIComponent(response.storyboardText)}`
  await navigateTo(storyboardUrl)
}
</script>

<template>
  <div class="space-y-6">
   <section class="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
     <div>
       <p class="text-sm uppercase tracking-[0.22em] text-indigo-300">Tạo chiến dịch</p>
       <h1 class="mt-2 text-3xl font-semibold text-white">Thêm brief mới</h1>
     </div>

     <div class="flex items-center gap-2">
       <UButton variant="outline" @click="saveDraft">Lưu nháp</UButton>
       <UButton color="primary" @click="submitForAiReview">Gửi cho AI</UButton>
     </div>
   </section>

   <div class="grid gap-6 xl:grid-cols-[1.4fr_0.6fr]">
     <div class="space-y-6">
       <UCard class="border border-white/10 bg-white/5">
         <template #header>
           <h2 class="text-lg font-semibold text-white">Thông tin sản phẩm</h2>
         </template>

         <div class="grid gap-4 md:grid-cols-2">
           <UInput v-model="form.productName" label="Tên sản phẩm" placeholder="Ví dụ: Aether Pro" />
           <UInput v-model="form.productCategory" label="Danh mục" placeholder="Ví dụ: Laptop" />
           <UInput v-model="form.productPrice" type="number" label="Giá" placeholder="899" />
           <UInput v-model="form.productCategoryText" label="Phân loại phụ" placeholder="Ví dụ: Premium / Workstation" />
           <UTextarea v-model="form.productUsp" label="USP" :rows="3" class="md:col-span-2" placeholder="Mô tả điểm khác biệt cốt lõi của sản phẩm..." />
           <UTextarea v-model="form.productFeatures" label="Tính năng" :rows="3" class="md:col-span-2" placeholder="Mỗi dòng hoặc mỗi mục cách nhau bằng dấu phẩy" />
           <UTextarea v-model="form.productOffer" label="Ưu đãi / chương trình khuyến mãi" :rows="3" class="md:col-span-2" placeholder="Ví dụ: Giảm 20% trong tháng đầu ra mắt" />
           <UTextarea v-model="form.allowedClaims" label="Khẳng định được phép" :rows="2" class="md:col-span-2" placeholder="Mỗi claim trên 1 dòng hoặc phân cách bằng dấu phẩy" />
         </div>
       </UCard>

       <UCard class="border border-white/10 bg-white/5">
         <template #header>
           <h2 class="text-lg font-semibold text-white">Tài nguyên / asset</h2>
         </template>

         <div class="space-y-4">
           <div v-for="type in assetTypes" :key="type" class="rounded-2xl border border-dashed border-zinc-200 bg-zinc-50 p-4 dark:border-zinc-700 dark:bg-zinc-900/40">
             <div class="mb-3 flex items-center justify-between gap-3">
               <div>
                 <p class="text-sm font-semibold capitalize text-zinc-800 dark:text-white">{{ type }} assets</p>
                 <p class="text-xs text-zinc-500 dark:text-zinc-400">File tham chiếu cho loại asset này</p>
               </div>
               <UBadge v-if="assetFiles[type]?.length" color="primary" variant="soft">
                 {{ assetFiles[type].length }} file
               </UBadge>
             </div>

             <UFileUpload
               v-model="assetFiles[type]"
               :label="`Tải lên ${type} assets`"
               :description="'PNG, JPG, MP4, MOV, PDF hoặc hình ảnh tham khảo'"
               multiple
               accept="image/*,.png,.jpg,.jpeg,.webp,.mp4,.mov,.pdf"
               :preview="true"
               class="w-full"
             />

             <ul v-if="assetFiles[type]?.length" class="mt-3 space-y-2">
               <li v-for="(file, index) in assetFiles[type]" :key="`${type}-${file.name}-${index}`" class="flex items-center justify-between gap-3 rounded-xl border border-zinc-200 bg-white px-3 py-2 text-sm text-zinc-700 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-200">
                 <span class="truncate">{{ file.name }}</span>
                 <span class="shrink-0 text-xs text-zinc-500">{{ (file.size / 1024 / 1024).toFixed(2) }} MB</span>
               </li>
             </ul>
           </div>
         </div>
       </UCard>

       <UCard class="border border-white/10 bg-white/5">
         <template #header>
           <h2 class="text-lg font-semibold text-white">Khán giả & mục tiêu</h2>
         </template>

         <div class="grid gap-4 md:grid-cols-2">
           <UTextarea v-model="form.audienceProfile" label="Khán giả" :rows="3" placeholder="Ví dụ: nhân viên sáng tạo, digital nomad, freelancer" />
           <USelect
             v-model="form.objective"
             :items="[
               { label: 'Chuyển đổi', value: 'Conversion' },
               { label: 'Lead', value: 'Lead' },
               { label: 'Traffic', value: 'Traffic' },
               { label: 'Nhận thức', value: 'Awareness' }
             ]"
             label="Mục tiêu"
             value-key="value"
             option-attribute="label"
           />
           <USelect
             v-model="form.channel"
             :items="[
               { label: 'TikTok', value: 'TikTok' },
               { label: 'Reels', value: 'Reels' },
               { label: 'Meta', value: 'Meta' }
             ]"
             label="Kênh"
             value-key="value"
             option-attribute="label"
           />
           <UInput v-model="form.aspectRatio" label="Tỷ lệ khung hình" placeholder="Ví dụ: 9:16" />
           <UInput v-model="form.language" label="Ngôn ngữ" placeholder="Ví dụ: vi" />
           <UInput v-model="form.requiredCta" label="CTA bắt buộc" placeholder="Ví dụ: Mua ngay hôm nay" />
           <UInput v-model="form.creativeReference" label="Tham chiếu sáng tạo" class="md:col-span-2" placeholder="Link video mẫu hoặc ghi chú phong cách" />
           <UInput v-model="form.keyMessage" label="Thông điệp chính" class="md:col-span-2" placeholder="Thông điệp chính của chiến dịch..." />
          </div>
        </UCard>

       <UCard class="border border-white/10 bg-white/5">
         <template #header>
           <h2 class="text-lg font-semibold text-white">Ràng buộc sáng tạo</h2>
         </template>

         <div class="grid gap-4 md:grid-cols-2">
           <UInput v-model="form.maxDurationMs" type="number" label="Thời lượng tối đa (ms)" placeholder="18000" />
           <UTextarea v-model="form.bannedClaims" label="Khẳng định bị cấm" :rows="2" class="md:col-span-2" placeholder="Mỗi claim trên 1 dòng hoặc phân cách bằng dấu phẩy" />
           <UTextarea v-model="form.bannedContent" label="Nội dung bị cấm" :rows="2" class="md:col-span-2" placeholder="Ví dụ: không dùng hiệu ứng quá ồn, không dùng cảnh quá dài ..." />
         </div>
       </UCard>
     </div>

     <aside class="space-y-4">
       <UCard class="border border-white/10 bg-zinc-900/80">
         <template #header>
           <h2 class="text-lg font-semibold text-white">Tóm tắt chiến dịch</h2>
         </template>

         <div class="space-y-3 text-sm text-zinc-300">
           <div>
             <p class="text-zinc-400">Sản phẩm</p>
             <p class="font-medium text-white">{{ form.productName || 'Chưa nhập' }}</p>
           </div>
           <div>
             <p class="text-zinc-400">Kênh</p>
             <p class="font-medium text-white">{{ form.channel }}</p>
           </div>
           <div>
             <p class="text-zinc-400">Mục tiêu</p>
             <p class="font-medium text-white">{{ form.objective }}</p>
           </div>
           <div>
             <p class="text-zinc-400">Thông điệp</p>
             <p class="font-medium text-white">{{ form.keyMessage || 'Chưa nhập' }}</p>
           </div>
           <div class="rounded-2xl border border-indigo-500/30 bg-indigo-500/10 p-3 text-indigo-100">
             <p class="text-xs uppercase tracking-[0.2em] text-indigo-300">Next step</p>
             <p class="mt-2 text-sm">Sau khi submit, hệ thống sẽ tạo storyboard và chờ bạn review.</p>
           </div>
         </div>
       </UCard>
     </aside>
   </div>
  </div>
</template>
