# CAD → WCS 布局映射 Skill

将 CAD 布局图中的设备标签转换为 WCS `expdata` 34 列 CSV，并生成可编辑、可保存的 HTML 网格画布。既可从 DXF 建立新布局，也可直接维护已有的 WCS 布局 CSV。

仓库同时包含 Codex skill 指令和可独立复制使用的 Python 脚本。

## 功能概览

- 流式解析大型文本 DXF，支持块嵌套、平移、缩放和旋转后的世界坐标还原。
- 将 CAD 毫米坐标换算为画布格子坐标，输出固定的 WCS 34 列结构。
- 根据 CAD 箭头锚点或设备编号序列推断流向。
- 提供浏览、编辑、搜索、单选、批量修改、框选、拖动、新增和删除。
- 修改保存前支持 50 步撤回和 `Ctrl+Z`。
- 同坐标设备按 `field5` 折叠，支持扇形展开和点击组外自动收回。
- 箭头支持上、下、左、右多选组合，枚举为 `1=上、2=下、3=左、4=右`。
- `direction` 支持水平或垂直文字，留空默认水平。
- 链路填充只在点击按钮后重算，不会随页面加载或普通编辑自动运行。
- 支持按 `stationtype` 和备注包含规则配置背景、边框、文字颜色。
- 颜色输入同时提供取色器和 `#RRGGBB` HEX 编码。
- 通过本地服务把页面修改整体保存回 CSV。
- CSV 读取兼容 UTF-8 BOM 和 GB18030，适配 Excel/WPS 另存后的中文编码。

## 仓库结构

```text
cad-wcs-layout/
├─ SKILL.md                         Codex skill 入口和核心约定
├─ README.md                        项目结构和使用说明
├─ agents/
│  └─ openai.yaml                   Codex 展示名称、简介和默认提示词
├─ references/
│  └─ editor-behavior.md            编辑器交互、颜色和服务端详细约定
└─ scripts/
   ├─ extract_devices.py            DXF → 世界坐标中间表
   ├─ generate_layout.py            世界坐标 → WCS 34 列布局 CSV
   ├─ build_html.py                 CSV → 自包含 HTML 编辑器
   ├─ server.py                     本地页面与保存接口
   └─ wcs_schema.py                 字段、中文标签和编辑权限的唯一来源
```

运行时会在脚本所在目录使用或生成以下文件：

```text
*.dxf                   CAD 输入文件
devices_world.csv       DXF 提取后的中间数据
wcs_layout.csv          WCS 布局数据源
wcs_monitor.html        静态构建的页面
station_colors.json     页面保存的颜色配置
```

这些运行数据不需要提交到 skill 仓库。

## 环境要求

- Python 3.10 或更高版本。
- 现代桌面浏览器。
- 脚本仅使用 Python 标准库，无需安装第三方运行依赖。
- Node.js 只用于开发阶段检查生成页面中的 JavaScript，不是运行要求。

## 安装为 Codex Skill

将仓库克隆到 Codex skills 目录：

```powershell
git clone https://github.com/Z11-Eleven/cad-wcs-layout.git "$env:USERPROFILE\.codex\skills\cad-wcs-layout"
```

重新启动 Codex 或开启新任务后，可直接使用类似请求：

```text
使用 $cad-wcs-layout 把这个 DXF 转成 WCS 设备表和可编辑布局页面。
```

```text
使用 $cad-wcs-layout 修改现有 wcs_layout.csv 的画布编辑器。
```

## 快速使用

### 方案一：从 DXF 新建布局

建议把 `scripts` 中的五个 Python 文件复制到独立项目目录，再把一个文本格式 DXF 放在同一目录。`extract_devices.py` 会读取找到的第一个 `*.dxf`。

```powershell
cd D:\path\to\your-layout-project
python extract_devices.py
python generate_layout.py
python build_html.py
python server.py
```

然后访问：

```text
http://127.0.0.1:8734/
```

处理顺序：

1. `extract_devices.py` 流式解析 DXF，生成 `devices_world.csv`。
2. `generate_layout.py` 将毫米坐标换算为格子坐标，生成 `wcs_layout.csv`。
3. `build_html.py` 可选生成静态 `wcs_monitor.html`。
4. `server.py` 动态读取最新 CSV，并提供保存接口。

### 方案二：编辑已有 WCS CSV

把以下文件放在同一目录：

