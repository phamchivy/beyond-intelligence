import { mockRenderById } from '../../../utils/mockData'

export default defineEventHandler(async (event) => {
  const body = await readBody(event)
  const taskId = String(body?.taskId || '')
  const storyboardId = String(body?.storyboardId || '')
  const decision = String(body?.decision || 'approved')
  const feedback = String(body?.feedback || '')
  const renderJobId = `render-${Date.now()}`

  mockRenderById[renderJobId] = {
    id: renderJobId,
    briefId: storyboardId || taskId || 'brief-001',
    status: 'processing',
    progress: 15,
    currentStep: decision === 'revised' ? 'Đang sửa storyboard theo phản hồi.' : 'Đang render video theo storyboard đã duyệt.',
    updatedAt: new Date().toISOString(),
    video_url: ''
  }

  return {
    status: decision === 'rejected' ? 'rejected' : 'accepted',
    render_job_id: renderJobId,
    message: feedback || 'Storyboard accepted and render job created.'
  }
})
