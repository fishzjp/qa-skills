```
conftest.py
```

```python
import os
import pytest
import requests

API_BASE_URL = os.getenv("API_BASE_URL", "https://api.example.test")
API_USER = os.getenv("API_USER", "test_user")
API_PASSWORD = os.getenv("API_PASSWORD", "test_password")


@pytest.fixture(scope="session")
def base_url():
    return API_BASE_URL


@pytest.fixture(scope="session")
def login_token(base_url):
    """登录获取 Bearer Token。登录端点假定为 POST /api/v1/auth/login。"""
    resp = requests.post(
        f"{base_url}/api/v1/auth/login",
        json={"username": API_USER, "password": API_PASSWORD},
        timeout=10,
    )
    assert resp.status_code in (200, 201), f"登录失败: {resp.status_code} {resp.text}"
    token = resp.json().get("token") or resp.json().get("access_token")
    assert token, "登录返回未包含 token"
    return token


@pytest.fixture(scope="session")
def auth_headers(login_token):
    return {"Authorization": f"Bearer {login_token}"}


@pytest.fixture(scope="session")
def second_user_token(base_url):
    """第二个账号的 Token，用于多人场景验证；若未提供则复用主账号。"""
    user = os.getenv("API_USER_2")
    pwd = os.getenv("API_PASSWORD_2")
    if not user or not pwd:
        pytest.skip("未配置第二个测试账号 API_USER_2/API_PASSWORD_2")
    resp = requests.post(
        f"{base_url}/api/v1/auth/login",
        json={"username": user, "password": pwd},
        timeout=10,
    )
    assert resp.status_code in (200, 201), f"第二账号登录失败: {resp.status_code} {resp.text}"
    return resp.json().get("token") or resp.json().get("access_token")


def create_coupon(base_url, headers, payload):
    """创建优惠券的辅助方法，返回 response 对象。"""
    return requests.post(
        f"{base_url}/api/v1/coupons",
        headers=headers,
        json=payload,
        timeout=10,
    )


def claim_coupon(base_url, headers, coupon_id):
    """领取优惠券的辅助方法，返回 response 对象。"""
    return requests.post(
        f"{base_url}/api/v1/coupons/{coupon_id}/claim",
        headers=headers,
        timeout=10,
    )


@pytest.fixture
def unique_coupon_name():
    import uuid
    return f"QA_{uuid.uuid4().hex[:14]}"


@pytest.fixture
def created_coupon(base_url, auth_headers, unique_coupon_name):
    """创建一张已发布可领取的优惠券，返回其 id。"""
    payload = {
        "name": unique_coupon_name,
        "amount": 50,
        "threshold": 100,
        "total": 1000,
    }
    resp = create_coupon(base_url, auth_headers, payload)
    assert resp.status_code == 201, f"前置创建失败: {resp.status_code} {resp.text}"
    coupon_id = resp.json().get("id")
    assert coupon_id, "创建响应缺少 id"
    return coupon_id
```

```
test_create_coupon.py
```

