## 文件：requirements.txt

```txt
pytest>=7.0
requests>=2.28
```

---

## 文件：conftest.py

```python
import os
import uuid

import pytest
import requests


@pytest.fixture(scope="session")
def base_url():
    """API 基础地址，通过环境变量 API_BASE_URL 注入"""
    return os.environ.get("API_BASE_URL", "https://api.example.test")


@pytest.fixture(scope="session")
def auth_token(base_url):
    """通过登录接口获取 Bearer Token，整个测试会话复用"""
    user = os.environ.get("API_USER")
    password = os.environ.get("API_PASSWORD")
    assert user and password, "请设置环境变量 API_USER 和 API_PASSWORD"

    resp = requests.post(
        f"{base_url}/api/v1/auth/login",
        json={"username": user, "password": password},
    )
    assert resp.status_code == 200, f"登录失败: {resp.status_code} {resp.text}"

    data = resp.json()
    token = data.get("token") or data.get("access_token")
    assert token, "登录响应中未找到 token / access_token"
    return token


@pytest.fixture(scope="session")
def auth_headers(auth_token):
    """携带 Bearer Token 的请求头"""
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture
def unique_name():
    """生成唯一的优惠券名称（不超过 20 字符）"""
    return f"测试券_{uuid.uuid4().hex[:12]}"


@pytest.fixture
def make_coupon_payload(unique_name):
    """构造优惠券创建 payload 的工厂函数，可通过 kwargs 覆盖默认值"""
    def _make(**overrides):
        payload = {
            "name": unique_name,
            "amount": 100,
            "threshold": 100,
            "total": 1000,
        }
        payload.update(overrides)
        return payload
    return _make


@pytest.fixture
def create_coupon(base_url, auth_headers):
    """发送创建优惠券请求，返回 Response 对象。
    默认携带认证头；传入 headers={} 可模拟未认证。"""
    def _create(payload, headers=None):
        return requests.post(
            f"{base_url}/api/v1/coupons",
            json=payload,
            headers=headers if headers is not None else auth_headers,
        )
    return _create


@pytest.fixture
def publish_coupon(base_url, auth_headers):
    """发布优惠券（假设接口: POST /api/v1/coupons/{id}/publish）"""
    def _publish(coupon_id):
        return requests.post(
            f"{base_url}/api/v1/coupons/{coupon_id}/publish",
            headers=auth_headers,
        )
    return _publish


@pytest.fixture
def claim_coupon(base_url, auth_headers):
    """发送领取优惠券请求，返回 Response 对象。
    默认携带认证头；传入 headers={} 可模拟未认证。"""
    def _claim(coupon_id, headers=None):
        return requests.post(
            f"{base_url}/api/v1/coupons/{coupon_id}/claim",
            headers=headers if headers is not None else auth_headers,
        )
    return _claim


@pytest.fixture
def published_coupon_id(create_coupon, publish_coupon, make_coupon_payload):
    """创建并发布一张优惠券，返回 coupon_id（用于领取测试）"""
    payload = make_coupon_payload()
    resp = create_coupon(payload)
    assert resp.status_code == 201, f"创建优惠券失败: {resp.status_code} {resp.text}"
    body = resp.json()
    coupon_id = str(body["id"])
    assert body.get("status") == "待发布", f"初始状态应为'待发布'，实际: {body.get('status')}"

    pub_resp = publish_coupon(coupon_id)
    assert pub_resp.status_code in (200, 204), f"发布优惠券失败: {pub_resp.status_code} {pub_resp.text}"
    return coupon_id
```

---

## 文件：test_create_coupon.py

