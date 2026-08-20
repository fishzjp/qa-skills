```
api-tests/
├── requirements.txt
├── common/
│   ├── __init__.py
│   └── client.py
├── conftest.py
├── test_coupon_create.py
└── test_coupon_claim.py
```

---

### 文件: `api-tests/requirements.txt`

```text
pytest>=7.0
requests>=2.28
```

---

### 文件: `api-tests/common/__init__.py`

```python
```

---

### 文件: `api-tests/common/client.py`

```python
"""统一请求封装：日志、超时、鉴权头。"""

import logging
from typing import Optional

import requests

logger = logging.getLogger(__name__)


class APIClient:
    """封装 HTTP 请求，统一鉴权头与超时。"""

    DEFAULT_TIMEOUT = 10

    def __init__(self, base_url: str, token: Optional[str] = None):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        if token:
            self.session.headers.update({"Authorization": f"Bearer {token}"})

    def _request(self, method: str, path: str, **kwargs) -> requests.Response:
        url = f"{self.base_url}{path}"
        kwargs.setdefault("timeout", self.DEFAULT_TIMEOUT)
        logger.info("%s %s | kwargs=%s", method, url, kwargs)
        resp = self.session.request(method, url, **kwargs)
        logger.info("Response: %s | body=%s", resp.status_code, resp.text[:500])
        return resp

    # ---- 优惠券接口 ----

    def create_coupon(self, payload: dict) -> requests.Response:
        return self._request("POST", "/api/v1/coupons", json=payload)

    def claim_coupon(self, coupon_id: str) -> requests.Response:
        return self._request("POST", f"/api/v1/coupons/{coupon_id}/claim")

    def publish_coupon(self, coupon_id: str) -> requests.Response:
        """发布优惠券（假设接口存在，见待澄清 #1）。"""
        return self._request("POST", f"/api/v1/coupons/{coupon_id}/publish")

    def delete_coupon(self, coupon_id: str) -> requests.Response:
        """删除优惠券（假设接口存在，见待澄清 #2）。"""
        return self._request("DELETE", f"/api/v1/coupons/{coupon_id}")

    def get_user_coupons(self) -> requests.Response:
        """查询当前用户已领取的优惠券列表（假设接口存在，见待澄清 #3）。"""
        return self._request("GET", "/api/v1/user/coupons")
```

---

### 文件: `api-tests/conftest.py`

```python
"""pytest 全局 fixture：环境配置、鉴权 Token、测试数据工厂。"""

import os
import uuid

import pytest
import requests

from common.client import APIClient


def login(base_url: str, user: str, password: str) -> str:
    """登录获取 Bearer Token（假设登录接口路径，见待澄清 #5）。"""
    resp = requests.post(
        f"{base_url}/api/v1/auth/login",
        json={"username": user, "password": password},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()["token"]


# ---- Session 级 fixture ----

@pytest.fixture(scope="session")
def base_url() -> str:
    return os.environ["API_BASE_URL"]


@pytest.fixture(scope="session")
def auth_token(base_url: str) -> str:
    return login(base_url, os.environ["API_USER"], os.environ["API_PASSWORD"])


@pytest.fixture(scope="session")
def client(base_url, auth_token) -> APIClient:
    return APIClient(base_url=base_url, token=auth_token)


@pytest.fixture(scope="session")
def no_auth_client(base_url) -> APIClient:
    """无鉴权 client，用于 401 测试。"""
    return APIClient(base_url=base_url, token=None)


@pytest.fixture(scope="session")
def expired_token_client(base_url) -> APIClient:
    """过期 Token client。"""
    return APIClient(base_url=base_url, token="expired.token.placeholder")


@pytest.fixture(scope="session")
def invalid_token_client(base_url) -> APIClient:
    """错误 Token client。"""
    return APIClient(base_url=base_url, token="invalid_token_abc123")


# ---- Function 级 fixture ----

@pytest.fixture
def unique_name() -> str:
    """生成唯一优惠券名称（<= 12 字符，为特殊字符留余量）。"""
    return f"c{uuid.uuid4().hex[:11]}"


@pytest.fixture
def created_coupon_id(client, unique_name):
    """创建一张待发布优惠券，返回 id；测试后自动清理。"""
    payload = {
        "name": unique_name,
        "amount": 10,
        "threshold": 0,
        "total": 100,
    }
    resp = client.create_coupon(payload)
    assert resp.status_code == 201, f"setup: 创建券失败: {resp.text}"
    coupon_id = resp.json()["id"]
    yield coupon_id
    try:
        client.delete_coupon(coupon_id)
    except Exception:
        pass


@pytest.fixture
def published_coupon_id(client, unique_name):
    """创建并发布一张优惠券，返回 id；测试后自动清理。"""
    payload = {
        "name": unique_name,
        "amount": 10,
        "threshold": 0,
        "total": 100,
    }
    resp = client.create_coupon(payload)
    assert resp.status_code == 201, f"setup: 创建券失败: {resp.text}"
    coupon_id = resp.json()["id"]
    pub_resp = client.publish_coupon(coupon_id)
    assert pub_resp.status_code in (200, 204), f"setup: 发布券失败: {pub_resp.text}"
    yield coupon_id
    try:
        client.delete_coupon(coupon_id)
    except Exception:
        pass
```

