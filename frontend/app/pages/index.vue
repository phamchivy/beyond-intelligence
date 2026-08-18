<script setup lang="ts">
import type { EChartsOption } from 'echarts'

const { isDemoMode } = useEngineApi()

// Mock Overview Data
const kpis = ref([
  {
    title: 'Tỷ lệ Giảm thiểu Vi phạm',
    value: '94.2%',
    change: '+12.4%',
    positive: true,
    icon: 'i-lucide-shield-check',
    color: 'text-emerald-500'
  },
  {
    title: 'CVR Uplift Dự phóng',
    value: '+18.6%',
    change: '+3.8%',
    positive: true,
    icon: 'i-lucide-trending-up',
    color: 'text-indigo-500'
  },
  {
    title: 'Video Đang Chờ Phê duyệt',
    value: '7 files',
    change: '2 Critical',
    positive: false,
    icon: 'i-lucide-alert-triangle',
    color: 'text-amber-500'
  },
  {
    title: 'Tổng Video Đã Quét',
    value: '1,428',
    change: '24h qua',
    positive: true,
    icon: 'i-lucide-film',
    color: 'text-primary'
  }
])

// ECharts CVR Trend Option
const cvrChartOption = ref<EChartsOption>({
  tooltip: { trigger: 'axis' },
  legend: { data: ['Trước tối ưu', 'Sau AI Mitigation'] },
  xAxis: {
    type: 'category',
    data: ['T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'CN']
  },
  yAxis: {
    type: 'value',
    axisLabel: { formatter: '{value}%' }
  },
  series: [
    {
      name: 'Trước tối ưu',
      type: 'line',
      smooth: true,
      data: [2.1, 2.4, 2.0, 2.3, 2.2, 2.5, 2.3],
      itemStyle: { color: '#94a3b8' },
      lineStyle: { type: 'dashed' }
    },
    {
      name: 'Sau AI Mitigation',
      type: 'line',
      smooth: true,
      data: [2.1, 2.9, 3.4, 3.8, 4.1, 4.3, 4.6],
      itemStyle: { color: '#6366f1' },
      areaStyle: {
        color: {
          type: 'linear',
          x: 0,
          y: 0,
          x2: 0,
          y2: 1,
          colorStops: [
            { offset: 0, color: 'rgba(99, 102, 241, 0.35)' },
            { offset: 1, color: 'rgba(99, 102, 241, 0.0)' }
          ]
        }
      }
    }
  ]
})

// ECharts Violations Breakdown Option
const violationsChartOption = ref<EChartsOption>({
  tooltip: { trigger: 'item' },
  series: [
    {
      name: 'Loại vi phạm',
      type: 'pie',
      radius: ['50%', '75%'],
      avoidLabelOverlap: false,
      itemStyle: { borderRadius: 8, borderColor: '#fff', borderWidth: 2 },
      label: { show: false },
      data: [
        { value: 42, name: 'Bản quyền Logo / Watermark', itemStyle: { color: '#f59e0b' } },
        { value: 28, name: 'Âm thanh bản quyền', itemStyle: { color: '#ef4444' } },
        { value: 20, name: 'Text che khuất CTA', itemStyle: { color: '#6366f1' } },
        { value: 10, name: 'Sai tỷ lệ khung hình (Aspect)', itemStyle: { color: '#06b6d4' } }
      ]
    }
  ]
})

// Video Queue List
const recentVideos = ref([
  {
    id: 'VID-9021',
    title: 'TikTok_Summer_Sale_Campaign_v2.mp4',
    channel: 'TikTok Shop VN',
    violations: 3,
    status: 'pending',
    riskLevel: 'critical',
    cvrPotential: '+21.4%'
  },
  {
    id: 'VID-8840',
    title: 'MetaAds_Beauty_Product_Hook.mp4',
    channel: 'Meta Reels US',
    violations: 1,
    status: 'pending',
    riskLevel: 'warning',
    cvrPotential: '+14.2%'
  },
  {
    id: 'VID-7612',
    title: 'YoutubeShorts_Unboxing_Tech.mp4',
    channel: 'Shorts Global',
    violations: 0,
    status: 'mitigated',
    riskLevel: 'info',
    cvrPotential: '+8.0%'
  }
])
</script>

<template>
  <div class="flex flex-col gap-6">
    <!-- Header Page Banner -->
    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
      <div>
        <h1 class="text-2xl font-bold text-highlighted tracking-tight">Intelligence Workspace</h1>
        <p class="text-sm text-muted mt-1">
          Giám sát tự động hóa vi phạm bản quyền và tối ưu tỷ lệ chuyển đổi (CVR) xuyên biên giới.
        </p>
      </div>
      <UButton
        to="/scan"
        color="primary"
        variant="solid"
        icon="i-lucide-scan-line"
        label="Bắt đầu Quét Video Mới"
      />
    </div>

    <!-- KPI Metrics Grid -->
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      <UCard v-for="kpi in kpis" :key="kpi.title">
        <div class="flex items-center justify-between">
          <span class="text-xs font-medium text-muted">{{ kpi.title }}</span>
          <UIcon :name="kpi.icon" :class="kpi.color" class="size-5" />
        </div>
        <div class="mt-3 flex items-baseline justify-between">
          <span class="text-2xl font-bold text-highlighted font-mono">{{ kpi.value }}</span>
          <UBadge :color="kpi.positive ? 'success' : 'warning'" variant="subtle" size="xs">
            {{ kpi.change }}
          </UBadge>
        </div>
      </UCard>
    </div>

    <!-- 2 Charts Row -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <div class="lg:col-span-2">
        <BaseChart
          title="Xu hướng CVR: Trước vs Sau khi áp dụng AI Auto-Mitigation"
          description="Đo lường hiệu suất chuyển đổi thực tế qua 7 ngày thử nghiệm"
          :option="cvrChartOption"
        />
      </div>
      <div class="lg:col-span-1">
        <BaseChart
          title="Phân bổ Vi phạm theo Chính sách"
          description="Tỷ trọng rủi ro kiểm duyệt phổ biến nhất"
          :option="violationsChartOption"
        />
      </div>
    </div>

    <!-- Recent Scanning Queue Table -->
    <UCard>
      <template #header>
        <div class="flex items-center justify-between">
          <div>
            <h3 class="font-semibold text-highlighted text-sm">Hàng đợi Phân tích & Phê duyệt</h3>
            <p class="text-xs text-muted mt-0.5">Danh sách các video vừa được AI Agent quét và gắn cờ</p>
          </div>
          <UBadge color="neutral" variant="outline" size="sm">
            {{ recentVideos.length }} mục cần xử lý
          </UBadge>
        </div>
      </template>

      <div class="overflow-x-auto">
        <table class="w-full text-left text-xs">
          <thead class="border-b border-muted text-muted font-medium uppercase tracking-wider">
            <tr>
              <th class="py-3 px-4">Mã Video</th>
              <th class="py-3 px-4">Tên File</th>
              <th class="py-3 px-4">Kênh Target</th>
              <th class="py-3 px-4">Số Lỗi Vi phạm</th>
              <th class="py-3 px-4">CVR Tiềm năng</th>
              <th class="py-3 px-4 text-right">Thao tác</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-muted/50">
            <tr v-for="video in recentVideos" :key="video.id" class="hover:bg-muted/20 transition-colors">
              <td class="py-3 px-4 font-mono font-semibold text-highlighted">{{ video.id }}</td>
              <td class="py-3 px-4 font-medium text-highlighted flex items-center gap-2">
                <UIcon name="i-lucide-file-video" class="size-4 text-primary" />
                {{ video.title }}
              </td>
              <td class="py-3 px-4 text-muted">{{ video.channel }}</td>
              <td class="py-3 px-4">
                <UBadge
                  :color="video.violations > 0 ? (video.riskLevel === 'critical' ? 'error' : 'warning') : 'success'"
                  variant="subtle"
                  size="xs"
                >
                  {{ video.violations }} lỗi phát hiện
                </UBadge>
              </td>
              <td class="py-3 px-4 font-mono font-bold text-indigo-600 dark:text-indigo-400">
                {{ video.cvrPotential }}
              </td>
              <td class="py-3 px-4 text-right">
                <UButton
                  :to="`/scan/${video.id}`"
                  color="primary"
                  variant="ghost"
                  size="xs"
                  label="Vào Studio & Phê duyệt"
                  icon="i-lucide-arrow-right"
                  trailing
                />
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </UCard>
  </div>
</template>