using System.Text;
using AIHackathonApi.Endpoints;
using AIHackathonApi.Models;
using FastEndpoints;
using FluentAssertions;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Http;
using Moq;

namespace AIHackathonApi.Tests.Endpoints;

public class UploadVideoEndpointTests
{
  private readonly Mock<IWebHostEnvironment> _mockEnv;
  private readonly string _testTempDir;

  public UploadVideoEndpointTests()
  {
    _testTempDir = Path.Combine(Path.GetTempPath(), "SentraLoopTests", Guid.NewGuid().ToString("N"));
    Directory.CreateDirectory(_testTempDir);

    _mockEnv = new Mock<IWebHostEnvironment>();
    _mockEnv.Setup(e => e.WebRootPath).Returns(_testTempDir);
  }

  private static IFormFile CreateMockFormFile(string fileName, byte[] content)
  {
    var stream = new MemoryStream(content);
    return new FormFile(stream, 0, content.Length, "VideoFile", fileName)
    {
      Headers = new HeaderDictionary(),
      ContentType = "video/mp4"
    };
  }

  [Fact]
  public async Task HandleAsync_WithValidMp4File_ShouldSaveFileAndReturnSuccessResponse()
  {
    // Arrange
    var endpoint = Factory.Create<UploadVideoEndpoint>(_mockEnv.Object);
    var fileContent = Encoding.UTF8.GetBytes("fake-video-binary-content-12345");
    var formFile = CreateMockFormFile("demo-ad.mp4", fileContent);

    var request = new UploadVideoRequest
    {
      VideoFile = formFile,
      ProductTitle = "Vintage Camping T-Shirt",
      ProductCategory = "Fashion",
      TargetMarket = "US"
    };

    // Act
    await endpoint.HandleAsync(request, CancellationToken.None);

    // Assert
    endpoint.HttpContext.Response.StatusCode.Should().Be(200);

    // Đọc response object trả về từ FastEndpoints
    var response = endpoint.Response;
    
    if (string.IsNullOrEmpty(response.AnalysisId))
    {
      var videoFiles = Directory.GetFiles(Path.Combine(_testTempDir, "uploads", "videos"), "*.mp4");
      videoFiles.Should().NotBeEmpty();
      
      var savedFileName = Path.GetFileName(videoFiles.First());
      savedFileName.Should().StartWith("ANL-");
    }
    else
    {
      response.Status.Should().Be("PROCESSING");
      response.AnalysisId.Should().StartWith("ANL-");
      response.VideoUrl.Should().StartWith("/uploads/videos/ANL-");
      response.VideoUrl.Should().EndWith(".mp4");
      response.FileSizeBytes.Should().Be(fileContent.Length);
    }

    if (Directory.Exists(_testTempDir))
    {
      Directory.Delete(_testTempDir, true);
    }
  }

  [Fact]
  public async Task HandleAsync_WithEmptyFile_ShouldThrowValidationFailure()
  {
    // Arrange
    var endpoint = Factory.Create<UploadVideoEndpoint>(_mockEnv.Object);
    var formFile = CreateMockFormFile("empty.mp4", Array.Empty<byte>());

    var request = new UploadVideoRequest
    {
      VideoFile = formFile
    };

    // Act
    Func<Task> action = async () => await endpoint.HandleAsync(request, CancellationToken.None);

    // Assert
    await action.Should().ThrowAsync<Exception>();
  }

  [Fact]
  public async Task HandleAsync_WithInvalidExtension_ShouldThrowValidationFailure()
  {
    // Arrange
    var endpoint = Factory.Create<UploadVideoEndpoint>(_mockEnv.Object);
    var fileContent = Encoding.UTF8.GetBytes("plain text content");
    var formFile = CreateMockFormFile("document.pdf", fileContent);

    var request = new UploadVideoRequest
    {
      VideoFile = formFile
    };

    // Act
    Func<Task> action = async () => await endpoint.HandleAsync(request, CancellationToken.None);

    // Assert
    await action.Should().ThrowAsync<Exception>();
  }
}