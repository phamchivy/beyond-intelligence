using FastEndpoints;
using Dapper;
using Npgsql;
using AIHackathonApi.Models.DTOs;
using AIHackathonApi.Services;

namespace AIHackathonApi.Endpoints;

public class UploadAssetEndpoint : Endpoint<UploadAssetRequest, UploadAssetResponse>
{
    private readonly IDataPodService _dataPodService;
    private readonly IConfiguration _config;

    public UploadAssetEndpoint(IDataPodService dataPodService, IConfiguration config)
    {
        _dataPodService = dataPodService;
        _config = config;
    }

    public override void Configure()
    {
        Post("/api/v1/briefs/{brief_id}/assets");
        AllowAnonymous();
        AllowFileUploads();
        Summary(s => s.Summary = "Upload asset cho Brief (đẩy sang Data Pod và ghi DB)");
    }

    public override async Task HandleAsync(UploadAssetRequest req, CancellationToken ct)
    {
        // 1. Đọc route param brief_id
        var briefIdStr = Route<string>("brief_id");
        if (!Guid.TryParse(briefIdStr, out var briefId))
        {
            ThrowError("brief_id không hợp lệ.");
        }

        if (req.File == null || req.File.Length == 0)
        {
            ThrowError("File tải lên không hợp lệ.");
        }

        // 2. Gọi Data Pod lưu vào Object Storage
        var storageRes = await _dataPodService.UploadToStorageAsync(req.File, req.AssetType, ct);

        // 3. Ghi thông tin asset vào Postgres
        await using var conn = new NpgsqlConnection(_config.GetConnectionString("DefaultConnection"));
        await conn.OpenAsync(ct);

        const string sql = @"
            INSERT INTO assets (
                brief_id, asset_type, storage_key, processed_key, width, height, mime_type
            ) VALUES (
                @BriefId, @AssetType, @StorageKey, @ProcessedKey, @Width, @Height, @MimeType
            ) RETURNING id;";

        var assetId = await conn.ExecuteScalarAsync<Guid>(sql, new
        {
            BriefId = briefId,
            AssetType = req.AssetType,
            storageRes.StorageKey,
            storageRes.ProcessedKey,
            storageRes.Width,
            storageRes.Height,
            storageRes.MimeType
        });

        var res = new UploadAssetResponse
        {
            AssetId = assetId,
            BriefId = briefId,
            AssetType = req.AssetType,
            StorageKey = storageRes.StorageKey
        };
        await HttpContext.Response.WriteAsJsonAsync(res, cancellationToken: ct);
    }
}