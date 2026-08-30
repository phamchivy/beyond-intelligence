export type BriefStatus = 'draft' | 'reasoning' | 'storyboard_review' | 'render_processing' | 'rendering' | 'completed' | 'done' | 'failed' | 'cancelled' | 'needs_manual_review'

export type BriefObjective = 'conversion' | 'lead' | 'traffic' | 'awareness' | 'Conversion' | 'Lead' | 'Traffic' | 'Awareness'
export type BriefChannel = 'tiktok' | 'reels' | 'meta_feed' | 'TikTok' | 'Reels' | 'Meta'

export interface BriefAsset {
  id: string
  type: 'hero' | 'closeup' | 'lifestyle' | 'variant' | 'logo' | 'detail'
  name: string
  url: string
  file?: File
}

export interface BriefForm {
  id?: string
  title?: string
  status?: BriefStatus
  productName: string
  productCategory: string
  productPrice: number | string
  productUsp: string
  productFeatures: string[] | string
  productOffer?: string
  allowedClaims?: string[] | string
  audienceProfile: {
    who?: string
    pain_points?: string[]
    needs?: string[]
    buy_reasons?: string[]
  } | string
  objective: string
  keyMessage: string
  channel: string
  aspectRatio: string
  creativeReference?: string
  maxDurationMs: number | string
  language: string
  requiredCta?: string
  bannedClaims?: string[] | string
  bannedContent?: string[] | string
  assets?: Array<File | BriefAsset>
}

export interface StoryboardScene {
  scene_number: number
  duration_ms: number
  visual_description: string
  audio_script: string
  suggested_asset?: string
}

export interface StoryboardPlan {
  scenes: StoryboardScene[]
  soundtrack?: string
  voiceover_tone?: string
  [key: string]: any
}

export interface SubmitBriefResponse {
  taskId: string
  storyboardId: string
  revisionNumber: number
  plan: StoryboardPlan
  taskStatus: string
}

export type ReviewDecision = 'approved' | 'needs_revision' | 'rejected'

export interface StoryboardReviewPayload {
  taskId: string
  storyboardId: string
  decision: ReviewDecision
  feedback?: string
}

export interface StoryboardReviewResponse {
  status: string
  render_job_id?: string
  storyboard_id?: string
  revision_number?: number
  plan?: StoryboardPlan
  message?: string
}

export interface RenderStatusResponse {
  status: 'queued' | 'processing' | 'completed' | 'failed'
  video_url?: string
  error?: any
}

export interface DashboardOverviewResponse {
  totalRevenue: number
  profitMargin: number
  activeCampaigns: number
  riskLevel: string
}

export interface VideoResult {
  id: string
  taskId?: string
  title: string
  status: 'completed' | 'processing' | 'failed'
  duration: string
  platform: string
  ratio: string
  downloadUrl: string
  previewUrl: string
  createdAt?: string
}

