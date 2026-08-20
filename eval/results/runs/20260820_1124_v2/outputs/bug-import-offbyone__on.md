### BUG-2077: 批量导入优惠券失败行的行号提示错位一行

- **严重程度**: P2
- **现象**: 管理后台批量导入优惠券 CSV，当存在校验失败的行时，错误提示中的行号总比实际行号大 1（例：CSV 第 3 行面额超限，提示"第 4 行：面额需为 1-1000"）
- **复现步骤**:
  1. 准备 CSV：第 1 行表头，第 2 行合法数据，第 3 行面额=5000（非法），第 4 行合法数据
  2. 后台 → 券工场 → 批量导入，上传该文件
  3. 导入结果提示"成功 2 条，失败 1 条：第 4 行：面额需为 1-1000"
  - 环境：staging-2，Chrome 120
  - 确定性复现，非概率性
- **Root Cause**: `importer.py` L31 `line_no = reader.line_num + 1` 对行号多加 1。Python `csv.DictReader.line_num` 在迭代到 CSV 第 N 行数据时值已为 N（表头占第 1 行，迭代器内部读取表头后 `line_num=1`，读取第一条数据后 `line_num=2`，以此类推）。L31 额外 `+1` 导致所有 `ValidationError` 路径行号偏移 +1。同一函数通用异常分支 L35 `line_no = reader.line_num` 未加 1，两处不一致佐证 L31 为误加。 [Verified]
- **Evidence**:
  - E3 运行证据：复现结果提示"第 4 行：面额需为 1-1000"，实际非法数据位于 CSV 第 3 行（Bug 报告复现步骤 3）
  - E2 代码证据：`importer.py:31` — `line_no = reader.line_num + 1`；对照 `importer.py:35` — `line_no = reader.line_num`（通用异常分支无 +1，行为正确）
- **影响范围**:
  - **功能面**：所有通过 `import_coupons()` 执行的 CSV 导入，当数据行触发 `ValidationError`（面额超限 `validate_coupon` L43 / 门槛低于面额 L45）时，错误提示行号均偏移 +1。同一函数 `Exception` 分支（`importer.py:33-35`）行号正确，不受影响。[来源：`importer.py:31` vs `importer.py:35` 代码对比]
  - **数据面**：无脏数据影响，行号仅写入 `results` 列表的提示文本，不涉及 `save_coupon` 数据写入路径。[来源：`importer.py:31` 仅操作 `results` 列表；`save_coupon` 在 L28 校验通过后才调用]
  - **用户面**：所有使用后台"券工场 → 批量导入"功能的操作人员，排查导入失败行时被错误行号误导，需手动减 1 定位。[来源：Bug 报告复现步骤 2]
- **Severity 依据**: 不阻断导入流程（成功行正常入库），仅错误提示行号偏移 +1 误导排查方向，属体验问题 → P2
- **修复建议**: 将 `importer.py:31` `line_no = reader.line_num + 1` 改为 `line_no = reader.line_num`，与 L35 通用异常分支保持一致。修复后确认 `csv.DictReader` 在含空行或多行记录场景下 `line_num` 语义无回归。
- **回归建议**:
  - 修复验证用例（建议新增 TC-COUPON-IMPORT-ROWNUM-001）：上传"第 1 行表头 + 第 2 行合法 + 第 3 行面额超限 + 第 4 行合法"CSV，验证提示行号为"第 3 行"
  - 关联回归场景：
    - 第一行数据即校验失败（边界：行号=2，验证 +1 后不误报为 3）
    - 最后一行数据校验失败（边界）
    - 连续多行校验失败，逐行验证行号正确
    - 非法行触发 `Exception` 路径（如 `parse_coupon` 中 `int(row["面额"])` 对非数字值抛 `ValueError`），验证 L35 分支行号仍正确无回归
    - 批量导入功能锚点用例：全合法数据导入、混合合法/非法导入汇总计数
  - 回归范围选择移交 `regression-testing`