```text
build_html.py
server.py
wcs_schema.py
wcs_layout.csv
```

启动服务：

```powershell
python server.py
```

访问 `http://127.0.0.1:8734/`。服务每次请求页面时都会重新读取 `wcs_layout.csv`，无需先运行 `build_html.py`。

不要使用 `file://` 打开页面，也不要用 `python -m http.server` 代替；这两种方式都没有保存接口。

## 脚本说明

### `extract_devices.py`

- 逐行处理文本 DXF，适合体积较大的图纸。
- 解析 `BLOCKS` 和 `ENTITIES`，还原块嵌套后的世界坐标。
- 提取设备编号、参数文字和箭头锚点，输出 `devices_world.csv`。
- 输入 DXF 和输出 CSV 都位于脚本目录。

适配新图纸时，先检查脚本中的图层、文本类型和设备编号过滤规则。

### `generate_layout.py`

- 读取 `devices_world.csv`。
- 使用 `MM_PER_CELL` 将 CAD 毫米换算为格子坐标，并把 Y 轴转换为画布向下。
- 优先使用附近 CAD 箭头角度确定方向；没有箭头时，根据同行或同列的编号序列推断。
- 输出 `wcs_layout.csv`，字段顺序严格跟随 `wcs_schema.py`。

常用可调参数：

| 参数 | 作用 | 默认值 |
|---|---|---|
| `MM_PER_CELL` | 每格对应的 CAD 毫米数 | `1150.0` |
| `OFFSET_X / OFFSET_Y` | 画布格子偏移 | `0` |
| `GROUP_NAME` | `groupname` 默认值 | `Convery` |
| `ZONE_CODE` | `zonecode` 默认值 | `输送机监控` |
| `STATUS` | 是否在画布显示 | `1` |
| `BELONG` | 线程编号默认值 | `1` |
| `STATION_TYPE` | 站台类型默认值 | `0` |
| `NEAR_RADIUS` | 编号与箭头锚点最大匹配距离 | `8000.0` mm |

### `wcs_schema.py`

集中维护：

- `WCS_FIELDS`：CSV 列名和顺序。
- `FIELD_LABELS`：属性面板中文标签。
- `SINGLE_EDIT_FIELDS`：单选属性面板可编辑字段。
- `BATCH_EDIT_FIELDS`：多选批量修改字段。
- `READONLY_FIELDS`：画布属性面板只读字段。

需要增加或调整字段编辑能力时，优先修改此文件，不要分别硬编码页面表头和面板。

### `build_html.py`

- 读取 `wcs_layout.csv`，兼容 UTF-8 BOM 和 GB18030。
- 把设备数据、字段元数据和颜色配置注入自包含 HTML。
- 实现画布、数据表、属性面板、撤回、重叠展开、多方向箭头和颜色配置。
- 直接运行时生成 `wcs_monitor.html`。

### `server.py`

- 默认监听 `127.0.0.1:8734`，可通过环境变量 `PORT` 修改端口。
- 请求页面时重新加载 `wcs_schema.py` 和 `build_html.py`，确保读取最新代码和 CSV。
- 所有响应带 `Cache-Control: no-store`。
- `POST /save-layout`：校验后以 UTF-8 BOM 整体写回 `wcs_layout.csv`。
- `POST /save-station-colors`：校验并保存 `station_colors.json`。

## WCS 字段约定

CSV 固定为以下 34 列：

```text
itemid,itemname,groupname,objects,datetype,signaltype,value,stationno,remark,
userid,createtime,field1,field2,field3,field4,field5,warehouseid,status,stationtype,
locationx,locationy,width,height,belong,direction,zonecode,areacode,arrowdirection,
zone,workingLocation1,workingLocation2,workingNumber,protocolType,equipmentType
```

关键字段：

| 字段 | 约定 |
|---|---|
| `itemid` | 设备主键，不能为空 |
| `locationx / locationy` | 格子坐标，Y 轴向下 |
| `width / height` | 画布渲染跨度，不是 CAD 物理尺寸 |
| `status` | 只有值 `1` 的设备显示在画布上 |
| `field5` | 层级，值越大越靠上；重叠设备默认显示最大者 |
| `direction` | 1 上、2 下、3 左、4 右；1/2 垂直文字，3/4 水平文字，空值默认水平 |
| `arrowdirection` | 逗号分隔多选：1 上、2 下、3 左、4 右 |

