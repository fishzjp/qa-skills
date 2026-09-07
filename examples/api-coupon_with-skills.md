=== common/client.py ===
```python
import os
import requests

class Client:
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url.rstrip("/")
        self.s = requests.Session()
        self.s.headers.update({"Authorization": f"Bearer {token}"})

    def request(self, method: str, path: str, **kwargs):
        url = f"{self.base_url}/{path.lstrip('/')}"
        kwargs.setdefault("timeout", 10)
        return self.s.request(method, url, **kwargs)

    def get(self, path, **kw):
        return self.request("GET", path, **kw)
    def post(self, path, **kw):
        return self.request("POST", path, **kw)
    def put(self, path, **kw):
        return self.request("PUT", path, **kw)
    def delete(self, path, **kw):
        return self.request("DELETE", path, **kw)

def login(base_url: str, user: str, password: str) -> str:
    """登录获取 Bearer Token"""
    url = f"{base_url}/api/v1/auth/login"
    resp = requests.post(url, json={"username": user, "password": password}, timeout=10)
    resp.raise_for_status()
    return resp.json()["token"]
```

=== conftest.py ===
```python
import os
import pytest
import requests
from common.client import Client, login

@pytest.fixture(scope="session")
def client():
    base_url = os.environ["API_BASE_URL"]
    user = os.environ["API_USER"]
    password = os.environ["API_PASSWORD"]
    token = login(base_url, user, password)
    return Client(base_url, token)

@pytest.fixture(scope="session")
def coupon_base_id():
    id = os.environ.get("COUPON_BASE_ID")
    if not id:
        pytest.skip("COUPON_BASE_ID 环境变量未设置，跳过依赖预置数据的测试")
    return id

@pytest.fixture(scope="session")
def coupon_ended_id():
    id = os.environ.get("COUPON_ENDED_ID")
    if not id:
        pytest.skip("COUPON_ENDED_ID 环境变量未设置，跳过依赖预置数据的测试")
    return id
```

