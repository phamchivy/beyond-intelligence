namespace AIHackathonApi.Models.DTOs;

// --- BƯỚC 1: FRONTEND -> BACKEND ---
public class SubmitBriefFormRequest
{
    public string ProductInfoJson { get; set; } = default!;
    public string TargetAudienceJson { get; set; } = default!;
    public string AdObjective { get; set; } = "conversion";
    public string KeyMessage { get; set; } = default!;
    public string Channel { get; set; } = "tiktok";
    public string? CreativeReferenceJson { get; set; }
    public string ConstraintsJson { get; set; } = default!;
    public List<IFormFile> Assets { get; set; } = new();
}

public class SubmitBriefResponse
{
    public Guid TaskId { get; set; }
    public Guid StoryboardId { get; set; }
    public int RevisionNumber { get; set; }
    public object StoryboardPlan { get; set; } = default!;
    public object? ComplianceReport { get; set; }
    public decimal Confidence { get; set; }
    public string TaskStatus { get; set; } = "storyboard_review";
}

// --- BƯỚC 2 & 3: BACKEND <-> DATA POD ---
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

// --- BƯỚC 4 & 5: BACKEND <-> AGENT POD ---
public class AgentStoryboardRequest
{
    public Guid TaskId { get; set; }
    public object Brief { get; set; } = default!;
    public List<AgentReferenceAssetDto> ReferenceAssets { get; set; } = new();
}

public class AgentReferenceAssetDto
{
    public string AssetRole { get; set; } = default!;
    public string MimeType { get; set; } = default!;
    public string ContentBase64 { get; set; } = default!;
}

public class AgentStoryboardResponse
{
    public Guid TaskId { get; set; }
    public int RevisionNumber { get; set; } = 1;
    public object StoryboardPlan { get; set; } = default!;
    public object? ComplianceReport { get; set; }
    public decimal Confidence { get; set; }
}

// --- BƯỚC 7: HITL REVIEW ---
public class StoryboardReviewRequest
{
    public Guid TaskId { get; set; }
    public Guid StoryboardId { get; set; }
    public string Decision { get; set; } = default!; // approved | needs_revision | rejected
    public string? Feedback { get; set; }
}

// --- BƯỚC 9, 10 & 11: RENDER & POLLING ---
public class AgentRenderTriggerResponse
{
    public string RenderJobId { get; set; } = default!;
}

public class AgentRenderStatusResponse
{
    public string RenderJobId { get; set; } = default!;
    public string Status { get; set; } = default!; // queued | processing | completed | failed
    public string? VideoUrl { get; set; }
    public object? QaReport { get; set; }
}

public class DataSaveVideoResponse
{
    public string ObjectRef { get; set; } = default!;
    public string FinalUrl { get; set; } = default!;
}