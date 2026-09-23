# WALL / ATLAS 资源更新与运维手册

本文说明如何安全地更新 PaywallPro 公开付费墙数据、验证结果、部署 GitHub Pages，以及处理常见故障。

## 1. 系统概览

WALL / ATLAS 是一个静态资源浏览站点：

- 数据来源：PaywallPro 美国区公开列表（`region_code=1102`）。
- 年份口径：`recent_capture_update`，即流程截图更新时间。
- 媒体策略：仓库只保存图片和视频 URL，不下载媒体文件。
- 展示方式：每个 App 独占一行，视频在前，完整截图序列在后。
- 浏览分页：每页 **100 个 App**。当前 1,465 个 App 共 15 页，末页 65 个。
- 部署方式：`main` 分支推送后由 GitHub Pages 自动发布。
- 在线地址：https://devsc.github.io/paywall-atlas/

数据处理链路：

```text
PaywallPro 公开分页
  -> 临时缓存 page-XXXX.json
  -> 年份筛选 selected.json
  -> data.js + manifest.json
  -> 完整性与链接报告
  -> Git commit / push
  -> GitHub Pages
```

浏览页和来源接口都使用每页 100 条。来源接口已验证 `limit=100` 时返回 100 条、总数 4,268、日期顺序正确；完整列表约 43 页。采集器限制 `--page-size` 最大为 100，不允许继续扩大。

## 2. 环境要求

需要：

- macOS 或 Linux
- Python 3.10 及以上版本
- curl
- Git
- 已配置仓库推送权限
- 可选：GitHub CLI，用于检查 Pages 部署状态

不需要安装 Python 第三方包。

首次获取仓库：

```bash
gh repo clone devSC/paywall-atlas
cd paywall-atlas
```

已有仓库时先同步：

```bash
git pull --ff-only origin main
git status --short
```

开始更新前，`git status --short` 应为空。若已有改动，先确认其归属，不要覆盖或混入资源更新提交。

## 3. 推荐方式：交互式更新向导

运行：

```bash
python3 scripts/refresh.py
```

向导会依次询问：

1. 目标年份。
2. 临时缓存目录。
3. 抓取节奏。
4. 可选的主站真实 IP。
5. 是否开始抓取。
6. 是否生成并覆盖网页资源数据。
7. 是否检查代表截图和全部视频链接。
8. 是否提交并推送到个人仓库。

任何会修改仓库或推送远端的阶段都会再次确认。

### 3.1 抓取节奏

| 模式 | 页面间隔 | 定期休息 | 适用场景 |
|---|---|---|---|
| 温和 | 随机 1.2–2.8 秒 | 每 24–36 页休息 7–15 秒 | 默认、日常更新 |
| 均衡 | 随机 0.6–1.4 秒 | 每 40–60 页休息 3–8 秒 | 已确认网络稳定 |
| 快速 | 固定 0.35 秒 | 无 | 调试或使用完整本地缓存 |

温和与均衡模式只是模拟人工浏览节奏、降低请求频率。脚本使用透明的 `paywall-atlas-refresh/1.0` 标识，不伪装浏览器指纹、不处理验证码，也不突破登录或 Pro 权限。

### 3.2 只查看计划

```bash
python3 scripts/refresh.py --plan
```

也可以指定参数：

```bash
python3 scripts/refresh.py \
  --plan \
  --year 2026 \
  --cache /tmp/paywallpro-2026-preview \
  --pace gentle
```

`--plan` 不访问网络，也不修改仓库。

## 4. 缓存与断点续传

正式刷新应使用新的缓存目录。向导默认生成类似以下路径：

```text
/tmp/paywallpro-2026-20260923-223000
```

每个成功页面保存为：

```text
page-0001.json
page-0002.json
...
```

缓存目录同时包含 `config.json`，记录来源分页大小、地区和排序。若新参数与缓存配置不同，采集器会拒绝继续，防止把旧的 12 条/页缓存和新的 100 条/页缓存混合。

抓取中断后：

1. 重新运行 `python3 scripts/refresh.py`。
2. 输入相同年份。
3. 输入上次相同的缓存目录。
4. 选择任意节奏并继续。

缓存中已经存在的页面会直接读取，不会重新请求，也不会触发等待。新页面从断点继续。

不要用一个已经完成的旧缓存目录执行“新一次刷新”，否则会复用旧数据。新刷新使用新目录；故障恢复才复用原目录。

## 5. 手动执行流程

交互向导不可用时，可以手动运行。

### 5.1 创建独立缓存目录

```bash
refresh_dir=$(mktemp -d /tmp/paywallpro-2026.XXXXXX)
```

