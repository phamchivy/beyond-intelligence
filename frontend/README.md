# AI Hackathon Starter

Thư mục này chứa mã nguồn **Frontend Service** thuộc dự án **Beyond Intelligence**, hiện đang có:

- landing page đơn giản
- trang demo workspace với chỉ số phân tích mock và panel AI trợ lí
- trang dashboard với dữ liệu mock
- cấu trúc Nuxt UI + Tailwind sạch cho việc tái sử dụng

## Bắt đầu nhanh

```bash
npm install
npm dev
```

Entry: http://localhost:3000 

## Cấu trúc thư mục

- `app/pages/index.vue` -- landing page
- `app/pages/demo.vue` -- demo workspace
- `app/pages/dashboard.vue` -- demo dashboard
- `app/components/ui/BaseChart.vue` và `app/components/ui/AiCopilot.vue` -- demo widgets
- `app/composables/useApi.ts` và `app/composables/useEngineApi.ts` -- api caller

## Build và preview

```bash
npm build
npm preview
```

