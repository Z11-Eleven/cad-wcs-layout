"""提取可见 CAD 箭头，并仅关联到线框范围内唯一的设备编号。"""
import argparse
import csv
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parent
IDENTITY = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)


def entities(path, encoding="utf-8"):
    section, kind, tags = "", None, []
    expect_section = False
    # 按 LF 读取也能处理部分 CAD 导出文件的 CRCRLF。
    with Path(path).open(encoding=encoding, newline="\n") as stream:
        iterator = iter(stream)
        for line in iterator:
            if not line.strip():
                continue
            code, value = int(line.strip()), next(iterator).rstrip("\r\n")
            if code == 0:
                if kind is not None or tags:
                    yield section, kind, tags
                kind, tags = None, []
                if value == "SECTION":
                    section, expect_section = "", True
                elif value == "ENDSEC":
                    section = ""
                else:
                    kind = value
            elif expect_section and code == 2:
                section, expect_section = value, False
            else:
                tags.append((code, value))
        if kind is not None or tags:
            yield section, kind, tags


def bounds(points):
    return (min(p[0] for p in points), min(p[1] for p in points),
            max(p[0] for p in points), max(p[1] for p in points))


def inside(box, point):
    return box[0] - 0.01 <= point[0] <= box[2] + 0.01 and box[1] - 0.01 <= point[1] <= box[3] + 0.01


def transform(point, matrix):
    a, b, c, d, tx, ty = matrix
    x, y = point
    return a * x + c * y + tx, b * x + d * y + ty


def compose(outer, inner):
    a, b, c, d, tx, ty = outer
    e, f, g, h, ux, uy = inner
    return (a * e + c * f, b * e + d * f, a * g + c * h, b * g + d * h,
            a * ux + c * uy + tx, b * ux + d * uy + ty)


def insertion(node, base):
    sx, sy, angle = node["sx"], node["sy"], math.radians(node["rotation"])
    a, b, c, d = sx * math.cos(angle), sx * math.sin(angle), -sy * math.sin(angle), sy * math.cos(angle)
    return a, b, c, d, node["point"][0] - a * base[0] - c * base[1], node["point"][1] - b * base[0] - d * base[1]


def inverse(point, matrix):
    a, b, c, d, tx, ty = matrix
    x, y, determinant = point[0] - tx, point[1] - ty, a * d - b * c
    return (d * x - c * y) / determinant, (-b * x + a * y) / determinant


def arrow_tips(node):
    """识别 7/8 点单向和 10 点双向闭合直线轮廓，排除凹入尾部。"""
    if node["kind"] != "LWPOLYLINE" or not node["closed"] or node["curved"]:
        return []
    points = node["points"]
    if len(points) not in (7, 8, 10):
        return []
    xmin, ymin, xmax, ymax = bounds(points)
    swapped = ymax - ymin > xmax - xmin
    shape = [(p[1], p[0]) if swapped else p for p in points]
    xmin, ymin, xmax, ymax = bounds(shape)
    width, height = xmax - xmin, ymax - ymin
    if height <= 0 or width < 1.5 * height:
        return []
    result = []
    for index, point in enumerate(shape):
        before, after = shape[index - 1], shape[(index + 1) % len(shape)]
        if (abs(before[0] - after[0]) < width * 1e-5
                and abs(before[1] + after[1] - 2 * point[1]) < height * 1e-5
                and abs(before[1] - after[1]) > height * 0.95
                and abs(point[0] - before[0]) > width * 0.25
                and (abs(point[0] - xmin) < width * 1e-5 or abs(point[0] - xmax) < width * 1e-5)):
            shoulder = ((before[0] + after[0]) / 2, (before[1] + after[1]) / 2)
            result.append(((point[1], point[0]), (shoulder[1], shoulder[0])) if swapped else (point, shoulder))
    return result if len(result) == (2 if len(points) == 10 else 1) else []


def cardinal(vector):
    x, y = vector
    if math.hypot(x, y) < 1e-8 or min(abs(x), abs(y)) / max(abs(x), abs(y)) > math.tan(math.radians(1)):
        return None
    return (4 if x > 0 else 3) if abs(x) > abs(y) else (1 if y > 0 else 2)


