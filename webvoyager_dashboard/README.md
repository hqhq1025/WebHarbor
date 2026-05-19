# WebHarbor 本地审计与任务设计面板

这份目录是我们在 `cpu001` 上为 WebHarbor/WebVoyager 做的本地运维、审计和任务设计资料。它不是 WebHarbor 上游 README 的替代品；上游项目介绍仍看仓库根目录的 `README.md`。

## 当前公司内网入口

- Dashboard: `http://20.225.168.143:5188/`
- WebHarbor mirrors: `http://20.225.168.143:43000/` 到 `http://20.225.168.143:43014/`
- Control plane: `http://20.225.168.143:8311/health`

这些入口依赖 Azure NSG，当前只允许微软 CorpNet 出口访问：

- `AllowWebVoyagerDashboard5188`: `CorpNetPublic -> TCP 5188`
- `AllowWebHarborMirrors43000_43014`: `CorpNetPublic -> TCP 43000-43014`

如果需要临时公开给 Internet，应该显式改 NSG source；默认不要开放给全 Internet。不要只改本机进程；公司内网能否访问首先由 NSG 决定。

本机浏览器不要用 `http://localhost:43000/` 访问远端镜像。`localhost` 指的是你本机，不是这台 `cpu001`。如果不走公司内网，可以自己开 SSH 端口转发，例如：

```bash
ssh -L 43000:127.0.0.1:43000 -L 43001:127.0.0.1:43001 azure
```

## 端口映射

| Port | Site |
| --- | --- |
| 43000 | Allrecipes |
| 43001 | Amazon |
| 43002 | Apple |
| 43003 | ArXiv |
| 43004 | BBC News |
| 43005 | Booking |
| 43006 | GitHub |
| 43007 | Google Flights |
| 43008 | Google Maps |
| 43009 | Google Search |
| 43010 | Hugging Face |
| 43011 | Wolfram Alpha |
| 43012 | Cambridge Dictionary |
| 43013 | Coursera |
| 43014 | ESPN |

## 当前运行方式和持久化

WebHarbor 官方镜像运行在 Docker 容器 `webharbor-audit`，当前已经改成 Docker 自恢复：

```bash
docker ps --filter name=webharbor-audit
docker inspect webharbor-audit --format '{{json .HostConfig.RestartPolicy}} AutoRemove={{.HostConfig.AutoRemove}}'
curl -s http://127.0.0.1:8311/health | python3 -m json.tool
```

期望输出里 restart policy 应是：

```bash
{"Name":"unless-stopped","MaximumRetryCount":0} AutoRemove=false
```

也就是说：

- 容器进程崩了会自动重启。
- VM 重启后 Docker 会自动拉起容器。
- 不再使用 `--rm` / AutoRemove 容器运行 WebHarbor。

Dashboard 是静态站，由 systemd 服务 `webharbor-dashboard-preview.service` 托管：

```bash
systemctl status webharbor-dashboard-preview.service --no-pager -l
systemctl is-enabled webharbor-dashboard-preview.service
systemctl is-active webharbor-dashboard-preview.service
```

systemd 服务文件：

```text
/etc/systemd/system/webharbor-dashboard-preview.service
```

它会运行：

```bash
python3 -m http.server 5188 \
  --bind 0.0.0.0 \
  --directory /home/v-haoqiwang/repos/WebHarbor/webvoyager_dashboard
```

并且配置了：

```text
Restart=always
RestartSec=3
WantedBy=multi-user.target
```

如果 dashboard 端口挂了，用下面命令恢复/重启：

```bash
sudo systemctl restart webharbor-dashboard-preview.service
```

如果需要查看日志：

```bash
tail -f /home/v-haoqiwang/repos/WebHarbor/webvoyager_dashboard/server-5188.log
journalctl -u webharbor-dashboard-preview.service -n 100 --no-pager
```

### 健康检查

```bash
curl -I --max-time 5 http://127.0.0.1:5188/
curl -I --max-time 5 http://127.0.0.1:8311/health
curl -I --max-time 5 http://127.0.0.1:43000/
curl -I --max-time 5 http://127.0.0.1:43014/
ss -ltnp | rg '5188|8311|43000|43014|State'
```

