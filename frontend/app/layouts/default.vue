<script setup lang="ts">
const links = [
  { label: 'Home', to: '/' },
  { label: 'Demo', to: '/demo' },
  { label: 'Dashboard', to: '/dashboard' },
  { label: 'Decision', to: '/decision' }
]
</script>

<template>
  <div class="min-h-screen bg-[radial-gradient(circle_at_top_left,rgba(0,209,130,0.18),transparent_40%),linear-gradient(135deg,rgba(255,255,255,0.95),rgba(243,250,247,0.9))] text-gray-900 transition-colors duration-300 dark:bg-[radial-gradient(circle_at_top_left,_rgba(0,209,130,0.2),_transparent_40%),linear-gradient(135deg,rgba(6,15,24,0.98),rgba(3,10,18,0.95))] dark:text-white">
    <UHeader>
      <template #title>
        <div class="flex items-center gap-2">
          <UIcon name="i-lucide-sparkles" class="text-primary" />
          <span class="font-semibold tracking-tight">AI Hackathon Starter</span>
        </div>
      </template>

      <nav class="hidden items-center gap-6 text-sm font-medium md:flex">
        <NuxtLink v-for="item in links" :key="item.to" :to="item.to" class="transition-colors hover:text-primary">
          {{ item.label }}
        </NuxtLink>
      </nav>

      <template #right>
        <UColorModeButton />
        <UButton label="Open demo" to="/demo" />
      </template>

      <template #body>
        <nav class="flex flex-col gap-3 text-sm font-medium">
          <NuxtLink v-for="item in links" :key="item.to" :to="item.to" class="transition-colors hover:text-primary">
            {{ item.label }}
          </NuxtLink>
        </nav>
      </template>
    </UHeader>

    <UMain>
      <UContainer class="py-6 md:py-10">
        <slot />
      </UContainer>
    </UMain>

    <UFooter>
      <template #left>
        <p class="text-sm text-muted">
          Built with Nuxt UI • © {{ new Date().getFullYear() }}
        </p>
      </template>

      <template #right>
        <UButton
          to="https://github.com/nuxt-ui-templates/starter"
          target="_blank"
          icon="i-simple-icons-github"
          aria-label="GitHub"
          color="neutral"
          variant="ghost"
        />
      </template>
    </UFooter>
  </div>
</template>