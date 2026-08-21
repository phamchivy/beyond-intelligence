export const useApi = () => {
  const config = useRuntimeConfig()
  const isDemoMode = useState<boolean>('demo_mode', () => config.public.demoMode ?? true)

  const fetchApi = async <T>(endpoint: string, options: Record<string, any> = {}): Promise<T> => {
    const baseUrl = isDemoMode.value ? '/api' : (config.public.apiBase || 'http://localhost:3001/api/v1')
    const target = `${baseUrl}${endpoint.startsWith('/') ? endpoint : `/${endpoint}`}`

    return await $fetch<T>(target, {
      ...options,
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
