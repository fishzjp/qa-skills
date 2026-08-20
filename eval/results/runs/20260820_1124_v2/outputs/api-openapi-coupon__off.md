# config.py

```python
"""测试配置 - 通过环境变量注入"""
import os

API_BASE_URL = os.getenv("API_BASE_URL", "https://api.example.test")
API_USER = os.getenv("API_USER", "test_user")
API_PASSWORD = os.getenv("API_PASSWORD", "test_password")

# 接口路径
LOGIN_PATH = "/api/v1/auth/login"
COUPONS_PATH = "/api/v1/coupons"
CLAIM_PATH = "/api/v1/coupons/{coupon_id}/claim"
PUBLISH_PATH = "/api/v1/coupons/{coupon_id}/publish"
```

---

# conftest.py

```python
"""Pytest 共享 fixtures：认证、会话、优惠券数据工厂"""
import uuid

import pytest
import requests

from config import (
    API_BASE_URL,
    API_USER,
    API_PASSWORD,
    LOGIN_PATH,
    COUPONS_PATH,
    PUBLISH_PATH,
)


# ── 基础 fixtures ──────────────────────────────────────────

@pytest.fixture(scope="session")
def base_url():
    return API_BASE_URL


@pytest.fixture(scope="session")
def auth_token(base_url):
    """登录获取 Bearer Token"""
    resp = requests.post(
        f"{base_url}{LOGIN_PATH}",
        json={"username": API_USER, "password": API_PASSWORD},
    )
    assert resp.status_code == 200, f"登录失败: {resp.status_code} {resp.text}"
    data = resp.json()
    token = data.get("token") or data.get("access_token")
    assert token, f"登录响应中未找到 token 字段: {data}"
    return token


@pytest.fixture(scope="session")
def auth_headers(auth_token):
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture(scope="session")
def api_session(auth_headers):
    """携带认证头的 requests.Session"""
    s = requests.Session()
    s.headers.update(auth_headers)
    return s


# ── 优惠券数据工厂 ────────────────────────────────────────

@pytest.fixture
def unique_name():
    """生成唯一优惠券名称（避免同商户重名）"""
    return f"test_{uuid.uuid4().hex[:12]}"


@pytest.fixture
def valid_coupon_data(unique_name):
    """合法优惠券请求体"""
    return {
        "name": unique_name,
        "amount": 100,
        "threshold": 100,
        "total": 1000,
    }


@pytest.fixture
def create_coupon(base_url, api_session):
    """创建优惠券的可调用 fixture，返回 Response"""
    def _create(data):
        return api_session.post(f"{base_url}{COUPONS_PATH}", json=data)
    return _create


@pytest.fixture
def published_coupon_id(base_url, api_session, create_coupon, valid_coupon_data):
    """创建并发布一张优惠券，返回 coupon_id

    待澄清: 发布接口路径 assumed as POST /api/v1/coupons/{id}/publish
    """
    resp = create_coupon(valid_coupon_data)
    assert resp.status_code == 201, f"创建优惠券失败: {resp.status_code} {resp.text}"
    coupon_id = resp.json()["id"]

    pub_resp = api_session.post(
        f"{base_url}{PUBLISH_PATH.format(coupon_id=coupon_id)}"
    )
    assert pub_resp.status_code in (200, 201), (
        f"发布优惠券失败: {pub_resp.status_code} {pub_resp.text}"
    )
    return coupon_id
```

---

# test_create_coupon.py

