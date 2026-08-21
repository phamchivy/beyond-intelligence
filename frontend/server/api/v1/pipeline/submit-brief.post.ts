import { mockPipelineTasks } from '../../../utils/mockData'

export default defineEventHandler(async (event) => {
  const formData = await readMultipartFormData(event)
  const productInfoJson = formData?.find(item => item.name === 'productInfoJson')?.data?.toString() || '{}'
  const targetAudienceJson = formData?.find(item => item.name === 'targetAudienceJson')?.data?.toString() || '{}'
  const adObjective = formData?.find(item => item.name === 'adObjective')?.data?.toString() || 'Conversion'
  const keyMessage = formData?.find(item => item.name === 'keyMessage')?.data?.toString() || 'Key message'
  const channel = formData?.find(item => item.name === 'channel')?.data?.toString() || 'Reels'
  const storyboardText = [
    `Hook: ${keyMessage}`,
    `Mục tiêu: ${adObjective}`,
    `Kênh: ${channel}`,
    `Thông tin sản phẩm: ${productInfoJson}`,
    `Khán giả: ${targetAudienceJson}`
  ].join('\n\n')

  const taskId = `task-${Date.now()}`
  const storyboardId = `brief-001`

  mockPipelineTasks[taskId] = {
    taskId,
    storyboardId,
    revisionNumber: 1,
    storyboardText,
    taskStatus: 'submitted',
    createdAt: new Date().toISOString()
  }

  return {
    taskId,
    storyboardId,
    revisionNumber: 1,
    storyboardText,
    taskStatus: 'submitted'
  }
})
