# 用户资料模块 测试用例

## 模块信息
- 仓库：user-service（分支 main）
- 覆盖文件：user_service.py / vip_service.py / profile_cleanup.py
- 用例设计方法：等价类划分、边界值、需求-实现差异分析
- 覆盖维度：功能正向 / 异常输入 / 边界条件 / 数据一致性 / 合规 / 缺陷回归

## 1. 用户注销 delete_user

### 1.1 功能正向
- TC-DEL-001 注销存在的用户
  - 前置：users 表存在 id=1001 记录
  - 步骤：delete_user(1001)
  - 预期：返回 {"deleted": True}；db.find_one("users", id=1001) 为 None
- TC-DEL-002 注销后清除资料缓存
  - 前置：cache 存在 key=user:profile:1001
  - 步骤：delete_user(1001)
  - 预期：cache.get("user:profile:1001") 为 None
- TC-DEL-003 注销已缓存用户后再注销（幂等性验证）
  - 前置：用户已注销、缓存已清
  - 步骤：再次 delete_user(1001)
  - 预期：抛出 ValueError("user 1001 not found")

### 1.2 异常输入
- TC-DEL-004 用户不存在
  - 步骤：delete_user(999999)
  - 预期：抛出 ValueError，且不触发 db.delete / cache.delete
- TC-DEL-005 user_id 类型非法
  - 步骤：delete_user("abc") / delete_user(None) / delete_user(-1)
  - 预期：抛出 TypeError 或 ValueError，无副作用

### 1.3 需求-实现差异（缺陷标记）
- BUG-DEL-01 公开内容未下线
  - 需求：注销后其公开内容下线
  - 实现：仅删除 users 行 + 清缓存，未处理 user_profiles（avatar/bio）
  - 预期用例（待修复后）：注销后 user_profiles 对应行不可见/被删除
- BUG-DEL-02 注销后登录未拦截
  - 需求：注销后用户不可再登录
  - 实现：无登录态校验逻辑（硬删除后理论上查不到，但需验证登录链路依赖）
  - 预期用例：以已注销 user_id 调用登录接口，应拒绝
- BUG-DEL-03 orders 外键孤儿数据
  - 注释：orders.user_id 外键，硬删除 users 后产生孤儿订单
  - 预期用例：注销后核查 orders 表无破坏/或按策略保留

## 2. 修改昵称 update_nickname

### 2.1 功能正向
- TC-NICK-001 修改为 1 字符昵称
  - 步骤：update_nickname(1001, "A")
  - 预期：返回 {"ok": True}；DB 中 nickname="A"
- TC-NICK-002 修改为 20 字符昵称
  - 步骤：update_nickname(1001, "a"*20)
  - 预期：返回 {"ok": True}
- TC-NICK-003 修改为中间长度昵称（如 10 字符）
  - 预期：成功

### 2.2 异常输入
- TC-NICK-004 nickname 为 None
  - 步骤：update_nickname(1001, None)
  - 预期：抛出 ValueError("nickname required")
- TC-NICK-005 nickname 为空字符串
  - 步骤：update_nickname(1001, "")
  - 预期：抛出 ValueError
- TC-NICK-006 nickname 仅含空白字符
  - 步骤：update_nickname(1001, "   ")
  - 预期：抛出 ValueError

### 2.3 边界与实现差异
- BUG-NICK-01 未校验 20 字符上限
  - 需求：昵称 1–20 个字符
  - 实现：仅校验非空，未限制最大长度
  - 用例 TC-NICK-007：update_nickname(1001, "a"*21)
    - 当前实际：成功写入（缺陷）
    - 修复后预期：抛出 ValueError 或截断拒绝
- BUG-NICK-02 前后空格被存入
  - 实现：strip() 仅用于判空，db.update 写入原值 nickname
  - 用例 TC-NICK-008：update_nickname(1001, "  Alice  ")
    - 当前实际：存储 "  Alice  "（长度含空格，可能突破 20 限制）
    - 建议预期：存储前 strip 或拒绝
