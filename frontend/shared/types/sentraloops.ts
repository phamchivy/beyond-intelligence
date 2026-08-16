export type SeverityLevel = 'critical' | 'warning' | 'info'
export type TrackType = 'safety' | 'growth'
export type DecisionStatus = 'pending' | 'approved' | 'rejected'

export interface ViolationTimestamp {
  id: string
  timeInSeconds: number
  timestampFormatted: string
  label: string
  severity: SeverityLevel
  ruleCode: string
  description: string
  thumbnailUrl?: string
}

export interface DecisionItem {
  id: string
  videoId: string
  track: TrackType
  title: string
  description: string
  confidenceScore: number
  status: DecisionStatus
  impact: string
  suggestedAction: string
  diffOriginal?: string
  diffProposed?: string
  evidenceId: string
  createdAt: string
}

export interface EvidenceDetails {
  id: string
  policyRef: string
  policyTitle: string
  policyExcerpt: string
  platform: 'TikTok' | 'Meta' | 'YouTube Shorts'
  lakehouseMetric: {
    name: string
    baseline: number
    projected: number
    unit: string
    sampleSize: string
  }
  agentRationale: string
  confidenceFactors: { factor: string; score: number }[]
}

export interface VideoScanDetail {
  id: string
  title: string
  duration: number
  videoUrl: string
  status: 'scanning' | 'ready' | 'mitigated'
  safetyRiskScore: number
  growthPotentialScore: number
  timestamps: ViolationTimestamp[]
  decisions: DecisionItem[]
  metadata: {
    category: string
    targetMarket: string
    caption: string
    resolution: string
  }
}

export interface VideoUploadPayload {
  videoFile: File
  productTitle: string
  productCategory: string
  targetMarket: string
}

export interface VideoUploadResponse {
  analysisId: string
  videoUrl: string
  fileSizeBytes: number
  status: 'PROCESSING' | 'COMPLETED' | 'FAILED' | string
  message: string
}