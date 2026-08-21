export default defineEventHandler(async (event) => {
  const body = await readBody(event)

  return {
    ok: true,
    jobId: 'job-demo-4821',
    status: 'rendered',
    productName: body?.productName || 'Aether Pro',
    generatedAt: new Date().toISOString(),
    steps: [
      'Đang phân tích USP sản phẩm...',
      'Đang viết kịch bản Hook 3s...',
      'Đang xử lý hình ảnh và khớp âm thanh...',
      'Đang render video 9:16 và tối ưu CTA...'
    ],
    preview: {
      title: 'Aether Pro — Launch Demo',
      caption: 'Độ mỏng tối ưu. Pin bền bỉ. Năng suất không ngừng.',
      cta: body?.cta || 'Tận dụng ưu đãi 20% hôm nay'
    }
  }
})
