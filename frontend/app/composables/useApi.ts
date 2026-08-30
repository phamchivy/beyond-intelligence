export const useApi = () => {
  const config = useRuntimeConfig()
  const isDemoMode = useState<boolean>('demo_mode', () => config.public.demoMode ?? true)

  const buildApiUrl = (endpoint: string) => {
    const baseUrl = isDemoMode.value ? '/api/v1' : (config.public.apiBase || 'http://localhost:8000/api/v1')
    const normalized = endpoint.startsWith('/') ? endpoint : `/${endpoint}`
    return `${baseUrl}${normalized}`
  }

  const getApiErrorMessage = (err: any): string => {
    if (!err) return 'Đã xảy ra lỗi không xác định.'
    const data = err.data || err.response?._data

    if (typeof data === 'string' && data.trim()) return data
    if (data?.message) return data.message
    if (data?.error?.message) return data.error.message
    if (data?.statusMessage) return data.statusMessage
    if (err.message) return err.message

    return `Lỗi máy chủ (${err.statusCode || err.status || 500})`
  }

  const fetchApi = async <T>(endpoint: string, options: Record<string, any> = {}): Promise<T> => {
    return await $fetch<T>(buildApiUrl(endpoint), {
      ...options,
      onResponseError({ response }) {
        console.error(`[API Error ${response.status}]:`, response.url, response._data)
      }
    })
  }

  return {
    fetchApi,
    buildApiUrl,
    isDemoMode,
    getApiErrorMessage
  }
}

