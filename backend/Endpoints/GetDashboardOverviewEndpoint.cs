using FastEndpoints;
using System.Text.Json;

namespace AIHackathonApi.Endpoints;

public class OverviewResponse
{
    public double TotalRevenue { get; set; }
    public double ProfitMargin { get; set; }
    public int ActiveCampaigns { get; set; }
    public string RiskLevel { get; set; } = "MEDIUM";
}

public class GetDashboardOverviewEndpoint : EndpointWithoutRequest<OverviewResponse>
{
    public override void Configure()
    {
        Get("/api/v1/dashboard/overview");
        AllowAnonymous();
    }

    public override async Task HandleAsync(CancellationToken ct)
    {
        var resp = new OverviewResponse
        {
            TotalRevenue = 45200.50,
            ProfitMargin = 22.4,
            ActiveCampaigns = 8,
            RiskLevel = "MEDIUM"
        };

        // HttpContext.Response.ContentType = "application/json";
        // HttpContext.Response.StatusCode = 200;
        // await JsonSerializer.SerializeAsync(HttpContext.Response.Body, resp, cancellationToken: ct);
        await HttpContext.Response.WriteAsJsonAsync(resp, cancellationToken: ct);
    }
}