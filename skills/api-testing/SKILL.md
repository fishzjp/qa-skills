---
name: api-testing
slug: api-testing
displayName: API 接口测试
version: 0.7.0
description: 接口级测试时使用——从 OpenAPI/Swagger 文档或用例 Schema 中可自动化的接口用例出发，覆盖参数、边界、鉴权、幂等、并发、错误响应与数据一致性，产出可执行的 API 测试脚本与运行结果。不用于：Web UI 流程（automated-e2e-testing）、手动用例编写（test-case-writing）。
---

# API 测试（api-testing）

接口级测试——E2E 之外的另一条执行路径。

- **输入**：API 文档（OpenAPI/Swagger）、用例 Schema 中 `execution_model` 可自动化的接口用例、被测环境信息（base URL、账号/Token）
- **输出（落盘）**：API 测试脚本（pytest + requests，或项目既定技术栈）+ 运行结果（报告条目按 `../core/report-template.md` 对齐）
- **边界**：Web UI 流程 → `automated-e2e-testing`；接口手动用例设计 → `test-case-writing`；性能压测 → 专项工具（k6/locust，见 `test-strategy` 的 handoff）

## When to Use

- 给定 OpenAPI/Swagger 文档，需要产出并运行接口自动化测试
- 从用例 Schema 中筛出接口级可自动化用例，转换为 API 脚本执行
- 需要覆盖鉴权/越权、幂等、并发写、错误响应等接口层专项

## When NOT to Use

- Web UI 交互流程（点击 / 页面状态）→ `automated-e2e-testing`
- 编写接口的手动测试用例 → `test-case-writing`
- 端到端流水线 → `qa` 编排
- 接口压测 / 限流摸底 → k6 / locust 专项
- Mock Server 搭建 → 开发协作事项，不在本 skill 范围

## 脚手架（默认 pytest + requests，可替换为项目既定栈）

```text
api-tests/
├── conftest.py            # fixture：base_url、会话/Token、环境配置（读 .env，不硬编码）
├── common/
│   └── client.py          # 统一请求封装：日志、超时、鉴权头、断言辅助
├── test_{模块}_{接口}.py   # 一个接口一个文件，test 名沿用 TC 编号
└── requirements.txt
```

```python
# common/client.py —— 统一请求封装（requests.Session 不支持 base_url，必须显式拼接）
class Client:
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url.rstrip("/")
        self.s = requests.Session()
        self.s.headers.update({"Authorization": f"Bearer {token}"})

    def request(self, method: str, path: str, **kwargs):
        url = f"{self.base_url}/{path.lstrip('/')}"
        kwargs.setdefault("timeout", 10)
        return self.s.request(method, url, **kwargs)

    def get(self, path, **kw):  return self.request("GET", path, **kw)
    def post(self, path, **kw): return self.request("POST", path, **kw)
    # put / delete / patch 同理扩展

def login(user: str, password: str) -> str:
    """按项目实际登录接口实现（如 POST /login 换 token）——占位，勿直接照抄"""
    raise NotImplementedError("按项目登录接口实现")
```

```python
# conftest.py 关键 fixture
@pytest.fixture(scope="session")
def client():
    base_url = os.environ["API_BASE_URL"]          # 环境与账号不硬编码，走环境变量
    token = login(os.environ["API_USER"], os.environ["API_PASSWORD"])
    return Client(base_url, token)
```

> 敏感信息（账号/Token/环境地址）一律环境变量注入，不进代码仓库（与 `automated-e2e-testing` 的 constants 约定一致）。

## 工作流

### 1. 输入解析与范围确认

- 从 OpenAPI 文档提取：接口清单、参数表（必填/类型/范围/默认值）、错误码、鉴权方式
- 从用例 Schema 过滤：`execution_model: dev-collab` 或 `automation.framework: api` 的用例 → 转换对象（test 名沿用 TC 编号：`test_TC_05_01_写入字段读回一致`）
- 环境未知 → 向用户索取（base URL、账号、是否可写生产旁路环境），**不确定就问，不猜接口行为**（提问格式与裁决落盘统一按 `../core/clarify-pattern.md`，场景用「执行确认」）

### 2. 用例设计（此时加载 `../core/testing-principles.md`，方法细节 `../core/methods/data-driven.md`）

每接口一张参数矩阵（**分析过程工具，心内构建或草稿即可，不落盘为中间文件**——结论直接进用例，与 test-case-writing 的无中间文件口径一致），逐参数 × 逐属性；重点覆盖：

| 类别 | 必测点 |
|------|--------|
| 参数 | 必填缺失 / 类型错误 / 边界值（空/最值/超大，见 `../core/methods/boundary.md`） |
| 鉴权 | 无 Token / 过期 Token / 错误 Token / 越权（他人资源 id） |
| 幂等 | 同一业务键重复提交 → 不重复创建；重试安全 |
| 并发 | 并发写同一资源 → 无互相覆盖、无中间态 |
| 错误响应 | 每个错误码的触发条件 + 响应体结构与文案 |
| 数据一致性 | 写后读回一致；级联操作后关联数据一致 |

