import { mockRenderById } from '../../../utils/mockData'

export default defineEventHandler((event) => {
  const id = getRouterParam(event, 'id') || ''
  const render = mockRenderById[id]

  if (!render) {
    // Tạo fallback mock job nếu ID ngẫu nhiên được gọi
    return {
      status: 'completed',
      video_url: 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4'
    }
  }

  if (render.status === 'processing') {
    return {
      status: 'processing',
      video_url: render.video_url || ''
    }
  }

  if (render.status === 'completed') {
    return {
      status: 'completed',
      video_url: render.video_url || 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4'
    }
  }

  if (render.status === 'failed') {
    return {
      status: 'failed',
      error: {
        code: 'RENDER_FAILED',
        message: 'Lỗi tổng hợp video từ Agent Pod.'
      }
    }
  }

  return {
    status: render.status || 'processing',
    video_url: render.video_url || ''
  }
})

