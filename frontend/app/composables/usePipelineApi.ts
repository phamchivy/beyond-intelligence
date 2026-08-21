export type ReviewDecision = 'approved' | 'revised' | 'rejected'

export interface SubmitBriefPayload {
  productName: string
  productCategory: string
  productPrice: number | string
  productUsp: string
  productFeatures: string[]
  productOffer: string
  allowedClaims: string[]
  audienceProfile: string
  objective: string
  keyMessage: string
  channel: string
  aspectRatio: string
  creativeReference: string
  maxDurationMs: number
  language: string
  requiredCta: string
  bannedClaims: string[]
  bannedContent: string[]
  assets?: Array<File | string>
}

export interface UploadBriefAssetPayload {
  briefId: string
  assetType: string
  file: File
}

export interface SubmitBriefResponse {
  taskId: string
  storyboardId: string
  revisionNumber: number
  storyboardText: string
  taskStatus: string
}

export interface ReviewStoryboardPayload {
  taskId: string
  storyboardId: string
  decision: ReviewDecision
  feedback?: string
}

export interface ReviewStoryboardResponse {
  status: string
  render_job_id: string
}

export interface UploadBriefAssetResponse {
  assetId: string
  briefId: string
  assetType: string
  storageKey: string
}

export const usePipelineApi = () => {
  const { fetchApi } = useApi()

  const createBrief = async (payload: Record<string, any>) => {
    return await fetchApi<{ id: string, status: string, message: string }>('/briefs', {
      method: 'POST',
      body: payload
    })
  }

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

  const submitBriefForReview = async (payload: SubmitBriefPayload): Promise<SubmitBriefResponse> => {
    const productInfoJson = JSON.stringify({
      productName: payload.productName,
      productCategory: payload.productCategory,
      productPrice: payload.productPrice,
      productUsp: payload.productUsp,
      productFeatures: payload.productFeatures,
      productOffer: payload.productOffer,
      allowedClaims: payload.allowedClaims,
      maxDurationMs: payload.maxDurationMs,
      language: payload.language,
      requiredCta: payload.requiredCta,
      aspectRatio: payload.aspectRatio,
      channel: payload.channel,
      creativeReference: payload.creativeReference,
      objective: payload.objective,
      keyMessage: payload.keyMessage
    })

    const targetAudienceJson = JSON.stringify({
      audienceProfile: payload.audienceProfile,
      objective: payload.objective,
      keyMessage: payload.keyMessage
    })

    const creativeReferenceJson = JSON.stringify({
      url: payload.creativeReference,
      assetCount: Array.isArray(payload.assets) ? payload.assets.length : 0
    })

    const constraintsJson = JSON.stringify({
      maxDurationMs: payload.maxDurationMs,
      aspectRatio: payload.aspectRatio,
      language: payload.language,
      requiredCta: payload.requiredCta,
      bannedClaims: payload.bannedClaims,
      bannedContent: payload.bannedContent,
      channel: payload.channel
    })

    const formData = new FormData()

    formData.append('productInfoJson', productInfoJson)
    formData.append('targetAudienceJson', targetAudienceJson)
    formData.append('adObjective', payload.objective)
    formData.append('keyMessage', payload.keyMessage)
    formData.append('channel', payload.channel)
    formData.append('creativeReferenceJson', creativeReferenceJson)
    formData.append('constraintsJson', constraintsJson)

    if (Array.isArray(payload.assets)) {
      payload.assets.forEach((item) => {
        if (item instanceof File) {
          formData.append('assets', item)
        } else if (typeof item === 'string' && item.trim()) {
          formData.append('assets', item)
        }
      })
    }

    try {
      return await fetchApi<SubmitBriefResponse>('/pipeline/submit-brief', {
        method: 'POST',
        body: formData
      })
    } catch (error) {
      console.warn('[pipeline.submit-brief] using demo fallback', error)
      const mockTaskId = `task-${Date.now()}`
      const mockStoryboardId = `story-001` //`story-${Date.now()}`
      return {
        taskId: mockTaskId,
        storyboardId: mockStoryboardId,
        revisionNumber: 1,
        storyboardText: [
          'Hook: ' + payload.keyMessage,
          'Scene 1: Giới thiệu sản phẩm ' + payload.productName + ' trong ngữ cảnh ' + payload.channel,
          'Scene 2: Nêu lợi ích chính và điểm nổi bật theo USP',
          'Scene 3: Chốt CTA với ' + (payload.requiredCta || 'Mua ngay hôm nay'),
          'CTA: ' + (payload.requiredCta || 'Mua ngay hôm nay')
        ].join('\n\n'),
        taskStatus: 'submitted'
      }
    }
  }

  const reviewStoryboard = async ({ taskId, storyboardId, decision, feedback }: ReviewStoryboardPayload): Promise<ReviewStoryboardResponse> => {
    try {
      return await fetchApi<ReviewStoryboardResponse>('/pipeline/review-storyboard', {
        method: 'POST',
        body: {
          taskId,
          storyboardId,
          decision,
          feedback: feedback || ''
        }
      })
    } catch (error) {
      console.warn('[pipeline.review-storyboard] using demo fallback', error)
      return {
        status: 'accepted',
        render_job_id: `render-${Date.now()}`
      }
    }
  }

  return {
    createBrief,
    uploadBriefAsset,
    submitBriefForReview,
    reviewStoryboard
  }
}
