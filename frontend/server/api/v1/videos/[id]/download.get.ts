import { mockVideosByBriefId } from '../../../../utils/mockData'

export default defineEventHandler((event) => {
  const id = getRouterParam(event, 'id') || ''
  const video = (Object.values(mockVideosByBriefId) as Array<any[]>)
    .flat()
    .find((item: any) => item.id === id) as Record<string, any> | undefined

  if (!video) {
    throw createError({ statusCode: 404, statusMessage: 'Video not found' })
  }

  return {
    url: video.downloadUrl || 'https://example.com/videos/demo.mp4',
    filename: `${video.title}.mp4`
  }
})
