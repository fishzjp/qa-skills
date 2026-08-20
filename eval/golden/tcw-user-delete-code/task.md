# 任务：基于代码编写用户资料模块测试用例

你是测试工程师。请根据下方需求摘要与代码实现，为「用户资料模块」编写测试用例文件（markmap 格式）。仓库路径以材料中文件名为准（本任务为自包含代码摘录）。

请直接输出最终用例文件的完整内容（含代码模式下应有的全部附录产出）。

---

## 输入材料

### 材料 1：需求摘要《用户资料模块》

- 运营后台可注销违规用户；注销后用户不可再登录，其公开内容下线
- 会员可开通 VIP，按月计费，到期自动失效
- 用户可修改昵称，昵称要求 1–20 个字符
- 已注销用户的资料应在 30 天内从搜索索引中清除（合规要求）

### 材料 2：代码实现（节选自用户服务仓库 user-service，分支 main）

```python
# user_service.py
from db import DB
from cache import Cache

db = DB()
cache = Cache()

def delete_user(user_id: int):
    """注销用户：删除账号与公开内容下线"""
    user = db.find_one("users", id=user_id)
    if user is None:
        raise ValueError(f"user {user_id} not found")
    db.delete("users", user_id)                      # 删除账号
    cache.delete(f"user:profile:{user_id}")          # 清缓存
    # 搜索索引通过每日全量任务重建，无需即时清理
    return {"deleted": True}


def update_nickname(user_id: int, nickname: str):
    """修改昵称：1-20 个字符"""
    if nickname is None or len(nickname.strip()) == 0:
        raise ValueError("nickname required")
    db.update("users", user_id, {"nickname": nickname})
    return {"ok": True}


# vip_service.py
import calendar
from datetime import datetime, timedelta

def open_vip(user_id: int, months: int) -> dict:
    """开通 VIP：按月计费，到期自动失效"""
    if months < 1 or months > 12:
        raise ValueError("months must be 1-12")
    now = datetime.now()
    expire = now + timedelta(days=30 * months + 1)   # 满月即到期，多给 1 天宽限
    db.update("users", user_id, {"vip_expire_at": expire})
    return {"vip_expire_at": expire.isoformat()}


def is_vip(user_id: int) -> bool:
    row = db.find_one("users", id=user_id)
    if row is None or row.get("vip_expire_at") is None:
        return False
    expire = datetime.fromisoformat(row["vip_expire_at"])
    return expire >= datetime.now()                  # 到期时刻即失效
```

```python
# profile_cleanup.py（每日定时任务，凌晨 3 点执行）
def daily_cleanup():
    """每日清理：将已注销用户从搜索索引移除"""
    deleted_users = db.query("SELECT id FROM users WHERE deleted = 1")
    for u in deleted_users:
        search_index.remove("user", u["id"])
```

### 材料 3：数据库表结构（节选）

```sql
-- users 表删除为硬删除（DELETE），deleted 字段仅供软删除标记的历史遗留，当前代码路径不写入
CREATE TABLE users (
  id BIGINT PRIMARY KEY,
  nickname VARCHAR(255) NOT NULL,
  vip_expire_at DATETIME NULL,
  deleted TINYINT DEFAULT 0
);
CREATE TABLE user_profiles (          -- 用户公开资料（头像、简介），随账号创建
  user_id BIGINT PRIMARY KEY,
  avatar TEXT, bio TEXT
);
CREATE TABLE orders (                 -- 历史订单，user_id 外键
  id BIGINT PRIMARY KEY,
  user_id BIGINT NOT NULL,
  status VARCHAR(20)
);
```
