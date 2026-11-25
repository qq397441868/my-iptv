# 我的 IPTV 直播订阅源（GitHub 版）

个人整理的免费电视直播播放列表，托管在 GitHub，可作为订阅源被 TVBox、DIYP、PotPlayer、VLC、TiviMate 等播放器订阅。

## 文件说明

| 文件 | 内容 |
| --- | --- |
| `live.m3u` | 国内主用源：央视、卫视、地方台、电影、纪录、少儿、音乐等（由脚本自动生成） |
| `international.m3u` | 国际/海外补充源（国内网络下部分可能不可达，由脚本自动生成） |
| `sources.json` | 上游公开源列表与测速开关，可自行增删上游地址 |
| `scripts/aggregate.py` | 聚合、去重、测速并生成上面两份 m3u 的 Python 脚本（仅用标准库） |
| `.github/workflows/update-iptv.yml` | GitHub Actions 定时工作流：自动跑脚本并把生成结果提交回仓库 |

## 一、上传步骤

1. 在 GitHub 新建一个 **Public（公开）** 仓库（例如仓库名 `my-iptv`）。
2. 把本目录里的 `live.m3u`、`international.m3u` 上传到仓库根目录。
3. 确认仓库默认分支名（常见为 `main`，旧仓库可能是 `master`），下面链接里的分支名要与之对应。

## 二、订阅直链（把占位符换成你的信息）

> 占位符：`<用户名>` = 你的 GitHub 账号；`<仓库名>` = 上面新建的仓库；`<分支>` = `main` 或 `master`。

### 国内主用源 `live.m3u`

**原始 raw 链接：**
```
https://raw.githubusercontent.com/<用户名>/<仓库名>/<分支>/live.m3u
```

**jsDelivr 镜像（国内通常更稳，推荐填这条）：**
```
https://cdn.jsdelivr.net/gh/<用户名>/<仓库名>@<分支>/live.m3u
```

**gh-proxy 加速：**
```
https://gh-proxy.com/https://raw.githubusercontent.com/<用户名>/<仓库名>/<分支>/live.m3u
```

### 国际补充源 `international.m3u`

```
https://cdn.jsdelivr.net/gh/<用户名>/<仓库名>@<分支>/international.m3u
```

### 填好后的示例（用户名 `myname`，仓库 `my-iptv`，分支 `main`）

```
https://cdn.jsdelivr.net/gh/myname/my-iptv@main/live.m3u
```

把这条链接粘贴到播放器的「订阅地址 / 远程播放列表」即可。

## 三、自动更新（GitHub Actions 工作流）

仓库已内置定时工作流 `.github/workflows/update-iptv.yml`，无需自己维护 m3u：

- **定时运行**：每天北京时间 08:00（UTC 00:00）自动拉取 `sources.json` 里的上游源，聚合去重、测速后重新生成 `live.m3u` 和 `international.m3u`，并自动提交回仓库。
- **手动触发**：仓库页 → Actions → Update IPTV Sources → Run workflow，可随时手动跑一次。
- **上游源管理**：编辑 `sources.json` 的 `sources` 数组即可增删上游 m3u 地址；`check` 设为 `true` 开启测速（可用线路排前面），`false` 则跳过测速、保留全部线路。
- **脚本**：`scripts/aggregate.py` 仅用 Python 标准库，可在本地直接 `python scripts/aggregate.py` 试运行。

> 说明：Actions 运行在海外服务器，测速结果只用于线路排序参考；个别国内专线在 Runner 上探测不到，不代表你本地网络不可播放。若某频道多条线路都不理想，可在 `sources.json` 里补充更多上游源。

## 四、手动更新源

- 也可以直接在仓库里替换/编辑对应的 `.m3u` 文件并提交（Commit），订阅链接不变，播放器下次拉取即为最新内容。
- jsDelivr 有几分钟缓存，更新后若没刷新，稍等片刻或换 raw / gh-proxy 链接测试。
- 新增频道时保持标准 m3u 格式（见第六节）。

## 五、EPG 节目单（电视报）

播放列表头部已引用公开 EPG：

```
http://epg.51zmt.top:8000/e.xml
```

如播放器需要单独填写 EPG 地址，可填上面这条；备用：`https://live.fanmingming.com/e.xml.gz`。

## 六、m3u 格式规范（新增频道时参照）

```
#EXTM3U x-tvg-url="http://epg.51zmt.top:8000/e.xml"
#EXTINF:-1 tvg-name="CCTV1" tvg-logo="https://台标地址" group-title="央视频道",CCTV 1
http://流地址.m3u8
```

- 文件编码：**UTF-8（无 BOM）**，避免中文台名乱码。
- 每个频道两行：`#EXTINF` 信息行 + 流地址行。
- `group-title` 决定播放器里的分组；`tvg-logo` 为台标图。

## 七、注意事项

- 仓库必须 **Public**，私有仓库的 raw 链接无法匿名访问。
- 单个 m3u 文件建议小于 20MB（jsDelivr 限制）。
- 公开 IPTV 线路时效较短，个别频道打不开时，切换同频道的备用线路即可。

## 免责说明

本仓库仅收录互联网公开可访问的免费源，供个人技术测试与学习使用；频道版权归各电视台及权利人所有。请在所在地法律法规允许的范围内收看，勿用于商业用途。
