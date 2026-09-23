# 原型到页面的交接依据

用一个文件将内容、画布和实现对齐。继续使用项目已有格式即可，不强制 JSON。稳定 ID 用于定位，不自动显示在前台。

## 页面层

- 名称、角色、语言、主要转化及目的地。
- 当前版本：画布区域/链接、修订日期、用户最新决定；区分历史参考。
- 模块顺序、共享内容、必要状态、待定项。

## 模块层示例

这是交接结构示例，实际交付填入项目的完整文案与来源，不保留示例提示句：

```json
{
  "id": "home-workflow",
  "question": "现有工作流能减少哪些交接？",
  "purpose": "说明流程连续性",
  "copy": {
    "heading": "Keep the workflow. Bring the steps together.",
    "body": "经资料核实后，写入本项目实际的一句话说明。",
    "cta": null
  },
  "layout": {
    "pattern": "before-after-flow",
    "alignment": "content-left",
    "desktop": "两条可对照路径；右侧真实产品画面中呈现动作",
    "mobile": "Before 在上、Now 在下，各自保留顺序与终点"
  },
  "media": {
    "role": "证明动作发生在同一设备上",
    "asset": null,
    "status": "needed",
    "ratio": "16:9",
    "safe_area": "文字放画面外，不挡屏幕",
    "fallback": "真实操作静帧"
  },
  "claims": [],
  "states": [],
  "status": "draft"
}
```

`claims` 每项记 `claim / source / model-or-scope / condition / verification-status`，只为有事实意义的内容记录。状态记 `trigger / default / changed-copy / changed-media / destination / close-or-return`。目的地未知就标待配置，不能造有效地址。

## 实现后的闭环

前端可依据真实画面调细节，但保留用户确认的定位、事实与转化。新增/删除/重排模块、改变含义或素材逻辑时，更新清单并记录画布是否同步。圆角、字距等通常不必回写黑白原型。

交接不强制再开确认轮次；已有授权足够就继续。只对会实质改变结果的未知事实、目的地或范围询问。
