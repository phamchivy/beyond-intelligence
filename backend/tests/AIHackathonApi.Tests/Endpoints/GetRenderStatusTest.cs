using System;
using System.Threading;
using System.Threading.Tasks;
using AIHackathonApi.Models.DTOs;
using AIHackathonApi.Services;
using FluentAssertions;
using Microsoft.Extensions.Configuration;
using Moq;
using Xunit;

namespace AIHackathonApi.Tests.Endpoints;

public class GetRenderStatusEndpointTests
{
    private readonly Mock<IAgentPodClient> _mockAgentPod;
    private readonly Mock<IDataPodClient> _mockDataPod;
    private readonly Mock<IConfiguration> _mockConfig;

    public GetRenderStatusEndpointTests()
    {
        _mockAgentPod = new Mock<IAgentPodClient>();
        _mockDataPod = new Mock<IDataPodClient>();
        _mockConfig = new Mock<IConfiguration>();
    }

    [Theory]
    [InlineData("not-a-uuid", false)]
    [InlineData("12345678-1234-1234-1234-123456789abc", true)]
    public void RenderId_Validation_ShouldDetectValidGuid(string rawId, bool expectedValid)
    {
        bool isValid = Guid.TryParse(rawId, out var parsedGuid);

        isValid.Should().Be(expectedValid);
        if (expectedValid)
        {
            parsedGuid.Should().NotBeEmpty();
        }
    }

    [Fact]
    public async Task AgentPod_WhenRenderCompleted_ShouldTriggerDataPodPermanentSave()
    {
        var taskId = Guid.NewGuid();
        var agentJobId = "agent-job-999";
        var tempUrl = "https://temp-storage.com/rendered-sample.mp4";
        var finalS3Url = "https://s3.ap-southeast-1.amazonaws.com/beyond-videos/final.mp4";
        var finalObjectRef = "rendered-videos/task-1/job-1.mp4";

        _mockAgentPod
            .Setup(x => x.GetRenderStatusAsync(agentJobId, It.IsAny<CancellationToken>()))
            .ReturnsAsync(new AgentRenderStatusResponse
            {
                RenderJobId = agentJobId,
                Status = "completed",
                VideoUrl = tempUrl,
                Error = null
            });

        _mockDataPod
            .Setup(x => x.SavePermanentVideoAsync(taskId, agentJobId, tempUrl, It.IsAny<CancellationToken>()))
            .ReturnsAsync(new DataSaveVideoResponse
            {
                FinalUrl = finalS3Url,
                ObjectRef = finalObjectRef
            });

        var agentStatus = await _mockAgentPod.Object.GetRenderStatusAsync(agentJobId, CancellationToken.None);
        var savedVideo = await _mockDataPod.Object.SavePermanentVideoAsync(taskId, agentJobId, agentStatus.VideoUrl!, CancellationToken.None);

        agentStatus.Status.Should().Be("completed");
        agentStatus.VideoUrl.Should().Be(tempUrl);
        savedVideo.FinalUrl.Should().Be(finalS3Url);
        savedVideo.ObjectRef.Should().Be(finalObjectRef);
    }

    [Fact]
    public async Task AgentPod_WhenRenderFails_ShouldReturnFailedStatus()
    {
        var agentJobId = "agent-job-failed";

        _mockAgentPod
            .Setup(x => x.GetRenderStatusAsync(agentJobId, It.IsAny<CancellationToken>()))
            .ReturnsAsync(new AgentRenderStatusResponse
            {
                RenderJobId = agentJobId,
                Status = "failed",
                Error = new { code = "RENDER_ERROR", message = "Video engine timeout" }
            });

        var agentStatus = await _mockAgentPod.Object.GetRenderStatusAsync(agentJobId, CancellationToken.None);

        agentStatus.Should().NotBeNull();
        agentStatus.Status.Should().Be("failed");
        agentStatus.VideoUrl.Should().BeNull();
        agentStatus.Error.Should().NotBeNull();
    }

    [Theory]
    [InlineData("queued")]
    [InlineData("processing")]
    public async Task AgentPod_WhenRenderPending_ShouldReturnCurrentProgressStatus(string pendingStatus)
    {
        var agentJobId = "agent-job-in-progress";

        _mockAgentPod
            .Setup(x => x.GetRenderStatusAsync(agentJobId, It.IsAny<CancellationToken>()))
            .ReturnsAsync(new AgentRenderStatusResponse
            {
                RenderJobId = agentJobId,
                Status = pendingStatus,
                Error = null
            });

        var agentStatus = await _mockAgentPod.Object.GetRenderStatusAsync(agentJobId, CancellationToken.None);

        agentStatus.Status.Should().Be(pendingStatus);
        agentStatus.VideoUrl.Should().BeNull();
    }
}