"""
ToolPolicy -- business rule kiem soat Agent duoc phep goi Tool nao, va
Tool nao can nguoi phe duyet truoc khi thuc thi.

Day la lop bao ve quan trong: mot Agent co the bi prompt-injection hoac
tu suy luan sai ma co gang goi mot Tool co side-effect nguy hiem (vd:
"execute_payment", "send_customer_email", "update_price") ma khong nam
trong ke hoach duoc duyet. ToolPolicy dung o giua Planner va ToolExecutor
de chan truoc khi Tool thuc su chay:

    Planner -> ToolPolicy -> ToolExecutor -> Tool
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class ToolRiskLevel(str, Enum):
    """Muc do rui ro cua mot Tool neu thuc thi sai / ngoai ke hoach."""

    LOW = "low"        # vd: doc du lieu, tinh toan, tra cuu thi truong
    MEDIUM = "medium"  # vd: ghi du lieu noi bo, tao bao cao
    HIGH = "high"       # vd: gui email khach hang, thay doi gia, thanh toan


class ToolPolicyDecision(str, Enum):
    ALLOW = "allow"
    REQUIRE_APPROVAL = "require_approval"
    DENY = "deny"


@dataclass(frozen=True, slots=True)
class ToolPermission:
    """Cau hinh quyen han cho mot Tool cu the, theo ten Tool."""

    tool_name: str
    risk_level: ToolRiskLevel = ToolRiskLevel.LOW
    enabled: bool = True


@dataclass(frozen=True, slots=True)
class ToolPolicy:
    """
    Danh sach quyen han cho tung Tool, dung de quyet dinh Tool co duoc
    goi hay khong TRUOC khi ToolExecutor thuc thi.

    `permissions` duoc truyen vao qua constructor (thuong duoc doc tu
    config/settings o application layer) -- domain khong tu biet danh
    sach Tool nao dang ton tai trong he thong, chi biet luat ap dung
    cho tung muc rui ro.
    """

    permissions: dict[str, ToolPermission] = field(default_factory=dict)
    default_risk_level: ToolRiskLevel = ToolRiskLevel.MEDIUM
    auto_deny_unknown_tools: bool = True

    def authorize(self, tool_name: str) -> ToolPolicyDecision:
        """
        Tool khong nam trong `permissions`:
          - auto_deny_unknown_tools=True (mac dinh) -> DENY thang, an
            toan hon la doan risk level cho mot Tool khong ro.
          - auto_deny_unknown_tools=False -> ap dung default_risk_level.
        """
        permission = self.permissions.get(tool_name)

        if permission is None:
            if self.auto_deny_unknown_tools:
                return ToolPolicyDecision.DENY
            risk_level = self.default_risk_level
        else:
            if not permission.enabled:
                return ToolPolicyDecision.DENY
            risk_level = permission.risk_level

        if risk_level == ToolRiskLevel.HIGH:
            return ToolPolicyDecision.REQUIRE_APPROVAL
        return ToolPolicyDecision.ALLOW

    def with_permission(self, permission: ToolPermission) -> "ToolPolicy":
        """Tra ve ToolPolicy MOI voi mot ToolPermission duoc them/cap nhat."""
        new_permissions = dict(self.permissions)
        new_permissions[permission.tool_name] = permission
        return ToolPolicy(
            permissions=new_permissions,
            default_risk_level=self.default_risk_level,
            auto_deny_unknown_tools=self.auto_deny_unknown_tools,
        )