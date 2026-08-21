namespace AIHackathonApi.Models.DTOs;

// Request JSON tạo Brief
public class CreateBriefJsonRequest
{
  public string ProductName { get; set; } = default!;
  public string? ProductCategory { get; set; }
  public decimal? ProductPrice { get; set; }
  public string? ProductUsp { get; set; }
  public List<string>? ProductFeatures { get; set; }
  public string? ProductOffer { get; set; }
  public List<string>? AllowedClaims { get; set; }

  public object AudienceProfile { get; set; } = default!; // {who, pain_points, needs, buy_reasons}

  public string Objective { get; set; } = default!;      // conversion | lead | traffic | awareness
  public string KeyMessage { get; set; } = default!;
  public string Channel { get; set; } = default!;        // tiktok | reels | meta_feed
  public string AspectRatio { get; set; } = "9:16";

  public object? CreativeReference { get; set; }

  public int MaxDurationMs { get; set; } = 30000;
  public string Language { get; set; } = "vi";
  public string? RequiredCta { get; set; }
  public List<string>? BannedClaims { get; set; }
  public List<string>? BannedContent { get; set; }
}

public class CreateBriefJsonResponse
{
  public Guid Id { get; set; }
  public string Status { get; set; } = "draft";
  public string Message { get; set; } = "Brief created successfully.";
}

// Request Multipart Upload Asset
public class UploadAssetRequest
{
  public Guid BriefId { get; set; }
  public string AssetType { get; set; } = "hero"; // hero | closeup | lifestyle | variant | logo
  public IFormFile File { get; set; } = default!;
}

public class UploadAssetResponse
{
  public Guid AssetId { get; set; }
  public Guid BriefId { get; set; }
  public string AssetType { get; set; } = default!;
  public string StorageKey { get; set; } = default!;
}

// Model nhận từ Data Pod
public class DataPodUploadResponse
{
  public string StorageKey { get; set; } = default!;
  public string? ProcessedKey { get; set; }
  public int? Width { get; set; }
  public int? Height { get; set; }
  public string MimeType { get; set; } = default!;
}