---

### 文件: `api-tests/test_coupon_create.py`

```python
"""
创建优惠券接口测试
POST /api/v1/coupons

覆盖维度：
- 正常创建（各参数边界正常值、特殊字符）
- 必填参数缺失（逐字段 + 全缺失）
- 类型错误（逐字段）
- 边界值（空 / 最小 / 最小-1 / 最大 / 最大+1 / 超大）
- 业务规则（名称同商户唯一、门槛≥面额）
- 鉴权（无 Token / 过期 Token / 错误 Token）
- 拦截后重试恢复
"""

import uuid

import pytest


def make_unique_name() -> str:
    """生成唯一名称（<= 12 字符）。"""
    return f"c{uuid.uuid4().hex[:11]}"


# ========== 正常用例 ==========

class TestCreateCouponSuccess:
    """创建优惠券 - 正常场景。"""

    def test_TC_CREATE_01_正常创建返回201和待发布状态(self, client, unique_name):
        """正常创建优惠券，返回 201，body 含 id 和 status=待发布。"""
        payload = {
            "name": unique_name,
            "amount": 100,
            "threshold": 100,
            "total": 1000,
        }
        resp = client.create_coupon(payload)
        assert resp.status_code == 201
        body = resp.json()
        assert "id" in body
        assert body["status"] == "待发布"
        client.delete_coupon(body["id"])

    def test_TC_CREATE_02_name为20字符创建成功(self, client):
        """name 为 maxLength=20 字符，创建成功。"""
        name = "c" * 20
        payload = {"name": name, "amount": 10, "threshold": 0, "total": 100}
        resp = client.create_coupon(payload)
        assert resp.status_code == 201
        assert "id" in resp.json()
        client.delete_coupon(resp.json()["id"])

    def test_TC_CREATE_03_amount为最小值1创建成功(self, client, unique_name):
        """amount=1（minimum），创建成功。"""
        payload = {"name": unique_name, "amount": 1, "threshold": 0, "total": 100}
        resp = client.create_coupon(payload)
        assert resp.status_code == 201
        assert "id" in resp.json()
        client.delete_coupon(resp.json()["id"])

    def test_TC_CREATE_04_amount为最大值1000创建成功(self, client, unique_name):
        """amount=1000（maximum），创建成功。"""
        payload = {"name": unique_name, "amount": 1000, "threshold": 1000, "total": 100}
        resp = client.create_coupon(payload)
        assert resp.status_code == 201
        assert "id" in resp.json()
        client.delete_coupon(resp.json()["id"])

    def test_TC_CREATE_05_threshold为0创建成功(self, client, unique_name):
        """threshold=0（minimum），创建成功。"""
        payload = {"name": unique_name, "amount": 10, "threshold": 0, "total": 100}
        resp = client.create_coupon(payload)
        assert resp.status_code == 201
        assert "id" in resp.json()
        client.delete_coupon(resp.json()["id"])

    def test_TC_CREATE_06_threshold等于amount创建成功(self, client, unique_name):
        """threshold 等于 amount（门槛≥面额边界），创建成功。"""
        payload = {"name": unique_name, "amount": 100, "threshold": 100, "total": 100}
        resp = client.create_coupon(payload)
        assert resp.status_code == 201
        assert "id" in resp.json()
        client.delete_coupon(resp.json()["id"])

    def test_TC_CREATE_07_total为最小值1创建成功(self, client, unique_name):
        """total=1（minimum），创建成功。"""
        payload = {"name": unique_name, "amount": 10, "threshold": 0, "total": 1}
        resp = client.create_coupon(payload)
        assert resp.status_code == 201
        assert "id" in resp.json()
        client.delete_coupon(resp.json()["id"])

    def test_TC_CREATE_08_total为最大值100000创建成功(self, client, unique_name):
        """total=100000（maximum），创建成功。"""
        payload = {"name": unique_name, "amount": 10, "threshold": 0, "total": 100000}
        resp = client.create_coupon(payload)
        assert resp.status_code == 201
        assert "id" in resp.json()
        client.delete_coupon(resp.json()["id"])

    def test_TC_CREATE_09_name含特殊字符创建成功(self, client):
        """name 含特殊字符（引号、尖括号），创建成功且读回一致。"""
        name = f'{make_unique_name()}"<>'
        payload = {"name": name, "amount": 10, "threshold": 0, "total": 100}
        resp = client.create_coupon(payload)
        assert resp.status_code == 201
        assert resp.json()["name"] == name
        client.delete_coupon(resp.json()["id"])

    def test_TC_CREATE_10_name含emoji创建成功(self, client):
        """name 含 emoji，创建成功且读回一致。"""
        name = f"{make_unique_name()}🎉"
        payload = {"name": name, "amount": 10, "threshold": 0, "total": 100}
        resp = client.create_coupon(payload)
        assert resp.status_code == 201
        assert resp.json()["name"] == name
        client.delete_coupon(resp.json()["id"])


# ========== 必填参数缺失 ==========

class TestCreateCouponMissingField:
    """创建优惠券 - 必填参数缺失。"""

    def test_TC_CREATE_11_缺少name返回400(self, client, unique_name):
        """缺少必填字段 name，返回 400，body 含 code 和 message。"""
        payload = {"amount": 10, "threshold": 0, "total": 100}
        resp = client.create_coupon(payload)
        assert resp.status_code == 400
        body = resp.json()
        assert "code" in body
        assert "message" in body

    def test_TC_CREATE_12_缺少amount返回400(self, client, unique_name):
        """缺少必填字段 amount，返回 400。"""
        payload = {"name": unique_name, "threshold": 0, "total": 100}
        resp = client.create_coupon(payload)
        assert resp.status_code == 400
        body = resp.json()
        assert "code" in body
        assert "message" in body

    def test_TC_CREATE_13_缺少threshold返回400(self, client, unique_name):
        """缺少必填字段 threshold，返回 400。"""
        payload = {"name": unique_name, "amount": 10, "total": 100}
        resp = client.create_coupon(payload)
        assert resp.status_code == 400
        body = resp.json()
        assert "code" in body
        assert "message" in body

    def test_TC_CREATE_14_缺少total返回400(self, client, unique_name):
        """缺少必填字段 total，返回 400。"""
        payload = {"name": unique_name, "amount": 10, "threshold": 0}
        resp = client.create_coupon(payload)
        assert resp.status_code == 400
        body = resp.json()
        assert "code" in body
        assert "message" in body

    def test_TC_CREATE_15_请求体为空返回400(self, client):
        """请求体为空对象（全部必填缺失），返回 400。"""
        resp = client.create_coupon({})
        assert resp.status_code == 400
        body = resp.json()
        assert "code" in body
        assert "message" in body


# ========== 类型错误 ==========

class TestCreateCouponTypeError:
    """创建优惠券 - 类型错误。"""

    def test_TC_CREATE_16_name为整数类型返回400(self, client):
        """name 传整数类型，返回 400。"""
        payload = {"name": 12345, "amount": 10, "threshold": 0, "total": 100}
        resp = client.create_coupon(payload)
        assert resp.status_code == 400

    def test_TC_CREATE_17_amount为字符串返回400(self, client, unique_name):
        """amount 传字符串 "100"，返回 400。"""
        payload = {"name": unique_name, "amount": "100", "threshold": 0, "total": 100}
        resp = client.create_coupon(payload)
        assert resp.status_code == 400

    def test_TC_CREATE_18_amount为小数返回400(self, client, unique_name):
        """amount 传小数 10.5（非整数），返回 400。"""
        payload = {"name": unique_name, "amount": 10.5, "threshold": 0, "total": 100}
        resp = client.create_coupon(payload)
        assert resp.status_code == 400

    def test_TC_CREATE_19_threshold为字符串返回400(self, client, unique_name):
        """threshold 传字符串 "0"，返回 400。"""
        payload = {"name": unique_name, "amount": 10, "threshold": "0", "total": 100}
        resp = client.create_coupon(payload)
        assert resp.status_code == 400

    def test_TC_CREATE_20_total为字符串返回400(self, client, unique_name):
        """total 传字符串 "100"，返回 400。"""
        payload = {"name": unique_name, "amount": 10, "threshold": 0, "total": "100"}
        resp = client.create_coupon(payload)
        assert resp.status_code == 400

    def test_TC_CREATE_21_total为小数返回400(self, client, unique_name):
        """total 传小数 100.5（非整数），返回 400。"""
        payload = {"name": unique_name, "amount": 10, "threshold": 0, "total": 100.5}
        resp = client.create_coupon(payload)
        assert resp.status_code == 400


# ========== 边界值 ==========

class TestCreateCouponBoundary:
    """创建优惠券 - 边界值（逐值一条）。"""

    # ---- name 边界 ----

    def test_TC_CREATE_22_name为空串返回400(self, client):
        """name 为空字符串，返回 400。"""
        payload = {"name": "", "amount": 10, "threshold": 0, "total": 100}
        resp = client.create_coupon(payload)
        assert resp.status_code == 400

    def test_TC_CREATE_23_name为21字符返回400(self, client):
        """name 为 21 字符（超过 maxLength=20），返回 400。"""
        name = "c" * 21
        payload = {"name": name, "amount": 10, "threshold": 0, "total": 100}
        resp = client.create_coupon(payload)
        assert resp.status_code == 400

    def test_TC_CREATE_24_name为纯空格返回400(self, client):
        """name 为纯空格，返回 400（见待澄清 #9）。"""
        payload = {"name": "   ", "amount": 10, "threshold": 0, "total": 100}
        resp = client.create_coupon(payload)
        assert resp.status_code == 400

    # ---- amount 边界 ----

    def test_TC_CREATE_25_amount为0返回400(self, client, unique_name):
        """amount=0（minimum-1），返回 400。"""
        payload = {"name": unique_name, "amount": 0, "threshold": 0, "total": 100}
        resp = client.create_coupon(payload)
        assert resp.status_code == 400

    def test_TC_CREATE_26_amount为负数返回400(self, client, unique_name):
        """amount=-1，返回 400。"""
        payload = {"name": unique_name, "amount": -1, "threshold": 0, "total": 100}
        resp = client.create_coupon(payload)
        assert resp.status_code == 400

    def test_TC_CREATE_27_amount为1001返回400(self, client, unique_name):
        """amount=1001（maximum+1），返回 400。"""
        payload = {"name": unique_name, "amount": 1001, "threshold": 1001, "total": 100}
        resp = client.create_coupon(payload)
        assert resp.status_code == 400

    def test_TC_CREATE_28_amount为超大数返回400(self, client, unique_name):
        """amount=10**10（超大值），返回 400。"""
        payload = {"name": unique_name, "amount": 10**10, "threshold": 10**10, "total": 100}
        resp = client.create_coupon(payload)
        assert resp.status_code == 400

    # ---- threshold 边界 ----

    def test_TC_CREATE_29_threshold为负数返回400(self, client, unique_name):
        """threshold=-1（minimum-1），返回 400。"""
        payload = {"name": unique_name, "amount": 10, "threshold": -1, "total": 100}
        resp = client.create_coupon(payload)
        assert resp.status_code == 400

    # ---- total 边界 ----

    def test_TC_CREATE_30_total为0返回400(self, client, unique_name):
        """total=0（minimum-1），返回 400。"""
        payload = {"name": unique_name, "amount": 10, "threshold": 0, "total": 0}
        resp = client.create_coupon(payload)
        assert resp.status_code == 400

    def test_TC_CREATE_31_total为负数返回400(self, client, unique_name):
        """total=-1，返回 400。"""
        payload = {"name": unique_name, "amount": 10, "threshold": 0, "total": -1}
        resp = client.create_coupon(payload)
        assert resp.status_code == 400

    def test_TC_CREATE_32_total为100001返回400(self, client, unique_name):
        """total=100001（maximum+1），返回 400。"""
        payload = {"name": unique_name, "amount": 10, "threshold": 0, "total": 100001}
        resp = client.create_coupon(payload)
        assert resp.status_code == 400

    def test_TC_CREATE_33_total为超大数返回400(self, client, unique_name):
        """total=10**10（超大值），返回 400。"""
        payload = {"name": unique_name, "amount": 10, "threshold": 0, "total": 10**10}
        resp = client.create_coupon(payload)
        assert resp.status_code == 400


# ========== 业务规则 ==========

class TestCreateCouponBusinessRule:
    """创建优惠券 - 业务规则。"""

    def test_TC_CREATE_34_门槛非0且小于面额返回THRESHOLD_INVALID(self, client, unique_name):
        """threshold 非 0 且 < amount，返回 400，code=THRESHOLD_INVALID。"""
        payload = {"name": unique_name, "amount": 100, "threshold": 50, "total": 100}
        resp = client.create_coupon(payload)
        assert resp.status_code == 400
        body = resp.json()
        assert body["code"] == "THRESHOLD_INVALID"
        assert "message" in body

    def test_TC_CREATE_35_门槛为0时不受面额约束(self, client, unique_name):
        """threshold=0 时不受 threshold≥amount 约束，amount=100 创建成功。"""
        payload = {"name": unique_name, "amount": 100, "threshold": 0, "total": 100}
        resp = client.create_coupon(payload)
        assert resp.status_code == 201
        client.delete_coupon(resp.json()["id"])

    def test_TC_CREATE_36_名称同商户重复返回NAME_DUPLICATED(self, client, unique_name):
        """同一商户下名称重复，第二次创建返回 400，code=NAME_DUPLICATED。"""
        payload = {"name": unique_name, "amount": 10, "threshold": 0, "total": 100}
        # 第一次创建成功
        resp1 = client.create_coupon(payload)
        assert resp1.status_code == 201
        coupon_id = resp1.json()["id"]
        try:
            # 第二次同名创建
            resp2 = client.create_coupon(payload)
            assert resp2.status_code == 400
            body = resp2.json()
            assert body["code"] == "NAME_DUPLICATED"
            assert "message" in body
        finally:
            client.delete_coupon(coupon_id)


# ========== 鉴权 ==========

class TestCreateCouponAuth:
    """创建优惠券 - 鉴权。"""

    def test_TC_CREATE_37_无Token返回401(self, no_auth_client):
        """未携带 Authorization 头，返回 401。"""
        payload = {"name": "no_auth_test", "amount": 10, "threshold": 0, "total": 100}
        resp = no_auth_client.create_coupon(payload)
        assert resp.status_code == 401

    def test_TC_CREATE_38_过期Token返回401(self, expired_token_client):
        """携带过期 Token，返回 401。"""
        payload = {"name": "expired_test", "amount": 10, "threshold": 0, "total": 100}
        resp = expired_token_client.create_coupon(payload)
        assert resp.status_code == 401

    def test_TC_CREATE_39_错误Token返回401(self, invalid_token_client):
        """携带错误 Token，返回 401。"""
        payload = {"name": "invalid_test", "amount": 10, "threshold": 0, "total": 100}
        resp = invalid_token_client.create_coupon(payload)
        assert resp.status_code == 401


# ========== 拦截后重试恢复 ==========

class TestCreateCouponRetryRecovery:
    """创建优惠券 - 拦截后修正重提恢复。"""

    def test_TC_CREATE_40_name超长拦截后修正重提创建成功(self, client, unique_name):
        """name 超长被 400 拦截后，修改为合法长度重提，创建成功。"""
        # 第一次：name 超长，被拦截
        payload = {"name": "c" * 21, "amount": 10, "threshold": 0, "total": 100}
        resp1 = client.create_coupon(payload)
        assert resp1.status_code == 400
        # 第二次：修正为合法 name，创建成功
        payload["name"] = unique_name
        resp2 = client.create_coupon(payload)
        assert resp2.status_code == 201
        assert "id" in resp2.json()
        client.delete_coupon(resp2.json()["id"])

    def test_TC_CREATE_41_门槛非法拦截后修正重提创建成功(self, client, unique_name):
        """threshold < amount 被拦截后，修正 threshold 重提，创建成功。"""
        # 第一次：threshold < amount 且非 0，被拦截
        payload = {"name": unique_name, "amount": 100, "threshold": 50, "total": 100}
        resp1 = client.create_coupon(payload)
        assert resp1.status_code == 400
        assert resp1.json()["code"] == "THRESHOLD_INVALID"
        # 第二次：修正 threshold=0，创建成功
        payload["threshold"] = 0
        resp2 = client.create_coupon(payload)
        assert resp2.status_code == 201
        client.delete_coupon(resp2.json()["id"])
```

