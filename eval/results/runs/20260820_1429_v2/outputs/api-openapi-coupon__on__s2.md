## 文件清单

```
api-tests/
├── conftest.py
├── common/
│   ├── __init__.py
│   ├── client.py
│   └── test_data.py
├── test_coupon_create.py
├── test_coupon_claim.py
└── requirements.txt
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

### 文件: `api-tests/common/test_data.py`

```python
"""共享测试数据与辅助函数。"""

import uuid

# 标准测试数据——创建优惠券的合法 payload 模板
VALID_PAYLOAD = {
    "name": "满100减20券",
    "amount": 20,
    "threshold": 100,
    "total": 1000,
}


def unique_name(prefix="测试券"):
    """生成唯一券名称，避免触发同商户名称唯一约束。"""
    return f"{prefix}{uuid.uuid4().hex[:8]}"
```

---

### 文件: `api-tests/common/client.py`

```python
"""统一请求封装：日志、超时、鉴权头、断言辅助。"""

import logging

import pytest
import requests

logger = logging.getLogger(__name__)


class ApiClient:
    """统一的 API 请求客户端，封装 base_url、鉴权头、超时与日志。"""

    def __init__(self, base_url, token=None):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        if token:
            self.session.headers.update({"Authorization": f"Bearer {token}"})

    def _url(self, path):
        return f"{self.base_url}{path}"

    def request(self, method, path, **kwargs):
        kwargs.setdefault("timeout", 10)
        resp = self.session.request(method, self._url(path), **kwargs)
        self._log(resp)
        return resp

    def get(self, path, **kwargs):
        return self.request("GET", path, **kwargs)

    def post(self, path, **kwargs):
        return self.request("POST", path, **kwargs)

    def put(self, path, **kwargs):
        return self.request("PUT", path, **kwargs)

    def delete(self, path, **kwargs):
        return self.request("DELETE", path, **kwargs)

    @staticmethod
    def _log(resp):
        logger.info("[%s] %s", resp.request.method, resp.request.url)
        logger.info("Request Body: %s", resp.request.body)
        logger.info("Response [%s]: %s", resp.status_code, resp.text)


def assert_response(resp, expected_status, expected_code=None, expected_fields=None):
    """断言三件套：状态码 + 业务码 + 响应体关键字段。

    Args:
        resp: requests.Response 对象。
        expected_status: 预期 HTTP 状态码。
        expected_code: 预期业务码（错误响应 body 中的 code 字段）。
        expected_fields: 预期响应体字段 {field: value}；
                        value=None 表示只检查字段存在。
    """
    # 1. 状态码
    assert resp.status_code == expected_status, (
        f"状态码断言失败: expected {expected_status}, "
        f"got {resp.status_code}, body={resp.text}"
    )

    # 无需检查业务码或字段时结束
    if expected_code is None and expected_fields is None:
        return

    # 解析 JSON
    try:
        body = resp.json()
    except ValueError:
        pytest.fail(
            f"响应体非 JSON 但预期检查业务码/字段: "
            f"status={resp.status_code}, body={resp.text}"
        )

    # 2. 业务码
    if expected_code is not None:
        actual_code = body.get("code")
        assert actual_code == expected_code, (
            f"业务码断言失败: expected '{expected_code}', "
            f"got '{actual_code}', body={resp.text}"
        )

    # 3. 关键字段
    if expected_fields is not None:
        for field, expected in expected_fields.items():
            if expected is not None:
                actual = body.get(field)
                assert actual == expected, (
                    f"字段断言失败 [{field}]: expected '{expected}', "
                    f"got '{actual}', body={resp.text}"
                )
            else:
                assert field in body, (
                    f"响应体缺少字段: {field}, body={resp.text}"
                )
```

---

### 文件: `api-tests/conftest.py`

```python
"""pytest 全局 fixture：环境配置、鉴权、测试数据工厂。"""

import os
import sys
import logging

import pytest
import requests

# 确保 common 包可导入
sys.path.insert(0, os.path.dirname(__file__))

from common.client import ApiClient
from common.test_data import VALID_PAYLOAD, unique_name

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


# ── 环境与鉴权 ────────────────────────────────────────────────

