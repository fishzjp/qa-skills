# BUG-2077：批量导入优惠券失败行的行号提示错位一行 根因分析

## 1. 根因定位
- **位置**：`coupon-import` 模块 `importer.py` 第 31 行
- **根因**：在 `except ValidationError as e:` 分支中，使用了 `line_no = reader.line_num + 1` 获取错误行号。Python 的 `csv.DictReader` 的 `line_num` 属性表示当前读取到的文件物理行号（从 1 开始计数，包含表头行）。当处理数据行（例如文件第 3 行数据）发生异常时，此时的 `reader.line_num` 已经是 3。代码在此基础额外 `+ 1`，导致行号计算结果为 4，比 CSV 实际物理行号偏移了 +1。
- **对比**：第 35 行的 `except Exception as e:` 分支中使用 `line_no = reader.line_num`，此处理逻辑是正确的。

## 2. 影响范围分析
- **功能影响**：影响后台批量导入优惠券（`import_coupons`）功能。当 CSV 中的某行数据触发 `ValidationError`（如面额超限、门槛低于面额等）时，返回给前端的错误行号均比 CSV 实际物理行号大 1。
- **用户体验影响**：不阻断导入流程，但会导致管理员根据错误提示去 CSV 文件中定位问题时看错行，特别是在行数较多的 CSV 文件中，增加排障成本和心智负担。
- **波及范围**：仅限 `ValidationError` 异常分支；`Exception` 异常分支不受影响；已成功导入的数据不受影响。

## 3. 修复建议
在 `importer.py` 第 31 行，去除 `+ 1` 的计算，使其与普通异常处理逻辑保持一致。
修改前：
```python
line_no = reader.line_num + 1       # L31: line_num 已含表头行，再 +1 多算一行
```
修改后：
```python
line_no = reader.line_num
```

## 4. 回归建议
1. **单元测试**：针对 `import_coupons` 方法补充单元测试，构造包含表头、合法数据、触发 `ValidationError` 数据、合法数据的 CSV 字节流，断言返回的失败行号与 CSV 实际物理行号完全一致。
2. **边界用例覆盖**：
   - 首行数据（CSV 第 2 行）触发 `ValidationError` 的情况。
   - 连续多行触发 `ValidationError` 的情况。
   - 触发其他 `Exception` 的情况（验证普通异常分支行号计算未被破坏）。
   - 构造包含空行或非法 CSV 格式的文件进行导入验证（视 `csv.DictReader` 行号变化而定）。
3. **端到端验证**：在测试环境 staging-2，使用 Chrome 120 按照复现步骤上传 CSV，验证提示信息变为“成功 2 条，失败 1 条：第 3 行：面额需为 1-1000”。
4. **日志核查**：检查 `importer` 相关的日志输出或前端展示，确保错误行号信息一致。

## 待澄清清单
1. 除了 `ValidationError` 和普通 `Exception` 外，是否存在其他特定异常类需要单独处理行号？
2. 前端展示错误提示时是否对行号有额外处理或偏移？（根据材料推测没有，但代码上下文未包含前端逻辑）
3. 若 CSV 包含空行，`csv.DictReader` 的 `line_num` 增量是否会导致行号跳动，是否需要针对空行做特殊处理？