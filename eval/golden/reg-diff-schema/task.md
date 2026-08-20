# 任务：根据代码变更选择回归范围

你是测试工程师。请根据下方的代码 diff 与用例 Schema（含追溯映射），产出回归清单：必须回归（P0）/ 建议回归（P1）/ 可选回归（P2）三级，每条给依据；对不受影响的模块显式排除。直接输出回归清单文件（Markdown）。

---

## 输入材料

### 材料 1：代码变更（feature/coupon-fee，即将合并至 main）

```diff
diff --git a/coupon/service.py b/coupon/service.py
@@ -120,9 +120,14 @@ def create_coupon(data):
     validate_coupon(data)
-    coupon = Coupon.create(**data)
+    # 手续费需求：创建时按面额档位记手续费
+    fee = calc_fee(data["amount"])          # 新增：1-100 → 0.5 元；101-500 → 2 元；>500 → 5 元
+    coupon = Coupon.create(fee=fee, **data)
     notify("coupon_created", coupon.id)
     return coupon

diff --git a/common/validator.py b/common/validator.py
@@ -18,6 +18,9 @@ def validate_amount(amount):
     if not isinstance(amount, int):
         raise ValidationError("面额需为整数")
+    if amount > 500:
+        raise ValidationError("面额上限 500")   # 新增：风控要求面额上限 1000 → 500
```

变更说明：① 新增创建手续费（按面额档位）；② 面额上限从 1000 收紧到 500（validator 为全局公共校验器，被创建/编辑/批量导入共用）。

### 材料 2：测试用例 Schema（测试用例.schema.yaml，节选）

```yaml
test_cases:
  - {id: TC-01-01, title: 正常创建优惠券, module: 创建, priority: P0, type: functional, risk_ref: R1, code_refs: ["coupon/service.py:122"], automation: {supported: yes, framework: playwright}}
  - {id: TC-01-02, title: 面额边界校验, module: 创建, priority: P2, type: boundary, risk_ref: R2, code_refs: ["common/validator.py:18", "coupon/service.py:121"]}
  - {id: TC-01-03, title: 门槛低于面额拦截, module: 创建, priority: P1, type: boundary, risk_ref: R2, code_refs: ["coupon/service.py:118"]}
  - {id: TC-02-01, title: 编辑调整发放总量, module: 编辑, priority: P1, type: functional, risk_ref: null, code_refs: ["coupon/edit.py:40"]}
  - {id: TC-02-02, title: 编辑路径面额校验一致, module: 编辑, priority: P1, type: regression, risk_ref: R2, code_refs: ["common/validator.py:18", "coupon/edit.py:44"]}
  - {id: TC-03-01, title: 批量导入标准文件, module: 导入, priority: P0, type: functional, risk_ref: null, code_refs: ["coupon/importer.py:30"]}
  - {id: TC-03-02, title: 批量导入面额非法行拦截, module: 导入, priority: P1, type: boundary, risk_ref: R2, code_refs: ["common/validator.py:18", "coupon/importer.py:33"]}
  - {id: TC-04-01, title: 发布优惠券, module: 发布, priority: P0, type: functional, risk_ref: R1, code_refs: ["coupon/publish.py:20"]}
  - {id: TC-04-02, title: 到期自动结束, module: 发布, priority: P1, type: state, risk_ref: R3, code_refs: ["coupon/scheduler.py:88"]}
  - {id: TC-05-01, title: 用户领取优惠券, module: 领取, priority: P0, type: functional, risk_ref: R1, code_refs: ["coupon/claim.py:52"]}

risk_map:
  - {id: R1, feature: 优惠券生命周期, dimension: 数据一致性, level: High, anchors: [TC-01-01, TC-04-01, TC-05-01]}
  - {id: R2, feature: 面额校验, dimension: 边界, level: High, anchors: [TC-01-02, TC-01-03, TC-02-02, TC-03-02]}
  - {id: R3, feature: 到期调度, dimension: 状态流转, level: Medium, anchors: [TC-04-02]}
```
