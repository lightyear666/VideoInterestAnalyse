"""统计分析"""
from typing import List
from collections import Counter, defaultdict
from .models import VideoRecord, AnalysisReport
from .console import Console

class Analyzer:
    def analyze(self, records: List[VideoRecord]) -> AnalysisReport:
        Console.section("统计分析")
        
        total = len(records)
        if total == 0:
            return AnalysisReport(total_records=0, platforms={}, categories={}, 
                                  top_authors=[], top_tags=[], devices={},
                                  time_span='N/A', total_duration_h=0, records=[])
        
        platforms = Counter(r.platform for r in records)
        categories = Counter(r.category for r in records)
        authors = Counter(r.author for r in records if r.author)
        top_authors = authors.most_common(20)
        tags = Counter(r.tag for r in records if r.tag)
        top_tags = tags.most_common(20)
        devices = Counter(r.device.value for r in records)
        times = [r.view_at for r in records if r.view_at]
        time_span = f'{times[-1]} ~ {times[0]}' if len(times) >= 2 else 'N/A'
        dur_h = sum(r.duration for r in records if r.duration > 0) / 3600
        
        Console.info(f"平台: {dict(platforms)}")
        Console.info(f"分类: {dict(categories.most_common(10))}")
        Console.info(f"设备: {dict(devices)}")
        
        # ═══ 时长统计 ═══
        Console.section("时长分析")
        
        # 1. 每日观看时长 (按日期汇总duration)
        daily = defaultdict(int)
        # 2. 各平台时长占比
        plat_dur = defaultdict(int)
        # 3. 每小时时段分布 (按view_at的小时统计记录数)
        hourly = Counter()
        
        for r in records:
            if r.view_at and len(r.view_at) >= 10:
                date_key = r.view_at[:10]  # "2026-05-23"
                daily[date_key] += (r.duration or 0)
                plat_dur[r.platform] += (r.duration or 0)
                try:
                    hour = int(r.view_at[11:13])  # extract HH
                    hourly[hour] += 1
                except:
                    pass
        
        daily_sorted = sorted(daily.items())
        plat_dur_h = {k: round(v/3600, 1) for k, v in sorted(plat_dur.items(), key=lambda x: -x[1])}
        hourly_sorted = [(f'{h:02d}:00-{(h+2)%24:02d}:00', hourly.get(h,0)+hourly.get((h+1)%24,0)) 
                        for h in range(0, 24, 2)]
        
        Console.info(f"每日时长: {dict(daily_sorted)}")
        Console.info(f"平台时长(h): {plat_dur_h}")
        Console.info(f"时段分布: {dict(hourly_sorted[:6])}...")
        Console.ok(f"总计 {total} 条 | 分类 {len(categories)} 种 | 时长 {dur_h:.1f}h | {time_span}")
        
        return AnalysisReport(
            total_records=total,
            platforms=dict(platforms),
            categories=dict(categories),
            top_authors=top_authors,
            top_tags=top_tags,
            devices=dict(devices),
            time_span=time_span,
            total_duration_h=dur_h,
            records=records,
            daily_duration=[(d, s) for d, s in daily_sorted],
            platform_duration=plat_dur_h,
            hourly_dist=hourly_sorted,
        )
