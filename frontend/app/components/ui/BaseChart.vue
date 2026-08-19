<script setup lang="ts">
import type { EChartsOption } from 'echarts'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart, BarChart, PieChart } from 'echarts/charts'
import {
  GridComponent,
  TooltipComponent,
  LegendComponent,
  TitleComponent
} from 'echarts/components'

use([
  CanvasRenderer,
  LineChart,
  BarChart,
  PieChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
  TitleComponent
])

interface Props {
  title?: string
  description?: string
  option: EChartsOption
  loading?: boolean
  height?: string
}

const props = withDefaults(defineProps<Props>(), {
  title: '',
  description: '',
  loading: false,
  height: '320px'
})

const colorMode = useColorMode()
const isDark = computed(() => colorMode.value === 'dark')

// Tự động tinh chỉnh Palette và Grid theo Color Mode
const themeAdaptedOption = computed<EChartsOption>(() => {
  const textColor = isDark.value ? '#a1a1aa' : '#52525b'
  const splitLineColor = isDark.value ? '#27272a' : '#f1f5f9'

  return {
    backgroundColor: 'transparent',
    textStyle: {
      fontFamily: 'Inter, sans-serif'
    },
    grid: {
      top: 30,
      right: 20,
      bottom: 25,
      left: 45,
      containLabel: true
    },
    tooltip: {
      backgroundColor: isDark.value ? '#18181b' : '#ffffff',
      borderColor: isDark.value ? '#3f3f46' : '#e4e4e7',
      textStyle: {
        color: isDark.value ? '#fafafa' : '#09090b',
        fontSize: 12
      }
    },
    ...props.option,
    xAxis: Array.isArray(props.option.xAxis)
      ? props.option.xAxis
      : {
          ...props.option.xAxis,
          axisLine: { lineStyle: { color: splitLineColor } },
          axisLabel: { color: textColor }
        },
    yAxis: Array.isArray(props.option.yAxis)
      ? props.option.yAxis
      : {
          ...props.option.yAxis,
          splitLine: { lineStyle: { color: splitLineColor } },
          axisLabel: { color: textColor }
        }
  }
})
</script>

<template>
  <UCard>
    <template v-if="title || $slots.header" #header>
      <div class="flex items-center justify-between">
        <div>
          <h3 class="font-semibold text-highlighted text-sm">{{ title }}</h3>
          <p v-if="description" class="text-xs text-muted mt-0.5">{{ description }}</p>
        </div>
        <slot name="actions" />
      </div>
    </template>

    <div :style="{ height }" class="w-full relative">
      <div v-if="loading" class="absolute inset-0 z-10 flex flex-col gap-3 justify-center p-4 bg-elevated/80 backdrop-blur-xs">
        <USkeleton class="h-6 w-1/3" />
        <USkeleton class="h-full w-full rounded-lg" />
      </div>
      <VChart
        v-else
        :option="themeAdaptedOption"
        autoresize
        class="w-full h-full"
      />
    </div>
  </UCard>
</template>