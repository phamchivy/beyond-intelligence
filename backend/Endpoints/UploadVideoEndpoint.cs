using AIHackathonApi.Models;
using FastEndpoints;
namespace AIHackathonApi.Endpoints;

public class UploadVideoEndpoint : Endpoint<UploadVideoRequest, UploadVideoResponse>
{
  private readonly IWebHostEnvironment _env;

  public UploadVideoEndpoint(IWebHostEnvironment env)
  {
    _env = env;
  }

  public override void Configure()
  {
    Post("/api/v1/videos/upload");
    AllowAnonymous();
    AllowFileUploads(); // multipart/form-data
    Summary(s =>
    {
      s.Summary = "Upload trực tiếp file video lên hệ thống";
      s.Description = "Nhận file .mp4, .mov, lưu vào storage và khởi tạo luồng phân tích SentraLoop AI";
    });
  }

  public override async Task HandleAsync(UploadVideoRequest req, CancellationToken ct)
  {
    if (req.VideoFile == null || req.VideoFile.Length == 0)
    {
      ThrowError("File video không được để trống!", 400);
      return;
    }

    var allowedExtensions = new[] { ".mp4", ".mov", ".avi", ".webm" };
    var extension = Path.GetExtension(req.VideoFile.FileName).ToLowerInvariant();
    if (!allowedExtensions.Contains(extension))
    {
      ThrowError("Định dạng file không hỗ trợ. Vui lòng upload .mp4 hoặc .mov", 400);
      return;
    }

    string uploadsFolder = Path.Combine(_env.WebRootPath ?? Path.Combine(Directory.GetCurrentDirectory(), "wwwroot"), "uploads", "videos");
    if (!Directory.Exists(uploadsFolder))
    {
      Directory.CreateDirectory(uploadsFolder);
    }

    string analysisId = $"ANL-{DateTime.UtcNow:yyyyMMddHHmmss}-{Guid.NewGuid().ToString("N")[..6]}";
    string uniqueFileName = $"{analysisId}{extension}";
    string filePath = Path.Combine(uploadsFolder, uniqueFileName);

    using (var stream = new FileStream(filePath, FileMode.Create))
    {
      await req.VideoFile.CopyToAsync(stream, ct);
    }

    string videoUrl = $"/uploads/videos/{uniqueFileName}";

    var res = new UploadVideoResponse
    {
      AnalysisId = analysisId,
      VideoUrl = videoUrl,
      FileSizeBytes = req.VideoFile.Length,
      Status = "PROCESSING",
      Message = "Upload video thành công! Đã chuyển sang hàng đợi phân tích Agent."
    };
    await HttpContext.Response.WriteAsJsonAsync(res, cancellationToken: ct);
  
  }
}