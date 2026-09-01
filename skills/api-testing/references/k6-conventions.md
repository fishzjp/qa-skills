# k6 压测工程约定（k6-conventions）

> `api-testing` 的性能压测执行层，类型矩阵轴 1 决策 include 时的执行形态。两种承接：
> **agent 直接承接**（type_scope `executor: agent`，standard 起步）与本文件全程工作；
> **移交包承接**（`executor: k6/locust` + handoff_ref）时按移交包的字段与口径执行，
> 可顺带产出脚本草稿回写移交包。档位语义（light / standard / full）以
> `../core/test-type-matrix.md` 轴 1 为唯一来源，本文件不为档位发明新语义。

## 1. 接入与运行

```bash
brew install k6          # 或官方二进制/包管理器，单文件无运行时依赖
k6 run load-xxx.js       # 退出码即 thresholds 判定：0 = 全部阈值通过，非 0 = 存在失败
```

- **退出码对接 pipeline-integration**：thresholds 失败**不是自动 Bug**——默认进 S 级复核 /
  未决项通道，归因（环境容量 / 数据 / 脚本缺陷 / 真实回归）之后才可升 A 类；
  CI 门禁语义是"阻断合入"，不是"自动定性为缺陷"
- 环境地址与账号走环境变量注入（与 api-testing 主纪律一致），不硬编码

## 2. 移交包字段 → k6 options 映射

移交包（`专项移交_性能_{日期}.yaml`）三要素逐项映射，缺项先向移交发起方/用户索取（提问格式按 `../core/clarify-pattern.md` 场景「执行确认」）：

| 移交包字段 | k6 options | 说明 |
|---|---|---|
| 目标（接口清单） | 各 scenario 的 http 请求定义 | 一个核心接口一个 scenario；标明方法 + 路径 + 鉴权方式 |
| 场景参数（并发用户数 / 持续时间 / 阶梯） | `stages` 或 `scenarios` | standard = 单接口阶梯加压；full = 用户旅程 × 到达率 → 多 scenario |
| 阈值 / 验收口径 | `thresholds` | p95 / 错误率起步；移交包带口径时按口径，不带时从业务 SLO 推导并向用户确认 |

## 3. 最小脚本模板（standard：单接口阶梯加压）

```javascript
import http from 'k6/http';
import { check } from 'k6';

export const options = {
  stages: [
    { duration: '1m', target: 20 },   // 阶梯值来自移交包"场景参数"
    { duration: '3m', target: 20 },
    { duration: '1m', target: 0 },
  ],
  thresholds: {
    http_req_duration: ['p(95)<500'],  // 阈值来自移交包"阈值/验收口径"或 SLO
    http_req_failed: ['rate<0.01'],
  },
};

export function setup() {
  // 登录取 token——复用 api-testing 鉴权纪律：环境变量注入，占位实现按项目实际接口改
  const res = http.post(`${__ENV.API_BASE_URL}/login`, JSON.stringify({
    user: __ENV.API_USER, password: __ENV.API_PASSWORD,
  }), { headers: { 'Content-Type': 'application/json' } });
  return { token: res.json('token') };
}

export default function (data) {
  const res = http.get(`${__ENV.API_BASE_URL}/api/target`, {
    headers: { Authorization: `Bearer ${data.token}` },
  });
  check(res, { '状态码 200': (r) => r.status === 200 });
}
```

## 4. 档位对接

- **light**：代码级性能审查（分页 / 缓存 / N+1 / 锁，逐项出 E2 证据清单）——矩阵既有语义，无脚本
- **standard**：单接口阶梯加压（第 3 节模板），p95 + 错误率两阈值起步
- **full**：压测模型（用户旅程 × 到达率阶梯）→ `scenarios` 多场景展开（浏览 / 下单 / 支付各按到达率配 `constant-arrival-rate` 或 `ramping-arrival-rate`），每场景独立 thresholds；产出瓶颈归因报告（慢在哪个接口 / 哪类资源，E3 证据 = summary 原文）

## 5. 触发分层对接（pipeline-integration）

| 层级 | 压测动作 |
|---|---|
| PR 冒烟 | 不跑压测（快失败 <10 分钟，压测不进 P0） |
| 夜间全量 | standard 档压测（阈值失败走 S 级复核，不直接红灯定性） |
| 发布卡点 | full 档（类型矩阵 full 轴范围），thresholds 失败阻断发布 + 归因 |

## 6. 结果回收

- `k6 run` 末尾的 end-of-test summary 是回收源：截取指标块 + 阈值判定落
  `{项目}/压测报告_{日期}.md`
- 回填 `../core/report-template.md` §7 表：执行方列如实填 `k6`，结果摘要含
  "指标 / 阈值 / 通过与否"，产物路径指向压测报告
- **移交承接场景**：按移交包"阈值/验收口径"判定后回填；执行前提不可得（无独立环境 /
  数据不可重置）时按矩阵 R5 记 blocked + todo，不静默跳过
- 移交承接时可附 k6 脚本草稿：脚本路径写回移交包（optional 字段），把"移交不断链"
  升级为"移交可执行"

## 7. 处置纪律

- **基准先行**：正式加压前先跑一次短程基准（1 VU × 30s）测当前水位——阈值不拍脑袋，
  从 SLO 或移交包口径推导，与基准差距异常先查环境
- **前置确认**（「执行确认」）：压测环境是否独立（不打生产 / 不与同事共用环境）、
  数据是否可重置、能打多大压力——三问清了再开压
- **基准噪音控制**：矩阵轴 1 成本因子——共用环境的干扰流量会让基准失真，结论里声明环境状况
- **压测不达标 ≠ Bug**：先归因（环境容量 / 数据 / 脚本缺陷 / 真实回归），归因依据落
  报告后才可进缺陷流程
- **压测安全**：阶梯值不自行放大——移交包/用户给多少就压多少，"多压一点看看极限"
  必须先问
