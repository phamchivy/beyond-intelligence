import { mockBriefs } from '#server/utils/mockData'

export default defineEventHandler((event) => {
  const id = getRouterParam(event, 'id') || ''
  const brief = mockBriefs.find((item: any) => item.id === id)

  if (!brief) {
    throw createError({ statusCode: 404, statusMessage: 'Brief not found' })
  }

  return brief
})
