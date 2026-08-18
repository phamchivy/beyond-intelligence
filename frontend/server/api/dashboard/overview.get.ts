// server/api/dashboard/overview.get.ts
export default defineEventHandler(() => {
  return {
    totalRevenue: 128450.00,
    profitMargin: 24.5,
    activeCampaigns: 12,
    riskLevel: 'Low',
    revenueTrend: {
      categories: ['T1', 'T2', 'T3', 'T4', 'T5', 'T6'],
      series: [
        { name: 'Doanh thu Thực tế ($)', data: [18000, 22000, 25000, 21000, 28000, 34450] },
        { name: 'Dự báo AI ($)', data: [17500, 21000, 24500, 22000, 29000, 35000] }
      ]
    }
  }
})