```python
import pytest


class TestCreateCoupon:
    """POST /api/v1/coupons — 创建优惠券"""

    # ==================== 正向用例 ====================

    def test_create_success(self, create_coupon, make_coupon_payload):
        """正常创建优惠券，返回 201，body 含 id 和 status=待发布"""
        payload = make_coupon_payload()
        resp = create_coupon(payload)

        assert resp.status_code == 201
        body = resp.json()
        assert "id" in body, "响应体应包含 id"
        assert body.get("status") == "待发布", f"初始状态应为'待发布'，实际: {body.get('status')}"

    def test_create_with_threshold_zero(self, create_coupon, make_coupon_payload):
        """门槛为 0 时应创建成功（无门槛券）"""
        payload = make_coupon_payload(threshold=0)
        resp = create_coupon(payload)

        assert resp.status_code == 201
        assert "id" in resp.json()

    def test_create_threshold_equals_amount(self, create_coupon, make_coupon_payload):
        """门槛等于面额时应创建成功"""
        payload = make_coupon_payload(amount=50, threshold=50)
        resp = create_coupon(payload)

        assert resp.status_code == 201
        assert "id" in resp.json()

    def test_create_threshold_greater_than_amount(self, create_coupon, make_coupon_payload):
        """门槛大于面额时应创建成功"""
        payload = make_coupon_payload(amount=50, threshold=200)
        resp = create_coupon(payload)

        assert resp.status_code == 201
        assert "id" in resp.json()

    # ==================== 认证用例 ====================

    def test_create_without_token(self, create_coupon, make_coupon_payload):
        """未携带 Token 创建优惠券，返回 401"""
        payload = make_coupon_payload()
        resp = create_coupon(payload, headers={})

        assert resp.status_code == 401

    # ==================== 必填字段缺失 ====================

    @pytest.mark.parametrize("missing_field", ["name", "amount", "threshold", "total"])
    def test_create_missing_required_field(self, create_coupon, make_coupon_payload, missing_field):
        """缺少任一必填字段，返回 400，body 含 code 和 message"""
        payload = make_coupon_payload()
        del payload[missing_field]
        resp = create_coupon(payload)

        assert resp.status_code == 400
        body = resp.json()
        assert "code" in body, "400 响应应包含 code"
        assert "message" in body, "400 响应应包含 message"

    # ==================== 字段约束 ====================

    def test_create_name_exceeds_max_length(self, create_coupon, make_coupon_payload):
        """名称超过 20 字符，返回 400"""
        payload = make_coupon_payload(name="测" * 21)
        resp = create_coupon(payload)

        assert resp.status_code == 400

    def test_create_amount_below_minimum(self, create_coupon, make_coupon_payload):
        """面额小于 1，返回 400"""
        payload = make_coupon_payload(amount=0)
        resp = create_coupon(payload)

        assert resp.status_code == 400

    def test_create_amount_above_maximum(self, create_coupon, make_coupon_payload):
        """面额大于 1000，返回 400"""
        payload = make_coupon_payload(amount=1001)
        resp = create_coupon(payload)

        assert resp.status_code == 400

    def test_create_threshold_negative(self, create_coupon, make_coupon_payload):
        """门槛为负数，返回 400"""
        payload = make_coupon_payload(threshold=-1)
        resp = create_coupon(payload)

        assert resp.status_code == 400

    def test_create_total_below_minimum(self, create_coupon, make_coupon_payload):
        """总发行量小于 1，返回 400"""
        payload = make_coupon_payload(total=0)
        resp = create_coupon(payload)

        assert resp.status_code == 400

    def test_create_total_above_maximum(self, create_coupon, make_coupon_payload):
        """总发行量大于 100000，返回 400"""
        payload = make_coupon_payload(total=100001)
        resp = create_coupon(payload)

        assert resp.status_code == 400

    # ==================== 业务规则 ====================

    def test_create_name_duplicated(self, create_coupon, make_coupon_payload):
        """名称同商户重复，返回 400，code=NAME_DUPLICATED"""
        payload = make_coupon_payload()

        # 第一次创建 — 成功
        resp1 = create_coupon(payload)
        assert resp1.status_code == 201

        # 第二次使用相同名称 — 应返回 NAME_DUPLICATED
        resp2 = create_coupon(payload)
        assert resp2.status_code == 400
        body = resp2.json()
        assert body.get("code") == "NAME_DUPLICATED", \
            f"期望 code=NAME_DUPLICATED，实际: {body.get('code')}"

    def test_create_threshold_less_than_amount(self, create_coupon, make_coupon_payload):
        """门槛非 0 且小于面额，返回 400，code=THRESHOLD_INVALID"""
        payload = make_coupon_payload(amount=100, threshold=50)
        resp = create_coupon(payload)

        assert resp.status_code == 400
        body = resp.json()
        assert body.get("code") == "THRESHOLD_INVALID", \
            f"期望 code=THRESHOLD_INVALID，实际: {body.get('code')}"
```

