<script setup lang="ts">
const { getDashboardOverview } = useEngineApi()

// Gọi API lấy dữ liệu Overview
const { data: overview, pending, refresh } = await getDashboardOverview()

// Helper format tiền tệ USD
const formatCurrency = (val: number) => {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(val)
}

// Cấu hình Option cho Biểu đồ ECharts (Tự động thích ứng màu qua BaseChart)
const chartOptions = computed(() => {
  if (!overview.value?.revenueTrend) return {}

  return {
    legend: { top: '0%' },
    xAxis: {
      type: 'category',
      data: overview.value.revenueTrend.categories
    },
    yAxis: { type: 'value' },
    series: overview.value.revenueTrend.series.map((s, idx) => ({
      name: s.name,
      type: 'line',
      smooth: true,
      data: s.data,
      lineStyle: { width: idx === 0 ? 3 : 2, type: idx === 1 ? 'dashed' : 'solid' },
      areaStyle: idx === 0 ? {
        color: {
          type: 'linear',
          x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [
            { offset: 0, color: 'rgba(99, 102, 241, 0.35)' }, // Indigo-500 tint
            { offset: 1, color: 'rgba(99, 102, 241, 0.0)' }
          ]
        }
      } : undefined
    }))
  }
})
</script>

<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold tracking-tight">Dashboard Overview</h1>
        <p class="text-sm text-gray-500 dark:text-gray-400">
          Tổng quan chỉ số kinh doanh & Dự báo vận hành AI xuyên biên giới
        </p>
      </div>
      <UButton
        icon="i-lucide-refresh-cw"
        color="neutral"
        variant="outline"
        :loading="pending"
        @click="() => refresh()"
      >
        Làm mới
      </UButton>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      <template v-if="pending">
        <USkeleton v-for="i in 4" :key="i" class="h-32 rounded-xl" />
      </template>

      <template v-else-if="overview">
        <UCard class="rounded-xl border border-gray-200 dark:border-gray-800">
          <div class="flex items-center justify-between">
            <span class="text-xs font-semibold text-gray-500 uppercase">Tổng Doanh Thu</span>
            <div class="p-2 bg-indigo-50 dark:bg-indigo-950/50 rounded-lg text-indigo-600 dark:text-indigo-400">
              <UIcon name="i-lucide-dollar-sign" class="w-5 h-5" />
            </div>
          </div>
          <div class="mt-3">
            <div class="text-2xl font-extrabold">{{ formatCurrency(overview.totalRevenue) }}</div>
            <p class="text-xs text-emerald-500 font-medium mt-1 flex items-center gap-1">
              <UIcon name="i-lucide-trending-up" class="w-3.5 h-3.5" /> +14.2% so với tháng trước
            </p>
          </div>
        </UCard>

        <UCard class="rounded-xl border border-gray-200 dark:border-gray-800">
          <div class="flex items-center justify-between">
            <span class="text-xs font-semibold text-gray-500 uppercase">Biên Lợi Nhuận</span>
            <div class="p-2 bg-emerald-50 dark:bg-emerald-950/50 rounded-lg text-emerald-600 dark:text-emerald-400">
              <UIcon name="i-lucide-percent" class="w-5 h-5" />
            </div>
          </div>
          <div class="mt-3">
            <div class="text-2xl font-extrabold">{{ overview.profitMargin }}%</div>
            <p class="text-xs text-gray-500 mt-1">Đã tối ưu hóa chi phí Logistics</p>
          </div>
        </UCard>

        <UCard class="rounded-xl border border-gray-200 dark:border-gray-800">
          <div class="flex items-center justify-between">
            <span class="text-xs font-semibold text-gray-500 uppercase">Chiến Dịch Đang Chạy</span>
            <div class="p-2 bg-blue-50 dark:bg-blue-950/50 rounded-lg text-blue-600 dark:text-blue-400">
              <UIcon name="i-lucide-megaphone" class="w-5 h-5" />
            </div>
          </div>
          <div class="mt-3">
            <div class="text-2xl font-extrabold">{{ overview.activeCampaigns }}</div>
            <p class="text-xs text-gray-500 mt-1">Trên 5 thị trường quốc tế</p>
          </div>
        </UCard>

        <UCard class="rounded-xl border border-gray-200 dark:border-gray-800">
          <div class="flex items-center justify-between">
            <span class="text-xs font-semibold text-gray-500 uppercase">Mức Độ Rủi Ro (Fintech)</span>
            <div class="p-2 bg-amber-50 dark:bg-amber-950/50 rounded-lg text-amber-600 dark:text-amber-400">
              <UIcon name="i-lucide-shield-check" class="w-5 h-5" />
            </div>
          </div>
          <div class="mt-3 flex items-center justify-between">
            <div class="text-2xl font-extrabold capitalize">{{ overview.riskLevel }}</div>
            <UBadge
              :color="overview.riskLevel.toLowerCase() === 'low' ? 'success' : 'warning'"
              variant="soft"
              class="capitalize"
            >
              {{ overview.riskLevel === 'Low' ? 'An toàn' : 'Cảnh báo' }}
            </UBadge>
          </div>
        </UCard>
      </template>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <div class="lg:col-span-2">
        <UiBaseChart
          title="Xu Hướng Doanh Thu Xuyên Biên Giới & Dự Báo AI"
          :option="chartOptions"
          :loading="pending"
        />
      </div>

      <UCard class="rounded-xl border border-gray-200 dark:border-gray-800 flex flex-col justify-between">
        <template #header>
          <div class="flex items-center gap-2">
            <UIcon name="i-lucide-sparkles" class="w-5 h-5 text-indigo-500" />
            <h3 class="font-semibold text-base">Khuyến Nghị AI Hệ Thống</h3>
          </div>
        </template>

        <div class="space-y-4 text-sm">
          <div class="p-3 bg-indigo-50 dark:bg-indigo-950/40 rounded-lg border border-indigo-200 dark:border-indigo-900">
            <p class="font-medium text-indigo-700 dark:text-indigo-300">Tối ưu quảng cáo tại Đức (DE)</p>
            <p class="text-xs text-gray-600 dark:text-gray-400 mt-1">
              AI phát hiện CTR tăng 18% tại thị trường Đức. Đề xuất tăng 15% ngân sách Ad Predictor.
            </p>
          </div>

          <div class="p-3 bg-emerald-50 dark:bg-emerald-950/40 rounded-lg border border-emerald-200 dark:border-emerald-900">
            <p class="font-medium text-emerald-700 dark:text-emerald-300">Định tuyến thanh toán an toàn</p>
            <p class="text-xs text-gray-600 dark:text-gray-400 mt-1">
              Tỷ lệ gian lận ở cổng US-West giảm xuống 0.02%. Luồng tiền ổn định.
            </p>
          </div>
        </div>

        <template #footer>
          <UButton color="primary" block variant="solid" icon="i-lucide-play">
            Chạy Giả Lập What-If (View 2)
          </UButton>
        </template>
      </UCard>
    </div>
  </div>
</template>