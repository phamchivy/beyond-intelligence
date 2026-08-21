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

export const mockPipelineTasks: Record<string, any> = {}

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

export const mockBriefs = [
  {
    id: 'brief-001',
    title: 'Aether Pro Launch',
    status: 'awaiting_approval',
    objective: 'Conversion',
    channel: 'Reels',
    duration: '18s',
    ratio: '9:16',
    createdAt: '2026-08-20T09:00:00Z',
    updatedAt: '2026-08-20T09:45:00Z',
    category: 'Laptop',
    productName: 'Aether Pro',
    price: '899',
    usp: 'Sạc nhanh 65W, pin 32h, thiết kế siêu nhẹ cho người làm việc di động.',
    features: 'Khung nhôm sợi carbon, webcam 1080p, keyboard backlight, Spatial Audio.',
    offers: 'Giảm 20% trong chuỗi mở bán đầu tiên.',
    allowedClaims: 'Pin 32h, sạc 65W, trọng lượng 1.2kg.',
    audience: 'Nhân viên văn phòng, creators, freelancer di động.',
    painPoint: 'Laptop quá nặng và pin yếu khi đi làm ngoài văn phòng.',
    needs: 'Năng suất ổn định, di chuyển linh hoạt, không cần cắm sạc nhiều lần.',
    keyMessage: 'Laptop di động mạnh như máy để bàn.',
    creativeReference: 'https://example.com/reference/aether',
    language: 'vi',
    cta: 'Tận dụng ưu đãi 20% hôm nay',
    bannedClaims: 'Pin 72h, hiệu năng vượt trội hơn MacBook Pro.',
    assets: [
      { id: 'asset-1', type: 'hero', name: 'hero.png', url: 'https://images.unsplash.com/photo-1517336714731-489689fd1ca8' },
      { id: 'asset-2', type: 'detail', name: 'detail.png', url: 'https://images.unsplash.com/photo-1496181133206-80ce9b88a853' },
      { id: 'asset-3', type: 'lifestyle', name: 'lifestyle.png', url: 'https://images.unsplash.com/photo-1522202176988-66273c2fd55f' },
      { id: 'asset-4', type: 'variant', name: 'variant.png', url: 'https://images.unsplash.com/photo-1545239351-1141bd82e8a6' },
      { id: 'asset-5', type: 'logo', name: 'logo.png', url: 'https://images.unsplash.com/photo-1556740749-887f6717d7e4' }
    ]
  },
  {
    id: 'brief-002',
    title: 'Glow Skin Serum',
    status: 'rendering',
    objective: 'Traffic',
    channel: 'TikTok',
    duration: '15s',
    ratio: '9:16',
    createdAt: '2026-08-19T14:00:00Z',
    updatedAt: '2026-08-19T15:20:00Z',
    category: 'Beauty',
    productName: 'Glow Skin Serum',
    price: '320',
    usp: 'Làm sáng tức thì và cấp ẩm 72h cho làn da mệt mỏi.',
    features: 'Form serum nhẹ, không nhờn, phù hợp da nhạy cảm.',
    offers: 'Miễn phí ship đơn từ 2 sản phẩm.',
    allowedClaims: 'Cấp ẩm 72h, dưỡng sáng, không gây nhờn.',
    audience: 'Phụ nữ 20-35, da thiếu nước, yếu sáng.',
    painPoint: 'Da mệt mỏi, thiếu nước, không đều màu.',
    needs: 'Sản phẩm dễ dùng, hiệu quả rõ, không làm bít tắc lỗ chân lông.',
    keyMessage: 'Làn da sáng khỏe, không cần nhiều bước.',
    creativeReference: 'https://example.com/reference/glow',
    language: 'vi',
    cta: 'Mua ngay hôm nay',
    bannedClaims: 'Chữa trừ sâu, thay đổi da sau 1 lần dùng.',
    assets: [
      { id: 'asset-6', type: 'hero', name: 'serum-hero.png', url: 'https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9' },
      { id: 'asset-7', type: 'detail', name: 'serum-detail.png', url: 'https://images.unsplash.com/photo-1556228720-195a672e8a03' },
      { id: 'asset-8', type: 'lifestyle', name: 'serum-life.png', url: 'https://images.unsplash.com/photo-1529139574466-a303027c1d8b' },
      { id: 'asset-9', type: 'logo', name: 'serum-logo.png', url: 'https://images.unsplash.com/photo-1524504388940-b1c1722653e1' }
    ]
  },
  {
    id: 'brief-003',
    title: 'Night Shift Recovery',
    status: 'done',
    objective: 'Awareness',
    channel: 'Meta',
    duration: '20s',
    ratio: '1:1',
    createdAt: '2026-08-17T13:00:00Z',
    updatedAt: '2026-08-17T18:30:00Z',
    category: 'Wellness',
    productName: 'Night Shift Recovery',
    price: '250',
    usp: 'Công thức hỗ trợ phục hồi sau một ngày làm việc căng thẳng.',
    features: 'Hỗn hợp dưỡng chất, dạng uống, dễ uống mỗi ngày.',
    offers: 'Tặng bộ dụng cụ uống trên 3 đơn đầu tiên.',
    allowedClaims: 'Hỗ trợ phục hồi, giảm mệt mỏi.',
    audience: 'Người làm việc ca đêm, sinh viên, doanh nhân bận rộn.',
    painPoint: 'Mệt mỏi, mất ngủ, khó hồi phục sau ngày dài.',
    needs: 'Giải pháp nhẹ nhàng, dễ dùng mỗi ngày.',
    keyMessage: 'Một bước nhỏ để phục hồi sau ngày dài.',
    creativeReference: 'https://example.com/reference/nightshift',
    language: 'vi',
    cta: 'Khám phá ngay',
    bannedClaims: 'Điều trị mất ngủ, thay thế thuốc.',
    assets: [
      { id: 'asset-10', type: 'hero', name: 'night-hero.png', url: 'https://images.unsplash.com/photo-1517849845537-4d257902454a' },
      { id: 'asset-11', type: 'detail', name: 'night-detail.png', url: 'https://images.unsplash.com/photo-1515377905703-c4788e51af15' },
      { id: 'asset-12', type: 'lifestyle', name: 'night-life.png', url: 'https://images.unsplash.com/photo-1516321318423-f06f85e504b3' }
    ]
  }
]

