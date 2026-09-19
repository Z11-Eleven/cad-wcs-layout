import csv
import io
import json
import os
import re

from wcs_schema import (WCS_FIELDS, FIELD_LABELS, SINGLE_EDIT_FIELDS,
                        BATCH_EDIT_FIELDS, READONLY_FIELDS)


ROOT = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(ROOT, "wcs_layout.csv")
COLOR_CONFIG_PATH = os.path.join(ROOT, "station_colors.json")

DEFAULT_STATION_COLORS = {
    "__default__": {"fill": "#ccdcf0", "border": "#55708c", "text": "#1b3350"},
    "0": {"fill": "#ccdcf0", "border": "#55708c", "text": "#1b3350"},
    "1": {"fill": "#d1fae5", "border": "#059669", "text": "#065f46"},
    "3": {"fill": "#fef3c7", "border": "#d97706", "text": "#92400e"},
    "5": {"fill": "#ede9fe", "border": "#7c3aed", "text": "#5b21b6"},
    "6": {"fill": "#fce7f3", "border": "#db2777", "text": "#9d174d"},
    "7": {"fill": "#cffafe", "border": "#0891b2", "text": "#155e75"},
    "8": {"fill": "#ffedd5", "border": "#ea580c", "text": "#9a3412"},
    "10": {"fill": "#ccfbf1", "border": "#0d9488", "text": "#115e59"},
    "11": {"fill": "#e0e7ff", "border": "#4f46e5", "text": "#3730a3"},
    "16": {"fill": "#fee2e2", "border": "#dc2626", "text": "#991b1b"},
}


def _int(value, default=0):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _arrow_types(value):
    """arrowdirection 多选值；兼容旧枚举 5=左右、6=上下。"""
    found = []
    for part in re.split(r"[,，;；\s]+", str(value or "").strip()):
        if not part:
            continue
        try:
            arrow = int(float(part))
        except ValueError:
            continue
        values = (1, 2) if arrow == 5 else ((3, 4) if arrow == 6 else (arrow,))
        for item in values:
            if item in (1, 2, 3, 4) and item not in found:
                found.append(item)
    return sorted(found)


def devices_from_rows(rows):
    """CSV 行 -> 页面设备对象;raw 保留整行 WCS 字段,保存时原样带回。"""
    devices = []
    for r in rows:
        raw = {k: str(r.get(k) or "") for k in WCS_FIELDS}
        itemid = raw["itemid"]
        devices.append({
            "id": itemid,
            "name": raw["itemname"] or itemid,
            "remark": raw["remark"],
            "x": _int(raw["locationx"]),
            "y": _int(raw["locationy"]),
            "w": max(1, _int(raw["width"], 1)),
            "h": max(1, _int(raw["height"], 1)),
            # arrowdirection 是逗号分隔的多选方向：1右 2左 3下 4上。
            "arrows": _arrow_types(raw["arrowdirection"]),
            "field5": _int(raw["field5"]),
            "raw": raw,
        })
    return devices


def load_rows():
    data = open(CSV_PATH, "rb").read()
    errors = []
    for encoding in ("utf-8-sig", "gb18030"):
        try:
            text = data.decode(encoding)
            return list(csv.DictReader(io.StringIO(text, newline="")))
        except UnicodeDecodeError as exc:
            errors.append(f"{encoding}: {exc}")
    raise UnicodeDecodeError("wcs_layout.csv", data, 0, min(1, len(data)),
                             "无法按 UTF-8 或 GB18030 解码；" + "; ".join(errors))


def load_station_color_config():
    colors = {k: dict(v) for k, v in DEFAULT_STATION_COLORS.items()}
    remark_rules = []
    if not os.path.isfile(COLOR_CONFIG_PATH):
        return {"colors": colors, "remark_rules": remark_rules}
    try:
        with open(COLOR_CONFIG_PATH, encoding="utf-8-sig") as f:
            saved = json.load(f)
        # 兼容旧版直接以 stationtype 为键的配置文件。
        saved_colors = saved.get("colors", {}) if isinstance(saved, dict) and "colors" in saved else saved
        if isinstance(saved_colors, dict):
            for key, value in saved_colors.items():
                if isinstance(value, dict):
                    colors[str(key)] = {
                        "fill": str(value.get("fill") or colors["__default__"]["fill"]),
                        "border": str(value.get("border") or colors["__default__"]["border"]),
                        "text": str(value.get("text") or colors["__default__"]["text"]),
                    }
        saved_rules = saved.get("remark_rules", []) if isinstance(saved, dict) else []
        if isinstance(saved_rules, list):
            for rule in saved_rules:
                keyword = str(rule.get("contains") or "").strip() if isinstance(rule, dict) else ""
                if keyword:
                    remark_rules.append({
                        "contains": keyword,
                        "fill": str(rule.get("fill") or colors["__default__"]["fill"]),
                        "border": str(rule.get("border") or colors["__default__"]["border"]),
                        "text": str(rule.get("text") or colors["__default__"]["text"]),
                    })
    except (OSError, ValueError, TypeError):
        pass
    return {"colors": colors, "remark_rules": remark_rules}


def load_station_colors():
    """保留给旧调用方使用。"""
    return load_station_color_config()["colors"]

TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>输送机布局编辑</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  html, body { height: 100%; }
  body { font-family: "Microsoft YaHei", "PingFang SC", sans-serif; background: #e9edf1; color: #1c2733; overflow: hidden; }
  header {
    display: flex; align-items: center; gap: 10px; flex-wrap: wrap;
    padding: 8px 14px; background: #1c2733; color: #e8edf2;
  }
  header h1 { font-size: 16px; font-weight: 600; letter-spacing: 0; margin-right: 6px; }
  .seg { display: flex; }
  .seg button {
    border: 1px solid #3a4a5a; background: transparent; color: #c6d0da;
    padding: 5px 13px; cursor: pointer; font-size: 13px;
  }
  .seg button:first-child { border-radius: 4px 0 0 4px; }
  .seg button:last-child { border-radius: 0 4px 4px 0; }
  .seg button.on { background: #2d3d4f; color: #fff; border-color: #4a5d72; }
  .btn {
    border: 1px solid #3a4a5a; background: transparent; color: #c6d0da;
    padding: 5px 11px; border-radius: 4px; cursor: pointer; font-size: 13px;
    display: inline-flex; align-items: center; gap: 6px;
  }
  .btn:hover { background: #2d3d4f; }
  .btn:disabled { opacity: .4; cursor: default; }
  .btn.primary { background: #2563eb; border-color: #2563eb; color: #fff; }
  .btn.primary:hover { background: #1d4fd8; }
  .btn.danger { color: #ffb4a8; border-color: #6b3a34; }
  .btn.danger:hover { background: #4a2320; }
  .tools { display: flex; align-items: center; gap: 6px; }
  .tools button {
    width: 30px; height: 30px; display: inline-flex; align-items: center; justify-content: center;
    border: 1px solid #3a4a5a; background: transparent; color: #c6d0da;
    border-radius: 4px; cursor: pointer;
  }
  .tools button:hover { background: #2d3d4f; }
  .tools svg { width: 15px; height: 15px; }
  .mstat { font-size: 12px; color: #b9c4cf; }
  #map-search { display: flex; align-items: center; gap: 5px; margin-left: auto; }
  #map-search input {
    width: 150px; height: 30px; padding: 4px 8px; border: 1px solid #3a4a5a;
    border-radius: 4px; background: #111c28; color: #e8edf2; font-size: 12px;
  }
  #map-search input::placeholder { color: #8291a0; }
  #map-search input:focus { outline: none; border-color: #60a5fa; }
  #map-search button { height: 30px; }
  #edit-tools { display: none; align-items: center; gap: 6px; margin-left: 8px; }
  body.editing #edit-tools { display: inline-flex; }
  #stage { position: relative; height: calc(100vh - 49px); overflow: hidden; cursor: grab; }
  #stage.panning { cursor: grabbing; }
  body.editing #stage { cursor: crosshair; }
  #world { position: absolute; left: 0; top: 0; transform-origin: 0 0; }
  #grid-bg { position: absolute; pointer-events: none;
    background-image:
      linear-gradient(to right, rgba(28,39,51,.08) 1px, transparent 1px),
      linear-gradient(to bottom, rgba(28,39,51,.08) 1px, transparent 1px);
  }
  #arrows { position: absolute; left: 0; top: 0; pointer-events: none; }
  .blk {
    position: absolute; border-radius: 3px; display: flex; align-items: center; justify-content: center;
    flex-direction: column; line-height: 1.15; overflow: visible; text-align: center;
    font-size: 11px; font-weight: 600; color: #1b3350; user-select: none;
    background: #ccdcf0; border: 1px solid #55708c; box-shadow: 0 1px 2px rgba(20,30,40,.22);
    z-index: 1;
  }
  .blk .nm, .blk .rm { max-width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .blk .rm { font-weight: 400; font-size: 9px; opacity: .72; }
  .blk.text-vertical { flex-direction: row; }
  .blk.text-vertical .nm, .blk.text-vertical .rm {
    writing-mode: vertical-rl; text-orientation: upright; white-space: nowrap;
    max-width: none; max-height: 100%; line-height: 1; font-size: var(--vertical-font-size, 9px);
  }
  .blk.text-vertical .rm { font-size: var(--vertical-remark-size, 7px); }
  .overlap-badge, .overlap-anchor {
    display: grid; place-items: center; border-radius: 999px; background: #dc2626; color: #fff;
    border: 2px solid #edf2f6; font-size: 10px; font-weight: 700; cursor: pointer;
    box-shadow: 0 2px 5px rgba(20,30,40,.3); user-select: none;
  }
  .overlap-badge {
    position: absolute; right: -5px; top: -5px; min-width: 15px; height: 15px; padding: 0 2px;
    z-index: 2; border-width: 1px; font-size: 8px; box-shadow: 0 1px 3px rgba(20,30,40,.25);
  }
  .overlap-anchor { position: absolute; width: 25px; height: 25px; z-index: 110000; }
  .overlap-collapsed { outline: 2px solid rgba(220,38,38,.2); }
  body.editing .blk { cursor: pointer; }
  body.editing .blk:hover { box-shadow: 0 1px 2px rgba(20,30,40,.16), 0 0 0 2px #2563eb; }
  .blk.sel { outline: 2px solid #1d4fd8; outline-offset: 1px; box-shadow: 0 0 0 3px rgba(37,99,235,.22), 0 1px 3px rgba(20,30,40,.25); }
  .blk.located { animation: locate-pulse .65s ease-in-out 3; }
  @keyframes locate-pulse {
    0%, 100% { box-shadow: 0 0 0 2px #ef4444, 0 1px 3px rgba(20,30,40,.25); }
    50% { box-shadow: 0 0 0 7px rgba(239,68,68,.28), 0 1px 3px rgba(20,30,40,.25); }
  }
  #arrows { z-index: 100000; }
  #marquee {
    position: absolute; display: none; pointer-events: none;
    border: 1.5px dashed #1d4fd8; background: rgba(37,99,235,.15); z-index: 150000;
  }
  #tip {
    position: fixed; pointer-events: none; display: none; z-index: 50;
    background: #1c2733; color: #e8edf2; padding: 7px 10px; border-radius: 5px;
    font-size: 12px; line-height: 1.7; box-shadow: 0 4px 14px rgba(10,18,28,.35);
  }
  #tip b { color: #fff; }
  #panel {
    position: absolute; right: 14px; top: 14px; width: 340px; background: #fff;
    border: 1px solid #c4ced7; border-radius: 6px; box-shadow: 0 6px 18px rgba(20,30,40,.16);
    display: none; z-index: 30; padding: 12px;
    max-height: calc(100vh - 104px); overflow: auto;
    overscroll-behavior: contain; scrollbar-gutter: stable;
  }
  #panel.show { display: block; }
  #panel h3 { font-size: 13px; margin-bottom: 9px; color: #22313f; }
  .frow { display: flex; align-items: center; gap: 6px; margin-bottom: 7px; }
  .frow label {
    width: 168px; font-size: 11px; color: #5b6975; flex: none;
    line-height: 1.35; word-break: break-word;
  }
  .frow input, .frow select {
    flex: 1; min-width: 0; padding: 4px 6px; border: 1px solid #c4ced7; border-radius: 4px;
    font-size: 12px; color: #1c2733; background: #fff;
  }
  .frow input:disabled { background: #f2f5f8; color: #5b6975; }
  .arrowrow { display: flex; align-items: center; gap: 6px; }
  .arrowrow .val { flex: 1; font-size: 12px; font-variant-numeric: tabular-nums; }
  .hint { font-size: 11px; color: #7b8794; margin-top: 6px; line-height: 1.5; }
  .arrowrow button {
    width: 26px; height: 24px; border: 1px solid #c4ced7; background: #fff; border-radius: 4px;
    cursor: pointer; font-size: 13px; color: #33414f; line-height: 1;
  }
  .arrowrow button:hover { border-color: #2563eb; color: #2563eb; }
  .arrow-checks { display: flex; flex-wrap: wrap; gap: 5px 9px; flex: 1; }
  .arrow-checks label { width: auto; display: inline-flex; align-items: center; gap: 3px; color: #33414f; cursor: pointer; }
  .arrow-checks input[type="checkbox"] { flex: none; width: 14px; height: 14px; padding: 0; }
  #statusbar {
    position: absolute; left: 0; bottom: 0; right: 0; pointer-events: none;
    padding: 5px 12px; font-size: 12px;
  }
  #statusbar span {
    display: inline-block; background: rgba(28,39,51,.88); color: #fff;
    padding: 4px 12px; border-radius: 12px;
  }
  #toast {
    position: fixed; left: 50%; bottom: 34px; transform: translateX(-50%);
    background: #1c2733; color: #fff; padding: 8px 16px; border-radius: 5px;
    font-size: 13px; display: none; z-index: 60; box-shadow: 0 6px 18px rgba(10,18,28,.35);
  }
  #toast.err { background: #b42318; }
  #color-modal {
    position: fixed; inset: 0; z-index: 250000; display: none; align-items: center; justify-content: center;
    background: rgba(15,27,39,.48); padding: 24px;
  }
  #color-modal.show { display: flex; }
  .color-dialog {
    width: min(920px, 96vw); max-height: 88vh; display: flex; flex-direction: column;
    background: #fff; border-radius: 8px; box-shadow: 0 16px 48px rgba(10,18,28,.35); overflow: hidden;
  }
  .color-head, .color-foot { display: flex; align-items: center; gap: 8px; padding: 12px 16px; }
  .color-head { border-bottom: 1px solid #dde4ea; }
  .color-head h2 { font-size: 16px; margin-right: auto; }
  .color-body { overflow: auto; padding: 12px 16px; overscroll-behavior: contain; }
  .color-grid { display: grid; grid-template-columns: 130px repeat(3, 120px) 1fr; gap: 7px 10px; align-items: center; }
  .color-grid .th { font-size: 12px; font-weight: 700; color: #536474; padding-bottom: 4px; }
  .color-grid .type { font-size: 13px; font-weight: 600; }
  .hex-color { display: grid; grid-template-columns: 32px minmax(72px, 1fr); gap: 4px; align-items: center; }
  .hex-color input[type="color"] { width: 32px; height: 32px; padding: 2px; border: 1px solid #c4ced7; border-radius: 4px; background: #fff; cursor: pointer; }
  .hex-color input[type="text"] { min-width: 0; height: 32px; padding: 4px 5px; border: 1px solid #c4ced7; border-radius: 4px; font: 11px Consolas, monospace; text-transform: uppercase; }
  .color-preview { height: 32px; display: grid; place-items: center; border: 2px solid; border-radius: 5px; font-size: 12px; font-weight: 700; }
  .color-add { display: flex; gap: 7px; margin-top: 14px; padding-top: 12px; border-top: 1px solid #edf1f4; }
  .color-add input { flex: 1; padding: 6px 9px; border: 1px solid #c4ced7; border-radius: 4px; }
  .remark-color-section { margin-top: 20px; padding-top: 15px; border-top: 2px solid #dde4ea; }
  .remark-color-section h3 { font-size: 14px; margin-bottom: 4px; color: #22313f; }
  .remark-color-section .desc { font-size: 11px; color: #6b7885; margin-bottom: 10px; }
  .remark-color-grid { display: grid; grid-template-columns: minmax(145px, 1fr) repeat(3, 118px) 110px 104px; gap: 7px 8px; align-items: center; }
  .remark-color-grid .th { font-size: 12px; font-weight: 700; color: #536474; }
  .remark-color-grid input[type="text"] { min-width: 0; padding: 6px 8px; border: 1px solid #c4ced7; border-radius: 4px; }
  .remark-color-grid .hex-color input[type="color"] { width: 32px; }
  .remark-rule-actions { display: flex; gap: 3px; }
  .remark-rule-actions button { padding: 5px 7px; }
  .color-foot { border-top: 1px solid #dde4ea; justify-content: flex-end; }
  #ops-hint {
    position: absolute; top: 10px; left: 50%; transform: translateX(-50%);
    display: none; gap: 12px; align-items: center; padding: 5px 14px;
    background: rgba(28,39,51,.88); color: #cfe0ee; font-size: 11px;
    border-radius: 14px; z-index: 20; white-space: nowrap;
  }
  body.editing #ops-hint { display: flex; }
  #ops-hint kbd {
    background: #2d3d4f; border: 1px solid #46586b; border-radius: 3px;
    padding: 1px 5px; font-size: 11px; color: #dfe7ee; font-family: inherit;
  }
  #data-view { display: none; height: calc(100vh - 49px); overflow: auto; padding: 16px 18px; }
  .toolbar { display: flex; gap: 10px; margin-bottom: 10px; align-items: center; }
  .search input {
    width: 220px; padding: 7px 10px; border: 1px solid #c4ced7; border-radius: 4px;
    font-size: 13px; background: #fff; color: #1c2733;
  }
  .btn2 {
    border: 1px solid #c4ced7; background: #fff; color: #33414f;
    padding: 6px 12px; border-radius: 4px; cursor: pointer; font-size: 13px;
  }
  .btn2:hover { border-color: #2563eb; color: #2563eb; }
  .btn2.primary { background: #2563eb; border-color: #2563eb; color: #fff; }
  .btn2.primary:hover { background: #1d4fd8; border-color: #1d4fd8; color: #fff; }
  .btn2.danger { color: #b42318; border-color: #e0b4ae; }
  .btn2.danger:hover { background: #fdf2f1; border-color: #b42318; color: #b42318; }
  .btn2:disabled { opacity: .45; cursor: default; }
  .btn2:disabled:hover { border-color: #c4ced7; color: #33414f; }
  .spacer { flex: 1; }
  .dcount, .dhint { font-size: 12px; color: #5b6975; }
  .tablewrap {
    max-height: calc(100vh - 158px); overflow: auto;
    background: #fff; border: 1px solid #dde3e9; border-radius: 4px;
  }
  #dtable { width: max-content; min-width: 100%; background: #fff; border-collapse: separate; border-spacing: 0; font-size: 12px; }
  #dtable th, #dtable td {
    border-right: 1px solid #eef2f6; border-bottom: 1px solid #eef2f6;
    padding: 4px 8px; text-align: left; white-space: nowrap;
  }
  #dtable th {
    background: #f2f5f8; font-weight: 600; position: sticky; top: 0; z-index: 2;
    cursor: pointer; user-select: none;
  }
  #dtable tbody tr:nth-child(even) td { background: #fafcfe; }
  #dtable td.ed { cursor: text; }
  #dtable td.ed:focus { outline: 2px solid #2563eb; outline-offset: -2px; background: #eef4ff !important; }
  #dtable td.dirty { background: #fff6db !important; }
  #dtable th.pick, #dtable td.pick {
    width: 30px; min-width: 30px; max-width: 30px; padding: 4px 0;
    text-align: center; position: sticky; left: 0; z-index: 1; background: #fff;
  }
  #dtable th.pick { background: #f2f5f8; z-index: 4; }
  #dtable tbody tr:nth-child(even) td.pick { background: #fafcfe; }
  #dtable th.idcol, #dtable td.idcol {
    position: sticky; left: 30px; z-index: 1; background: #fff;
    box-shadow: 1px 0 0 #eef2f6;
  }
  #dtable th.idcol { background: #f2f5f8; z-index: 4; }
  #dtable tbody tr:nth-child(even) td.idcol { background: #fafcfe; }
  #dtable td.num { font-variant-numeric: tabular-nums; }
  #empty { display: none; color: #5b6975; padding: 24px 4px; font-size: 13px; }
</style>
</head>
<body>
<header>
  <h1>输送机布局编辑</h1>
  <div class="seg">
    <button id="mode-browse" class="on">浏览</button>
    <button id="mode-edit">编辑</button>
  </div>
  <div id="edit-tools">
    <button class="btn" id="btn-add">添加设备</button>
    <button class="btn danger" id="btn-del" disabled>删除</button>
    <button class="btn" id="btn-refill" title="按相邻设备间隔重算 width/height 链路填充">重算链路填充</button>
    <button class="btn primary" id="btn-save">保存到数据源</button>
  </div>
  <button class="btn" id="btn-undo" title="撤回最近一次尚未保存的修改（Ctrl+Z）" disabled>撤回</button>
  <button class="btn" id="btn-colors" title="配置不同 stationtype 的图标颜色">颜色配置</button>
  <div id="map-search">
    <input id="map-search-input" type="text" placeholder="设备ID / 编号 / 名称">
    <button class="btn" id="map-search-btn">定位</button>
  </div>
  <div class="tools" title="缩放">
    <button id="zoom-in" title="放大"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"><path d="M12 5v14M5 12h14"/></svg></button>
    <button id="zoom-out" title="缩小"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"><path d="M5 12h14"/></svg></button>
    <button id="zoom-fit" title="适应画面"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M8 3H5a2 2 0 0 0-2 2v3M16 3h3a2 2 0 0 1 2 2v3M8 21H5a2 2 0 0 1-2-2v-3M16 21h3a2 2 0 0 0 2-2v-3"/></svg></button>
  </div>
  <span class="mstat" id="map-stat"></span>
  <div class="seg">
    <button id="v-map" class="on">布局图</button>
    <button id="v-data">设备数据</button>
  </div>
</header>
<div id="stage">
  <div id="ops-hint">
    <span><kbd>Ctrl</kbd>+单击 多选</span>
    <span>空白处拖拽 框选</span>
    <span>拖拽 整格移动</span>
    <span><kbd>Del</kbd> 删除所选</span>
    <span><kbd>Ctrl</kbd>+<kbd>S</kbd> 保存</span>
    <span><kbd>Ctrl</kbd>+<kbd>Z</kbd> 撤回</span>
    <span>右键拖拽 平移画布</span>
  </div>
  <div id="world">
    <div id="grid-bg"></div>
    <svg id="arrows"></svg>
    <div id="marquee"></div>
  </div>
  <div id="panel"></div>
  <div id="statusbar"></div>
</div>
<div id="data-view">
  <div class="toolbar">
    <div class="search">
      <input id="q" type="text" placeholder="搜索任意字段">
    </div>
    <button class="btn2" id="d-add">新增设备</button>
    <button class="btn2 danger" id="d-del" disabled>删除所选</button>
    <span class="dcount" id="d-count"></span>
    <span class="spacer"></span>
    <span class="dhint">单元格可直接编辑,回车或点开别处提交</span>
    <button class="btn2 primary" id="btn-save-data">保存到数据源</button>
  </div>
  <div class="tablewrap">
    <table id="dtable">
      <thead><tr id="dhead"></tr></thead>
      <tbody id="tbody"></tbody>
    </table>
  </div>
  <div id="empty">没有匹配的设备</div>
</div>
<div id="color-modal">
  <div class="color-dialog">
    <div class="color-head"><h2>站台颜色配置</h2><button class="btn2" id="color-close">关闭</button></div>
    <div class="color-body">
      <div class="color-grid" id="color-grid"></div>
      <div class="color-add">
        <input id="color-new-type" type="text" placeholder="输入新的 stationtype，例如 12">
        <button class="btn2" id="color-add-type">添加类型</button>
      </div>
      <div class="remark-color-section">
        <h3>按备注包含内容映射颜色</h3>
        <div class="desc">备注包含关键词时应用该行颜色；多条规则命中时，使用排在最前面的规则，并优先于 stationtype 配色。</div>
        <div class="remark-color-grid" id="remark-color-grid"></div>
        <div class="color-add">
          <input id="remark-new-keyword" type="text" placeholder="输入备注中需要包含的关键词">
          <button class="btn2" id="remark-add-rule">添加备注规则</button>
        </div>
      </div>
    </div>
    <div class="color-foot">
      <button class="btn2" id="color-reset">恢复内置配色</button>
      <button class="btn2" id="color-cancel">取消</button>
      <button class="btn2 primary" id="color-save">保存颜色配置</button>
    </div>
  </div>
</div>
<div id="tip"></div>
<div id="toast"></div>
<script>
const RAW = __DATA__;
const FIELDS = __FIELDS__;
const LABELS = __LABELS__;
const EDIT_META = __EDIT_META__;
const BUILTIN_STATION_COLORS = __DEFAULT_STATION_COLORS__;
let stationColors = __STATION_COLORS__;
let remarkColorRules = __REMARK_COLOR_RULES__;
// 这些字段用数字输入并做整数校验
const NUM_EDIT = new Set(['locationx', 'locationy', 'width', 'height', 'field5', 'status']);
// 单元格基础尺寸。浏览器缩放只改变显示比例，不会增加文字排版宽度。
const CELL = 40;
const CHAIN_MAX = 4;
const DEFAULTS = { groupname: 'Convery', type: 'Convery', zone: '输送机监控' };
// arrowdirection 箭头类型
const ARROWS = [
  { v: 0, label: '无' }, { v: 1, label: '右' }, { v: 2, label: '左' },
  { v: 3, label: '下' }, { v: 4, label: '上' },
];
const STATION_TYPES = ['0', '1', '3', '5', '6', '7', '8', '10', '11', '16'];
const TEXT_DIRECTIONS = [
  { v: '', label: '留空（默认水平）' },
  { v: '1', label: '水平排列' },
  { v: '2', label: '垂直排列' },
];
// 兼容 generate_layout.py 产生的旧方向枚举：1/3 水平，2/4 垂直。
const isVerticalText = value => ['2', '4', 'vertical', 'v'].includes(
  String(value == null ? '' : value).trim().toLowerCase());
const textDirectionValue = value => {
  const raw = String(value == null ? '' : value).trim();
  return raw === '' ? '' : (isVerticalText(raw) ? '2' : '1');
};
function normalizeArrows(value) {
  const source = Array.isArray(value) ? value : String(value == null ? '' : value).split(/[,，;；\s]+/);
  const result = [];
  source.forEach(part => {
    const arrow = Number(part);
    const values = arrow === 5 ? [1, 2] : (arrow === 6 ? [3, 4] : [arrow]);
    values.forEach(item => { if ([1, 2, 3, 4].includes(item) && !result.includes(item)) result.push(item); });
  });
  return result.sort((a, b) => a - b);
}
const arrowValue = d => normalizeArrows(d.arrows).join(',');
const pad2 = n => String(n).padStart(2, '0');
const nowStr = () => {
  const t = new Date();
  return t.getFullYear() + '-' + pad2(t.getMonth() + 1) + '-' + pad2(t.getDate()) +
    ' ' + pad2(t.getHours()) + ':' + pad2(t.getMinutes()) + ':' + pad2(t.getSeconds());
};

const devices = RAW.map(r => ({
  id: r.id, name: r.name, remark: r.remark,
  x: r.x, y: r.y, w: r.w, h: r.h,
  arrows: normalizeArrows(r.arrows), field5: r.field5,
  raw: r.raw,
  manual: r.w > 1 || r.h > 1,
  ox: r.x, oy: r.y,
}));

// 预览图只画 status == 1 的设备
const visible = () => devices.filter(d => String(d.raw.status == null ? '' : d.raw.status).trim() === '1');

const fallbackStationColor = { fill: '#ccdcf0', border: '#55708c', text: '#1b3350' };
function stationColor(device) {
  const remark = String(device.raw.remark == null ? '' : device.raw.remark);
  const matched = remarkColorRules.find(rule => {
    const keyword = String(rule.contains == null ? '' : rule.contains).trim();
    return keyword && remark.includes(keyword);
  });
  if (matched) return matched;
  const key = String(device.raw.stationtype == null ? '' : device.raw.stationtype).trim();
  return stationColors[key] || stationColors.__default__ || fallbackStationColor;
}

// ---- 链路填充:相邻同排/同列设备合并成连续块,结果写回 width/height ----
function autoFill() {
  // 邻居图必须包含全部设备(含手工值的),否则手工值被排除后会重新发现链路,
  // 导致每次保存-重载都多填一批跨度。只对非手工设备应用结果。
  const rows = new Map(), cols = new Map();
  visible().forEach(d => {
    if (!d.manual) { d.w = 1; d.h = 1; }
    if (!rows.has(d.y)) rows.set(d.y, []);
    if (!cols.has(d.x)) cols.set(d.x, []);
    rows.get(d.y).push(d);
    cols.get(d.x).push(d);
  });
  rows.forEach(list => {
    list.sort((a, b) => a.x - b.x);
    for (let i = 0; i + 1 < list.length; i++) {
      const gap = list[i + 1].x - list[i].x;
      if (gap >= 1 && gap <= CHAIN_MAX && !list[i].manual) { list[i].w = gap; list[i].h = 1; }
    }
  });
  cols.forEach(list => {
    list.sort((a, b) => a.y - b.y);
    for (let i = 0; i + 1 < list.length; i++) {
      const gap = list[i + 1].y - list[i].y;
      if (gap >= 1 && gap <= CHAIN_MAX && !list[i].manual && list[i].w === 1) { list[i].h = gap; }
    }
  });
  // 立即同步到 raw，避免随后编辑其他字段时 syncDerived() 又读到旧宽高。
  visible().forEach(d => {
    d.raw.width = String(d.w);
    d.raw.height = String(d.h);
  });
}

const stage = document.getElementById('stage');
const world = document.getElementById('world');
const gridBg = document.getElementById('grid-bg');
const svg = document.getElementById('arrows');
const tip = document.getElementById('tip');
const panel = document.getElementById('panel');
const marquee = document.getElementById('marquee');
const statusbar = document.getElementById('statusbar');
const toastEl = document.getElementById('toast');

let editMode = false;
let selected = new Set();
const byId = () => Object.fromEntries(devices.map(d => [d.id, d]));

// ---- 保存前撤回 ----
const UNDO_LIMIT = 50;
const undoStack = [];
const cloneDevice = d => ({
  id: d.id, name: d.name, remark: d.remark,
  x: d.x, y: d.y, w: d.w, h: d.h,
  arrows: normalizeArrows(d.arrows), field5: d.field5,
  raw: Object.assign({}, d.raw), manual: d.manual,
  ox: d.ox, oy: d.oy,
});

function updateUndoButton() {
  const btn = document.getElementById('btn-undo');
  btn.disabled = !undoStack.length;
  btn.title = undoStack.length ?
    '撤回：' + undoStack[undoStack.length - 1].label + '（Ctrl+Z）' :
    '没有可撤回的修改';
}

function pushUndo(label) {
  undoStack.push({
    label,
    devices: devices.map(cloneDevice),
    selected: [...selected],
    expanded: [...expandedOverlapKeys],
    picked: [...pick],
    dirty: [...dirtyCells],
  });
  if (undoStack.length > UNDO_LIMIT) undoStack.shift();
  updateUndoButton();
}

function undoLast() {
  const state = undoStack.pop();
  if (!state) { toast('没有可撤回的修改', true); return; }
  devices.splice(0, devices.length, ...state.devices.map(cloneDevice));
  selected = new Set(state.selected.filter(id => devices.some(d => d.id === id)));
  expandedOverlapKeys = new Set(state.expanded);
  pick.clear();
  state.picked.forEach(id => pick.add(id));
  dirtyCells.clear();
  state.dirty.forEach(key => dirtyCells.add(key));
  dataDirty = true;
  renderAll();
  updateUndoButton();
  toast('已撤回：' + state.label);
}

let toastTimer = null;
function toast(msg, err) {
  toastEl.textContent = msg;
  toastEl.className = err ? 'err' : '';
  toastEl.style.display = 'block';
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toastEl.style.display = 'none', err ? 4200 : 2200);
}

// ---- stationtype 图标颜色配置 ----
const colorModal = document.getElementById('color-modal');
const colorGrid = document.getElementById('color-grid');
const remarkColorGrid = document.getElementById('remark-color-grid');
let colorOpenSnapshot = null;
const cloneColors = value => JSON.parse(JSON.stringify(value));
const validHex = (value, fallback) => /^#[0-9a-f]{6}$/i.test(String(value || '')) ?
  String(value).toLowerCase() : fallback;

function colorConfigKeys() {
  const keys = new Set(Object.keys(stationColors));
  devices.forEach(d => keys.add(String(d.raw.stationtype == null ? '' : d.raw.stationtype).trim()));
  keys.add('__default__');
  return [...keys].sort((a, b) => {
    if (a === '__default__') return -1;
    if (b === '__default__') return 1;
    if (a === '') return -1;
    if (b === '') return 1;
    const na = Number(a), nb = Number(b);
    if (isFinite(na) && isFinite(nb)) return na - nb;
    return a.localeCompare(b);
  });
}

function colorForEdit(key) {
  const fallback = stationColors.__default__ || fallbackStationColor;
  const color = stationColors[key] || fallback;
  return {
    fill: validHex(color.fill, fallbackStationColor.fill),
    border: validHex(color.border, fallbackStationColor.border),
    text: validHex(color.text, fallbackStationColor.text),
  };
}

function applyColorPreview(preview, color) {
  preview.style.backgroundColor = color.fill;
  preview.style.borderColor = color.border;
  preview.style.color = color.text;
}

function colorEditor(attrs, value) {
  const lower = String(value).toLowerCase(), upper = lower.toUpperCase();
  return '<div class="hex-color"><input type="color" ' + attrs + ' data-color-control="picker" value="' + lower + '">' +
    '<input type="text" ' + attrs + ' data-color-control="hex" value="' + upper +
    '" maxlength="7" spellcheck="false" aria-label="HEX 颜色值"></div>';
}

function renderColorGrid() {
  let html = '<div class="th">stationtype</div><div class="th">背景色</div>' +
    '<div class="th">边框色</div><div class="th">文字色</div><div class="th">预览</div>';
  colorConfigKeys().forEach(key => {
    const encoded = encodeURIComponent(key), c = colorForEdit(key);
    stationColors[key] = c;
    const label = key === '__default__' ? '默认/未配置' : (key === '' ? '空值' : key);
    html += '<div class="type">' + esc(label) + '</div>' +
      ['fill', 'border', 'text'].map(role => colorEditor('data-color-key="' + encoded +
        '" data-color-role="' + role + '"', c[role])).join('') +
      '<div class="color-preview" data-color-preview="' + encoded + '">站台 ' + esc(label) + '</div>';
  });
  colorGrid.innerHTML = html;
  colorGrid.querySelectorAll('[data-color-preview]').forEach(preview => {
    applyColorPreview(preview, colorForEdit(decodeURIComponent(preview.dataset.colorPreview)));
  });
}

function remarkRuleForEdit(index) {
  const fallback = stationColors.__default__ || fallbackStationColor;
  const rule = remarkColorRules[index] || {};
  return {
    contains: String(rule.contains == null ? '' : rule.contains),
    fill: validHex(rule.fill, fallback.fill),
    border: validHex(rule.border, fallback.border),
    text: validHex(rule.text, fallback.text),
  };
}

function renderRemarkColorGrid() {
  let html = '<div class="th">备注包含关键词</div><div class="th">背景色</div>' +
    '<div class="th">边框色</div><div class="th">文字色</div><div class="th">预览</div><div class="th">操作</div>';
  remarkColorRules = remarkColorRules.map((_, index) => remarkRuleForEdit(index));
  remarkColorRules.forEach((rule, index) => {
    html += '<input type="text" data-remark-index="' + index + '" data-remark-role="contains" value="' + esc(rule.contains) + '">' +
      ['fill', 'border', 'text'].map(role => colorEditor('data-remark-index="' + index +
        '" data-remark-role="' + role + '"', rule[role])).join('') +
      '<div class="color-preview" data-remark-preview="' + index + '">备注规则 ' + (index + 1) + '</div>' +
      '<div class="remark-rule-actions"><button class="btn2" data-rule-action="up" data-rule-index="' + index + '" title="上移">↑</button>' +
      '<button class="btn2" data-rule-action="down" data-rule-index="' + index + '" title="下移">↓</button>' +
      '<button class="btn2 danger" data-rule-action="delete" data-rule-index="' + index + '">删除</button></div>';
  });
  if (!remarkColorRules.length) {
    html += '<div class="hint" style="grid-column:1/-1">尚未配置备注颜色规则</div>';
  }
  remarkColorGrid.innerHTML = html;
  remarkColorGrid.querySelectorAll('[data-remark-preview]').forEach(preview => {
    applyColorPreview(preview, remarkRuleForEdit(Number(preview.dataset.remarkPreview)));
  });
}

function openColorConfig() {
  colorOpenSnapshot = { colors: cloneColors(stationColors), rules: cloneColors(remarkColorRules) };
  renderColorGrid();
  renderRemarkColorGrid();
  colorModal.classList.add('show');
}

function cancelColorConfig() {
  if (colorOpenSnapshot) {
    stationColors = cloneColors(colorOpenSnapshot.colors);
    remarkColorRules = cloneColors(colorOpenSnapshot.rules);
  }
  colorModal.classList.remove('show');
  colorOpenSnapshot = null;
  renderBlocks();
}

colorGrid.addEventListener('input', e => {
  const input = e.target.closest('input[data-color-key]');
  if (!input) return;
  const key = decodeURIComponent(input.dataset.colorKey), role = input.dataset.colorRole;
  const value = input.value.trim().toLowerCase();
  if (!/^#[0-9a-f]{6}$/.test(value)) return;
  stationColors[key] = Object.assign(colorForEdit(key), { [role]: value });
  colorGrid.querySelectorAll('input[data-color-key]').forEach(peer => {
    if (peer !== input && peer.dataset.colorKey === input.dataset.colorKey && peer.dataset.colorRole === role) {
      peer.value = peer.dataset.colorControl === 'hex' ? value.toUpperCase() : value;
    }
  });
  const preview = colorGrid.querySelector('[data-color-preview="' + input.dataset.colorKey + '"]');
  if (preview) applyColorPreview(preview, stationColors[key]);
  renderBlocks();
});

colorGrid.addEventListener('change', e => {
  const input = e.target.closest('input[data-color-key][data-color-control="hex"]');
  if (!input || /^#[0-9a-f]{6}$/i.test(input.value.trim())) return;
  input.value = colorForEdit(decodeURIComponent(input.dataset.colorKey))[input.dataset.colorRole].toUpperCase();
  toast('颜色值请使用 #RRGGBB 格式', true);
});

remarkColorGrid.addEventListener('input', e => {
  const input = e.target.closest('input[data-remark-index]');
  if (!input) return;
  const index = Number(input.dataset.remarkIndex), role = input.dataset.remarkRole;
  if (!remarkColorRules[index]) return;
  const value = input.value.trim().toLowerCase();
  if (role !== 'contains' && !/^#[0-9a-f]{6}$/.test(value)) return;
  remarkColorRules[index][role] = role === 'contains' ? input.value : value;
  if (role !== 'contains') {
    remarkColorGrid.querySelectorAll('input[data-remark-index]').forEach(peer => {
      if (peer !== input && Number(peer.dataset.remarkIndex) === index && peer.dataset.remarkRole === role) {
        peer.value = peer.dataset.colorControl === 'hex' ? value.toUpperCase() : value;
      }
    });
  }
  const preview = remarkColorGrid.querySelector('[data-remark-preview="' + index + '"]');
  if (preview) applyColorPreview(preview, remarkRuleForEdit(index));
  renderBlocks();
});

remarkColorGrid.addEventListener('change', e => {
  const input = e.target.closest('input[data-remark-index][data-color-control="hex"]');
  if (!input || /^#[0-9a-f]{6}$/i.test(input.value.trim())) return;
  input.value = remarkRuleForEdit(Number(input.dataset.remarkIndex))[input.dataset.remarkRole].toUpperCase();
  toast('颜色值请使用 #RRGGBB 格式', true);
});

remarkColorGrid.addEventListener('click', e => {
  const button = e.target.closest('button[data-rule-action]');
  if (!button) return;
  const index = Number(button.dataset.ruleIndex), action = button.dataset.ruleAction;
  if (action === 'delete') remarkColorRules.splice(index, 1);
  if (action === 'up' && index > 0) [remarkColorRules[index - 1], remarkColorRules[index]] = [remarkColorRules[index], remarkColorRules[index - 1]];
  if (action === 'down' && index + 1 < remarkColorRules.length) [remarkColorRules[index], remarkColorRules[index + 1]] = [remarkColorRules[index + 1], remarkColorRules[index]];
  renderRemarkColorGrid();
  renderBlocks();
});

document.getElementById('btn-colors').onclick = openColorConfig;
document.getElementById('color-close').onclick = cancelColorConfig;
document.getElementById('color-cancel').onclick = cancelColorConfig;
colorModal.addEventListener('pointerdown', e => { if (e.target === colorModal) cancelColorConfig(); });
document.getElementById('color-reset').onclick = () => {
  stationColors = cloneColors(BUILTIN_STATION_COLORS);
  remarkColorRules = [];
  renderColorGrid();
  renderRemarkColorGrid();
  renderBlocks();
  toast('已恢复内置配色，点击保存后写入配置文件');
};
document.getElementById('color-add-type').onclick = () => {
  const input = document.getElementById('color-new-type');
  const key = input.value.trim();
  if (!key || key === '__default__' || !/^[A-Za-z0-9_.-]+$/.test(key)) {
    toast('stationtype 只能使用字母、数字、点、下划线或横线', true);
    return;
  }
  if (!stationColors[key]) stationColors[key] = Object.assign({}, stationColors.__default__ || fallbackStationColor);
  input.value = '';
  renderColorGrid();
};
document.getElementById('remark-add-rule').onclick = () => {
  const input = document.getElementById('remark-new-keyword');
  const keyword = input.value.trim();
  if (!keyword) { toast('备注关键词不能为空', true); return; }
  const base = stationColors.__default__ || fallbackStationColor;
  remarkColorRules.push({ contains: keyword, fill: base.fill, border: base.border, text: base.text });
  input.value = '';
  renderRemarkColorGrid();
  renderBlocks();
};
document.getElementById('color-save').onclick = async () => {
  try {
    const invalidRule = remarkColorRules.find(rule => !String(rule.contains || '').trim());
    if (invalidRule) throw new Error('备注包含关键词不能为空');
    const res = await fetch('/save-station-colors', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ format: 'station_colors_v2', colors: stationColors, remark_rules: remarkColorRules }),
    });
    const data = await res.json();
    if (!res.ok || !data.ok) throw new Error(data.error || ('HTTP ' + res.status));
    colorOpenSnapshot = { colors: cloneColors(stationColors), rules: cloneColors(remarkColorRules) };
    colorModal.classList.remove('show');
    colorOpenSnapshot = null;
    toast('已保存 ' + data.count + ' 个站台类型颜色、' + data.rule_count + ' 条备注规则');
  } catch (err) {
    toast('颜色配置保存失败：' + err.message, true);
  }
};

function updateBounds() {
  const shown = visible();
  const maxX = Math.max(10, ...shown.map(d => d.x + d.w)) + 2;
  const maxY = Math.max(10, ...shown.map(d => d.y + d.h)) + 2;
  world.style.width = maxX * CELL + 'px';
  world.style.height = maxY * CELL + 'px';
  gridBg.style.width = world.style.width;
  gridBg.style.height = world.style.height;
  gridBg.style.backgroundSize = CELL + 'px ' + CELL + 'px';
  svg.setAttribute('width', maxX * CELL);
  svg.setAttribute('height', maxY * CELL);
  svg.setAttribute('viewBox', '0 0 ' + maxX * CELL + ' ' + maxY * CELL);
}

// ---- 同坐标设备聚合显示 ----
let expandedOverlapKeys = new Set();
const overlapKey = d => d.x + ',' + d.y;

function overlapGroups() {
  const groups = new Map();
  visible().forEach(d => {
    const key = overlapKey(d);
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(d);
  });
  groups.forEach(list => list.sort((a, b) =>
    (b.field5 | 0) - (a.field5 | 0) ||
    String(a.id).localeCompare(String(b.id), undefined, { numeric: true })));
  return groups;
}

function displayEntries() {
  const groups = overlapGroups();
  const validExpanded = new Set([...expandedOverlapKeys].filter(k => (groups.get(k) || []).length > 1));
  expandedOverlapKeys = validExpanded;
  const entries = [];
  groups.forEach((list, key) => {
    if (list.length === 1) {
      entries.push({ d: list[0], x: list[0].x, y: list[0].y, key, group: list });
      return;
    }
    if (!expandedOverlapKeys.has(key)) {
      // 收起时只显示 field5 最大的设备；排序相同时按 itemid 稳定选择。
      entries.push({ d: list[0], x: list[0].x, y: list[0].y, key, group: list, collapsed: true });
      return;
    }
    // 向上方按 120° 扇形展开；避免完整圆周遮住下方相邻链路。
    const radius = Math.min(4.2, 1.8 + Math.max(0, list.length - 3) * .28);
    const fanStart = -Math.PI * 5 / 6;
    const fanSpan = Math.PI * 2 / 3;
    list.forEach((d, i) => {
      const angle = list.length === 1 ? -Math.PI / 2 :
        fanStart + i * fanSpan / (list.length - 1);
      entries.push({
        d, key, group: list, expanded: true,
        x: d.x + Math.cos(angle) * radius,
        y: d.y + Math.sin(angle) * radius,
      });
    });
  });
  return { groups, entries };
}

function collapseOverlapGroup(key) {
  if (!expandedOverlapKeys.has(key)) return false;
  expandedOverlapKeys.delete(key);
  const group = overlapGroups().get(key) || [];
  if (group.some(d => selected.has(d.id))) {
    group.forEach(d => selected.delete(d.id));
    if (group[0]) selected.add(group[0].id);
  }
  return true;
}

function renderBlocks() {
  world.querySelectorAll('.blk').forEach(el => el.remove());
  world.querySelectorAll('.overlap-anchor').forEach(el => el.remove());
  const display = displayEntries();
  display.entries.forEach(entry => {
    const d = entry.d;
    const el = document.createElement('div');
    const sel = selected.has(d.id);
    const verticalText = isVerticalText(d.raw.direction);
    el.className = 'blk' + (sel ? ' sel' : '') + (entry.collapsed ? ' overlap-collapsed' : '') +
      (verticalText ? ' text-vertical' : '');
    el.dataset.id = d.id;
    el.style.left = entry.x * CELL + 1 + 'px';
    el.style.top = entry.y * CELL + 1 + 'px';
    el.style.width = d.w * CELL - 3 + 'px';
    el.style.height = d.h * CELL - 3 + 'px';
    const typeColor = stationColor(d);
    el.style.backgroundColor = typeColor.fill;
    el.style.borderColor = typeColor.border;
    el.style.color = typeColor.text;
    // field5:数字越大越置顶;选中的压在所有设备之上(箭头层仍在最上面)
    el.style.zIndex = String(sel ? 90000 : 1 + Math.max(0, d.field5 | 0));
    const label = d.name || d.id;
    const remark = String(d.raw.remark == null ? '' : d.raw.remark).trim();
    if (verticalText) {
      const usableHeight = Math.max(12, d.h * CELL - 6);
      el.style.setProperty('--vertical-font-size', Math.max(6, Math.min(11, usableHeight / Math.max(1, String(label).length))) + 'px');
      el.style.setProperty('--vertical-remark-size', Math.max(5, Math.min(8, usableHeight / Math.max(1, remark.length || 1))) + 'px');
    }
    el.innerHTML = '<span class="nm">' + esc(label) + '</span>' +
      (remark ? '<span class="rm">' + esc(remark) + '</span>' : '') +
      (entry.collapsed ? '<span class="overlap-badge" data-overlap-key="' + esc(entry.key) +
        '" title="同坐标 ' + entry.group.length + ' 台，点击展开">×' + entry.group.length + '</span>' : '');
    world.appendChild(el);

    el.addEventListener('mouseenter', e => {
      tip.innerHTML = '<b>' + esc(label) + '</b>' +
        (remark ? '<br>' + esc(remark) : '') +
        '<br>坐标:(' + d.x + ', ' + d.y + ')' +
        '<br>渲染大小:' + d.w + '×' + d.h +
        '<br>文字排列:' + (verticalText ? '垂直' : '水平') +
        (entry.collapsed ? '<br>同坐标设备:' + entry.group.length + ' 台' +
          '<br>当前显示 field5 最大设备(' + d.field5 + ')' : '');
      tip.style.display = 'block';
    });
    el.addEventListener('mousemove', e => {
      tip.style.left = Math.min(e.clientX + 14, innerWidth - 200) + 'px';
      tip.style.top = Math.min(e.clientY + 14, innerHeight - 80) + 'px';
    });
    el.addEventListener('mouseleave', () => tip.style.display = 'none');
  });

  display.groups.forEach((list, key) => {
    if (list.length < 2 || !expandedOverlapKeys.has(key)) return;
    const anchor = document.createElement('div');
    anchor.className = 'overlap-anchor';
    anchor.dataset.overlapKey = key;
    anchor.title = '收起同坐标设备';
    anchor.textContent = '×' + list.length;
    anchor.style.left = (list[0].x * CELL + CELL / 2 - 12.5) + 'px';
    anchor.style.top = (list[0].y * CELL + CELL / 2 - 12.5) + 'px';
    world.appendChild(anchor);
  });
}

function esc(s) {
  return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

const ARROW_DEF = '<path d="M0.8,0.8L7.2,4L0.8,7.2" fill="none" stroke-width="1.5" ' +
  'stroke-linecap="round" stroke-linejoin="round"/>';

function marker(id, color, reverse) {
  return '<marker id="' + id + '" markerWidth="9" markerHeight="9" refX="6" refY="4" ' +
    'orient="' + (reverse ? 'auto-start-reverse' : 'auto') + '" markerUnits="userSpaceOnUse">' +
    '<g stroke="' + color + '">' + ARROW_DEF + '</g></marker>';
}

// 单个箭头类型 -> 方向；多方向由多条单向箭头组合显示。
function arrowGeom(type) {
  switch (type) {
    case 1: return { dir: 1 };                  // 右
    case 2: return { dir: -1 };                 // 左
    case 3: return { vert: true, dir: 1 };       // 下
    case 4: return { vert: true, dir: -1 };      // 上
    default: return null;
  }
}

function renderArrows() {
  const parts = ['<defs>' +
    marker('ah', '#4a5a68', false) + marker('ahr', '#4a5a68', true) +
    marker('ahs', '#d92d20', false) + marker('ahsr', '#d92d20', true) +
    '</defs>'];
  displayEntries().entries.forEach(entry => {
    const d = entry.d;
    const arrows = normalizeArrows(d.arrows);
    const horizontal = arrows.filter(v => v === 1 || v === 2);
    const vertical = arrows.filter(v => v === 3 || v === 4);
    arrows.forEach(type => {
      const geo = arrowGeom(type);
      if (!geo) return;
      const vert = !!geo.vert;
      const sameAxis = vert ? vertical : horizontal;
      const offset = (sameAxis.indexOf(type) - (sameAxis.length - 1) / 2) * 5;
      const cx = (entry.x + d.w / 2) * CELL + (vert ? offset : 0);
      const cy = (entry.y + d.h / 2) * CELL + (vert ? 0 : offset);
      let len = (vert ? d.h : d.w) * CELL - 14;
      len = Math.max(18, len);
      const half = len / 2;
      const x1 = vert ? cx : cx - half, y1 = vert ? cy - half : cy;
      const x2 = vert ? cx : cx + half, y2 = vert ? cy + half : cy;
      const sel = selected.has(d.id);
      const stroke = sel ? '#d92d20' : '#4a5a68';
      parts.push('<line data-id="' + esc(d.id) + '" data-arrow="' + type + '" x1="' + x1.toFixed(1) + '" y1="' + y1.toFixed(1) +
        '" x2="' + x2.toFixed(1) + '" y2="' + y2.toFixed(1) +
        '" stroke="' + stroke + '" stroke-opacity="' + (sel ? '.8' : '.38') + '" stroke-width="1.6"' +
        (geo.dir < 0 ? ' marker-start="url(#' + (sel ? 'ahsr' : 'ahr') + ')"' : '') +
        (geo.dir > 0 ? ' marker-end="url(#' + (sel ? 'ahs' : 'ah') + ')"' : '') + '/>');
    });
  });
  svg.innerHTML = parts.join('');
}

function selDevices() {
  const map = byId();
  return [...selected].map(id => map[id]).filter(Boolean);
}

function refreshSel() {
  world.querySelectorAll('.blk').forEach(el => el.classList.toggle('sel', selected.has(el.dataset.id)));
  renderArrows();
  const n = selected.size;
  document.getElementById('btn-del').disabled = !n;
  renderPanel();
  statusbar.innerHTML = editMode && n ? '<span>已选 ' + n + ' 台</span>' : '';
}

function frowText(label, key, val) {
  return '<div class="frow"><label>' + label + '</label><input type="text" data-k="' + key +
    '" value="' + esc(val == null ? '' : val) + '"></div>';
}

function frowNum(label, key, val) {
  return '<div class="frow"><label>' + label + '</label><input type="number" step="1" data-k="' + key +
    '" value="' + esc(val == null ? '' : val) + '"></div>';
}

function frowSelect(label, key, val, options) {
  return '<div class="frow"><label>' + label + '</label><select data-k="' + key + '">' +
    options.map(o => '<option value="' + esc(o.v) + '"' + (String(o.v) === String(val) ? ' selected' : '') +
      '>' + esc(o.label) + '</option>').join('') + '</select></div>';
}

function arrowCheckboxGroup(label, val, batch = false) {
  const picked = new Set(normalizeArrows(val));
  const attr = batch ? 'data-barrow-v' : 'data-arrow-v';
  const checks = '<div class="arrow-checks">' +
    ARROWS.filter(a => a.v > 0).map(a => '<label><input type="checkbox" ' + attr + '="' + a.v + '"' +
      (picked.has(a.v) ? ' checked' : '') + '>' + a.label + '</label>').join('') +
    (batch ? '<input type="hidden" data-bk="arrowdirection" value="">' : '') +
    '</div>';
  return batch ? checks : '<div class="frow"><label>' + label + '</label>' + checks + '</div>';
}

// 面板改动统一走这里:写回 raw -> 同步派生属性 -> 刷新 createtime
function applyPanelEdit(d, key, value) {
  if (key === 'itemid') {
    const v = String(value).trim();
    if (!v) { toast('itemid 不能为空', true); return false; }
    if (v !== d.id && byId()[v]) { toast('itemid ' + v + ' 已存在', true); return false; }
  }
  if ((NUM_FIELDS.has(key) || key === 'status' || key === 'field5') && String(value).trim() !== '') {
    const n = Number(value);
    if (!isFinite(n)) { toast(key + ' 需要数字', true); return false; }
    value = String(Math.round(n));
  }
  if (String(d.raw[key] == null ? '' : d.raw[key]) === String(value)) return true;
  pushUndo('修改 ' + fieldLabel(key));
  if (key === 'itemid') {
    const v = String(value).trim();
    if (selected.delete(d.id)) selected.add(v);
    if (pick.delete(d.id)) pick.add(v);
  }
  d.raw[key] = value;
  if (key === 'width' || key === 'height') d.manual = true;
  syncDerived(d);
  touch(d);
  renderAll();
  return true;
}

function frowReadonly(label, key, val) {
  return '<div class="frow"><label>' + label + '</label><input type="text" data-ro="' + key +
    '" value="' + esc(val == null ? '' : val) + '" disabled></div>';
}

// 面板标签统一显示成 itemname(设备名称) 这种形式
function fieldLabel(key) {
  const cn = LABELS[key];
  return cn && cn !== key ? key + '(' + cn + ')' : key;
}

// 可单选编辑字段 -> 控件(select 用于枚举字段,其余按数字/文本)
function fieldWidget(key, val) {
  const label = fieldLabel(key);
  if (key === 'arrowdirection') return arrowCheckboxGroup(label, val);
  if (key === 'direction') {
    return frowSelect(label, key, textDirectionValue(val), TEXT_DIRECTIONS);
  }
  if (key === 'stationtype') {
    return frowSelect(label, key, val, STATION_TYPES.map(v => ({ v, label: v })));
  }
  return NUM_EDIT.has(key) ? frowNum(label, key, val) : frowText(label, key, val);
}

// 可批量编辑字段 -> 只返回控件本身(data-bk,不会被单选编辑逻辑捕获)
function batchControl(key) {
  const ph = ' placeholder="留空不改"';
  if (key === 'direction') {
    return '<select data-bk="' + key + '"><option value="__NO_CHANGE__">不修改</option>' +
      TEXT_DIRECTIONS.map(o => '<option value="' + o.v + '">' + o.label + '</option>').join('') + '</select>';
  }
  if (key === 'arrowdirection') return arrowCheckboxGroup('', '', true);
  if (key === 'stationtype') {
    return '<select data-bk="' + key + '">' +
      STATION_TYPES.map(v => '<option value="' + v + '">' + v + '</option>').join('') + '</select>';
  }
  return '<input type="' + (NUM_EDIT.has(key) ? 'number" step="1"' : 'text') + '" data-bk="' + key + '"' + ph + '>';
}

function renderPanel() {
  const sel = selDevices();
  if (!editMode || !sel.length) { panel.classList.remove('show'); panel.innerHTML = ''; return; }
  panel.classList.add('show');
  if (sel.length === 1) {
    const d = sel[0], r = d.raw;
    panel.innerHTML = '<h3>设备属性 · ' + esc(r.itemid) + '</h3>' +
      EDIT_META.single.map(k => fieldWidget(k, r[k])).join('') +
      '<div class="hint">' + (d.manual
        ? '宽/高为手工值,不参与自动链路填充'
        : '宽/高由链路填充自动计算(相邻间隔 1~' + CHAIN_MAX + ' 格)') +
      '<br>状态填 1 才会在预览图显示;层级顺序越大越置顶</div>' +
      '<h3 style="margin-top:10px">只读字段</h3>' +
      EDIT_META.readonly.map(k => frowReadonly(fieldLabel(k), k, r[k])).join('');
  } else {
    panel.innerHTML = '<h3>批量编辑(' + sel.length + ' 台)</h3>' +
      '<div class="frow"><label>批量移动</label><input type="number" data-k="bdx" placeholder="ΔX">' +
      '<input type="number" data-k="bdy" placeholder="ΔY">' +
      '<button type="button" data-act="bmove" class="mini">移动</button></div>' +
      EDIT_META.batch.map(k => '<div class="frow"><label>' + fieldLabel(k) + '</label>' +
        batchControl(k) +
        '<button type="button" data-act="bset" data-field="' + k + '" class="mini">应用</button></div>').join('') +
      '<div class="hint">留空表示不修改该字段;可批量编辑字段按你给的规则来</div>';
  }
  panel.querySelectorAll('button[data-act]').forEach(b => b.onclick = () => {
    const act = b.dataset.act;
    const cur = selDevices();
    if (!cur.length) return;
    if (act === 'bmove') {
      const bx = panel.querySelector('input[data-k="bdx"]'), by = panel.querySelector('input[data-k="bdy"]');
      let dx = Math.round(+bx.value || 0), dy = Math.round(+by.value || 0);
      if (!dx && !dy) { toast('请填写 ΔX 或 ΔY', true); return; }
      const minX = Math.min(...cur.map(d => d.x)), minY = Math.min(...cur.map(d => d.y));
      if (minX + dx < 0) dx = -minX;
      if (minY + dy < 0) dy = -minY;
      if (!dx && !dy) { toast('设备位置没有变化', true); return; }
      pushUndo('批量移动 ' + cur.length + ' 台设备');
      cur.forEach(d => {
        d.x += dx; d.y += dy; d.ox = d.x; d.oy = d.y;
        d.raw.locationx = String(d.x); d.raw.locationy = String(d.y);
        touch(d);
      });
      renderAll();
      toast('已移动 ' + cur.length + ' 台（尚未保存）');
      return;
    }
    if (act === 'bset') {
      const key = b.dataset.field;
      const inp = panel.querySelector('[data-bk="' + key + '"]');
      let v = String(inp.value);
      if (v === '__NO_CHANGE__') { toast('请选择 ' + fieldLabel(key), true); return; }
      if (v.trim() === '' && key !== 'direction' && key !== 'arrowdirection') {
        toast('请先填写 ' + fieldLabel(key), true); return;
      }
      if (NUM_EDIT.has(key)) {
        const n = Number(v);
        if (!isFinite(n)) { toast((LABELS[key] || key) + ' 需要数字', true); return; }
        v = String(Math.round(n));
      }
      if (cur.every(d => String(d.raw[key] == null ? '' : d.raw[key]) === v)) {
        toast(fieldLabel(key) + ' 已经是该值');
        return;
      }
      pushUndo('批量修改 ' + fieldLabel(key));
      cur.forEach(d => {
        d.raw[key] = v;
        if (key === 'width' || key === 'height') d.manual = true;
        syncDerived(d);
        touch(d);
      });
      renderAll();
      toast('已批量设置 ' + fieldLabel(key) + ' = ' + v + '（尚未保存）');
    }
  });
  panel.querySelectorAll('input[data-arrow-v]').forEach(inp => inp.onchange = () => {
    const d = selDevices()[0];
    if (!d) return;
    const value = [...panel.querySelectorAll('input[data-arrow-v]:checked')]
      .map(x => Number(x.dataset.arrowV)).sort((a, b) => a - b).join(',');
    applyPanelEdit(d, 'arrowdirection', value);
  });
  panel.querySelectorAll('input[data-barrow-v]').forEach(inp => inp.onchange = () => {
    const hidden = panel.querySelector('input[data-bk="arrowdirection"]');
    if (hidden) hidden.value = [...panel.querySelectorAll('input[data-barrow-v]:checked')]
      .map(x => Number(x.dataset.barrowV)).sort((a, b) => a - b).join(',');
  });
  panel.querySelectorAll('input[data-k], select[data-k]').forEach(inp => inp.onchange = () => {
    const k = inp.dataset.k;
    if (k === 'bdx' || k === 'bdy') return;   // 批量移动由"移动"按钮处理
    const d = selDevices()[0];
    if (!d) return;
    if (!applyPanelEdit(d, k, inp.value)) renderPanel();  // 校验失败时回显原值
  });
}

function renderAll(recomputeChains = false) {
  // 普通编辑只刷新界面，不隐式改变 width/height。
  // 链路填充仅在用户明确点击“重算链路填充”时执行。
  if (recomputeChains) autoFill();
  updateBounds();
  renderBlocks();
  renderArrows();
  refreshSel();
  const shown = visible().length;
  const stat = document.getElementById('map-stat');
  if (stat) stat.textContent = '显示 ' + shown + ' 台' +
    (shown < devices.length ? '（status≠1 隐藏 ' + (devices.length - shown) + ' 台）' : '');
  dataDirty = true;
  if (dataView.style.display === 'block') renderTable(document.getElementById('q').value.trim());
}

// ---- 缩放与平移 ----
const MIN_SCALE = 0.05;
const MAX_SCALE = 10;
let scale = 1, tx = 0, ty = 0;
function applyT() {
  world.style.transform = 'translate(' + tx + 'px,' + ty + 'px) scale(' + scale + ')';
}
function fit() {
  const r = stage.getBoundingClientRect();
  const w = parseFloat(world.style.width) || 100, h = parseFloat(world.style.height) || 100;
  scale = Math.min((r.width - 40) / w, (r.height - 40) / h, 1);
  tx = (r.width - w * scale) / 2;
  ty = (r.height - h * scale) / 2;
  applyT();
}
function zoomAt(cx, cy, factor) {
  const ns = Math.min(MAX_SCALE, Math.max(MIN_SCALE, scale * factor));
  tx = cx - (cx - tx) * (ns / scale);
  ty = cy - (cy - ty) * (ns / scale);
  scale = ns;
  applyT();
}
stage.addEventListener('wheel', e => {
  // 编辑面板内的滚轮保留给面板自身滚动，不传给画布缩放。
  if (e.target.closest('#panel')) return;
  e.preventDefault();
  const r = stage.getBoundingClientRect();
  zoomAt(e.clientX - r.left, e.clientY - r.top, e.deltaY < 0 ? 1.12 : 1 / 1.12);
}, { passive: false });

let pan = null;
function startPan(e) {
  pan = { x: e.clientX, y: e.clientY, tx, ty, btn: e.button };
  stage.classList.add('panning');
}
function movePan(e) {
  tx = pan.tx + e.clientX - pan.x;
  ty = pan.ty + e.clientY - pan.y;
  applyT();
}

let marq = null, move = null;
let pendingCollapse = null;
stage.addEventListener('contextmenu', e => e.preventDefault());
stage.addEventListener('pointerdown', e => {
  if (e.target.closest('#panel')) return;
  const map = byId();
  const overlapToggle = e.target.closest('.overlap-badge, .overlap-anchor');
  if (overlapToggle && e.button === 0) {
    const key = overlapToggle.dataset.overlapKey;
    if (expandedOverlapKeys.has(key)) {
      collapseOverlapGroup(key);
    } else {
      [...expandedOverlapKeys].forEach(collapseOverlapGroup);
      expandedOverlapKeys.add(key);
    }
    renderAll();
    e.preventDefault();
    e.stopPropagation();
    return;
  }

  // 点击展开组以外的设备或画布空白处时自动收起；组内设备仍可正常选择和编辑。
  const clickedBlock = e.target.closest('.blk');
  const clickedDevice = clickedBlock ? map[clickedBlock.dataset.id] : null;
  const keepKey = clickedDevice && expandedOverlapKeys.has(overlapKey(clickedDevice)) ?
    overlapKey(clickedDevice) : null;
  let collapsedAny = false;
  [...expandedOverlapKeys].forEach(key => {
    if (key !== keepKey) collapsedAny = collapseOverlapGroup(key) || collapsedAny;
  });
  if (collapsedAny) renderAll();

  if (e.target.closest('.blk') && editMode && e.button === 0) {
    const id = e.target.closest('.blk').dataset.id;
    const d = map[id];
    if (!d) return;
    e.stopPropagation();
    if (e.ctrlKey || e.metaKey) {
      selected.has(id) ? selected.delete(id) : selected.add(id);
      refreshSel();
    } else {
      if (selected.has(id) && selected.size > 1) pendingCollapse = id;
      else if (!selected.has(id)) {
        selected = new Set([id]);
        refreshSel();
      }
    }
    move = { sx: e.clientX, sy: e.clientY, ox: d.x, oy: d.y, dx: 0, dy: 0 };
    window.addEventListener('pointermove', onMove);
    window.addEventListener('pointerup', onUp);
    return;
  }
  if (e.button === 2 || e.button === 1) { startPan(e); return; }
  if (!editMode && e.button === 0) { startPan(e); return; }
  if (editMode && e.button === 0) {
    const r = stage.getBoundingClientRect();
    const wx = (e.clientX - r.left - tx) / scale, wy = (e.clientY - r.top - ty) / scale;
    if (!(e.ctrlKey || e.metaKey)) { selected = new Set(); refreshSel(); }
    marq = { x0: wx, y0: wy, add: e.ctrlKey || e.metaKey, base: new Set(selected) };
    marquee.style.display = 'block';
    window.addEventListener('pointermove', onMarqMove);
    window.addEventListener('pointerup', onMarqUp);
  }
});

function onMove(e) {
  if (!move) return;
  const ndx = Math.round((e.clientX - move.sx) / (CELL * scale));
  const ndy = Math.round((e.clientY - move.sy) / (CELL * scale));
  move.dx = ndx; move.dy = ndy;
  const t = 'translate(' + ndx * CELL + 'px,' + ndy * CELL + 'px)';
  selected.forEach(id => {
    const el = world.querySelector('.blk[data-id="' + CSS.escape(id) + '"]');
    if (el) el.style.transform = t;
    svg.querySelectorAll('line[data-id="' + CSS.escape(id) + '"]').forEach(line => line.style.transform = t);
  });
}

function onUp() {
  window.removeEventListener('pointermove', onMove);
  window.removeEventListener('pointerup', onUp);
  world.querySelectorAll('.blk').forEach(el => el.style.transform = '');
  svg.querySelectorAll('line').forEach(l => l.style.transform = '');
  if (move && (move.dx || move.dy)) {
    const sel = selDevices();
    let dx = move.dx, dy = move.dy;
    const minX = Math.min(...sel.map(d => d.x)), minY = Math.min(...sel.map(d => d.y));
    if (minX + dx < 0) dx = -minX;
    if (minY + dy < 0) dy = -minY;
    if (dx || dy) {
      pushUndo('拖动 ' + sel.length + ' 台设备');
      sel.forEach(d => {
        d.x += dx; d.y += dy; d.ox = d.x; d.oy = d.y;
        d.raw.locationx = String(d.x); d.raw.locationy = String(d.y);
        touch(d);
      });
      renderAll();
    }
  } else if (move && pendingCollapse) {
    selected = new Set([pendingCollapse]);
    refreshSel();
  }
  pendingCollapse = null;
  move = null;
  applyT();
}

function onMarqMove(e) {
  if (!marq) return;
  const r = stage.getBoundingClientRect();
  const wx = (e.clientX - r.left - tx) / scale, wy = (e.clientY - r.top - ty) / scale;
  const x = Math.min(marq.x0, wx), y = Math.min(marq.y0, wy);
  const w = Math.abs(wx - marq.x0), h = Math.abs(wy - marq.y0);
  marquee.style.left = x + 'px'; marquee.style.top = y + 'px';
  marquee.style.width = w + 'px'; marquee.style.height = h + 'px';
  marq.x1 = wx; marq.y1 = wy;
  const xhi = Math.max(marq.x0, wx), yhi = Math.max(marq.y0, wy);
  const gx0 = Math.min(marq.x0, wx) / CELL, gy0 = Math.min(marq.y0, wy) / CELL;
  const gx1 = xhi / CELL, gy1 = yhi / CELL;
  const hits = new Set(visible().filter(d =>
    d.x < gx1 && (d.x + d.w) > gx0 && d.y < gy1 && (d.y + d.h) > gy0).map(d => d.id));
  const preview = new Set([...marq.base, ...hits]);
  world.querySelectorAll('.blk').forEach(el => el.classList.toggle('sel', preview.has(el.dataset.id)));
}

function onMarqUp() {
  window.removeEventListener('pointermove', onMarqMove);
  window.removeEventListener('pointerup', onMarqUp);
  marquee.style.display = 'none';
  if (marq && marq.x1 !== undefined) {
    const x0 = Math.min(marq.x0, marq.x1), x1 = Math.max(marq.x0, marq.x1);
    const y0 = Math.min(marq.y0, marq.y1), y1 = Math.max(marq.y0, marq.y1);
    visible().forEach(d => {
      const hit = d.x < x1 / CELL && (d.x + d.w) > x0 / CELL &&
        d.y < y1 / CELL && (d.y + d.h) > y0 / CELL;
      if (hit) selected.add(d.id);
    });
  }
  marq = null;
  refreshSel();
}

window.addEventListener('pointermove', e => {
  if (pan) movePan(e);
});
window.addEventListener('pointerup', () => { pan = null; stage.classList.remove('panning'); });

document.getElementById('zoom-in').onclick = () => {
  const r = stage.getBoundingClientRect();
  zoomAt(r.width / 2, r.height / 2, 1.25);
};
document.getElementById('zoom-out').onclick = () => {
  const r = stage.getBoundingClientRect();
  zoomAt(r.width / 2, r.height / 2, 0.8);
};
document.getElementById('zoom-fit').onclick = fit;
addEventListener('resize', fit);

// ---- 设备快速定位 ----
const mapSearchInput = document.getElementById('map-search-input');
function locateDevice() {
  const q = mapSearchInput.value.trim().toLowerCase();
  if (!q) { toast('请输入设备ID、设备编号或设备名称', true); mapSearchInput.focus(); return; }

  let found = devices.find(d => String(d.raw.itemid || d.id).trim().toLowerCase() === q);
  if (!found) {
    let matches = devices.filter(d =>
      [d.raw.stationno, d.raw.itemname].some(v => String(v || '').trim().toLowerCase() === q));
    if (!matches.length) {
      matches = devices.filter(d =>
        [d.raw.itemid || d.id, d.raw.stationno, d.raw.itemname].some(v =>
          String(v || '').toLowerCase().includes(q)));
    }
    if (matches.length > 1) {
      toast('找到 ' + matches.length + ' 台匹配设备，请输入更完整的设备号', true);
      return;
    }
    found = matches[0];
  }
  if (!found) { toast('未找到设备：' + mapSearchInput.value.trim(), true); return; }
  if (String(found.raw.status == null ? '' : found.raw.status).trim() !== '1') {
    toast('设备 ' + found.id + ' 的 status≠1，当前未显示在布局图', true);
    return;
  }

  if (dataView.style.display === 'block') document.getElementById('v-map').click();
  const foundKey = overlapKey(found);
  if ((overlapGroups().get(foundKey) || []).length > 1) expandedOverlapKeys.add(foundKey);
  selected = new Set([found.id]);
  renderAll();
  const foundEntry = displayEntries().entries.find(entry => entry.d.id === found.id) ||
    { x: found.x, y: found.y };
  scale = Math.min(MAX_SCALE, Math.max(scale, 2));
  const r = stage.getBoundingClientRect();
  const usableWidth = editMode ? Math.max(240, r.width - 380) : r.width;
  tx = usableWidth / 2 - (foundEntry.x + found.w / 2) * CELL * scale;
  ty = r.height / 2 - (foundEntry.y + found.h / 2) * CELL * scale;
  applyT();
  const el = world.querySelector('.blk[data-id="' + CSS.escape(found.id) + '"]');
  if (el) el.classList.add('located');
  toast('已定位设备：' + found.id);
}
document.getElementById('map-search-btn').onclick = locateDevice;
mapSearchInput.addEventListener('keydown', e => {
  if (e.key === 'Enter') { e.preventDefault(); locateDevice(); }
});

// ---- 编辑操作 ----
function setMode(edit) {
  editMode = edit;
  document.body.classList.toggle('editing', edit);
  document.getElementById('mode-edit').classList.toggle('on', edit);
  document.getElementById('mode-browse').classList.toggle('on', !edit);
  if (!edit) { selected = new Set(); refreshSel(); }
}
document.getElementById('mode-edit').onclick = () => setMode(true);
document.getElementById('mode-browse').onclick = () => setMode(false);

document.getElementById('btn-add').onclick = () => {
  const nums = devices.map(d => parseInt(d.id, 10)).filter(v => !isNaN(v));
  let n = (nums.length ? Math.max(...nums) : 0) + 1;
  while (devices.some(d => d.id === String(n))) n++;
  const r = stage.getBoundingClientRect();
  const x = Math.round((-tx + r.width / 2) / scale / CELL) - 0;
  const y = Math.round((-ty + r.height / 2) / scale / CELL) - 0;
  const id = String(n);
  const raw = {};
  FIELDS.forEach(f => raw[f] = '');
  Object.assign(raw, {
    itemid: id, itemname: id, stationno: id,
    groupname: DEFAULTS.groupname, zonecode: DEFAULTS.zone, equipmentType: DEFAULTS.type,
    locationx: String(Math.max(0, x)), locationy: String(Math.max(0, y)),
    width: '1', height: '1', arrowdirection: '',
    status: '1', belong: '1', stationtype: '0', createtime: nowStr(),
  });
  const d = {
    id, name: id, remark: '', x: Math.max(0, x), y: Math.max(0, y),
    w: 1, h: 1, arrows: [], field5: 0,
    raw, manual: false, ox: x, oy: y,
  };
  pushUndo('添加设备 ' + id);
  devices.push(d);
  selected = new Set([d.id]);
  renderAll();
  const inp = panel.querySelector('input[data-k="name"]');
  if (inp) { inp.focus(); inp.select(); }
};

document.getElementById('btn-del').onclick = () => {
  if (!selected.size) return;
  const ids = new Set(selected);
  pushUndo('删除 ' + ids.size + ' 台设备');
  for (let i = devices.length - 1; i >= 0; i--) {
    if (ids.has(devices[i].id)) devices.splice(i, 1);
  }
  selected = new Set();
  renderAll();
};

document.getElementById('btn-refill').onclick = () => {
  pushUndo('重算链路填充');
  devices.forEach(d => { d.manual = false; });
  renderAll(true);
  toast('已按当前坐标重算链路填充,保存后写入 width/height');
};


async function saveToCsv() {
  const seen = new Set();
  for (const d of devices) {
    const id = String(d.raw.itemid || '').trim();
    if (!id) { toast('存在空 itemid，请修正后保存', true); return; }
    if (seen.has(id)) { toast('itemid 重复：' + id, true); return; }
    seen.add(id);
  }
  // 以原始行做基底,覆盖页面负责的字段,其余 WCS 列原样带回
  const rows = devices.map(d => Object.assign({}, d.raw, {
    itemid: String(d.raw.itemid || ''),
    itemname: String(d.raw.itemname || d.raw.itemid || ''),
    locationx: String(d.x),
    locationy: String(d.y),
    width: String(d.w),
    height: String(d.h),
    arrowdirection: arrowValue(d),
  }));
  try {
    const res = await fetch('/save-layout', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ format: 'wcs_layout_v1', rows }),
    });
    const data = await res.json();
    if (!res.ok || !data.ok) throw new Error(data.error || ('HTTP ' + res.status));
    dirtyCells.clear();
    undoStack.length = 0;
    updateUndoButton();
    toast('已保存 ' + data.count + ' 台设备到 wcs_layout.csv');
    if (dataView.style.display === 'block') renderTable(document.getElementById('q').value.trim());
  } catch (err) {
    toast('保存失败：' + err.message, true);
  }
}
document.getElementById('btn-save').onclick = saveToCsv;
document.getElementById('btn-save-data').onclick = saveToCsv;
document.getElementById('btn-undo').onclick = undoLast;

addEventListener('keydown', e => {
  const editingText = e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT' ||
    e.target.tagName === 'TEXTAREA' || e.target.isContentEditable;
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'z' && !editingText) {
    e.preventDefault();
    undoLast();
    return;
  }
  if (!editMode || editingText) return;
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 's') {
    e.preventDefault();
    document.getElementById('btn-save').click();
    return;
  }
  if (e.key === 'Delete' || e.key === 'Backspace') { document.getElementById('btn-del').click(); }
  if (e.key === 'Escape') { selected = new Set(); refreshSel(); }
});

// ---- 视图切换 ----
const vMap = document.getElementById('v-map'), vData = document.getElementById('v-data');
const dataView = document.getElementById('data-view');
let dataDirty = true;
vMap.onclick = () => { vMap.classList.add('on'); vData.classList.remove('on');
  stage.style.display = ''; dataView.style.display = 'none'; fit(); };
vData.onclick = () => { vData.classList.add('on'); vMap.classList.remove('on');
  stage.style.display = 'none'; dataView.style.display = 'block';
  if (dataDirty) { renderTable(document.getElementById('q').value.trim()); dataDirty = false; } };

// ---- 数据表:全部 WCS 字段,支持增删改查 ----
const tbody = document.getElementById('tbody');
const dhead = document.getElementById('dhead');
const dcount = document.getElementById('d-count');
const btnDelRows = document.getElementById('d-del');
// direction 现在是"暂存备用",按自由文本处理
const NUM_FIELDS = new Set(['locationx', 'locationy', 'width', 'height']);
const pick = new Set();
const dirtyCells = new Set();
let sortKey = null, sortAsc = true;

const intOr = (v, dflt) => {
  const n = parseInt(String(v == null ? '' : v).trim(), 10);
  return isNaN(n) ? dflt : n;
};

// 表格里改的是 raw,这里把 raw 同步回地图渲染用的派生属性
function syncDerived(d) {
  const r = d.raw;
  d.id = String(r.itemid || d.id);
  d.name = String(r.itemname || r.itemid || d.id);
  d.remark = String(r.remark == null ? '' : r.remark);
  d.x = intOr(r.locationx, 0);
  d.y = intOr(r.locationy, 0);
  d.w = Math.max(1, intOr(r.width, 1));
  d.h = Math.max(1, intOr(r.height, 1));
  d.arrows = normalizeArrows(r.arrowdirection);
  d.field5 = intOr(r.field5, 0);
}

// 预览图里改动过就刷新 createtime
function touch(d) {
  d.raw.createtime = nowStr();
}

function filterRows(q) {
  const needle = String(q || '').toLowerCase();
  let list = needle
    ? devices.filter(d => FIELDS.some(f => String(d.raw[f] || '').toLowerCase().includes(needle)))
    : devices.slice();
  if (sortKey) {
    list.sort((a, b) => {
      const va = String(a.raw[sortKey] || ''), vb = String(b.raw[sortKey] || '');
      const na = parseFloat(va), nb = parseFloat(vb);
      const numeric = va !== '' && vb !== '' && !isNaN(na) && !isNaN(nb);
      const c = numeric ? na - nb : va.localeCompare(vb);
      return c * (sortAsc ? 1 : -1);
    });
  }
  return list;
}

function renderTable(q = '') {
  const list = filterRows(q);
  document.getElementById('empty').style.display = list.length ? 'none' : 'block';
  tbody.innerHTML = list.map(d =>
    '<tr data-id="' + esc(d.id) + '">' +
    '<td class="pick"><input type="checkbox" data-pick="' + esc(d.id) + '"' + (pick.has(d.id) ? ' checked' : '') + '></td>' +
    FIELDS.map(f => '<td class="ed' + (f === 'itemid' ? ' idcol' : '') + (NUM_FIELDS.has(f) ? ' num' : '') +
      (dirtyCells.has(d.id + '|' + f) ? ' dirty' : '') +
      '" contenteditable="true" data-id="' + esc(d.id) + '" data-key="' + f + '">' +
      esc(d.raw[f] == null ? '' : d.raw[f]) + '</td>').join('') +
    '</tr>').join('');
  dcount.textContent = '共 ' + list.length + ' 台' + (pick.size ? ' · 已选 ' + pick.size + ' 台' : '');
  btnDelRows.disabled = !pick.size;
  const all = document.getElementById('d-all');
  if (all) all.checked = list.length > 0 && list.every(d => pick.has(d.id));
}

function commitCell(td) {
  const key = td.dataset.key, id = td.dataset.id;
  const d = byId()[id];
  if (!d) return;
  let v = td.textContent.replace(/[\r\n\t]+/g, ' ').trim();
  if (key === 'itemid') {
    if (!v) { toast('itemid 不能为空', true); td.textContent = d.raw.itemid; return; }
    if (v !== d.id && byId()[v]) { toast('itemid ' + v + ' 已存在', true); td.textContent = d.raw.itemid; return; }
  }
  if (NUM_FIELDS.has(key) && v !== '') {
    const n = Number(v);
    if (!isFinite(n)) { toast(key + ' 需要数字', true); td.textContent = d.raw[key]; return; }
    v = String(Math.round(n));
  }
  if (String(d.raw[key] == null ? '' : d.raw[key]) === v) { td.textContent = v; return; }
  pushUndo('修改 ' + fieldLabel(key));
  const oldId = d.id;
  d.raw[key] = v;
  if (key === 'width' || key === 'height') d.manual = true;
  syncDerived(d);
  touch(d);
  dirtyCells.add(d.id + '|' + key);
  if (d.id !== oldId) {
    if (pick.delete(oldId)) pick.add(d.id);
    if (selected.delete(oldId)) selected.add(d.id);
  }
  renderAll();
  toast('已修改 ' + key + '（尚未保存）');
}

dhead.innerHTML = '<th class="pick"><input type="checkbox" id="d-all"></th>' +
  FIELDS.map(f => '<th data-k="' + f + '"' + (f === 'itemid' ? ' class="idcol"' : '') + '>' + f + '</th>').join('');

tbody.addEventListener('focusout', e => {
  const td = e.target.closest && e.target.closest('td.ed');
  if (td) commitCell(td);
});
tbody.addEventListener('keydown', e => {
  if (e.key === 'Enter' && e.target.closest && e.target.closest('td.ed')) {
    e.preventDefault();
    e.target.blur();
  }
});
tbody.addEventListener('change', e => {
  const cb = e.target.closest && e.target.closest('input[data-pick]');
  if (!cb) return;
  cb.checked ? pick.add(cb.dataset.pick) : pick.delete(cb.dataset.pick);
  dcount.textContent = '共 ' + filterRows(document.getElementById('q').value.trim()).length + ' 台' +
    (pick.size ? ' · 已选 ' + pick.size + ' 台' : '');
  btnDelRows.disabled = !pick.size;
});
dhead.addEventListener('change', e => {
  if (e.target.id !== 'd-all') return;
  const list = filterRows(document.getElementById('q').value.trim());
  if (e.target.checked) list.forEach(d => pick.add(d.id));
  else list.forEach(d => pick.delete(d.id));
  renderTable(document.getElementById('q').value.trim());
});
dhead.addEventListener('click', e => {
  const th = e.target.closest && e.target.closest('th[data-k]');
  if (!th) return;
  const k = th.dataset.k;
  if (sortKey === k) sortAsc = !sortAsc; else { sortKey = k; sortAsc = true; }
  renderTable(document.getElementById('q').value.trim());
});
document.getElementById('q').addEventListener('input', e => {
  renderTable(e.target.value.trim());
});

document.getElementById('d-add').onclick = () => {
  const nums = devices.map(d => parseInt(d.raw.itemid, 10)).filter(v => !isNaN(v));
  let n = (nums.length ? Math.max(...nums) : 0) + 1;
  while (devices.some(d => String(d.raw.itemid) === String(n))) n++;
  const raw = {};
  FIELDS.forEach(f => raw[f] = '');
  Object.assign(raw, {
    itemid: String(n), itemname: String(n), stationno: String(n),
    groupname: DEFAULTS.groupname, zonecode: DEFAULTS.zone, equipmentType: DEFAULTS.type,
    locationx: '0', locationy: '0', width: '1', height: '1', arrowdirection: '',
    status: '1', belong: '1', stationtype: '0', createtime: nowStr(),
  });
  pushUndo('新增设备 ' + n);
  devices.push({
    id: String(n), name: String(n), remark: '', x: 0, y: 0, w: 1, h: 1,
    arrows: [], field5: 0, raw, manual: false, ox: 0, oy: 0,
  });
  renderAll();
  const tr = tbody.querySelector('tr[data-id="' + CSS.escape(String(n)) + '"]');
  if (tr) {
    tr.scrollIntoView({ block: 'center' });
    const td = tr.querySelector('td[data-key="itemid"]');
    if (td) td.focus();
  }
  toast('已新增设备 ' + n + '，补充字段后保存');
};

btnDelRows.onclick = () => {
  if (!pick.size) return;
  const n = pick.size;
  pushUndo('删除 ' + n + ' 台设备');
  for (let i = devices.length - 1; i >= 0; i--) if (pick.has(devices[i].id)) devices.splice(i, 1);
  pick.clear();
  renderAll();
  toast('已删除 ' + n + ' 台设备（尚未保存）');
};

renderTable();
renderAll();
fit();
</script>
</body>
</html>
"""

def render_html(devices, station_colors=None):
    meta = {"single": SINGLE_EDIT_FIELDS, "batch": BATCH_EDIT_FIELDS,
            "readonly": READONLY_FIELDS}
    config = load_station_color_config()
    if station_colors is not None:
        config["colors"] = station_colors
    html = TEMPLATE.replace("__DATA__", json.dumps(devices, ensure_ascii=False))
    html = html.replace("__FIELDS__", json.dumps(WCS_FIELDS, ensure_ascii=False))
    html = html.replace("__LABELS__", json.dumps(FIELD_LABELS, ensure_ascii=False))
    html = html.replace("__EDIT_META__", json.dumps(meta, ensure_ascii=False))
    html = html.replace("__STATION_COLORS__", json.dumps(
        config["colors"], ensure_ascii=False))
    html = html.replace("__REMARK_COLOR_RULES__", json.dumps(
        config["remark_rules"], ensure_ascii=False))
    return html.replace("__DEFAULT_STATION_COLORS__", json.dumps(
        DEFAULT_STATION_COLORS, ensure_ascii=False))


if __name__ == "__main__":
    devices = devices_from_rows(load_rows())
    html = render_html(devices)
    with open(os.path.join(ROOT, "wcs_monitor.html"), "w", encoding="utf-8") as f:
        f.write(html)
    print(f"已生成 wcs_monitor.html | 设备 {len(devices)} 台, 字段 {len(WCS_FIELDS)} 列, "
          f"文件 {len(html) / 1024:.0f} KB")
