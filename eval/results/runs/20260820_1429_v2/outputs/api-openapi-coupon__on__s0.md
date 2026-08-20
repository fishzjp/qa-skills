```
api-tests/
├── common/
│   ├── __init__.py
│   └── client.py
├── conftest.py
├── requirements.txt
├── test_coupon_create.py
└── test_coupon_claim.py
```

---

### 文件：`api-tests/requirements.txt`

```text
pytest>=7.0
requests>=2.28
```

---

### 文件：`api-tests/common/__init__.py`

```python
```

---

### 文件：`api-tests/common/client.py`

```python
"""统一 API 客户端：封装鉴权头、超时、请求日志。"""

import logging

import requests

logger = logging.getLogger(__name__)


class APIClient:
    def __init__(self, base_url, timeout=15):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()

    # ---------- 鉴权 ----------

    def login(self, username, password):
        """登录获取 Bearer Token（假设 POST /api/v1/auth/login 返回 {"token": "..."}）。"""
        url = f"{self.base_url}/api/v1/auth/login"
        logger.info("POST %s", url)
        resp = self.session.post(
            url,
            json={"username": username, "password": password},
            timeout=self.timeout,
        )
        logger.info("login status=%s body=%s", resp.status_code, resp.text[:500])
        token = resp.json().get("token")
        if token:
            self.session.headers.update({"Authorization": f"Bearer {token}"})
        return resp

    def set_token(self, token):
        self.session.headers.update({"Authorization": f"Bearer {token}"})

    def clear_auth(self):
        self.session.headers.pop("Authorization", None)

    # ---------- 优惠券接口 ----------

    def create_coupon(self, payload):
        url = f"{self.base_url}/api/v1/coupons"
        logger.info("POST %s payload=%s", url, payload)
        resp = self.session.post(url, json=payload, timeout=self.timeout)
        logger.info("create_coupon status=%s body=%s", resp.status_code, resp.text[:500])
        return resp

    def claim_coupon(self, coupon_id):
        url = f"{self.base_url}/api/v1/coupons/{coupon_id}/claim"
        logger.info("POST %s", url)
        resp = self.session.post(url, timeout=self.timeout)
        logger.info("claim_coupon status=%s body=%s", resp.status_code, resp.text[:500])
        return resp

    def publish_coupon(self, coupon_id):
        """发布优惠券 — 文档未提供此接口，假设 POST /api/v1/coupons/{id}/publish。"""
        url = f"{self.base_url}/api/v1/coupons/{coupon_id}/publish"
        logger.info("POST %s", url)
        resp = self.session.post(url, timeout=self.timeout)
        logger.info("publish_coupon status=%s body=%s", resp.status_code, resp.text[:500])
        return resp

    def get_coupon(self, coupon_id):
        """获取优惠券详情 — 文档未提供此接口，假设 GET /api/v1/coupons/{id}。"""
        url = f"{self.base_url}/api/v1/coupons/{coupon_id}"
        logger.info("GET %s", url)
        resp = self.session.get(url, timeout=self.timeout)
        logger.info("get_coupon status=%s body=%s", resp.status_code, resp.text[:500])
        return resp

    def delete_coupon(self, coupon_id):
        """删除优惠券 — 文档未提供此接口，假设 DELETE /api/v1/coupons/{id}。"""
        url = f"{self.base_url}/api/v1/coupons/{coupon_id}"
        logger.info("DELETE %s", url)
        resp = self.session.delete(url, timeout=self.timeout)
        logger.info("delete_coupon status=%s body=%s", resp.status_code, resp.text[:500])
        return resp

    def close(self):
        self.session.close()
```

---

### 文件：`api-tests/conftest.py`

