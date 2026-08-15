// composables/useApi.ts
export const useApi = () => {
  const config = useRuntimeConfig()
  // Trạng thái Demo Mode toàn cục (dùng useState)
  const isDemoMode = useState<boolean>('demo_mode', () => true)

  /**
   * Hàm gọi API chung
   * @param endpoint - Đường dẫn API (ví dụ: '/dashboard/overview')
   * @param options - Cấu hình fetch bổ sung
   */
  const fetchApi = async <T>(endpoint: string, options: any = {}) => {
    // Nếu bật Demo Mode, hướng request về Local Mock API của Nuxt (server/api/)
    const baseUrl = isDemoMode.value ? '' : config.public.apiBase

    return await useFetch<T>(`${baseUrl}${endpoint}`, {
      ...options,
      onRequest({ options }) {
        options.headers = options.headers || {}
        // options.headers.Authorization = `Bearer ${token}`
      },
      onResponseError({ response }) {
        console.error('[API Error]:', response.status, response._data)
      }
    })
  }

  return {
    fetchApi,
    isDemoMode
  }
}