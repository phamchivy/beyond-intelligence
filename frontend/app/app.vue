<script setup>
const title = 'Beyond Intelligence'
const description = 'Bảng điều khiển tạo video quảng cáo AI cho storytelling sản phẩm, render và phân tích chiến dịch.'

useHead({
  titleTemplate: '%s',
  meta: [
    { name: 'description', content: description },
    { name: 'viewport', content: 'width=device-width, initial-scale=1' }
  ],
  link: [
    { rel: 'icon', href: '/favicon.ico' }
  ],
  htmlAttrs: {
    lang: 'vi'
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
