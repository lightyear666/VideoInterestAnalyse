#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
兴趣分析器 InterestProfiler v1.0
================================
主程序入口 — 交互式CLI + 全流程自动化
"""

import os, sys, json, time
from datetime import datetime
from pathlib import Path
from collections import Counter

# 确保src可导入
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.console import Console
from src.models import VideoRecord, AnalysisReport, DataSource
from src.analyzer import Analyzer
from src.reporter import ReportGenerator


# ═══════════════════════════════════════════════════════════
# 环境检测
# ═══════════════════════════════════════════════════════════

def check_environment() -> dict:
    """检查运行环境和依赖"""
    Console.section("环境检测")
    status = {'ok': True, 'modules': {}, 'warnings': []}
    
    # Python版本
    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}"
    Console.info(f"Python {py_ver}")
    
    # 核心依赖
    deps = {
        'yaml': 'pyyaml',
        'websocket': 'websocket-client',
        'playwright': 'playwright',
    }
    
    for mod, pkg in deps.items():
        try:
            __import__(mod)
            Console.ok(f"{pkg}")
            status['modules'][pkg] = True
        except ImportError:
            Console.warn(f"{pkg} — 未安装 (pip install {pkg})")
            status['modules'][pkg] = False
            status['warnings'].append(pkg)
    
    # 可选: sentence-transformers
    try:
        __import__('sentence_transformers')
        Console.ok("sentence-transformers (向量分类可用)")
        status['modules']['sentence-transformers'] = True
    except ImportError:
        Console.warn("sentence-transformers — 未安装 (可选, 增强分类精度)")
        status['modules']['sentence-transformers'] = False
    
    # Edge检测
    edge_path = os.path.expandvars(r'%LOCALAPPDATA%\Microsoft\Edge\User Data')
    if os.path.isdir(edge_path):
        Console.ok(f"Edge浏览器: 已安装")
        status['edge'] = True
    else:
        Console.warn("Edge浏览器: 未检测到")
        status['edge'] = False
        status['warnings'].append('Edge未安装')
    
    if status['warnings']:
        Console.warn(f"警告: {', '.join(status['warnings'])}")
    
    return status


# ═══════════════════════════════════════════════════════════
# 数据保存
# ═══════════════════════════════════════════════════════════

def save_records_txt(records: list, output_dir: Path, platform: str):
    """保存原始记录到TXT"""
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    path = output_dir / f'{platform}_history_{ts}.txt'
    
    authors = Counter(r.author for r in records if r.author)
    cats = Counter(r.category for r in records)
    dur_h = sum(r.duration for r in records if r.duration > 0) / 3600
    
    with open(path, 'w', encoding='utf-8') as f:
        f.write(f"{'='*80}\n")
        f.write(f"  {platform.upper()} 浏览历史记录\n")
        f.write(f"  生成: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | {len(records)} 条\n")
        f.write(f"{'='*80}\n\n")
        f.write(f"总浏览:{len(records)} | 作者:{len(authors)}位 | 时长:{dur_h:.1f}h\n\n")
        f.write(f"[Top-15 作者]\n{'-'*40}\n")
        for i,(n,c) in enumerate(authors.most_common(15),1):
            f.write(f"  {i:2d}. {n:24s} {c:4d}\n")
        f.write(f"\n[分类分布]\n{'-'*40}\n")
        for cat, cnt in cats.most_common():
            f.write(f"  {cat:12s} {cnt:4d}\n")
        f.write(f"\n[详细记录]\n{'-'*80}\n")
        for i,r in enumerate(records,1):
            f.write(f"{i:4d}. [{r.view_at}] {r.category:8s} @{r.author:16s} | {r.title}\n")
        f.write(f"\n{'='*80}\n")
    
    Console.ok(f"TXT: {path.name} ({path.stat().st_size/1024:.1f}KB)")
    return str(path)


# ═══════════════════════════════════════════════════════════
# 爬取调度
# ═══════════════════════════════════════════════════════════

def run_scraper(platform: str, cookies: dict, max_records: int) -> list:
    """运行单个平台爬虫"""
    if platform == 'bilibili':
        from src.scrapers.bilibili import BiliScraper
        scraper = BiliScraper(cookies)
    elif platform == 'douyin':
        from src.scrapers.douyin import DouyinScraper
        scraper = DouyinScraper(cookies)
    else:
        return []
    
    Console.section(f"爬取 {platform.upper()} 浏览历史")
    records = scraper.fetch(max_records)
    Console.ok(f"{platform}: 获取 {len(records)} 条")
    return records


def scrape_platform(platform: str, max_records: int) -> tuple:
    """
    完整的平台爬取流程: Cookie提取 → 登录检测 → 爬取 → 返回记录
    """
    from src.cookie_manager import CookieManager
    
    cm = CookieManager()
    
    # 提取Cookie
    Console.section(f"{platform.upper()} — Cookie提取")
    login_urls = {
        'bilibili': 'https://www.bilibili.com/',
        'douyin': 'https://www.douyin.com/',
    }
    cookies = cm.extract(platform, login_urls.get(platform))
    
    if not cookies:
        Console.err(f"{platform}: 无法提取Cookie")
        cm.cleanup()
        return [], [f"{platform}: Cookie提取失败"]
    
    # 检测登录
    Console.info("检测登录状态...")
    time.sleep(3)  # 等待页面加载完成
    
    logged_in = cm.check_login(platform, cookies)
    
    # 抖音特殊处理: 未登录时等待用户手动登录
    if not logged_in and platform == 'douyin':
        Console.warn(f"抖音未登录 — Edge窗口已打开抖音首页")
        Console.info("请在Edge窗口中完成抖音登录...")
        Console.info("登录完成后按 Enter 继续")
        
        try:
            input()
        except (EOFError, KeyboardInterrupt):
            pass
        
        Console.info("重新检测登录状态...")
        time.sleep(2)
        
        # 重新提取Cookie(不重启Edge, 登录后Cookie会更新)
        cookies = cm.re_extract(login_urls.get(platform))
        if cookies:
            logged_in = cm.check_login(platform, cookies)
    
    if not logged_in:
        Console.err(f"{platform}: 仍未登录!")
        Console.warn(f"  请在Edge中打开 {login_urls.get(platform)} 登录后重试")
        cm.cleanup()
        return [], [f"{platform}: 未登录"]
    
    Console.ok(f"{platform}: 已登录 ✓")
    
    # 爬取
    records = run_scraper(platform, cookies, max_records)
    
    cm.cleanup()
    return records, []


# ═══════════════════════════════════════════════════════════
# 主流程
# ═══════════════════════════════════════════════════════════

def main():
    Console.title("🎬 兴趣分析器 InterestProfiler v1.0")
    
    # ======== 1. 环境检测 ========
    env = check_environment()
    
    # ======== 2. 选择平台 ========
    Console.menu("选择分析平台:", [
        ("B站 (bilibili)", "通过B站History API获取全设备浏览记录"),
        ("抖音 (douyin)", "通过抖音History API获取全设备浏览记录"),
        ("B站 + 抖音", "同时分析两个平台"),
    ])
    
    try:
        choice = input(f"\n  请选择 [1-3] (默认=3): ").strip() or '3'
    except (EOFError, KeyboardInterrupt):
        print("\n已取消")
        sys.exit(0)
    
    platforms = []
    if choice == '1': platforms = ['bilibili']
    elif choice == '2': platforms = ['douyin']
    else: platforms = ['bilibili', 'douyin']
    
    # ======== 3. 选择分析方法 ========
    Console.menu("选择分析方法:", [
        ("规则引擎 (推荐)", "基于B站官方分区+关键词匹配，快速准确"),
        ("规则+向量模型", "规则引擎为主 + 向量模型增强低置信度记录"),
    ])
    
    try:
        method = input(f"\n  请选择 [1-2] (默认=1): ").strip() or '1'
    except (EOFError, KeyboardInterrupt):
        print("\n已取消")
        sys.exit(0)
    
    use_vector = (method == '2')
    
    # ======== 4. 记录数量 ========
    try:
        n = input(f"\n  爬取记录数 (默认=100): ").strip()
        max_records = int(n) if n else 100
    except (EOFError, KeyboardInterrupt):
        print("\n已取消")
        sys.exit(0)
    except ValueError:
        max_records = 100
    
    print()
    Console.info(f"平台: {' + '.join(platforms)} | 方法: {'规则+向量' if use_vector else '规则引擎'} | 目标: {max_records}条")
    print()
    
    # ======== 5. 开始爬取 ========
    all_records = []
    all_errors = []
    output_dir = Path(__file__).parent / 'output'
    output_dir.mkdir(exist_ok=True)
    
    for i, platform in enumerate(platforms):
        Console.title(f"▸ [{i+1}/{len(platforms)}] 爬取 {platform.upper()}")
        
        records, errors = scrape_platform(platform, max_records)
        all_records.extend(records)
        all_errors.extend(errors)
        
        # 保存原始记录
        if records:
            save_records_txt(records, output_dir, platform)
    
    if not all_records:
        Console.err("未获取到任何记录!")
        for e in all_errors:
            Console.err(f"  {e}")
        Console.warn("\n请确保已在Edge浏览器登录对应平台后重试")
        sys.exit(1)
    
    # ======== 6. 分类 ========
    Console.title("▸ 内容分类")
    
    from src.classifier import RuleClassifier
    classifier = RuleClassifier()
    all_records = classifier.classify_batch(all_records)
    
    # 显示分类统计
    cats = Counter(r.category for r in all_records)
    for cat, cnt in cats.most_common():
        Console.info(f"  {cat:8s}: {cnt:4d} 条")
    
    # 可选向量增强
    if use_vector and env['modules'].get('sentence-transformers'):
        from src.classifier import VectorClassifier
        vc = VectorClassifier()
        if vc.try_load():
            vc.classify_batch(all_records)
    
    # ======== 7. 统计 ========
    Console.title("▸ 统计分析")
    analyzer = Analyzer()
    report = analyzer.analyze(all_records)
    
    # ======== 8. 生成报告 ========
    Console.title("▸ 生成报告")
    generator = ReportGenerator(str(output_dir))
    html_path = generator.generate(report)
    
    # ======== 9. 完成 ========
    print()
    Console.title("✅ 分析完成!")
    Console.ok(f"总记录: {report.total_records} 条")
    Console.ok(f"平台: {', '.join(f'{k}({v})' for k,v in report.platforms.items())}")
    Console.ok(f"分类: {len(report.categories)} 种")
    Console.ok(f"时长: {report.total_duration_h:.1f} 小时")
    Console.ok(f"时间: {report.time_span}")
    Console.ok(f"")
    Console.ok(f"📁 HTML报告: {html_path}")
    Console.ok(f"📁 原始数据: {output_dir}/")
    print()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n[!] 用户中断")
        sys.exit(0)