### 5.2 温和抓取

```bash
python3 scripts/collect.py \
  --cache "$refresh_dir" \
  --year 2026 \
  --page-size 100 \
  --delay-min 1.2 \
  --delay-max 2.8 \
  --break-every-min 24 \
  --break-every-max 36 \
  --break-min 7 \
  --break-max 15
```

完成后检查：

```bash
cat "$refresh_dir/report.json"
```

必须满足：

- `status` 为 `complete`。
- `unique_rows` 与 `reported_count` 相等。
- `stop_reason` 为 `Public list exhausted`。
- `selected_rows` 是目标年份的条目数。

若状态为 `partial`，不要发布。修复连接后使用同一缓存目录续传。

### 5.3 生成网页数据

```bash
python3 scripts/build_data.py --cache "$refresh_dir"
```

该命令会更新：

- `data.js`
- `manifest.json`
- `reports/collection.json`
- `reports/undated-records.json`

已有人工封面选择来自 `curated-covers.json`，会尽量保留；新 App 默认使用第一张截图作为封面。

### 5.4 完整性审计

```bash
python3 scripts/audit_collection.py --cache "$refresh_dir"
```

审计内容包括：

- 所有来源页面是否齐全。
- 来源总数是否一致。
- `info_id` 是否重复。
- 日期是否保持降序。
- 年份筛选结果是否与导出的 `manifest.json` 完全一致。
- 每个缓存页面的 SHA-256 指纹。

结果写入 `reports/integrity.json`。

### 5.5 媒体链接检查

```bash
python3 scripts/check_links.py \
  --cache "$refresh_dir" \
  --output reports/link-checks.json
```

检查范围：

- 每个 App 的第一张截图。
- 每个 App 的全部视频链接。
- HTTP 状态码。
- `Content-Type` 是否与图片或视频匹配。

该操作只读取响应头，不下载媒体内容。

链接检查中断后可以续传：

```bash
python3 scripts/check_links.py \
  --resume \
  --cache "$refresh_dir" \
  --output reports/link-checks.json
```

### 5.6 页面策略检查

```bash
python3 scripts/check_access_policy.py
python3 scripts/check_media_policy.py
python3 scripts/check_gallery_policy.py
```

分别验证：

- 轻量密码门、SHA-256 校验、按小时失效和延迟加载数据。
- CDN 所需的 `no-referrer` 策略。
- 每页 100 条、当前页数、图片懒加载及视频不预加载。

### 5.7 离线回归测试

```bash
python3 scripts/test_refresh.py
python3 -m py_compile scripts/*.py
```

离线测试不会访问 PaywallPro，覆盖：

- 缓存续传不会等待或重复请求。
- 年份筛选随目标年份变化。
- 权限错误时停止。
- 重复分页保护。
- 向导取消后不修改仓库。
- `--plan` 输出稳定。

## 6. 检查变更

生成数据后：

```bash
git diff --stat
git diff --check
git status --short
```

重点检查：

- App 数量是否符合预期。
- 截图和视频数量是否出现异常骤降。
- 年份范围是否正确。
- `collection.json` 是否为 `complete`。
- `integrity.json` 是否 `passed: true`。
- `link-checks.json` 的 `checked` 与 `passed` 是否一致。
- 是否只有预期数据和报告文件发生变化。

## 7. 提交与部署

交互向导可以自动完成以下步骤。手动执行时使用明确的文件列表：

```bash
git add -- \
  data.js \
  manifest.json \
  reports/collection.json \
  reports/integrity.json \
  reports/link-checks.json \
  reports/undated-records.json

git commit -m "Refresh 2026 paywall resources"
git push origin main
```

不要使用 `git add .`，避免把缓存、临时文件或其他改动混入提交。

GitHub Pages 会在推送后自动部署。检查状态：

```bash
gh api repos/devSC/paywall-atlas/pages/builds/latest \
  --jq '{status:.status,commit:.commit,error:.error.message}'
```

部署完成后打开：

```text
https://devsc.github.io/paywall-atlas/
```

## 8. 浏览页分页与性能

浏览页常量为：

```text
pageSize = 100
```

100 个 App 的所有截图节点会写入当前页面，但图片使用 `loading="lazy"`，视频使用 `preload="none"`。因此浏览器只在接近可视区域时请求图片，视频只有在用户操作后才加载。

修改分页数量后，必须同步：

- `index.html` 中的 `pageSize`。
- `README.md` 中的分页说明。
- `reports/verification.md` 中的验证结果。
- `scripts/check_gallery_policy.py` 中的契约检查。

## 9. 访问密码说明

网站使用客户端轻量密码门：

