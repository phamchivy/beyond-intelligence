// server/api/video-scan.get.ts
export default defineEventHandler(() => {
  return {
    videoId: "vid_88412",
    status: "scanned",
    metadata: {
      title: "Review sạc dự phòng 20000mAh",
      duration: 45, // giây
    },
    issues: [
      {
        id: "iss_1",
        type: "Safety",
        riskLevel: "High",
        timestamp: 12, // giây thứ 12
        description: "Phát hiện logo nền tảng đối thủ (vi phạm chính sách).",
        recommendedAction: "Tự động làm mờ (Blur) vùng tọa độ [x:120, y:40]."
      },
      {
        id: "iss_2",
        type: "Growth",
        riskLevel: "Low",
        timestamp: 30, // giây thứ 30
        description: "Thiếu Call-to-Action (CTA) ở cuối video.",
        recommendedAction: "Chèn lớp phủ (Overlay) 'Mua ngay' dựa trên lịch sử video chuyển đổi cao."
      }
    ]
  }
})