# WALL / ATLAS

按应用分类浏览付费墙与完整流程。每个 App 独占一行：名称直接链接 App Store，下方按「视频 → 全部截图」横向展示。

支持分类、搜索、收藏、排序、截图放大与键盘翻页；每页 20 个应用，适配手机。图片和视频仅保存原始链接，浏览时按需加载，不需要下载媒体文件。

## 当前数据

采集于 **2026-09-23**，来源为 [PaywallPro](https://www.paywallpro.app/zh/paywalls) 当前美国区公开列表（region_code=1102）。

| 项目 | 数量 |
|---|---:|
| 2026 年应用记录 | 1,465 |
| 应用分类 | 25 |
| 流程截图链接 | 17,347 |
| 视频链接 | 1,462 |
| 页面数（每页 20 个应用） | 74 |

日期口径是 `recent_capture_update`（截图／流程更新时间），范围为 `2026-01-01`（含）至 `2027-01-01`（不含）。本次公开数据实际日期为 **2026-01-04 至 2026-05-09**；不意味着其他权限或地区的数据也只到这个日期。

遍历了公开列表的 **356 页、4,268 条记录**，与接口报告的总数一致，无重复 info_id。筛出 1,465 条 2026 年记录；3 条缺少截图日期的记录单独保存在 `reports/undated-records.json`，不混入年度数据。

本次覆盖列表当前提供的流程，不声称覆盖其他地区、需登录／Pro 权限的内容或每个应用的全部历史版本。网站高级日期筛选需要 Pro，本次未使用该功能，读取普通公开分页后在本地按日期归类。

截图序列包含引导页、付费墙和应用内页面。完整序列保持来源顺序；少量人工选定封面记在 `curated-covers.json`，其他应用默认使用第一张截图作为视频封面，不把所有截图标为付费墙。

## 打开页面

```bash
gh repo clone devSC/paywall-atlas
cd paywall-atlas
python3 -m http.server 8765 --bind 127.0.0.1
```

保持服务运行，在浏览器打开 http://127.0.0.1:8765。也可直接打开本目录的 `index.html`，不需要构建或安装前端依赖。加载远程图片和视频需要联网。

GitHub 仓库保存源码与链接数据，当前未启用在线网站托管。

## 文件

- `index.html`：可交互浏览页。
- `data.js`：页面使用的数据与采集范围说明。
- `manifest.json`：保留来源字段的 2026 年原始记录。
- `reports/collection.json`：采集范围、分页进度及分类计数。
- `reports/integrity.json`：数量、去重、日期排序和分页响应 SHA-256 校验。
- `reports/link-checks.json`：每个应用第一张截图及全部视频链接的 HEAD 检查结果。检查不下载媒体，不代表已逐一验证全部 17,347 张截图；可用性也可能随来源变化。
- `reports/undated-records.json`：缺少截图日期的来源记录。
- `reports/verification.md`：本次页面与数据验证说明。

## 重新采集

需要 Python 3 和 curl，无额外 Python 依赖。缓存目录应为当前采集独立使用的新目录；相同目录可用于故障后的断点续采。

```bash
python3 scripts/collect.py --cache /tmp/paywallpro-new-run --year 2026
python3 scripts/build_data.py --cache /tmp/paywallpro-new-run
python3 scripts/audit_collection.py --cache /tmp/paywallpro-new-run
python3 scripts/check_links.py --cache /tmp/paywallpro-new-run --output reports/link-checks.json
```

采集器保持网站正常分页大小，有限重试连接错误，遇到权限错误立即停止。只有总数和去重核对通过才标为完整；失败时页面会显示部分收录状态。若本机代理 DNS 返回虚拟地址导致 TLS 失败，可先核实公开 DNS 的当前解析，再通过 `--resolve IP` 指定真实 IP；TLS 证书校验始终开启。

媒体文件、临时截图和缓存目录不提交到仓库。