export const mockStoryboardByBriefId: Record<string, any> = {
  'brief-001': {
    id: 'story-001',
    briefId: 'brief-001',
    hook: 'Việc làm việc di chuyển không còn là rào cản.',
    shots: [
      { id: 'shot-1', role: 'hook', asset: 'https://images.unsplash.com/photo-1496181133206-80ce9b88a853', overlayText: 'Khả năng di chuyển không còn là rào cản', duration: 3 },
      { id: 'shot-2', role: 'product', asset: 'https://images.unsplash.com/photo-1517336714731-489689fd1ca8', overlayText: 'Aether Pro — siêu nhẹ, pin 32h', duration: 4 },
      { id: 'shot-3', role: 'benefit', asset: 'https://images.unsplash.com/photo-1522202176988-66273c2fd55f', overlayText: 'Sạc nhanh 65W, làm việc liền mạch', duration: 6 },
      { id: 'shot-4', role: 'cta', asset: 'https://images.unsplash.com/photo-1545239351-1141bd82e8a6', overlayText: 'Tận dụng ưu đãi 20% hôm nay', duration: 5 }
    ],
    complianceWarnings: [
      { id: 'warn-1', severity: 'medium', title: 'Claim review', message: 'Câu “hiệu năng mạnh như máy để bàn” cần được xác nhận trước khi chạy quảng cáo.' }
    ],
    status: 'awaiting_approval',
    generatedAt: '2026-08-20T09:40:00Z'
  },
  'brief-002': {
    id: 'story-002',
    briefId: 'brief-002',
    hook: 'Nước cho da, không cần nhiều bước',
    shots: [
      { id: 'shot-5', role: 'hook', asset: 'https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9', overlayText: 'Da mệt mỏi cần một bước giải tỏa', duration: 3 },
      { id: 'shot-6', role: 'product', asset: 'https://images.unsplash.com/photo-1556228720-195a672e8a03', overlayText: 'Glow Skin Serum — dưỡng sáng, cấp ẩm', duration: 5 },
      { id: 'shot-7', role: 'benefit', asset: 'https://images.unsplash.com/photo-1529139574466-a303027c1d8b', overlayText: 'Không nhờn, không bít tắc lỗ chân lông', duration: 4 },
      { id: 'shot-8', role: 'cta', asset: 'https://images.unsplash.com/photo-1524504388940-b1c1722653e1', overlayText: 'Mua ngay hôm nay', duration: 3 }
    ],
    complianceWarnings: [],
    status: 'approved',
    generatedAt: '2026-08-19T15:00:00Z'
  }
}