```python
"""pytest 全局配置：环境注入、客户端 fixture、测试数据造数与清理。"""

import os
import uuid

import pytest

from common.client import APIClient


# ============================================================
# 环境配置（全部走环境变量，不硬编码）
# ============================================================

@pytest.fixture(scope="session")
def base_url():
    return os.environ["API_BASE_URL"]


@pytest.fixture(scope="session")
def api_credentials():
    return {
        "username": os.environ["API_USER"],
        "password": os.environ["API_PASSWORD"],
    }


# ============================================================
# 客户端 fixtures
# ============================================================

@pytest.fixture(scope="session")
def client(base_url, api_credentials):
    """已认证客户端（session 级别，全量共享）。"""
    c = APIClient(base_url)
    c.login(api_credentials["username"], api_credentials["password"])
    yield c
    c.close()


@pytest.fixture
def unauth_client(base_url):
    """无鉴权客户端（不携带任何 Token）。"""
    return APIClient(base_url)


@pytest.fixture
def expired_token_client(base_url):
    """过期 Token 客户端。"""
    c = APIClient(base_url)
    c.set_token("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE1OTAwMDAwMDB9.expired_signature")
    return c


@pytest.fixture
def invalid_token_client(base_url):
    """无效 Token 客户端。"""
    c = APIClient(base_url)
    c.set_token("this_is_a_completely_invalid_token_string")
    return c


# ============================================================
# 测试数据 fixtures（自建自清理）
# ============================================================

@pytest.fixture
def create_and_cleanup_coupon(client):
    """创建优惠券的工厂函数，测试结束后自动清理所有成功创建的记录。

    用法::

        resp = create_and_cleanup_coupon({"name": "...", ...})
        assert resp.status_code == 201
    """
    created_ids = []

    def _create(payload):
        resp = client.create_coupon(payload)
        if resp.status_code == 201:
            coupon_id = resp.json().get("id")
            if coupon_id:
                created_ids.append(coupon_id)
        return resp

    yield _create

    # teardown — 删除所有创建成功的优惠券
    for cid in created_ids:
        try:
            client.delete_coupon(cid)
        except Exception:
            pass


@pytest.fixture
def published_coupon(client):
    """创建并发布一张优惠券（function 级别，每个测试独立一张）。

    返回 coupon_id，供领取测试使用。
    """
    unique_name = f"claim_test_{uuid.uuid4().hex[:8]}"
    resp = client.create_coupon({
        "name": unique_name,
        "amount": 10,
        "threshold": 0,
        "total": 100,
    })
    assert resp.status_code == 201, f"setup: 创建优惠券失败: {resp.text}"
    coupon_id = resp.json()["id"]

    # 发布（文档未提供发布接口，假设存在）
    pub_resp = client.publish_coupon(coupon_id)
    assert pub_resp.status_code in (200, 204), f"setup: 发布优惠券失败: {pub_resp.text}"

    yield coupon_id

    # teardown
    try:
        client.delete_coupon(coupon_id)
    except Exception:
        pass


@pytest.fixture
def unpublished_coupon(client):
    """创建但不发布的优惠券（状态=待发布），用于测试领取 404。

    返回 coupon_id。
    """
    unique_name = f"unpub_test_{uuid.uuid4().hex[:8]}"
    resp = client.create_coupon({
        "name": unique_name,
        "amount": 10,
        "threshold": 0,
        "total": 100,
    })
    assert resp.status_code == 201, f"setup: 创建优惠券失败: {resp.text}"
    coupon_id = resp.json()["id"]

    yield coupon_id

    try:
        client.delete_coupon(coupon_id)
    except Exception:
        pass
```

---

### 文件：`api-tests/test_coupon_create.py`

