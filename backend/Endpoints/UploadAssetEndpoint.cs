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

        var taskId = await conn.ExecuteScalarAsync<Guid?>(
            "SELECT task_id FROM briefs WHERE id = @BriefId", new { BriefId = briefId });
        if (taskId is null)
        {
            ThrowError("Không tìm thấy brief.");
        }

        const string sql = @"
            INSERT INTO asset_refs (id, task_id, data_object_ref, asset_type, asset_role, mime_type)
            VALUES (@Id, @TaskId, @ObjectRef, @AssetType, @AssetRole, @MimeType)
            RETURNING id;";

        var assetId = await conn.ExecuteScalarAsync<Guid>(sql, new
        {
            Id = Guid.NewGuid(),
            TaskId = taskId,
            ObjectRef = storageRes.StorageKey,
            AssetType = req.AssetType == "logo" ? "logo" : "image",
            AssetRole = req.AssetType,
            MimeType = storageRes.MimeType ?? req.File.ContentType ?? "application/octet-stream"
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