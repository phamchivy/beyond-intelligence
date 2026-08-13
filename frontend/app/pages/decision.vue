<script setup lang="ts">
const route = useRoute()
const decisionId = route.params.id as string

const { getDecision, executeWorkflow } = useEngineApi()
const toast = useToast() // Toast Notification của Nuxt UI [cite: 308]

// 1. Lấy dữ liệu Quyết định từ Backend FastEndpoints
const { data: decision, pending, refresh } = await getDecision(decisionId)
const isExecuting = ref(false)

// 2. Gọi API Phê duyệt Workflow (ExecuteWorkflowEndpoint)
const handleApprove = async (approved: boolean) => {
  isExecuting.value = true
  try {
    const { data, error } = await executeWorkflow({
      decisionId,
      approved,
      comment: approved ? 'Đã phê duyệt qua Workspace UI' : 'Từ chối'
    })

    if (error.value) throw error.value

    toast.add({
      title: approved ? 'Thành công' : 'Đã từ chối',
      description: data.value?.message || 'Workflow đã được xử lý',
      color: approved ? 'success' : 'error'
    })

    refresh() // Refresh lại dữ liệu
  } catch (err) {
    toast.add({
      title: 'Lỗi xử lý',
      description: 'Không thể kết nối Backend Engine',
      color: 'error'
    })
  } finally {
    isExecuting.value = false
  }
}
</script>

<template>
  <div class="p-6 space-y-6">
    <USkeleton v-if="pending" class="h-48 w-full rounded-xl" />

    <UCard v-else-if="decision" class="rounded-xl border border-gray-200 dark:border-gray-800">
      <template #header>
        <div class="flex items-center justify-between">
          <h2 class="text-xl font-bold">{{ decision.title }}</h2>
          <UBadge :color="decision.confidence > 0.8 ? 'success' : 'warning'" variant="soft">
            Độ tin cậy AI: {{ (decision.confidence * 100).toFixed(0) }}%
          </UBadge>
        </div>
      </template>

      <div class="space-y-4">
        <h3 class="font-semibold text-sm text-gray-500">BẰNG CHỨNG & DỮ LIỆU AI (EVIDENCE):</h3>
        <ul class="list-disc pl-5 space-y-1 text-sm">
          <li v-for="(ev, idx) in decision.evidences" :key="idx">{{ ev }}</li>
        </ul>

        <div class="p-3 bg-indigo-50 dark:bg-indigo-950/40 rounded-lg text-sm text-indigo-600 dark:text-indigo-400">
          <strong>Hành động đề xuất:</strong> {{ decision.recommendation }}
        </div>
      </div>

      <template #footer>
        <div class="flex justify-end gap-3">
          <UButton
            color="error"
            variant="soft"
            :loading="isExecuting"
            @click="handleApprove(false)"
          >
            Từ chối
          </UButton>
          <UButton
            color="primary"
            variant="solid"
            :loading="isExecuting"
            @click="handleApprove(true)"
          >
            Phê duyệt & Kích hoạt Action
          </UButton>
        </div>
      </template>
    </UCard>
  </div>
</template>