```python
"""创建优惠券接口测试  POST /api/v1/coupons

覆盖维度：
  - 正常路径（各参数边界有效值）
  - 必填缺失（name / amount / threshold / total）
  - 类型错误（字符串/小数/数字/布尔值）
  - 边界值无效（超长 / 0 / 负数 / 超大值 / 空串 / 纯空格）
  - 业务规则（名称同商户唯一 NAME_DUPLICATED / 门槛≥面额 THRESHOLD_INVALID）
  - 鉴权（无 Token / 过期 Token / 错误 Token → 401）
  - 幂等（同一名称重复提交不重复创建）
  - 并发（并发创建同名券只成功一个）
  - 数据一致性（创建后读回字段一致）
  - 特殊字符（emoji / 中文）
"""

import threading
import uuid

import pytest
import requests as req


# ============================================================
# 正常路径
# ============================================================

class TestCreateCouponSuccess:
    """创建优惠券 — 正常路径与边界有效值。"""

    def test_TC_01_01_正常创建返回201含id和待发布状态(self, client, create_and_cleanup_coupon):
        resp = create_and_cleanup_coupon({
            "name": f"normal_{uuid.uuid4().hex[:8]}",
            "amount": 50,
            "threshold": 100,
            "total": 1000,
        })
        assert resp.status_code == 201
        body = resp.json()
        assert "id" in body
        assert body["status"] == "待发布"

    def test_TC_01_02_name长度1创建成功(self, client, create_and_cleanup_coupon):
        resp = create_and_cleanup_coupon({
            "name": "A",
            "amount": 10,
            "threshold": 0,
            "total": 100,
        })
        assert resp.status_code == 201
        assert "id" in resp.json()

    def test_TC_01_03_name长度20创建成功(self, client, create_and_cleanup_coupon):
        resp = create_and_cleanup_coupon({
            "name": "A" * 20,
            "amount": 10,
            "threshold": 0,
            "total": 100,
        })
        assert resp.status_code == 201
        assert "id" in resp.json()

    def test_TC_01_04_amount最小值1创建成功(self, client, create_and_cleanup_coupon):
        resp = create_and_cleanup_coupon({
            "name": f"min_amt_{uuid.uuid4().hex[:8]}",
            "amount": 1,
            "threshold": 0,
            "total": 100,
        })
        assert resp.status_code == 201

    def test_TC_01_05_amount最大值1000创建成功(self, client, create_and_cleanup_coupon):
        resp = create_and_cleanup_coupon({
            "name": f"max_amt_{uuid.uuid4().hex[:8]}",
            "amount": 1000,
            "threshold": 0,
            "total": 100,
        })
        assert resp.status_code == 201

    def test_TC_01_06_threshold为0创建成功(self, client, create_and_cleanup_coupon):
        resp = create_and_cleanup_coupon({
            "name": f"thr0_{uuid.uuid4().hex[:8]}",
            "amount": 50,
            "threshold": 0,
            "total": 100,
        })
        assert resp.status_code == 201

    def test_TC_01_07_threshold等于amount创建成功(self, client, create_and_cleanup_coupon):
        """门槛非 0 时必须 ≥ 面额；等于面额是边界有效值。"""
        resp = create_and_cleanup_coupon({
            "name": f"thr_eq_amt_{uuid.uuid4().hex[:8]}",
            "amount": 50,
            "threshold": 50,
            "total": 100,
        })
        assert resp.status_code == 201

    def test_TC_01_08_total最小值1创建成功(self, client, create_and_cleanup_coupon):
        resp = create_and_cleanup_coupon({
            "name": f"min_total_{uuid.uuid4().hex[:8]}",
            "amount": 10,
            "threshold": 0,
            "total": 1,
        })
        assert resp.status_code == 201

    def test_TC_01_09_total最大值100000创建成功(self, client, create_and_cleanup_coupon):
        resp = create_and_cleanup_coupon({
            "name": f"max_total_{uuid.uuid4().hex[:8]}",
            "amount": 10,
            "threshold": 0,
            "total": 100000,
        })
        assert resp.status_code == 201

    def test_TC_01_10_name含emoji和中文创建成功(self, client, create_and_cleanup_coupon):
        resp = create_and_cleanup_coupon({
            "name": f"优惠券🎉{uuid.uuid4().hex[:4]}",
            "amount": 10,
            "threshold": 0,
            "total": 100,
        })
        assert resp.status_code == 201
        assert "id" in resp.json()


# ============================================================
# 必填参数缺失
# ============================================================

class TestCreateCouponMissingField:
    """创建优惠券 — 必填字段缺失，预期 400。"""

    @pytest.fixture
    def valid_payload(self):
        return {
            "name": f"miss_{uuid.uuid4().hex[:8]}",
            "amount": 10,
            "threshold": 0,
            "total": 100,
        }

    def test_TC_01_11_缺失name返回400(self, client, valid_payload):
        del valid_payload["name"]
        resp = client.create_coupon(valid_payload)
        assert resp.status_code == 400
        body = resp.json()
        assert "code" in body
        assert "message" in body

    def test_TC_01_12_缺失amount返回400(self, client, valid_payload):
        del valid_payload["amount"]
        resp = client.create_coupon(valid_payload)
        assert resp.status_code == 400
        body = resp.json()
        assert "code" in body
        assert "message" in body

    def test_TC_01_13_缺失threshold返回400(self, client, valid_payload):
        del valid_payload["threshold"]
        resp = client.create_coupon(valid_payload)
        assert resp.status_code == 400
        body = resp.json()
        assert "code" in body
        assert "message" in body

    def test_TC_01_14_缺失total返回400(self, client, valid_payload):
        del valid_payload["total"]
        resp = client.create_coupon(valid_payload)
        assert resp.status_code == 400
        body = resp.json()
        assert "code" in body
        assert "message" in body


# ============================================================
# 参数类型错误
# ============================================================

class TestCreateCouponTypeError:
    """创建优惠券 — 参数类型错误，预期 400。"""

    @pytest.fixture
    def valid_payload(self):
        return {
            "name": f"type_{uuid.uuid4().hex[:8]}",
            "amount": 10,
            "threshold": 0,
            "total": 100,
        }

    def test_TC_01_15_amount为字符串返回400(self, client, valid_payload):
        valid_payload["amount"] = "ten"
        resp = client.create_coupon(valid_payload)
        assert resp.status_code == 400

    def test_TC_01_16_threshold为小数返回400(self, client, valid_payload):
        valid_payload["threshold"] = 10.5
        resp = client.create_coupon(valid_payload)
        assert resp.status_code == 400

    def test_TC_01_17_name为整数返回400(self, client, valid_payload):
        valid_payload["name"] = 12345
        resp = client.create_coupon(valid_payload)
        assert resp.status_code == 400

    def test_TC_01_18_total为布尔值返回400(self, client, valid_payload):
        valid_payload["total"] = True
        resp = client.create_coupon(valid_payload)
        assert resp.status_code == 400


# ============================================================
# 边界值（无效）
# ============================================================

class TestCreateCouponBoundaryInvalid:
    """创建优惠券 — 边界值无效，预期 400。"""

    @pytest.fixture
    def valid_payload(self):
        return {
            "name": f"bnd_{uuid.uuid4().hex[:8]}",
            "amount": 10,
            "threshold": 0,
            "total": 100,
        }

    # --- name 边界 ---

    def test_TC_01_19_name超长21字符返回400(self, client, valid_payload):
        valid_payload["name"] = "A" * 21
        resp = client.create_coupon(valid_payload)
        assert resp.status_code == 400

    def test_TC_01_20_name空串返回400(self, client, valid_payload):
        valid_payload["name"] = ""
        resp = client.create_coupon(valid_payload)
        assert resp.status_code == 400

    def test_TC_01_21_name纯空格返回400(self, client, valid_payload):
        valid_payload["name"] = "   "
        resp = client.create_coupon(valid_payload)
        assert resp.status_code == 400

    # --- amount 边界 ---

    def test_TC_01_22_amount为0返回400(self, client, valid_payload):
        valid_payload["amount"] = 0
        resp = client.create_coupon(valid_payload)
        assert resp.status_code == 400

    def test_TC_01_23_amount为1001返回400(self, client, valid_payload):
        valid_payload["amount"] = 1001
        resp = client.create_coupon(valid_payload)
        assert resp.status_code == 400

    def test_TC_01_24_amount为负5返回400(self, client, valid_payload):
        valid_payload["amount"] = -5
        resp = client.create_coupon(valid_payload)
        assert resp.status_code == 400

    def test_TC_01_25_amount为小数0_5返回400(self, client, valid_payload):
        valid_payload["amount"] = 0.5
        resp = client.create_coupon(valid_payload)
        assert resp.status_code == 400

    def test_TC_01_26_amount超大值1e10返回400(self, client, valid_payload):
        valid_payload["amount"] = 10 ** 10
        resp = client.create_coupon(valid_payload)
        assert resp.status_code == 400

    # --- threshold 边界 ---

    def test_TC_01_27_threshold为负1返回400(self, client, valid_payload):
        valid_payload["threshold"] = -1
        resp = client.create_coupon(valid_payload)
        assert resp.status_code == 400

    # --- total 边界 ---

    def test_TC_01_28_total为0返回400(self, client, valid_payload):
        valid_payload["total"] = 0
        resp = client.create_coupon(valid_payload)
        assert resp.status_code == 400

    def test_TC_01_29_total为100001返回400(self, client, valid_payload):
        valid_payload["total"] = 100001
        resp = client.create_coupon(valid_payload)
        assert resp.status_code == 400

    def test_TC_01_30_total超大值1e10返回400(self, client, valid_payload):
        valid_payload["total"] = 10 ** 10
        resp = client.create_coupon(valid_payload)
        assert resp.status_code == 400


# ============================================================
# 业务规则
# ============================================================

class TestCreateCouponBusinessRule:
    """创建优惠券 — 业务规则校验。"""

    def test_TC_01_31_名称重复返回400_NAME_DUPLICATED(self, client, create_and_cleanup_coupon):
        name = f"dup_{uuid.uuid4().hex[:8]}"
        payload = {
            "name": name,
            "amount": 10,
            "threshold": 0,
            "total": 100,
        }
        # 第一次创建成功
        resp1 = create_and_cleanup_coupon(payload)
        assert resp1.status_code == 201

        # 同名再次创建 → 400 + NAME_DUPLICATED
        resp2 = client.create_coupon(payload)
        assert resp2.status_code == 400
        body = resp2.json()
        assert body["code"] == "NAME_DUPLICATED"
        assert "message" in body

    def test_TC_01_32_门槛非0且小于面额返回400_THRESHOLD_INVALID(self, client):
        resp = client.create_coupon({
            "name": f"thr_lt_amt_{uuid.uuid4().hex[:8]}",
            "amount": 50,
            "threshold": 30,  # threshold > 0 且 < amount
            "total": 100,
        })
        assert resp.status_code == 400
        body = resp.json()
        assert body["code"] == "THRESHOLD_INVALID"
        assert "message" in body

    def test_TC_01_33_门槛为0时面额可任意有效值(self, client, create_and_cleanup_coupon):
        """门槛为 0 表示无门槛，不受面额约束。"""
        resp = create_and_cleanup_coupon({
            "name": f"thr0_high_amt_{uuid.uuid4().hex[:8]}",
            "amount": 1000,
            "threshold": 0,
            "total": 100,
        })
        assert resp.status_code == 201


# ============================================================
# 幂等
# ============================================================

class TestCreateCouponIdempotency:
    """创建优惠券 — 幂等性：同一业务键（name）重复提交不重复创建。"""

    def test_TC_01_34_同一名称重复提交第二次返回NAME_DUPLICATED不产生新记录(
        self, client, create_and_cleanup_coupon
    ):
        name = f"idem_{uuid.uuid4().hex[:8]}"
        payload = {
            "name": name,
            "amount": 10,
            "threshold": 0,
            "total": 100,
        }
        resp1 = create_and_cleanup_coupon(payload)
        assert resp1.status_code == 201
        id1 = resp1.json().get("id")

        resp2 = client.create_coupon(payload)
        assert resp2.status_code == 400
        assert resp2.json()["code"] == "NAME_DUPLICATED"

        # 如果第二次响应体中也带了 id，则 id 必须与第一次相同（幂等返回原记录）
        if "id" in resp2.json():
            assert resp2.json()["id"] == id1


# ============================================================
# 并发
# ============================================================

class TestCreateCouponConcurrent:
    """创建优惠券 — 并发创建同名券，预期只成功一个。"""

    def test_TC_01_35_并发创建同名券只成功一个(self, client):
        name = f"conc_{uuid.uuid4().hex[:8]}"
        base_url = client.base_url
        token = client.session.headers.get("Authorization")

        results = []
        created_ids = []
        barrier = threading.Barrier(5)

        def _create():
            barrier.wait()  # 所有线程同时触发
            resp = req.post(
                f"{base_url}/api/v1/coupons",
                json={
                    "name": name,
                    "amount": 10,
                    "threshold": 0,
                    "total": 100,
                },
                headers={"Authorization": token},
                timeout=15,
            )
            results.append(resp.status_code)
            if resp.status_code == 201:
                try:
                    created_ids.append(resp.json()["id"])
                except Exception:
                    pass

        threads = [threading.Thread(target=_create) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        success_count = results.count(201)
        assert success_count == 1, (
            f"并发创建同名券: 成功 {success_count} 次，预期仅 1 次成功"
        )

        # cleanup
        for cid in created_ids:
            try:
                client.delete_coupon(cid)
            except Exception:
                pass


# ============================================================
# 鉴权
# ============================================================

class TestCreateCouponAuth:
    """创建优惠券 — 鉴权校验。"""

    @pytest.fixture
    def valid_payload(self):
        return {
            "name": f"auth_{uuid.uuid4().hex[:8]}",
            "amount": 10,
            "threshold": 0,
            "total": 100,
        }

    def test_TC_01_36_无Token创建返回401(self, unauth_client, valid_payload):
        resp = unauth_client.create_coupon(valid_payload)
        assert resp.status_code == 401

    def test_TC_01_37_过期Token创建返回401(self, expired_token_client, valid_payload):
        resp = expired_token_client.create_coupon(valid_payload)
        assert resp.status_code == 401

    def test_TC_01_38_错误Token创建返回401(self, invalid_token_client, valid_payload):
        resp = invalid_token_client.create_coupon(valid_payload)
        assert resp.status_code == 401


# ============================================================
# 数据一致性
# ============================================================

class TestCreateCouponConsistency:
    """创建优惠券 — 写后读回一致。"""

    def test_TC_01_39_创建后读回字段一致(self, client, create_and_cleanup_coupon):
        name = f"readback_{uuid.uuid4().hex[:8]}"
        payload = {
            "name": name,
            "amount": 88,
            "threshold": 200,
            "total": 500,
        }
        resp = create_and_cleanup_coupon(payload)
        assert resp.status_code == 201
        coupon_id = resp.json()["id"]

        # 读回验证（假设存在 GET /api/v1/coupons/{id}）
        get_resp = client.get_coupon(coupon_id)
        assert get_resp.status_code == 200
        body = get_resp.json()
        assert body["id"] == coupon_id
        assert body["name"] == name
        assert body["amount"] == 88
        assert body["threshold"] == 200
        assert body["total"] == 500
        assert body["status"] == "待发布"
```