- TC-NICK-009 超长 + 前后空格组合
  - 步骤："  " + "a"*20 + "  "（strip 后 20，原始 24）
  - 当前实际：通过校验并写入 24 字符
  - 标记为缺陷回归用例

## 3. 开通 VIP open_vip

### 3.1 功能正向
- TC-VIP-001 开通 1 个月
  - 步骤：open_vip(1001, 1)
  - 预期：返回 vip_expire_at = now + 31 天（30*1+1）；DB 已写入
- TC-VIP-002 开通 12 个月
  - 步骤：open_vip(1001, 12)
  - 预期：vip_expire_at = now + 361 天
- TC-VIP-003 开通中间月数 6
  - 预期：vip_expire_at = now + 181 天
- TC-VIP-004 返回值为 isoformat 字符串
  - 预期：可被 datetime.fromisoformat 解析

### 3.2 异常输入
- TC-VIP-005 months=0
  - 预期：抛出 ValueError("months must be 1-12")
- TC-VIP-006 months=13
  - 预期：抛出 ValueError
- TC-VIP-007 months 为负数
  - 预期：抛出 ValueError
- TC-VIP-008 months 为 None / 字符串 / 浮点
  - 预期：抛出 TypeError 或 ValueError

### 3.3 需求-实现差异
- BUG-VIP-01 "按月计费"实现为固定 30 天 + 1 天宽限
  - 需求：按月计费，到期自动失效
  - 实现：timedelta(days=30*months+1)，非自然月
  - 场景：1 月 31 日开通 1 个月，理论应 2 月 28/29 日到期，实现为 3 月 3 日
  - 建议澄清：是否接受固定 30 天口径
- BUG-VIP-02 宽限 1 天未在需求体现
  - 实现：+1 天宽限
  - 影响：is_vip 在第 31 天仍返回 True
  - 待澄清：是否为产品确认的宽限策略

## 4. VIP 状态判断 is_vip

### 4.1 功能正向
- TC-CHK-001 VIP 未到期
  - 前置：vip_expire_at = now + 10 天
  - 预期：is_vip(1001) == True
- TC-CHK-002 VIP 已过期
  - 前置：vip_expire_at = now - 1 天
  - 预期：is_vip(1001) == False

### 4.2 边界
- TC-CHK-003 到期时刻等于当前时刻
  - 前置：vip_expire_at = now（精度对齐到秒）
  - 实现：expire >= now → True
  - 预期：True（需与产品确认"到期即失效"口径，存在语义冲突）
- TC-CHK-004 超过 1 秒
  - 前置：vip_expire_at = now - 1s
  - 预期：False
- TC-CHK-005 到期日当天 23:59:59
  - 预期：根据 expire 与 now 比较结果

### 4.3 异常
- TC-CHK-006 用户不存在
  - 前置：db.find_one 返回 None
  - 预期：False
- TC-CHK-007 vip_expire_at 为 None（从未开通）
  - 预期：False
- TC-CHK-008 vip_expire_at 格式非法
  - 预期：fromisoformat 抛出 ValueError（当前未捕获，需评估容错）

## 5. 每日清理任务 daily_cleanup

### 5.1 功能正向（基于当前实现的假设）
- TC-CLN-001 存在 deleted=1 的用户
  - 前置：DB 存在 deleted=1 记录（需手工构造，因 delete_user 不写 deleted）
  - 步骤：daily_cleanup()
  - 预期：search_index.remove("user", id) 被调用
- TC-CLN-002 无 deleted=1 用户
  - 预期：正常结束，无 remove 调用
- TC-CLN-003 多个已注销用户批量处理
  - 预期：逐个 remove

### 5.2 严重缺陷（合规阻断）
- BUG-CLN-01 daily_cleanup 永远查不到已注销用户
  - 根因：delete_user 为硬删除（DELETE），不写 deleted=1
  - 结果：daily_cleanup 的 "WHERE deleted=1" 恒为空集
  - 影响：合规要求"30 天内从搜索索引清除"无法通过本任务实现
  - 回归用例 TC-CLN-004：
    - 步骤：delete_user(1001) → daily_cleanup()
    - 当前实际：搜索索引中仍存在 user:1001（缺陷）
    - 修复后预期：搜索索引中 user:1001 被移除
