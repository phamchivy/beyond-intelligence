<script setup lang="ts">
const route = useRoute()
const videoId = computed(() => route.params.id as string)

// Mock Data Chi tiết Video & Vi phạm
const videoData = ref<VideoScanDetail>({
  id: videoId.value || 'VID-9021',
  title: 'TikTok_Summer_Sale_Campaign_v2.mp4',
  duration: 32,
  videoUrl: 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4',
  status: 'ready',
  safetyRiskScore: 78,
  growthPotentialScore: 86,
  metadata: {
    category: 'E-Commerce Thời trang',
    targetMarket: 'TikTok Shop Vietnam',
    caption: 'Mẫu áo chống nắng thế hệ mới hè 2026 - Giảm ngay 30% hôm nay! #sale #fashion',
    resolution: '1080x1920 (9:16)'
  },
  timestamps: [
    {
      id: 'ts-1',
      timeInSeconds: 4,
      timestampFormatted: '00:04',
      label: 'Logo nhãn hiệu bên thứ 3 chưa cấp quyền',
      severity: 'critical',
      ruleCode: 'POLICY-TK-4.2',
      description: 'Phát hiện logo bản quyền ở góc trên bên trái khung hình.'
    },
    {
      id: 'ts-2',
      timeInSeconds: 12,
      timestampFormatted: '00:12',
      label: 'Text che khuất vùng an toàn (Safe Zone)',
      severity: 'warning',
      ruleCode: 'UX-ZONE-1.1',
      description: 'Tiêu đề giảm giá nằm đè lên nút CTA Mua ngay của TikTok.'
    },
    {
      id: 'ts-3',
      timeInSeconds: 24,
      timestampFormatted: '00:24',
      label: 'Âm lượng nhạc nền vượt ngưỡng quy định (-14 LUFS)',
      severity: 'info',
      ruleCode: 'AUDIO-LOUD-3',
      description: 'Biên độ âm thanh đạt -8 LUFS có nguy cơ bị thuật toán bóp reach.'
    }
  ],
  decisions: [
    {
      id: 'DEC-01',
      videoId: 'VID-9021',
      track: 'safety',
      title: 'Tự động làm mờ (Auto-Blur) Logo nhãn hiệu giây thứ 4',
      description: 'Sử dụng AI inpainting để che logo vi phạm bản quyền mà không làm giảm thẩm mỹ video.',
      confidenceScore: 0.984,
      status: 'pending',
      impact: 'Tránh 100% nguy cơ bị đình chỉ chiến dịch quảng cáo',
      suggestedAction: 'Áp dụng Smart Blur Mask tại timestamp 00:04 - 00:07',
      diffOriginal: 'Khung hình chứa logo gốc chưa mua quyền',
      diffProposed: 'Đã phủ AI Inpainting đồng màu background',
      evidenceId: 'EVI-8891',
      createdAt: 'Vừa xong'
    },
    {
      id: 'DEC-02',
      videoId: 'VID-9021',
      track: 'safety',
      title: 'Dịch chuyển Text CTA lên 45px vào Vùng An toàn',
      description: 'Điều chỉnh tọa độ Y của dòng chữ giảm 30% để tránh bị nút Giỏ hàng che lấp.',
      confidenceScore: 0.962,
      status: 'pending',
      impact: 'Tăng khả năng đọc text thêm 38%',
      suggestedAction: 'Dịch chuyển bounding box phụ đề',
      diffOriginal: 'Tọa độ Y: 1680px (Vùng bị che)',
      diffProposed: 'Tọa độ Y: 1520px (Safe Zone chuẩn)',
      evidenceId: 'EVI-8892',
      createdAt: 'Vừa xong'
    },
    {
      id: 'DEC-03',
      videoId: 'VID-9021',
      track: 'growth',
      title: 'Tối ưu lại Hook 3 giây đầu với Dynamic Caption Động',
      description: 'Phân tích Lakehouse cho thấy video có Hook Motion giữ chân người xem tốt hơn 2.4 lần.',
      confidenceScore: 0.915,
      status: 'pending',
      impact: 'Dự kiến CVR tăng +18.4% và Giữ chân người xem +24%',
      suggestedAction: 'Chèn hiệu ứng Kinetic Typography tại 00:00 - 00:03',
      diffOriginal: 'Text tĩnh tiêu chuẩn',
      diffProposed: 'Kinetic Text + Hiệu ứng âm thanh Pop',
      evidenceId: 'EVI-8893',
      createdAt: 'Vừa xong'
    }
  ]
})

// Tab Navigation
const tabItems = [
  { label: 'Tất cả Quyết định', value: 'all', icon: 'i-lucide-list-checks' },
  { label: 'Safety Track (An toàn)', value: 'safety', icon: 'i-lucide-shield-alert' },
  { label: 'Growth Track (Tăng trưởng)', value: 'growth', icon: 'i-lucide-trending-up' }
]
const activeTab = ref('all')

const filteredDecisions = computed(() => {
  if (activeTab.value === 'all') return videoData.value.decisions
  return videoData.value.decisions.filter(d => d.track === activeTab.value)
})

// Evidence Slideover State
const isSlideoverOpen = ref(false)
const selectedEvidence = ref<EvidenceDetails | null>(null)
const isEvidenceLoading = ref(false)