---

### 文件：`api-tests/test_coupon_claim.py`

```python
"""领取优惠券接口测试  POST /api/v1/coupons/{id}/claim

覆盖维度：
  - 正常领取（第 1 / 2 / 3 张，第 3 张达上限）
  - 超额领取（第 4 张 → 409）
  - 重复领取到上限后持续 409
  - 券不存在 / 券未发布 → 404
  - 路径参数校验（空 id / 非 UUID 格式）
  - 鉴权（无 Token / 过期 Token / 错误 Token → 401）
  - 并发领取（不超过上限，无超发）
"""

import threading
import uuid

import pytest
import requests as req


# ============================================================
# 正常领取
# ============================================================

class TestClaimCouponSuccess:
    """领取优惠券 — 正常路径。"""

    def test_TC_02_01_正常领取返回200含user_coupon_id(self, client, published_coupon):
        resp = client.claim_coupon(published_coupon)
        assert resp.status_code == 200
        body = resp.json()
        assert "user_coupon_id" in body

    def test_TC_02_02_领取同一券第2张成功(self, client, published_coupon):
        resp1 = client.claim_coupon(published_coupon)
        assert resp1.status_code == 200

        resp2 = client.claim_coupon(published_coupon)
        assert resp2.status_code == 200
        assert "user_coupon_id" in resp2.json()

    def test_TC_02_03_领取同一券第3张达到上限成功(self, client, published_coupon):
        for i in range(3):
            resp = client.claim_coupon(published_coupon)
            assert resp.status_code == 200, f"第 {i + 1} 张领取失败: {resp.text}"


# ============================================================
# 超额领取
# ============================================================

class TestClaimCouponLimitExceeded:
    """领取优惠券 — 超过每人限领 3 张。"""

    def test_TC_02_04_领取第4张返回409(self, client, published_coupon):
        # 先领 3 张（达到上限）
        for i in range(3):
            resp = client.claim_coupon(published_coupon)
            assert resp.status_code == 200

        # 第 4 张 → 409
        resp = client.claim_coupon(published_coupon)
        assert resp.status_code == 409
        body = resp.json()
        assert "code" in body or "message" in body

    def test_TC_02_05_重复领取到上限后持续409(self, client, published_coupon):
        """到上限后继续领取，每次都应返回 409。"""
        for i in range(3):
            resp = client.claim_coupon(published_coupon)
            assert resp.status_code == 200

        # 第 4 次
        resp4 = client.claim_coupon(published_coupon)
        assert resp4.status_code == 409

        # 第 5 次
        resp5 = client.claim_coupon(published_coupon)
        assert resp5.status_code == 409


# ============================================================
# 券状态校验
# ============================================================

class TestClaimCouponStatus:
    """领取优惠券 — 券不存在或状态非已发布 → 404。"""

    def test_TC_02_06_领取未发布券返回404(self, client, unpublished_coupon):
        """创建后状态为「待发布」，领取应返回 404。"""
        resp = client.claim_coupon(unpublished_coupon)
        assert resp.status_code == 404

    def test_TC_02_07_领取不存在的券返回404(self, client):
        fake_id = str(uuid.uuid4())
        resp = client.claim_coupon(fake_id)
        assert resp.status_code == 404


# ============================================================
# 路径参数校验
# ============================================================

class TestClaimCouponParam:
    """领取优惠券 — 路径参数校验。"""

    def test_TC_02_08_id为空字符串返回404或400(self, client):
        resp = client.claim_coupon("")
        assert resp.status_code in (404, 400)

    def test_TC_02_09_id为非UUID格式返回404或400(self, client):
        resp = client.claim_coupon("not_a_valid_id")
        assert resp.status_code in (404, 400)


# ============================================================
# 鉴权
# ============================================================

class TestClaimCouponAuth:
    """领取优惠券 — 鉴权校验（未携带或过期 Token → 401）。"""

    def test_TC_02_10_无Token领取返回401(self, unauth_client, published_coupon):
        resp = unauth_client.claim_coupon(published_coupon)
        assert resp.status_code == 401

    def test_TC_02_11_过期Token领取返回401(self, expired_token_client, published_coupon):
        resp = expired_token_client.claim_coupon(published_coupon)
        assert resp.status_code == 401

    def test_TC_02_12_错误Token领取返回401(self, invalid_token_client, published_coupon):
        resp = invalid_token_client.claim_coupon(published_coupon)
        assert resp.status_code == 401


# ============================================================
# 并发领取
# ============================================================

class TestClaimCouponConcurrent:
    """领取优惠券 — 并发领取同一张券，不超过每人限领 3 张，无超发。"""

    def test_TC_02_13_并发领取5次最多成功3次无超发(self, client, published_coupon):
        base_url = client.base_url
        token = client.session.headers.get("Authorization")
        url = f"{base_url}/api/v1/coupons/{published_coupon}/claim"

        results = []
        barrier = threading.Barrier(5)

        def _claim():
            barrier.wait()  # 所有线程同时触发
            resp = req.post(url, headers={"Authorization": token}, timeout=15)
            results.append(resp.status_code)

        threads = [threading.Thread(target=_claim) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        success_count = results.count(200)
        conflict_count = results.count(409)
        assert success_count <= 3, (
            f"并发超发: 成功 {success_count} 次，超过每人限领 3 张"
        )
        assert success_count + conflict_count == 5, (
            f"并发结果异常: 成功 {success_count}, 409 {conflict_count}, "
            f"其他 {[r for r in results if r not in (200, 409)]}"
        )
```

