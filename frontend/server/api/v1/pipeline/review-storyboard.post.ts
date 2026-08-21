import { mockRenderById } from '../../../utils/mockData'

export default defineEventHandler(async (event) => {
  const body = await readBody(event)
  const taskId = String(body?.taskId || '')
  const storyboardId = String(body?.storyboardId || '')
  const decision = String(body?.decision || 'approved').toLowerCase()
  const feedback = String(body?.feedback || '')

  // 1. Nhánh Approved -> Kích hoạt Render
  if (decision === 'approved') {
    const renderJobId = `render-${Date.now()}`
    mockRenderById[renderJobId] = {
      id: renderJobId,
      taskId,
      storyboardId,
      status: 'processing',
      progress: 25,
      currentStep: 'Khởi tạo luồng render khung hình và tổng hợp âm thanh...',
      updatedAt: new Date().toISOString(),
      video_url: ''
    }

    // Tự động hoàn tất sau 3 giây cho trải nghiệm demo mượt mà
    setTimeout(() => {
      if (mockRenderById[renderJobId]) {
        mockRenderById[renderJobId].status = 'completed'
        mockRenderById[renderJobId].progress = 100
        mockRenderById[renderJobId].currentStep = 'Hoàn tất render và vượt qua kiểm định an toàn (QA Passed).'
        mockRenderById[renderJobId].video_url = 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4'
      }
    }, 3500)

    return {
      status: 'render_processing',
      render_job_id: renderJobId
    }
  }

  // 2. Nhánh Needs Revision -> Agent Pod sinh kịch bản chỉnh sửa
  if (decision === 'needs_revision') {
    const newStoryboardId = `story-${Date.now()}`
    const revisedPlan = {
      scenes: [
        {
          scene_number: 1,
          duration_ms: 3000,
          visual_description: `[Đã điều chỉnh theo feedback: "${feedback || 'Tối ưu lại'}"] Mở đầu với visual bùng nổ, text hook sắc bén hơn.`,
          audio_script: `Bí quyết sở hữu giải pháp dẫn đầu xu hướng ngay trong tầm tay!`,
          suggested_asset: 'hero'
        },
        {
          scene_number: 2,
          duration_ms: 4000,
          visual_description: `Cận cảnh độ chi tiết và tính năng cốt lõi. Nhịp điệu dồn dập, chuyển cảnh năng động.`,
          audio_script: `Chất lượng cao cấp, thiết kế tối giản dành riêng cho bạn.`,
          suggested_asset: 'closeup'
        },
        {
          scene_number: 3,
          duration_ms: 4000,
          visual_description: `Cảnh quay tương tác thực tế với phong cách hiện đại. Màu sắc rực rỡ, sống động.`,
          audio_script: `Trải nghiệm sự khác biệt và đẳng cấp vượt trội.`,
          suggested_asset: 'lifestyle'
        },
        {
          scene_number: 4,
          duration_ms: 4000,
          visual_description: `Hiệu ứng chớp nháy ưu đãi, logo thương hiệu và nút bấm CTA kêu gọi hành động quyết liệt.`,
          audio_script: `Bấm ngay vào liên kết để nhận ưu đãi đặc biệt hôm nay!`,
          suggested_asset: 'logo'
        }
      ],
      soundtrack: 'Hyper-energetic TikTok Phonk Beat (130 BPM)',
      voiceover_tone: 'Sôi nổi, cuốn hút, dứt khoát'
    }

    return {
      status: 'storyboard_review',
      storyboard_id: newStoryboardId,
      revision_number: 2,
      plan: revisedPlan
    }
  }

  // 3. Nhánh Rejected -> Hủy bỏ
  return {
    status: 'cancelled',
    message: 'Chiến dịch đã được hủy bỏ.'
  }
})

