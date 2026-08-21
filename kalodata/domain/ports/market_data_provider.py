"""
Vi tri file nay: data/domain/ports/market_data_provider.py

MarketDataProvider Port -- "hop dong" cho kha nang truy van du lieu thi
truong (ranking + detail) tu mot nguon du lieu ben ngoai (Kalodata la
implementation hien tai, nhung domain KHONG biet ten Kalodata).

Kalodata co 6 nhom du lieu (video/product/shop/creator/category/
livestream), MOI nhom deu co dung 2 loai truy van (ranking list +
detail) voi cau truc endpoint giong het nhau -- vi vay dung MOT port
tong quat voi tham so `domain` thay vi 6 port rieng biet, tranh lap
code (dung tinh than da ap dung cho HttpJsonRetriever trong agent/).

`raw: dict` (khong ep thanh dataclass co truong cu the) vi moi nhom du
lieu co field khac nhau hoan toan (video co digg_count, product co
commission_rate...) -- ep chung mot schema se rat gan hoac phai tao 6
dataclass rieng, khong dang gia luc nay khi service moi bat dau. Ne
neu sau nay 1 nhom du lieu duoc dung nhieu/on dinh, co the tach rieng
thanh dataclass co cau truc.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol, runtime_checkable


class MarketDataDomain(str, Enum):
    VIDEO = "video"
    PRODUCT = "product"
    SHOP = "shop"
    CREATOR = "creator"
    CATEGORY = "category"
    LIVESTREAM = "livestream"


@dataclass(frozen=True, slots=True)
class RankingQuery:
    """
    Truy van danh sach xep hang. `filters` la dict tu do, truyen thang
    xuong tham so goc cua Kalodata (vd: category_ids, revenue_range,
    keyword...) -- domain khong ep cung tung field vi moi domain co bo
    filter khac nhau, xem tai lieu goc de biet field hop le cho tung
    MarketDataDomain.
    """

    domain: MarketDataDomain
    filters: dict[str, Any] = field(default_factory=dict)
    sort_field: str = "revenue"
    page_size: int = 20
    page_number: int = 1


@dataclass(frozen=True, slots=True)
class RankingItem:
    """Mot dong ket qua trong danh sach xep hang -- giu nguyen du lieu goc trong `raw`."""

    domain: MarketDataDomain
    item_id: str
    raw: dict[str, Any]


@dataclass(frozen=True, slots=True)
class DetailQuery:
    domain: MarketDataDomain
    item_id: str


@runtime_checkable
class MarketDataProvider(Protocol):
    """
    Port cho kha nang truy van du lieu thi truong. Implementation cu
    the (KalodataClient) o infrastructure/kalodata/ -- domain/application
    khong biet ten Kalodata, khong biet URL/header xac thuc cu the.
    """

    async def get_ranking(self, query: RankingQuery) -> list[RankingItem]:
        ...

    async def get_detail(self, query: DetailQuery) -> dict[str, Any]:
        ...