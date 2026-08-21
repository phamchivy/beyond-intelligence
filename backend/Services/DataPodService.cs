using Amazon;
using Amazon.S3;
using Amazon.S3.Transfer;
using AIHackathonApi.Models.DTOs;

namespace AIHackathonApi.Services;

public interface IDataPodService
{
    Task<DataPodUploadResponse> UploadToStorageAsync(IFormFile file, string assetType, CancellationToken ct);
}

public class DataPodService : IDataPodService
{
    private readonly IAmazonS3 _s3Client;
    private readonly string _bucketName;
    private readonly ILogger<DataPodService> _logger;

    public DataPodService(IConfiguration config, ILogger<DataPodService> logger)
    {
        _logger = logger;
        _bucketName = config["AWS:BucketName"] ?? "beyond-videos";

        var accessKey = config["AWS:AccessKey"];
        var secretKey = config["AWS:SecretKey"];
        var regionName = config["AWS:Region"] ?? "ap-southeast-1";
        var region = RegionEndpoint.GetBySystemName(regionName);

        _s3Client = new AmazonS3Client(accessKey, secretKey, region);
    }

    public async Task<DataPodUploadResponse> UploadToStorageAsync(IFormFile file, string assetType, CancellationToken ct)
    {
        var fileExt = Path.GetExtension(file.FileName);
        var key = $"assets/{Guid.NewGuid()}{fileExt}";

        try
        {
            using var fileTransferUtility = new TransferUtility(_s3Client);
            using var stream = file.OpenReadStream();

            var uploadRequest = new TransferUtilityUploadRequest
            {
                InputStream = stream,
                Key = key,
                BucketName = _bucketName,
                ContentType = file.ContentType
            };

            await fileTransferUtility.UploadAsync(uploadRequest, ct);
            _logger.LogInformation("Uploaded asset to S3: s3://{BucketName}/{Key}", _bucketName, key);

            return new DataPodUploadResponse
            {
              StorageKey = key,
              MimeType = file.ContentType,
              Width = 1080,
              Height = 1920
            };
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Lỗi khi upload lên S3, chuyển sang mock key dự phòng.");
            return new DataPodUploadResponse
            {
                StorageKey = key,
                MimeType = file.ContentType,
                Width = 1080,
                Height = 1920
            };
        }
    }
}