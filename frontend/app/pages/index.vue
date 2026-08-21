<script setup lang="ts">
const { fetchApi } = useApi()

const { data: overview, pending } = await useAsyncData('dashboard-overview', () =>
  fetchApi<{ totalVideos: number; successRate: number; avgWatchTime: number; activeCampaigns: number; weeklyTrend: number[]; recentVideos: Array<{ id: string; title: string; channel: string; status: string; pulls: string; watchTime: string }> }>('/dashboard/overview')
)

const summaryCards = computed(() => [
  {
    label: 'Total videos',
    value: overview.value?.totalVideos ?? 0,
    detail: '+18% this month'
  },
  {
    label: 'Success rate',
    value: `${overview.value?.successRate ?? 0}%`,
    detail: 'ROAS > 4.2x'
  },
  {
    label: 'Avg watch time',
    value: `${overview.value?.avgWatchTime ?? 0}s`,
    detail: 'Above benchmark'
  },
  {
    label: 'Active campaigns',
    value: overview.value?.activeCampaigns ?? 0,
    detail: '7 optimized this week'
  }
])

const trendBars = computed(() => overview.value?.weeklyTrend ?? [])
</script>

<template>
  <div class="space-y-8">
    <section class="flex flex-col gap-4 rounded-3xl border border-white/10 bg-gradient-to-br from-indigo-500/15 via-zinc-900 to-zinc-950 p-6 md:flex-row md:items-end md:justify-between">
      <div>
        <p class="text-sm uppercase tracking-[0.24em] text-indigo-300">Overview</p>
        <h1 class="mt-3 text-3xl font-semibold text-white">AI Shorts performance dashboard</h1>
      </div>

      <UButton to="/workspace" color="primary" size="lg">
        Create new campaign
      </UButton>
    </section>

    <div v-if="pending" class="grid gap-4 md:grid-cols-4">
      <USkeleton v-for="index in 4" :key="index" class="h-32 w-full" />
    </div>

    <div v-else class="space-y-8">
      <section class="grid gap-4 md:grid-cols-4">
        <UCard v-for="card in summaryCards" :key="card.label" class="border border-white/10 bg-white/5">
          <div class="space-y-3">
            <p class="text-sm text-zinc-400">{{ card.label }}</p>
            <p class="text-3xl font-semibold text-white">{{ card.value }}</p>
            <p class="text-xs text-emerald-400">{{ card.detail }}</p>
          </div>
        </UCard>
      </section>

      <section class="grid gap-6 lg:grid-cols-[1.6fr_1fr]">
        <UCard class="border border-white/10 bg-white/5">
          <template #header>
            <div class="flex items-center justify-between">
              <h2 class="text-lg font-semibold text-white">Weekly output</h2>
              <span class="text-xs uppercase tracking-[0.2em] text-zinc-400">Last 7 days</span>
            </div>
          </template>

          <div class="mt-6 flex h-44 items-end gap-3">
            <div v-for="(value, index) in trendBars" :key="index" class="flex flex-1 flex-col items-center justify-end gap-2">
              <span class="text-[10px] text-zinc-500">{{ index + 1 }}</span>
              <div
                class="w-full rounded-t-xl bg-gradient-to-t from-indigo-500 to-violet-400"
                :style="{ height: `${value}%` }"
              />
            </div>
          </div>
        </UCard>

        <UCard class="border border-white/10 bg-white/5">
          <template #header>
            <h2 class="text-lg font-semibold text-white">AI notes</h2>
          </template>

          <div class="space-y-4 text-sm text-zinc-300">
            <div class="rounded-2xl border border-emerald-500/30 bg-emerald-500/10 p-3">
              <p class="font-medium text-emerald-300">Hook quality</p>
              <p class="mt-1">Strong 3-second opener with concise offers and product proof.</p>
            </div>
            <div class="rounded-2xl border border-indigo-500/30 bg-indigo-500/10 p-3">
              <p class="font-medium text-indigo-300">CTA performance</p>
              <p class="mt-1">Offer-led CTA drives 28% higher click-through than generic product CTAs.</p>
            </div>
          </div>
        </UCard>
      </section>

      <UCard class="border border-white/10 bg-white/5">
        <template #header>
          <div class="flex items-center justify-between">
            <h2 class="text-lg font-semibold text-white">Recent videos</h2>
            <UButton to="/history" variant="ghost" color="neutral" size="sm">View library</UButton>
          </div>
        </template>

        <div class="space-y-3">
          <div
            v-for="video in overview?.recentVideos ?? []"
            :key="video.id"
            class="flex flex-col gap-3 rounded-2xl border border-white/10 bg-zinc-900/70 p-4 md:flex-row md:items-center md:justify-between"
          >
            <div>
              <p class="text-base font-medium text-white">{{ video.title }}</p>
              <div class="mt-1 flex flex-wrap gap-2 text-xs text-zinc-400">
                <span>{{ video.channel }}</span>
                <span>•</span>
                <span>{{ video.status }}</span>
              </div>
            </div>

            <div class="flex items-center gap-8 text-sm text-zinc-300">
              <div>
                <p class="text-zinc-400">Pulls</p>
                <p class="font-medium text-white">{{ video.pulls }}</p>
              </div>
              <div>
                <p class="text-zinc-400">Watch</p>
                <p class="font-medium text-white">{{ video.watchTime }}</p>
              </div>
            </div>
          </div>
        </div>
      </UCard>
    </div>
  </div>
</template>
