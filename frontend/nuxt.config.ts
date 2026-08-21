// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  runtimeConfig: {
    public: {
      appName: process.env.NUXT_PUBLIC_APP_NAME || 'Beyond Intelligence',
      apiBase: process.env.NUXT_PUBLIC_API_BASE || 'http://localhost:3001/api/v1',
      demoMode: !process.env.NUXT_PUBLIC_DEMO_MODE ? true : ['true', '1', 'yes'].includes((process.env.NUXT_PUBLIC_DEMO_MODE || '').toLowerCase())
    }
  },
  modules: [
    '@nuxt/eslint',
    '@nuxt/ui',
    '@nuxt/icon'
  ],
  devtools: {
    enabled: true
  },  
  icon: {
    clientBundle: {
      scan: true,
    }
  },
  css: ['~/assets/css/main.css'],
  colorMode: {
    preference: 'dark', 
    fallback: 'dark',
    classSuffix: ''
  },
  routeRules: {
    '/': { prerender: true }
  },

  compatibilityDate: '2026-06-30',

  eslint: {
    config: {
      stylistic: {
        commaDangle: 'never',
        braceStyle: '1tbs'
      }
    }
  }
})
