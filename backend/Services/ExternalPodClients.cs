using System;
using System.Collections.Generic;
using System.IO;
using System.Net.Http;
using System.Net.Http.Json;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;
using AIHackathonApi.Models.DTOs;
using Microsoft.AspNetCore.Http;
using Microsoft.Extensions.Logging;

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
    Task<AgentStoryboardResponse> ReviseStoryboardAsync(Guid taskId, string feedback, CancellationToken ct);
    Task<AgentRenderTriggerResponse> TriggerRenderAsync(Guid taskId, CancellationToken ct);
    Task<AgentRenderStatusResponse> GetRenderStatusAsync(string jobId, CancellationToken ct);
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
        HttpResponseMessage response;
        try
        {
            response = await _http.PostAsJsonAsync("/agent/reasoning/storyboard", req, ct);
        }
        catch (Exception ex)
        {
            _logger.LogWarning(ex, "Agent Pod chưa sẵn sàng, kích hoạt Mock Storyboard.");
            return MockStoryboard(req.TaskId, 1);
        }

        using (response)
        {
            if (!response.IsSuccessStatusCode)
            {
                var error = await response.Content.ReadAsStringAsync(ct);
                _logger.LogError("Agent Pod Error {Status}: {Detail}", response.StatusCode, error);
                return MockStoryboard(req.TaskId, 1);
            }

            var options = new JsonSerializerOptions { PropertyNameCaseInsensitive = true };
            var result = await response.Content.ReadFromJsonAsync<AgentStoryboardResponse>(options, ct);

            return result ?? throw new InvalidOperationException("Agent Pod trả về dữ liệu rỗng.");
        }
    }

    public async Task<AgentStoryboardResponse> ReviseStoryboardAsync(Guid taskId, string feedback, CancellationToken ct)
    {
        try
        {
            var payload = new AgentReviseStoryboardRequest
            {
                TaskId = taskId.ToString(),
                Feedback = feedback
            };

            using var response = await _http.PostAsJsonAsync("/agent/reasoning/storyboard/revise", payload, ct);

            if (!response.IsSuccessStatusCode)
            {
                var errorDetail = await response.Content.ReadAsStringAsync(ct);
                _logger.LogError("Agent Pod Revise trả về lỗi {StatusCode}: {ErrorDetail}", response.StatusCode, errorDetail);
                return MockStoryboard(taskId.ToString(), 2);
            }

            var options = new JsonSerializerOptions { PropertyNameCaseInsensitive = true };
            var result = await response.Content.ReadFromJsonAsync<AgentStoryboardResponse>(options, cancellationToken: ct);

            return result ?? MockStoryboard(taskId.ToString(), 2);
        }
        catch (Exception ex)
        {
            _logger.LogWarning(ex, "Agent Pod Revise chưa sẵn sàng, kích hoạt Mock Revision.");
            return MockStoryboard(taskId.ToString(), 2);
        }
    }

    public async Task<AgentRenderTriggerResponse> TriggerRenderAsync(Guid taskId, CancellationToken ct)
    {
        try
        {
            var payload = new AgentRenderTriggerRequest
            {
                TaskId = taskId.ToString()
            };
            var res = await _http.PostAsJsonAsync("/agent/render", payload, ct);
            res.EnsureSuccessStatusCode();
            return (await res.Content.ReadFromJsonAsync<AgentRenderTriggerResponse>(cancellationToken: ct))!;
        }
        catch (Exception ex)
        {
            _logger.LogWarning(ex, "Agent Render chưa sẵn sàng, kích hoạt Mock Job ID.");
            return new AgentRenderTriggerResponse
            {
                RenderJobId = Guid.NewGuid().ToString(),
                Status = "queued"
            };
        }
    }

    public async Task<AgentRenderStatusResponse> GetRenderStatusAsync(string jobId, CancellationToken ct)
    {
        try
        {
            using var response = await _http.GetAsync($"/agent/render/{jobId}", ct);

            if (!response.IsSuccessStatusCode)
            {
                var errorDetail = await response.Content.ReadAsStringAsync(ct);
                _logger.LogError("Agent Pod trả về lỗi {StatusCode}: {ErrorDetail}", response.StatusCode, errorDetail);

                return new AgentRenderStatusResponse
                {
                    RenderJobId = jobId,
                    Status = "queued"
                };
            }

            var result = await response.Content.ReadFromJsonAsync<AgentRenderStatusResponse>(cancellationToken: ct);

            return result ?? new AgentRenderStatusResponse
            {
                RenderJobId = jobId,
                Status = "queued"
            };
        }
        catch (Exception ex)
        {
            _logger.LogWarning(ex, "Agent Render status chưa sẵn sàng, giữ queued.");
            return new AgentRenderStatusResponse
            {
                RenderJobId = jobId,
                Status = "queued"
            };
        }
    }

    static AgentStoryboardResponse MockStoryboard(string taskId, int revision) => new()
    {
        TaskId = taskId,
        RevisionNumber = revision,
        Plan = new
        {
            hook = new { text = "Mock hook", duration_seconds = 3 },
            shots = Array.Empty<object>(),
            cta = new { text = "Shop Now", duration_seconds = 2 }
        }
    };
}