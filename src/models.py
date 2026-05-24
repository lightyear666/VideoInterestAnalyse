"""数据模型"""
from dataclasses import dataclass, field
from typing import Optional, List
from enum import Enum

class DataSource(Enum):
    BROWSER = "browser"
    BILIBILI_API = "bilibili"
    DOUYIN_API = "douyin"

class DeviceType(Enum):
    MOBILE = "mobile"
    WEB = "web"
    PAD = "pad"
    TV = "tv"
    UNKNOWN = "unknown"

@dataclass
class VideoRecord:
    title: str
    author: str = ""
    platform: str = ""
    tag: str = ""             # 平台原始标签
    category: str = ""        # 一级分类
    sub_category: str = ""    # 二级分类
    confidence: str = ""      # high/medium/low
    source: DataSource = DataSource.BROWSER
    device: DeviceType = DeviceType.UNKNOWN
    video_id: str = ""
    url: str = ""
    view_at: str = ""
    duration: int = 0
    progress: int = 0
    visit_count: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    keywords: List[str] = field(default_factory=list)

@dataclass
class ScrapeResult:
    platform: str
    records: List[VideoRecord]
    errors: List[str] = field(default_factory=list)
    total_fetched: int = 0
    logged_in: bool = False

@dataclass
class AnalysisReport:
    total_records: int
    platforms: dict
    categories: dict
    top_authors: list
    top_tags: list
    devices: dict
    time_span: str
    total_duration_h: float
    records: List[VideoRecord]
    daily_duration: list = field(default_factory=list)      # [(date, seconds), ...]
    platform_duration: dict = field(default_factory=dict)     # {platform: seconds}
    hourly_dist: list = field(default_factory=list)           # [(hour_label, count), ...]
    errors: List[str] = field(default_factory=list)

DEVICE_MAP = {1:'📱', 3:'📱', 5:'📱', 7:'📱', 2:'💻', 4:'📟', 6:'📟', 33:'📺'}
DEVICE_LABEL = {1:'手机', 3:'手机', 5:'手机', 7:'手机', 2:'PC', 4:'Pad', 6:'Pad', 33:'TV', 0:'未知'}

def dt_to_device(dt: int) -> DeviceType:
    if dt in (1,3,5,7): return DeviceType.MOBILE
    if dt == 2: return DeviceType.WEB
    if dt in (4,6): return DeviceType.PAD
    if dt == 33: return DeviceType.TV
    return DeviceType.UNKNOWN
