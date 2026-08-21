import type {
  BriefForm,
  SubmitBriefResponse,
  StoryboardReviewPayload,
  StoryboardReviewResponse,
  RenderStatusResponse,
  DashboardOverviewResponse,
  StoryboardPlan
} from '../types/brief'

export interface UploadBriefAssetPayload {
  briefId: string
  assetType: string
  file: File
}

export interface UploadBriefAssetResponse {
  assetId: string
  briefId: string
  assetType: string
  storageKey: string
}

export const usePipelineApi = () => {
  const { fetchApi } = useApi()

  // 1. Tạo brief dạng draft (POST /api/v1/briefs)
  const createBrief = async (payload: Record<string, any>) => {
    return await fetchApi<{ id: string, status: string, message: string }>('/briefs', {
      method: 'POST',
      body: payload
    })
  }

  // 2. Upload asset riêng lẻ (POST /api/v1/briefs/{id}/assets)
  const uploadBriefAsset = async ({ briefId, assetType, file }: UploadBriefAssetPayload): Promise<UploadBriefAssetResponse> => {
    const formData = new FormData()
    formData.append('briefId', briefId)
    formData.append('assetType', assetType)
    formData.append('file', file)

    return await fetchApi<UploadBriefAssetResponse>(`/briefs/${briefId}/assets`, {
      method: 'POST',
      body: formData
    })
  }

  const uploadBriefAssets = async (briefId: string, filesByType: Record<string, File[]>) => {
    const results: UploadBriefAssetResponse[] = []
    for (const [assetType, files] of Object.entries(filesByType)) {
      for (const file of files) {
        results.push(await uploadBriefAsset({ briefId, assetType, file }))
      }
    }
    return results
  }

  // 3. Submit Brief trọn gói qua Pipeline (POST /api/v1/pipeline/submit-brief)
  const submitBriefForReview = async (payload: BriefForm): Promise<SubmitBriefResponse> => {
    const featuresArray = Array.isArray(payload.productFeatures)
      ? payload.productFeatures
      : typeof payload.productFeatures === 'string'
        ? payload.productFeatures.split(/[\n,]+/).map(s => s.trim()).filter(Boolean)
        : []

    const allowedClaimsArray = Array.isArray(payload.allowedClaims)
      ? payload.allowedClaims
      : typeof payload.allowedClaims === 'string'
        ? payload.allowedClaims.split(/[\n,]+/).map(s => s.trim()).filter(Boolean)
        : []

    const bannedClaimsArray = Array.isArray(payload.bannedClaims)
      ? payload.bannedClaims
      : typeof payload.bannedClaims === 'string'
        ? payload.bannedClaims.split(/[\n,]+/).map(s => s.trim()).filter(Boolean)
        : []

    const bannedContentArray = Array.isArray(payload.bannedContent)
      ? payload.bannedContent
      : typeof payload.bannedContent === 'string'
        ? payload.bannedContent.split(/[\n,]+/).map(s => s.trim()).filter(Boolean)
        : []

    const audienceProfileObj = typeof payload.audienceProfile === 'object'
      ? payload.audienceProfile
      : {
          who: payload.audienceProfile || 'Khách hàng mục tiêu tiềm năng',
          pain_points: ['Cần giải pháp nhanh, hiệu quả'],
          needs: ['Tiện lợi, giá hợp lý, chất lượng cao'],
          buy_reasons: ['Uy tín, ưu đãi tốt']
        }

    const productInfoObj = {
      productName: payload.productName,
      productCategory: payload.productCategory,
      productPrice: Number(payload.productPrice || 0),
      productUsp: payload.productUsp,
      productFeatures: featuresArray,
      productOffer: payload.productOffer || '',
      allowedClaims: allowedClaimsArray
    }

    const constraintsObj = {
      maxDurationMs: Number(payload.maxDurationMs || 15000),
      aspectRatio: payload.aspectRatio || '9:16',
      language: payload.language || 'vi',
      requiredCta: payload.requiredCta || 'Mua ngay hôm nay',
      bannedClaims: bannedClaimsArray,
      bannedContent: bannedContentArray
    }

    const formData = new FormData()
    formData.append('productInfoJson', JSON.stringify(productInfoObj))
    formData.append('targetAudienceJson', JSON.stringify(audienceProfileObj))
    formData.append('adObjective', (payload.objective || 'conversion').toLowerCase())
    formData.append('keyMessage', payload.keyMessage || `${payload.productName} - Giải pháp tối ưu`)
    formData.append('channel', (payload.channel || 'tiktok').toLowerCase())
    formData.append('creativeReferenceJson', JSON.stringify({ url: payload.creativeReference || '' }))
    formData.append('constraintsJson', JSON.stringify(constraintsObj))

    if (Array.isArray(payload.assets)) {
      payload.assets.forEach((item) => {
        if (item instanceof File) {
          formData.append('assets', item)
        } else if (item && typeof item === 'object' && 'file' in item && item.file instanceof File) {
          formData.append('assets', item.file)
        }
      })
    }

    try {
      return await fetchApi<SubmitBriefResponse>('/pipeline/submit-brief', {
        method: 'POST',
        body: formData
      })
    } catch (error) {
      console.warn('[pipeline.submit-brief] Dùng fallback demo storyboard', error)
      const mockTaskId = `task-${Date.now()}`
      const mockStoryboardId = `story-${Date.now()}`

      const mockPlan: StoryboardPlan = {
        scenes: [
          {
            scene_number: 1,
            duration_ms: 3000,
            visual_description: `Cận cảnh mở đầu ấn tượng với vấn đề nổi cộm: "${payload.keyMessage}". Chuyển cảnh nhanh với hiệu ứng zoom.`,
            audio_script: `Bạn có đang tìm kiếm giải pháp đột phá cho ${payload.productCategory || 'cuộc sống'}?`,
            suggested_asset: 'hero'
          },
          {
            scene_number: 2,
            duration_ms: 4500,
            visual_description: `Trải nghiệm thực tế sản phẩm ${payload.productName}. Xuất hiện icon nổi bật tính năng USP: "${payload.productUsp}".`,
            audio_script: `Khám phá ngay ${payload.productName} với ${featuresArray[0] || payload.productUsp}.`,
            suggested_asset: 'closeup'
          },
          {
            scene_number: 3,
            duration_ms: 4500,
            visual_description: `Lifestyle shot: Người dùng tươi cười, hài lòng khi trải nghiệm sự khác biệt. Hiệu ứng text pop-up bắt mắt.`,
            audio_script: `Hiệu quả rõ rệt, tiết kiệm thời gian và tối ưu chi phí cho bạn.`,
            suggested_asset: 'lifestyle'
          },
          {
            scene_number: 4,
            duration_ms: 3000,
            visual_description: `Màn hình kết thúc với Logo thương hiệu, thông tin ưu đãi "${payload.productOffer || 'Ưu đãi có hạn'}" và CTA nổi bật.`,
            audio_script: `${payload.requiredCta || 'Bấm vào link bên dưới để nhận ưu đãi ngay hôm nay!'}`,
            suggested_asset: 'logo'
          }
        ],
        soundtrack: 'Upbeat Tech Trending Beats (128 BPM)',
        voiceover_tone: 'Năng động, tự tin, truyền cảm hứng'
      }

      return {
        taskId: mockTaskId,
        storyboardId: mockStoryboardId,
        revisionNumber: 1,
        plan: mockPlan,
        taskStatus: 'storyboard_review'
      }
    }
  }

  // 4. HITL Review Storyboard (POST /api/v1/pipeline/review-storyboard)
  const reviewStoryboard = async ({ taskId, storyboardId, decision, feedback }: StoryboardReviewPayload): Promise<StoryboardReviewResponse> => {
    try {
      return await fetchApi<StoryboardReviewResponse>('/pipeline/review-storyboard', {
        method: 'POST',
        body: {
          taskId,
          storyboardId,
          decision, // 'approved' | 'needs_revision' | 'rejected'
          feedback: feedback || ''
        }
      })
    } catch (error) {
      console.warn('[pipeline.review-storyboard] Dùng fallback demo review', error)
      if (decision === 'approved') {
        return {
          status: 'render_processing',
          render_job_id: `render-${Date.now()}`
        }
      }

      if (decision === 'needs_revision') {
        const revisedPlan: StoryboardPlan = {
          scenes: [
            {
              scene_number: 1,
              duration_ms: 3000,
              visual_description: `[Đã chỉnh sửa theo phản hồi] Mở đầu trực diện với hook sắc nét hơn: "${feedback || 'Tăng tốc nhịp điệu'}".`,
              audio_script: `Đừng bỏ lỡ giải pháp tối ưu nhất năm nay!`,
              suggested_asset: 'hero'
            },
            {
              scene_number: 2,
              duration_ms: 4000,
              visual_description: `Cận cảnh chi tiết tính năng đã được điều chỉnh. Text overlay rõ ràng, tương phản cao.`,
              audio_script: `Trải nghiệm chất lượng vượt trội được người dùng tin cậy.`,
              suggested_asset: 'closeup'
            },
            {
              scene_number: 3,
              duration_ms: 4000,
              visual_description: `Cảnh quay lifestyle nhịp điệu nhanh, đồng bộ với âm nhạc.`,
              audio_script: `Sự lựa chọn hoàn hảo dành riêng cho bạn.`,
              suggested_asset: 'lifestyle'
            },
            {
              scene_number: 4,
              duration_ms: 4000,
              visual_description: `Khóa chốt CTA mạnh mẽ, sticker ưu đãi chớp nháy thu hút click.`,
              audio_script: `Nhận ngay ưu đãi độc quyền hôm nay!`,
              suggested_asset: 'logo'
            }
          ],
          soundtrack: 'Energetic High-tempo Viral TikTok Mix',
          voiceover_tone: 'Sôi nổi, cuốn hút, dứt khoát'
        }

        return {
          status: 'storyboard_review',
          storyboard_id: `story-${Date.now()}`,
          revision_number: 2,
          plan: revisedPlan
        }
      }

      return {
        status: 'cancelled',
        message: 'Chiến dịch đã được hủy bỏ.'
      }
    }
  }

  // 5. Polling tiến trình Render (GET /api/v1/renders/{id})
  const getRenderStatus = async (renderJobId: string): Promise<RenderStatusResponse> => {
    return await fetchApi<RenderStatusResponse>(`/renders/${renderJobId}`)
  }

  // 6. Lấy số liệu KPI Dashboard (GET /api/v1/dashboard/overview)
  const getDashboardOverview = async (): Promise<DashboardOverviewResponse> => {
    try {
      return await fetchApi<DashboardOverviewResponse>('/dashboard/overview')
    } catch {
      return {
        totalRevenue: 45200.5,
        profitMargin: 22.4,
        activeCampaigns: 8,
        riskLevel: 'MEDIUM'
      }
    }
  }

  return {
    createBrief,
    uploadBriefAsset,
    uploadBriefAssets,
    submitBriefForReview,
    reviewStoryboard,
    getRenderStatus,
    getDashboardOverview
  }
}

