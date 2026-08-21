using FastEndpoints;
using Dapper;
using Npgsql;
using System.Text.Json;
using AIHackathonApi.Models.DTOs;
using AIHackathonApi.Services;

namespace AIHackathonApi.Endpoints;

public class ReviewStoryboardEndpoint : Endpoint<StoryboardReviewRequest>
{
    private readonly IAgentPodClient _agentPod;
    private readonly IConfiguration _config;
    private readonly ILogger<ReviewStoryboardEndpoint> _logger;

    public ReviewStoryboardEndpoint(IAgentPodClient agentPod, IConfiguration config, ILogger<ReviewStoryboardEndpoint> logger)
    {
        _agentPod = agentPod;
        _config = config;
        _logger = logger;
    }

    public override void Configure()
    {
        Post("/api/v1/pipeline/review-storyboard");
        AllowAnonymous();
        Summary(s => s.Summary = "Phê duyệt HITL Storyboard (approved / needs_revision / rejected)");
    }

    public override async Task HandleAsync(StoryboardReviewRequest req, CancellationToken ct)
    {
        await using var conn = new NpgsqlConnection(_config.GetConnectionString("DefaultConnection"));
        await conn.OpenAsync(ct);

        var decision = (req.Decision ?? "approved").Trim().ToLower();

        // Nhánh 1: Approved -> Trigger Render
        if (decision == "approved")
        {
            await conn.ExecuteAsync(@"
                UPDATE storyboards SET review_status = 'approved', reviewed_at = now() WHERE id = @StoryboardId;
                UPDATE tasks SET status = 'render_pending' WHERE id = @TaskId;", req);

            var renderTrigger = await _agentPod.TriggerRenderAsync(req.TaskId, ct);
            _logger.LogInformation(">>> [ReviewStoryboard] TriggerRenderAsync thành công. TaskId: {TaskId} | AgentJobId: {AgentJobId} | Status: {Status}", 
                req.TaskId, renderTrigger.RenderJobId, renderTrigger.Status);

            // Dùng trực tiếp ID từ Agent trả về (parse sang GUID để khớp kiểu cột id)
            var renderJobId = Guid.TryParse(renderTrigger.RenderJobId, out var parsedGuid) 
                ? parsedGuid 
                : Guid.NewGuid();

            await conn.ExecuteAsync(@"
                INSERT INTO render_jobs (id, task_id, storyboard_id, agent_job_id, status)
                VALUES (@Id, @TaskId, @StoryboardId, @AgentJobId, @Status);
                UPDATE tasks SET status = 'render_processing' WHERE id = @TaskId;", new
            {
                Id = renderJobId,
                req.TaskId,
                req.StoryboardId,
                AgentJobId = renderTrigger.RenderJobId,
                Status = renderTrigger.Status
            });

            var approvedRes = new 
            { 
                status = "render_processing", 
                render_job_id = renderTrigger.RenderJobId 
            };
            await HttpContext.Response.WriteAsJsonAsync(approvedRes, cancellationToken: ct);
            return;
        }

        // Nhánh 2: Needs Revision -> Sửa storyboard qua API Revise của Agent
        if (decision == "needs_revision")
        {
            var currentCount = await conn.ExecuteScalarAsync<int>(
                "SELECT COUNT(*) FROM storyboards WHERE task_id = @TaskId", new { req.TaskId });

            if (currentCount >= 3)
            {
                await conn.ExecuteAsync("UPDATE tasks SET status = 'needs_manual_review' WHERE id = @TaskId", new { req.TaskId });
                var limitRes = new { status = "needs_manual_review", message = "Đã vượt quá số lần sửa tối đa (3 lần)." };
                await HttpContext.Response.WriteAsJsonAsync(limitRes, cancellationToken: ct);
                return;
            }

            await conn.ExecuteAsync(@"
                UPDATE storyboards SET review_status = 'needs_revision', user_feedback = @Feedback, reviewed_at = now() 
                WHERE id = @StoryboardId;", req);

            var revisedStoryboard = await _agentPod.ReviseStoryboardAsync(req.TaskId, req.Feedback ?? "", ct);

            var newStoryboardId = Guid.NewGuid();
            await conn.ExecuteAsync(@"
                INSERT INTO storyboards (
                    id, task_id, revision_number, plan, confidence, review_status
                ) VALUES (
                    @Id, @TaskId, @RevisionNumber, @Plan::jsonb, 0.90, 'pending'
                );", new
            {
                Id = newStoryboardId,
                req.TaskId,
                revisedStoryboard.RevisionNumber,
                Plan = JsonSerializer.Serialize(revisedStoryboard.Plan)
            });

            var revisionRes = new
            {
                status = "storyboard_review",
                storyboard_id = newStoryboardId,
                revision_number = revisedStoryboard.RevisionNumber,
                plan = revisedStoryboard.Plan
            };
            await HttpContext.Response.WriteAsJsonAsync(revisionRes, cancellationToken: ct);
            return;
        }

        // Nhánh 3: Rejected
        await conn.ExecuteAsync(@"
            UPDATE storyboards SET review_status = 'rejected', reviewed_at = now() WHERE id = @StoryboardId;
            UPDATE tasks SET status = 'cancelled' WHERE id = @TaskId;", req);

        var rejectedRes = new { status = "cancelled" };
        await HttpContext.Response.WriteAsJsonAsync(rejectedRes, cancellationToken: ct);
    }
}