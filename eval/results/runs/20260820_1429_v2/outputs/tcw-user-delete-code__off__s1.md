# 用户资料模块测试用例

## 1. 用户注销 (delete_user)
### 1.1 正常场景
- TC_DEL_001: 注销存在的有效用户
  - 前置条件: 用户存在于 `users` 表，缓存 `user:profile:{user_id}` 存在
  - 操作步骤: 调用 `delete_user(user_id)`
  - 预期结果: 返回 `{"deleted": True}`；DB中 `users` 表该记录被硬删除；缓存被清除
### 1.2 异常场景
- TC_DEL_002: 注销不存在的用户
  - 前置条件: `user_id` 在 `users` 表中不存在
  - 操作步骤: 调用 `delete_user(user_id)`
  - 预期结果: 抛出 `ValueError: user {user_id} not found`
### 1.3 需求与代码差异覆盖（缺陷验证）
- TC_DEL_003: 验证注销后用户不可登录
  - 操作步骤: 注销用户后尝试使用该用户凭证登录
  - 预期结果: 登录失败（代码未见拦截逻辑，需追踪验证）
- TC_DEL_004: 验证公开内容下线
  - 操作步骤: 注销用户后访问其 `user_profiles` 等公开内容
  - 预期结果: 内容不可见（代码未处理，需追踪验证）
- TC_DEL_005: 验证搜索索引在30天内清除 (合规要求)
  - 操作步骤: 注销用户后执行 `daily_cleanup`
  - 预期结果: 搜索索引移除该用户。**实际代码因硬删除导致无法查询到 `deleted=1`，不满足合规要求（严重缺陷）**

## 2. 修改昵称 (update_nickname)
### 2.1 正常场景
- TC_NICK_001: 修改昵称为合法长度 (1-20个字符)
  - 前置条件: 用户存在
  - 操作步骤: 传入 5 个字符的合法昵称调用 `update_nickname`
  - 预期结果: 返回 `{"ok": True}`，DB中 `nickname` 字段更新成功
- TC_NICK_002: 修改昵称为最小边界 (1个字符)
  - 操作步骤: 传入 1 个字符的昵称
  - 预期结果: 更新成功
- TC_NICK_003: 修改昵称为最大边界 (20个字符)
  - 操作步骤: 传入 20 个字符的昵称
  - 预期结果: 更新成功
### 2.2 异常场景
- TC_NICK_004: 传入空昵称 (None)
  - 操作步骤: 传入 `None`
  - 预期结果: 抛出 `ValueError: nickname required`
- TC_NICK_005: 传入纯空格昵称
  - 操作步骤: 传入 `"   "`
  - 预期结果: 抛出 `ValueError: nickname required`
### 2.3 需求与代码差异覆盖（缺陷验证）
- TC_NICK_006: 修改昵称为超长长度 (21个字符)
  - 操作步骤: 传入 21 个字符的昵称
  - 预期结果: 需求要求1-20个字符，应拒绝修改。**实际代码未做长度校验直接保存（缺陷）**
- TC_NICK_007: 传入包含首尾空格的昵称
  - 操作步骤: 传入 `"  abc  "` (总长度<20，strip后非空)
  - 预期结果: 代码校验strip后非空，但保存原字符串带空格。需确认是否应统一去除首尾空格。

## 3. 开通VIP (open_vip)
### 3.1 正常场景
- TC_VIP_001: 开通1个月VIP
  - 前置条件: 用户存在
  - 操作步骤: 调用 `open_vip(user_id, 1)`
  - 预期结果: 返回 `vip_expire_at`，时间为当前时间 + 31天 (30*1+1)；DB更新成功
- TC_VIP_002: 开通12个月VIP
  - 操作步骤: 调用 `open_vip(user_id, 12)`
  - 预期结果: 返回时间为当前时间 + 361天 (30*12+1)；DB更新成功
### 3.2 异常场景
- TC_VIP_003: 开通0个月VIP
  - 操作步骤: 调用 `open_vip(user_id, 0)`
  - 预期结果: 抛出 `ValueError: months must be 1-12`
- TC_VIP_004: 开通13个月VIP
  - 操作步骤: 调用 `open_vip(user_id, 13)`
  - 预期结果: 抛出 `ValueError: months must be 1-12`
- TC_VIP_005: 开通负数个月VIP
  - 操作步骤: 调用 `open_vip(user_id, -1)`
  - 预期结果: 抛出 `ValueError: months must be 1-12`
### 3.3 需求与代码差异覆盖
- TC_VIP_006: 验证VIP到期失效逻辑
  - 操作步骤: 检查 `is_vip` 在到期前后的表现
  - 预期结果: 需求为按月计费到期失效，代码实际多给1天宽限期，确认为产品逻辑差异。

## 4. VIP状态判断 (is_vip)
### 4.1 正常状态判断
- TC_ISVIP_001: 判断未过期VIP用户
  - 前置条件: 用户 `vip_expire_at` 为未来时间
  - 操作步骤: 调用 `is_vip(user_id)`
  - 预期结果: 返回 `True`
- TC_ISVIP_002: 判断无VIP用户
  - 前置条件: 用户 `vip_expire_at` 为 `None`
  - 操作步骤: 调用 `is_vip(user_id)`
  - 预期结果: 返回 `False`
### 4.2 边界与异常状态判断
- TC_ISVIP_003: 判断已过期VIP用户
  - 前置条件: 用户 `vip_expire_at` 为过去时间
  - 操作步骤: 调用 `is_vip(user_id)`
  - 预期结果: 返回 `False`
- TC_ISVIP_004: 判断不存在的用户
  - 前置条件: `user_id` 在DB中不存在
  - 操作步骤: 调用 `is_vip(user_id)`
  - 预期结果: 返回 `False`
- TC_ISVIP_005: 判断到期时刻边界
  - 前置条件: `vip_expire_at` 恰好等于当前时间 `datetime.now()`
  - 操作步骤: 调用 `is_vip(user_id)`
  - 预期结果: 返回 `True` (代码实现为 `>=`，等于时仍判定为VIP)

## 5. 定时清理任务 (daily_cleanup)
### 5.1 正常清理场景
- TC_CLEAN_001: 存在已软删除用户
  - 前置条件: `users` 表存在 `deleted = 1` 用户且在 `search_index` 中
  - 操作步骤: 调用 `daily_cleanup()`
  - 预期结果: 搜索索引移除对应记录
### 5.2 异常清理场景
- TC_CLEAN_002: 无已软删除用户
  - 前置条件: `users` 表无 `deleted = 1` 用户
  - 操作步骤: 调用 `daily_cleanup()`
  - 预期结果: 正常执行，无异常
- TC_CLEAN_003: 搜索索引中不存在的用户
  - 前置条件: 存在 `deleted = 1` 用户但已不在 `search_index`
  - 操作步骤: 调用 `daily_cleanup()`
  - 预期结果: 正常执行，无异常抛出

## 6. 待澄清清单
1. `delete_user` 采用硬删除，但 `daily_cleanup` 依赖 `deleted=1` 查询，导致搜索索引无法清理，是否需要将注销改为软删除？
2. 用户注销后“不可再登录”和“公开内容下线”的实现代码未在当前模块中体现，是否在其他服务中处理？
3. 昵称修改只校验非空，未校验1-20字符长度限制，是否需要补充代码逻辑？
4. VIP开通逻辑增加了1天宽限期，是否符合最终产品需求？
5. `update_nickname` 中仅判断了 `strip()` 非空，但实际存入DB的是未strip的原字符串，是否需要统一处理空格？