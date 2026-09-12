---
name: cad-wcs-layout
description: Convert a CAD layout drawing (DXF) into a WCS device table (expdata schema) plus an editable HTML grid monitor/canvas page, or edit an existing WCS-shaped layout CSV with a full-field CRUD table, single/batch property panels, chain-fill spans, and flow-arrow tools. Use for CAD-to-WCS layout mapping; not for general CAD viewing or 3D work.
---

# CAD -> WCS 布局映射

把 CAD 布局图里的设备标签解析成 WCS 设备表结构（`expdata` 34 列）的 CSV，
并生成带编辑态的 HTML 监控页；编辑结果经本地服务整体写回 CSV。
`scripts/` 下是经过验证的脚本，复制到目标项目后按需改常量即可，不要凭记忆重写解析逻辑。

## 输出数据结构（核心约定）

CSV 列名与顺序严格等于 WCS 设备表 `expdata`：

```
itemid,itemname,groupname,objects,datetype,signaltype,value,stationno,remark,
userid,createtime,field1,field2,field3,field4,field5,warehouseid,status,stationtype,
locationx,locationy,width,height,belong,direction,zonecode,areacode,arrowdirection,
zone,workingLocation1,workingLocation2,workingNumber,protocolType,equipmentType
```

**所有字段定义集中在 `scripts/wcs_schema.py`**：`WCS_FIELDS`（列顺序）、`FIELD_LABELS`（中文名）、
`SINGLE_EDIT_FIELDS` / `BATCH_EDIT_FIELDS` / `READONLY_FIELDS`（预览图编辑能力）。
改字段只改这一处，页面表头、属性面板、批量面板都会跟着变。

CAD 能提供来源的字段：

- `itemid` = 图纸编号；`itemname` / `stationno` 默认同 itemid
- `groupname` / `equipmentType` = `Convery`；`zonecode` = `输送机监控`（常量，按项目改）
- `locationx` / `locationy` = CAD 毫米换算的格子坐标（1 格 = `MM_PER_CELL`，默认 1150mm，Y 轴朝下）
- `arrowdirection` = 箭头类型：0 空 / 1 右 / 2 左 / 3 下 / 4 上 / 5 左右双向 / 6 上下双向。
  来源有优先级：① CAD 箭头锚点角度（0°→1、90°→4、180°→2、270°→3，常量 `ANGLE_TO_ARROW`）
  ② 编号序列推断出的流向（右→1、上→4、左→2、下→3，常量 `DIRECTION_TO_ARROW`）
  两者都没有才是 0
- `width` / `height` = 提取阶段一律 1，链路填充跨度由 HTML 计算后写回
- `status` = 1（预览图只显示 status==1 的设备）、`belong` = 1、`stationtype` = 0、
  `createtime` = 导出时的当前时间

其余字段无数据来源时留空字符串，不要编造默认值。

**不要**再引入 `renderwidth`/`renderheight`/`x_mm`/`y_mm`/`direction_source` 之类旁路列；
渲染跨度并入 `width`/`height`。

## 流程

1. `extract_devices.py`：流式解析 DXF（支持几百 MB 文本 DXF），按块层级还原世界坐标，
   输出 `devices_world.csv`（kind,value,x,y）。适配新图纸时改顶部的图层名/类型过滤。
2. `generate_layout.py`：毫米 -> 格子（Y 翻转），箭头类型换算，按 WCS 34 列输出 `wcs_layout.csv`。
   可调参数集中在顶部（`MM_PER_CELL`、偏移、`GROUP_NAME`、`ZONE_CODE`、`STATUS`、`BELONG`、
   `STATION_TYPE`、`ANGLE_TO_ARROW`、`DIRECTION_TO_ARROW`）。
   方向推断是"CAD 箭头锚点优先、编号序列兜底"，推断结果只写进 `arrowdirection`。
3. `build_html.py`：读 CSV 渲染 `wcs_monitor.html`（自包含；server.py 也会按请求动态渲染）。
4. `server.py`：本地服务（默认 `127.0.0.1:8734`）+ `POST /save-layout` 整体回写 CSV。

脚本都用「脚本所在目录」定位输入输出，可从任意工作目录运行；`wcs_schema.py` 必须和它们同目录。

## 链路填充

预览里的"设备连成一条线"由链路填充实现：相邻同排/同列设备、间隔 1~`CHAIN_MAX`（默认 4）格，
横向优先。实现在页面 JS 的 `autoFill()`，加载时按坐标计算，编辑后自动重算，
保存时结果写进 `width`/`height`。手工改过宽高的设备标记 `manual`，不再被自动填充覆盖；
顶部`重算链路填充`按钮清空标记后重算。

**不变量**：`autoFill()` 的邻居图必须包含全部设备（含手工值设备），只对非手工设备应用结果。
早期版本把手工值设备排除出邻居图，导致保存→重载→再保存时反复多填（224 涨到 259）。
改这段前先守住这个不变量，并验证幂等：载入 224 → 保存 → 重载 224。

## 三个编辑入口

**布局视图 · 单选面板**：单击设备后在右侧改 `SINGLE_EDIT_FIELDS` 里的字段。
标签统一显示成 `itemname(设备名称)`（原始字段名 + 中文名）。
`READONLY_FIELDS`（创建时间、仓库ID）在面板底部只读展示。

**布局视图 · 批量面板**：框选或 Ctrl+多选后，对 `BATCH_EDIT_FIELDS` 逐字段批量设置
（留空表示不改该字段），另有 `ΔX/ΔY` 相对批量移动。
整格拖拽移动、Del 删除、Esc 清选、右键拖拽平移画布、Ctrl+S 保存。

**设备数据视图**：全字段表格，单元格 `contenteditable` 直接改（改动标黄），
支持任意字段搜索、新增设备、勾选批量删除、列头排序、保存到数据源；
`itemid` 列横向滚动时固定。这一视图不受上面的编辑能力清单限制，是原始数据入口。

## 渲染约定

- 设备块只画 `status == 1` 的；标签默认 `itemname`，`remark` 非空时换行加一行小字
- `field5` = 层级，块 `z-index = 1 + field5`（越大越置顶），选中设备临时置顶，箭头层始终最上
- 悬停提示显示名称 / 备注 / 坐标 / 渲染大小，不显示设备状态
- 预览图里任何改动都会把该设备的 `createtime`（在 Python 侧）刷新为修改时间

## 验证与坑

- 预览必须走 `python server.py` 的 localhost 服务，`file://` 会被浏览器安全策略拦截；
  普通 `python -m http.server` 没有保存端点。
- 保存报"CSV 被占用"时，让用户关闭 Excel/WPS 后重试；写回前校验 `itemid` 唯一。
- `server.py` 每次请求会重载 `wcs_schema` 和 `build_html` —— 只重载 `build_html` 不够，
  字段定义改了不会生效（踩过）。
- 重启服务前确认端口没有残留进程（曾出现两个进程抢答、页面读到旧数据）。
- 批量面板的控件不要用和单选面板相同的 `data-k` 绑定，否则下拉 change 会触发单选逻辑
  并重渲染面板、把值重置回默认（踩过）。
- 浏览器自动化验证：设备块很小时 `page.click('.blk', {hasText})` 可能误点相邻块，
  改用元素中心坐标 `mouse.click`；框选命中判定必须统一用格子坐标（混用像素是历史 bug）。
- 大图纸上 width/height 是"渲染跨度"而非物理尺寸；真实外形需要从轮廓几何提取，那是独立的后续工作。
