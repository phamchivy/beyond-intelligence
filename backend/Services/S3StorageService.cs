using Amazon;
using Amazon.S3;
using Amazon.S3.Transfer;
using AIHackathonApi.Models.DTOs;

namespace AIHackathonApi.Services;

public interface IS3StorageService
{
    Task<List<DataAssetItemDto>> UploadAssetsToS3Async(Guid taskId, List<IFormFile> files, CancellationToken ct);
}

public class S3StorageService : IS3StorageService
{
  private readonly IAmazonS3 _s3Client;
  private readonly string _bucketName;

  public S3StorageService(IConfiguration config)
  {
    var awsSection = config.GetSection("AWS");
    var accessKey = awsSection["AccessKey"];
    var secretKey = awsSection["SecretKey"];
    var regionName = awsSection["Region"] ?? "ap-southeast-1";
    _bucketName = awsSection["BucketName"] ?? "raw-assets";

    var region = RegionEndpoint.GetBySystemName(regionName);
    _s3Client = new AmazonS3Client(accessKey, secretKey, region);
  }

  public async Task<List<DataAssetItemDto>> UploadAssetsToS3Async(Guid taskId, List<IFormFile> files, CancellationToken ct)
  {
    var resultList = new List<DataAssetItemDto>();
    using var fileTransferUtility = new TransferUtility(_s3Client);

    foreach (var file in files)
    {
        var assetId = Guid.NewGuid();
        var extension = Path.GetExtension(file.FileName);
        // Chuẩn key: {task_id}/{asset_id}.{ext}
        var s3Key = $"{taskId}/{assetId}{extension}";

        using var memoryStream = new MemoryStream();
        await file.CopyToAsync(memoryStream, ct);
        memoryStream.Position = 0;

        // 1. Đẩy file vật lý lên AWS S3 Bucket
        await fileTransferUtility.UploadAsync(new TransferUtilityUploadRequest
        {
            InputStream = memoryStream,
            Key = s3Key,
            BucketName = _bucketName,
            ContentType = file.ContentType
        }, ct);

        // 2. Chuyển đổi sang Base64 để gửi Agent Pod
        var base64Content = Convert.ToBase64String(memoryStream.ToArray());

        resultList.Add(new DataAssetItemDto
        {
            AssetRole = "hero",
            MimeType = file.ContentType,
            ContentBase64 = base64Content,
            ObjectRef = $"{_bucketName}/{s3Key}"
        });
    }

    return resultList;
  }
}