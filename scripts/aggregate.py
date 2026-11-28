# -*- coding: utf-8 -*-
"""
聚合多个公开 IPTV 上游 m3u，按频道名去重合并多线路，可选测速后生成：
  live.m3u            国内频道（央视/卫视/地方/专题等）
  international.m3u   国际/其它频道

仅使用 Python 标准库，可直接在 GitHub Actions (ubuntu-latest) 运行。
上游列表见仓库根目录 sources.json。
"""
import os, re, json, ssl, socket, urllib.request, urllib.error, collections
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCES_FILE = os.path.join(ROOT, "sources.json")
EPG = "http://epg.51zmt.top:8000/e.xml"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")

GROUP_MAP = {
    "央视": "央视频道", "央视频道": "央视频道", "CCTV": "央视频道",
    "卫视": "卫视频道", "卫视频道": "卫视频道",
    "地方": "地方频道", "地方频道": "地方频道",
}
INTL = {"General", "News", "Movies", "Music", "Sports", "Kids", "Education",
        "Entertainment", "Documentary", "Business", "Lifestyle", "Culture",
        "Religious", "Science", "Weather", "Shop", "Travel", "Family", "Classic",
        "Undefined", "Animation;Kids", "Kids;Lifestyle", "Education;Outdoor",
        "Education;Science", "Legislative", "General;Travel",
        "Education;Lifestyle;Science", "Education;Kids;Lifestyle;Science",
        "Kids;Education;Lifestyle;Science"}

GROUP_ORDER = ["央视频道", "卫视频道", "地方频道", "电影频道", "纪录频道", "儿童频道",
               "音乐频道", "NewTV", "SiTV", "iHOT", "春晚频道", "数字频道", "解说频道",
               "教育", "影视", "超高", "其他", "其它", "国际/其它"]

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
socket.setdefaulttimeout(10)


def norm_group(g, name=""):
    g = (g or "").strip()
    if g in GROUP_MAP:
        return GROUP_MAP[g]
    if g in INTL:
        return "国际/其它"
    return g or "未分组"


def clean_name(raw):
    s = raw or ""
    s = re.sub(r'(tvg-name|tvg-logo|tvg-id|group-title)\s*=\s*"[^"]*"', "", s)
    s = s.split(",")[-1]
    s = re.sub(r'(tvg-name|tvg-logo|tvg-id|group-title)\s*=\s*[^ ]*', "", s)
    s = s.strip(" -,")
    s = re.sub(r"\s*(50\s*FPS|HEVC|线路\s*\d+)$", "", s, flags=re.I).strip()
    return s


def norm_key(s):
    return re.sub(r"\s+", "", s or "").upper()


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=10, context=ctx) as r:
        return r.read().decode("utf-8", errors="replace")


def parse_m3u(text):
    """产出 (name, group, logo, url) 列表。"""
    out = []
    ext = None
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("#EXTINF"):
            name = line.split(",", 1)[-1].strip()
            g = re.search(r'group-title="([^"]*)"', line)
            logo = re.search(r'tvg-logo="([^"]*)"', line)
            tvn = re.search(r'tvg-name="([^"]*)"', line)
            ext = dict(name=name,
                       group=norm_group(g.group(1) if g else "", name),
                       logo=logo.group(1) if logo else "",
                       tvg=tvn.group(1) if tvn else name)
        elif line.startswith("http") and ext:
            out.append((clean_name(ext["tvg"] or ext["name"]), ext["group"],
                        ext["logo"], line))
            ext = None
    return out


def probe(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=5, context=ctx) as r:
            body = r.read(1024)
            ct = r.headers.get("Content-Type", "")
            ok = r.status in (200, 206) and (
                b"#EXT" in body or "mpegurl" in ct or "octet-stream" in ct
                or "mp2t" in ct or "video" in ct)
            return url, ok
    except Exception:
        return url, False


def main():
    cfg = json.load(open(SOURCES_FILE, encoding="utf-8"))
    do_check = bool(cfg.get("check", True))
    sources = cfg.get("sources", [])

    channels = {}
    order = []
    for src in sources:
        name, url = src.get("name", ""), src.get("url", "")
        try:
            text = fetch(url)
            items = parse_m3u(text)
            print(f"[拉取] {name}: {len(items)} 条线路")
        except Exception as e:
            print(f"[跳过] {name} 拉取失败: {type(e).__name__} {e}")
            continue
        for cname, group, logo, stream in items:
            if not cname or not stream.startswith("http"):
                continue
            if group == "更新时间" or re.match(r"^\d{4}-\d{2}-\d{2}", cname):
                continue
            key = norm_key(cname)
            if key not in channels:
                channels[key] = dict(name=cname, group=group, logo=logo, urls=[])
                order.append(key)
            c = channels[key]
            if group != "未分组" and c["group"] == "未分组":
                c["group"] = group
            if not c["logo"] and logo:
                c["logo"] = logo
            if stream not in c["urls"]:
                c["urls"].append(stream)

    # 测速（可选）：可用线路前置
    ok_urls = set()
    if do_check and order:
        tasks = [(k, u) for k in order for u in channels[k]["urls"]]
        print(f"[测速] 共 {len(tasks)} 条线路 ...")
        with ThreadPoolExecutor(max_workers=20) as ex:
            futs = {ex.submit(probe, u): (k, u) for k, u in tasks}
            done = 0
            for f in as_completed(futs):
                k, u = futs[f]
                _, ok = f.result()
                if ok:
                    ok_urls.add(u)
                done += 1
                if done % 40 == 0:
                    print(f"  进度 {done}/{len(tasks)}")
        for k in order:
            c = channels[k]
            good = [u for u in c["urls"] if u in ok_urls]
            rest = [u for u in c["urls"] if u not in ok_urls]
            c["urls"] = good + rest

    def gpos(g):
        return GROUP_ORDER.index(g) if g in GROUP_ORDER else 99

    domestic, intl = [], []
    for k in order:
        c = channels[k]
        if not c["urls"]:
            continue
        (intl if c["group"] == "国际/其它" else domestic).append(c)
    domestic.sort(key=lambda m: (gpos(m["group"]), m["name"]))
    intl.sort(key=lambda m: (gpos(m["group"]), m["name"]))

    def write_m3u(path, items):
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(f'#EXTM3U x-tvg-url="{EPG}"\n')
            for m in items:
                for i, u in enumerate(m["urls"]):
                    label = m["name"] if i == 0 else f"{m['name']} 线路{i+1}"
                    f.write(f'#EXTINF:-1 tvg-name="{m["name"]}" tvg-logo="{m["logo"]}" '
                            f'group-title="{m["group"]}",{label}\n{u}\n')

    write_m3u(os.path.join(ROOT, "live.m3u"), domestic)
    write_m3u(os.path.join(ROOT, "international.m3u"), intl)

    stat = collections.Counter(m["group"] for m in domestic)
    print(f"\n[完成] 国内 {len(domestic)} 个频道, 国际 {len(intl)} 个频道")
    for g, n in stat.most_common():
        print(f"  {g}: {n}")


if __name__ == "__main__":
    main()
