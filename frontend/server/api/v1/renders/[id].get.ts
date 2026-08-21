import { mockRenderById } from '../../../utils/mockData'

export default defineEventHandler((event) => {
  const id = getRouterParam(event, 'id') || ''
  const render = mockRenderById[id]

  if (!render) {
    throw createError({ statusCode: 404, statusMessage: 'Render status not found' })
  }

  if (render.status === 'processing' && !render.video_url) {
    return {
      status: 'processing',
      video_url: ''
    }
  }

  if (render.status === 'completed') {
    return {
      status: 'completed',
      video_url: render.video_url || 'https://interactive-examples.mdn.mozilla.net/media/cc0-videos/flower.mp4'
    }
  }

  if (render.status === 'failed') {
    return {
      status: 'failed',
      video_url: ''
    }
  }

  return {
    status: render.status || 'processing',
    video_url: render.video_url || ''
  }
})
