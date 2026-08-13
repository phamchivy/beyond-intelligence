"""
DecisionPolicy -- business rule quyet dinh mot Decision co duoc phep tu
dong thuc thi (auto-execute), can nguoi phe duyet, hay bi tu choi hoan
toan truoc khi buoc vao giai doan Execute.

Day la noi tap trung logic "khi nao AI duoc tu quyet dinh, khi nao phai
hoi nguoi" -- rat quan trong voi kien truc "AI Decision & Execution
System": khong phai Decision nao cung duoc Execute ngay, dac biet voi
hanh dong co anh huong thuc te (vd: thay doi gia, gui de xuat cho khach
hang, tao campaign moi...).

Policy nhan tham so cau hinh qua constructor (KHONG tu doc config/settings)
-- day la nguyen tac giu domain "pure": application layer (bootstrap/
container.py) se doc Settings va truyen gia tri vao khi tao Policy nay.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from agent.domain.entities.decision import Decision


class PolicyOutcome(str, Enum):
    AUTO_EXECUTE = "auto_execute"
    REQUIRE_APPROVAL = "require_approval"
    REJECT = "reject"


@dataclass(frozen=True, slots=True)
class DecisionPolicy:
    """
    Rang buoc de quyet dinh so phan cua mot Decision truoc khi Execute.

    auto_execute_threshold: confidence toi thieu de duoc tu dong thuc thi
        ma khong can nguoi duyet (mac dinh 0.85 -- kha cao vi hanh dong
        di thang ra thuc te, khac voi chi tra loi cau hoi).
    reject_threshold: confidence duoi muc nay bi tu choi thang, khong
        dua len cho nguoi duyet vi qua thap de co gia tri tham khao.
    allow_high_risk_auto_execute: neu False (mac dinh), bat ky Decision
        nao co risk "high" deu KHONG duoc auto-execute du confidence cao
        toi dau -- day la "circuit breaker" an toan, tranh AI tu thuc
        hien hanh dong rui ro cao ma khong ai kiem tra.
    """

    auto_execute_threshold: float = 0.85
    reject_threshold: float = 0.3
    allow_high_risk_auto_execute: bool = False

    def evaluate(self, decision: Decision) -> PolicyOutcome:
        """
        Thu tu uu tien: REJECT (qua thap) > REQUIRE_APPROVAL (rui ro cao)
        > AUTO_EXECUTE (confidence du cao) > REQUIRE_APPROVAL (mac dinh
        an toan neu khong roi vao hai truong hop tren).
        """
        if decision.confidence < self.reject_threshold:
            return PolicyOutcome.REJECT

        if decision.is_high_risk() and not self.allow_high_risk_auto_execute:
            return PolicyOutcome.REQUIRE_APPROVAL

        if decision.confidence >= self.auto_execute_threshold:
            return PolicyOutcome.AUTO_EXECUTE

        return PolicyOutcome.REQUIRE_APPROVAL