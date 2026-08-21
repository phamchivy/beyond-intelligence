using FastEndpoints;
using Dapper;
using Npgsql;
using System.Text.Json;
using AIHackathonApi.Services;

namespace AIHackathonApi.Endpoints;

public class GetRenderStatusEndpoint : EndpointWithoutRequest
{
    private readonly IAgentPodClient _agentPod;
    private readonly IDataPodClient _dataPod;
    private readonly IConfiguration _config;

    public GetRenderStatusEndpoint(IAgentPodClient agentPod, IDataPodClient dataPod, IConfiguration config)
    {
        _agentPod = agentPod;
        _dataPod = dataPod;
        _config = config;
    }

    public override void Configure()
    {
        Get("/api/v1/renders/{id}");
        AllowAnonymous();
        Summary(s => s.Summary = "Frontend Polling kiểm tra tiến trình Render và nhận kết quả Video");
    }

    public override async Task HandleAsync(CancellationToken ct)
    {
        var renderIdStr = Route<string>("id");
        if (!Guid.TryParse(renderIdStr, out var renderJobId))
        {
            HttpContext.Response.StatusCode = StatusCodes.Status400BadRequest;
            await HttpContext.Response.WriteAsJsonAsync(new { message = "ID render không đúng định dạng UUID." }, cancellationToken: ct);
            return;
        }

        await using var conn = new NpgsqlConnection(_config.GetConnectionString("DefaultConnection"));
        await conn.OpenAsync(ct);

        const string selectJobSql = @"
            SELECT 
                id, 
                task_id, 
                agent_job_id, 
                status, 
                temp_video_url
            FROM render_jobs 
            WHERE id = @Id;";

        var job = await conn.QuerySingleOrDefaultAsync<RenderJobRecord>(selectJobSql, new { Id = renderJobId });

        if (job == null)
        {
            HttpContext.Response.StatusCode = StatusCodes.Status404NotFound;
            await HttpContext.Response.WriteAsJsonAsync(new { message = "Không tìm thấy render job." }, cancellationToken: ct);
            return;
        }

        // 1. Trường hợp đã hoàn tất trước đó
        if (job.status == "completed" && !string.IsNullOrEmpty(job.temp_video_url))
        {
            var cachedRes = new
            {
                status = "completed",
                video_url = job.temp_video_url
            };
            await HttpContext.Response.WriteAsJsonAsync(cachedRes, cancellationToken: ct);
            return;
        }

        // 2. Gọi Agent Pod kiểm tra trạng thái mới nhất (/agent/render/{job_id})
        var agentStatus = await _agentPod.GetRenderStatusAsync(job.agent_job_id, ct);

        // 3. Trường hợp Agent báo render thành công
        if (agentStatus.Status == "completed")
        {
            var savedData = await _dataPod.SavePermanentVideoAsync(job.task_id, job.agent_job_id, agentStatus.VideoUrl!, ct);

            // Cập nhật Postgres
            await conn.ExecuteAsync(@"
                UPDATE render_jobs 
                SET status = 'completed', 
                    temp_video_url = @FinalUrl, 
                    final_object_ref = @ObjectRef, 
                    completed_at = now() 
                WHERE id = @Id;
                
                UPDATE tasks 
                SET status = 'completed', 
                    updated_at = now() 
                WHERE id = @TaskId;", new
            {
                Id = renderJobId,
                TaskId = job.task_id,
                FinalUrl = savedData.FinalUrl,
                ObjectRef = savedData.ObjectRef
            });

            var completedRes = new
            {
                status = "completed",
                video_url = savedData.FinalUrl
            };
            await HttpContext.Response.WriteAsJsonAsync(completedRes, cancellationToken: ct);
            return;
        }

        // 4. Trường hợp Agent báo render thất bại
        if (agentStatus.Status == "failed")
        {
            await conn.ExecuteAsync(@"
                UPDATE render_jobs 
                SET status = 'failed',
                    error_message = @ErrorMsg
                WHERE id = @Id;
                
                UPDATE tasks 
                SET status = 'failed',
                    updated_at = now() 
                WHERE id = @TaskId;", new 
            { 
                Id = renderJobId, 
                TaskId = job.task_id,
                ErrorMsg = agentStatus.Error != null ? JsonSerializer.Serialize(agentStatus.Error) : null
            });

            var failedRes = new 
            { 
                status = "failed",
                error = agentStatus.Error
            };
            await HttpContext.Response.WriteAsJsonAsync(failedRes, cancellationToken: ct);
            return;
        }

        // 5. Trường hợp đang xử lý (queued / processing)
        var processingRes = new { status = agentStatus.Status };
        await HttpContext.Response.WriteAsJsonAsync(processingRes, cancellationToken: ct);
    }

    private sealed class RenderJobRecord
    {
        public Guid id { get; set; }
        public Guid task_id { get; set; }
        public string agent_job_id { get; set; } = string.Empty;
        public string status { get; set; } = string.Empty;
        public string? temp_video_url { get; set; }
    }
}