export const useApi = () => {
  const config = useRuntimeConfig()
  const isDemoMode = useState<boolean>('demo_mode', () => config.public.demoMode ?? true)

  const buildApiUrl = (endpoint: string) => {
    const baseUrl = isDemoMode.value ? '/api/v1' : (config.public.apiBase || 'http://localhost:3000/api/v1')
    const normalized = endpoint.startsWith('/') ? endpoint : `/${endpoint}`
    return `${baseUrl}${normalized}`
  }

  const fetchApi = async <T>(endpoint: string, options: Record<string, any> = {}): Promise<T> => {
    return await $fetch<T>(buildApiUrl(endpoint), {
      ...options,
      onResponseError({ response }) {
        console.error('[API Error]:', response.status, response._data)
      }
    })
  }

  return {
    fetchApi,
    buildApiUrl,
    isDemoMode
  }
}
