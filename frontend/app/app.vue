<script setup>
const title = 'Nuxt Boilerplate'
const description = 'Enterprise AI Video Intelligence & Auto-Mitigation Workspace'

useHead({
  titleTemplate: '%s — SentraLoop AI',
  meta: [
    { name: 'description', content: description },
    { name: 'viewport', content: 'width=device-width, initial-scale=1' }
  ],
  link: [
    { rel: 'icon', href: '/favicon.ico' }
  ],
  htmlAttrs: {
    lang: 'en'
  }
})

useSeoMeta({
  title,
  description,
  ogTitle: title,
  ogDescription: description,
  ogImage: 'https://ui.nuxt.com/assets/templates/nuxt/starter-light.png',
  twitterCard: 'summary_large_image'
})
</script>

<template>
  <UApp>
    <NuxtLayout>
        <NuxtPage />
    </NuxtLayout>
  </UApp>
</template>
