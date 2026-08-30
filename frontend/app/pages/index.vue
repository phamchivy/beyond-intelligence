<script setup lang="ts">
import type { DashboardOverviewResponse } from '../types/brief'

const { fetchApi } = useApi()
const { getDashboardOverview } = usePipelineApi()

const normalizeStatus = (status: string) => {
  const normalized = String(status || '').toLowerCase()
  if (['draft', 'saved', 'new'].includes(normalized)) return 'draft'
  if (['submitted', 'queued', 'processing', 'reviewing', 'storyboard_review', 'storyboard_pending'].includes(normalized)) return 'storyboard_review'
  if (['rendering', 'render', 'render_processing'].includes(normalized)) return 'rendering'
  if (['done', 'completed', 'success'].includes(normalized)) return 'done'
  if (['failed', 'error'].includes(normalized)) return 'failed'
  return normalized || 'draft'
}

const { data: overviewData } = await useAsyncData<DashboardOverviewResponse>('dashboard-overview', () =>
  getDashboardOverview()
)

const { data: briefsData, pending } = await useLazyAsyncData('home-briefs', () =>
  fetchApi<{ items: Array<Record<string, any>> }>('/briefs?page=1')
)

const briefs = computed(() => (briefsData.value?.items ?? []).map((item: Record<string, any>) => ({
  ...item,
  id: item.id || `campaign-${Math.random().toString(36).slice(2, 8)}`,
  status: normalizeStatus(item.status),
  title: item.title || item.productName || 'Chiến dịch Video',
  channel: item.channel || 'TikTok',
  objective: item.objective || 'Conversion'
})))

const statusColor = (status: string): 'error' | 'primary' | 'secondary' | 'success' | 'info' | 'warning' | 'neutral' => {
  const map: Record<string, 'error' | 'primary' | 'secondary' | 'success' | 'info' | 'warning' | 'neutral'> = {
    draft: 'neutral',
    storyboard_review: 'warning',
    rendering: 'primary',
    done: 'success',
    failed: 'error'
  }
  return map[status] || 'neutral'
}

const statusLabel = (status: string) => {
  const map: Record<string, string> = {
    draft: 'Bản nháp',
    storyboard_review: 'Chờ duyệt HITL',
    rendering: 'Đang Render',
    done: 'Hoàn tất',
    failed: 'Thất bại'
  }
  return map[status] || status
}
</script>

