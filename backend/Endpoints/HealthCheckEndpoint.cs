using FastEndpoints;

namespace AIHackathonApi.Endpoints;

public class HealthCheckResponse
{
    public string Status { get; set; } = "healthy";
    public DateTime Timestamp { get; set; } = DateTime.UtcNow;
}

public class HealthCheckEndpoint : EndpointWithoutRequest<HealthCheckResponse>
{
  public override void Configure()
  {
    Get("/health");
    AllowAnonymous();
  }

  public override async Task HandleAsync(CancellationToken ct)
  {
    var res = new HealthCheckResponse();
    await HttpContext.Response.WriteAsJsonAsync(res, cancellationToken: ct);
  }
}