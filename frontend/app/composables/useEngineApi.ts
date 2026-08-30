type VideoUploadPayload = {
  videoFile: File
  productTitle: string
  productCategory: string
  targetMarket: string
}

type VideoUploadResponse = {
  id: string
  status: string
  message?: string
}

type VideoScanDetail = {
  analysisId: string
  status: string
  progress: number
  details?: string[]
}

export const useEngineApi = () => {
  const { fetchApi, isDemoMode } = useApi()

  const uploadVideo = async (payload: VideoUploadPayload): Promise<VideoUploadResponse> => {
    const formData = new FormData()
    formData.append('videoFile', payload.videoFile)
    formData.append('productTitle', payload.productTitle)
    formData.append('productCategory', payload.productCategory)
    formData.append('targetMarket', payload.targetMarket)

    return await fetchApi<VideoUploadResponse>('/videos/upload', {
      method: 'POST',
      body: formData
    })
  }

  const getVideoScan = async (analysisId: string): Promise<VideoScanDetail> => {
    return await fetchApi<VideoScanDetail>(`/video-scan/${analysisId}`)
  }

  return {
    isDemoMode,
    uploadVideo,
    getVideoScan
  }
}