<template>
  <div class="space-y-8">
    <!-- Hero Banner -->
    <section class="relative overflow-hidden rounded-3xl border border-indigo-500/20 bg-gradient-to-br from-indigo-900/90 via-slate-900 to-zinc-950 p-6 text-white shadow-xl sm:p-8">
      <div class="relative z-10 flex flex-col gap-6 md:flex-row md:items-center md:justify-between">
        <div class="max-w-xl space-y-2">
          <div class="inline-flex items-center gap-1.5 rounded-full bg-indigo-500/20 px-3 py-1 text-xs font-semibold text-indigo-300">
            <UIcon name="lucide:zap" class="h-3.5 w-3.5" />
            Platform 6: Action & Workflow Engine
          </div>
          <h1 class="text-2xl font-bold tracking-tight sm:text-3xl">
            Tự Động Hóa Sản Xuất Short Video Ads Với AI
          </h1>
          <p class="text-sm text-indigo-200/80">
            Biến Brief sản phẩm & hình ảnh thành video quảng cáo 9:16 chuẩn hóa cho TikTok, Reels & Meta Feed qua quy trình kiểm định Human-In-The-Loop.
          </p>
        </div>

        <div class="flex flex-wrap items-center gap-3">
          <UButton to="/workspace" color="primary" size="lg" icon="lucide:sparkles">
            Vào Workspace Tạo Video
          </UButton>
          <UButton to="/briefs" variant="outline" color="neutral" size="lg">
            Quản Lý Briefs
          </UButton>
        </div>
      </div>

      <!-- Subtle background glow -->
      <div class="absolute -right-20 -top-20 h-64 w-64 rounded-full bg-indigo-500/20 blur-3xl" />
    </section>

    <!-- 4 Core KPIs -->
    <section class="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <UCard class="border border-slate-200 dark:border-zinc-800">
        <div class="space-y-2">
          <div class="flex items-center justify-between">
            <span class="text-xs font-bold uppercase tracking-wider text-slate-500">Doanh Thu Mục Tiêu</span>
            <div class="rounded-lg bg-emerald-500/10 p-1.5 text-emerald-600 dark:text-emerald-400">
              <UIcon name="lucide:dollar-sign" class="h-4 w-4" />
            </div>
          </div>
          <p class="text-2xl font-extrabold text-slate-900 dark:text-white">
            {{ overviewData?.totalRevenue !== undefined ? `$${overviewData.totalRevenue.toLocaleString('en-US')}` : '---' }}
          </p>
          <p class="text-xs text-emerald-600 dark:text-emerald-400 flex items-center gap-1 font-medium">
            <UIcon name="lucide:trending-up" class="h-3 w-3" /> Số liệu chiến dịch thời gian thực
          </p>
        </div>
      </UCard>

      <UCard class="border border-slate-200 dark:border-zinc-800">
        <div class="space-y-2">
          <div class="flex items-center justify-between">
            <span class="text-xs font-bold uppercase tracking-wider text-slate-500">Tỷ Suất Lợi Nhuận</span>
            <div class="rounded-lg bg-indigo-500/10 p-1.5 text-indigo-600 dark:text-indigo-400">
              <UIcon name="lucide:percent" class="h-4 w-4" />
            </div>
          </div>
          <p class="text-2xl font-extrabold text-slate-900 dark:text-white">
            {{ overviewData?.profitMargin !== undefined ? `${overviewData.profitMargin}%` : '---' }}
          </p>
          <p class="text-xs text-indigo-600 dark:text-indigo-400 flex items-center gap-1 font-medium">
            <UIcon name="lucide:check" class="h-3 w-3" /> Tối ưu chi phí sản xuất AI
          </p>
        </div>
      </UCard>

      <UCard class="border border-slate-200 dark:border-zinc-800">
        <div class="space-y-2">
          <div class="flex items-center justify-between">
            <span class="text-xs font-bold uppercase tracking-wider text-slate-500">Chiến Dịch Đang Chạy</span>
            <div class="rounded-lg bg-violet-500/10 p-1.5 text-violet-600 dark:text-violet-400">
              <UIcon name="lucide:activity" class="h-4 w-4" />
            </div>
          </div>
          <p class="text-2xl font-extrabold text-slate-900 dark:text-white">
            {{ overviewData?.activeCampaigns !== undefined ? overviewData.activeCampaigns : '---' }}
          </p>
          <p class="text-xs text-slate-500">
            Tổng số chiến dịch đang xử lý
          </p>
        </div>
      </UCard>

      <UCard class="border border-slate-200 dark:border-zinc-800">
        <div class="space-y-2">
          <div class="flex items-center justify-between">
            <span class="text-xs font-bold uppercase tracking-wider text-slate-500">Mức Độ Rủi Ro QA</span>
            <div class="rounded-lg bg-amber-500/10 p-1.5 text-amber-600 dark:text-amber-400">
              <UIcon name="lucide:shield-alert" class="h-4 w-4" />
            </div>
          </div>
          <div class="flex items-center gap-2">
            <p class="text-2xl font-extrabold text-slate-900 dark:text-white">
              {{ overviewData?.riskLevel || 'AN TOÀN' }}
            </p>
            <UBadge :color="overviewData?.riskLevel === 'HIGH' ? 'error' : overviewData?.riskLevel === 'MEDIUM' ? 'warning' : 'success'" size="xs">
              {{ overviewData?.riskLevel || 'LOW' }}
            </UBadge>
          </div>
          <p class="text-xs text-slate-500">
            Tuân thủ chính sách quảng cáo TikTok
          </p>
        </div>
      </UCard>
    </section>

    <!-- Main Content: Recent Campaigns & Pipeline Flow Guidance -->
    <div class="grid gap-6 lg:grid-cols-12">
      <!-- Recent Campaigns (7 / 12) -->
      <div class="lg:col-span-7">
        <UCard>
          <template #header>
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2">
                <UIcon name="lucide:history" class="h-4 w-4 text-indigo-600 dark:text-indigo-400" />
                <h2 class="text-sm font-bold uppercase tracking-wider text-slate-800 dark:text-zinc-200">
                  Chiến Dịch Gần Đây
                </h2>
              </div>
              <UButton to="/briefs" variant="ghost" size="xs">
                Xem tất cả
              </UButton>
            </div>
          </template>

          <div v-if="pending" class="space-y-3">
            <USkeleton v-for="n in 3" :key="n" class="h-16 w-full rounded-xl" />
          </div>

          <div v-else class="space-y-3">
            <div
              v-for="brief in briefs.slice(0, 5)"
              :key="brief.id"
              class="flex flex-col gap-3 rounded-xl border border-slate-200 bg-slate-50/50 p-3.5 transition hover:border-indigo-500/40 dark:border-zinc-800 dark:bg-zinc-900/50 sm:flex-row sm:items-center sm:justify-between"
            >
              <div class="space-y-1">
                <p class="text-sm font-bold text-slate-900 dark:text-white">{{ brief.title }}</p>
                <div class="flex items-center gap-2 text-xs text-slate-500">
                  <span class="font-medium text-indigo-600 dark:text-indigo-400">{{ brief.channel }}</span>
                  <span>•</span>
                  <span>{{ brief.objective }}</span>
                </div>
              </div>

              <div class="flex items-center gap-2">
                <UBadge :color="statusColor(brief.status)" size="sm" variant="subtle">
                  {{ statusLabel(brief.status) }}
                </UBadge>
                <UButton :to="`/workspace`" size="xs" variant="outline">
                  Mở
                </UButton>
              </div>
            </div>
          </div>
        </UCard>
      </div>

      <!-- Quick Guidance & Safe Zones (5 / 12) -->
      <div class="space-y-4 lg:col-span-5">
        <UCard class="border-indigo-500/20 bg-indigo-50/30 dark:bg-indigo-950/20">
          <template #header>
            <div class="flex items-center gap-2">
              <UIcon name="lucide:check-circle" class="h-4 w-4 text-indigo-600 dark:text-indigo-400" />
              <h3 class="text-sm font-bold text-slate-900 dark:text-white">Quy Trình 3 Bước Chuẩn</h3>
            </div>
          </template>

          <div class="space-y-3 text-xs text-slate-600 dark:text-zinc-300">
            <div class="flex items-start gap-2.5">
              <span class="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-indigo-600 text-[10px] font-bold text-white">1</span>
              <div>
                <p class="font-semibold text-slate-900 dark:text-white">Nhập Brief & Upload Assets</p>
                <p class="text-slate-500">Dán USP sản phẩm và tải ảnh Hero, Detail, Lifestyle.</p>
              </div>
            </div>

            <div class="flex items-start gap-2.5">
              <span class="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-indigo-600 text-[10px] font-bold text-white">2</span>
              <div>
                <p class="font-semibold text-slate-900 dark:text-white">Duyệt HITL Storyboard</p>
                <p class="text-slate-500">Xem kịch bản Hook, Lời thoại, Âm nhạc và yêu cầu sửa nếu cần.</p>
              </div>
            </div>

            <div class="flex items-start gap-2.5">
              <span class="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-indigo-600 text-[10px] font-bold text-white">3</span>
              <div>
                <p class="font-semibold text-slate-900 dark:text-white">Xem Preview 9:16 & Tải Video</p>
                <p class="text-slate-500">Kiểm tra safe zone TikTok trước khi chạy quảng cáo.</p>
              </div>
            </div>
          </div>
        </UCard>
      </div>
    </div>
  </div>
</template>