- BUG-CLN-02 依赖"每日全量重建"的合规时效
  - 注释：搜索索引通过每日全量任务重建
  - 风险：若全量重建失败/延迟，30 天合规可能突破
  - 用例：模拟全量重建失败，验证是否有告警/补偿

### 5.3 时效与调度
- TC-CLN-005 凌晨 3 点触发
  - 验证调度配置（cron 表达式）
- TC-CLN-006 注销后最坏 24 小时内被清理
  - 前置：注销发生在凌晨 3:01
  - 预期：次日 3:00 清理，间隔 < 24h，满足 30 天合规
- TC-CLN-007 注销后立即触发场景
  - 当前实现无即时清理，待澄清是否需补

## 6. 集成与端到端

### 6.1 注销全链路
- TC-E2E-01 运营后台注销违规用户 → 用户登录被拒
- TC-E2E-02 注销 → 公开内容（profile/bio/avatar）对外不可见
- TC-E2E-03 注销 → 次日 3:00 后搜索索引无该用户
- TC-E2E-04 注销 → 30 天内搜索索引必定清除（合规验收）

### 6.2 VIP 全生命周期
- TC-E2E-05 开通 VIP → 期间 is_vip=True → 到期自动 is_vip=False
- TC-E2E-06 到期后再开通，过期时间从 now 重新计算（当前实现覆盖原值，未叠加）
- TC-E2E-07 未到期续费 months 叠加
  - 当前实现：open_vip 直接以 now 为基准覆盖，未叠加剩余有效期
  - 标记缺陷 BUG-VIP-03：续费未叠加原剩余时长

## 7. 附录 A：缺陷清单

| 编号 | 模块 | 严重度 | 描述 |
| --- | --- | --- | --- |
| BUG-DEL-01 | delete_user | 高 | 公开内容（user_profiles）未下线 |
| BUG-DEL-02 | delete_user | 高 | 注销后登录拦截未在代码链路体现 |
| BUG-DEL-03 | delete_user | 中 | orders 外键孤儿数据未处理 |
| BUG-NICK-01 | update_nickname | 高 | 未校验 20 字符上限 |
| BUG-NICK-02 | update_nickname | 中 | 前后空格被存入，可绕过长度限制 |
| BUG-VIP-01 | open_vip | 中 | 按月计费实现为固定 30 天，非自然月 |
| BUG-VIP-02 | open_vip | 中 | +1 天宽限未在需求体现 |
| BUG-VIP-03 | open_vip | 中 | 续费未叠加剩余有效期 |
| BUG-CLN-01 | daily_cleanup | 阻断 | 硬删除导致 deleted=1 查询恒空，清理任务失效 |
| BUG-CLN-02 | daily_cleanup | 中 | 依赖全量重建，缺补偿与告警 |

## 8. 附录 B：待澄清清单

1. "公开内容下线"具体范围：user_profiles？动态/评论/作品？是否需要保留审计副本？
2. 搜索索引清除的 30 天起算点：注销当日 0 点？注销时刻？次日凌晨 3 点？
3. 昵称是否需要敏感词、特殊字符、Emoji、组合字符（ZWP）过滤？
4. 昵称前后空格的存储策略：strip 后存储 还是 拒绝含前后空格？
5. VIP "按月计费"口径：自然月 还是 固定 30 天？+1 天宽限是否产品确认？
6. VIP 续费是否应叠加剩余有效期？是否存在订单/支付状态机？
7. orders 表在用户注销后：保留？脱敏？软删除？外键约束策略？
8. daily_cleanup 是否需要即时触发入口（事件驱动）以满足极端合规？
9. deleted 字段是否应恢复为软删除统一标记，以支持清理任务与审计？
10. is_vip 在 expire == now 的边界口径："到期即失效"与 >= 实现冲突，以哪个为准？