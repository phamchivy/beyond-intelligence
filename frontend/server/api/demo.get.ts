export default defineEventHandler(() => ({
  metrics: [
    { label: 'Signal volume', value: 128 },
    { label: 'Engagement rate', value: '94%' }
  ],
  trend: {
    labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'],
    values: [32, 45, 41, 54, 38, 61]
  },
  prompts: [
    'Summarize the product in one sentence',
    'Suggest the next best action for the user',
    'Surface the most important insight from the data'
  ],
  nextSteps: [
    'Connect the assistant to your model or workflow',
    'Replace mock analytics with real product signals',
    'Prepare a polished pitch and deployment checklist'
  ]
}))
