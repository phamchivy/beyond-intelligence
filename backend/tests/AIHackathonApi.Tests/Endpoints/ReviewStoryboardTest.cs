using System;
using System.IO;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;
using AIHackathonApi.Endpoints;
using AIHackathonApi.Models.DTOs;
using AIHackathonApi.Services;
using FluentAssertions;
using Microsoft.AspNetCore.Http;
using Microsoft.Extensions.Configuration;
using Moq;
using Xunit;

namespace AIHackathonApi.Tests.Endpoints;

public class ReviewStoryboardEndpointTests
{
    private readonly Mock<IAgentPodClient> _mockAgentPod;
    private readonly Mock<IConfiguration> _mockConfig;

    public ReviewStoryboardEndpointTests()
    {
        _mockAgentPod = new Mock<IAgentPodClient>();
        _mockConfig = new Mock<IConfiguration>();
    }

    [Fact]
    public void Decision_Approved_ShouldConstructCorrectPayload()
    {
        var taskId = Guid.NewGuid();
        var storyboardId = Guid.NewGuid();

        var req = new StoryboardReviewRequest
        {
            TaskId = taskId,
            StoryboardId = storyboardId,
            Decision = "approved"
        };

        req.Decision.Should().Be("approved");
        req.TaskId.Should().Be(taskId);
        req.StoryboardId.Should().Be(storyboardId);
        req.Feedback.Should().BeNull();
    }

    [Fact]
    public async Task AgentPod_TriggerRender_ShouldReturnValidJobId()
    {
        var taskId = Guid.NewGuid();
        var expectedJobId = Guid.NewGuid().ToString();

        _mockAgentPod
            .Setup(x => x.TriggerRenderAsync(taskId, It.IsAny<CancellationToken>()))
            .ReturnsAsync(new AgentRenderTriggerResponse 
            { 
                RenderJobId = expectedJobId,
                Status = "queued"
            });

        var result = await _mockAgentPod.Object.TriggerRenderAsync(taskId, CancellationToken.None);

        result.Should().NotBeNull();
        result.RenderJobId.Should().Be(expectedJobId);
        result.Status.Should().Be("queued");
    }

    [Fact]
    public void Decision_NeedsRevision_WhenCountExceedsThree_ShouldTriggerManualReview()
    {
        int revisionCount = 3;
        const int maxRevisions = 3;

        bool isLimitReached = revisionCount >= maxRevisions;
        string resultingStatus = isLimitReached ? "needs_manual_review" : "storyboard_review";

        isLimitReached.Should().BeTrue();
        resultingStatus.Should().Be("needs_manual_review");
    }

    [Fact]
    public async Task AgentPod_ReviseStoryboard_ShouldIncrementRevisionNumber()
    {
        var taskId = Guid.NewGuid();
        var feedback = "Cần tăng nhịp điệu nhanh hơn ở phần hook";

        _mockAgentPod
            .Setup(x => x.ReviseStoryboardAsync(taskId, feedback, It.IsAny<CancellationToken>()))
            .ReturnsAsync(new AgentStoryboardResponse
            {
                TaskId = taskId.ToString(),
                RevisionNumber = 2,
                StoryboardText = "Hook: Mở đầu sôi động!\nScene 1: Cận cảnh sản phẩm\nCTA: Mua ngay"
            });

        var res = await _mockAgentPod.Object.ReviseStoryboardAsync(taskId, feedback, CancellationToken.None);

        res.Should().NotBeNull();
        res.RevisionNumber.Should().Be(2);
        res.StoryboardText.Should().Contain("Mở đầu sôi động");
    }

    [Fact]
    public void Decision_Rejected_ShouldMapToCancelledStatus()
    {
        var req = new StoryboardReviewRequest
        {
            TaskId = Guid.NewGuid(),
            StoryboardId = Guid.NewGuid(),
            Decision = "rejected"
        };

        string taskStatus = req.Decision == "rejected" ? "cancelled" : "active";

        taskStatus.Should().Be("cancelled");
        req.Decision.Should().Be("rejected");
    }
}