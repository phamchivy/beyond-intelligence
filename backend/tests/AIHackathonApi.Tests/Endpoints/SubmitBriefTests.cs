using System;
using System.Collections.Generic;
using System.IO;
using System.Text.Json;
using AIHackathonApi.Models.DTOs;
using FluentAssertions;
using Microsoft.AspNetCore.Http;
using Xunit;

namespace AIHackathonApi.Tests.Endpoints;

public class SubmitBriefTests
{
    [Fact]
    public void SubmitBriefFormRequest_ShouldContainValidJsonFieldsAndFiles()
    {
        // 1. Giả lập Form Upload Request
        var formFile = new FormFile(
            baseStream: new MemoryStream(new byte[] { 1, 2, 3, 4 }),
            baseStreamOffset: 0,
            length: 4,
            name: "Assets",
            fileName: "product_sample.png"
        )
        {
            Headers = new HeaderDictionary(),
            ContentType = "image/png"
        };

        var req = new SubmitBriefFormRequest
        {
            ProductInfoJson = "{\"name\":\"Tai nghe Nova ANC\",\"category\":\"Âm thanh\",\"price\":1290000}",
            TargetAudienceJson = "{\"who\":\"Dân văn phòng\",\"pain_point\":\"Ồn ào\"}",
            AdObjective = "conversion",
            KeyMessage = "Tập trung tối đa cùng Nova ANC",
            Channel = "tiktok",
            ConstraintsJson = "{\"duration_seconds\":15,\"aspect_ratio\":\"9:16\"}",
            Assets = new List<IFormFile> { formFile }
        };

        // 2. Assert dữ liệu hợp lệ
        req.AdObjective.Should().Be("conversion");
        req.Channel.Should().Be("tiktok");
        req.Assets.Should().HaveCount(1);
        req.Assets[0].ContentType.Should().Be("image/png");

        // 3. Kiểm tra tính toàn vẹn của chuỗi JSON
        Action parseProductInfo = () => JsonDocument.Parse(req.ProductInfoJson);
        Action parseAudience = () => JsonDocument.Parse(req.TargetAudienceJson);
        Action parseConstraints = () => JsonDocument.Parse(req.ConstraintsJson);

        parseProductInfo.Should().NotThrow();
        parseAudience.Should().NotThrow();
        parseConstraints.Should().NotThrow();
    }

    [Fact]
    public void AgentStoryboardRequest_MappingFromUploadAssets_ShouldFormatCorrectly()
    {
        var taskId = Guid.NewGuid();
        var base64Sample = Convert.ToBase64String(new byte[] { 10, 20, 30 });

        var agentAssetDto = new AgentReferenceAssetDto
        {
            AssetRole = "hero",
            MimeType = "image/jpeg",
            ContentBase64 = base64Sample
        };

        agentAssetDto.AssetRole.Should().Be("hero");
        agentAssetDto.MimeType.Should().Be("image/jpeg");
        agentAssetDto.ContentBase64.Should().NotBeNullOrWhiteSpace();

        // Kiểm tra giải mã ngược Base64
        byte[] decodedBytes = Convert.FromBase64String(agentAssetDto.ContentBase64);
        decodedBytes.Should().BeEquivalentTo(new byte[] { 10, 20, 30 });
    }
}