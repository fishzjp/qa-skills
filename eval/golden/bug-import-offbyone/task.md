# 任务：定位优惠券批量导入 Bug 的根因

你是测试工程师。以下 Bug 已确认为缺陷，请完成根因分析：定位根因（到具体代码行）、影响范围分析、修复建议与回归建议。直接输出 Bug 分析条目（Markdown）。

---

## 输入材料

### 材料 1：Bug 报告

**BUG-2077：批量导入优惠券失败行的行号提示错位一行**

- 现象：管理后台批量导入优惠券 CSV，当存在校验失败的行时，错误提示中的行号总比实际行号大 1（例：CSV 第 3 行面额超限，提示"第 4 行：面额需为 1-1000"）
- 复现步骤：
  1. 准备 CSV：第 1 行表头，第 2 行合法数据，第 3 行面额=5000（非法），第 4 行合法数据
  2. 后台 → 券工场 → 批量导入，上传该文件
  3. 导入结果提示"成功 2 条，失败 1 条：第 4 行：面额需为 1-1000"
- 预期：提示"第 3 行"
- 实际：提示"第 4 行"
- 环境：测试环境 staging-2，Chrome 120
- 严重程度：P2（不阻断导入，但误导排查）

### 材料 2：相关代码（coupon-import 模块，commit a1b2c3d）

```python
# importer.py
def import_coupons(csv_file):
    """批量导入优惠券。返回 (成功条数, [(行号, 错误信息), ...])"""
    reader = csv.DictReader(csv_file)
    results = []
    for row in reader:                          # L24: 逐行读取，row 不含行号
        try:
            coupon = parse_coupon(row)
            validate_coupon(coupon)
            save_coupon(coupon)
            results.append(("ok", None, None))
        except ValidationError as e:
            line_no = reader.line_num + 1       # L31: line_num 已含表头行，再 +1 多算一行
            results.append(("fail", line_no, str(e)))
        except Exception as e:
            logging.exception("import error")
            line_no = reader.line_num
            results.append(("fail", line_no, f"系统错误: {e}"))
    ok = sum(1 for r in results if r[0] == "ok")
    return ok, [(r[1], r[2]) for r in results if r[0] == "fail"]


def parse_coupon(row):
    """CSV 行 → 优惠券对象"""
    return {
        "name": row["券名称"].strip(),
        "amount": int(row["面额"]),
        "threshold": int(row.get("使用门槛", 0) or 0),
        "total": int(row["发放总量"]),
    }


def validate_coupon(c):
    if not (1 <= c["amount"] <= 1000):
        raise ValidationError("面额需为 1-1000")
    if c["threshold"] != 0 and c["threshold"] < c["amount"]:
        raise ValidationError("使用门槛不能低于面额")
    # 名称唯一性由数据库唯一索引保证，冲突时抛 IntegrityError
```
