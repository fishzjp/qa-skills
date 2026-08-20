# 用户资料模块测试用例

## 1. 账号注销 (delete_user)
### 1.1 正常场景
- **TC_DEL_001: 注销已存在的正常用户**
  - 前置: 用户存在于 `users` 表，且缓存 `user:profile:{id}` 存在
  - 步骤: 调用 `delete_user(user_id)`
  - 预期: 返回 `{"deleted": True}`
  - 预期: `users` 表中该用户记录被硬删除 (DELETE)
  - 预期: 缓存 `user:profile:{id}` 被成功清除
- **TC_DEL_002: 验证注销后用户不可再登录**
  - 前置: 用户已被 `delete_user` 成功注销
  - 步骤: 尝试使用该用户凭证进行登录
  - 预期: 登录失败，提示用户不存在或已注销
- **TC_DEL_003: 验证注销后公开内容下线 (需求符合度)**
  - 前置: 用户存在 `user_profiles` 表记录及相关公开内容
  - 步骤: 调用 `delete_user(user_id)` 后，访问该用户的公开资料与内容接口
  - 预期: 公开内容不可见/已下线 (注: 代码未实现此逻辑，预期失败，作为缺陷记录)

### 1.2 异常场景
- **TC_DEL_004: 注销不存在的用户**
  - 前置: 传入的 `user_id` 在 `users` 表中不存在
  - 步骤: 调用 `delete_user(user_id)`
  - 预期: 抛出 `ValueError`，包含信息 `"user {user_id} not found"`

## 2. 修改昵称 (update_nickname)
### 2.1 正常场景
- **TC_NICK_001: 修改昵称为1个字符**
  - 前置: 用户存在
  - 步骤: 调用 `update_nickname(user_id, "A")`
  - 预期: 返回 `{"ok": True}`，DB中 `nickname` 更新为 "A"
- **TC_NICK_002: 修改昵称为20个字符**
  - 前置: 用户存在
  - 步骤: 调用 `update_nickname(user_id, "12345678901234567890")`
  - 预期: 返回 `{"ok": True}`，DB中 `nickname` 更新为指定的20个字符

### 2.2 异常场景
- **TC_NICK_003: 昵称为空字符串**
  - 前置: 用户存在
  - 步骤: 调用 `update_nickname(user_id, "")`
  - 预期: 抛出 `ValueError("nickname required")`
- **TC_NICK_004: 昵称为纯空格**
  - 前置: 用户存在
  - 步骤: 调用 `update_nickname(user_id, "   ")`
  - 预期: 抛出 `ValueError("nickname required")`
- **TC_NICK_005: 昵称为 None**
  - 前置: 用户存在
  - 步骤: 调用 `update_nickname(user_id, None)`
  - 预期: 抛出 `ValueError("nickname required")`

### 2.3 边界与缺陷验证
- **TC_NICK_006: 修改昵称为21个字符 (需求不符缺陷验证)**
  - 前置: 用户存在
  - 步骤: 调用 `update_nickname(user_id, "123456789012345678901")`
  - 预期: 需求要求1-20字符，应抛出异常
  - 实际预期: 代码未做长度上限校验，将成功更新，作为缺陷记录
- **TC_NICK_007: 修改昵称包含首尾空格 (逻辑缺陷验证)**
  - 前置: 用户存在
  - 步骤: 调用 `update_nickname(user_id, "  Test  ")`
  - 预期: 保存时去除首尾空格
  - 实际预期: 代码校验使用 `strip()`，但保存使用原字符串，将保存带空格的昵称，作为缺陷记录

## 3. 开通VIP (open_vip)
### 3.1 正常场景
- **TC_VIP_OPEN_001: 开通1个月VIP**
  - 前置: 用户存在
  - 步骤: 调用 `open_vip(user_id, 1)`
  - 预期: 返回 `{"vip_expire_at": <ISO format>}`
  - 预期: 过期时间为当前时间 + 31天 (30*1 + 1)
- **TC_VIP_OPEN_002: 开通12个月VIP**
  - 前置: 用户存在
  - 步骤: 调用 `open_vip(user_id, 12)`
  - 预期: 返回 `{"vip_expire_at": <ISO format>}`
  - 预期: 过期时间为当前时间 + 361天 (30*12 + 1)

### 3.2 异常场景
- **TC_VIP_OPEN_003: 开通0个月VIP**
  - 步骤: 调用 `open_vip(user_id, 0)`
  - 预期: 抛出 `ValueError("months must be 1-12")`
- **TC_VIP_OPEN_004: 开通13个月VIP**
  - 步骤: 调用 `open_vip(user_id, 13)`
  - 预期: 抛出 `ValueError("months must be 1-12")`
- **TC_VIP_OPEN_005: 开通负数月VIP**
  - 步骤: 调用 `open_vip(user_id, -1)`
  - 预期: 抛出 `ValueError("months must be 1-12")`

