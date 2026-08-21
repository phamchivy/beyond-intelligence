using FastEndpoints;
using Dapper;
using Npgsql;
using System.Text.Json;
using AIHackathonApi.Models.DTOs;

namespace AIHackathonApi.Endpoints;

public class CreateBriefEndpoint : Endpoint<CreateBriefJsonRequest, CreateBriefJsonResponse>
{
    private readonly IConfiguration _config;

    public CreateBriefEndpoint(IConfiguration config)
    {
        _config = config;
    }

    public override void Configure()
    {
        Post("/api/v1/briefs");
        AllowAnonymous();
        Summary(s => s.Summary = "Tạo mới Brief (JSON thuần, status=draft)");
    }

    public override async Task HandleAsync(CreateBriefJsonRequest req, CancellationToken ct)
    {
        await using var conn = new NpgsqlConnection(_config.GetConnectionString("DefaultConnection"));
        await conn.OpenAsync(ct);

        var taskId = Guid.NewGuid();
        var briefId = Guid.NewGuid();

        await conn.ExecuteAsync(
            "INSERT INTO tasks (id, status) VALUES (@TaskId, 'brief_submitted')",
            new { TaskId = taskId });

        const string sql = @"
            INSERT INTO briefs (
                id, task_id, product_info, target_audience, ad_objective,
                key_message, channel, creative_reference, constraints
            ) VALUES (
                @Id, @TaskId, @ProductInfo::jsonb, @TargetAudience::jsonb, @AdObjective,
                @KeyMessage, @Channel, @CreativeReference::jsonb, @Constraints::jsonb
            );";

        var productInfo = JsonSerializer.Serialize(new
        {
            name = req.ProductName,
            category = req.ProductCategory,
            price = req.ProductPrice,
            usp = req.ProductUsp,
            features = req.ProductFeatures ?? new List<string>(),
            offer = req.ProductOffer,
            allowed_claims = req.AllowedClaims ?? new List<string>()
        });
        var constraints = JsonSerializer.Serialize(new
        {
            duration_seconds = req.MaxDurationMs / 1000,
            aspect_ratio = req.AspectRatio,
            language = req.Language,
            cta = req.RequiredCta,
            forbidden_content = req.BannedContent ?? new List<string>()
        });

        await conn.ExecuteAsync(sql, new
        {
            Id = briefId,
            TaskId = taskId,
            ProductInfo = productInfo,
            TargetAudience = JsonSerializer.Serialize(req.AudienceProfile ?? new { }),
            AdObjective = req.Objective ?? "conversion",
            KeyMessage = req.KeyMessage ?? "",
            Channel = req.Channel ?? "tiktok",
            CreativeReference = req.CreativeReference != null ? JsonSerializer.Serialize(req.CreativeReference) : null,
            Constraints = constraints
        });

        var res =new CreateBriefJsonResponse
        {
          Id = briefId,
          Status = "draft",
          Message = "Tạo Brief thành công."
        };
        await HttpContext.Response.WriteAsJsonAsync(res, cancellationToken: ct);
    }
}