export const mockRenderById: Record<string, any> = {
  'render-001': {
    id: 'render-001',
    briefId: 'brief-001',
    status: 'completed',
    progress: 100,
    currentStep: 'Hoàn tất render và QA',
    updatedAt: '2026-08-20T09:55:00Z',
    video_url: 'https://interactive-examples.mdn.mozilla.net/media/cc0-videos/flower.mp4'
  },
  'render-002': {
    id: 'render-002',
    briefId: 'brief-002',
    status: 'completed',
    progress: 100,
    currentStep: 'Hoàn tất render và QA',
    updatedAt: '2026-08-19T15:42:00Z',
    video_url: 'https://interactive-examples.mdn.mozilla.net/media/cc0-videos/flower.webm'
  }
}

export const mockVideosByBriefId: Record<string, any[]> = {
  'brief-001': [
    {
      id: 'video-001',
      briefId: 'brief-001',
      title: 'Aether Pro Launch v1',
      status: 'done',
      duration: '18s',
      platform: 'Reels',
      ratio: '9:16',
      downloadUrl: 'https://example.com/videos/brief-001-v1.mp4',
      previewUrl: 'https://images.unsplash.com/photo-1496181133206-80ce9b88a853',
      qa: { ratioMatch: true, durationMatch: true, assetVisibleRatio: 92 }
    },
    {
      id: 'video-002',
      briefId: 'brief-001',
      title: 'Aether Pro Launch v2',
      status: 'rendering',
      duration: '18s',
      platform: 'Reels',
      ratio: '9:16',
      downloadUrl: '',
      previewUrl: 'https://images.unsplash.com/photo-1517336714731-489689fd1ca8',
      qa: { ratioMatch: true, durationMatch: true, assetVisibleRatio: 88 }
    }
  ],
  'brief-002': [
    {
      id: 'video-003',
      briefId: 'brief-002',
      title: 'Glow Skin Serum v1',
      status: 'done',
      duration: '15s',
      platform: 'TikTok',
      ratio: '9:16',
      downloadUrl: 'https://example.com/videos/brief-002-v1.mp4',
      previewUrl: 'https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9',
      qa: { ratioMatch: true, durationMatch: true, assetVisibleRatio: 94 }
    }
  ],
  'brief-003': [
    {
      id: 'video-004',
      briefId: 'brief-003',
      title: 'Night Shift Recovery v1',
      status: 'done',
      duration: '20s',
      platform: 'Meta',
      ratio: '1:1',
      downloadUrl: 'https://example.com/videos/brief-003-v1.mp4',
      previewUrl: 'https://images.unsplash.com/photo-1516321318423-f06f85e504b3',
      qa: { ratioMatch: true, durationMatch: true, assetVisibleRatio: 89 }
    }
  ]
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