自恢复验证已做过：

- kill 掉 dashboard 的 `http.server 5188` 进程后，systemd 在数秒内重新拉起。
- `webharbor-audit` 容器已重建为 `--restart unless-stopped`。

## Dashboard 内容

Dashboard 包含：

- WebHarbor 基础设施状态。
- 15 个 WebVoyager mirror 的健康和数据规模。
- 643 条 WebVoyager 原任务浏览器。
- WebVoyager 覆盖审计：原始 643 条任务按站点、能力标签、答案口径、实时风险和状态操作拆解。
- 中文 Playbook：逐站人工任务设计建议。
- Variant Library：基于每个站点现有基础设施，可以继续造哪些题、参数怎么变、如何验证、有哪些坑。
- 浏览器截图和资源完整性审计。
- 黑夜模式。
- 文档页使用 HTML 渲染，不直接让用户打开 Markdown；宽表格会自动换行，桌面端不应出现横向滚动条。

核心文件：

```text
webvoyager_dashboard/index.html
webvoyager_dashboard/styles.css
webvoyager_dashboard/app.js
webvoyager_dashboard/data.js
webvoyager_dashboard/review_data.js
webvoyager_dashboard/variant_playbook.js
webvoyager_dashboard/assets/audit_screens/
webvoyager_dashboard/manual_review/
```

重新生成数据：

```bash
python3 webvoyager_dashboard/generate_data.py
python3 webvoyager_dashboard/localize_reviews_zh.py
python3 webvoyager_dashboard/build_review_data.py
```

## 当前资源完整性状态

最新审计结果：

- Booking 首页：0 broken images，0 4xx static responses。
- ESPN 首页：0 broken images，0 4xx static responses。
- Dashboard：0 broken images，0 4xx static responses。

验证命令示例：

```bash
curl --noproxy '*' -sS -L --max-time 8 \
  -o /tmp/booking.html \
  -w '%{http_code} %{size_download}\n' \
  http://20.225.168.143:43005/
```

## 上游问题和跟进

上游官方镜像 `battalion7244/webharbor:latest` 仍能复现资源问题：

- Booking 首页模板引用了不存在的：
  - `/static/images/gallery/paris/paris_1.jpg`
  - `/static/images/gallery/bali/bali_1.jpg`
  - `/static/images/gallery/paris/paris_2.jpg`
- ESPN 缺少部分 league/team 图片：
  - `soccer.png`
  - `ncaaf.png`
  - `ncaam.png`
  - `ncaaw.png`
  - `tennis.png`
  - `golf.png`
  - `fantasy.png`
  - `teams/soccer/rma.png`
  - `teams/soccer/mia.png`
  - `teams/soccer/psg.png`

已创建上游 issue：

- `https://github.com/aiming-lab/WebHarbor/issues/3`

已创建 Booking 模板修复 PR：

- `https://github.com/aiming-lab/WebHarbor/pull/4`

PR 只修 Booking。ESPN 更像 HF dataset asset 缺失，需要后续补 `espn.tar.gz` 或做代码侧 fallback。

## 本地热修补

当前运行容器和本地文件里已经热修：

- Booking 首页的 3 张 travel inspiration 图片改为现有 `screenshots/*.png`。
- ESPN 补了缺失的 league/team PNG 占位图。

注意：ESPN 的图片在 `sites/*/static/images` 下，属于 HF-managed 资产路径。当前容器和本地目录是好的，但如果重新 pull 官方镜像或重新 fetch HF assets，这些补图可能丢失。要永久修复，需要把 ESPN 图片补进 HF dataset 的 `espn.tar.gz`。

## Git 状态提醒

当前主工作区包含本地 dashboard 和热修补文件，不应该直接 `git add -A` 提交到上游 PR。

Booking 上游 PR 使用独立 worktree：

```text
/home/v-haoqiwang/repos/WebHarbor-booking-image-pr
```
