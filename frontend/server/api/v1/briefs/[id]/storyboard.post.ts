import { mockBriefs, mockStoryboardByBriefId } from '#server/utils/mockData'

export default defineEventHandler((event) => {
  const id = getRouterParam(event, 'id') || ''
  const brief = mockBriefs.find((item: any) => item.id === id)

  if (!brief) {
    throw createError({ statusCode: 404, statusMessage: 'Brief not found' })
  }

  const storyboard = mockStoryboardByBriefId[id] ?? {
    id: `story-${id}`,
    briefId: id,
    hook: brief.keyMessage,
    shots: [
      { id: 'shot-1', role: 'hook', asset: brief.assets[0]?.url || '', overlayText: brief.keyMessage, duration: 3 },
      { id: 'shot-2', role: 'product', asset: brief.assets[1]?.url || brief.assets[0]?.url || '', overlayText: brief.productName, duration: 5 },
      { id: 'shot-3', role: 'benefit', asset: brief.assets[2]?.url || brief.assets[0]?.url || '', overlayText: brief.usp, duration: 6 },
      { id: 'shot-4', role: 'cta', asset: brief.assets[3]?.url || brief.assets[0]?.url || '', overlayText: brief.cta, duration: 4 }
    ],
    complianceWarnings: [],
    status: 'awaiting_approval',
    generatedAt: new Date().toISOString()
  }

  return storyboard
})
