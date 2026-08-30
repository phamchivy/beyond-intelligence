<script setup lang="ts">
const { isDemoMode } = useApi()
const colorMode = useColorMode()

const isDark = computed({
  get: () => colorMode.value === 'dark',
  set: (val: boolean) => {
    colorMode.preference = val ? 'dark' : 'light'
  }
})

const toggleTheme = () => {
  colorMode.preference = colorMode.value === 'dark' ? 'light' : 'dark'
}

const navItems = [
  { label: 'Tổng quan', to: '/' },
  { label: 'Workspace AI', to: '/workspace', badge: 'Flagship' },
  { label: 'Chiến dịch / Briefs', to: '/briefs' },
  { label: 'Lịch sử Video', to: '/history' }
]
</script>

<template>
  <div class="min-h-screen bg-slate-50 text-slate-900 dark:bg-zinc-950 dark:text-zinc-100 transition-colors">
    <header class="sticky top-0 z-40 border-b border-slate-200 bg-white/80 backdrop-blur-xl dark:border-zinc-800 dark:bg-zinc-950/80">
      <div class="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-3">
        <!-- Logo -->
        <NuxtLink to="/workspace" class="flex items-center gap-3">
          <div class="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-600 via-indigo-500 to-violet-600 text-sm font-bold text-white shadow-lg shadow-indigo-500/25">
            BI
          </div>
          <div>
            <p class="text-sm font-bold tracking-tight text-slate-900 dark:text-white">Beyond Intelligence</p>
            <p class="text-[10px] font-semibold uppercase tracking-[0.2em] text-indigo-600 dark:text-indigo-400">AI VIDEO ENGINE</p>
          </div>
        </NuxtLink>

        <!-- Navigation Links -->
        <nav class="hidden items-center gap-6 md:flex">
          <NuxtLink
            v-for="item in navItems"
            :key="item.to"
            :to="item.to"
            class="flex items-center gap-1.5 text-xs font-semibold text-slate-600 transition hover:text-indigo-600 dark:text-zinc-400 dark:hover:text-white"
            active-class="text-indigo-600 dark:text-indigo-400 font-bold"
          >
            <span>{{ item.label }}</span>
            <span v-if="item.badge" class="rounded bg-indigo-500/10 px-1.5 py-0.5 text-[9px] font-bold text-indigo-600 dark:bg-indigo-500/20 dark:text-indigo-400">
              {{ item.badge }}
            </span>
          </NuxtLink>
        </nav>

        <!-- Right Controls -->
        <div class="flex items-center gap-3">
          <!-- Theme Toggle (Light / Dark) -->
          <ClientOnly>
            <UButton
              :icon="isDark ? 'lucide:moon' : 'lucide:sun'"
              color="neutral"
              variant="ghost"
              size="sm"
              :aria-label="isDark ? 'Chuyển sang chế độ sáng' : 'Chuyển sang chế độ tối'"
              @click="toggleTheme"
            />
          </ClientOnly>

          <!-- Demo Mode Switcher -->
          <div class="flex items-center gap-2 rounded-full border border-slate-200 bg-slate-100 px-3 py-1 dark:border-zinc-800 dark:bg-zinc-900">
            <span class="text-[10px] font-bold uppercase tracking-[0.18em]" :class="isDemoMode ? 'text-indigo-600 dark:text-indigo-400' : 'text-slate-500'">
              {{ isDemoMode ? 'Demo Mock' : 'Live Pods' }}
            </span>
            <USwitch v-model="isDemoMode" size="xs" />
          </div>

          <UButton to="/workspace" color="primary" variant="solid" size="sm" icon="lucide:sparkles">
            Tạo Video Ngay
          </UButton>
        </div>
      </div>
    </header>


    <main class="mx-auto max-w-7xl px-4 py-6 sm:px-6">
      <slot />
    </main>
  </div>
</template>

