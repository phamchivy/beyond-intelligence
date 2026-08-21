import { mockPipelineTasks } from '../../../utils/mockData'

export default defineEventHandler(async (event) => {
  const formData = await readMultipartFormData(event)
  const productInfoRaw = formData?.find(item => item.name === 'productInfoJson')?.data?.toString() || '{}'
  const targetAudienceRaw = formData?.find(item => item.name === 'targetAudienceJson')?.data?.toString() || '{}'
  const adObjective = formData?.find(item => item.name === 'adObjective')?.data?.toString() || 'conversion'
  const keyMessage = formData?.find(item => item.name === 'keyMessage')?.data?.toString() || 'Giải pháp tối ưu cho bạn'
  const channel = formData?.find(item => item.name === 'channel')?.data?.toString() || 'tiktok'

  let productInfo: any = {}
  try {
    productInfo = JSON.parse(productInfoRaw)
  } catch {
    productInfo = { productName: 'Sản phẩm mới' }
  }

  const productName = productInfo.productName || 'Sản phẩm'
  const usp = productInfo.productUsp || 'Đột phá hiệu quả vượt trội'

  const taskId = `task-${Date.now()}`
  const storyboardId = `story-${Date.now()}`

  const plan = {
    scenes: [
      {
        scene_number: 1,
        duration_ms: 3000,
        visual_description: `[Hook] Cận cảnh ấn tượng với visual sống động. Text overlay: "${keyMessage}". Hiệu ứng glitch nhẹ thu hút sự chú ý trong 3 giây đầu.`,
        audio_script: `Bạn có đang gặp khó khăn khi tìm kiếm giải pháp cho ${productInfo.productCategory || 'cuộc sống'}?`,
        suggested_asset: 'hero'
      },
      {
        scene_number: 2,
        duration_ms: 4500,
        visual_description: `[Problem / Agitate] Người dùng trải nghiệm giải pháp thông thường nhưng thất vọng. Chuyển cảnh nhanh sang giải pháp mới.`,
        audio_script: `Đừng để những bất tiện cũ làm chậm bước tiến của bạn mỗi ngày.`,
        suggested_asset: 'closeup'
      },
      {
        scene_number: 3,
        duration_ms: 4500,
        visual_description: `[Solution / USP] Xuất hiện sản phẩm ${productName} với góc quay 3D mượt mà. Highlight USP: "${usp}".`,
        audio_script: `Đã có ${productName} — bí quyết tối ưu hiệu suất và tiết kiệm tối đa.`,
        suggested_asset: 'lifestyle'
      },
      {
        scene_number: 4,
        duration_ms: 3000,
        visual_description: `[CTA & Offer] Logo thương hiệu xuất hiện, badge ưu đãi "${productInfo.productOffer || 'Giảm 20% hôm nay'}" và nút kêu gọi hành động bắt mắt.`,
        audio_script: `Bấm vào link bên dưới để sở hữu ngay với ưu đãi đặc quyền!`,
        suggested_asset: 'logo'
      }
    ],
    soundtrack: 'Trendy Phonk / Upbeat Electronic Beats (128 BPM)',
    voiceover_tone: 'Năng động, cuốn hút, giàu năng lượng'
  }

  mockPipelineTasks[taskId] = {
    taskId,
    storyboardId,
    revisionNumber: 1,
    plan,
    taskStatus: 'storyboard_review',
    createdAt: new Date().toISOString()
  }

  return {
    taskId,
    storyboardId,
    revisionNumber: 1,
    plan,
    taskStatus: 'storyboard_review'
  }
})

