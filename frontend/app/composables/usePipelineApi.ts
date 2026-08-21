import type {
  BriefForm,
  SubmitBriefResponse,
  StoryboardReviewPayload,
  StoryboardReviewResponse,
  RenderStatusResponse,
  DashboardOverviewResponse
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

    return await fetchApi<SubmitBriefResponse>('/pipeline/submit-brief', {
      method: 'POST',
      body: formData
    })
  }

  // 4. HITL Review Storyboard (POST /api/v1/pipeline/review-storyboard)
  const reviewStoryboard = async ({ taskId, storyboardId, decision, feedback }: StoryboardReviewPayload): Promise<StoryboardReviewResponse> => {
    return await fetchApi<StoryboardReviewResponse>('/pipeline/review-storyboard', {
      method: 'POST',
      body: {
        taskId,
        storyboardId,
        decision, // 'approved' | 'needs_revision' | 'rejected'
        feedback: feedback || ''
      }
    })
  }

  // 5. Polling tiến trình Render (GET /api/v1/renders/{id})
  const getRenderStatus = async (renderJobId: string): Promise<RenderStatusResponse> => {
    return await fetchApi<RenderStatusResponse>(`/renders/${renderJobId}`)
  }

  // 6. Lấy số liệu KPI Dashboard (GET /api/v1/dashboard/overview)
  const getDashboardOverview = async (): Promise<DashboardOverviewResponse> => {
    return await fetchApi<DashboardOverviewResponse>('/dashboard/overview')
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