=== test_coupon_create.py ===
```python
import os
import pytest
import uuid
import requests
from common.client import Client

def unique_name():
    return f"test-{uuid.uuid4().hex[:12]}"

# 正常创建
def test_TC_05_01_001_create_success(client: Client):
    name = unique_name()
    resp = client.post("/api/v1/coupons", json={
        "name": name,
        "amount": 100,
        "threshold": 0,
        "total": 1000
    })
    assert resp.status_code == 201
    data = resp.json()
    assert "id" in data
    assert data["status"] == "待发布"

# 参数缺失（必填项）
@pytest.mark.parametrize("missing_field", ["name", "amount", "threshold", "total"])
def test_TC_05_01_002_missing_required_field(client: Client, missing_field):
    valid = {
        "name": unique_name(),
        "amount": 100,
        "threshold": 0,
        "total": 1000
    }
    del valid[missing_field]
    resp = client.post("/api/v1/coupons", json=valid)
    assert resp.status_code == 400

# 类型错误：amount 传字符串
def test_TC_05_01_003_amount_type_error(client: Client):
    resp = client.post("/api/v1/coupons", json={
        "name": unique_name(),
        "amount": "abc",
        "threshold": 0,
        "total": 1000
    })
    assert resp.status_code == 400

# 边界值：name 空字符串
def test_TC_05_01_004_name_empty(client: Client):
    resp = client.post("/api/v1/coupons", json={
        "name": "",
        "amount": 100,
        "threshold": 0,
        "total": 1000
    })
    assert resp.status_code == 400

# 边界值：name 纯空白
def test_TC_05_01_005_name_blank(client: Client):
    resp = client.post("/api/v1/coupons", json={
        "name": "   ",
        "amount": 100,
        "threshold": 0,
        "total": 1000
    })
    assert resp.status_code == 400

# 边界值：name 超长（21字符）
def test_TC_05_01_006_name_too_long(client: Client):
    resp = client.post("/api/v1/coupons", json={
        "name": "a" * 21,
        "amount": 100,
        "threshold": 0,
        "total": 1000
    })
    assert resp.status_code == 400

# 边界值：amount 最小值 1
def test_TC_05_01_007_amount_min(client: Client):
    resp = client.post("/api/v1/coupons", json={
        "name": unique_name(),
        "amount": 1,
        "threshold": 0,
        "total": 1000
    })
    assert resp.status_code == 201

# 边界值：amount 最大值 1000
def test_TC_05_01_008_amount_max(client: Client):
    resp = client.post("/api/v1/coupons", json={
        "name": unique_name(),
        "amount": 1000,
        "threshold": 0,
        "total": 1000
    })
    assert resp.status_code == 201

# 边界值：amount 0（无效）
def test_TC_05_01_009_amount_zero(client: Client):
    resp = client.post("/api/v1/coupons", json={
        "name": unique_name(),
        "amount": 0,
        "threshold": 0,
        "total": 1000
    })
    assert resp.status_code == 400

# 边界值：amount 负数
def test_TC_05_01_010_amount_negative(client: Client):
    resp = client.post("/api/v1/coupons", json={
        "name": unique_name(),
        "amount": -1,
        "threshold": 0,
        "total": 1000
    })
    assert resp.status_code == 400

# 边界值：amount 超过最大值
def test_TC_05_01_011_amount_exceed_max(client: Client):
    resp = client.post("/api/v1/coupons", json={
        "name": unique_name(),
        "amount": 1001,
        "threshold": 0,
        "total": 1000
    })
    assert resp.status_code == 400

# 边界值：threshold 最小值 0
def test_TC_05_01_012_threshold_min(client: Client):
    resp = client.post("/api/v1/coupons", json={
        "name": unique_name(),
        "amount": 100,
        "threshold": 0,
        "total": 1000
    })
    assert resp.status_code == 201

# 边界值：threshold 负数
def test_TC_05_01_013_threshold_negative(client: Client):
    resp = client.post("/api/v1/coupons", json={
        "name": unique_name(),
        "amount": 100,
        "threshold": -1,
        "total": 1000
    })
    assert resp.status_code == 400

# 边界值：total 最小值 1
def test_TC_05_01_014_total_min(client: Client):
    resp = client.post("/api/v1/coupons", json={
        "name": unique_name(),
        "amount": 100,
        "threshold": 0,
        "total": 1
    })
    assert resp.status_code == 201

# 边界值：total 最大值 100000
def test_TC_05_01_015_total_max(client: Client):
    resp = client.post("/api/v1/coupons", json={
        "name": unique_name(),
        "amount": 100,
        "threshold": 0,
        "total": 100000
    })
    assert resp.status_code == 201

# 边界值：total 0（无效）
def test_TC_05_01_016_total_zero(client: Client):
    resp = client.post("/api/v1/coupons", json={
        "name": unique_name(),
        "amount": 100,
        "threshold": 0,
        "total": 0
    })
    assert resp.status_code == 400

# 边界值：total 负数
def test_TC_05_01_017_total_negative(client: Client):
    resp = client.post("/api/v1/coupons", json={
        "name": unique_name(),
        "amount": 100,
        "threshold": 0,
        "total": -1
    })
    assert resp.status_code == 400

# 边界值：total 超过最大值
def test_TC_05_01_018_total_exceed_max(client: Client):
    resp = client.post("/api/v1/coupons", json={
        "name": unique_name(),
        "amount": 100,
        "threshold": 0,
        "total": 100001
    })
    assert resp.status_code == 400

# 唯一性：名称重复
def test_TC_05_01_019_name_duplicate(client: Client):
    name = unique_name()
    resp1 = client.post("/api/v1/coupons", json={
        "name": name,
        "amount": 100,
        "threshold": 0,
        "total": 1000
    })
    assert resp1.status_code == 201
    resp2 = client.post("/api/v1/coupons", json={
        "name": name,
        "amount": 200,
        "threshold": 0,
        "total": 2000
    })
    assert resp2.status_code == 400
    assert resp2.json().get("code") == "NAME_DUPLICATED"

# 门槛规则：threshold 非0且小于 amount
def test_TC_05_01_020_threshold_less_than_amount(client: Client):
    resp = client.post("/api/v1/coupons", json={
        "name": unique_name(),
        "amount": 100,
        "threshold": 50,
        "total": 1000
    })
    assert resp.status_code == 400
    assert resp.json().get("code") == "THRESHOLD_INVALID"

# 门槛规则：threshold 等于 amount（合法）
def test_TC_05_01_021_threshold_equal_amount(client: Client):
    resp = client.post("/api/v1/coupons", json={
        "name": unique_name(),
        "amount": 100,
        "threshold": 100,
        "total": 1000
    })
    assert resp.status_code == 201

# 门槛规则：threshold 大于 amount（合法）
def test_TC_05_01_022_threshold_greater_than_amount(client: Client):
    resp = client.post("/api/v1/coupons", json={
        "name": unique_name(),
        "amount": 100,
        "threshold": 150,
        "total": 1000
    })
    assert resp.status_code == 201

# 鉴权：无 Token
def test_TC_05_01_023_no_auth(client: Client):
    base_url = os.environ["API_BASE_URL"]
    resp = requests.post(
        f"{base_url}/api/v1/coupons",
        json={"name": unique_name(), "amount": 100, "threshold": 0, "total": 1000},
        timeout=10
    )
    assert resp.status_code == 401

# 鉴权：错误 Token
def test_TC_05_01_024_invalid_token(client: Client):
    base_url = os.environ["API_BASE_URL"]
    resp = requests.post(
        f"{base_url}/api/v1/coupons",
        json={"name": unique_name(), "amount": 100, "threshold": 0, "total": 1000},
        headers={"Authorization": "Bearer invalid_token"},
        timeout=10
    )
    assert resp.status_code == 401
```

