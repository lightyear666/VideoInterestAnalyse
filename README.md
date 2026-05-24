[overview.md](https://github.com/user-attachments/files/28193194/overview.md)
# 兴趣分析器 — 需求分析与总体设计 (v2.0)

## 完成内容

完成了「兴趣分析器（InterestProfiler）」项目的完整需求分析、技术选型和总体设计。
**v2.0 更新**：新增移动端覆盖 — 平台网页爬虫模块（B站 + 抖音 History API），支持跨设备数据收集。

## 关键决策 (v2.0)

| 决策项 | 选择 | 理由 |
|--------|------|------|
| AI分类主力方案 | 本地向量模型 (sentence-transformers) | 完全离线、隐私安全、零成本 |
| 分类管道架构 | 规则引擎 → 向量模型 → LLM (可选) | 三级递进，兼顾速度与准确率 |
| 前端输出 | 纯 HTML + ECharts | 离线可用、零依赖、交互丰富 |
| 平台爬虫 (NEW) | B站API直调 + 抖音curl_cffi + Playwright兜底 | 覆盖全设备历史，处理反爬 |
| Cookie提取 (NEW) | SQLite + AES-256-GCM解密 (DPAPI) | 从浏览器自动提取，无需手动复制 |
| 数据合并 (NEW) | video_id→URL→标题+作者 三级去重 | 多数据源取并集，API元数据增强浏览器记录 |

## 实测验证

基于真实 Edge 浏览器数据（8,806条记录）：
- 视频内容占比 54.0%
- Bilibili 占视频流量 97.1%

## API调研成果

- B站：`/x/web-interface/history/cursor` — Cursor分页，`dt`字段标识设备类型
- 抖音：`/aweme/v1/web/history/read/` — Cursor分页，需a-bogus签名

## 下一步

按 5 阶段开发计划推进，Phase 1 MVP 优先启动（浏览器扫描 + 历史提取 + 规则分类 + 基础报告）
