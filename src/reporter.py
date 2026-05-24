"""HTML报告生成器 v4 — 纯HTML/CSS图表, 零JavaScript依赖"""
import json, os
from datetime import datetime
from pathlib import Path
from .models import AnalysisReport
from .console import Console

COLORS = ['#f06292','#ec407a','#f48fb1','#f8bbd0','#ff80ab',
          '#ff4081','#e91e63','#ad1457','#fce4ec','#f50057','#c51162','#880e4f']

class ReportGenerator:
    def __init__(self, output_dir: str = None):
        if output_dir is None:
            output_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'output')
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def _make_bar(self, label: str, value: int, max_val: int, color: str = '#ec407a') -> str:
        pct = value / max_val * 100 if max_val else 0
        return f'''<div style="display:flex;align-items:center;margin:6px 0;gap:10px">
  <div style="width:80px;text-align:right;font-size:0.85em;color:#555;flex-shrink:0">{label}</div>
  <div style="flex:1;background:#fce4ec;border-radius:8px;height:24px;overflow:hidden;min-width:50px">
    <div style="width:{pct}%;height:100%;background:{color};border-radius:8px;transition:width 0.5s;min-width:2px"></div>
  </div>
  <div style="width:50px;font-size:0.85em;color:#999;flex-shrink:0;text-align:right">{value}</div>
  <div style="width:45px;font-size:0.8em;color:#bbb;flex-shrink:0">{pct:.1f}%</div>
</div>'''

    def _make_svg_pie(self, items: list, size: int = 200) -> str:
        """生成SVG环形图"""
        total = sum(v for _, v in items)
        if total == 0: return ''
        
        cx, cy, r = size//2, size//2, size//2 - 10
        inner_r = r * 0.55
        angle = -90
        slices = []
        
        for i, (name, val) in enumerate(items[:10]):
            sweep = val / total * 360
            if sweep < 3: sweep = 3  # minimum visible
            start_rad = angle * 3.14159 / 180
            end_rad = (angle + sweep) * 3.14159 / 180
            
            x1 = cx + inner_r * __import__('math').cos(start_rad)
            y1 = cy + inner_r * __import__('math').sin(start_rad)
            x2 = cx + r * __import__('math').cos(start_rad)
            y2 = cy + r * __import__('math').sin(start_rad)
            x3 = cx + r * __import__('math').cos(end_rad)
            y3 = cy + r * __import__('math').sin(end_rad)
            x4 = cx + inner_r * __import__('math').cos(end_rad)
            y4 = cy + inner_r * __import__('math').sin(end_rad)
            
            large = 1 if sweep > 180 else 0
            color = COLORS[i % len(COLORS)]
            pct = val / total * 100
            
            slices.append(f'''<path d="M{x1:.1f},{y1:.1f} L{x2:.1f},{y2:.1f} A{r},{r} 0 {large},1 {x3:.1f},{y3:.1f} L{x4:.1f},{y4:.1f} A{inner_r},{inner_r} 0 {large},0 {x1:.1f},{y1:.1f} Z" fill="{color}" stroke="#fff" stroke-width="2">
  <title>{name}: {val} ({pct:.1f}%)</title></path>''')
            angle += sweep
        
        # 中心文字
        center_text = f'<text x="{cx}" y="{cy-8}" text-anchor="middle" font-size="18" font-weight="bold" fill="#555">{total}</text><text x="{cx}" y="{cy+12}" text-anchor="middle" font-size="11" fill="#999">总计</text>'
        
        # 图例
        legend = ''
        y_offset = 15
        for i, (name, val) in enumerate(items[:10]):
            if i > 0 and i % 5 == 0:
                y_offset += 22
            x_offset = 15 + (i % 5) * (size // 5)
            color = COLORS[i % len(COLORS)]
            legend += f'<rect x="{x_offset}" y="{size + y_offset}" width="10" height="10" rx="2" fill="{color}"/><text x="{x_offset+14}" y="{size + y_offset + 10}" font-size="10" fill="#666">{name[:6]}</text>'
        
        return f'<svg width="{size}" height="{size + y_offset + 30}" xmlns="http://www.w3.org/2000/svg">\n{"".join(slices)}\n{center_text}\n{legend}\n</svg>'

    def _make_svg_bar(self, items: list, width: int = 500, height: int = 300) -> str:
        """生成SVG柱状图"""
        if not items: return ''
        max_val = max(v for _, v in items)
        bar_count = len(items)
        bar_w = min(40, (width - 120) // bar_count)
        gap = (width - 120 - bar_w * bar_count) // max(bar_count - 1, 1)
        
        bars = ''
        for i, (name, val) in enumerate(items):
            x = 100 + i * (bar_w + gap)
            h = (val / max_val) * (height - 60) if max_val else 0
            y = height - 40 - h
            color = COLORS[i % len(COLORS)]
            bars += f'''<rect x="{x}" y="{y}" width="{bar_w}" height="{h}" rx="6" fill="{color}">
  <title>{name}: {val}</title></rect>
<text x="{x + bar_w/2}" y="{y - 6}" text-anchor="middle" font-size="11" fill="#999">{val}</text>
<text x="{x + bar_w/2}" y="{height - 15}" text-anchor="middle" font-size="10" fill="#666" transform="rotate(-30,{x+bar_w/2},{height-15})">{name[:8]}</text>'''
        
        return f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">\n{bars}\n<line x1="100" y1="{height-40}" x2="{width-20}" y2="{height-40}" stroke="#e0e0e0"/>\n</svg>'

    def generate(self, report: AnalysisReport) -> str:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        html_path = self.output_dir / f'interest_report_{timestamp}.html'
        
        total = report.total_records
        # 分类排序
        cat_sorted = sorted(report.categories.items(), key=lambda x: -x[1])
        cat_bars = '\n'.join(self._make_bar(k, v, cat_sorted[0][1] if cat_sorted else 1, COLORS[i % len(COLORS)]) 
                             for i, (k, v) in enumerate(cat_sorted))
        
        # SVG 环形图
        cat_svg = self._make_svg_pie([(k, v) for k, v in cat_sorted], 280)
        
        # 平台柱状图
        plat_svg = self._make_svg_bar(
            [('B站' if k == 'bilibili' else '抖音' if k == 'douyin' else k, v) for k, v in report.platforms.items()],
            400, 250
        )
        
        # 设备柱状图
        dev_map = {'web': 'PC', 'mobile': '手机', 'pad': '平板', 'tv': '电视', 'unknown': '未知'}
        dev_svg = self._make_svg_bar(
            [(dev_map.get(k, k), v) for k, v in sorted(report.devices.items(), key=lambda x: -x[1])],
            400, 250
        )
        
        # ═══ NEW: 时长分析 ═══
        # 每日时长 SVG 柱状图
        daily_svg = self._make_daily_svg(report.daily_duration, 600, 250)
        
        # 平台时长占比 CSS bar
        plat_dur_bars = ''
        max_pd = max(report.platform_duration.values()) if report.platform_duration else 1
        pd_colors = {'bilibili': '#ec407a', 'douyin': '#f48fb1'}
        for plat, dur_h in report.platform_duration.items():
            label = 'B站' if plat == 'bilibili' else '抖音' if plat == 'douyin' else plat
            pct = dur_h / max_pd * 100 if max_pd else 0
            color = pd_colors.get(plat, '#f06292')
            plat_dur_bars += f'''<div style="display:flex;align-items:center;margin:5px 0;gap:8px">
  <div style="width:50px;text-align:right;font-size:0.85em;color:#555">{label}</div>
  <div style="flex:1;background:#fce4ec;border-radius:6px;height:20px;overflow:hidden;min-width:40px">
    <div style="width:{pct}%;height:100%;background:{color};border-radius:6px;min-width:2px"></div>
  </div>
  <div style="width:55px;font-size:0.85em;color:#555;text-align:right">{dur_h:.1f}h</div>
  <div style="width:45px;font-size:0.8em;color:#999">{pct:.0f}%</div>
</div>'''
        
        # 每日时段分布 SVG
        hourly_svg = self._make_hourly_svg(report.hourly_dist, 600, 250)
        
        # 每日时长表格
        daily_rows = ''
        for d, s in report.daily_duration[::-1][:30]:
            h = s / 3600
            daily_rows += f'<tr><td>{d}</td><td style="text-align:right">{h:.1f}h</td><td style="text-align:right">{s//60}min</td></tr>'
        
        author_svg = self._make_svg_bar(
            [(a[:10], c) for a, c in report.top_authors[:12]],
            600, 300
        ) if report.top_authors else ''
        
        # 详细记录表格
        rows = ''
        for i, r in enumerate(report.records, 1):
            conf_color = {'high': '#66bb6a', 'medium': '#ffa726', 'low': '#ef5350'}.get(r.confidence, '#999')
            dev_label = {'web': 'PC', 'mobile': '手机', 'pad': '平板', 'tv': '电视', 'unknown': '?'}.get(r.device.value, r.device.value)
            dev_color = {'手机': '#ec407a', 'PC': '#42a5f5', 'pad': '#66bb6a', 'tv': '#ffa726', '?': '#999'}.get(dev_label, '#999')
            title_esc = r.title.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')
            rows += f'''<tr>
  <td>{i}</td><td style="white-space:nowrap">{r.view_at}</td><td>{r.platform}</td>
  <td style="color:{dev_color}">{dev_label}</td><td>{r.category}</td>
  <td style="max-width:100px;overflow:hidden;text-overflow:ellipsis">{r.tag}</td>
  <td>{r.author[:16]}</td><td>{r.duration}s</td>
  <td style="color:{conf_color};font-weight:600">{r.confidence}</td>
  <td style="max-width:250px;overflow:hidden;text-overflow:ellipsis" title="{title_esc}">{r.title[:60]}</td>
</tr>'''[:600]  # limit per row
        
        html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>兴趣分析报告</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:"Microsoft YaHei","PingFang SC",sans-serif;background:linear-gradient(135deg,#fff5f7,#fce4ec);color:#333;min-height:100vh}}
.container{{max-width:1200px;margin:0 auto;padding:20px}}
.header{{text-align:center;padding:50px 20px 30px;background:linear-gradient(135deg,#f8bbd0,#f48fb1,#f06292);color:#fff;border-radius:0 0 30px 30px;box-shadow:0 4px 20px rgba(240,98,146,0.2)}}
.header h1{{font-size:2.2em;font-weight:700;text-shadow:0 2px 4px rgba(0,0,0,0.1);margin-bottom:8px}}
.header .meta{{font-size:0.95em;opacity:0.9}}
.stats{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:14px;padding:30px 0}}
.stat-box{{background:#fff;border-radius:16px;padding:22px;text-align:center;box-shadow:0 2px 12px rgba(0,0,0,0.05);border:1px solid #fce4ec;transition:transform 0.2s}}
.stat-box:hover{{transform:translateY(-2px);box-shadow:0 4px 20px rgba(240,98,146,0.12)}}
.stat-box .value{{font-size:2em;font-weight:800;background:linear-gradient(135deg,#ec407a,#f06292,#f48fb1);-webkit-background-clip:text;-webkit-text-fill-color:transparent}}
.stat-box .label{{font-size:0.85em;color:#999;margin-top:4px}}
.card{{background:#fff;border-radius:16px;padding:24px;box-shadow:0 2px 12px rgba(0,0,0,0.05);border:1px solid #fce4ec;margin-bottom:20px}}
.card h2{{font-size:1.1em;color:#ec407a;margin-bottom:16px;font-weight:600;display:flex;align-items:center;gap:8px}}
.card h2::before{{content:'';display:inline-block;width:4px;height:20px;background:linear-gradient(135deg,#ec407a,#f48fb1);border-radius:2px}}
.grid2{{display:grid;grid-template-columns:1fr 1fr;gap:20px}}@media(max-width:768px){{.grid2{{grid-template-columns:1fr}}}}
.chart-wrap{{display:flex;justify-content:center;align-items:flex-start;padding:10px 0}}
table{{width:100%;border-collapse:collapse;font-size:0.82em}}
th{{background:linear-gradient(135deg,#fce4ec,#f8bbd0);padding:10px 8px;text-align:left;color:#555;font-weight:600;white-space:nowrap;position:sticky;top:0;z-index:1}}
td{{padding:8px;border-bottom:1px solid #fce4ec;max-width:250px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:#555}}
tr:hover td{{background:#fff5f7}}
.footer{{text-align:center;padding:30px;color:#bbb;font-size:0.85em}}
</style>
</head>
<body>
<div class="header">
  <h1>🎬 兴趣分析报告</h1>
  <div class="meta">生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 总记录 {total} 条 | {report.time_span}</div>
</div>

<div class="container">
<div class="stats">
  <div class="stat-box"><div class="value">{total}</div><div class="label">总浏览数</div></div>
  <div class="stat-box"><div class="value">{len(report.categories)}</div><div class="label">兴趣分类</div></div>
  <div class="stat-box"><div class="value">{len(report.platforms)}</div><div class="label">视频平台</div></div>
  <div class="stat-box"><div class="value">{report.total_duration_h:.1f}h</div><div class="label">总时长</div></div>
</div>

<div class="card">
  <h2>📊 兴趣分类分布</h2>
  <div class="grid2">
    <div class="chart-wrap">{cat_svg}</div>
    <div style="padding:10px">{cat_bars}</div>
  </div>
</div>

<div class="grid2">
  <div class="card">
    <h2>🎯 视频平台分布</h2>
    <div class="chart-wrap">{plat_svg}</div>
  </div>
  <div class="card">
    <h2>📱 设备来源分布</h2>
    <div class="chart-wrap">{dev_svg}</div>
  </div>
</div>

<div class="card">
  <h2>⏱ 观看时长分析</h2>
  <div class="grid2">
    <div>
      <h3 style="font-size:0.95em;color:#ec407a;margin-bottom:10px">📅 每日观看时长</h3>
      <div class="chart-wrap">{daily_svg}</div>
      <div style="overflow-y:auto;max-height:180px;margin-top:8px">
        <table style="font-size:0.8em">
          <thead><tr><th>日期</th><th>时长</th><th>分钟</th></tr></thead>
          <tbody>{daily_rows}</tbody>
        </table>
      </div>
    </div>
    <div>
      <h3 style="font-size:0.95em;color:#ec407a;margin-bottom:10px">🎯 各平台时长占比</h3>
      <div style="padding:10px">{plat_dur_bars}</div>
      <h3 style="font-size:0.95em;color:#ec407a;margin:16px 0 10px">🕐 每日集中观看时段</h3>
      <div class="chart-wrap">{hourly_svg}</div>
    </div>
  </div>
</div>

<div class="card">
  <h2>👤 Top-{min(12, len(report.top_authors))} UP主/作者</h2>
  <div class="chart-wrap">{author_svg}</div>
</div>

<div class="card">
  <h2>📋 详细浏览记录 (共{total}条)</h2>
  <div style="overflow-x:auto;max-height:550px;overflow-y:auto">
    <table>
      <thead><tr><th>#</th><th>时间</th><th>平台</th><th>设备</th><th>分类</th><th>标签</th><th>作者</th><th>时长</th><th>置信</th><th>标题</th></tr></thead>
      <tbody>{self._make_table_rows(report.records)}</tbody>
    </table>
  </div>
</div>

<div class="footer">InterestProfiler v1.0 · 浏览器历史API · 本地处理 · 隐私安全</div>
</div>
</body></html>'''
        
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html)
        
        Console.ok(f"HTML报告: {html_path.name} ({html_path.stat().st_size/1024:.1f}KB)")
        return str(html_path)

    def _make_daily_svg(self, data: list, width: int = 600, height: int = 250) -> str:
        """每日时长SVG柱状图"""
        if not data: return ''
        import math
        max_h = max(s for _, s in data) if data else 1
        bar_count = len(data)
        bar_w = max(8, width // max(bar_count, 1) - 6)
        gap = (width - 60 - bar_w * bar_count) // max(bar_count - 1, 1) if bar_count > 1 else 0
        
        bars = ''
        for i, (date, secs) in enumerate(data):
            x = 40 + i * (bar_w + gap)
            h = (secs / max_h) * (height - 50) if max_h else 0
            y = height - 35 - h
            hours = secs / 3600
            bars += f'''<rect x="{x}" y="{y}" width="{bar_w}" height="{h}" rx="3" fill="#ec407a" opacity="0.8">
  <title>{date}: {hours:.1f}h</title></rect>
<text x="{x + bar_w/2}" y="{y - 8}" text-anchor="middle" font-size="9" fill="#999">{hours:.1f}h</text>'''
            # Only show date label every 5 bars or if few
            if bar_count <= 15 or i % max(1, bar_count // 8) == 0:
                label = date[5:]  # MM-DD
                bars += f'<text x="{x + bar_w/2}" y="{height - 8}" text-anchor="middle" font-size="9" fill="#666">{label}</text>'
        
        return f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">\n<line x1="35" y1="{height-35}" x2="{width-10}" y2="{height-35}" stroke="#f0e0e6"/>\n{bars}\n</svg>'

    def _make_hourly_svg(self, data: list, width: int = 600, height: int = 250) -> str:
        """时段分布面积图 (12个2h时段)"""
        if not data: return ''
        import math
        max_count = max(c for _, c in data) if data else 1
        n = len(data)
        bar_w = width // n - 4
        cx = width / 2
        
        bars = ''
        points = ''
        for i, (label, count) in enumerate(data):
            x = 10 + i * (width // n)
            h = (count / max_count) * (height - 60) if max_count else 0
            y = height - 40 - h
            color = '#f06292' if 18 <= i * 2 <= 23 else '#f48fb1'  # 晚上深色
            bars += f'''<rect x="{x}" y="{y}" width="{bar_w}" height="{h}" rx="4" fill="{color}" opacity="0.85">
  <title>{label}: {count}条</title></rect>
<text x="{x + bar_w/2}" y="{height - 15}" text-anchor="middle" font-size="8" fill="#999">{label[:2]}h</text>'''
            if count > 0:
                bars += f'<text x="{x + bar_w/2}" y="{y - 2}" text-anchor="middle" font-size="8" fill="#ec407a">{count}</text>'
        
        return f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">\n<line x1="5" y1="{height-40}" x2="{width-5}" y2="{height-40}" stroke="#f0e0e6"/>\n{bars}\n</svg>'

    def _make_table_rows(self, records) -> str:
        rows = ''
        for i, r in enumerate(records, 1):
            conf_color = {'high': '#66bb6a', 'medium': '#ffa726', 'low': '#ef5350'}.get(r.confidence, '#999')
            dev_label = {'web': 'PC', 'mobile': '手机', 'pad': '平板', 'tv': '电视', 'unknown': '?'}.get(r.device.value, r.device.value)
            dev_color = {'手机': '#ec407a', 'PC': '#42a5f5', '平板': '#66bb6a', '电视': '#ffa726', '?': '#999'}.get(dev_label, '#999')
            title_esc = r.title.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')
            rows += f'<tr><td>{i}</td><td style="white-space:nowrap">{r.view_at}</td><td>{r.platform}</td><td style="color:{dev_color}">{dev_label}</td><td>{r.category}</td><td style="max-width:100px;overflow:hidden;text-overflow:ellipsis" title="{r.tag}">{r.tag[:12]}</td><td>{r.author[:14]}</td><td>{r.duration}s</td><td style="color:{conf_color};font-weight:600">{r.confidence}</td><td style="max-width:280px;overflow:hidden;text-overflow:ellipsis" title="{title_esc}">{r.title[:60]}</td></tr>\n'
        return rows
