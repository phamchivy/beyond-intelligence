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

        var job = await conn.QuerySingleOrDefaultAsync<dynamic>(
            "SELECT * FROM render_jobs WHERE id = @Id", new { Id = renderJobId });

        if (job == null)
        {
            HttpContext.Response.StatusCode = StatusCodes.Status404NotFound;
            await HttpContext.Response.WriteAsJsonAsync(new { message = "Không tìm thấy render job." }, cancellationToken: ct);
            return;
        }

        // Trường hợp đã hoàn tất trước đó
        if (job.status == "completed")
        {
            var cachedRes = new
            {
                status = "completed",
                video_url = (string)job.temp_video_url,
                qa_report = job.qa_report
            };
            await HttpContext.Response.WriteAsJsonAsync(cachedRes, cancellationToken: ct);
            return;
        }

        // Gọi Agent Pod kiểm tra trạng thái mới nhất
        var agentStatus = await _agentPod.GetRenderStatusAsync((string)job.agent_job_id, ct);

        // Trường hợp Agent báo render thành công
        if (agentStatus.Status == "completed")
        {
            // Báo Data Pod lưu video vĩnh viễn
            var savedData = await _dataPod.SavePermanentVideoAsync((Guid)job.task_id, (string)job.agent_job_id, agentStatus.VideoUrl!, ct);

            // Cập nhật Postgres
            await conn.ExecuteAsync(@"
                UPDATE render_jobs 
                SET status = 'completed', 
                    temp_video_url = @FinalUrl, 
                    final_object_ref = @ObjectRef, 
                    qa_report = @QaReport::jsonb, 
                    completed_at = now() 
                WHERE id = @Id;
                UPDATE tasks SET status = 'completed' WHERE id = @TaskId;", new
            {
                Id = renderJobId,
                job.task_id,
                savedData.FinalUrl,
                savedData.ObjectRef,
                QaReport = JsonSerializer.Serialize(agentStatus.QaReport)
            });

            var completedRes = new
            {
                status = "completed",
                video_url = savedData.FinalUrl,
                qa_report = agentStatus.QaReport
            };
            await HttpContext.Response.WriteAsJsonAsync(completedRes, cancellationToken: ct);
            return;
        }

        // Trường hợp Agent báo render thất bại
        if (agentStatus.Status == "failed")
        {
            await conn.ExecuteAsync(@"
                UPDATE render_jobs SET status = 'failed' WHERE id = @Id;
                UPDATE tasks SET status = 'failed' WHERE id = @TaskId;", new { Id = renderJobId, job.task_id });

            var failedRes = new { status = "failed" };
            await HttpContext.Response.WriteAsJsonAsync(failedRes, cancellationToken: ct);
            return;
        }

        // Trường hợp đang xử lý (queued / processing)
        var processingRes = new { status = (string)agentStatus.Status };
        await HttpContext.Response.WriteAsJsonAsync(processingRes, cancellationToken: ct);
    }
}