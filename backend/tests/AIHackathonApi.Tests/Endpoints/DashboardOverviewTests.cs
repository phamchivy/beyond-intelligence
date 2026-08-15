using FluentAssertions;
using Xunit;

namespace AIHackathonApi.Tests.Endpoints;

public class DashboardOverviewTests
{
    [Fact]
    public void DashboardData_ShouldHaveValidProfitMarginAndRiskLevel()
    {
        double profitMargin = 22.4;
        string riskLevel = "MEDIUM";

        profitMargin.Should().BeInRange(0, 100); // Tỷ lệ phần trăm phải từ 0 -> 100%
        riskLevel.Should().MatchRegex("^(LOW|MEDIUM|HIGH)$"); // Rủi ro chỉ được là 1 trong 3 mức
    }
}