---

### 文件: `api-tests/test_coupon_claim.py`

```python
"""
领取优惠券接口测试
POST /api/v1/coupons/{id}/claim

覆盖维度：
- 正常领取（含限领上限内第 3 张）
- 参数（不存在的 id、待发布状态券）
- 鉴权（无 Token / 过期 Token / 错误 Token）
- 重复领取（同一张券到上限后 409）
- 并发领取（不超领）
- 数据一致性（领取后用户券列表包含已领取的券）
- 超领后恢复（领取其他券仍成功）
"""

import threading

import pytest
import requests as req_lib


# ========== 正常用例 ==========

class TestClaimCouponSuccess:
    """领取优惠券 - 正常场景。"""

    def test_TC_CLAIM_01_正常领取已发布券返回200和user_coupon_id(self, client, published_coupon_id):
        """正常领取已发布券，返回 200，body 含 user_coupon_id。"""
        resp = client.claim_coupon(published_coupon_id)
        assert resp.status_code == 200
        body = resp.json()
        assert "user_coupon_id" in body

    def test_TC_CLAIM_02_领取第三张在上限内返回200(self, client, unique_name):
        """同一张券领取第 3 次（每人限领 3 张，上限内），返回 200。"""
        payload = {"name": unique_name, "amount": 10, "threshold": 0, "total": 100}
        resp = client.create_coupon(payload)
        assert resp.status_code == 201
        coupon_id = resp.json()["id"]
        client.publish_coupon(coupon_id)
        try:
            for i in range(3):
                r = client.claim_coupon(coupon_id)
                assert r.status_code == 200, (
                    f"第 {i + 1} 次领取应返回 200，实际 {r.status_code}: {r.text}"
                )
                assert "user_coupon_id" in r.json()
        finally:
            client.delete_coupon(coupon_id)


# ========== 参数 ==========

class TestClaimCouponParam:
    """领取优惠券 - 参数校验。"""

    def test_TC_CLAIM_03_不存在的券id返回404(self, client):
        """领取不存在的券 id，返回 404。"""
        resp = client.claim_coupon("non_existent_id_000")
        assert resp.status_code == 404

    def test_TC_CLAIM_04_待发布状态的券领取返回404(self, client, created_coupon_id):
        """领取待发布状态的券（创建后默认待发布），返回 404。"""
        resp = client.claim_coupon(created_coupon_id)
        assert resp.status_code == 404


# ========== 鉴权 ==========

class TestClaimCouponAuth:
    """领取优惠券 - 鉴权。"""

    def test_TC_CLAIM_05_无Token返回401(self, no_auth_client, published_coupon_id):
        """未携带 Authorization 头，返回 401。"""
        resp = no_auth_client.claim_coupon(published_coupon_id)
        assert resp.status_code == 401

    def test_TC_CLAIM_06_过期Token返回401(self, expired_token_client, published_coupon_id):
        """携带过期 Token，返回 401。"""
        resp = expired_token_client.claim_coupon(published_coupon_id)
        assert resp.status_code == 401

    def test_TC_CLAIM_07_错误Token返回401(self, invalid_token_client, published_coupon_id):
        """携带错误 Token，返回 401。"""
        resp = invalid_token_client.claim_coupon(published_coupon_id)
        assert resp.status_code == 401


# ========== 重复领取 / 幂等 ==========

class TestClaimCouponDuplicate:
    """领取优惠券 - 重复领取。"""

    def test_TC_CLAIM_08_重复领取到上限后返回409(self, client, unique_name):
        """同一张券重复领取 3 次后，第 4 次返回 409。"""
        payload = {"name": unique_name, "amount": 10, "threshold": 0, "total": 100}
        resp = client.create_coupon(payload)
        assert resp.status_code == 201
        coupon_id = resp.json()["id"]
        client.publish_coupon(coupon_id)
        try:
            # 前 3 次都应成功
            for i in range(3):
                r = client.claim_coupon(coupon_id)
                assert r.status_code == 200, f"第 {i + 1} 次应返回 200"
            # 第 4 次应返回 409
            resp = client.claim_coupon(coupon_id)
            assert resp.status_code == 409
        finally:
            client.delete_coupon(coupon_id)


# ========== 并发 ==========

class TestClaimCouponConcurrent:
    """领取优惠券 - 并发。"""

    def test_TC_CLAIM_09_并发领取同一张券不超领(self, client, base_url, auth_token, unique_name):
        """4 个并发请求同时领取同一张券（每人限领 3 张），最多 3 个 200，至少 1 个 409。"""
        payload = {"name": unique_name, "amount": 10, "threshold": 0, "total": 100}
        resp = client.create_coupon(payload)
        assert resp.status_code == 201
        coupon_id = resp.json()["id"]
        client.publish_coupon(coupon_id)
        try:
            results = []
            lock = threading.Lock()
            headers = {"Authorization": f"Bearer {auth_token}"}
            url = f"{base_url}/api/v1/coupons/{coupon_id}/claim"

            def claim():
                r = req_lib.post(url, headers=headers, timeout=10)
                with lock:
                    results.append(r.status_code)

            threads = [threading.Thread(target=claim) for _ in range(4)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            success_count = results.count(200)
            conflict_count = results.count(409)
            assert success_count <= 3, (
                f"并发领取不应超过限领 3 张，实际成功 {success_count} 次，结果: {results}"
            )
            assert success_count + conflict_count == 4, (
                f"所有请求应有明确结果（200 或 409），实际: {results}"
            )
        finally:
            client.delete_coupon(coupon_id)


# ========== 数据一致性 ==========

class TestClaimCouponConsistency:
    """领取优惠券 - 数据一致性。"""

    def test_TC_CLAIM_10_领取后用户券列表包含该券(self, client, published_coupon_id):
        """领取后查询用户优惠券列表，包含已领取的 user_coupon_id。"""
        resp = client.claim_coupon(published_coupon_id)
        assert resp.status_code == 200
        user_coupon_id = resp.json()["user_coupon_id"]

        list_resp = client.get_user_coupons()
        assert list_resp.status_code == 200
        items = list_resp.json().get("items", [])
        coupon_ids = [item.get("user_coupon_id") for item in items]
        assert user_coupon_id in coupon_ids, (
            f"领取后用户券列表应包含 user_coupon_id={user_coupon_id}，"
            f"实际列表: {coupon_ids}"
        )


# ========== 超领后恢复 ==========

class TestClaimCouponRecovery:
    """领取优惠券 - 超领后恢复。"""

    def test_TC_CLAIM_11_超领409后领取其他券仍成功(self, client, unique_name):
        """某券超领返回 409 后，领取另一张已发布券仍返回 200。"""
        # 创建并发布两张券
        payloads = [
            {"name": f"{unique_name}_a", "amount": 10, "threshold": 0, "total": 100},
            {"name": f"{unique_name}_b", "amount": 10, "threshold": 0, "total": 100},
        ]
        coupon_ids = []
        try:
            for p in payloads:
                r = client.create_coupon(p)
                assert r.status_code == 201
                cid = r.json()["id"]
                client.publish_coupon(cid)
                coupon_ids.append(cid)

            # 第一张券领满 3 次
            for _ in range(3):
                client.claim_coupon(coupon_ids[0])
            # 第 4 次超领
            over_resp = client.claim_coupon(coupon_ids[0])
            assert over_resp.status_code == 409
            # 领取第二张券，应成功
            resp = client.claim_coupon(coupon_ids[1])
            assert resp.status_code == 200
            assert "user_coupon_id" in resp.json()
        finally:
            for cid in coupon_ids:
                try:
                    client.delete_coupon(cid)
                except Exception:
                    pass
```

