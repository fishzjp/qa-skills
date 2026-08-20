# Benchmark 报告（v2 科学评估体系）— 20260820_1429_v2

> **生成后勘误（2026-08-20）**：Wilson 区间原显示为倒挂的 [50.0%, 31.1%]（误把点估计当下界），正确为 **[31.1%, 69.0%]（点估计 50.0%）**；`effective_coverage_all` 的 Off 均值含 1 个 judge 错位样本且 On/Off 分母不对称（10 vs 11 任务）——harness 已修（配对口径 + GT-id 校验），本表保留原始口径供追溯。metrics.json 原始数据未动。

- 生成模型：glm-5-2-260617；评审模型：glm-5-2-260617；每任务×模式 3 采样；judge 3 采样多数表决；成对评审含位置互换
- 统计推断：任务层配对 bootstrap 10000 次报 95%CI；成对胜率报 Wilson 95%CI
- 时间：2026-08-20T17:06:14

## 逐任务指标（任务均值 ± 生成 SD）

| 任务 | 模式 | 有效覆盖(mean±sd) | 检出 | 质量 | 可执行性 | 编译 | 执行通过率 | 成对 |
|---|---|---|---|---|---|---|---|---|
| api-openapi-coupon | on | 87.2%±22pp | — | 0.911 | — | 67% | — | 0胜/0负/2平 |
| api-openapi-coupon | off | 97.4%±4pp | — | 0.889 | — | 67% | — | 0胜/0负/2平 |
| bug-import-offbyone | on | —±0pp | 100.0% | 0.978 | — | — | — | 0胜/0负/2平 |
| bug-import-offbyone | off | —±0pp | 100.0% | 1.0 | — | — | — | 0胜/0负/2平 |
| e2e-markmap-to-spec | on | 96.3%±6pp | — | 0.889 | — | 100% | — | 1胜/0负/1平 |
| e2e-markmap-to-spec | off | 81.5%±6pp | — | 0.822 | — | 33% | — | 1胜/0负/1平 |
| reg-diff-schema | on | 100.0%±0pp | 79.2% | 0.844 | — | — | — | 0胜/0负/2平 |
| reg-diff-schema | off | 100.0%±0pp | 87.5% | 0.911 | — | — | — | 0胜/0负/2平 |
| req-prd-contradictions | on | 100.0%±0pp | 76.7% | 0.933 | — | — | — | 0胜/1负/1平 |
| req-prd-contradictions | off | 100.0%±0pp | 76.7% | 0.844 | — | — | — | 0胜/1负/1平 |
| rev-flawed-cases | on | —±0pp | 100.0% | 0.978 | 0.948 | — | — | 0胜/0负/2平 |
| rev-flawed-cases | off | 37.5%±0pp | 77.8% | 0.667 | 0.549 | — | — | 0胜/0负/2平 |
| strategy-transfer-risk | on | 100.0%±0pp | 100.0% | 1.0 | — | — | — | 0胜/0负/2平 |
| strategy-transfer-risk | off | 71.4%±14pp | 100.0% | 0.822 | — | — | — | 0胜/0负/2平 |
| tcw-coupon-prd | on | 99.6%±1pp | — | 1.0 | 0.996 | — | — | 0胜/0负/1平 |
| tcw-coupon-prd | off | 97.1%±3pp | — | 0.922 | — | — | — | 0胜/0负/1平 |
| tcw-export-noui | on | 98.6%±0pp | — | 1.0 | 0.986 | — | — | 0胜/0负/2平 |
| tcw-export-noui | off | 97.4%±4pp | — | 0.889 | — | — | — | 0胜/0负/2平 |
| tcw-incremental | on | 90.5%±8pp | — | 0.778 | 0.986 | — | — | 0胜/0负/2平 |
| tcw-incremental | off | 91.7%±7pp | — | 0.844 | 1.0 | — | — | 0胜/0负/2平 |
| tcw-order-state | on | 93.5%±5pp | — | 0.889 | 0.982 | — | — | 0胜/0负/2平 |
| tcw-order-state | off | 87.3%±14pp | 100.0% | 0.911 | — | — | — | 0胜/0负/2平 |
| tcw-user-delete-code | on | 94.7%±3pp | 100.0% | 0.867 | 0.991 | — | — | 0胜/0负/2平 |
| tcw-user-delete-code | off | 84.4%±4pp | 100.0% | 0.867 | — | — | — | 0胜/0负/2平 |

