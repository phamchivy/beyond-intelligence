<script setup lang="ts">
// State quản lý cờ Demo Mode (Mock API vs Live .NET 8 Backend)
const isDemoMode = useState<boolean>('isDemoMode', () => true)
const colorMode = useColorMode()

const toggleColorMode = () => {
  colorMode.preference = colorMode.value === 'dark' ? 'light' : 'dark'
}
</script>

<template>
  <div class="min-h-screen bg-surface text-default flex flex-col font-sans antialiased">
    <!-- Top Enterprise Header -->
    <header class="h-16 border-b border-muted bg-elevated/80 backdrop-blur-md sticky top-0 z-40 px-4 sm:px-6 flex items-center justify-between">
      <!-- Brand Logo -->
      <div class="flex items-center gap-6">
        <NuxtLink to="/" class="flex items-center gap-2.5 focus:outline-none">
          <div class="size-8 rounded-lg bg-indigo-600 flex items-center justify-center text-white shadow-xs">
            <UIcon name="i-lucide-sparkles" class="size-5" />
          </div>
          <div class="flex flex-col">
            <span class="font-bold text-highlighted text-base leading-tight tracking-tight">SentraLoop AI</span>
            <span class="text-[10px] text-muted font-mono tracking-wider">VIDEO INTELLIGENCE</span>
          </div>
        </NuxtLink>

        <!-- Navigation Links -->
        <nav class="hidden md:flex items-center gap-1">
          <UButton
            to="/"
            variant="ghost"
            color="neutral"
            size="sm"
            label="Intelligence Workspace"
            icon="i-lucide-layout-dashboard"
          />
          <UButton
            to="/scan"
            variant="ghost"
            color="neutral"
            size="sm"
            label="Scanning Studio"
            icon="i-lucide-scan-line"
          />
        </nav>
      </div>

      <!-- Right Actions: Demo Mode Toggle, Channel, Theme -->
      <div class="flex items-center gap-3">
        <!-- Demo-Proof Resilience Switcher -->
        <div class="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-muted/40 border border-muted">
          <UIcon
            :name="isDemoMode ? 'i-lucide-shield-check' : 'i-lucide-server'"
            :class="isDemoMode ? 'text-amber-500' : 'text-emerald-500'"
            class="size-4"
          />
          <span class="text-xs font-medium text-highlighted">
            {{ isDemoMode ? 'Mock API (Demo Mode)' : '.NET 8 Live API' }}
          </span>
          <USwitch v-model="isDemoMode" size="sm" />
        </div>

        <UButton
          :icon="colorMode.value === 'dark' ? 'i-lucide-moon' : 'i-lucide-sun'"
          color="neutral"
          variant="ghost"
          size="sm"
          @click="toggleColorMode"
        />

        <div class="size-8 rounded-full bg-primary/10 border border-primary/20 flex items-center justify-center text-primary font-bold text-xs">
          SL
        </div>
      </div>
    </header>

    <!-- Main Workspace Content -->
    <main class="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 lg:p-8">
      <slot />
    </main>
  </div>
</template>