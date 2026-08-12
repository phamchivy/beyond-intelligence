<script setup lang="ts">
const { data: health } = await useFetch('/api/health')
const { data: insights } = await useFetch('/api/demo')

const chartOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  xAxis: {
    type: 'category',
    axisLine: { show: false },
    data: insights.value?.trend?.labels ?? []
  },
  yAxis: { type: 'value', show: false },
  grid: { left: 12, right: 12, top: 16, bottom: 16 },
  series: [{
    type: 'bar',
    data: insights.value?.trend?.values ?? [],
    itemStyle: { color: 'var(--ui-primary)' }
  }]
}))
</script>

<template>
  <div class="space-y-8">
    <UPageHero
      title="Demo workspace"
      description="Use this page as your interactive prototype shell during the hackathon."
      :links="[{ label: 'Back home', to: '/', color: 'neutral', variant: 'subtle' }]"
    />

    <div class="grid gap-4 lg:grid-cols-[1.2fr_0.8fr]">
      <UCard>
        <template #header>
          <div class="flex items-center justify-between">
            <div>
              <h2 class="text-lg font-semibold">Live API snapshot</h2>
              <p class="text-sm text-muted">Health and event metrics from the starter API.</p>
            </div>
            <UBadge color="success" variant="subtle">Connected</UBadge>
          </div>
        </template>

        <div class="grid gap-3 md:grid-cols-2">
          <div class="rounded-2xl border border-default bg-default/70 p-4">
            <p class="text-sm text-muted">Service status</p>
            <p class="mt-2 text-2xl font-semibold">{{ health?.status ?? 'loading' }}</p>
            <p class="mt-1 text-sm text-muted">{{ health?.service ?? 'AI Hackathon Starter' }}</p>
          </div>
          <div class="rounded-2xl border border-default bg-default/70 p-4">
            <p class="text-sm text-muted">Signal count</p>
            <p class="mt-2 text-2xl font-semibold">{{ insights?.metrics?.at(0)?.value ?? 0 }}</p>
            <p class="mt-1 text-sm text-muted">Updated every request</p>
          </div>
        </div>
      </UCard>

      <UCard>
        <template #header>
          <div>
            <h2 class="text-lg font-semibold">Next actions</h2>
            <p class="text-sm text-muted">Swap mock data with your real backend or AI workflow.</p>
          </div>
        </template>

        <ul class="space-y-3 text-sm text-muted">
          <li v-for="item in insights?.nextSteps ?? []" :key="item" class="flex items-start gap-2">
            <UIcon name="i-lucide-check-circle-2" class="mt-0.5 text-primary" />
            <span>{{ item }}</span>
          </li>
        </ul>
      </UCard>
    </div>

    <div class="grid gap-4 lg:grid-cols-2">
      <ClientOnly>
        <UiBaseChart title="Weekly signals" :option="chartOption" />
      </ClientOnly>

      <div class="space-y-4">
        <UCard>
          <template #header>
            <div>
              <h2 class="text-lg font-semibold">Suggested prompts</h2>
              <p class="text-sm text-muted">Use these as placeholders for your own AI experience.</p>
            </div>
          </template>

          <div class="space-y-2">
            <UBadge v-for="prompt in insights?.prompts ?? []" :key="prompt" color="neutral" variant="subtle">
              {{ prompt }}
            </UBadge>
          </div>
        </UCard>

        <UCard>
          <template #header>
            <div>
              <h2 class="text-lg font-semibold">Deployment checklist</h2>
              <p class="text-sm text-muted">A quick reminder before you pitch.</p>
            </div>
          </template>

          <ul class="space-y-2 text-sm text-muted">
            <li class="flex items-start gap-2"><UIcon name="i-lucide-circle-check-big" class="mt-0.5 text-primary" /><span>Replace mock content with your real product story.</span></li>
            <li class="flex items-start gap-2"><UIcon name="i-lucide-circle-check-big" class="mt-0.5 text-primary" /><span>Connect your AI model or service endpoint.</span></li>
            <li class="flex items-start gap-2"><UIcon name="i-lucide-circle-check-big" class="mt-0.5 text-primary" /><span>Prepare a short demo script and rollout plan.</span></li>
          </ul>
        </UCard>
      </div>
    </div>
    <div>
      <UiAiCopilot />
    </div>
  </div>
</template>
