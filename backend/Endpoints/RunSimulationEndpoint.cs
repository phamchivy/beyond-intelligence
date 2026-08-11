using FastEndpoints;

namespace AIHackathonApi.Endpoints;

public class SimulationRequest
{
    public double PriceChange { get; set; } // Ví dụ: -1.5 ($)
    public double AdsBudget { get; set; }   // Ví dụ: 350 ($/ngày)
}

public class SimulationResponse
{
    public double ProjectedRevenue { get; set; }
    public double ProjectedProfit { get; set; }
    public List<ChartDataPoint> ChartData { get; set; } = new();
}

public class ChartDataPoint
{
    public string Day { get; set; } = string.Empty;
    public double Baseline { get; set; }
    public double Simulated { get; set; }
}

public class RunSimulationEndpoint : Endpoint<SimulationRequest, SimulationResponse>
{
    public override void Configure()
    {
        Post("/api/v1/simulation/run");
        AllowAnonymous();
    }

    public override async Task HandleAsync(SimulationRequest req, CancellationToken ct)
    {
        // Công thức tính toán mô phỏng (giả lập logic từ P5)
        double baseRev = 1500.0;
        double newRevPerDay = (baseRev + (req.AdsBudget * 2.2)) * (1 - (req.PriceChange * 0.05));
        double newProfitPerDay = newRevPerDay * 0.25;

        var chart = new List<ChartDataPoint>();
        for (int i = 1; i <= 7; i++)
        {
            chart.Add(new ChartDataPoint
            {
                Day = $"Day {i}",
                Baseline = Math.Round(baseRev * i, 2),
                Simulated = Math.Round(newRevPerDay * i, 2)
            });
        }

        var res = new SimulationResponse
        {
            ProjectedRevenue = Math.Round(newRevPerDay * 30, 2),
            ProjectedProfit = Math.Round(newProfitPerDay * 30, 2),
            ChartData = chart
        };
        await HttpContext.Response.WriteAsJsonAsync(res, cancellationToken: ct);
    }
}