---

## 文件：test_claim_coupon.py

```python
import uuid


class TestClaimCoupon:
    """POST /api/v1/coupons/{id}/claim — 领取优惠券"""

    # ==================== 正向用例 ====================

    def test_claim_success(self, claim_coupon, published_coupon_id):
        """正常领取已发布优惠券，返回 200，body 含 user_coupon_id"""
        resp = claim_coupon(published_coupon_id)

        assert resp.status_code == 200
        body = resp.json()
        assert "user_coupon_id" in body, "响应体应包含 user_coupon_id"

    # ==================== 认证用例 ====================

    def test_claim_without_token(self, claim_coupon, published_coupon_id):
        """未携带 Token 领取优惠券，返回 401"""
        resp = claim_coupon(published_coupon_id, headers={})

        assert resp.status_code == 401

    # ==================== 券不存在 / 状态无效 ====================

    def test_claim_nonexistent_coupon(self, claim_coupon):
        """领取不存在的券，返回 404"""
        fake_id = str(uuid.uuid4())
        resp = claim_coupon(fake_id)

        assert resp.status_code == 404

    def test_claim_unpublished_coupon(self, claim_coupon, create_coupon, make_coupon_payload):
        """领取待发布（未发布）的券，返回 404"""
        payload = make_coupon_payload()
        resp = create_coupon(payload)
        assert resp.status_code == 201
        coupon_id = str(resp.json()["id"])

        # 不发布，直接领取
        resp = claim_coupon(coupon_id)
        assert resp.status_code == 404

    # ==================== 限领数量 ====================

    def test_claim_exceeds_per_user_limit(self, claim_coupon, published_coupon_id):
        """每人限领 3 张，前 3 次成功，第 4 次返回 409"""
        # 前三次领取应成功
        for i in range(3):
            resp = claim_coupon(published_coupon_id)
            assert resp.status_code == 200, \
                f"第 {i + 1} 次领取应成功，实际: {resp.status_code} {resp.text}"

        # 第四次领取应返回 409
        resp = claim_coupon(published_coupon_id)
        assert resp.status_code == 409
```

---

## 待澄清清单

1. **登录接口**：OpenAPI 文档未提供登录接口的定义。当前脚本假设登录路径为 `POST /api/v1/auth/login`，请求体为 `{"username": "...", "password": "..."}`，响应体包含 `token` 或 `access_token` 字段。需确认实际接口路径与字段名。

2. **优惠券发布接口**：业务规则提到"券状态非已发布返回 404"，创建后状态为"待发布"，但 OpenAPI 文档未提供发布接口。当前脚本假设发布路径为 `POST /api/v1/coupons/{id}/publish`，成功状态码为 200 或 204。需确认实际接口。

3. **"每人限领 3 张"的作用域**：是指同一张券每人限领 3 张，还是同一用户所有券合计限领 3 张？当前脚本假设为前者（同一张券）。若为后者，需要使用不同测试用户或提供清理机制来隔离测试。

4. **优惠券删除/清理接口**：文档未提供删除接口，测试创建的优惠券无法自动清理。长期运行可能产生脏数据，需确认是否有清理接口或方案。

5. **401 响应体格式**：文档仅描述 401 为"未认证"，未说明响应体结构。当前脚本仅校验状态码，如需校验响应体请提供格式说明。

6. **过期 Token 场景**：业务规则提到"过期返回 401"，但当前脚本未覆盖过期 Token 场景（需要可生成过期 Token 的机制或 mock）。需确认是否需要补充此场景及如何获取过期 Token。

7. **券已结束场景**：领取接口 404 描述为"券不存在或已结束"，但"已结束"的具体条件未明确（如总领取量达到 total、手动结束、过期等）。需确认"已结束"的定义以便补充对应测试。