### BUG-2077: 批量导入优惠券失败行号提示错位 +1

- **严重程度**: P2
- **现象**: 管理后台批量导入优惠券 CSV，校验失败的行在错误提示中行号总比实际行号大 1（如第 3 行面额超限，提示"第 4 行"）。
- **复现步骤**:
  1. 准备 CSV：第 1 行表头，第 2 行合法数据，第 3 行面额=5000（非法），第 4 行合法数据
  2. 后台 → 券工场 → 批量导入，上传该文件
  3. 导入结果提示"成功 2 条，失败 1 条：第 4 行：面额需为 1-1000"（预期应为"第 3 行"）
  - 确定性复现；环境 staging-2，Chrome 120
- **Root Cause**: `importer.py:31` 计算 `line_no = reader.line_num + 1`。`csv.DictReader.line_num` 返回的是**已从源迭代器读取的总行数（含表头）**，本身已正确反映 CSV 物理行号。读表头后 `line_num=1`，读第一条数据行（CSV 第 2 行）后 `line_num=2`，读第二条数据行（CSV 第 3 行）后 `line_num=3`。此处再 `+ 1` 导致 `ValidationError` 分支的行号恒比实际大 1。对比 L33 的 `except Exception` 分支使用 `reader.line_num`（不加 1），行号正确——两个异常分支不一致证实了 `+ 1` 是多余操作。**Status: Verified**（E3：Bug 报告已复现确认；E2：`importer.py:31` 代码行明确）。
- **Evidence**:
  - E3（运行证据）：Bug 报告复现结果——CSV 第 3 行面额=5000 触发 `ValidationError("面额需为 1-1000")`，提示"第 4 行"
  - E2（代码证据）：`importer.py:31` `line_no = reader.line_num + 1`——`reader.line_num` 已含表头计数，`+ 1` 多算一行
  - E2（代码证据）：`importer.py:33` `except Exception` 分支 `line_no = reader.line_num`——无 `+ 1`，行号正确，佐证 L31 的 `+ 1` 为错误
- **影响范围**:
  - **功能面**：仅 `ValidationError` 分支（L31）受影响——`validate_coupon` 抛出的所有校验错误（面额超限、使用门槛低于面额）的行号均错位 +1；`except Exception` 分支（L33，含 `parse_coupon` 的 `ValueError`/`KeyError`、`save_coupon` 的 `IntegrityError` 等）行号正确，不受影响。来源：`importer.py:31` vs `importer.py:33` 对比。
  - **数据面**：无脏数据产生。错误仅出现在返回给前端的提示信息中，不影响实际入库数据的正确性（校验失败的行未执行 `save_coupon`）。来源：`importer.py:29` 校验通过才调用 `save_coupon`。
  - **用户面**：所有使用后台批量导入优惠券功能的管理员用户，在导入文件含校验失败行时均会看到误导性行号，增加排查成本。来源：Bug 报告复现步骤 2。
- **Severity 依据**: 体验问题——功能正常运作（导入不阻断、数据不入错），仅错误提示的行号信息不准确，误导排查方向。对应 P2。
- **修复建议**:
  - 将 `importer.py:31` 的 `reader.line_num + 1` 改为 `reader.line_num`，与 L33 的 `except Exception` 分支保持一致。
  - 建议抽取 `line_no = reader.line_num` 到 `try` 块内、两个 `except` 之前，消除两个分支行号取值不一致的隐患（当前 L31 与 L33 各自独立取值，后续维护易再出偏差）。
- **回归建议**:
  - **直接复现用例**（建议新增 TC-IMP-015）：CSV 第 3 行触发 `ValidationError`（面额超限），断言错误提示行号 = 3。当前无对应用例，需新增。
  - **关联回归用例**（建议新增 TC-IMP-016）：CSV 第一条数据行（第 2 行）即触发 `ValidationError`，验证首行边界行号正确（不应为 1 或 3）。
  - **关联回归用例**（建议新增 TC-IMP-017）：CSV 同时含 `ValidationError` 行和 `Exception` 行（如某行缺字段触发 `KeyError`），验证两类错误的行号均正确且一致。
  - **锚点回归**：批量导入全成功（无失败行）、批量导入全失败两条以上（多行行号逐行验证）的既有场景应纳入回归。
  - 回归**范围选择**移交 `regression-testing`。