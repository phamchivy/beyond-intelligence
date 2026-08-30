<script setup lang="ts">
const { fetchApi } = useApi()

const statusFilter = ref('all')
const { data } = await useLazyAsyncData('brief-list', () => fetchApi<{ items: Array<Record<string, any>> }>('/briefs?page=1'))

const filteredItems = computed(() => {
  const items = data.value?.items ?? []

  if (statusFilter.value === 'all') {
    return items
  }

  return items.filter(item => item.status === statusFilter.value)
})

const statusOptions = [
  { label: 'Tất cả', value: 'all' },
  { label: 'Bản nháp', value: 'draft' },
  { label: 'Đang suy luận', value: 'reasoning' },
  { label: 'Chờ phê duyệt', value: 'awaiting_approval' },
  { label: 'Đang render', value: 'rendering' },
  { label: 'Hoàn tất', value: 'done' },
  { label: 'Thất bại', value: 'failed' }
]

const statusColor = (status: string): 'error' | 'primary' | 'secondary' | 'success' | 'info' | 'warning' | 'neutral' | undefined => {
  const map: Record<string, 'error' | 'primary' | 'secondary' | 'success' | 'info' | 'warning' | 'neutral'> = {
    draft: 'neutral',
    reasoning: 'info',
    awaiting_approval: 'warning',
    rendering: 'primary',
    done: 'success',
    failed: 'error'
  }

  return map[status] || 'neutral'
}

const statusLabel = (status: string) => {
  const map: Record<string, string> = {
    draft: 'Bản nháp',
    reasoning: 'Đang suy luận',
    awaiting_approval: 'Chờ phê duyệt',
    rendering: 'Đang render',
    done: 'Hoàn tất',
    failed: 'Thất bại'
  }

  return map[status] || status
}
</script>

<template>
  <div class="space-y-6">
    <section class="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
      <div>
        <p class="text-sm uppercase tracking-[0.22em] text-indigo-300">Thư viện brief</p>
        <h1 class="mt-2 text-3xl font-semibold text-white">Brief chiến dịch</h1>
      </div>

      <UButton to="/briefs/new" color="primary">Tạo brief mới</UButton>
    </section>

    <UCard class="border border-white/10 bg-white/5">
      <div class="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div class="flex-1">
          <UInput placeholder="Tìm brief hoặc sản phẩm" icon="i-lucide-search" />
        </div>

        <USelect v-model="statusFilter" :items="statusOptions" value-key="value" option-attribute="label" />
      </div>
    </UCard>

    <div class="grid gap-4">
      <UCard v-for="brief in filteredItems" :key="brief.id" class="border border-white/10 bg-zinc-900/70">
        <div class="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div class="space-y-2">
            <div class="flex items-center gap-2">
              <h2 class="text-xl font-semibold text-white">{{ brief.title }}</h2>
              <UBadge :color="statusColor(brief.status)" variant="soft">{{ statusLabel(brief.status) }}</UBadge>
            </div>

            <div class="flex flex-wrap gap-3 text-sm text-zinc-400">
              <span>{{ brief.productName }}</span>
              <span>•</span>
              <span>{{ brief.objective }}</span>
              <span>•</span>
              <span>{{ brief.channel }}</span>
              <span>•</span>
              <span>{{ brief.duration }}</span>
            </div>
          </div>

          <div class="flex items-center gap-2">
            <UButton :to="`/briefs/${brief.id}`" variant="outline">Xem</UButton>
            <UButton :to="`/briefs/${brief.id}/storyboard`" color="primary">Storyboard</UButton>
          </div>
        </div>
      </UCard>
    </div>
  </div>
</template>
