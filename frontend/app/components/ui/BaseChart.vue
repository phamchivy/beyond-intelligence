<script setup>
import { computed } from 'vue'
import { useColorMode } from '#imports'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart, BarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'

// Đăng ký các module cần thiết của ECharts
use([CanvasRenderer, LineChart, BarChart, GridComponent, TooltipComponent, LegendComponent])

const props = defineProps({
  title: {
    type: String,
    default: 'Chart Title'
  },
  option: {
    type: Object,
    required: true
  }
})

const colorMode = useColorMode()

function getThemeColors() {
  const style = getComputedStyle(document.documentElement)
  return {
    primary: style.getPropertyValue('--ui-primary').trim(),
    secondary: style.getPropertyValue('--ui-secondary').trim(),
    success: style.getPropertyValue('--ui-success').trim(),
    text: style.getPropertyValue('--ui-text').trim(),
    border: style.getPropertyValue('--ui-border').trim()
  }
}

const themeColors = computed(() => colorMode.value === 'dark' ? 'dark' : 'light')

const computedOption = computed(() => {
  const colors = getThemeColors()
  return {
    backgroundColor: 'transparent',
    color: [colors.primary, colors.secondary, colors.success],
    ...props.option
  }
})
</script>

<template>
  <UCard :ui="{ body: { padding: 'p-0 sm:p-0' } }">
    <template #header>
      <h3 class="text-base font-semibold text-gray-900 dark:text-white">
        {{ title }}
      </h3>
    </template>
    
    <div class="h-75 w-full p-4">
      <ClientOnly>
        <VChart :option="computedOption" :theme="themeColors" autoresize />
        <template #fallback>
          <div class="flex items-center justify-center h-full w-full">
            <UIcon name="i-heroicons-arrow-path" class="animate-spin text-3xl text-gray-400" />
          </div>
        </template>
      </ClientOnly>
    </div>
  </UCard>
</template>