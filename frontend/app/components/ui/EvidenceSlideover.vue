<script setup lang="ts">
interface Props {
  open: boolean
  evidence: EvidenceDetails | null
  loading?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  loading: false
})

const emit = defineEmits<{
  (e: 'update:open', value: boolean): void
  (e: 'apply'): void
}>()
</script>

<template>
  <USlideover
    :open="open"
    title="Dấu vết Dữ liệu & Dẫn chứng AI"
    description="Truy xuất nguồn gốc quyết định từ Platform Policy & Dữ liệu Lakehouse"
    @update:open="emit('update:open', $event)"
  >
    <template #body>
      <div v-if="loading || !evidence" class="flex flex-col gap-4 p-2">
        <USkeleton class="h-24 w-full rounded-xl" />
        <USkeleton class="h-36 w-full rounded-xl" />
        <USkeleton class="h-28 w-full rounded-xl" />
      </div>

      <div v-else class="flex flex-col gap-5 py-2">
        <!-- Policy Violation Notice -->
        <UAlert
          color="warning"
          variant="subtle"
          icon="i-lucide-book-open-check"
          :title="`Căn cứ Quy định: ${evidence.platform}`"
          :description="evidence.policyTitle"
        >
          <template #footer>
            <div class="mt-2 text-xs font-mono p-2 rounded bg-amber-500/10 border border-amber-500/20 text-amber-900 dark:text-amber-200">
              Điều khoản: {{ evidence.policyRef }}
              <div class="mt-1 font-sans italic">"{{ evidence.policyExcerpt }}"</div>
            </div>
          </template>
        </UAlert>

        <!-- Lakehouse Metric Baseline Card -->
        <div class="rounded-xl border border-default p-4 bg-muted/20 flex flex-col gap-3">
          <div class="flex items-center justify-between">
            <span class="text-xs font-semibold text-highlighted uppercase tracking-wider">
              Phân tích Tăng trưởng Lakehouse
            </span>
            <UBadge color="primary" variant="subtle" size="xs">
              {{ evidence.lakehouseMetric.sampleSize }} mẫu A/B
            </UBadge>
          </div>

          <div class="grid grid-cols-2 gap-3 mt-1">
            <div class="p-3 rounded-lg bg-elevated border border-muted">
              <span class="text-xs text-muted">Baseline hiện tại</span>
              <div class="text-lg font-bold font-mono text-highlighted mt-0.5">
                {{ evidence.lakehouseMetric.baseline }}{{ evidence.lakehouseMetric.unit }}
              </div>
            </div>
            <div class="p-3 rounded-lg bg-indigo-500/10 border border-indigo-500/20">
              <span class="text-xs text-indigo-600 dark:text-indigo-400 font-medium">Dự phóng sau tối ưu</span>
              <div class="text-lg font-bold font-mono text-indigo-600 dark:text-indigo-400 mt-0.5">
                +{{ evidence.lakehouseMetric.projected }}{{ evidence.lakehouseMetric.unit }}
              </div>
            </div>
          </div>
        </div>

        <!-- AI Agent Rationale Explainability -->
        <div class="flex flex-col gap-2">
          <span class="text-xs font-semibold text-highlighted uppercase tracking-wider">
            Lý luận của AI Mitigation Agent
          </span>
          <div class="text-xs text-muted leading-relaxed p-3.5 rounded-xl bg-elevated border border-default">
            {{ evidence.agentRationale }}
          </div>
        </div>

        <!-- Confidence Factor Breakdown -->
        <div class="flex flex-col gap-2">
          <span class="text-xs font-semibold text-highlighted uppercase tracking-wider">
            Thành phần Điểm số Tin cậy
          </span>
          <div class="flex flex-col gap-2.5">
            <div
              v-for="factor in evidence.confidenceFactors"
              :key="factor.factor"
              class="flex items-center justify-between text-xs"
            >
              <span class="text-muted">{{ factor.factor }}</span>
              <span class="font-mono font-bold text-highlighted">{{ (factor.score * 100).toFixed(0) }}%</span>
            </div>
          </div>
        </div>
      </div>
    </template>

    <template #footer>
      <div class="w-full flex items-center justify-end gap-2">
        <UButton
          color="neutral"
          variant="ghost"
          label="Đóng"
          @click="emit('update:open', false)"
        />
        <UButton
          color="primary"
          variant="solid"
          label="Đồng ý Đề xuất này"
          icon="i-lucide-check-circle"
          @click="emit('apply')"
        />
      </div>
    </template>
  </USlideover>
</template>