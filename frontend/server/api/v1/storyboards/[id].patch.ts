import { mockStoryboardByBriefId } from '../../../utils/mockData'

export default defineEventHandler(async (event) => {
  const id = getRouterParam(event, 'id') || ''
  const body = await readBody(event)
  const storyboard = Object.values(mockStoryboardByBriefId).find((item: any) => item.id === id) as Record<string, any> | undefined

  if (!storyboard) {
    throw createError({ statusCode: 404, statusMessage: 'Storyboard not found' })
  }

  if (body?.hook) {
    storyboard.hook = body.hook
  }

  if (Array.isArray(body?.shots)) {
    storyboard.shots = body.shots
  }

  return storyboard
})