---

## 运行方式

```bash
# 全量运行
export API_BASE_URL=https://api.example.test
export API_USER=your_user
export API_PASSWORD=your_password
pytest api-tests/ -v --tb=short

# 单文件运行
pytest api-tests/test_coupon_create.py -v --tb=short
pytest api-tests/test_coupon_claim.py -v --tb=short
```

## 用例统计

| 文件 | 用例数 | 覆盖维度 |
|------|--------|---------|
| test_coupon_create.py | 41 | 正常创建(10) / 必填缺失(5) / 类型错误(6) / 边界值(12) / 业务规则(3) / 鉴权(3) / 拦截后重试恢复(2) |
| test_coupon_claim.py | 11 | 正常领取(2) / 参数校验(2) / 鉴权(3) / 重复领取(1) / 并发(1) / 数据一致性(1) / 超领后恢复(1) |
| **合计** | **52** | — |

---

## 待澄清清单

1. **发布券接口缺失**：OpenAPI 文档未提供 `POST /api/v1/coupons/{id}/publish` 的定义，脚本中假设该接口存在且返回 200/204 用于将券从「待发布」切换到「已发布」。如发布路径不同或需其他参数，需提供接口文档。

2. **删除券接口缺失**：文档未提供删除优惠券接口，脚本中假设 `DELETE /api/v1/coupons/{id}` 存在，用于测试数据 teardown 清理。如接口不存在或路径不同，需提供信息。

