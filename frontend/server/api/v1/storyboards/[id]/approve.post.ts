import { mockRenderById } from '../../../../utils/mockData'

export default defineEventHandler((event) => {
  const id = getRouterParam(event, 'id') || ''
  const renderId = `render-${String(Object.keys(mockRenderById).length + 1).padStart(3, '0')}`

  mockRenderById[renderId] = {
    id: renderId,
    briefId: id,
    status: 'processing',
    progress: 12,
    currentStep: 'Render job đã được nhận và đang xếp hàng',
    updatedAt: new Date().toISOString(),
    video_url: ''
  }

  return {
    status: 'accepted',
    render_job_id: renderId,
    redirectUrl: `/renders/${renderId}`
  }
})
