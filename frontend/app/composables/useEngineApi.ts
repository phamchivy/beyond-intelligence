// composables/useEngineApi.ts
export const useEngineApi = () => {
  const { fetchApi } = useApi()

  // 1. GetDashboardOverviewEndpoint (View 1: KPIs)
  const getDashboardOverview = () => {
    return fetchApi<{
      totalRevenue: number
      profitMargin: number
      activeCampaigns: number
      riskLevel: string
      revenueTrend?: {
        categories: string[]
        series: Array<{ name: string; data: number[] }>
      }
    }>('/dashboard/overview')
  }

  // 2. RunSimulationEndpoint (View 2: Giả lập kịch bản What-If)
  const runSimulation = (payload: { scenarioId: string; parameters: Record<string, any> }) => {
    return fetchApi<{ simulationResult: any; status: string }>('/simulation/run', {
      method: 'POST',
      body: payload
    })
  }

  // 3. GetDecisionEndpoint (View 3 & 5: Quyết định & AI Evidence)
  const getDecision = (decisionId: string) => {
    return fetchApi<{
      id: string
      title: string
      confidence: number
      evidences: string[]
      recommendation: string
      expectedImpact: string
    }>(`/decision/latest`) // {decisionId}`) 
  }

  // 4. ExecuteWorkflowEndpoint (View 4: Phê duyệt & Trigger Action)
  const executeWorkflow = (payload: { decisionId: string; approved: boolean; comment?: string }) => {
    return fetchApi<{ success: boolean; message: string }>('/workflow/execute', {
      method: 'POST',
      body: payload
    })
  }

  return {
    getDashboardOverview,
    runSimulation,
    getDecision,
    executeWorkflow
  }
}