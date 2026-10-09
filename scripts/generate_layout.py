import csv
import os
from collections import Counter
from datetime import datetime

from wcs_schema import WCS_FIELDS, blank_row

ROOT = os.path.dirname(os.path.abspath(__file__))
WORLD_CSV = os.path.join(ROOT, "devices_world.csv")
ARROW_CSV = os.path.join(ROOT, "station_arrows.csv")
LAYOUT_CSV = os.path.join(ROOT, "wcs_layout.csv")

# ---- 可调参数(接入真实 WCS 库后可再标定) ----
MM_PER_CELL = 1150.0   # 1 格对应的 CAD 毫米数(中位设备间距)
OFFSET_X = 0           # 画布平移,格子单位
OFFSET_Y = 0
WIDTH = 1              # CAD 提取默认 1x1;链路填充跨度由 wcs_monitor.html 算好后写回
HEIGHT = 1
GROUP_NAME = "Convery"     # groupname
ZONE_CODE = "输送机监控"   # zonecode
AREA_CODE = ""             # 项目区域码未知,留空
EQUIPMENT_TYPE = "Convery"
# createtime 在导出时统一填当前时间;status/belong/stationtype 按业务默认值
STATUS = "1"               # 预览图只显示 status=1 的设备
BELONG = "1"
STATION_TYPE = "0"         # 设备类型/功能,目前已知取值 1,3,5,6,7,8,10,11,16
CREATETIME = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# 文字初始水平，与输送箭头独立。没有明确 CAD 来源的箭头留空。

rows = list(csv.DictReader(open(WORLD_CSV, encoding="utf-8-sig")))
devices = [(r["value"], float(r["x"]), float(r["y"]))
           for r in rows if r["kind"].startswith("L")]

if not devices:
    raise SystemExit("devices_world.csv 中没有设备标签")

# ---- CAD 坐标 -> 画布格子(y 朝下) ----
y_max = max(y for _, _, y in devices)
x_min = min(x for _, x, _ in devices)

def to_grid(x, y):
    return (round((x - x_min) / MM_PER_CELL) + OFFSET_X,
            round((y_max - y) / MM_PER_CELL) + OFFSET_Y)

# ---- 只保留已关联到设备的 CAD 箭头，多方向不截断 ----
matched = {}
if os.path.isfile(ARROW_CSV):
    with open(ARROW_CSV, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            if r.get("association") not in ("unique_device", "verified") or not r.get("arrow_handles"):
                continue
            parts = {p.strip() for p in r.get("arrowdirection", "").split(",") if p.strip()}
            if not parts:
                continue
            if not parts <= {"1", "2", "3", "4"}:
                raise ValueError("CAD 箭头证据应使用 1上/2下/3左/4右：" + r["value"])
            key = (r["value"], round(float(r["x"]), 1), round(float(r["y"]), 1))
            matched.setdefault(key, set()).update(parts)

# ---- 输出布局表 ----
out_rows = []
for v, x, y in sorted(devices, key=lambda p: int(p[0])):
    gx, gy = to_grid(x, y)
    parts = matched.get((v, round(x, 1), round(y, 1)), set())
    arrow_type = ",".join(sorted(parts, key=int))
    src = "arrow" if parts else "none"
    row = blank_row()
    row.update({
        "itemid": v,
        "itemname": v,
        "groupname": GROUP_NAME,
        "stationno": v,
        "locationx": gx,
        "locationy": gy,
        "width": WIDTH,
        "height": HEIGHT,
        "direction": "",
        "createtime": CREATETIME,
        "status": STATUS,
        "belong": BELONG,
        "stationtype": STATION_TYPE,
        "zonecode": ZONE_CODE,
        "areacode": AREA_CODE,
        "arrowdirection": arrow_type,
        "equipmentType": EQUIPMENT_TYPE,
        "direction_source": src,   # 统计用,不写入 CSV
    })
    out_rows.append(row)

# 链路填充跨度已并入 width/height,由 wcs_monitor.html 按当前坐标计算后写回,
# 这里保持 CAD 提取口径:width/height 一律输出 1x1。
fieldnames = WCS_FIELDS
with open(LAYOUT_CSV, "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
    w.writeheader()
    w.writerows(out_rows)

# ---- 统计 ----
cells = [(r["locationx"], r["locationy"]) for r in out_rows]
c = Counter(cells)
collisions = sum(n - 1 for n in c.values() if n > 1)
gx_span = max(p[0] for p in cells) - min(p[0] for p in cells)
gy_span = max(p[1] for p in cells) - min(p[1] for p in cells)
n_arrow = sum(1 for r in out_rows if r["direction_source"] == "arrow")
n_none = sum(1 for r in out_rows if r["direction_source"] == "none")
print(f"设备: {len(out_rows)} | 画布: {gx_span}x{gy_span} 格 | 同格设备: {collisions}")
n_with_arrow = sum(1 for r in out_rows if r["arrowdirection"])
print(f"arrowdirection 来源: CAD 箭头 {n_arrow} | 空 {n_none}")
dist = Counter(r["arrowdirection"] for r in out_rows)
ARROW_NAMES = {0: "空", 1: "上", 2: "下", 3: "左", 4: "右"}
detail = " | ".join(f"{'/'.join(ARROW_NAMES[int(p)] for p in k.split(',')) if k else '空'}={dist[k]}" for k in sorted(dist))
print(f"arrowdirection 类型: 有箭头 {n_with_arrow} 台 / 空 {len(out_rows) - n_with_arrow} 台 ({detail})")
print("width/height 输出 1;链路填充由 wcs_monitor.html 计算后写回")
print(f"已生成 wcs_layout.csv (WCS 设备表 {len(fieldnames)} 列)")