def login(base_url, username, password):
    """登录获取 Token。

    待确认：登录接口路径与响应结构。
    暂假设 POST /api/v1/auth/login，返回 {"token": "..."}（见待澄清 #1）。
    """
    resp = requests.post(
        f"{base_url}/api/v1/auth/login",
        json={"username": username, "password": password},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()["token"]


@pytest.fixture(scope="session")
def base_url():
    """被测环境地址，从环境变量注入。"""
    return os.environ["API_BASE_URL"]


@pytest.fixture(scope="session")
def auth_token(base_url):
    """登录获取 Bearer Token。"""
    return login(base_url, os.environ["API_USER"], os.environ["API_PASSWORD"])


@pytest.fixture
def client(base_url, auth_token):
    """已认证的 ApiClient（Bearer Token）。"""
    return ApiClient(base_url, token=auth_token)


@pytest.fixture
def unauth_client(base_url):
    """未认证的 ApiClient（不携带 Token）。"""
    return ApiClient(base_url, token=None)


@pytest.fixture
def expired_client(base_url):
    """携带过期/无效 Token 的 ApiClient。"""
    return ApiClient(base_url, token="expired.invalid.token")


# ── 测试数据工厂 ──────────────────────────────────────────────

@pytest.fixture
def create_coupon(client):
    """创建优惠券工厂函数。自动清理创建成功的券。

    用法::

        resp = create_coupon(payload)
        assert resp.status_code == 201

    返回: requests.Response
    """
    created_ids = []

    def _create(payload):
        resp = client.post("/api/v1/coupons", json=payload)
        if resp.status_code == 201:
            coupon_id = resp.json().get("id")
            if coupon_id:
                created_ids.append(coupon_id)
        return resp

    yield _create

    # teardown: 删除创建的优惠券
    # 待确认：删除接口路径（见待澄清 #3），暂假设 DELETE /api/v1/coupons/{id}
    for cid in created_ids:
        try:
            client.delete(f"/api/v1/coupons/{cid}")
        except Exception:
            pass


@pytest.fixture
def publish_coupon(client):
    """发布优惠券工厂函数。

    待确认：发布接口路径与响应（见待澄清 #2），
    暂假设 POST /api/v1/coupons/{id}/publish，返回 200 或 204。
    """
    def _publish(coupon_id):
        return client.post(f"/api/v1/coupons/{coupon_id}/publish")
    return _publish


@pytest.fixture
def published_coupon(client, create_coupon, publish_coupon):
    """创建并发布一张优惠券，返回券 ID。

    total=10000 保证并发领取测试有足够库存。
    自动清理（通过 create_coupon 的 teardown）。
    """
    payload = {**VALID_PAYLOAD, "name": unique_name("领取测试"), "total": 10000}
    resp = create_coupon(payload)
    assert resp.status_code == 201, f"前置失败-创建优惠券: {resp.text}"
    coupon_id = resp.json()["id"]

    pub_resp = publish_coupon(coupon_id)
    assert pub_resp.status_code in (200, 204), (
        f"前置失败-发布优惠券: {pub_resp.text}"
    )

    return coupon_id
```

---

### 文件: `api-tests/test_coupon_create.py`

```python
"""创建优惠券接口测试
接口: POST /api/v1/coupons

覆盖维度:
  - 正常创建
  - 参数缺失（name / amount / threshold / total 逐一缺失）
  - 参数类型错误（amount 传字符串 / 小数）
  - 边界值（name 长度 / amount 范围 / threshold 范围 / total 范围）
  - 业务规则（名称同商户唯一 NAME_DUPLICATED / 门槛≥面额 THRESHOLD_INVALID）
  - 鉴权（无 Token / 过期 Token）
  - 并发（同名券并发创建，仅一个成功）
  - 数据一致性（创建后读回——待查询接口确认后补全）
"""

import threading

import pytest
import requests as req

from common.client import assert_response
from common.test_data import VALID_PAYLOAD, unique_name


# ══════════════════════════════════════════════════════════════
# 正常创建
# ══════════════════════════════════════════════════════════════

class TestCreateCouponSuccess:

    def test_TC_CREATE_001_正常创建优惠券(self, client, create_coupon):
        """全参数合法 -> 201，body 含 id 和 status=待发布"""
        payload = {**VALID_PAYLOAD, "name": unique_name("正常创建")}
        resp = create_coupon(payload)
        assert_response(
            resp,
            expected_status=201,
            expected_fields={"id": None, "status": "待发布"},
        )


# ══════════════════════════════════════════════════════════════
# 参数缺失（逐必填字段）
# ══════════════════════════════════════════════════════════════

class TestCreateCouponMissingParam:

    def test_TC_CREATE_002_name缺失(self, client, create_coupon):
        """缺少必填字段 name -> 400，body 含 code 与 message"""
        payload = {**VALID_PAYLOAD, "name": unique_name()}
        del payload["name"]
        resp = create_coupon(payload)
        assert_response(
            resp, expected_status=400,
            expected_fields={"code": None, "message": None},
        )

    def test_TC_CREATE_003_amount缺失(self, client, create_coupon):
        """缺少必填字段 amount -> 400，body 含 code 与 message"""
        payload = {**VALID_PAYLOAD, "name": unique_name()}
        del payload["amount"]
        resp = create_coupon(payload)
        assert_response(
            resp, expected_status=400,
            expected_fields={"code": None, "message": None},
        )

    def test_TC_CREATE_004_threshold缺失(self, client, create_coupon):
        """缺少必填字段 threshold -> 400，body 含 code 与 message"""
        payload = {**VALID_PAYLOAD, "name": unique_name()}
        del payload["threshold"]
        resp = create_coupon(payload)
        assert_response(
            resp, expected_status=400,
            expected_fields={"code": None, "message": None},
        )

    def test_TC_CREATE_005_total缺失(self, client, create_coupon):
        """缺少必填字段 total -> 400，body 含 code 与 message"""
        payload = {**VALID_PAYLOAD, "name": unique_name()}
        del payload["total"]
        resp = create_coupon(payload)
        assert_response(
            resp, expected_status=400,
            expected_fields={"code": None, "message": None},
        )


# ══════════════════════════════════════════════════════════════
# name 边界值
# ══════════════════════════════════════════════════════════════

class TestCreateCouponNameBoundary:

    def test_TC_CREATE_006_name为空串(self, client, create_coupon):
        """name=""（空字符串）-> 400"""
        payload = {**VALID_PAYLOAD, "name": ""}
        resp = create_coupon(payload)
        assert_response(
            resp, expected_status=400,
            expected_fields={"code": None, "message": None},
        )

    def test_TC_CREATE_007_name正好20字符(self, client, create_coupon):
        """name 长度=20（maxLength 边界有效值）-> 201"""
        payload = {**VALID_PAYLOAD, "name": "a" * 20}
        resp = create_coupon(payload)
        assert_response(
            resp, expected_status=201,
            expected_fields={"id": None, "status": "待发布"},
        )

    def test_TC_CREATE_008_name超长21字符(self, client, create_coupon):
        """name 长度=21（超过 maxLength 20）-> 400"""
        payload = {**VALID_PAYLOAD, "name": "a" * 21}
        resp = create_coupon(payload)
        assert_response(
            resp, expected_status=400,
            expected_fields={"code": None, "message": None},
        )

    def test_TC_CREATE_009_name含特殊字符(self, client, create_coupon):
        """name 含 emoji / 引号 / 尖括号（长度未超限）-> 201"""
        special_name = "🎉'\"<>"
        payload = {**VALID_PAYLOAD, "name": special_name}
        resp = create_coupon(payload)
        assert_response(
            resp, expected_status=201,
            expected_fields={"id": None, "status": "待发布"},
        )
        # TODO: 有查询接口后补充读回一致性断言（见待澄清 #4）


# ══════════════════════════════════════════════════════════════
# amount 边界值
# ══════════════════════════════════════════════════════════════

class TestCreateCouponAmountBoundary:

    def test_TC_CREATE_010_amount为零(self, client, create_coupon):
        """amount=0（minimum-1）-> 400"""
        payload = {**VALID_PAYLOAD, "name": unique_name(), "amount": 0}
        resp = create_coupon(payload)
        assert_response(
            resp, expected_status=400,
            expected_fields={"code": None, "message": None},
        )

    def test_TC_CREATE_011_amount为最小值1(self, client, create_coupon):
        """amount=1（minimum 边界有效值），threshold=0 -> 201"""
        payload = {
            **VALID_PAYLOAD, "name": unique_name(),
            "amount": 1, "threshold": 0,
        }
        resp = create_coupon(payload)
        assert_response(
            resp, expected_status=201,
            expected_fields={"id": None, "status": "待发布"},
        )

    def test_TC_CREATE_012_amount为最大值1000(self, client, create_coupon):
        """amount=1000（maximum 边界有效值），threshold=0 -> 201"""
        payload = {
            **VALID_PAYLOAD, "name": unique_name(),
            "amount": 1000, "threshold": 0,
        }
        resp = create_coupon(payload)
        assert_response(
            resp, expected_status=201,
            expected_fields={"id": None, "status": "待发布"},
        )

    def test_TC_CREATE_013_amount超最大值1001(self, client, create_coupon):
        """amount=1001（maximum+1）-> 400"""
        payload = {**VALID_PAYLOAD, "name": unique_name(), "amount": 1001}
        resp = create_coupon(payload)
        assert_response(
            resp, expected_status=400,
            expected_fields={"code": None, "message": None},
        )

    def test_TC_CREATE_014_amount为字符串类型(self, client, create_coupon):
        """amount="20"（类型错误，应为 integer）-> 400"""
        payload = {**VALID_PAYLOAD, "name": unique_name(), "amount": "20"}
        resp = create_coupon(payload)
        assert_response(
            resp, expected_status=400,
            expected_fields={"code": None, "message": None},
        )

    def test_TC_CREATE_015_amount为小数(self, client, create_coupon):
        """amount=20.5（类型错误，integer 不接受小数）-> 400"""
        payload = {**VALID_PAYLOAD, "name": unique_name(), "amount": 20.5}
        resp = create_coupon(payload)
        assert_response(
            resp, expected_status=400,
            expected_fields={"code": None, "message": None},
        )


# ══════════════════════════════════════════════════════════════
# threshold 边界值与业务规则
# ══════════════════════════════════════════════════════════════

class TestCreateCouponThresholdBoundary:

    def test_TC_CREATE_016_threshold为零无门槛(self, client, create_coupon):
        """threshold=0（无门槛券，有效）-> 201"""
        payload = {**VALID_PAYLOAD, "name": unique_name(), "threshold": 0}
        resp = create_coupon(payload)
        assert_response(
            resp, expected_status=201,
            expected_fields={"id": None, "status": "待发布"},
        )

    def test_TC_CREATE_017_threshold为负数(self, client, create_coupon):
        """threshold=-1（小于 minimum 0）-> 400"""
        payload = {**VALID_PAYLOAD, "name": unique_name(), "threshold": -1}
        resp = create_coupon(payload)
        assert_response(
            resp, expected_status=400,
            expected_fields={"code": None, "message": None},
        )

    def test_TC_CREATE_018_threshold小于面额(self, client, create_coupon):
        """threshold=5, amount=10（门槛非 0 且 < 面额）-> 400, code=THRESHOLD_INVALID"""
        payload = {
            **VALID_PAYLOAD, "name": unique_name(),
            "amount": 10, "threshold": 5,
        }
        resp = create_coupon(payload)
        assert_response(resp, expected_status=400, expected_code="THRESHOLD_INVALID")

    def test_TC_CREATE_019_threshold等于面额(self, client, create_coupon):
        """threshold=10, amount=10（门槛等于面额，边界有效）-> 201"""
        payload = {
            **VALID_PAYLOAD, "name": unique_name(),
            "amount": 10, "threshold": 10,
        }
        resp = create_coupon(payload)
        assert_response(
            resp, expected_status=201,
            expected_fields={"id": None, "status": "待发布"},
        )


# ══════════════════════════════════════════════════════════════
# total 边界值
# ══════════════════════════════════════════════════════════════

class TestCreateCouponTotalBoundary:

    def test_TC_CREATE_020_total为零(self, client, create_coupon):
        """total=0（minimum-1）-> 400"""
        payload = {**VALID_PAYLOAD, "name": unique_name(), "total": 0}
        resp = create_coupon(payload)
        assert_response(
            resp, expected_status=400,
            expected_fields={"code": None, "message": None},
        )

    def test_TC_CREATE_021_total为最小值1(self, client, create_coupon):
        """total=1（minimum 边界有效值）-> 201"""
        payload = {**VALID_PAYLOAD, "name": unique_name(), "total": 1}
        resp = create_coupon(payload)
        assert_response(
            resp, expected_status=201,
            expected_fields={"id": None, "status": "待发布"},
        )

    def test_TC_CREATE_022_total为最大值100000(self, client, create_coupon):
        """total=100000（maximum 边界有效值）-> 201"""
        payload = {**VALID_PAYLOAD, "name": unique_name(), "total": 100000}
        resp = create_coupon(payload)
        assert_response(
            resp, expected_status=201,
            expected_fields={"id": None, "status": "待发布"},
        )

    def test_TC_CREATE_023_total超最大值100001(self, client, create_coupon):
        """total=100001（maximum+1）-> 400"""
        payload = {**VALID_PAYLOAD, "name": unique_name(), "total": 100001}
        resp = create_coupon(payload)
        assert_response(
            resp, expected_status=400,
            expected_fields={"code":