export const mockOverview = {
  totalVideos: 248,
  successRate: 91,
  avgWatchTime: 18.4,
  activeCampaigns: 14,
  weeklyTrend: [42, 55, 58, 61, 74, 87, 96],
  recentVideos: [
    {
      id: 'ad-2048',
      title: 'Glow Serum Launch',
      channel: 'Meta Ads',
      status: 'Published',
      pulls: '12.4K',
      watchTime: '28s'
    },
    {
      id: 'ad-2041',
      title: 'Desk Setup Mini Reel',
      channel: 'Reels',
      status: 'Rendering',
      pulls: '8.9K',
      watchTime: '18s'
    },
    {
      id: 'ad-2036',
      title: 'Summer Hydration Push',
      channel: 'TikTok',
      status: 'Optimized',
      pulls: '21.7K',
      watchTime: '32s'
    }
  ]
}

export const mockWorkspaceBrief = {
  productName: 'Aether Pro',
  productPrice: '899',
  usp: 'Công nghệ sạc siêu tốc, pin 32h và thiết kế siêu nhẹ cho người làm việc di động.',
  features: 'Sạc nhanh 65W, khung nhôm siêu mỏng, âm thanh Spatial Audio, đệm tay thoải mái.',
  targetAudience: 'Nhân viên sáng tạo, digital nomad, freelancer',
  positioning: 'Giải pháp laptop premium cho người làm việc trên đường',
  channel: 'Reels',
  objective: 'Conversion',
  painPoint: 'Mất tập trung khi máy nặng và pin yếu khi di chuyển.',
  negativePrompt: 'không có cảnh quay sản phẩm quá dài, không dùng phông nền tối quá mức',
  cta: 'Tận dụng ưu đãi 20% hôm nay',
  duration: '18s',
  aspectRatio: '9:16'
}

export const mockHistory = [
  {
    id: 'v-1042',
    title: 'Launch Hero - Aether Pro',
    platform: 'Reels',
    performance: '4.8% CTR',
    status: 'Success',
    createdAt: '2 giờ trước',
    hook: 'Bật máy chỉ trong 2 giây. Cao cấp trong từng chi tiết.'
  },
  {
    id: 'v-1039',
    title: 'Creator Desk Setup',
    platform: 'TikTok',
    performance: '3.7% CTR',
    status: 'Success',
    createdAt: '1 ngày trước',
    hook: 'Cấu hình bàn làm việc sáng tạo tối ưu cho mọi nơi.'
  },
  {
    id: 'v-1032',
    title: 'Hydration Campaign',
    platform: 'Meta Ads',
    performance: '2.5% CTR',
    status: 'Draft',
    createdAt: '2 ngày trước',
    hook: 'Nước và năng lượng trong một nhịp thở.'
  }
]