### 3.3 业务逻辑与风险验证
- **TC_VIP_OPEN_006: 续费VIP (时间是否叠加)**
  - 前置: 用户当前VIP未过期 (如还剩10天)
  - 步骤: 调用 `open_vip(user_id, 1)`
  - 预期: 到期时间应在原基础上增加1个月
  - 实际预期: 代码使用 `now + timedelta()` 直接覆盖，原有未到期时间被抹除，作为缺陷记录
- **TC_VIP_OPEN_007: 按月计费的月历差异风险**
  - 前置: 当前时间为1月31日
  - 步骤: 调用 `open_vip(user_id, 1)`
  - 实际预期: 代码使用固定30天计算，2月无31日，实际到期为3月2日。按自然月计费可能存在偏差，作为风险提示

## 4. VIP状态校验 (is_vip)
### 4.1 正常场景
- **TC_VIP_CHK_001: 用户VIP未过期**
  - 前置: `vip_expire_at` 设为未来时间
  - 步骤: 调用 `is_vip(user_id)`
  - 预期: 返回 `True`
- **TC_VIP_CHK_002: 用户VIP已过期**
  - 前置: `vip_expire_at` 设为过去时间
  - 步骤: 调用 `is_vip(user_id)`
  - 预期: 返回 `False`

### 4.2 异常与边界场景
- **TC_VIP_CHK_003: 用户无VIP记录**
  - 前置: `vip_expire_at` 为 NULL
  - 步骤: 调用 `is_vip(user_id)`
  - 预期: 返回 `False`
- **TC_VIP_CHK_004: 用户不存在**
  - 前置: `user_id` 不在 `users` 表中
  - 步骤: 调用 `is_vip(user_id)`
  - 预期: 返回 `False`
- **TC_VIP_CHK_005: VIP刚好到期 (边界)**
  - 前置: `vip_expire_at` 恰好等于当前 `datetime.now()` (精确到秒)
  - 步骤: 调用 `is_vip(user_id)`
  - 预期: 返回 `True` (因为代码使用 `expire >= datetime.now()`)

## 5. 搜索索引清理 (daily_cleanup)
### 5.1 正常清理逻辑
- **TC_CLEAN_001: 清理软删除标记的用户索引**
  - 前置: `users` 表存在 `deleted = 1` 的记录
  - 步骤: 调用 `daily_cleanup()`
  - 预期: 查询到该记录，并调用 `search_index.remove("user", id)`

### 5.2 合规与缺陷验证
- **TC_CLEAN_002: 硬删除用户的索引清理 (严重缺陷)**
  - 前置: 用户通过 `delete_user` 注销 (硬删除，无 `deleted=1` 标记)
  - 步骤: 调用 `daily_cleanup()`
  - 预期: 应清理该用户搜索索引
  - 实际预期: `daily_cleanup` 查询 `deleted=1`，硬删除用户查不到，导致索引永远不清理，作为严重缺陷记录
- **TC_CLEAN_003: 30天内从搜索索引清除 (合规验证)**
  - 前置: 用户注销后，等待30天
  - 步骤: 观察搜索索引状态
  - 预期: 索引已清除
  - 实际预期: 由于缺陷 TC_CLEAN_002，无法在30天内清除，违反合规要求

## 6. 待澄清清单
- `update_nickname` 中保存的字符串是否应该 `strip()` 后保存？需求未明确，代码行为不一致。
- `open_vip` 多给1天宽限的需求未在需求摘要中体现，是否为产品确认的业务逻辑？
- `open_vip` 续费时是否需要在原有到期时间基础上叠加？需求未明确。
- `is_vip` 判断条件 `expire >= datetime.now()` 导致刚好到期的瞬间仍是VIP，是否符合业务"到期自动失效"的预期？
- `delete_user` 需求要求"公开内容下线"，代码只删除了 `users` 表，未处理 `user_profiles` 等公开内容表，是否由其他机制实现？
- `daily_cleanup` 每天凌晨3点执行，如果某天任务失败，是否有重试机制？"30天内清除"的时效性如何保证（如任务挂了超过30天）？

## 7. 附录：发现的主要缺陷与风险摘要
- **[缺陷-高] 昵称长度校验缺失:** `update_nickname` 未校验最大长度20字符，违反需求约束。
- **[缺陷-中] 昵称存储含首尾空格:** `update_nickname` 仅校验 `strip()` 结果，保存原值可能引发显示异常。
- **[缺陷-高] VIP续费时间覆盖:** `open_vip` 未读取原有到期时间叠加，续费会导致原有剩余有效期丢失。
- **[缺陷-高] 注销未下线公开内容:** `delete_user` 仅删除 `users` 表，未处理 `user_profiles` 等公开内容下线。
- **[缺陷-致命] 搜索索引清理逻辑失效:** `daily_cleanup` 查询 `deleted=1`，而 `delete_user` 为硬删除，导致定时任务永远无法清理已注销用户索引，严重违反30天合规要求。
- **[风险-低] 月历计费偏差:** `open_vip` 使用固定30天计算，跨2月等场景可能导致计费天数与自然月不符。