旧 `arrowdirection=5`（左右）会读取为 `3,4`，旧值 `6`（上下）会读取为 `1,2`；新页面不再生成旧双向枚举。

没有真实来源的 WCS 字段应保留为空字符串，不要编造默认数据或增加旁路 CSV 列。

## 页面操作

### 画布工具

- “浏览 / 编辑”切换查看与修改状态。
- 搜索框可按设备 ID、编号或名称定位。
- `+ / -` 调整缩放，支持范围为 0.05～10。
- 鼠标位于画布时滚轮缩放；位于属性栏时滚动属性内容。
- 右键拖动画布进行平移。

### 编辑操作

- 单击选择设备，Ctrl+单击多选，空白处拖动框选。
- 拖动设备按整格移动。
- Del 删除，Esc 清除选择，Ctrl+S 保存。
- “撤回”或 Ctrl+Z 撤回尚未保存的修改，最多 50 步。
- 保存成功后清空撤回历史。
- “重算链路填充”是唯一触发自动宽高链路计算的入口。

### 重叠设备

同坐标设备默认折叠为一个图标，显示 `field5` 最大的设备。右上角红色数量角标可展开成扇形；点击组外区域自动收回。

### 箭头和文字

- 箭头方向使用上、下、左、右四个复选框，可同时选择多个方向。
- 相反方向显示为两条单向箭头，不使用双向箭头枚举。
- 不提供箭头旋转按钮。
- `direction` 可选择上、下、左、右；上/下使用垂直排列，左/右使用水平排列，留空默认水平。

## 颜色配置

页面可配置两类颜色规则：

1. 按 `stationtype` 精确映射。
2. 按 `remark` 包含关键词映射。

备注规则优先于 stationtype。多条备注规则同时命中时，列表中最靠前的一条生效。

`station_colors.json` v2 示例：

```json
{
  "format": "station_colors_v2",
  "colors": {
    "__default__": {
      "fill": "#ccdcf0",
      "border": "#55708c",
      "text": "#1b3350"
    },
    "1": {
      "fill": "#d1fae5",
      "border": "#059669",
      "text": "#065f46"
    }
  },
  "remark_rules": [
    {
      "contains": "人工站台",
      "fill": "#fff1b8",
      "border": "#d48806",
      "text": "#613400"
    }
  ]
}
```

`__default__` 是必需项。颜色必须使用六位 HEX。加载器兼容旧版顶层 stationtype 映射，下一次保存时升级为 v2。

## 保存接口

### 保存布局

```http
POST /save-layout
Content-Type: application/json
```

```json
{
  "format": "wcs_layout_v1",
  "rows": []
}
```

服务端要求 `rows` 为非空数组，每一项必须有非空 `itemid`。

### 保存颜色

```http
POST /save-station-colors
Content-Type: application/json
```

```json
{
  "format": "station_colors_v2",
  "colors": {},
  "remark_rules": []
}
```

## 常见问题

### 页面显示 `ERR_EMPTY_RESPONSE`

检查：

1. 是否使用 `python server.py` 启动。
2. 是否访问 `http://127.0.0.1:8734/`。
3. 8734 端口是否同时存在多个旧 Python 进程。
4. CSV 是否被保存成其他编码。当前读取器支持 UTF-8 BOM 和 GB18030。

### 保存显示 `Failed to fetch`

通常是通过 `file://` 打开页面、服务未启动、端口错误，或请求被旧服务处理。重新启动唯一的 `server.py` 进程后再试。

### 保存提示 CSV 被占用

关闭正在打开 `wcs_layout.csv` 的 Excel/WPS 窗口，再重新保存。

### 页面不是最新数据

确认访问 localhost 服务而不是静态文件，并用 `Ctrl+F5` 强制刷新。服务端页面请求会读取最新 CSV，且禁用浏览器缓存。

## 开发验证

修改脚本后建议执行：

```powershell
python -m py_compile scripts\build_html.py scripts\extract_devices.py scripts\generate_layout.py scripts\server.py scripts\wcs_schema.py
```

在包含测试 CSV 的项目目录生成页面后，可提取其中的 `<script>` 内容并运行：

```powershell
node --check generated-script.js
```

验证保存或 UI 操作时应使用数据副本，避免覆盖用户正在使用的 `wcs_layout.csv`。
