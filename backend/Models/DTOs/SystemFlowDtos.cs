using System;
using System.Collections.Generic;
using System.Text.Json.Serialization;
using FastEndpoints;
using Microsoft.AspNetCore.Http;

namespace AIHackathonApi.Models.DTOs;

// ==========================================
// 1. FRONTEND <-> BACKEND DTOs
// ==========================================

public class SubmitBriefFormRequest
{
    [BindFrom("product_info")]
    public string ProductInfoJson { get; set; } = default!;

    [BindFrom("target_audience")]
    public string TargetAudienceJson { get; set; } = default!;

    [BindFrom("ad_objective")]
    public string AdObjective { get; set; } = "conversion";

    [BindFrom("key_message")]
    public string KeyMessage { get; set; } = default!;

    [BindFrom("channel")]
    public string Channel { get; set; } = "tiktok";

    [BindFrom("creative_reference")]
    public string? CreativeReferenceJson { get; set; }

    [BindFrom("constraints")]
    public string ConstraintsJson { get; set; } = default!;

    [BindFrom("assets")]
    public List<IFormFile> Assets { get; set; } = new();
}

public class SubmitBriefResponse
{
    [JsonPropertyName("task_id")]
    public Guid TaskId { get; set; }

    [JsonPropertyName("storyboard_id")]
    public Guid StoryboardId { get; set; }

    [JsonPropertyName("revision_number")]
    public int RevisionNumber { get; set; }

    [JsonPropertyName("plan")]
    public object Plan { get; set; } = default!;

    [JsonPropertyName("task_status")]
    public string TaskStatus { get; set; } = "storyboard_review";
}

public class StoryboardReviewRequest
{
    [JsonPropertyName("task_id")]
    public Guid TaskId { get; set; }

    [JsonPropertyName("storyboard_id")]
    public Guid StoryboardId { get; set; }

    [JsonPropertyName("decision")]
    public string Decision { get; set; } = "approved";

    [JsonPropertyName("feedback")]
    public string? Feedback { get; set; }
}

// ==========================================
// 2. BACKEND <-> DATA POD DTOs
// ==========================================

public class DataAssetItemDto
{
    public string AssetRole { get; set; } = "hero";
    public string MimeType { get; set; } = "image/jpeg";
    public string ContentBase64 { get; set; } = default!;
    public string ObjectRef { get; set; } = default!;
}

public class DataProcessAssetsResponse
{
    public List<DataAssetItemDto> Assets { get; set; } = new();
}

public class DataSaveVideoResponse
{
    public string ObjectRef { get; set; } = default!;
    public string FinalUrl { get; set; } = default!;
}

// ==========================================
// 3. BACKEND <-> AGENT POD DTOs (Theo đúng spec 5 API)
// ==========================================

public class AgentReferenceAssetDto
{
    [JsonPropertyName("asset_role")]
    public string AssetRole { get; set; } = "hero";

    [JsonPropertyName("mime_type")]
    public string MimeType { get; set; } = "image/jpeg";

    [JsonPropertyName("content_base64")]
    public string ContentBase64 { get; set; } = string.Empty;
}

// POST /agent/reasoning/storyboard
public class AgentStoryboardRequest
{
    [JsonPropertyName("task_id")]
    public string TaskId { get; set; } = string.Empty;

    [JsonPropertyName("brief")]
    public object Brief { get; set; } = new();

    [JsonPropertyName("reference_assets")]
    public List<AgentReferenceAssetDto> ReferenceAssets { get; set; } = new();
}

// POST /agent/reasoning/storyboard/revise
public class AgentReviseStoryboardRequest
{
    [JsonPropertyName("task_id")]
    public string TaskId { get; set; } = string.Empty;

    [JsonPropertyName("feedback")]
    public string Feedback { get; set; } = string.Empty;
}

// Response chung cho Storyboard & Revise
public class AgentStoryboardResponse
{
    [JsonPropertyName("task_id")]
    public string TaskId { get; set; } = string.Empty;

    [JsonPropertyName("revision_number")]
    public int RevisionNumber { get; set; }

    [JsonPropertyName("plan")]
    public object? Plan { get; set; }

    [JsonPropertyName("storyboard_plan")]
    public object? StoryboardPlan { get; set; }

    public object ResolvedPlan => Plan ?? StoryboardPlan ?? new { };
}

// POST /agent/render
public class AgentRenderTriggerRequest
{
    [JsonPropertyName("task_id")]
    public string TaskId { get; set; } = string.Empty;
}

public class AgentRenderTriggerResponse
{
    [JsonPropertyName("render_job_id")]
    public string RenderJobId { get; set; } = string.Empty;

    [JsonPropertyName("status")]
    public string Status { get; set; } = "queued";
}

// GET /agent/render/{job_id}
public class AgentRenderStatusResponse
{
    [JsonPropertyName("render_job_id")]
    public string RenderJobId { get; set; } = string.Empty;

    [JsonPropertyName("status")]
    public string Status { get; set; } = string.Empty; // queued | processing | completed | failed

    [JsonPropertyName("video_url")]
    public string? VideoUrl { get; set; }

    [JsonPropertyName("error")]
    public object? Error { get; set; }
}

// Cấu trúc lỗi chung từ Agent Pod
public class AgentErrorDetail
{
    [JsonPropertyName("code")]
    public string Code { get; set; } = string.Empty;

    [JsonPropertyName("message")]
    public string Message { get; set; } = string.Empty;

    [JsonPropertyName("task_id")]
    public string? TaskId { get; set; }
}

public class AgentErrorResponse
{
    [JsonPropertyName("error")]
    public AgentErrorDetail Error { get; set; } = new();
}