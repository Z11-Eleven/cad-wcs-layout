# WCS 布局编辑器约定

## 画布与编辑

- `CELL=40`，缩放范围 0.05～10。
- 搜索框按设备 ID、编号或名称定位。
- 浏览与编辑模式分开；编辑模式支持单选、Ctrl 多选、框选、整格拖动、添加、删除和批量修改。
- 未保存修改支持按钮和 `Ctrl+Z` 撤回，默认上限 50 步。
- 属性面板使用独立滚动区域，鼠标在面板内时滚轮不能触发画布缩放。
- 保存布局调用 `POST /save-layout`，整体回写 CSV；文件被 Excel/WPS 占用时返回 409。

## 链路填充

`autoFill()` 只绑定“重算链路填充”按钮。相邻同排或同列设备间隔 1～`CHAIN_MAX` 时计算跨度，横向优先，结果写回 `width/height`。不要在页面初始化、普通编辑、拖动或保存前隐式调用。

## 坐标重叠

- 同坐标设备折叠时显示 `field5` 最大的设备名称。
- 右上角数量角标为 15px；点击后设备呈扇形排列。
- 点击展开组之外自动收回，中心按钮也可收回。

## 文字与箭头

- `direction` 与箭头统一为 1 上、2 下、3 左、4 右；1/2 垂直，3/4 水平，空值默认水平。
- `arrowdirection` 保存为排序后的逗号字符串，固定定义为 1 上、2 下、3 左、4 右，可多选。
- 旧 5（左右）映射到 3+4，旧 6（上下）映射到 1+2；保存后使用新格式。
- UI 使用上、下、左、右复选框，不显示旧双向选项或旋转按钮。

## 颜色配置

`station_colors.json` 使用 v2：

```json
{
  "format": "station_colors_v2",
  "colors": {
    "__default__": {"fill": "#ccdcf0", "border": "#55708c", "text": "#1b3350"}
  },
  "remark_rules": [
    {"contains": "关键词", "fill": "#fff1b8", "border": "#d48806", "text": "#613400"}
  ]
}
```

- `colors` 按 stationtype 匹配，必须包含 `__default__`。
- `remark_rules` 按数组顺序用 JavaScript `includes` 做包含匹配；第一条命中生效，并优先于 stationtype。
- 规则可添加、删除、上移、下移，并实时预览。
- 三类颜色都显示取色控件和 `#RRGGBB` HEX 文本框，二者双向同步；服务端验证六位 HEX 并转为小写保存。
- 加载器兼容旧版顶层 stationtype 映射，保存时升级为 v2。
- 保存配置调用 `POST /save-station-colors`，格式名为 `station_colors_v2`。

## 服务端

- `GET /wcs_monitor.html` 每次重载 schema 和构建模块，读取最新 CSV，响应 `Cache-Control: no-store`。
- 8734 端口存在多个 Python 监听进程时会出现随机旧页面或旧接口。重启时先清理所有该端口监听者，再只启动一个进程。
- `Failed to fetch` 通常表示用 `file://` 打开、服务未启动、端口错误或请求被旧服务处理。
- CSV 读取先尝试 `utf-8-sig`，失败后回退到 `gb18030`，以兼容 Excel/WPS 改变文件编码；否则 GET 会抛出 `UnicodeDecodeError`，浏览器显示 `ERR_EMPTY_RESPONSE`。
