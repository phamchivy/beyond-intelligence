import { mockBriefs } from '#server/utils/mockData'

export default defineEventHandler(async (event) => {
  const body = await readBody(event)
  const id = `brief-${String((mockBriefs.length + 1)).padStart(3, '0')}`
  const now = new Date().toISOString()
  const brief = {
    id,
    title: body?.title || body?.productName || 'New creative brief',
    status: 'draft',
    objective: body?.objective || 'Conversion',
    channel: body?.channel || 'Reels',
    duration: body?.duration || '18s',
    ratio: body?.ratio || '9:16',
    createdAt: now,
    updatedAt: now,
    category: body?.category || 'General',
    productName: body?.productName || 'New Product',
    price: body?.price || '0',
    usp: body?.usp || '',
    features: body?.features || '',
    offers: body?.offers || '',
    allowedClaims: body?.allowedClaims || '',
    audience: body?.audience || '',
    painPoint: body?.painPoint || '',
    needs: body?.needs || '',
    keyMessage: body?.keyMessage || '',
    creativeReference: body?.creativeReference || '',
    language: body?.language || 'vi',
    cta: body?.cta || '',
    bannedClaims: body?.bannedClaims || '',
    assets: Array.isArray(body?.assets) ? body.assets : []
  }

  mockBriefs.unshift(brief)

  return { brief, message: 'Brief created successfully' }
})
