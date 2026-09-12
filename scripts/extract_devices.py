import csv
import glob
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT_CSV = os.path.join(ROOT, "devices_world.csv")
import math
import re
from collections import defaultdict

dxf_path = glob.glob(os.path.join(ROOT, "*.dxf"))[0]

# Block definitions: name -> {"texts": [(type, layer, value, x, y)], "inserts": [(name, x, y, sx, sy, rot)]}
blocks = defaultdict(lambda: {"texts": [], "inserts": []})
top_inserts = []          # ENTITIES section: (name, x, y, sx, sy, rot)
top_texts = []            # ENTITIES section: (type, layer, value, x, y)

cur_text = None
cur_insert = None
value = None
layer = ""
coords = {}
section = ""
cur_block = None          # block being defined in BLOCKS section
pending_block = False     # saw BLOCK keyword, waiting for its name (code 2)


def clean_text(v):
    v = re.sub(r"\\P", " ", v)
    v = re.sub(r"\{|\}|\\[A-Za-z][^;]*;?", "", v)
    return v.strip()


def store_text(target):
    global cur_text, value
    if cur_text is None:
        return
    v = clean_text(value or "")
    if v:
        target["texts"].append((cur_text, layer, v,
                                coords.get("x"), coords.get("y")))
    cur_text = None
    value = None


def store_insert(target):
    global cur_insert
    if cur_insert is None:
        return
    target["inserts"].append((cur_insert,
                              coords.get("x", 0.0), coords.get("y", 0.0),
                              coords.get("sx", 1.0), coords.get("sy", 1.0),
                              coords.get("rot", 0.0)))
    cur_insert = None


with open(dxf_path, encoding="utf-8", errors="replace") as f:
    it = iter(f)
    expect_section_name = False
    while True:
        try:
            line = next(it).strip()
        except StopIteration:
            break
        if not line.isdigit():
            continue
        code = int(line)
        val = next(it).rstrip("\r\n")

        if code == 0:
            if section == "BLOCKS" and cur_block is not None:
                if cur_text is not None:
                    store_text(blocks[cur_block])
                elif cur_insert is not None:
                    store_insert(blocks[cur_block])
            elif section == "ENTITIES":
                if cur_text is not None:
                    store_text(top_target)
                elif cur_insert is not None:
                    store_insert(top_target)
            cur_text = None
            cur_insert = None
            value = None
            if val == "SECTION":
                expect_section_name = True
                continue
            if val == "ENDSEC":
                section = ""
                cur_block = None
                expect_section_name = False
                continue
            expect_section_name = False

            if section == "BLOCKS" and cur_block is not None:
                if val == "ENDBLK":
                    cur_block = None
                elif val in ("TEXT", "MTEXT", "ATTRIB"):
                    cur_text, cur_insert = val, None
                    value = None
                    layer = ""
                    coords = {}
                elif val == "INSERT":
                    cur_text, cur_insert = None, ""
                    layer = ""
                    coords = {}
            elif section == "ENTITIES":
                if val in ("TEXT", "MTEXT", "ATTRIB"):
                    cur_text, cur_insert = val, None
                    value = None
                    layer = ""
                    coords = {}
                elif val == "INSERT":
                    cur_text, cur_insert = None, ""
                    layer = ""
                    coords = {}
            if section == "BLOCKS" and val == "BLOCK":
                cur_block = None
                pending_block = True
                layer = ""
                coords = {}
            continue

        if expect_section_name:
            section = val
            expect_section_name = False
            if section == "ENTITIES":
                top_target = {"texts": top_texts, "inserts": top_inserts}
            continue

        if section == "BLOCKS" and pending_block and code == 2:
            cur_block = val
            pending_block = False
            continue

        if cur_text is not None:
            if code == 8:
                layer = val
            elif code in (1, 3) and val.strip():
                value = (value or "") + val
            elif code == 2 and cur_text == "ATTRIB" and not value:
                value = val
            elif code == 10 and "x" not in coords:
                try:
                    coords["x"] = float(val)
                except ValueError:
                    pass
            elif code == 20 and "y" not in coords:
                try:
                    coords["y"] = float(val)
                except ValueError:
                    pass
        elif cur_insert is not None:
            if code == 2:
                cur_insert = val
            elif code == 8:
                layer = val
            elif code == 10 and "x" not in coords:
                try:
                    coords["x"] = float(val)
                except ValueError:
                    pass
            elif code == 20 and "y" not in coords:
                try:
                    coords["y"] = float(val)
                except ValueError:
                    pass
            elif code == 41 and "sx" not in coords:
                coords["sx"] = float(val)
            elif code == 42 and "sy" not in coords:
                coords["sy"] = float(val)
            elif code == 50:
                coords["rot"] = float(val)