const handleInspectEvidence = (evidenceId: string) => {
  isSlideoverOpen.value = true
  isEvidenceLoading.value = true

  // Mô phỏng tải chi tiết bằng chứng từ Data Layer
  setTimeout(() => {
    selectedEvidence.value = {
      id: evidenceId,
      platform: 'TikTok',
      policyRef: 'Section 4.2.1 - Intellectual Property & Third-Party Marks',
      policyTitle: 'Nghiêm cấm hiển thị nhãn hiệu chưa được cấp phép trong nội dung thương mại',
      policyExcerpt: 'Mọi video quảng cáo hiển thị logo, nhãn hiệu đã đăng ký mà không kèm giấy ủy quyền hợp lệ sẽ bị từ chối phê duyệt ngay lập tức.',
      lakehouseMetric: {
        name: 'Tỷ lệ Giữ chân 3 giây đầu (Hook Rate)',
        baseline: 24.5,
        projected: 42.9,
        unit: '%',
        sampleSize: '124,500'
      },
      agentRationale: 'Mô hình phát hiện biểu tượng logo với độ tương đồng vector 0.98 so với cơ sở dữ liệu vi phạm. Thuật toán đề xuất inpainting vùng 42x42px tại góc trái để đảm bảo chuẩn an toàn tuyệt đối.',
      confidenceFactors: [
        { factor: 'Độ khớp Vector Chính sách Platform', score: 0.98 },
        { factor: 'Mẫu tương đồng trong Lakehouse', score: 0.94 },
        { factor: 'Độ bảo toàn chất lượng hình ảnh sau inpainting', score: 0.96 }
      ]
    }
    isEvidenceLoading.value = false
  }, 250)
}

const handleApprove = (id: string) => {
  const item = videoData.value.decisions.find(d => d.id === id)
  if (item) item.status = 'approved'
}

const handleReject = (id: string) => {
  const item = videoData.value.decisions.find(d => d.id === id)
  if (item) item.status = 'rejected'
}
</script>

<template>
  <div class="flex flex-col gap-6">
    <!-- Top Breadcrumb & Actions -->
    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
      <div class="flex items-center gap-3">
        <UButton
          to="/scan"
          icon="i-lucide-arrow-left"
          variant="ghost"
          color="neutral"
          size="sm"
        />
        <div>
          <div class="flex items-center gap-2">
            <h1 class="text-xl font-bold text-highlighted tracking-tight">{{ videoData.title }}</h1>
            <UBadge color="warning" variant="subtle" size="xs">
              {{ videoData.timestamps.length }} điểm vi phạm
            </UBadge>
          </div>
          <p class="text-xs text-muted mt-0.5 font-mono">
            ID: {{ videoData.id }} • {{ videoData.metadata.category }} • {{ videoData.metadata.targetMarket }}
          </p>
        </div>
      </div>

      <!-- Quick Metrics Pill -->
      <div class="flex items-center gap-2">
        <div class="px-3 py-1.5 rounded-lg bg-amber-500/10 border border-amber-500/20 text-xs">
          <span class="text-amber-700 dark:text-amber-300 font-semibold">Rủi ro Safety: {{ videoData.safetyRiskScore }}/100</span>
        </div>
        <div class="px-3 py-1.5 rounded-lg bg-indigo-500/10 border border-indigo-500/20 text-xs">
          <span class="text-indigo-600 dark:text-indigo-400 font-semibold">Tiềm năng Growth: {{ videoData.growthPotentialScore }}/100</span>
        </div>
      </div>
    </div>

    <!-- 2-Column Split Studio Grid -->
    <div class="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
      <!-- Cột Trái (7/12): Video Scanner Player & Metadata Details -->
      <div class="lg:col-span-7 flex flex-col gap-4">
        <VideoScannerPlayer
          :src="videoData.videoUrl"
          :timestamps="videoData.timestamps"
        />

        <!-- Video Metadata Specs Card -->
        <UCard>
          <template #header>
            <h3 class="font-semibold text-highlighted text-xs uppercase tracking-wider">Thông số Kỹ thuật & Metadata</h3>
          </template>
          <div class="grid grid-cols-2 sm:grid-cols-3 gap-3 text-xs">
            <div>
              <span class="text-muted">Độ phân giải:</span>
              <p class="font-mono font-medium text-highlighted mt-0.5">{{ videoData.metadata.resolution }}</p>
            </div>
            <div>
              <span class="text-muted">Thời lượng:</span>
              <p class="font-mono font-medium text-highlighted mt-0.5">{{ videoData.duration }} giây</p>
            </div>
            <div>
              <span class="text-muted">Kênh phân phối:</span>
              <p class="font-medium text-highlighted mt-0.5">{{ videoData.metadata.targetMarket }}</p>
            </div>
          </div>
        </UCard>
      </div>

      <!-- Cột Phải (5/12): Dual-Track Decision Hub (Human-in-the-Loop) -->
      <div class="lg:col-span-5 flex flex-col gap-4">
        <!-- Dual-Track Tabs Header -->
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-1.5">
            <UIcon name="i-lucide-bot" class="size-4 text-primary" />
            <h2 class="font-bold text-highlighted text-sm">Dual-Track Decision Hub</h2>
          </div>
          <span class="text-xs text-muted font-mono">
            {{ filteredDecisions.length }} đề xuất
          </span>
        </div>

        <!-- Filter Tabs -->
        <UTabs
          v-model="activeTab"
          :items="tabItems"
          class="w-full"
          color="primary"
          variant="pill"
        />

        <!-- Decision Cards List -->
        <div class="flex flex-col gap-3">
          <DecisionCard
            v-for="decision in filteredDecisions"
            :key="decision.id"
            :decision="decision"
            @approve="handleApprove"
            @reject="handleReject"
            @inspect-evidence="handleInspectEvidence"
          />
        </div>
      </div>
    </div>
    

    <!-- Evidence & Traceability Slideover Component -->
    <EvidenceSlideover
      v-model:open="isSlideoverOpen"
      :evidence="selectedEvidence"
      :loading="isEvidenceLoading"
      @apply="isSlideoverOpen = false"
    />
  </div>
</template>