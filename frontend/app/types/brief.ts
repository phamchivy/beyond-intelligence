export type BriefStatus = 'draft' | 'reasoning' | 'awaiting_approval' | 'rendering' | 'done' | 'failed'

export type BriefObjective = 'Conversion' | 'Lead' | 'Traffic' | 'Awareness'
export type BriefChannel = 'TikTok' | 'Reels' | 'Meta'

export interface BriefAsset {
  id: string
  type: 'hero' | 'detail' | 'lifestyle' | 'variant' | 'logo'
  name: string
  url: string
}

export interface BriefForm {
  id: string
  title: string
  status: BriefStatus
  productName: string
  category: string
  price: string
  usp: string
  features: string
  offers: string
  allowedClaims: string
  assetTypes: string[]
  audience: string
  painPoint: string
  needs: string
  objective: BriefObjective
  keyMessage: string
  channel: BriefChannel
  creativeReference: string
  duration: string
  ratio: string
  language: string
  cta: string
  bannedClaims: string
  createdAt: string
  updatedAt: string
  assets: BriefAsset[]
}

export interface Shot {
  id: string
  role: 'hook' | 'product' | 'benefit' | 'cta'
  asset: string
  overlayText: string
  duration: number
}

export interface ComplianceWarning {
  id: string
  severity: 'low' | 'medium' | 'high'
  title: string
  message: string
}

export interface Storyboard {
  id: string
  briefId: string
  hook: string
  shots: Shot[]
  complianceWarnings: ComplianceWarning[]
  status: 'awaiting_approval' | 'approved' | 'rejected'
  generatedAt: string
}

export interface RenderStatus {
  id: string
  briefId: string
  status: 'queued' | 'rendering' | 'qa_checking' | 'done' | 'failed'
  progress: number
  currentStep: string
  updatedAt: string
}

export interface VideoResult {
  id: string
  briefId: string
  title: string
  status: 'done' | 'rendering' | 'failed'
  duration: string
  platform: string
  ratio: string
  downloadUrl: string
  previewUrl: string
  qa: {
    ratioMatch: boolean
    durationMatch: boolean
    assetVisibleRatio: number
  }
}