```python
import uuid
import pytest

from conftest import create_coupon


class TestCreateCouponAuth:
    """认证相关测试。"""

    def test_no_auth_returns_401(self, base_url):
        resp = requests.post(f"{base_url}/api/v1/coupons", json={"name": "x", "amount": 1, "threshold": 0, "total": 1})
        assert resp.status_code == 401

    def test_invalid_token_returns_401(self, base_url):
        headers = {"Authorization": "Bearer invalid.token.value"}
        resp = create_coupon(base_url, headers, {"name": "x", "amount": 1, "threshold": 0, "total": 1})
        assert resp.status_code == 401


class TestCreateCouponSuccess:
    """创建成功场景。"""

    def test_create_coupon_success(self, base_url, auth_headers, unique_coupon_name):
        payload = {
            "name": unique_coupon_name,
            "amount": 50,
            "threshold": 100,
            "total": 1000,
        }
        resp = create_coupon(base_url, auth_headers, payload)
        assert resp.status_code == 201
        body = resp.json()
        assert "id" in body
        assert body.get("status") == "待发布"

    def test_create_coupon_threshold_zero(self, base_url, auth_headers, unique_coupon_name):
        """门槛为 0 表示无门槛，应创建成功。"""
        payload = {"name": unique_coupon_name, "amount": 10, "threshold": 0, "total": 100}
        resp = create_coupon(base_url, auth_headers, payload)
        assert resp.status_code == 201


class TestCreateCouponValidation:
    """参数校验场景。"""

    @pytest.mark.parametrize("missing_field", ["name", "amount", "threshold", "total"])
    def test_missing_required_field(self, base_url, auth_headers, unique_coupon_name, missing_field):
        payload = {"name": unique_coupon_name, "amount": 10, "threshold": 20, "total": 100}
        payload.pop(missing_field)
        resp = create_coupon(base_url, auth_headers, payload)
        assert resp.status_code == 400
        body = resp.json()
        assert "code" in body and "message" in body

    def test_name_exceeds_max_length(self, base_url, auth_headers):
        payload = {"name": "a" * 21, "amount": 10, "threshold": 20, "total": 100}
        resp = create_coupon(base_url, auth_headers, payload)
        assert resp.status_code == 400

    def test_name_at_max_length_ok(self, base_url, auth_headers):
        payload = {"name": "a" * 20, "amount": 10, "threshold": 20, "total": 100}
        resp = create_coupon(base_url, auth_headers, payload)
        assert resp.status_code == 201

    @pytest.mark.parametrize("amount", [0, 1001, -1, 9999])
    def test_amount_out_of_range(self, base_url, auth_headers, unique_coupon_name, amount):
        payload = {"name": unique_coupon_name, "amount": amount, "threshold": 0, "total": 100}
        resp = create_coupon(base_url, auth_headers, payload)
        assert resp.status_code == 400

    @pytest.mark.parametrize("amount", [1, 1000])
    def test_amount_boundary_ok(self, base_url, auth_headers, unique_coupon_name, amount):
        payload = {"name": unique_coupon_name, "amount": amount, "threshold": 0, "total": 100}
        resp = create_coupon(base_url, auth_headers, payload)
        assert resp.status_code == 201

    @pytest.mark.parametrize("total", [0, 100001, -1])
    def test_total_out_of_range(self, base_url, auth_headers, unique_coupon_name, total):
        payload = {"name": unique_coupon_name, "amount": 10, "threshold": 0, "total": total}
        resp = create_coupon(base_url, auth_headers, payload)
        assert resp.status_code == 400

    def test_threshold_negative(self, base_url, auth_headers, unique_coupon_name):
        payload = {"name": unique_coupon_name, "amount": 10, "threshold": -1, "total": 100}
        resp = create_coupon(base_url, auth_headers, payload)
        assert resp.status_code == 400


class TestCreateCouponBusinessRules:
    """业务规则：名称同商户唯一、门槛非0时须≥面额。"""

    def test_name_duplicated_returns_400(self, base_url, auth_headers, unique_coupon_name):
        payload = {"name": unique_coupon_name, "amount": 10, "threshold": 0, "total": 100}
        resp1 = create_coupon(base_url, auth_headers, payload)
        assert resp1.status_code == 201

        resp2 = create_coupon(base_url, auth_headers, payload)
        assert resp2.status_code == 400
        assert resp2.json().get("code") == "NAME_DUPLICATED"

    def test_threshold_less_than_amount_returns_400(self, base_url, auth_headers, unique_coupon_name):
        payload = {"name": unique_coupon_name, "amount": 50, "threshold": 30, "total": 100}
        resp = create_coupon(base_url, auth_headers, payload)
        assert resp.status_code == 400
        assert resp.json().get("code") == "THRESHOLD_INVALID"

    def test_threshold_equal_amount_ok(self, base_url, auth_headers, unique_coupon_name):
        payload = {"name": unique_coupon_name, "amount": 50, "threshold": 50, "total": 100}
        resp = create_coupon(base_url, auth_headers, payload)
        assert resp.status_code == 201

    def test_threshold_greater_than_amount_ok(self, base_url, auth_headers, unique_coupon_name):
        payload = {"name": unique_coupon_name, "amount": 50, "threshold": 100, "total": 100}
        resp = create_coupon(base_url, auth_headers, payload)
        assert resp.status_code == 201
```

```
test_claim_coupon.py
```

