# WebHarbor Dashboard Operations

## Services

### Dashboard preview

Port: `5188`

Systemd unit:

```text
/etc/systemd/system/webharbor-dashboard-preview.service
```

Commands:

```bash
systemctl status webharbor-dashboard-preview.service --no-pager -l
sudo systemctl restart webharbor-dashboard-preview.service
journalctl -u webharbor-dashboard-preview.service -n 100 --no-pager
```

The service runs:

```bash
python3 -m http.server 5188 \
  --bind 0.0.0.0 \
  --directory /home/v-haoqiwang/repos/WebHarbor/webvoyager_dashboard
```

Restart policy:

```text
Restart=always
RestartSec=3
```

### WebHarbor mirrors

Container:

```text
webharbor-audit
```

Ports:

```text
8311 -> 8101
43000-43014 -> 40000-40014
```

Commands:

```bash
docker ps --filter name=webharbor-audit
docker inspect webharbor-audit --format '{{json .HostConfig.RestartPolicy}} AutoRemove={{.HostConfig.AutoRemove}}'
docker logs --tail 100 webharbor-audit
```

Expected restart policy:

```text
{"Name":"unless-stopped","MaximumRetryCount":0} AutoRemove=false
```

## Azure NSG

Resource group:

```text
MSRA-IM-Share
```

NSG:

```text
vimeo-vm-nsg
```

Rules currently used by this dashboard/WebHarbor setup:

```text
AllowWebVoyagerDashboard5188      CorpNetPublic -> TCP 5188
AllowWebHarborMirrors43000_43014  CorpNetPublic -> TCP 43000-43014
```

Check:

```bash
az network nsg rule list \
  -g MSRA-IM-Share \
  --nsg-name vimeo-vm-nsg \
  --query "[?name=='AllowWebVoyagerDashboard5188' || name=='AllowWebHarborMirrors43000_43014'].{name:name,priority:priority,src:sourceAddressPrefix,port:destinationPortRange,access:access}" \
  -o table
```

## Health checks

Local checks:

```bash
curl -I --max-time 5 http://127.0.0.1:5188/
curl -I --max-time 5 http://127.0.0.1:8311/health
curl -I --max-time 5 http://127.0.0.1:43000/
curl -I --max-time 5 http://127.0.0.1:43014/
ss -ltnp | rg '5188|8311|43000|43014|State'
```

CorpNet/Public checks:

```bash
curl -I --max-time 8 http://20.225.168.143:5188/
curl -I --max-time 8 http://20.225.168.143:43000/
curl -I --max-time 8 http://20.225.168.143:43014/
```

## Recovery

Dashboard down:

```bash
sudo systemctl restart webharbor-dashboard-preview.service
```

WebHarbor container down:

```bash
docker start webharbor-audit
```

If the container was removed, recreate it:

```bash
docker run -d --name webharbor-audit --restart unless-stopped \
  -p 8311:8101 \
  -p 43000-43014:40000-40014 \
  battalion7244/webharbor:latest
```
