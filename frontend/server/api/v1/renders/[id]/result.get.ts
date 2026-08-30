import { mockVideosByBriefId, mockRenderById } from '../../../../utils/mockData'

export default defineEventHandler((event) => {
  const id = getRouterParam(event, 'id') || ''
  const render = mockRenderById[id]

  if (!render) {
    throw createError({ statusCode: 404, statusMessage: 'Render result not found' })
  }

  const videos = mockVideosByBriefId[render.briefId] || []
  const video = videos.find((item: any) => item.status === 'done') || videos[0]

  return {
    id: video?.id || 'video-fallback',
    title: video?.title || 'Generated video',
    duration: video?.duration || '18s',
    ratio: video?.ratio || '9:16',
    platform: video?.platform || 'Reels',
    qa: video?.qa || { ratioMatch: true, durationMatch: true, assetVisibleRatio: 91 },
    createdAt: new Date().toISOString(),
    previewUrl: video?.previewUrl || 'https://images.unsplash.com/photo-1496181133206-80ce9b88a853',
    downloadUrl: video?.downloadUrl || 'https://example.com/videos/demo.mp4'
  }
})
