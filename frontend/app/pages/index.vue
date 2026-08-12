<script setup lang="ts">
const features = [
  {
    title: 'Fast UI scaffolding',
    description: 'Landing page, demo workspace, and reusable cards are ready so you can focus on your product idea.',
    icon: 'i-lucide-layout-template'
  },
  {
    title: 'API starter routes',
    description: 'Health checks and mock analytics endpoints are already wired up for quick integration.',
    icon: 'i-lucide-route'
  },
  {
    title: 'AI UX shell',
    description: 'Drop in your own model or workflow behind the built-in assistant preview and analytics chart.',
    icon: 'i-lucide-sparkles'
  }
]

const workflow = [
  {
    title: 'Describe your idea',
    description: 'Swap the sample copy for your own product story and value proposition.'
  },
  {
    title: 'Connect your data',
    description: 'Use the demo API routes as a template for your real backend or AI pipeline.'
  },
  {
    title: 'Launch the prototype',
    description: 'Share the landing page and demo workspace with judges, mentors, or early testers.'
  }
]

const stack = [
  {
    title: 'Nuxt 4',
    description: 'Modern SSR-first framework with file-based routing and excellent DX.'
  },
  {
    title: 'Nuxt UI',
    description: 'Accessible and customizable components for dashboards, cards, and layouts.'
  },
  {
    title: 'API-ready',
    description: 'Server routes are built in so your prototype can quickly talk to a backend.'
  }
]

const heroLinks = [
  { label: 'Open demo', to: '/demo', icon: 'i-lucide-play' },
  { label: 'Explore stack', to: '#features', color: 'neutral' as const, variant: 'subtle' as const, trailingIcon: 'i-lucide-arrow-right' }
]
</script>

<template>
  <div class="space-y-14">
    <UPageHero
      headline="AI hackathon boilerplate"
      title="Ship your AI product in days, not weeks"
      description="A polished Nuxt 4 starter with a landing page, demo workspace, reusable UI blocks, and API routes ready for your next prototype."
      :links="heroLinks"
      orientation="horizontal"
    >
      <div class="rounded-3xl border border-muted/60 bg-elevated/80 p-4 shadow-2xl shadow-primary/10">
        <div class="rounded-2xl border border-default bg-default/70 p-4 space-y-4">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-sm font-semibold text-primary">Product sprint board</p>
              <p class="text-sm text-muted">Designed for fast ideation, demos, and iteration.</p>
            </div>
            <UBadge color="success" variant="subtle">Live demo ready</UBadge>
          </div>

          <div class="grid gap-3 sm:grid-cols-2">
            <div class="rounded-2xl border border-primary/20 bg-primary/10 p-3">
              <p class="text-2xl font-semibold text-primary">4x</p>
              <p class="text-sm text-muted">Faster setup for landing + dashboard</p>
            </div>
            <div class="rounded-2xl border border-success/20 bg-success/10 p-3">
              <p class="text-2xl font-semibold text-success">24/7</p>
              <p class="text-sm text-muted">API skeletons and AI assistant preview</p>
            </div>
          </div>

          <div class="rounded-2xl border border-default p-3">
            <div class="flex items-center gap-2 text-sm font-medium">
              <UIcon name="i-lucide-sparkles" class="text-primary" />
              <span>Mock analytics and AI assistant shell included</span>
            </div>
          </div>
        </div>
      </div>
    </UPageHero>

    <UPageSection
      id="features"
      headline="What you get"
      title="Everything you need to go from idea to prototype fast"
      description="This starter removes the boilerplate so your team can focus on product value, not setup."
      :features="features"
    />

    <UPageSection
      id="workflow"
      headline="Fast workflow"
      title="Three steps to your first demo"
      description="Use the same structure for a hackathon pitch, an internal prototype, or a first customer preview."
    >
      <div class="grid gap-4 md:grid-cols-3">
        <UCard v-for="(item, index) in workflow" :key="item.title" class="h-full">
          <div class="flex items-center gap-3">
            <div class="flex h-10 w-10 items-center justify-center rounded-full bg-primary/10 text-sm font-semibold text-primary">
              {{ index + 1 }}
            </div>
            <h3 class="font-semibold">{{ item.title }}</h3>
          </div>
          <p class="mt-3 text-sm text-muted">{{ item.description }}</p>
        </UCard>
      </div>
    </UPageSection>

    <UPageSection
      headline="Starter stack"
      title="Modern stack that removes setup friction"
      description="Nuxt 4, Nuxt UI, and ready-made API routes keep the experience consistent from design to deployment."
    >
      <div class="grid gap-4 md:grid-cols-3">
        <UCard v-for="item in stack" :key="item.title" class="h-full">
          <h3 class="font-semibold">{{ item.title }}</h3>
          <p class="mt-2 text-sm text-muted">{{ item.description }}</p>
        </UCard>
      </div>
    </UPageSection>

    <UPageCTA
      title="Ready to build?"
      description="Clone the repo, customize the copy, and launch your first AI hackathon prototype in minutes."
      :links="[
        { label: 'Open demo', to: '/demo', icon: 'i-lucide-play' },
        { label: 'View starter API', to: '/', color: 'neutral' as const, variant: 'subtle' as const, trailingIcon: 'i-lucide-arrow-right' }
      ]"
    />
  </div>
</template>