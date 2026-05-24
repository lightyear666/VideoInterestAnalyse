"""抖音历史爬虫"""
import json, time, ssl, urllib.request
from datetime import datetime
from ..models import VideoRecord, DataSource
from ..console import Console

class DouyinScraper:
    API = 'https://www.douyin.com/aweme/v1/web/history/read/'
    PAGE_SIZE = 20
    
    def __init__(self, cookies: dict):
        self.cookies = cookies
        self.cookie_str = '; '.join(f'{k}={v}' for k,v in cookies.items())
        self.ctx = ssl.create_default_context()
    
    def fetch(self, max_records=100) -> list[VideoRecord]:
        records = []
        max_cursor = 0
        has_more = True
        page = 0
        seen = set()
        
        while has_more and len(records) < max_records:
            page += 1
            try:
                req = urllib.request.Request(
                    f'{self.API}?count={self.PAGE_SIZE}&max_cursor={max_cursor}',
                    headers={
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Edg/148.0.0.0',
                        'Referer': 'https://www.douyin.com/user/self?from_tab_name=main&showTab=record',
                        'Cookie': self.cookie_str,
                    }
                )
                data = json.loads(urllib.request.urlopen(req, timeout=15, context=self.ctx).read())
            except Exception as e:
                Console.err(f"抖音API请求失败: {e}")
                break
            
            sc = data.get('status_code', -1)
            if sc != 0:
                msg = data.get('status_msg', '')
                Console.err(f"抖音API: code={sc} {msg}")
                if '登录' in str(msg):
                    Console.err("抖音未登录或Cookie已失效")
                break
            
            items = data.get('aweme_list', [])
            new_count = 0
            for it in items:
                aid = it.get('aweme_id', '')
                if aid in seen:
                    continue
                seen.add(aid)
                
                author = it.get('author', {}) or {}
                stats = it.get('statistics', {}) or {}
                video = it.get('video', {}) or {}
                ct = it.get('create_time', 0)
                
                records.append(VideoRecord(
                    title=(it.get('desc', '') or '')[:120],
                    author=author.get('nickname', ''),
                    platform='douyin',
                    tag='',
                    source=DataSource.DOUYIN_API,
                    video_id=aid,
                    view_at=datetime.fromtimestamp(ct).strftime('%Y-%m-%d %H:%M') if ct else '',
                    duration=round((video.get('duration', 0) or 0) / 1000, 1) if video.get('duration') else 0,
                    likes=stats.get('digg_count', 0),
                    comments=stats.get('comment_count', 0),
                    shares=stats.get('share_count', 0),
                ))
                new_count += 1
            
            Console.progress(len(records), max_records, f"抖音 第{page}页 +{len(items)}(+{new_count}新)")
            
            if records and len(records) <= max_records:
                r = records[-1]
                print()
                Console.info(f"  [{r.view_at}] @{r.author:16s} V{r.likes:>8,} | {r.duration}s | {r.title[:45]}")
            
            has_more = data.get('has_more', False)
            max_cursor = data.get('max_cursor', 0)
            if not items or not has_more:
                break
            if len(records) >= max_records:
                records = records[:max_records]
                break
            time.sleep(1.0)
        
        print()
        return records
