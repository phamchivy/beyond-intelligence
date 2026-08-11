using FastEndpoints;

namespace AIHackathonApi.Endpoints;
public class DecisionResponse
{
    public string DecisionId { get; set; } = string.Empty;
    public string Recommendation { get; set; } = string.Empty;
    public double Confidence { get; set; }
    public string ExpectedImpact { get; set; } = string.Empty;
    public List<string> Evidences { get; set; } = new();
    public List<TraceLog> ExecutionTrace { get; set; } = new();
}

public class TraceLog
{
    public string Component { get; set; } = string.Empty;
    public string Status { get; set; } = string.Empty;
    public int LatencyMs { get; set; }
}

public class GetDecisionEndpoint : EndpointWithoutRequest<DecisionResponse>
{
    public override void Configure()
    {
        Get("/api/v1/decision/latest");
        AllowAnonymous();
    }

    public override async Task HandleAsync(CancellationToken ct)
    {
        var res = new DecisionResponse
        {
            DecisionId = "DEC-2026-0812",
            Recommendation = "Giảm giá bán $1.5/sản phẩm và tăng $150/ngày ngân sách Ads TikTok ngách Outdoor.",
            Confidence = 0.88,
            ExpectedImpact = "+$2,400 Profit/Month | +12% Market Share",
            Evidences = new List<string>
            {
                "Data Ingest (P1): Giá đối thủ A vừa giảm 8% trên Amazon US.",
                "Knowledge (P2): Lịch sử đợt Tháng 6 cho thấy giảm giá $1.5 giúp CR tăng 2.3 lần.",
                "Simulation (P5): Kịch bản này có tỷ lệ Rủi ro Tồn kho thấp nhất (12%)."
            },
            ExecutionTrace = new List<TraceLog>
            {
                new TraceLog { Component = "P1_DataIntelligence", Status = "SUCCESS", LatencyMs = 120 },
                new TraceLog { Component = "P2_KnowledgeIntelligence", Status = "SUCCESS", LatencyMs = 85 },
                new TraceLog { Component = "P3_AIIntelligence", Status = "SUCCESS", LatencyMs = 340 },
                new TraceLog { Component = "P5_SimulationEngine", Status = "SUCCESS", LatencyMs = 210 }
            }
        };
        await HttpContext.Response.WriteAsJsonAsync(res, cancellationToken: ct);
    }
}