```python
"""创建优惠券接口 POST /api/v1/coupons 浀"""
import uuid

import pytest
import requests

from config import COUPONS_PATH


# ── 正向用例 ───────────────────────────────────────────────

class TestCreateCouponPositive:
    """创建优惠券 - 正向场景"""

    def test_create_success(self, create_coupon, valid_coupon_data):
        """创建成功返回 201，body 含 id 且 status=待发布"""
        resp = create_coupon(valid_coupon_data)
        assert resp.status_code == 201
        body = resp.json()
        assert "id" in body
        assert body["status"] == "待发布"

    def test_threshold_zero_ignores_amount(self, create_coupon, unique_name):
        """threshold=0 时不校验门槛与面额关系"""
        resp = create_coupon({
            "name": unique_name,
            "amount": 100,
            "threshold": 0,
            "total": 1000,
        })
        assert resp.status_code == 201

    def test_amount_boundary_min(self, create_coupon, unique_name):
        """amount 边界值 = 1"""
        resp = create_coupon({
            "name": unique_name,
            "amount": 1,
            "threshold": 0,
            "total": 1,
        })
        assert resp.status_code == 201

    def test_amount_boundary_max(self, create_coupon, unique_name):
        """amount 边界值 = 1000"""
        resp = create_coupon({
            "name": unique_name,
            "amount": 1000,
            "threshold": 1000,
            "total": 100000,
        })
        assert resp.status_code == 201

    def test_total_boundary_min(self, create_coupon, unique_name):
        """total 边界值 = 1"""
        resp = create_coupon({
            "name": unique_name,
            "amount": 1,
            "threshold": 0,
            "total": 1,
        })
        assert resp.status_code == 201

    def test_total_boundary_max(self, create_coupon, unique_name):
        """total 边界值 = 100000"""
        resp = create_coupon({
            "name": unique_name,
            "amount": 1,
            "threshold": 0,
            "total": 100000,
        })
        assert resp.status_code == 201

    def test_name_max_length(self, create_coupon):
        """name 长度 = 20（边界值，有效）"""
        resp = create_coupon({
            "name": uuid.uuid4().hex[:20],
            "amount": 50,
            "threshold": 50,
            "total": 100,
        })
        assert resp.status_code == 201

    def test_threshold_equal_amount(self, create_coupon, unique_name):
        """threshold 非 0 且等于 amount（边界值，有效）"""
        resp = create_coupon({
            "name": unique_name,
            "amount": 100,
            "threshold": 100,
            "total": 100,
        })
        assert resp.status_code == 201

    def test_threshold_greater_than_amount(self, create_coupon, unique_name):
        """threshold 非 0 且大于 amount（有效）"""
        resp = create_coupon({
            "name": unique_name,
            "amount": 50,
            "threshold": 200,
            "total": 100,
        })
        assert resp.status_code == 201


# ── 认证用例 ───────────────────────────────────────────────

class TestCreateCouponAuth:
    """创建优惠券 - 认证场景"""

    def test_no_token_returns_401(self, base_url, valid_coupon_data):
        """未携带 Token 返回 401"""
        resp = requests.post(f"{base_url}{COUPONS_PATH}", json=valid_coupon_data)
        assert resp.status_code == 401

    def test_invalid_token_returns_401(self, base_url, valid_coupon_data):
        """无效 Token 返回 401"""
        resp = requests.post(
            f"{base_url}{COUPONS_PATH}",
            json=valid_coupon_data,
            headers={"Authorization": "Bearer invalid_token_xxx"},
        )
        assert resp.status_code == 401


# ── 参数校验用例 ───────────────────────────────────────────

class TestCreateCouponValidation:
    """创建优惠券 - 参数校验场景"""

    # ─ 缺少必填字段 ─

    @pytest.mark.parametrize("missing_field", ["name", "amount", "threshold", "total"])
    def test_missing_required_field(self, create_coupon, valid_coupon_data, missing_field):
        """缺少必填字段 {missing_field} 返回 400"""
        data = valid_coupon_data.copy()
        del data[missing_field]
        resp = create_coupon(data)
        assert resp.status_code == 400

    # ─ amount 范围 ─

    @pytest.mark.parametrize("amount", [0, -1, 1001], ids=["zero", "negative", "exceed_max"])
    def test_amount_out_of_range(self, create_coupon, unique_name, amount):
        """amount={amount} 超出 [1, 1000] 范围返回 400"""
        resp = create_coupon({
            "name": unique_name,
            "amount": amount,
            "threshold": 0,
            "total": 100,
        })
        assert resp.status_code == 400

    # ─ total 范围 ─

    @pytest.mark.parametrize("total", [0, -1, 100001], ids=["zero", "negative", "exceed_max"])
    def test_total_out_of_range(self, create_coupon, unique_name, total):
        """total={total} 超出 [1, 100000] 范围返回 400"""
        resp = create_coupon({
            "name": unique_name,
            "amount": 10,
            "threshold": 0,
            "total": total,
        })
        assert resp.status_code == 400

    # ─ threshold 校验 ─

    def test_threshold_negative(self, create_coupon, unique_name):
        """threshold 为负数返回 400"""
        resp = create_coupon({
            "name": unique_name,
            "amount": 10,
            "threshold": -1,
            "total": 100,
        })
        assert resp.status_code == 400

    def test_threshold_less_than_amount(self, create_coupon, unique_name):
        """threshold 非 0 且小于 amount 返回 400，code=THRESHOLD_INVALID"""
        resp = create_coupon({
            "name": unique_name,
            "amount": 100,
            "threshold": 50,
            "total": 100,
        })
        assert resp.status_code == 400
        assert resp.json().get("code") == "THRESHOLD_INVALID"

    def test_threshold_just_below_amount(self, create_coupon, unique_name):
        """threshold=99, amount=100（边界值，仅差 1，无效）"""
        resp = create_coupon({
            "name": unique_name,
            "amount": 100,
            "threshold": 99,
            "total": 100,
        })
        assert resp.status_code == 400
        assert resp.json().get("code") == "THRESHOLD_INVALID"

    # ─ name 校验 ─

    def test_name_exceeds_max_length(self, create_coupon):
        """name 长度超过 20 返回 400"""
        resp = create_coupon({
            "name": "a" * 21,
            "amount": 10,
            "threshold": 0,
            "total": 100,
        })
        assert resp.status_code == 400

    def test_name_empty_string(self, create_coupon):
        """name 为空字符串返回 400"""
        resp = create_coupon({
            "name": "",
            "amount": 10,
            "threshold": 0,
            "total": 100,
        })
        assert resp.status_code == 400

    def test_name_duplicated(self, create_coupon, valid_coupon_data):
        """同商户名称重复返回 400，code=NAME_DUPLICATED"""
        resp1 = create_coupon(valid_coupon_data)
        assert resp1.status_code == 201

        resp2 = create_coupon(valid_coupon_data)
        assert resp2.status_code == 400
        assert resp2.json().get("code") == "NAME_DUPLICATED"

    # ─ 类型校验 ─

    def test_amount_as_string(self, create_coupon, unique_name):
        """amount 传入字符串类型返回 400"""
        resp = create_coupon({
            "name": unique_name,
            "amount": "100",
            "threshold": 0,
            "total": 100,
        })
        assert resp.status_code == 400

    def test_amount_as_float(self, create_coupon, unique_name):
        """amount 传入浮点数类型返回 400"""
        resp = create_coupon({
            "name": unique_name,
            "amount": 10.5,
            "threshold": 0,
            "total": 100,
        })
        assert resp.status_code == 400
```