- 校验通过后才加载 `data.js`。
- 密码输入使用 SHA-256 比较。
- 解锁状态只保存在当前标签页。
- 当前小时结束后自动清除并重新加载。

不要在 Markdown、Issue 或提交信息中写出密码规则。

由于仓库和 GitHub Pages 都是公开静态资源，这个密码门只能减少误访问，不能替代服务端鉴权。懂前端的用户仍可直接读取公开文件。如需真正限制访问，应迁移到支持服务端认证的托管服务，并关闭公开 Pages。

## 10. 常见故障

### 10.1 主站 TLS 连接失败

症状：

```text
SSL_connect: SSL_ERROR_SYSCALL
```

先确认本机代理和 DNS。只有在公开 DNS 已核实真实 IP 后，才通过向导填写真实 IP，或手动使用：

```bash
python3 scripts/collect.py \
  --cache "$refresh_dir" \
  --year 2026 \
  --resolve VERIFIED_IP
```

`--resolve` 仍保留原域名和 TLS 证书校验。不要长期硬编码 IP；CDN 地址可能变化。

### 10.2 API 返回 401 或 403

脚本会停止并把状态记录为 `partial`。不要重试轰炸，也不要尝试绕过登录、Pro 权限或验证码。确认请求仍属于公开列表范围后再继续。

### 10.3 抓取过程中断

复用同一个缓存目录重新运行。已成功保存的 `page-XXXX.json` 会直接读取。

### 10.4 数量核对失败

如果 `unique_rows != reported_count`、出现重复 ID 或日期顺序变化：

1. 不生成或部署新数据。
2. 保留缓存目录。
3. 检查 `report.json` 和最后几个分页响应。
4. 使用全新缓存重跑，判断是缓存问题还是来源接口变化。

### 10.5 图片或视频在 Pages 无法显示

CDN 会拒绝携带 GitHub Pages Referer 的请求。`index.html` 必须保留：

```html
<meta name="referrer" content="no-referrer">
```

运行 `python3 scripts/check_media_policy.py` 验证。不要移除该策略。

### 10.6 Pages 已部署但页面仍旧

1. 查看 Pages 最新构建提交。
2. 确认 commit 与本地 `git rev-parse HEAD` 一致。
3. 浏览器使用强制刷新。
4. 等待 GitHub Pages CDN 缓存更新。

### 10.7 链接检查部分失败

先区分：

- 网络超时。
- 403 防盗链。
- 404 资源已删除。
- `Content-Type` 异常。

不要把失败链接自动删除。来源可能暂时不可达；保留报告并人工确认后再决定。

## 11. 年份切换

更新 2027 年：

```bash
python3 scripts/refresh.py --year 2027
```

当前数据模型一次展示一个目标年份。生成 2027 数据会替换页面中的 2026 数据，不会自动合并多年份。若未来需要年份切换器，应先扩展数据结构和页面筛选逻辑。

## 12. 安全和合规边界

- 只读取公开列表。
- 不使用登录凭证抓取付费内容。
- 不绕过权限、验证码或访问控制。
- 不伪装浏览器指纹。
- 不下载媒体实体，仅保存公开 URL。
- 保持温和请求频率并支持断点续传。
- 来源返回限制或错误时停止，不自动升级对抗策略。

## 13. 发布前检查清单

- [ ] 使用新的缓存目录开始本次刷新。
- [ ] 抓取状态为 `complete`。
- [ ] 来源条数等于来源报告总数。
- [ ] 目标年份条目数合理。
- [ ] 完整性审计通过。
- [ ] 媒体链接检查完成或明确记录跳过。
- [ ] 密码、媒体和分页策略检查通过。
- [ ] 每页显示 100 个 App，末页数量正确。
- [ ] `git diff --check` 通过。
- [ ] 只暂存资源与报告文件。
- [ ] 推送到 `origin/main`。
- [ ] Pages 构建提交与本次 commit 一致。
- [ ] 线上密码门、图片和视频抽查正常。

## 14. 关键命令速查

```bash
# 交互式更新
python3 scripts/refresh.py

# 查看计划
python3 scripts/refresh.py --plan

# 断点续传：再次输入同一个缓存目录
python3 scripts/refresh.py

# 策略检查
python3 scripts/check_access_policy.py
python3 scripts/check_media_policy.py
python3 scripts/check_gallery_policy.py

# 离线测试
python3 scripts/test_refresh.py
python3 -m py_compile scripts/*.py

# 查看部署状态
gh api repos/devSC/paywall-atlas/pages/builds/latest \
  --jq '{status:.status,commit:.commit,error:.error.message}'
```