---

## 运行方式

```bash
# 全量运行
export API_BASE_URL=https://api.example.test
export API_USER=your_test_user
export API_PASSWORD=your_test_password
pytest api-tests/ -v --tb=short

# 单文件运行
pytest api-tests/test_coupon_create.py -v --tb=short
pytest api-tests/test_coupon_claim.py -v --tb=short
```

---

## 待澄清清单

| # | 问题 | 影响范围 | 当前处理方式 |
|---|------|---------|-------------|
| 1 | **发布接口**：创建后状态为"待发布"，领取要求"已发布"，但 OpenAPI 文档未提供发布接口的路径与请求结构。 | `conftest.py` 的 `published_coupon` fixture；所有领取测试依赖此 fixture | 假设 `POST /api/v1/coupons/{id}/publish`，成功返回 200/204 |
| 2 | **删除接口**：测试数据清理需要删除优惠券，文档未提供。 | `conftest.py` 所有 teardown 逻辑 | 假设 `DELETE /api/v1/coupons/{id}` |
| 3 | **查询接口**：数据一致性测试（写后读回）需要获取优惠券详情，文档未提供。 | `test_TC_01_39` | 假设 `GET /api/v1/coupons/{id}` 返回完整字段 |
| 4 | **登录接口**：文档未提供登录接口路径及响应结构。 | `conftest.py` 的 `client` fixture | 假设 `POST /api/v1/auth/login`，请求体 `{username, password}`，响应体含 `token` 字段 |
| 5 | **409 响应体结构**：超额领取返回 409 时，响应体是否包含 `code` 字段？code 值是什么（如 `CLAIM_LIMIT_EXCEEDED`）？ | `test_TC_02_04`、`test_TC_02_05` 的断言 | 仅断言 status code 409 + 响应体含 `code` 或 `message` |
| 6 | **404 响应体结构**：券不存在 / 券未发布返回 404 时，响应体结构是什么？是否区分"不存在"与"未发布"？ | `test_TC_02_06`、`test_TC_02_07` | 仅断言 status code 404 |
| 7 | **name 纯空格处理**：服务端是否对 name 做 trim？纯空格名称应报错还是接受？ | `test_TC_01_21` | 预期返回 400 |
| 8 | **name 类型转换**：服务端是否对非字符串类型（如整数 12345）做隐式转换？ | `test_TC_01_17` | 预期返回 400 |
| 9 | **商户隔离 / 越权**：创建和领取接口是否存在商户隔离？用户 A 能否领取用户 B 所属商户的券？ | 未编写越权领取测试（行为不确定） | 待确认后补充 `test_TC_02_xx` 越权用例 |
| 10 | **并发创建同名券**：并发场景下数据库唯一约束触发时，返回 400 NAME_DUPLICATED 还是 500？ | `test_TC_01_35` | 预期恰好 1 个 201，其余为 400 |
| 11 | **领取限制参数**：创建优惠券时是否支持设置每人限领数量？当前每人限领 3 张是全局固定值还是可配置？ | 创建接口参数矩阵 | 文档中创建接口未含此参数，按固定 3 张处理 |
| 12 | **领取接口幂等键**：领取接口是否有业务幂等键（防止网络重试导致重复领取）？还是完全依赖服务端计数？ | `test_TC_02_05` | 按服务端计数处理，无客户端幂等键 |
```
