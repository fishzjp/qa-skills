### BUG-2077: 批量导入优惠券失败行的行号提示错位一行

- **严重程度**: P2
- **现象**: 管理后台批量导入优惠券 CSV，校验失败行的错误提示行号比实际行号大 1。
- **复现步骤**:
  1. 准备 CSV：第 1 行表头，第 2 行合法数据（面额=100），第 3 行面额=5000（非法），第 4 行合法数据
  2. 后台 → 券工场 → 批量导入，上传该文件
  3. 导入结果提示"成功 2 条，失败 1 条：第 4 行：面额需为 1-1000"（预期提示"第 3 行"）
  4. 环境：staging-2，Chrome 120
- **Root Cause**: `importer.py` L31 计算 ValidationError 行号时执行 `line_no = reader.line_num + 1`。`csv.DictReader.line_num` 本身已是包含表头行在内的 1-based 行号（处理 CSV 第 3 行数据时 `line_num=3`），额外 `+1` 导致行号偏大 1。Status: Verified（Bug 报告复现结果 E3 与代码行 E2 交叉印证，行号偏移量与 `+1` 完全吻合）。
- **Evidence**:
  - E3（运行证据）：Bug 报告复现——CSV 第 3 行面额超限，实际提示"第 4 行"，偏移量恰好 +1
  - E2（代码证据）：`importer.py:31` → `line_no = reader.line_num + 1`；对照 L34 的 Exception 分支使用 `line_no = reader.line_num`（无 `+1`），两分支行号计算逻辑不一致
- **影响范围**:
  - **功能面**：所有 `ValidationError` 类校验失败的行号提示均偏大 1——面额超限（`importer.py:31` 调用栈 ← `validate_coupon` 面额校验）、使用门槛低于面额（同调用栈 ← `validate_coupon` 门槛校验）；`Exception` 分支（L34）使用 `reader.line_num` 不受影响，行号正确但与 ValidationError 分支逻辑不一致（来源：`importer.py:31` vs `importer.py:34`）
  - **数据面**：无脏数据、无数据丢失——错误仅发生在提示信息层，`save_coupon` 仅在校验通过后执行（来源：`importer.py:27` try 块顺序 parse → validate → save）
  - **用户面**：所有使用后台"券工场 → 批量导入"功能的管理员（来源：Bug 报告复现路径）
- **Severity 依据**: 导入流程不阻断（成功行正常入库），不影响数据正确性；但错误行号误导运营人员定位问题行，属体验问题 → P2
- **修复建议**: 将 `importer.py:31` 的 `reader.line_num + 1` 改为 `reader.line_num`，使 ValidationError 分支与 L34 Exception 分支行号计算逻辑统一。无需调整其他逻辑。
- **回归建议**:
  - **修复验证**（直接复现 Bug 的场景）：
    - TC-IMP-021（建议新增）：CSV 中间行面额超限 → 验证提示行号 = 实际行号
    - TC-IMP-022（建议新增）：CSV 中间行使用门槛低于面额 → 验证提示行号 = 实际行号
  - **关联回归**（同根因模式 + 锚点场景）：
    - 首行数据（CSV 第 2 行）校验失败 → 验证提示"第 2 行"（边界）
    - 末行数据校验失败 → 验证提示行号正确（边界）
    - 连续多行校验失败 → 逐行验证行号正确
    - 系统错误（Exception 分支，L34）行号 → 验证未被修复引入回归
    - 全部行合法 → 验证成功计数与提示正常（锚点）
  - 回归范围选择移交 `regression-testing`

---

### 待澄清

1. `save_coupon` 抛出 `IntegrityError`（名称唯一性冲突，`validate_coupon` 注释提及）时走 `except Exception` 分支（L33），该路径行号当前正确（`reader.line_num` 无 `+1`）。修复 L31 后需确认该路径不受影响——若后续将 `IntegrityError` 单独捕获并归入 ValidationError 分支，需同步确认行号计算。
2. 是否存在其他模块复用了相同的 `reader.line_num + 1` 模式（本 skill 仅审查了 `importer.py`，建议 `regression-testing` 阶段对仓库内 `csv.DictReader` / `line_num` 做 grep 扫描）。