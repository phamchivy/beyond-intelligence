export default defineEventHandler(async (event) => {
  const briefId = getRouterParam(event, 'id') || ''
  const formData = await readMultipartFormData(event)
  const briefIdField = formData?.find(item => item.name === 'briefId')?.data?.toString() || briefId
  const assetType = formData?.find(item => item.name === 'assetType')?.data?.toString() || 'hero'
  const file = formData?.find(item => item.name === 'file')

  if (!file || !file.filename) {
    throw createError({ statusCode: 400, statusMessage: 'Missing asset file' })
  }

  const storageKey = `storage/${briefIdField}/${assetType}/${Date.now()}-${file.filename}`

  return {
    assetId: `asset-${Date.now()}`,
    briefId: briefIdField,
    assetType,
    storageKey
  }
})