---

# test_claim_coupon.py

```python
"""领取优惠券接口 POST /api/v1/coupons/{id}/claim 测试"""
import pytest
import requests

from config import CLAIM_PATH


def _claim_url(base_url, coupon_id):
    return f"{base_url}{CLAIM_PATH.format(coupon_id=coupon_id)}"


# ── 正向用例 ───────────────────────────────────────────────

class TestClaimCouponPositive:
    """领取优惠券 - 正向场景"""

    def test_claim_success(self, base_url, api_session, published_coupon_id):
        """领取已发布优惠券成功，返回 200，body 含 user_coupon_id"""
        resp = api_session.post(_claim_url(base_url, published_coupon_id))
        assert resp.status_code == 200
        body = resp.json()
        assert "user_coupon_id" in body


# ── 认证用例 ───────────────────────────────────────────────

class TestClaimCouponAuth:
    """领取优惠券 - 认证场景"""

    def test_no_token_returns_401(self, base_url, published_coupon_id):
        """未携带 Token 返回 401"""
        resp = requests.post(_claim_url(base_url, published_coupon_id))
        assert resp.status_code == 401

    def test_invalid_token_returns_401(self, base_url, published_coupon_id):
        """无效 / 过期 Token 返回 401"""
        resp = requests.post(
            _claim_url(base_url, published_coupon_id),
            headers={"Authorization": "Bearer expired_or_invalid_token"},
        )
        assert resp.status_code == 401


# ── 券不存在或已结束 ─────────────────────────────────────

class TestClaimCouponNotFound:
    """领取优惠券 - 404 场景"""

    def test_claim_nonexistent_coupon(self, base_url, api_session):
        """领取不存在的券返回 404"""
        resp = api_session.post(
            _claim_url(base_url, "nonexistent_coupon_id_99999")
        )
        assert resp.status_code == 404

    def test_claim_unpublished_coupon(self, base_url, api_session, create_coupon, valid_coupon_data):
        """领取待发布（未发布）状态的券返回 404"""
        resp = create_coupon(valid_coupon_data)
        assert resp.status_code == 201
        coupon_id = resp.json()["id"]

        claim_resp = api_session.post(_claim_url(base_url, coupon_id))
        assert claim_resp.status_code == 404


# ── 限领数量 ───────────────────────────────────────────────

class TestClaimCouponLimit:
    """领取优惠券 - 限领场景"""

    def test_claim_exceeds_limit(self, base_url, api_session, published_coupon_id):
        """每人限领 3 张：前 3 次成功，第 4 次返回 409"""
        for i in range(3):
            resp = api_session.post(_claim_url(base_url, published_coupon_id))
            assert resp.status_code == 200, f"第 {i + 1} 次领取应成功，实际: {resp.status_code}"

        resp_4th = api_session.post(_claim_url(base_url, published_coupon_id))
        assert resp_4th.status_code == 409

    def test_claim_response_body_structure(self, base_url, api_session, published_coupon_id):
        """领取成功响应体包含 user_coupon_id"""
        resp = api_session.post(_claim_url(base_url, published_coupon_id))
        assert resp.status_code == 200
        body = resp.json()
        assert "user_coupon_id" in body
        assert body["user_coupon_id"]  # 非空
```