3. **用户券列表查询接口缺失**：TC_CLAIM_10 数据一致性用例需要查询当前用户已领取的优惠券列表，假设接口为 `GET /api/v1/user/coupons`，返回 `{ "items": [ { "user_coupon_id": "..." }, ... ] }`。如路径或响应结构不同，需提供接口文档。

4. **"每人限领 3 张"的口径**：业务规则中「每人限领 3 张」是指同一张券每人限领 3 张，还是每个用户所有券合计限领 3 张？脚本按**同一张券每人限领 3 张**设计。如为后者，需调整 TC_CLAIM_02/08/09 的预期。

5. **登录接口路径与响应结构**：文档未提供登录接口，脚本假设 `POST /api/v1/auth/login`，请求体 `{ "username", "password" }`，响应体 `{ "token": "..." }`。如不同需提供信息。

6. **401/404/409 响应体结构**：OpenAPI 文档仅给出状态码描述，未定义响应体 Schema。脚本中 401/404/409 仅断言状态码，未断言业务码与响应体字段。如这些错误有标准化响应体（如 `{ "code": "...", "message": "..." }`），需提供结构以便补充断言。

7. **name 同商户唯一中「商户」的确定方式**：创建接口无商户 ID 参数，商户身份是否从 Token 中解析？如果是，同一测试账号创建的所有券属于同一商户，名称唯一性约束会跨用例生效。脚本通过 UUID 生成唯一名称规避此问题。

8. **多用户越权测试**：领取接口是否需要测试「用户 A 领取用户 B 私有券」的越权场景？当前环境仅提供一个测试账号（`API_USER` / `API_PASSWORD`）。如需越权测试，需提供第二个账号或说明券是否对所有用户公开可见。

9. **name 纯空格的校验行为**：TC_CREATE_24 假设 name 为纯空格时返回 400。如服务端仅校验 maxLength 不做 trim，可能返回 201。需确认服务端是否对 name 做 trim。

10. **amount 传小数的服务端行为**：TC_CREATE_18 假设 amount=10.5 返回 400。如服务端做隐式类型转换（向下取整为 10 并创建成功），需调整预期。

11. **券发布后的状态值**：创建返回 `status=待发布`，发布后的状态值是「已发布」还是其他？领取接口要求「券状态非已发布返回 404」，脚本假设发布后 status 变为「已发布」，需确认。