def label_key(value, x, y):
    value = str(value).strip()
    # 兼容旧提取脚本为 #33设备编号增加的 P 前缀，仅用于证据定位。
    if value.startswith("P") and value[1:].isdigit():
        value = value[1:]
    return value, round(float(x), 1), round(float(y), 1)


def write_csv(path, fields, rows):
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def extract_arrows(dxf_path, world_path, output_dir, encoding="utf-8"):
    output_dir = Path(output_dir)
    with Path(world_path).open(encoding="utf-8-sig", newline="") as stream:
        targets = [row for row in csv.DictReader(stream) if row["kind"] != "ARROW"]
    target_keys = defaultdict(list)
    for index, row in enumerate(targets):
        target_keys[label_key(row["value"], row["x"], row["y"])].append(index)
    blocks, layers, top = {}, {}, []
    block, owner = None, ""
    for section, kind, tags in entities(dxf_path, encoding):
        values = {}
        for code, value in tags:
            values.setdefault(code, value)
        if section == "TABLES" and kind == "LAYER":
            layers[values[2]] = (int(values.get(62, "7")), int(values.get(70, "0")))
        if section == "BLOCKS" and kind == "BLOCK":
            block, owner = values[2], ""
            blocks[block] = {"base": (float(values.get(10, "0")), float(values.get(20, "0"))), "nodes": []}
            continue
        if kind == "ENDBLK":
            block, owner = None, ""
        if kind == "SEQEND":
            owner = ""
        if kind not in ("LINE", "LWPOLYLINE", "INSERT", "TEXT", "MTEXT", "ATTRIB"):
            continue
        if section not in ("BLOCKS", "ENTITIES") or (section == "ENTITIES" and int(values.get(67, "0"))):
            continue
        node = {"kind": kind, "handle": values.get(5, ""), "layer": values.get(8, "0"),
                "hidden": int(values.get(60, "0")),
                "planar": [float(values.get(c, v)) for c, v in ((210, "0"), (220, "0"), (230, "1"))] == [0, 0, 1]}
        if kind == "LWPOLYLINE":
            node.update(points=[(float(value), float(tags[i + 1][1])) for i, (code, value) in enumerate(tags)
                                if code == 10 and i + 1 < len(tags) and tags[i + 1][0] == 20],
                        closed=bool(int(values.get(70, "0")) & 1),
                        curved=any(code == 42 and abs(float(value)) > 1e-8 for code, value in tags))
        elif kind == "LINE":
            node["points"] = [(float(values[10]), float(values[20])), (float(values[11]), float(values[21]))]
        else:
            node["point"] = float(values.get(10, "0")), float(values.get(20, "0"))
            if kind == "INSERT":
                owner = node["handle"]
                node.update(name=values[2], sx=float(values.get(41, "1")), sy=float(values.get(42, "1")),
                            rotation=float(values.get(50, "0")), array=int(values.get(70, "1")) > 1 or int(values.get(71, "1")) > 1)
            else:
                text = "".join(value for code, value in tags if code in (1, 3))
                node.update(value=re.sub(r"\{|\}|\\[A-Za-z][^;]*;?", "", text.replace("\\P", " ")).strip(),
                            owner=owner if kind == "ATTRIB" else "")
        if section == "BLOCKS" and block is not None:
            blocks[block]["nodes"].append(node)
        elif section == "ENTITIES":
            top.append(node)
    arrows, frames, pending = [], {}, defaultdict(set)
    skipped = Counter()

    def walk(nodes, matrix, inherited, path, stack):
        points = []
        child_inserts = {node["handle"]: node for node in nodes if node["kind"] == "INSERT"}
        for node in nodes:
            layer = node["layer"] if node["layer"] != "0" else inherited
            color, flags = layers.get(layer, (7, 0))
            if node["hidden"] or color < 0 or flags & 1:
                continue
            if not node["planar"]:
                skipped["非XY平面实体"] += 1
                continue
            kind = node["kind"]
            if kind == "INSERT":
                child = blocks.get(node["name"])
                if not child or node["name"] in stack:
                    continue
                if node["array"] or node["sx"] == 0 or node["sy"] == 0:
                    skipped["阵列或零缩放插入"] += 1
                    continue
                walk(child["nodes"], compose(matrix, insertion(node, child["base"])), layer,
                     path + "/" + node["handle"], stack + (node["name"],))
            elif kind in ("LINE", "LWPOLYLINE"):
                points.extend(node["points"])
                tips = arrow_tips(node)
                if not tips:
                    continue
                vectors = []
                for tip, shoulder in tips:
                    tip, shoulder = transform(tip, matrix), transform(shoulder, matrix)
                    vectors.append((tip[0] - shoulder[0], tip[1] - shoulder[1]))
                dirs = {cardinal(vector) for vector in vectors}
                polygon = [transform(point, matrix) for point in node["points"]]
                box = bounds(polygon)
                arrows.append({"cad_handle": node["handle"], "instance_path": path,
                               "layer": layer, "x": (box[0] + box[2]) / 2, "y": (box[1] + box[3]) / 2,
                               "arrowdirection": ",".join(map(str, sorted(dirs))) if None not in dirs else "",
                               "association": "unresolved", "target_indices": [], "points": polygon})
            else:
                point = transform(node["point"], matrix)
                matches = target_keys.get(label_key(node["value"], *point), [])
                if len(matches) == 1:
                    parent_path = path + "/" + node["owner"] if node["owner"] in child_inserts else path
                    pending[parent_path].add(matches[0])
        if points and path != "model":
            frames[path] = {"box": bounds(points), "matrix": matrix}

    walk(top, IDENTITY, "0", "model", ())
    devices = [(frame, pending[path]) for path, frame in frames.items() if pending[path]]
    associations = defaultdict(list)
    for arrow in arrows:
        candidates, complete = set(), set()
        for frame, labels in devices:
            if inside(frame["box"], inverse((arrow["x"], arrow["y"]), frame["matrix"])):
                candidates.update(labels)
                if all(inside(frame["box"], inverse(point, frame["matrix"])) for point in arrow["points"]):
                    complete.update(labels)
        arrow["target_indices"] = sorted(candidates)
        if len(candidates) == len(complete) == 1 and arrow["arrowdirection"]:
            index = next(iter(candidates))
            arrow["association"] = "unique_device"
            associations[index].append(arrow)
        arrow["candidate_values"] = ";".join(targets[i]["value"] for i in sorted(candidates))
    station_rows = []
    for index, target in enumerate(targets):
        matched = associations[index]
        station_rows.append({"value": target["value"], "x": target["x"], "y": target["y"],
                             "arrowdirection": ",".join(map(str, sorted({int(value) for arrow in matched
                                                                       for value in arrow["arrowdirection"].split(",")}))),
                             "association": "unique_device" if matched else "unresolved",
                             "arrow_handles": ";".join(arrow["instance_path"] + "/" + arrow["cad_handle"] for arrow in matched)})
    output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(output_dir / "cad_arrows.csv", ["cad_handle", "instance_path", "layer", "x", "y", "arrowdirection", "association", "candidate_values"], arrows)
    write_csv(output_dir / "station_arrows.csv", ["value", "x", "y", "arrowdirection", "association", "arrow_handles"], station_rows)
    summary = {"source_dxf": str(Path(dxf_path).resolve()), "visible_arrow_contours": len(arrows),
               "associated_arrows": sum(arrow["association"] == "unique_device" for arrow in arrows),
               "stations_with_arrows": sum(bool(row["arrowdirection"]) for row in station_rows),
               "unresolved_arrows": sum(arrow["association"] == "unresolved" for arrow in arrows), "skipped": dict(skipped)}
    (output_dir / "arrow_extraction_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dxf", type=Path)
    parser.add_argument("--world", type=Path, default=ROOT / "devices_world.csv")
    parser.add_argument("--output-dir", type=Path, default=ROOT)
    parser.add_argument("--encoding", default="utf-8")
    args = parser.parse_args()
    if args.dxf is None:
        candidates = list(ROOT.glob("*.dxf"))
        if len(candidates) != 1:
            parser.error("请用 --dxf 指定唯一的输入图纸")
        args.dxf = candidates[0]
    extract_arrows(args.dxf, args.world, args.output_dir, args.encoding)
