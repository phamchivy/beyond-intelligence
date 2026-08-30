import { mockStoryboardByBriefId } from '../../../utils/mockData'

export default defineEventHandler((event) => {
  const id = getRouterParam(event, 'id') || ''
  const storyboard = Object.values(mockStoryboardByBriefId).find((item: any) => item.id === id)

  if (!storyboard) {
    throw createError({ statusCode: 404, statusMessage: 'Storyboard not found' })
  }

  return storyboard
})
