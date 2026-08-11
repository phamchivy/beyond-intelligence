using FastEndpoints;

namespace AIHackathonApi.Endpoints;

public class ExecuteRequest
{
    public string DecisionId { get; set; } = string.Empty;
    public string Action { get; set; } = "APPROVE"; // APPROVE hoặc REJECT
}

public class ExecuteResponse
{
    public string WorkflowStatus { get; set; } = string.Empty;
    public string Message { get; set; } = string.Empty;
    public DateTime ExecutedAt { get; set; }
}

public class ExecuteWorkflowEndpoint : Endpoint<ExecuteRequest, ExecuteResponse>
{
    public override void Configure()
    {
        Post("/api/v1/workflow/execute");
        AllowAnonymous();
    }

    public override async Task HandleAsync(ExecuteRequest req, CancellationToken ct)
    {
      if (req.Action.ToUpper() == "APPROVE")
      {
        var res = new ExecuteResponse
        {
          WorkflowStatus = "COMPLETED",
          Message = "Đã phê duyệt! Hệ thống đã tự động cập nhật giá niêm yết và điều chỉnh campaign TikTok Ads.",
          ExecutedAt = DateTime.UtcNow
        };
        await HttpContext.Response.WriteAsJsonAsync(res, cancellationToken: ct);
      }
      else
      {
        var res = new ExecuteResponse
        {
          WorkflowStatus = "REJECTED",
          Message = "Đã từ chối quyết định. Luồng công việc dừng lại.",
          ExecutedAt = DateTime.UtcNow
        };
        await HttpContext.Response.WriteAsJsonAsync(res, cancellationToken: ct);
      }
    }
}