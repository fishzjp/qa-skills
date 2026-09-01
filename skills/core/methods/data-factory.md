# 测试数据工厂（data-factory）

> 自动化测试（UI / API）的执行层造数工程模式（用例设计层的参数化方法见 `data-driven.md`，
> 两者分工：data-driven 决定"测哪些数据组合"，本文件决定"执行时数据怎么造、怎么清"）。
> 承接两处纪律：api-testing"自建自清理"、automated-e2e-testing"每条 test 独立"。

## 1. 构造器模式（makeX + overrides）

每类业务实体写一个构造函数，默认值收拢一处，用例只声明差异：

```typescript
// tests/factories/project.ts —— 默认值集中，测试只覆盖关心的字段
const baseProject = { type: 'normal', quota: 100, status: 'draft' };
export function makeProject(overrides: Partial<typeof baseProject> = {}) {
  const name = overrides.name ?? `auto-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`;
  return { ...baseProject, ...overrides, name };
}
// 用例里：makeProject({ quota: 0 })——意图即文档，默认值变更不牵连全库用例
```

```python
# api-tests/factories/coupon.py —— 同构 Python 形态
def make_coupon(**overrides):
    base = {"type": "normal", "quota": 100, "status": "draft"}
    base.update(overrides)
    base.setdefault("name", f"auto-{int(time.time()*1000)}")
    return base
```

- **默认值必须合规**：逐字段核对材料约束（maxLength / 枚举 / 格式 / 跨字段规则）——
  api-testing 的"模板总长 ≤ 约束上限 −2"在本层统一执行，构造器是唯一出口，用例不得散写裸数据
- **唯一性在构造器内保证**：唯一字段（名称/编号）由构造器生成，不靠用例自觉

## 2. 造数通道三选一

| 通道 | 适用 | 失效条件 / 约束 |
|---|---|---|
| **API 造数**（默认） | 被测系统有可用接口、鉴权可自动化 | 接口参数受限造不出的形态（如不可通过 API 设置的内部状态）→ 降 DB |
| **DB 快照 / fixture** | 大前置数据（存量记录、复杂关联）、只读场景、API 造不出的状态 | 快照含易变字段（时间戳/序列）要声明；写库绕过业务校验，可能造出业务上非法的状态——仅用于"存量脏数据"类被测场景 |
| **UI 造数** | 被测的就是录入流程本身；或无 API 可用 | 最慢最脆，仅此两情形可用；能 API 化的前置一律 API 化 |

选择原则：**前置造数永远选最快最稳的通道，被测行为才走最真实的通道**。前置用 UI 走完整表单 = 给失败率和时长上税。

## 3. 按执行隔离与清理

- **前缀 = 用例编号**（如 `TC-01-03-`）：动态数据统一 `TC编号-语义-随机段` 命名——
  失败后可按前缀识别归属，也支持会话尾批量扫尾
- **清理三道防线**：① `afterEach` 精确清理（api-testing/automated-e2e-testing 既有纪律）；
  ② 清理失败 `.catch()` 记 warning 不阻塞下条（噪音不吞错）；③ 会话尾按前缀批量扫尾
  （列表接口/API 按前缀过滤删除）——兜住 ① 漏网的
- **断言隔离**：查询/列表类断言永远先造自己的数据再断言其上，不假设库里有（或没有）
  任何存量数据——存量不确定性是 flaky 的最大来源之一

## 4. 与既有纪律的衔接

- api-testing"测试数据自建自清理（setup 创建 / teardown 删除）"→ 本文件第 1/3 节是其工程化落地
- automated-e2e-testing"每条 test 独立（自建数据 + 自清理）"+ 速查表"唯一命名"→ 前缀升级见第 3 节
- 跨字段业务规则回检（"使用门槛不能低于面额"类）→ 构造器默认值合法，overrides 后**逐格回检**
  （api-testing §3 既有纪律），非法组合拆显式负向用例