## 聚合与统计推断

- **effective_coverage_tcw**：Δ=3.8%，95%CI[0.5%, 7.1%]（On=95.4% / Off=91.6%，n=5 任务）
- **effective_coverage_all**：Δ=5.2%，95%CI[-0.6%, 11.8%]（On=96.0% / Off=86.0%，n=10 任务）
- **quality**：Δ=5.7%，95%CI[0.2%, 11.8%]（On=92.2% / Off=86.6%，n=12 任务）
- **detection**：Δ=2.3%，95%CI[-4.2%, 11.1%]（On=92.6% / Off=91.7%，n=6 任务）
- **pairwise**：{"win_rate_on": 0.5, "wilson95": [0.5, 0.3108, 0.6892], "on": 1, "off": 1, "tie": 21, "n": 23}
- **executability_on**：0.9814
- **executability_off**：0.7743
- **bug_detection_on**：1.0
- **compile_on**：{"api-openapi-coupon": 0.6667, "e2e-markmap-to-spec": 1.0}
- **execution_success**：{"e2e-markmap-to-spec__on": 0.7778, "e2e-markmap-to-spec__off": 0.0, "api-openapi-coupon__on": 0.5192, "api-openapi-coupon__off": 0.8693}
- **gen_sd_effective_coverage**：{"api-openapi-coupon__on": 0.222, "api-openapi-coupon__off": 0.0444, "e2e-markmap-to-spec__on": 0.0641, "e2e-markmap-to-spec__off": 0.0641, "reg-diff-schema__on": 0.0, "reg-diff-schema__off": 0.0, "req-prd-contradictions__on": 0.0, "req-prd-contradictions__off": 0.0, "rev-flawed-cases__off": 0.0, "strategy-transfer-risk__on": 0.0, "strategy-transfer-risk__off": 0.1429, "tcw-coupon-prd__on": 0.0069, "tcw-coupon-prd__off": 0.0251, "tcw-export-noui__on": 0.0045, "tcw-export-noui__off": 0.0444, "tcw-incremental__on": 0.0847, "tcw-incremental__off": 0.0722, "tcw-order-state__on": 0.0463, "tcw-order-state__off": 0.1375, "tcw-user-delete-code__on": 0.0342, "tcw-user-delete-code__off": 0.0385}
- **generalization**：{}
- **pairwise 胜率(On, 平局=0.5)**：50.0%，Wilson95[31.1%, 69.0%]（点估计 50.0%；1胜/1负/21平 / 23 对）
- **efficiency**：{"on": {"mean_cases": 39.3, "dup_rate": 0.0793, "mean_tokens_total": 26297}, "off": {"mean_cases": 10.3, "dup_rate": 0.0, "mean_tokens_total": 7858}}

## 预期效果门（v1.0 冻结版，见 eval/EXPECTED.md）

- ❌ **G1_tcw_cov_mean**：tcw 类有效覆盖均值差 ≥ +5pp 且 bootstrap 95%CI 下界 > 0 —— Δ=3.8% CI95=[0.5%, 7.1%] (n=5)
- ❌ **G1_state_cov**：状态机任务有效覆盖差 ≥ +20pp —— On=93.5% Off=87.3% Δ=6.2%
- ✅ **G2_exec**：tcw 类 On 可执行性均值 ≥ 0.85 —— On 可执行性均值=0.9814
- ✅ **G3_bug**：代码任务 bug 检出 On ≥ 75% —— On 检出=100.0%
- ❌ **G4_compile**：代码类任务 On 编译通过率 100% —— {'api-openapi-coupon': 0.6667, 'e2e-markmap-to-spec': 1.0}
- ✅ **G5_quality**：质量均分 On ≥ 0.80 且 > Off —— On=0.9222 Off=0.8657 Δ=0.0565
- ✅ **G6_no_regression**：On 在 ≥ 2/3 可比任务上不劣于 Off（-10pp 容差） —— 不劣于 11/12

## 观察型指标（本轮采集，下一轮纳入门）

- G-X1 执行成功率(E2E/API 真实执行)
- G-X2 成对胜率(pairwise)
- G-X3 生成方差(SD)
- G-X4 Efficiency(用例数/重复率/tokens)
