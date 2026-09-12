import csv
import json
import os

from wcs_schema import (WCS_FIELDS, FIELD_LABELS, SINGLE_EDIT_FIELDS,
                        BATCH_EDIT_FIELDS, READONLY_FIELDS)


ROOT = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(ROOT, "wcs_layout.csv")


def _int(value, default=0):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


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
            # arrowdirection 是箭头类型枚举(0空 1右 2左 3下 4上 5左右双向 6上下双向)
            "arrow": _int(raw["arrowdirection"]) if raw["arrowdirection"].strip() else 0,
            "field5": _int(raw["field5"]),
            "raw": raw,
        })
    return devices


def load_rows():
    return list(csv.DictReader(open(CSV_PATH, encoding="utf-8-sig")))

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
    flex-direction: column; line-height: 1.15; overflow: hidden; text-align: center;
    font-size: 10px; font-weight: 600; color: #1b3350; user-select: none;
    background: #ccdcf0; border: 1px solid #55708c; box-shadow: 0 1px 2px rgba(20,30,40,.22);
    z-index: 1;
  }
  .blk .rm { font-weight: 400; font-size: 9px; opacity: .72; }
  body.editing .blk { cursor: pointer; }
  body.editing .blk:hover { border-color: #2563eb; box-shadow: 0 1px 2px rgba(20,30,40,.16), 0 0 0 1px #2563eb; }
  .blk.sel { background: #9fc2ff; border-color: #1d4fd8; box-shadow: 0 0 0 1.5px #1d4fd8, 0 1px 3px rgba(20,30,40,.25); }
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
    <button class="btn" id="rot-ccw" title="选中设备箭头逆时针旋转 90 度" disabled>箭头⟲</button>
    <button class="btn" id="rot-cw" title="选中设备箭头顺时针旋转 90 度" disabled>箭头⟳</button>
    <button class="btn primary" id="btn-save">保存到数据源</button>
  </div>
  <div class="tools" style="margin-left:auto" title="缩放">
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
<div id="tip"></div>
<div id="toast"></div>
<script>
const RAW = __DATA__;
const FIELDS = __FIELDS__;
const LABELS = __LABELS__;
const EDIT_META = __EDIT_META__;
// 这些字段用数字输入并做整数校验
const NUM_EDIT = new Set(['locationx', 'locationy', 'width', 'height', 'field5', 'status']);
const CELL = 26;
const CHAIN_MAX = 4;
const DEFAULTS = { groupname: 'Convery', type: 'Convery', zone: '输送机监控' };
// arrowdirection 箭头类型
const ARROWS = [
  { v: 0, label: '无' }, { v: 1, label: '右' }, { v: 2, label: '左' },
  { v: 3, label: '下' }, { v: 4, label: '上' },
  { v: 5, label: '左右双向' }, { v: 6, label: '上下双向' },
];
// 顺时针/逆时针轮换(双向箭头只互换)
const ARROW_CW = { 0: 1, 1: 3, 3: 2, 2: 4, 4: 1, 5: 6, 6: 5 };
const ARROW_CCW = { 0: 1, 1: 4, 4: 2, 2: 3, 3: 1, 5: 6, 6: 5 };
const STATION_TYPES = ['0', '1', '3', '5', '6', '7', '8', '10', '11', '16'];
const pad2 = n => String(n).padStart(2, '0');
const nowStr = () => {
  const t = new Date();
  return t.getFullYear() + '-' + pad2(t.getMonth() + 1) + '-' + pad2(t.getDate()) +
    ' ' + pad2(t.getHours()) + ':' + pad2(t.getMinutes()) + ':' + pad2(t.getSeconds());
};

const devices = RAW.map(r => ({
  id: r.id, name: r.name, remark: r.remark,
  x: r.x, y: r.y, w: r.w, h: r.h,
  arrow: r.arrow, field5: r.field5,
  raw: r.raw,
  manual: r.w > 1 || r.h > 1,
  ox: r.x, oy: r.y,
}));

// 预览图只画 status == 1 的设备
const visible = () => devices.filter(d => String(d.raw.status == null ? '' : d.raw.status).trim() === '1');

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

let toastTimer = null;
function toast(msg, err) {
  toastEl.textContent = msg;
  toastEl.className = err ? 'err' : '';
  toastEl.style.display = 'block';
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toastEl.style.display = 'none', err ? 4200 : 2200);
}

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

function renderBlocks() {
  world.querySelectorAll('.blk').forEach(el => el.remove());
  visible().forEach(d => {
    const el = document.createElement('div');
    const sel = selected.has(d.id);
    el.className = 'blk' + (sel ? ' sel' : '');
    el.dataset.id = d.id;
    el.style.left = d.x * CELL + 1 + 'px';
    el.style.top = d.y * CELL + 1 + 'px';
    el.style.width = d.w * CELL - 3 + 'px';
    el.style.height = d.h * CELL - 3 + 'px';
    // field5:数字越大越置顶;选中的压在所有设备之上(箭头层仍在最上面)
    el.style.zIndex = String(sel ? 90000 : 1 + Math.max(0, d.field5 | 0));
    const label = d.name || d.id;
    const remark = String(d.raw.remark == null ? '' : d.raw.remark).trim();
    el.innerHTML = '<span class="nm">' + esc(label) + '</span>' +
      (remark ? '<span class="rm">' + esc(remark) + '</span>' : '');
    world.appendChild(el);

    el.addEventListener('mouseenter', e => {
      tip.innerHTML = '<b>' + esc(label) + '</b>' +
        (remark ? '<br>' + esc(remark) : '') +
        '<br>坐标:(' + d.x + ', ' + d.y + ')' +
        '<br>渲染大小:' + d.w + '×' + d.h;
      tip.style.display = 'block';
    });
    el.addEventListener('mousemove', e => {
      tip.style.left = Math.min(e.clientX + 14, innerWidth - 200) + 'px';
      tip.style.top = Math.min(e.clientY + 14, innerHeight - 80) + 'px';
    });
    el.addEventListener('mouseleave', () => tip.style.display = 'none');
  });
}

function esc(s) {
  return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

const ARROW_DEF = '<path d="M0.8,0.8L7.2,4L0.8,7.2" fill="none" stroke-width="1.5" ' +
  'stroke-linecap="round" stroke-linejoin="round"/>';

function marker(id, color, reverse) {
  return '<marker id="' + id + '" markerWidth="9" markerHeight="9" refX="6" refY="4" ' +
    'orient="' + (reverse ? 'auto-start-reverse' : 'auto') + '" markerUnits="userSpaceOnUse">' +
    '<g stroke="' + color + '">' + ARROW_DEF + '</g></marker>';
}

// 箭头类型 -> 方向(水平/垂直)与是否双向
function arrowGeom(type) {
  switch (type) {
    case 1: return { dir: 1, both: false };   // 右
    case 2: return { dir: -1, both: false };  // 左
    case 3: return { vert: true, dir: 1, both: false };   // 下
    case 4: return { vert: true, dir: -1, both: false };  // 上
    case 5: return { dir: 1, both: true };    // 左右双向
    case 6: return { vert: true, dir: 1, both: true };    // 上下双向
    default: return null;                     // 0 = 空
  }
}

function renderArrows() {
  const parts = ['<defs>' +
    marker('ah', '#4a5a68', false) + marker('ahr', '#4a5a68', true) +
    marker('ahs', '#d92d20', false) + marker('ahsr', '#d92d20', true) +
    '</defs>'];
  visible().forEach(d => {
    const geo = arrowGeom(d.arrow);
    if (!geo) return;
    const cx = (d.x + d.w / 2) * CELL;
    const cy = (d.y + d.h / 2) * CELL;
    const vert = !!geo.vert;
    let len = (vert ? d.h : d.w) * CELL - 14;
    len = Math.max(18, len);
    const half = len / 2;
    const x1 = vert ? cx : cx - half, y1 = vert ? cy - half : cy;
    const x2 = vert ? cx : cx + half, y2 = vert ? cy + half : cy;
    const sel = selected.has(d.id);
    const stroke = sel ? '#d92d20' : '#4a5a68';
    // 单向箭头的箭头端在 dir 指定的一侧;双向两端都有
    const startMark = geo.both || geo.dir < 0;
    const endMark = geo.both || geo.dir > 0;
    parts.push('<line data-id="' + esc(d.id) + '" x1="' + x1.toFixed(1) + '" y1="' + y1.toFixed(1) +
      '" x2="' + x2.toFixed(1) + '" y2="' + y2.toFixed(1) +
      '" stroke="' + stroke + '" stroke-opacity="' + (sel ? '.8' : '.38') + '" stroke-width="1.6"' +
      (startMark ? ' marker-start="url(#' + (sel ? 'ahsr' : 'ahr') + ')"' : '') +
      (endMark ? ' marker-end="url(#' + (sel ? 'ahs' : 'ah') + ')"' : '') + '/>');
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
  document.getElementById('rot-ccw').disabled = !n;
  document.getElementById('rot-cw').disabled = !n;
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

// 面板改动统一走这里:写回 raw -> 同步派生属性 -> 刷新 createtime
function applyPanelEdit(d, key, value) {
  if (key === 'itemid') {
    const v = String(value).trim();
    if (!v) { toast('itemid 不能为空', true); return false; }
    if (v !== d.id && byId()[v]) { toast('itemid ' + v + ' 已存在', true); return false; }
    if (selected.delete(d.id)) selected.add(v);
    if (pick && pick.delete(d.id)) pick.add(v);
  }
  if ((NUM_FIELDS.has(key) || key === 'status' || key === 'field5') && String(value).trim() !== '') {
    const n = Number(value);
    if (!isFinite(n)) { toast(key + ' 需要数字', true); return false; }
    value = String(Math.round(n));
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
  if (key === 'arrowdirection') return frowSelect(label, key, val, ARROWS);
  if (key === 'stationtype') {
    return frowSelect(label, key, val, STATION_TYPES.map(v => ({ v, label: v })));
  }
  return NUM_EDIT.has(key) ? frowNum(label, key, val) : frowText(label, key, val);
}

// 可批量编辑字段 -> 只返回控件本身(data-bk,不会被单选编辑逻辑捕获)
function batchControl(key) {
  const ph = ' placeholder="留空不改"';
  if (key === 'arrowdirection') {
    return '<select data-bk="' + key + '">' +
      ARROWS.map(a => '<option value="' + a.v + '">' + a.label + '</option>').join('') + '</select>';
  }
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
      if (v.trim() === '') { toast('请先填写 ' + fieldLabel(key), true); return; }
      if (NUM_EDIT.has(key)) {
        const n = Number(v);
        if (!isFinite(n)) { toast((LABELS[key] || key) + ' 需要数字', true); return; }
        v = String(Math.round(n));
      }
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
  panel.querySelectorAll('input[data-k], select[data-k]').forEach(inp => inp.onchange = () => {
    const k = inp.dataset.k;
    if (k === 'bdx' || k === 'bdy') return;   // 批量移动由"移动"按钮处理
    const d = selDevices()[0];
    if (!d) return;
    if (!applyPanelEdit(d, k, inp.value)) renderPanel();  // 校验失败时回显原值
  });
}

function renderAll() {
  autoFill();
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
  const ns = Math.min(3, Math.max(0.3, scale * factor));
  tx = cx - (cx - tx) * (ns / scale);
  ty = cy - (cy - ty) * (ns / scale);
  scale = ns;
  applyT();
}
stage.addEventListener('wheel', e => {
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
    const line = svg.querySelector('line[data-id="' + CSS.escape(id) + '"]');
    if (line) line.style.transform = t;
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
    sel.forEach(d => {
      d.x += dx; d.y += dy; d.ox = d.x; d.oy = d.y;
      d.raw.locationx = String(d.x); d.raw.locationy = String(d.y);
      touch(d);
    });
    renderAll();
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
    width: '1', height: '1', arrowdirection: '0',
    status: '1', belong: '1', stationtype: '0', createtime: nowStr(),
  });
  const d = {
    id, name: id, remark: '', x: Math.max(0, x), y: Math.max(0, y),
    w: 1, h: 1, arrow: 0, field5: 0,
    raw, manual: false, ox: x, oy: y,
  };
  devices.push(d);
  selected = new Set([d.id]);
  renderAll();
  const inp = panel.querySelector('input[data-k="name"]');
  if (inp) { inp.focus(); inp.select(); }
};

document.getElementById('btn-del').onclick = () => {
  if (!selected.size) return;
  const ids = new Set(selected);
  for (let i = devices.length - 1; i >= 0; i--) {
    if (ids.has(devices[i].id)) devices.splice(i, 1);
  }
  selected = new Set();
  renderAll();
};

document.getElementById('btn-refill').onclick = () => {
  devices.forEach(d => { d.manual = false; });
  renderAll();
  toast('已按当前坐标重算链路填充,保存后写入 width/height');
};

document.getElementById('rot-ccw').onclick = () => {
  selDevices().forEach(d => { d.raw.arrowdirection = String(ARROW_CCW[d.arrow] ?? 1); syncDerived(d); touch(d); });
  renderAll();
};
document.getElementById('rot-cw').onclick = () => {
  selDevices().forEach(d => { d.raw.arrowdirection = String(ARROW_CW[d.arrow] ?? 1); syncDerived(d); touch(d); });
  renderAll();
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
    arrowdirection: String(d.arrow),
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
    toast('已保存 ' + data.count + ' 台设备到 wcs_layout.csv');
    if (dataView.style.display === 'block') renderTable(document.getElementById('q').value.trim());
  } catch (err) {
    toast('保存失败：' + err.message, true);
  }
}
document.getElementById('btn-save').onclick = saveToCsv;
document.getElementById('btn-save-data').onclick = saveToCsv;

addEventListener('keydown', e => {
  if (!editMode || e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT') return;
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
const NUM_FIELDS = new Set(['locationx', 'locationy', 'width', 'height', 'arrowdirection']);
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
  d.arrow = intOr(r.arrowdirection, 0);
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
    locationx: '0', locationy: '0', width: '1', height: '1', arrowdirection: '0',
    status: '1', belong: '1', stationtype: '0', createtime: nowStr(),
  });
  devices.push({
    id: String(n), name: String(n), remark: '', x: 0, y: 0, w: 1, h: 1,
    arrow: 0, field5: 0, raw, manual: false, ox: 0, oy: 0,
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

def render_html(devices):
    meta = {"single": SINGLE_EDIT_FIELDS, "batch": BATCH_EDIT_FIELDS,
            "readonly": READONLY_FIELDS}
    html = TEMPLATE.replace("__DATA__", json.dumps(devices, ensure_ascii=False))
    html = html.replace("__FIELDS__", json.dumps(WCS_FIELDS, ensure_ascii=False))
    html = html.replace("__LABELS__", json.dumps(FIELD_LABELS, ensure_ascii=False))
    return html.replace("__EDIT_META__", json.dumps(meta, ensure_ascii=False))


if __name__ == "__main__":
    devices = devices_from_rows(load_rows())
    html = render_html(devices)
    with open(os.path.join(ROOT, "wcs_monitor.html"), "w", encoding="utf-8") as f:
        f.write(html)
    print(f"已生成 wcs_monitor.html | 设备 {len(devices)} 台, 字段 {len(WCS_FIELDS)} 列, "
          f"文件 {len(html) / 1024:.0f} KB")
