import csv
import math
import os
from datetime import datetime

from wcs_schema import WCS_FIELDS, blank_row

ROOT = os.path.dirname(os.path.abspath(__file__))
WORLD_CSV = os.path.join(ROOT, "devices_world.csv")
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

# direction 枚举: 1=右, 2=上(画布 y 减小), 3=左, 4=下(画布 y 增大)
ANGLE_TO_DIRECTION = {0: 1, 90: 2, 180: 3, 270: 4, 360: 1}
# arrowdirection 多选方向:空字符串/0=无箭头,1=右,2=左,3=下,4=上;多选用逗号分隔
# CAD 箭头角度 -> 箭头类型(CAD 90 度朝上,对应画布 y 减小)
ANGLE_TO_ARROW = {0: 1, 90: 4, 180: 2, 270: 3, 360: 1}
# 编号序列推断出的流向(direction 枚举 1右 2上 3左 4下)-> 箭头类型
DIRECTION_TO_ARROW = {1: 1, 2: 4, 3: 2, 4: 3}
NEAR_RADIUS = 8000.0    # 编号与箭头锚点匹配距离,mm

from collections import defaultdict

rows = list(csv.DictReader(open(WORLD_CSV, encoding="utf-8-sig")))
devices = [(r["value"], float(r["x"]), float(r["y"]))
           for r in rows if r["kind"].startswith("L")]
arrows = [(float(r["value"]), float(r["x"]), float(r["y"]))
          for r in rows if r["kind"] == "ARROW"]

if not devices:
    raise SystemExit("devices_world.csv 中没有设备标签")

# ---- CAD 坐标 -> 画布格子(y 朝下) ----
y_max = max(y for _, _, y in devices)
x_min = min(x for _, x, _ in devices)

def to_grid(x, y):
    return (round((x - x_min) / MM_PER_CELL) + OFFSET_X,
            round((y_max - y) / MM_PER_CELL) + OFFSET_Y)

# ---- 方向:近距箭头锚点 -> 编号序列推断 ----
matched = {}
for v, x, y in devices:
    best = None
    for a_deg, ax, ay in arrows:
        d = math.hypot(x - ax, y - ay)
        if d <= NEAR_RADIUS and (best is None or d < best[0]):
            best = (d, a_deg)
    if best:
        matched[v] = (best[1], "arrow")

grid_pos = {v: to_grid(x, y) for v, x, y in devices}
world_pos = {v: (x, y) for v, x, y in devices}

row_groups = defaultdict(list)
col_groups = defaultdict(list)
for v, (gx, gy) in grid_pos.items():
    row_groups[gy].append(v)
    col_groups[gx].append(v)

def sequence_direction(members, coord):
    """coord(v) 返回沿轴坐标;返回编号递增方向: +1 或 -1"""
    ms = sorted(members, key=coord)
    nums = [int(v) for v in ms]
    inc = sum(1 for a, b in zip(nums, nums[1:]) if b > a)
    dec = sum(1 for a, b in zip(nums, nums[1:]) if b < a)
    if inc == dec:
        return None
    return 1 if inc > dec else -1

seq_dirs = {}
for gy, members in row_groups.items():
    if len(members) < 2:
        continue
    s = sequence_direction(members, lambda v: world_pos[v][0])
    if s is not None:
        for v in members:
            seq_dirs.setdefault(v, (1 if s > 0 else 3, "row"))

for gx, members in col_groups.items():
    if len(members) < 2:
        continue
    s = sequence_direction(members, lambda v: world_pos[v][1])
    if s is not None:
        d = 2 if s > 0 else 4   # CAD y 递增 = 画布向上
        for v in members:
            if v not in seq_dirs or len(col_groups[gx]) > len(row_groups[grid_pos[v][1]]):
                seq_dirs[v] = (d, "col")

for v, _, _ in devices:
    if v not in matched and v in seq_dirs:
        matched[v] = (seq_dirs[v][0], "sequence")

# ---- 输出布局表 ----
out_rows = []
for v, x, y in sorted(devices, key=lambda p: int(p[0])):
    gx, gy = to_grid(x, y)
    if v in matched:
        val, src = matched[v]
        if src == "arrow":
            deg = int(val) % 360
            direction = ANGLE_TO_DIRECTION.get(deg, "")
            arrow_type = ANGLE_TO_ARROW.get(deg, 0)
        else:
            # 没有匹配到 CAD 箭头:用编号序列推断出来的流向换算成箭头类型
            direction = val
            arrow_type = DIRECTION_TO_ARROW.get(val, 0)
    else:
        src, direction, arrow_type = "none", "", 0
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
        "direction": direction,
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
from collections import Counter
c = Counter(cells)
collisions = sum(n - 1 for n in c.values() if n > 1)
gx_span = max(p[0] for p in cells) - min(p[0] for p in cells)
gy_span = max(p[1] for p in cells) - min(p[1] for p in cells)
n_arrow = sum(1 for r in out_rows if r["direction_source"] == "arrow")
n_seq = sum(1 for r in out_rows if r["direction_source"] == "sequence")
n_none = sum(1 for r in out_rows if r["direction_source"] == "none")
print(f"设备: {len(out_rows)} | 画布: {gx_span}x{gy_span} 格 | 同格设备: {collisions}")
n_with_arrow = sum(1 for r in out_rows if int(r["arrowdirection"] or 0) > 0)
print(f"arrowdirection 来源: CAD 箭头 {n_arrow} | 流向推断 {n_seq} | 空 {n_none}")
dist = Counter(int(r["arrowdirection"] or 0) for r in out_rows)
ARROW_NAMES = {0: "空", 1: "右", 2: "左", 3: "下", 4: "上"}
detail = " | ".join(f"{ARROW_NAMES[k]}={dist[k]}" for k in sorted(dist))
print(f"arrowdirection 类型: 有箭头 {n_with_arrow} 台 / 空 {len(out_rows) - n_with_arrow} 台 ({detail})")
print("width/height 输出 1;链路填充由 wcs_monitor.html 计算后写回")
print(f"已生成 wcs_layout.csv (WCS 设备表 {len(fieldnames)} 列)")
