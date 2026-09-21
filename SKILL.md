---
name: cad-wcs-layout
description: Convert a CAD layout drawing (DXF) into a WCS expdata-shaped CSV and an editable HTML grid monitor, or maintain an existing WCS layout editor with CRUD, search, undo, overlap handling, manual chain fill, multi-direction arrows, text direction, and configurable station colors. Use for CAD-to-WCS layout mapping and this editor pattern; not for general CAD viewing or 3D work.
---

# CAD → WCS 布局映射

将 CAD 设备标签转换成 WCS `expdata` 34 列 CSV，并生成可通过本地服务编辑和保存的 HTML 画布。优先复用 `scripts/` 中已验证的实现；适配项目时修改集中常量和字段定义，不要重新发明解析或编辑逻辑。

## 核心数据约定

字段顺序由 `scripts/wcs_schema.py` 的 `WCS_FIELDS` 唯一定义；中文标签和单选、批量、只读范围也在该文件维护。缺少真实来源的字段留空，不添加 `renderwidth`、`renderheight`、`x_mm`、`y_mm` 等旁路列。

- `locationx/locationy` 是格子坐标，Y 轴向下。
- `width/height` 是渲染跨度。
- `status=1` 的设备才显示。
- `field5` 越大层级越高，同坐标折叠时也用它选默认代表。
- `direction` 与箭头统一为 1 上、2 下、3 左、4 右，并控制文字轴向：1/2 垂直，3/4 水平；空值默认水平且必须保留为合法选项。
- `arrowdirection` 为逗号分隔多选值：1 上、2 下、3 左、4 右。旧 5/6 仅兼容读取为 `3,4`/`1,2`，不再生成双向枚举。

## 工作流

1. `extract_devices.py` 流式解析大型文本 DXF，输出 `devices_world.csv`。
2. `generate_layout.py` 将毫米坐标换算为格子坐标，按 WCS 34 列输出 `wcs_layout.csv`。
3. `build_html.py` 生成 `wcs_monitor.html`；`server.py` 也会按每次请求动态渲染。
4. 用 `python server.py` 启动 `127.0.0.1:8734`。不要用 `file://` 或普通静态服务器测试保存。

编辑已有 WCS CSV 时可跳过 DXF 两步。重新生成 CSV 属于覆盖当前编辑结果的操作，执行前确认用户意图。

## 编辑器不变量

- 链路填充只能由用户点击按钮触发，页面加载、编辑、拖动和保存不得自动重算。
- 链路算法的邻居图包含所有设备，只对允许重算的设备写入结果，保持保存和重载幂等。
- 箭头使用四个复选框多选；相反方向绘制成两条单向箭头；不提供旋转按钮。
- 未保存修改进入最多 50 步撤回栈，保存成功后清空。
- 属性面板悬浮时滚轮滚动面板，画布悬浮时滚轮缩放。
- 同坐标设备以扇形展开，点击组外自动收回，折叠角标保持紧凑。
- 页面 GET 时重载 `wcs_schema` 与 `build_html`，并禁用缓存；启动或重启前确保端口没有多个服务进程。

颜色、重叠、缩放、搜索、保存接口和 UI 的详细约定见 [references/editor-behavior.md](references/editor-behavior.md)。修改编辑器时只读取该参考文件，不需要在单纯 DXF 提取任务中加载。

## 验证

- 对变更过的 Python 文件执行 `py_compile`。
- 生成一次 HTML，并对内嵌 JavaScript 执行 `node --check`。
- 动态页面和保存接口必须从 `127.0.0.1:8734` 验证。
- UI 验证不得写坏用户 CSV；优先只读检查，涉及保存时使用副本或等价配置回写。
- 确认 CSV 行数和 34 列结构未意外变化。
