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

// Agent storyboard plan uses hook/scenes/call_to_action with time ranges (order, time_start_seconds,
// scene_description, on_screen_text). Adapt it to the flat scenes[] shape the UI renders.
const mapAgentPlanToUiPlan = (plan: any): StoryboardPlan => {
  if (!plan) return plan

  const rawScenes = [
    ...(plan.hook ? [plan.hook] : []),
    ...(Array.isArray(plan.scenes) ? plan.scenes : []),
    ...(plan.call_to_action ? [plan.call_to_action] : [])
  ]

  return {
    ...plan,
    scenes: rawScenes.map((s: any, idx: number) => ({
      scene_number: idx + 1,
      duration_ms: Math.round(((s.time_end_seconds ?? 0) - (s.time_start_seconds ?? 0)) * 1000),
      visual_description: s.scene_description || '',
      audio_script: s.on_screen_text || s.audio_note || '',
      suggested_asset: s.suggested_asset
    })),
    soundtrack: plan.soundtrack || plan.production_notes?.music_style,
    voiceover_tone: plan.voiceover_tone || plan.production_notes?.pacing_note
  }
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
    formData.append('product_info', JSON.stringify(productInfoObj))
    formData.append('target_audience', JSON.stringify(audienceProfileObj))
    formData.append('ad_objective', (payload.objective || 'conversion').toLowerCase())
    formData.append('key_message', payload.keyMessage || `${payload.productName} - Giải pháp tối ưu`)
    formData.append('channel', (payload.channel || 'tiktok').toLowerCase())
    formData.append('creative_reference', JSON.stringify({ url: payload.creativeReference || '' }))
    formData.append('constraints', JSON.stringify(constraintsObj))

    if (Array.isArray(payload.assets)) {
      payload.assets.forEach((item) => {
        if (item instanceof File) {
          formData.append('assets', item)
        } else if (item && typeof item === 'object' && 'file' in item && item.file instanceof File) {
          formData.append('assets', item.file)
        }
      })
    }

    const res = await fetchApi<{
      task_id: string
      storyboard_id: string
      revision_number: number
      plan: StoryboardPlan
      task_status: string
    }>('/pipeline/submit-brief', {
      method: 'POST',
      body: formData
    })

    return {
      taskId: res.task_id,
      storyboardId: res.storyboard_id,
      revisionNumber: res.revision_number,
      plan: mapAgentPlanToUiPlan(res.plan),
      taskStatus: res.task_status
    }
  }

  // 4. HITL Review Storyboard (POST /api/v1/pipeline/review-storyboard)
  const reviewStoryboard = async ({ taskId, storyboardId, decision, feedback }: StoryboardReviewPayload): Promise<StoryboardReviewResponse> => {
    const res = await fetchApi<StoryboardReviewResponse>('/pipeline/review-storyboard', {
      method: 'POST',
      body: {
        task_id: taskId,
        storyboard_id: storyboardId,
        decision, // 'approved' | 'needs_revision' | 'rejected'
        feedback: feedback || ''
      }
    })

    if (res.plan) {
      res.plan = mapAgentPlanToUiPlan(res.plan)
    }
    return res
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

