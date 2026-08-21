import { mockBriefs } from '#server/utils/mockData'

export default defineEventHandler((event) => {
  const query = getQuery(event)
  const status = typeof query.status === 'string' ? query.status : ''
  const page = Number(query.page ?? 1)
  const items = status
    ? mockBriefs.filter((brief: any) => brief.status === status)
    : mockBriefs

  return {
    items: items.slice((page - 1) * 10, page * 10),
    total: items.length,
    page,
    status
  }
})
