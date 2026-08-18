export const useEngineApi = () => {
  const { fetchApi, isDemoMode } = useApi()

  /**
   * 1. Upload Video & Khởi tạo phiên quét AI (multipart/form-data)
   * Endpoint: /videos/upload
   */
  const uploadVideo = async (payload: VideoUploadPayload): Promise<VideoUploadResponse> => {
    const formData = new FormData()
    formData.append('videoFile', payload.videoFile)
    formData.append('productTitle', payload.productTitle)
    formData.append('productCategory', payload.productCategory)
    formData.append('targetMarket', payload.targetMarket)

    // Gọi thông qua fetchApi của useApi.ts
    const { data, error } = await fetchApi<VideoUploadResponse>('/videos/upload', {
      method: 'POST',
      body: formData
    })

    if (error.value) {
      throw new Error(error.value.message || 'Lỗi khi tải lên video lên hệ thống.')
    }

    return data.value as VideoUploadResponse
  }

  /**
   * 2. Lấy chi tiết / polling trạng thái phiên phân tích
   * Endpoint: /video-scan/{analysisId}
   */
  const getVideoScan = async (analysisId: string) => {
    return await fetchApi<VideoScanDetail>(`/video-scan/${analysisId}`, {
      method: 'GET',
      key: `video-scan-${analysisId}`
    })
  }

  return {
    isDemoMode,
    uploadVideo,
    getVideoScan,
  }
}