多参数接口的组合面按 `../core/methods/data-driven.md` 第 2 节**显式降档**执行（全组合 → 成对组合 → 风险挑选）：单参数逐属性做全；跨参数交互（跨字段规则 / 参数依赖）选档覆盖，**成对组合为默认档**；降档与被排除的组合面写进 rationale，不静默收缩。

### 3. 脚本编写

- 一个接口一个 test 文件；一条 test 只测一个点，沿用 TC 编号命名
- **输出预算纪律（防空截断）**：同类边界/参数校验用 `@pytest.mark.parametrize` 合并为一条参数化测试，禁止逐值展开重复的 test 函数或超长重复断言——单文件超过 ~250 行即应参数化收敛（生成通道有输出上限，超限会截断产生不可编译代码）
- 断言三件套：状态码 + 业务码 + 响应体关键字段（不写"只断言 200"的弱断言）
- 测试数据自建自清理（setup 创建 / teardown 删除），不依赖执行顺序；数据模板（唯一名等）先核对材料字段约束（maxLength/枚举/格式），模板总长（前缀+随机段）≤ 约束上限 −2——顶格即数据自建缺陷（实测自伤案例：唯一名模板 22 字符撞契约 maxLength 20）；**参数矩阵逐格回检跨字段业务规则**（如"使用门槛不能低于面额"）——违反规则的组合改取合法值或拆为显式负向用例，不做隐式非法组合（实测自伤案例：金额顶格 1000 配低于面额的门槛 → 400 THRESHOLD_INVALID 而用例期望 201）
- 依赖前序状态的用例显式在前置里造数，不假设库里有数据

### 4. 运行与结果

报告条目与统计口径以 `../core/report-template.md` 为唯一来源（含机读摘要片段，收尾时加载），保证可直接拼装进 `qa` 收尾的最终报告：

```bash
pytest api-tests/ -v --tb=short          # 全量
pytest api-tests/test_coupon_create.py   # 单文件
```

- 失败用例先分辨：被测系统 Bug / 环境问题 / 用例自身错误——**不自行假设**，环境问题与预期歧义列出来问用户（提问格式同上，`../core/clarify-pattern.md`）
- 失败 ≥3 条时升级为**批量分流**：先按 `../core/triage.md` 四分类定类（A 真缺陷 / B 资产问题〔补齐产品预期变更 B1〕/ C 环境 / D 不稳定），仅 A 类进入下方 Bug 记录流程，替换单条逐个分辨
- **流水线运行**：以 headless 模式进入 PR 冒烟 / 夜间任务时，检查点降级为未决项、产物按规范落盘、退出码分离基建故障与真缺陷——三条约定见 `../core/pipeline-integration.md`（此时加载）
- **结构覆盖补充证据（可选）**：有被测服务代码且测试环境可插桩（Python 服务 `coverage run` 启动；JVM 服务 JaCoCo agent）时，接口用例跑完取**被测服务的行/分支覆盖率**作为补充 E3 证据——只用于发现**零覆盖/极低覆盖的接口与分支**（漏测信号，转补用例或策略升档），不作为追高的虚荣指标；无插桩条件直接跳过，不阻塞交付
- 发现的 Bug：证据（请求/响应原文、时间戳）按 `../core/report-template.md` §3 记录条目，根因分析移交 `bug-analysis`

### 5. 交付

脚本路径 + 运行统计（§2 执行统计：P0/P1/P2 × 通过/失败/阻塞/未执行，按 `../core/report-template.md`）+ Bug 条目 + 遗留问题清单 + （有插桩时）结构覆盖摘要：零覆盖/低覆盖接口清单。

## Common Mistakes

| 错误 | 后果 | 正确做法 |
|------|------|---------|
| 只断言状态码不断言业务码与响应体 | Bug 漏检（200 但业务失败） | 状态码 + 业务码 + 关键字段三件套 |
| 硬编码环境地址与账号 | 无法跨环境运行、泄露敏感信息 | 环境变量注入 |
| 测试间共享可变状态 | 顺序依赖、偶发失败 | 自建数据 + 自清理，每条独立 |
| 重复提交不测幂等 | 重复创建类 Bug 上线 | 同业务键重复请求必测 |
| 失败一律记为 Bug | 误报污染报告 | 先归因（系统/环境/用例），歧义问用户 |
| 无权限/越权只测前端表现 | 后端未拦截的越权漏检 | 直接调接口测鉴权（无 Token/过期/他人 id） |
| 多参数接口逐值全展开或随手抽样 | 组合爆炸截断 / 参数交互缺陷静默漏测 | 按降档策略显式选档（全组合 → 成对 → 风险挑选），降档留痕 |
| Schema 用例带占位符/虚构入口仍直接翻成脚本 | 幻觉脚本：能跑通但测的不是真实接口 | 转换前过 `../core/executability.md` 红线闸门，补不了的暂缓进遗留清单 |
