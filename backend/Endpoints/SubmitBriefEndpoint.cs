using FastEndpoints;
using Dapper;
using Npgsql;
using System.Text.Json;
using AIHackathonApi.Models.DTOs;
using AIHackathonApi.Services;

namespace AIHackathonApi.Endpoints;

public class SubmitBriefEndpoint : Endpoint<SubmitBriefFormRequest>
{
    private readonly IS3StorageService _s3Service; // Service đẩy trực tiếp lên S3
    private readonly IAgentPodClient _agentPod;
    private readonly IConfiguration _config;

    public SubmitBriefEndpoint(IS3StorageService s3Service, IAgentPodClient agentPod, IConfiguration config)
    {
        _s3Service = s3Service;
        _agentPod = agentPod;
        _config = config;
    }

    public override void Configure()
    {
        Post("/api/v1/pipeline/submit-brief");
        AllowAnonymous();
        AllowFileUploads();
        Summary(s => s.Summary = "Upload trực tiếp S3 + Lưu Brief & Sinh Storyboard");
    }

    public override async Task HandleAsync(SubmitBriefFormRequest req, CancellationToken ct)
    {
        var taskId = Guid.NewGuid();
        var briefId = Guid.NewGuid();
        var storyboardId = Guid.NewGuid();

        await using var conn = new NpgsqlConnection(_config.GetConnectionString("DefaultConnection"));
        await conn.OpenAsync(ct);

        // 1. Tạo task trạng thái asset_processing[cite: 1, 2]
        await conn.ExecuteAsync("INSERT INTO tasks (id, status) VALUES (@id, 'asset_processing')", new { id = taskId });

        // 2. Lưu Brief vào PostgreSQL[cite: 1, 2]
        const string insertBriefSql = @"
            INSERT INTO briefs (
                id, task_id, product_info, target_audience, ad_objective,
                key_message, channel, creative_reference, constraints
            ) VALUES (
                @Id, @TaskId, @ProductInfo::jsonb, @TargetAudience::jsonb, @AdObjective,
                @KeyMessage, @Channel, @CreativeReference::jsonb, @Constraints::jsonb
            );";

        await conn.ExecuteAsync(insertBriefSql, new
        {
            Id = briefId,
            TaskId = taskId,
            ProductInfo = req.ProductInfoJson,
            TargetAudience = req.TargetAudienceJson,
            req.AdObjective,
            req.KeyMessage,
            req.Channel,
            CreativeReference = req.CreativeReferenceJson,
            Constraints = req.ConstraintsJson
        });

        // 3. Đẩy file trực tiếp lên AWS S3 (Bucket: raw-assets) & lấy Base64[cite: 1, 2]
        var uploadedAssets = await _s3Service.UploadAssetsToS3Async(taskId, req.Assets, ct);

        // 4. Lưu metadata asset_refs vào PostgreSQL[cite: 1, 2]
        const string insertAssetRefSql = @"
            INSERT INTO asset_refs (id, task_id, data_object_ref, asset_type, asset_role, mime_type)
            VALUES (@Id, @TaskId, @ObjectRef, 'image', @AssetRole, @MimeType);";

        foreach (var a in uploadedAssets)
        {
            await conn.ExecuteAsync(insertAssetRefSql, new
            {
                Id = Guid.NewGuid(),
                TaskId = taskId,
                a.ObjectRef,
                a.AssetRole,
                a.MimeType
            });
        }

        // 5. Cập nhật task -> storyboard_pending & gọi Agent Pod[cite: 1, 2]
        await conn.ExecuteAsync("UPDATE tasks SET status = 'storyboard_pending' WHERE id = @id", new { id = taskId });

        var agentReq = new AgentStoryboardRequest
        {
            TaskId = taskId,
            Brief = new
            {
                product_info = JsonDocument.Parse(req.ProductInfoJson).RootElement,
                target_audience = JsonDocument.Parse(req.TargetAudienceJson).RootElement,
                ad_objective = req.AdObjective,
                key_message = req.KeyMessage,
                channel = req.Channel,
                constraints = JsonDocument.Parse(req.ConstraintsJson).RootElement
            },
            ReferenceAssets = uploadedAssets.Select(a => new AgentReferenceAssetDto
            {
                AssetRole = a.AssetRole,
                MimeType = a.MimeType,
                ContentBase64 = a.ContentBase64
            }).ToList()
        };

        var agentRes = await _agentPod.GenerateStoryboardAsync(agentReq, ct);

        // 6. Lưu Storyboard revision 1 vào PostgreSQL[cite: 1, 2]
        const string insertStoryboardSql = @"
            INSERT INTO storyboards (
                id, task_id, revision_number, plan, compliance_report, confidence, review_status
            ) VALUES (
                @Id, @TaskId, @RevisionNumber, @Plan::jsonb, @ComplianceReport::jsonb, @Confidence, 'pending'
            );";

        await conn.ExecuteAsync(insertStoryboardSql, new
        {
            Id = storyboardId,
            TaskId = taskId,
            agentRes.RevisionNumber,
            Plan = JsonSerializer.Serialize(agentRes.StoryboardPlan),
            ComplianceReport = JsonSerializer.Serialize(agentRes.ComplianceReport),
            agentRes.Confidence
        });

        // 7. Cập nhật task -> storyboard_review[cite: 1, 2]
        await conn.ExecuteAsync("UPDATE tasks SET status = 'storyboard_review' WHERE id = @id", new { id = taskId });

        var responsePayload = new
        {
            taskId = taskId,
            storyboardId = storyboardId,
            revisionNumber = agentRes.RevisionNumber,
            storyboardPlan = agentRes.StoryboardPlan,
            complianceReport = agentRes.ComplianceReport,
            confidence = agentRes.Confidence,
            taskStatus = "storyboard_review"
        };

        await HttpContext.Response.WriteAsJsonAsync(responsePayload, cancellationToken: ct);
    }
}