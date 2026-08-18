<script setup lang="ts">
interface Props {
  decision: DecisionItem
  loading?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  loading: false
})

const emit = defineEmits<{
  (e: 'approve', id: string): void
  (e: 'reject', id: string): void
  (e: 'inspect-evidence', evidenceId: string): void
}>()

const isSafety = computed(() => props.decision.track === 'safety')
const isApproved = computed(() => props.decision.status === 'approved')
const isRejected = computed(() => props.decision.status === 'rejected')
</script>

<template>
  <div
    class="rounded-xl border bg-elevated/90 transition-all p-4.5 flex flex-col gap-3.5 relative overflow-hidden"
    :class="[
      isSafety
        ? 'border-l-4 border-l-amber-500 border-default shadow-xs'
        : 'border-l-4 border-l-indigo-600 border-default shadow-xs'
    ]"
  >
    <!-- Header: Track Badge & Confidence Score -->
    <div class="flex items-start justify-between gap-3">
      <div class="flex items-center gap-2">
        <UBadge
          :color="isSafety ? 'warning' : 'primary'"
          variant="subtle"
          size="sm"
          class="font-semibold"
        >
          <UIcon :name="isSafety ? 'i-lucide-shield-alert' : 'i-lucide-trending-up'" class="size-3.5 mr-1" />
          {{ isSafety ? 'Safety & Compliance' : 'Growth & CVR Opt' }}
        </UBadge>
        <span class="text-xs text-muted font-mono">#{{ decision.id }}</span>
      </div>

      <!-- AI Confidence Pill -->
      <div class="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-muted/40 border border-muted text-xs">
        <UIcon name="i-lucide-sparkles" class="size-3 text-primary" />
        <span class="text-muted">Độ tin cậy:</span>
        <span class="font-bold text-highlighted font-mono">{{ (decision.confidenceScore * 100).toFixed(1) }}%</span>
      </div>
    </div>

    <!-- Title & Description -->
    <div>
      <h4 class="font-semibold text-highlighted text-sm leading-snug">{{ decision.title }}</h4>
      <p class="text-xs text-muted mt-1 leading-relaxed">{{ decision.description }}</p>
    </div>

    <!-- Impact & Diff Suggestion Area -->
    <div class="rounded-lg bg-muted/30 border border-muted/70 p-3 flex flex-col gap-2">
      <div class="flex items-center gap-1.5 text-xs">
        <UIcon name="i-lucide-zap" class="size-3.5 text-amber-500 shrink-0" />
        <span class="text-muted">Tác động dự kiến:</span>
        <span class="font-semibold text-highlighted">{{ decision.impact }}</span>
      </div>

      <!-- Proposed Mitigation Diff (if available) -->
      <div v-if="decision.diffOriginal || decision.diffProposed" class="mt-1 text-xs grid grid-cols-2 gap-2">
        <div class="p-2 rounded bg-red-500/10 border border-red-500/20 text-red-700 dark:text-red-300">
          <div class="font-semibold text-[10px] uppercase tracking-wider mb-0.5">Hiện tại</div>
          <p class="font-mono text-[11px] truncate">{{ decision.diffOriginal }}</p>
        </div>
        <div class="p-2 rounded bg-emerald-500/10 border border-emerald-500/20 text-emerald-700 dark:text-emerald-300">
          <div class="font-semibold text-[10px] uppercase tracking-wider mb-0.5">AI Đề xuất</div>
          <p class="font-mono text-[11px] truncate">{{ decision.diffProposed }}</p>
        </div>
      </div>
    </div>

    <!-- Actions & Traceability Buttons -->
    <div class="pt-2 border-t border-muted/50 flex items-center justify-between gap-2">
      <UButton
        icon="i-lucide-file-search"
        variant="ghost"
        color="neutral"
        size="xs"
        label="Dẫn chứng AI (Evidence)"
        @click="emit('inspect-evidence', decision.evidenceId)"
      />

      <div class="flex items-center gap-2">
        <!-- Status Indicator when action taken -->
        <UBadge v-if="isApproved" color="success" variant="solid" size="xs">
          <UIcon name="i-lucide-check" class="size-3 mr-1" /> Đã duyệt
        </UBadge>
        <UBadge v-else-if="isRejected" color="neutral" variant="outline" size="xs">
          Đã từ chối
        </UBadge>

        <template v-else>
          <UButton
            color="neutral"
            variant="ghost"
            size="xs"
            label="Từ chối"
            :loading="loading"
            @click="emit('reject', decision.id)"
          />
          <UButton
            :color="isSafety ? 'warning' : 'primary'"
            variant="solid"
            size="xs"
            label="Phê duyệt & Thực thi"
            icon="i-lucide-check"
            :loading="loading"
            @click="emit('approve', decision.id)"
          />
        </template>
      </div>
    </div>
  </div>
</template>