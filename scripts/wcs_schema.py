"""WCS device table (expdata) field definitions shared by the pipeline.

WCS_FIELDS matches the column order of the expdata sheet in
WCS device sample data.xls, so it maps 1:1 onto the WCS device table.
Fields with no CAD data source are emitted as empty strings.

The three edit lists below drive the preview editor:
  SINGLE_EDIT_FIELDS -> editable in the map view property panel (single selection)
  BATCH_EDIT_FIELDS  -> editable in the map view batch panel (marquee / Ctrl multi-select)
  READONLY_FIELDS    -> displayed but not editable in the map view panels
The data table view stays fully editable regardless of these lists.
"""

WCS_FIELDS = [
    "itemid", "itemname", "groupname", "objects", "datetype", "signaltype",
    "value", "stationno", "remark", "userid", "createtime",
    "field1", "field2", "field3", "field4", "field5",
    "warehouseid", "status", "stationtype",
    "locationx", "locationy", "width", "height", "belong",
    "direction", "zonecode", "areacode", "arrowdirection", "zone",
    "workingLocation1", "workingLocation2", "workingNumber",
    "protocolType", "equipmentType",
]

# 中文名(用于预览图属性面板与批量面板的标签)
FIELD_LABELS = {
    "itemid": "设备ID", "itemname": "设备名称", "groupname": "设备分组",
    "objects": "DB地址", "datetype": "扫码器类型", "signaltype": "数据长度",
    "value": "DB偏移量", "stationno": "设备编号", "remark": "备注",
    "userid": "PLC IP地址", "createtime": "创建时间",
    "field1": "线程组别", "field2": "所属PLC", "field3": "扫码功能类型",
    "field4": "暂存备用", "field5": "层级顺序",
    "warehouseid": "仓库ID", "status": "启用状态", "stationtype": "站台类型",
    "locationx": "X坐标", "locationy": "Y坐标",
    "width": "图标宽", "height": "图标长", "belong": "线程编号",
    "direction": "方向(文字排列)", "zonecode": "画布区域编号",
    "areacode": "拉线区域编号", "arrowdirection": "箭头方向", "zone": "库区编号",
    "workingLocation1": "双叉叉1站台号", "workingLocation2": "双叉叉2站台号",
    "workingNumber": "双叉货叉编号", "protocolType": "协议类型",
    "equipmentType": "设备类型",
}

# 可单选编辑(itemid 主键不可重复;itemname/stationno 默认取设备 id)
SINGLE_EDIT_FIELDS = [
    "itemid", "itemname", "groupname", "objects", "datetype", "signaltype",
    "value", "stationno", "remark", "userid",
    "field1", "field2", "field3", "field4", "field5",
    "status", "stationtype",
    "locationx", "locationy", "width", "height", "belong",
    "direction",
    "zonecode", "areacode", "arrowdirection", "zone",
    "workingLocation1", "workingLocation2", "workingNumber",
    "protocolType", "equipmentType",
]

# 可批量编辑(框选/多选后统一改)
BATCH_EDIT_FIELDS = [
    "groupname", "datetype", "userid",
    "field1", "field2", "field4",
    "status", "stationtype",
    "locationx", "locationy", "width", "height", "belong",
    "direction",
    "zonecode", "areacode", "arrowdirection", "zone",
    "protocolType", "equipmentType",
]

# 无编辑能力:只在属性面板里只读展示
READONLY_FIELDS = [f for f in WCS_FIELDS if f not in SINGLE_EDIT_FIELDS]

# Non-WCS keys carried on internal rows only (never written to CSV).
HELPER_FIELDS = ["renderwidth", "renderheight", "direction_source", "x_mm", "y_mm"]


def blank_row():
    """One row skeleton: every WCS column present, unfilled ones left empty."""
    row = {k: "" for k in WCS_FIELDS}
    row.update({"renderwidth": 1, "renderheight": 1,
                "direction_source": "", "x_mm": "", "y_mm": ""})
    return row
