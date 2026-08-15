namespace AIHackathonApi.Models
{
  public class UploadVideoRequest
  {
    public IFormFile VideoFile { get; set; } = default!;
    public string ProductTitle { get; set; } = string.Empty;
    public string ProductCategory { get; set; } = string.Empty;
    public string TargetMarket { get; set; } = "US";
  }

  public class UploadVideoResponse
  {
    public string AnalysisId { get; set; } = string.Empty;
    public string VideoUrl { get; set; } = string.Empty;
    public long FileSizeBytes { get; set; }
    public string Status { get; set; } = "PROCESSING";
    public string Message { get; set; } = string.Empty;
  }
}

