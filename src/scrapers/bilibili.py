"""B站历史爬虫"""
import json, time, ssl, urllib.request
from datetime import datetime
from ..models import VideoRecord, DataSource, dt_to_device
from ..console import Console

class BiliScraper:
    API = 'https://api.bilibili.com/x/web-interface/history/cursor'
    PAGE_SIZE = 30
    
    def __init__(self, cookies: dict):
        self.cookies = cookies
        self.cookie_str = '; '.join(f'{k}={v}' for k,v in cookies.items())
        self.ctx = ssl.create_default_context()
    
    def fetch(self, max_records=100) -> list[VideoRecord]:
        records = []
        cursor = {'max': '0', 'view_at': '0', 'business': ''}
        page = 0
        
        while len(records) < max_records:
            page += 1
            params = f'ps={self.PAGE_SIZE}&max={cursor["max"]}&view_at={cursor["view_at"]}&business={cursor["business"]}'
            
            try:
                req = urllib.request.Request(
                    f'{self.API}?{params}',
                    headers={
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                        'Referer': 'https://www.bilibili.com/',
                        'Cookie': self.cookie_str,
                    }
                )
                data = json.loads(urllib.request.urlopen(req, timeout=15, context=self.ctx).read())
            except Exception as e:
                Console.err(f"B站API请求失败: {e}")
                break
            
            if data.get('code') == -101:
                Console.err("B站未登录! Cookie已失效")
                break
            if data.get('code') != 0:
                Console.warn(f"B站API: {data.get('message', '未知错误')}")
                break
            
            items = data['data']['list']
            if not items:
                break
            
            for it in items:
                h = it.get('history', {})
                dt = h.get('dt', 0)
                records.append(VideoRecord(
                    title=it.get('title', ''),
                    author=it.get('author_name', ''),
                    platform='bilibili',
                    tag=it.get('tag_name', ''),
                    source=DataSource.BILIBILI_API,
                    device=dt_to_device(dt),
                    video_id=h.get('bvid', ''),
                    view_at=datetime.fromtimestamp(it.get('view_at', 0)).strftime('%Y-%m-%d %H:%M') if it.get('view_at') else '',
                    duration=it.get('duration', 0),
                    progress=it.get('progress', 0),
                ))
            
            Console.progress(len(records), max_records, f"B站 第{page}页 +{len(items)}条")
            
            if items and len(records) <= max_records:
                r = records[-1]
                print()
                Console.info(f"  [{r.view_at}] {r.title[:45]} @{r.author}")
            
            cursor = data['data']['cursor']
            if len(items) < self.PAGE_SIZE:
                break
            if len(records) >= max_records:
                records = records[:max_records]
                break
            time.sleep(0.4)
        
        print()
        return records
