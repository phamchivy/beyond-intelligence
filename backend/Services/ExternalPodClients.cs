using System.Net.Http.Json;
using AIHackathonApi.Models.DTOs;

namespace AIHackathonApi.Services;

public interface IDataPodClient
{
    Task<DataProcessAssetsResponse> ProcessAssetsAsync(Guid taskId, List<IFormFile> files, CancellationToken ct);
    Task<DataSaveVideoResponse> SavePermanentVideoAsync(Guid taskId, string renderJobId, string tempUrl, CancellationToken ct);
}

public class DataPodClient : IDataPodClient
{
    private readonly HttpClient _http;
    private readonly ILogger<DataPodClient> _logger;

    public DataPodClient(IHttpClientFactory factory, ILogger<DataPodClient> logger)
    {
        _http = factory.CreateClient("DataPod");
        _logger = logger;
    }

    public async Task<DataProcessAssetsResponse> ProcessAssetsAsync(Guid taskId, List<IFormFile> files, CancellationToken ct)
    {
        try
        {
            using var content = new MultipartFormDataContent();
            content.Add(new StringContent(taskId.ToString()), "task_id");
            foreach (var file in files)
            {
                var stream = new StreamContent(file.OpenReadStream());
                stream.Headers.ContentType = new(file.ContentType);
                content.Add(stream, "files", file.FileName);
            }

            var res = await _http.PostAsync("/data/assets/process", content, ct);
            res.EnsureSuccessStatusCode();
            return (await res.Content.ReadFromJsonAsync<DataProcessAssetsResponse>(cancellationToken: ct))!;
        }
        catch (Exception ex)
        {
            _logger.LogWarning(ex, "Data Pod chưa sẵn sàng, kích hoạt Mock Asset Base64.");
            var fallback = new DataProcessAssetsResponse();
            foreach (var file in files)
            {
                using var ms = new MemoryStream();
                await file.CopyToAsync(ms, ct);
                fallback.Assets.Add(new DataAssetItemDto
                {
                    AssetRole = "hero",
                    MimeType = file.ContentType,
                    ContentBase64 = Convert.ToBase64String(ms.ToArray()),
                    ObjectRef = $"processed-assets/{taskId}/{Guid.NewGuid()}_hero.jpg"
                });
            }
            return fallback;
        }
    }

    public async Task<DataSaveVideoResponse> SavePermanentVideoAsync(Guid taskId, string renderJobId, string tempUrl, CancellationToken ct)
    {
        try
        {
            var payload = new { task_id = taskId, render_job_id = renderJobId, source_temp_url = tempUrl };
            var res = await _http.PostAsJsonAsync("/data/videos/save", payload, ct);
            res.EnsureSuccessStatusCode();
            return (await res.Content.ReadFromJsonAsync<DataSaveVideoResponse>(cancellationToken: ct))!;
        }
        catch (Exception ex)
        {
            _logger.LogWarning(ex, "Data Pod Save Video chưa sẵn sàng, trả về mock URL.");
            return new DataSaveVideoResponse
            {
                ObjectRef = $"rendered-videos/{taskId}/{renderJobId}.mp4",
                FinalUrl = tempUrl
            };
        }
    }
}

public interface IAgentPodClient
{
    Task<AgentStoryboardResponse> GenerateStoryboardAsync(AgentStoryboardRequest req, CancellationToken ct);
    Task<AgentStoryboardResponse> RegenerateStoryboardAsync(Guid taskId, string feedback, CancellationToken ct);
    Task<AgentRenderTriggerResponse> TriggerRenderAsync(Guid taskId, Guid storyboardId, CancellationToken ct);
    Task<AgentRenderStatusResponse> GetRenderStatusAsync(string agentJobId, CancellationToken ct);
}

public class AgentPodClient : IAgentPodClient
{
    private readonly HttpClient _http;
    private readonly ILogger<AgentPodClient> _logger;

    public AgentPodClient(IHttpClientFactory factory, ILogger<AgentPodClient> logger)
    {
        _http = factory.CreateClient("AgentPod");
        _logger = logger;
    }

