<script setup lang="ts">
const { isDemoMode } = useApi()

const navItems = [
  { label: 'Overview', to: '/' },
  { label: 'Workspace', to: '/workspace' },
  { label: 'History', to: '/history' }
]
</script>

<template>
  <div class="min-h-screen bg-zinc-950 text-zinc-100">
    <header class="sticky top-0 z-40 border-b border-white/10 bg-zinc-950/80 backdrop-blur-xl">
      <div class="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-3">
        <NuxtLink to="/" class="flex items-center gap-3">
          <div class="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 to-violet-500 text-sm font-bold text-white shadow-lg shadow-indigo-500/30">
            BI
          </div>
          <div>
            <p class="text-sm font-semibold text-white">Beyond Intelligence</p>
            <p class="text-[10px] uppercase tracking-[0.22em] text-zinc-400">AI VIDEO STUDIO</p>
          </div>
        </NuxtLink>

        <nav class="hidden items-center gap-6 md:flex">
          <NuxtLink
            v-for="item in navItems"
            :key="item.to"
            :to="item.to"
            class="text-sm text-zinc-300 transition hover:text-white"
            active-class="text-indigo-300"
          >
            {{ item.label }}
          </NuxtLink>
        </nav>

        <div class="flex items-center gap-3">
          <div class="flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-2.5 py-1.5">
            <span class="text-[10px] font-medium uppercase tracking-[0.2em] text-zinc-400">
              {{ isDemoMode ? 'Demo' : 'Live' }}
            </span>
            <UToggle v-model="isDemoMode" size="sm" />
          </div>

          <UButton to="/workspace" color="primary" variant="solid" class="hidden sm:inline-flex">
            New campaign
          </UButton>
        </div>
      </div>
    </header>

    <main class="mx-auto max-w-7xl px-4 py-8">
      <slot />
    </main>
  </div>
</template>
