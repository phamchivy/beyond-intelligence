import { mockVideosByBriefId } from '../../../../utils/mockData'

export default defineEventHandler((event) => {
  const id = getRouterParam(event, 'id') || ''

  return {
    items: mockVideosByBriefId[id] || []
  }
})