---

# 待澄清清单

1. **登录接口路径与请求/响应格式**：OpenAPI 片段未包含登录端点。脚本假设 `POST /api/v1/auth/login`，请求体 `{"username", "password"}`，响应体含 `token` 或 `access_token` 字段。若实际不同需调整 `conftest.py`。

2. **发布优惠券接口**：创建后状态为「待发布」，但领取要求「已发布」。脚本假设存在 `POST /api/v1/coupons/{id}/publish`。若发布方式不同（如创建时传 status 参数、或通过其他端点），需调整 `published_coupon_id` fixture。

3. **「每人限领 3 张」的粒度**：是指同一张券每人限领 3 张，还是同一用户所有券合计限领 3 张？脚本按「同一张券每人限领 3 张」编写。若为全局限额，需补充跨券领取场景。

4. **商户标识**：业务规则提到「同商户唯一」，但 OpenAPI 中创建优惠券请求体无商户字段。是否通过 Token 自动关联商户？

5. **400 响应体结构**：OpenAPI 标注 `body: {code, message}`，脚本对 `THRESHOLD_INVALID` 和 `NAME_DUPLICATED` 断言了 `code` 字段。其余 400 用例仅断言状态码，是否需要统一断言 `code`/`message`？

6. **测试数据清理**：未提供删除优惠券接口，测试产生的数据无法自动清理。是否存在 `DELETE /api/v1/coupons/{id}` 或其他清理机制？

7. **领取响应体完整字段**：OpenAPI 仅说明 body 含 `user_coupon_id`，是否还有其他字段（如 coupon_id、expire_time 等）需要验证？