=== test_coupon_publish.py ===
```python
import os
import pytest
import uuid
import requests
from common.client import Client

def unique_name():
    return f"test-{uuid.uuid4().hex[:12]}"

def create_pending_coupon(client: Client) -> str:
    name = unique_name()
    resp = client.post("/api/v1/coupons", json={
        "name": name,
        "amount": 100,
        "threshold": 0,
        "total": 1000
    })
    assert resp.status_code == 201
    return resp.json()["id"]

# 正常发布
def test_TC_05_02_001_publish_success(client: Client):
    coupon_id = create_pending_coupon(client)
    resp = client.post(f"/api/v1/coupons/{coupon_id}/publish")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "已发布"

# 幂等：重复发布
def test_TC_05_02_002_publish_idempotent(client: Client):
    coupon_id = create_pending_coupon(client)
    client.post(f"/api/v1/coupons/{coupon_id}/publish")
    resp = client.post(f"/api/v1/coupons/{coupon_id}/publish")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "已发布"

# 已结束券发布
def test_TC_05_02_003_publish_ended(client: Client, coupon_ended_id):
    resp = client.post(f"/api/v1/coupons/{coupon_ended_id}/publish")
    assert resp.status_code == 404

# 不存在的券发布
def test_TC_05_02_004_publish_not_found(client: Client):
    resp = client.post("/api/v1/coupons/999999999/publish")
    assert resp.status_code == 404

# 鉴权：无 Token
def test_TC_05_02_005_publish_no_auth(client: Client):
    coupon_id = create_pending_coupon(client)
    base_url = os.environ["API_BASE_URL"]
    resp = requests.post(
        f"{base_url}/api/v1/coupons/{coupon_id}/publish",
        timeout=10
    )
    assert resp.status_code == 401

# 鉴权：错误 Token
def test_TC_05_02_006_publish_invalid_token(client: Client):
    coupon_id = create_pending_coupon(client)
    base_url = os.environ["API_BASE_URL"]
    resp = requests.post(
        f"{base_url}/api/v1/coupons/{coupon_id}/publish",
        headers={"Authorization": "Bearer invalid_token"},
        timeout=10
    )
    assert resp.status_code == 401
```

=== test_coupon_claim.py ===
```python
import os
import pytest
import uuid
import requests
from common.client import Client

def unique_name():
    return f"test-{uuid.uuid4().hex[:12]}"

def create_and_publish_coupon(client: Client) -> str:
    name = unique_name()
    resp = client.post("/api/v1/coupons", json={
        "name": name,
        "amount": 100,
        "threshold": 0,
        "total": 1000
    })
    assert resp.status_code == 201
    coupon_id = resp.json()["id"]
    pub_resp = client.post(f"/api/v1/coupons/{coupon_id}/publish")
    assert pub_resp.status_code == 200
    return coupon_id

# 正常领取
def test_TC_05_03_001_claim_success(client: Client):
    coupon_id = create_and_publish_coupon(client)
    resp = client.post(f"/api/v1/coupons/{coupon_id}/claim")
    assert resp.status_code == 200
    data = resp.json()
    assert "user_coupon_id" in data

# 重复领取到上限（每人限领3张）
def test_TC_05_03_002_claim_exceed_limit(client: Client):
    coupon_id = create_and_publish_coupon(client)
    for _ in range(3):
        resp = client.post(f"/api/v1/coupons/{coupon_id}/claim")
        assert resp.status_code == 200
    resp = client.post(f"/api/v1/coupons/{coupon_id}/claim")
    assert resp.status_code == 409

# 已结束券领取
def test_TC_05_03_003_claim_ended(client: Client, coupon_ended_id):
    resp = client.post(f"/api/v1/coupons/{coupon_ended_id}/claim")
    assert resp.status_code == 404

# 未发布券领取
def test_TC_05_03_004_claim_unpublished(client: Client):
    name = unique_name()
    create_resp = client.post("/api/v1/coupons", json={
        "name": name,
        "amount": 100,
        "threshold": 0,
        "total": 1000
    })
    assert create_resp.status_code == 201
    coupon_id = create_resp.json()["id"]
    resp = client.post(f"/api/v1/coupons/{coupon_id}/claim")
    assert resp.status_code == 404

# 不存在的券领取
def test_TC_05_03_005_claim_not_found(client: Client):
    resp = client.post("/api/v1/coupons/999999999/claim")
    assert resp.status_code == 404

# 鉴权：无 Token
def test_TC_05_03_006_claim_no_auth(client: Client):
    coupon_id = create_and_publish_coupon(client)
    base_url = os.environ["API_BASE_URL"]
    resp = requests.post(
        f"{base_url}/api/v1/coupons/{coupon_id}/claim",
        timeout=10
    )
    assert resp.status_code == 401

# 鉴权：错误 Token
def test_TC_05_03_007_claim_invalid_token(client: Client):
    coupon_id = create_and_publish_coupon(client)
    base_url = os.environ["API_BASE_URL"]
    resp = requests.post(
        f"{base_url}/api/v1/coupons/{coupon_id}/claim",
        headers={"Authorization": "Bearer invalid_token"},
        timeout=10
    )
    assert resp.status_code == 401
```

=== common/__init__.py ===
```python
# 空文件，标记 common 为包
```