    public async Task<AgentStoryboardResponse> GenerateStoryboardAsync(AgentStoryboardRequest req, CancellationToken ct)
    {
        try
        {
            var res = await _http.PostAsJsonAsync("/agent/reasoning/storyboard", req, ct);
            res.EnsureSuccessStatusCode();
            return (await res.Content.ReadFromJsonAsync<AgentStoryboardResponse>(cancellationToken: ct))!;
        }
        catch (Exception ex)
        {
            _logger.LogWarning(ex, "Agent Pod chưa sẵn sàng, kích hoạt Mock Storyboard.");
            return new AgentStoryboardResponse
            {
                TaskId = req.TaskId,
                RevisionNumber = 1,
                Confidence = 0.88m,
                ComplianceReport = new { passed = true, violations = Array.Empty<object>() },
                StoryboardPlan = new
                {
                    hook = new { text = "Bí quyết chống ồn đỉnh cao cho cả ngày năng động!", duration_seconds = 3 },
                    shots = new[]
                    {
                        new { order = 1, scene_description = "Cận cảnh sản phẩm sắc nét", motion = "zoom_in", overlay_text = "Chống ồn ANC 35dB", duration_seconds = 4, reference_asset_role = "hero" },
                        new { order = 2, scene_description = "Trải nghiệm nghe nhạc ngoài phố", motion = "pan_right", overlay_text = "Pin bền 30 giờ", duration_seconds = 4, reference_asset_role = "hero" }
                    },
                    cta = new { text = "Mua ngay hôm nay - Giảm 30%", duration_seconds = 2 }
                }
            };
        }
    }

    public async Task<AgentStoryboardResponse> RegenerateStoryboardAsync(Guid taskId, string feedback, CancellationToken ct)
    {
        try
        {
            var res = await _http.PostAsJsonAsync("/agent/reasoning/storyboard/regenerate", new { task_id = taskId, feedback }, ct);
            res.EnsureSuccessStatusCode();
            return (await res.Content.ReadFromJsonAsync<AgentStoryboardResponse>(cancellationToken: ct))!;
        }
        catch (Exception ex)
        {
            _logger.LogWarning(ex, "Agent Pod Regenerate chưa sẵn sàng, kích hoạt Mock Revision.");
            return new AgentStoryboardResponse
            {
                TaskId = taskId,
                RevisionNumber = 2,
                Confidence = 0.92m,
                ComplianceReport = new { passed = true, violations = Array.Empty<object>() },
                StoryboardPlan = new
                {
                    hook = new { text = $"[Đã cập nhật theo góp ý: {feedback}] Âm thanh đỉnh chóp!", duration_seconds = 3 },
                    shots = new[]
                    {
                        new { order = 1, scene_description = "Cận cảnh vỏ hộp và tai nghe", motion = "zoom_in", overlay_text = "Thiết kế cao cấp", duration_seconds = 5, reference_asset_role = "hero" }
                    },
                    cta = new { text = "Sở hữu ngay", duration_seconds = 2 }
                }
            };
        }
    }

    public async Task<AgentRenderTriggerResponse> TriggerRenderAsync(Guid taskId, Guid storyboardId, CancellationToken ct)
    {
        try
        {
            var res = await _http.PostAsJsonAsync("/agent/render", new { task_id = taskId, storyboard_id = storyboardId }, ct);
            res.EnsureSuccessStatusCode();
            return (await res.Content.ReadFromJsonAsync<AgentRenderTriggerResponse>(cancellationToken: ct))!;
        }
        catch (Exception ex)
        {
            _logger.LogWarning(ex, "Agent Render chưa sẵn sàng, kích hoạt Mock Job ID.");
            return new AgentRenderTriggerResponse { RenderJobId = Guid.NewGuid().ToString() };
        }
    }

    public async Task<AgentRenderStatusResponse> GetRenderStatusAsync(string agentJobId, CancellationToken ct)
    {
        try
        {
            return (await _http.GetFromJsonAsync<AgentRenderStatusResponse>($"/agent/render/{agentJobId}/status", ct))!;
        }
        catch (Exception ex)
        {
            _logger.LogWarning(ex, "Agent Render Status chưa sẵn sàng, giả lập render completed.");
            return new AgentRenderStatusResponse
            {
                RenderJobId = agentJobId,
                Status = "completed",
                VideoUrl = "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4",
                QaReport = new { product_match_score = 0.95, issues = Array.Empty<string>() }
            };
        }
    }
}