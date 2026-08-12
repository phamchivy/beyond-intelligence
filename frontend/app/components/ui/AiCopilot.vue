<script setup>
import { ref } from 'vue'

const isOpen = ref(false)
const inputQuery = ref('')
const isTyping = ref(false)

const messages = ref([
  { role: 'bot', text: 'Xin chào! Tôi là AI Copilot. Tôi có thể giúp gì cho chiến dịch E-commerce toàn cầu của bạn hôm nay?' }
])

const status = ref('online') // 'online' | 'offline' | 'typing'

const promptSuggestions = [
  'Phân tích rủi ro thị trường EU',
  'Tối ưu nội dung cho Nhật Bản',
  'Dự báo doanh thu tháng tới'
]

const handleSend = () => {
  if (!inputQuery.value.trim()) return
  
  messages.value.push({ role: 'user', text: inputQuery.value })
  const tempQuery = inputQuery.value
  inputQuery.value = ''
  isTyping.value = true
  
  setTimeout(() => {
    isTyping.value = false
    messages.value.push({ 
      role: 'bot', 
      text: `Dựa trên dữ liệu thời gian thực, yêu cầu "${tempQuery}" của bạn đang được xử lý tối ưu...` 
    })
  }, 1000)
}
</script>

<template>
  <div>
    <USlideover 
      v-model="isOpen"
      :dismissible="false"
      :unmount-on-hide="false"
    >
      <UButton
        icon="i-heroicons-sparkles"
        size="xl"
        color="primary"
        class="fixed bottom-6 right-6 shadow-xl rounded-full z-40 animate-bounce"
        @click="isOpen = true"
      />
      <template #title>
        <h3 class="text-base font-semibold flex items-center gap-2">
          <!-- <UIcon name="i-heroicons-sparkles" class="primary"/> -->
          AI Copilot
        </h3>
      </template>

      <template #body>
        <UChatMessages :messages="messages" :status="status" />

        <div class="p-2 flex flex-wrap gap-2 dark:bg-gray-900">
          <UBadge 
            v-for="prompt in promptSuggestions" 
            :key="prompt" 
            color="gray" 
            variant="solid" 
            class="cursor-pointer hover:bg-gray-200 dark:hover:bg-gray-700"
            @click="inputQuery = prompt"
          >
            {{ prompt }}
          </UBadge>
        </div>
      </template>

      <template #footer>
        <form @submit.prevent="handleSend" class="flex gap-2 w-full">
          <UInput v-model="inputQuery" placeholder="Nhập lệnh điều khiển..." class="flex-1" />
          <UButton type="submit" icon="i-heroicons-paper-airplane" color="primary" :disabled="!inputQuery" />
        </form>
      </template>
    </USlideover>
  </div>
</template>