print(f"block defs: {len(blocks)}, top inserts: {len(top_inserts)}, top texts: {len(top_texts)}")


def xform(px, py, tr):
    x, y, sx, sy, rot = tr
    px, py = px * sx, py * sy
    if rot:
        r = math.radians(rot)
        px, py = px * math.cos(r) - py * math.sin(r), px * math.sin(r) + py * math.cos(r)
    return px + x, py + y


labels = []       # (value, wx, wy)
arrows = []       # (wx, wy, rot)
seen = set()


def walk(name, tr, path):
    if (name, path) in seen or len(path) > 12:
        return
    seen.add((name, path))
    b = blocks.get(name)
    if b is None:
        return
    for t, layer, v, x, y in b["texts"]:
        if x is None:
            continue
        wx, wy = xform(x, y, tr)
        if layer == "6文字层" and v.isdigit():
            labels.append((v, wx, wy))
        elif layer.startswith("#33设备编号"):
            labels.append(("P" + v, wx, wy))
    for sub, x, y, sx, sy, rot in b["inserts"]:
        if sub == "实心箭头":
            wx, wy = xform(x, y, tr)
            arrows.append((wx, wy, (rot + tr[4]) % 360))
            continue
        r = math.radians(tr[4])
        sub_tr = (tr[0] + tr[2] * (x * math.cos(r) - y * math.sin(r)),
                  tr[1] + tr[3] * (x * math.sin(r) + y * math.cos(r)),
                  tr[2] * sx, tr[3] * sy, (tr[4] + rot) % 360)
        walk(sub, sub_tr, path + "/" + sub)


for t, layer, v, x, y in top_texts:
    if x is None:
        continue
    if layer == "6文字层" and v.isdigit():
        labels.append((v, x, y))
    elif layer.startswith("#33设备编号"):
        labels.append(("P" + v, x, y))

for name, x, y, sx, sy, rot in top_inserts:
    tr = (x, y, sx, sy, rot)
    if name == "实心箭头":
        arrows.append((x, y, rot))
        continue
    walk(name, tr, "/" + name)

# Deduplicate labels by value
best = {}
for v, x, y in labels:
    key = ("P" if v.startswith("P") else "L") + v.lstrip("P")
    if key not in best:
        best[key] = (v, x, y)

with open(OUT_CSV, "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["kind", "value", "x", "y"])
    for k, (v, x, y) in sorted(best.items()):
        w.writerow([k, v, f"{x:.1f}", f"{y:.1f}"])
    for x, y, rot in arrows:
        w.writerow(["ARROW", f"{rot:.1f}", f"{x:.1f}", f"{y:.1f}"])

lab = [(v, x, y) for v, x, y in labels]
if lab:
    xs = [p[1] for p in lab]
    ys = [p[2] for p in lab]
    print(f"labels: {len(best)} unique (raw {len(lab)}), arrows: {len(arrows)}")
    print(f"world x: {min(xs):.0f} ~ {max(xs):.0f}, y: {min(ys):.0f} ~ {max(ys):.0f}")
