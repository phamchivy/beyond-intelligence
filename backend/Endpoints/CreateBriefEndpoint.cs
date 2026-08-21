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

        const string sql = @"
            INSERT INTO briefs (
                status, product_name, product_category, product_price, product_usp,
                product_features, product_offer, allowed_claims, audience_profile,
                objective, key_message, channel, aspect_ratio,
                creative_reference, max_duration_ms, language, required_cta,
                banned_claims, banned_content
            ) VALUES (
                'draft', @ProductName, @ProductCategory, @ProductPrice, @ProductUsp,
                @ProductFeatures::jsonb, @ProductOffer, @AllowedClaims::jsonb, @AudienceProfile::jsonb,
                @Objective, @KeyMessage, @Channel, @AspectRatio,
                @CreativeReference::jsonb, @MaxDurationMs, @Language, @RequiredCta,
                @BannedClaims::jsonb, @BannedContent::jsonb
            ) RETURNING id;";

        var briefId = await conn.ExecuteScalarAsync<Guid>(sql, new
        {
            req.ProductName,
            req.ProductCategory,
            req.ProductPrice,
            req.ProductUsp,
            ProductFeatures = JsonSerializer.Serialize(req.ProductFeatures ?? new List<string>()),
            req.ProductOffer,
            AllowedClaims = JsonSerializer.Serialize(req.AllowedClaims ?? new List<string>()),
            AudienceProfile = JsonSerializer.Serialize(req.AudienceProfile),
            req.Objective,
            req.KeyMessage,
            req.Channel,
            req.AspectRatio,
            CreativeReference = req.CreativeReference != null ? JsonSerializer.Serialize(req.CreativeReference) : null,
            req.MaxDurationMs,
            req.Language,
            req.RequiredCta,
            BannedClaims = JsonSerializer.Serialize(req.BannedClaims ?? new List<string>()),
            BannedContent = JsonSerializer.Serialize(req.BannedContent ?? new List<string>())
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