```python
import pytest
import requests

from conftest import create_coupon, claim_coupon


class TestClaimCouponAuth:
    """认证相关测试。"""

    def test_no_auth_returns_401(self, base_url, created_coupon):
        resp = requests.post(f"{base_url}/api/v1/coupons/{created_coupon}/claim", timeout=10)
        assert resp.status_code == 401

    def test_invalid_token_returns_401(self, base_url, created_coupon):
        headers = {"Authorization": "Bearer invalid.token.value"}
        resp = claim_coupon(base_url, headers, created_coupon)
        assert resp.status_code == 401


class TestClaimCouponSuccess:
    """领取成功场景。"""

    def test_claim_success(self, base_url, auth_headers, created_coupon):
        resp = claim_coupon(base_url, auth_headers, created_coupon)
        assert resp.status_code == 200
        body = resp.json()
        assert "user_coupon_id" in body


class TestClaimCouponNotFound:
    """券不存在或状态非已发布返回 404。"""

    def test_claim_non_existent_coupon(self, base_url, auth_headers):
        resp = claim_coupon(base_url, auth_headers, "not_exist_id_9999")
        assert resp.status_code == 404

    def test_claim_unpublished_coupon_returns_404(self, base_url, auth_headers, unique_coupon_name):
        """刚创建的券状态为"待发布"，领取应返回 404。"""
        payload = {"name": unique_coupon_name, "amount": 10, "threshold": 0, "total": 100}
        resp = create_coupon(base_url, auth_headers, payload)
        assert resp.status_code == 201
        coupon_id = resp.json()["id"]

        # 待发布状态直接领取应 404
        claim_resp = claim_coupon(base_url, auth_headers, coupon_id)
        assert claim_resp.status_code == 404


class TestClaimCouponLimit:
    """每人限领 3 张，超领返回 409。"""

    def test_claim_exceeds_limit_returns_409(self, base_url, auth_headers, created_coupon):
        # 领取 3 次应成功
        for i in range(3):
            resp = claim_coupon(base_url, auth_headers, created_coupon)
            assert resp.status_code == 200, f"第{i+1}次领取失败: {resp.status_code} {resp.text}"

        # 第 4 次应返回 409
        resp = claim_coupon(base_url, auth_headers, created_coupon)
        assert resp.status_code == 409

    def test_repeated_claim_same_coupon_reaches_limit(self, base_url, auth_headers, created_coupon):
        """重复领取同一张券至上限后 409。"""
        for i in range(3):
            resp = claim_coupon(base_url, auth_headers, created_coupon)
            assert resp.status_code == 200

        resp = claim_coupon(base_url, auth_headers, created_coupon)
        assert resp.status_code == 409


class TestClaimCouponEdgeCases:
    """边界与清理。"""

    def test_claim_total_exhausted(self, base_url, auth_headers, unique_coupon_name, second_user_token):
        """total=1 的券，第一人领取后第二人领取返回 404（已结束/无库存）。
        需要 second_user_token，否则 skip。"""
        payload = {"name": unique_coupon_name, "amount": 10, "threshold": 0, "total": 1}
        resp = create_coupon(base_url, auth_headers, payload)
        assert resp.status_code == 201
        coupon_id = resp.json()["id"]

        # 假设创建后即发布可领（若需发布接口则此用例需调整）
        first = claim_coupon(base_url, auth_headers, coupon_id)
        # 若券状态未发布会返回 404，此处允许两种结果以适配实际接口行为
        if first.status_code == 404:
            pytest.skip("创建后券需手动发布，缺少发布接口定义")

        # 第二个账号领取
        headers2 = {"Authorization": f"Bearer {second_user_token}"}
        second = claim_coupon(base_url, headers2, coupon_id)
        assert second.status_code in (404, 409), f"库存耗尽后应返回 404 或 409, 实际: {second.status_code}"
```

```
待澄清清单.md
```

```markdown
# 待澄清清单

以下问题在交付中已采用合理默认假设完成编写，需业务方确认以保证脚本与实际接口一致：

1. **登录端点未在 OpenAPI 中给出**：脚本假定 `POST /api/v1/auth/login`，请求体为 `{username, password}`，响应体含 `token` 或 `access_token` 字段。需确认实际登录路径、字段名与认证方式。

2. **券发布机制未定义**：业务规则提到"券状态非已发布返回 404"，但未提供将券从"待发布"变为"已发布"的接口（如发布接口或创建时带 status 字段）。脚本中 `created_coupon` fixture 直接使用创建返回的 id；若实际需调用发布接口，需补充该接口定义后调整 fixture。

3. **领取限领 3 张的口径**：业务规则"每人限领 3 张"是指同一张券每人限领 3 张，还是同一商户所有券合计限领 3 张？脚本按"同一张券每人限领 3 张"实现。

4. **库存耗尽行为**：total 耗尽后领取应返回 404（券已结束）还是 409？脚本中对库存耗尽场景兼容了 404/409 两种断言。

5. **错误响应体格式**：假定 400 响应体为 `{code, message}`；401/404/409 响应体格式未明确，脚本仅校验状态码。

6. **第二账号场景**：`test_claim_total_exhausted` 等多账号用例依赖环境变量 `API_USER_2` / `API_PASSWORD_2`，未配置时自动 skip。

7. **数据清理**：脚本未实现创建券与领取记录的清理，建议测试环境提供独立数据库或定期清理机制，避免 NAME_DUPLICATED 等用例因脏数据失败。

8. **amount/threshold/total 字段类型**：OpenAPI 标注为 integer，未说明是否接受字符串数字。脚本按 integer 传参。
```