```
# conftest.py
import os
import time
import uuid

import pytest
import requests

API_BASE_URL = os.environ.get("API_BASE_URL", "https://api.example.test")
API_USER = os.environ.get("API_USER")
API_PASSWORD = os.environ.get("API_PASSWORD")


@pytest.fixture(scope="session")
def base_url():
    """返回 API 基础地址"""
    return API_BASE_URL


@pytest.fixture(scope="session")
def auth_token():
    """登录获取 Bearer Token"""
    login_url = f"{API_BASE_URL}/api/v1/auth/login"
    resp = requests.post(login_url, json={
        "username": API_USER,
        "password": API_PASSWORD,
    })
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
    """生成唯一优惠券名称（避免同商户重名）"""
    return f"测试券_{int(time.time())}_{uuid.uuid4().hex[:8]}"


@pytest.fixture
def create_coupon(auth_headers):
    """创建优惠券工厂函数，返回 requests.Response"""
    def _create(name=None, amount=100, threshold=200, total=1000):
        url = f"{API_BASE_URL}/api/v1/coupons"
        payload = {
            "name": name or f"测试券_{int(time.time())}_{uuid.uuid4().hex[:8]}",
            "amount": amount,
            "threshold": threshold,
            "total": total,
        }
        return requests.post(url, json=payload, headers=auth_headers)
    return _create


@pytest.fixture
def published_coupon(auth_headers, unique_name):
    """创建并发布一张优惠券，返回包含 id 的字典

    注意：OpenAPI 文档未提供发布接口，此处假设存在
    POST /api/v1/coupons/{id}/publish（待澄清）。
    """
    create_url = f"{API_BASE_URL}/api/v1/coupons"
    payload = {
        "name": unique_name,
        "amount": 100,
        "threshold": 200,
        "total": 1000,
    }
    resp = requests.post(create_url, json=payload, headers=auth_headers)
    assert resp.status_code == 201, f"创建优惠券失败: {resp.status_code} {resp.text}"
    data = resp.json()
    coupon_id = data["id"]

    publish_url = f"{API_BASE_URL}/api/v1/coupons/{coupon_id}/publish"
    pub_resp = requests.post(publish_url, headers=auth_headers)
    assert pub_resp.status_code == 200, f"发布优惠券失败: {pub_resp.status_code} {pub_resp.text}"

    data["status"] = "已发布"
    return data
```

```
# test_create_coupon.py
import os

import pytest
import requests

API_BASE_URL = os.environ.get("API_BASE_URL", "https://api.example.test")

CREATE_URL = f"{API_BASE_URL}/api/v1/coupons"


class TestCreateCoupon:
    """POST /api/v1/coupons — 创建优惠券"""

    # ==================== 正向用例 ====================

    def test_create_success(self, auth_headers, unique_name):
        """正常创建优惠券：返回 201，body 含 id 且 status=待发布"""
        payload = {
            "name": unique_name,
            "amount": 100,
            "threshold": 200,
            "total": 1000,
        }
        resp = requests.post(CREATE_URL, json=payload, headers=auth_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert "id" in data
        assert data["status"] == "待发布"

    def test_create_threshold_zero(self, auth_headers, unique_name):
        """门槛为 0 时允许创建（业务规则：门槛非 0 时才校验 ≥ 面额）"""
        payload = {
            "name": unique_name,
            "amount": 100,
            "threshold": 0,
            "total": 1000,
        }
        resp = requests.post(CREATE_URL, json=payload, headers=auth_headers)
        assert resp.status_code == 201

    def test_create_threshold_equals_amount(self, auth_headers, unique_name):
        """门槛等于面额时允许创建（边界值：threshold == amount）"""
        payload = {
            "name": unique_name,
            "amount": 100,
            "threshold": 100,
            "total": 1000,
        }
        resp = requests.post(CREATE_URL, json=payload, headers=auth_headers)
        assert resp.status_code == 201

    def test_create_name_max_length_boundary(self, auth_headers):
        """名称恰好 20 字符（边界值）"""
        payload = {
            "name": "a" * 20,
            "amount": 1,
            "threshold": 1,
            "total": 1,
        }
        resp = requests.post(CREATE_URL, json=payload, headers=auth_headers)
        assert resp.status_code == 201

    def test_create_amount_min_boundary(self, auth_headers, unique_name):
        """面额最小值 1（边界值）"""
        payload = {
            "name": unique_name,
            "amount": 1,
            "threshold": 1,
            "total": 1,
        }
        resp = requests.post(CREATE_URL, json=payload, headers=auth_headers)
        assert resp.status_code == 201

    def test_create_amount_max_boundary(self, auth_headers, unique_name):
        """面额最大值 1000（边界值）"""
        payload = {
            "name": unique_name,
            "amount": 1000,
            "threshold": 1000,
            "total": 100000,
        }
        resp = requests.post(CREATE_URL, json=payload, headers=auth_headers)
        assert resp.status_code == 201

    def test_create_total_min_boundary(self, auth_headers, unique_name):
        """总量最小值 1（边界值）"""
        payload = {
            "name": unique_name,
            "amount": 1,
            "threshold": 1,
            "total": 1,
        }
        resp = requests.post(CREATE_URL, json=payload, headers=auth_headers)
        assert resp.status_code == 201

    def test_create_total_max_boundary(self, auth_headers, unique_name):
        """总量最大值 100000（边界值）"""
        payload = {
            "name": unique_name,
            "amount": 1,
            "threshold": 1,
            "total": 100000,
        }
        resp = requests.post(CREATE_URL, json=payload, headers=auth_headers)
        assert resp.status_code == 201

    # ==================== 认证相关 ====================

    def test_create_without_auth_header(self, unique_name):
        """未携带 Authorization 头返回 401"""
        payload = {
            "name": unique_name,
            "amount": 100,
            "threshold": 200,
            "total": 1000,
        }
        resp = requests.post(CREATE_URL, json=payload)
        assert resp.status_code == 401

    def test_create_with_invalid_token(self, unique_name):
        """携带无效 Token 返回 401"""
        payload = {
            "name": unique_name,
            "amount": 100,
            "threshold": 200,
            "total": 1000,
        }
        headers = {"Authorization": "Bearer invalid_or_expired_token_xxx"}
        resp = requests.post(CREATE_URL, json=payload, headers=headers)
        assert resp.status_code == 401

    # ==================== 必填字段缺失 ====================

    @pytest.mark.parametrize("missing_field", ["name", "amount", "threshold", "total"])
    def test_create_missing_required_field(self, auth_headers, unique_name, missing_field):
        """缺少必填字段返回 400"""
        payload = {
            "name": unique_name,
            "amount": 100,
            "threshold": 200,
            "total": 1000,
        }
        del payload[missing_field]
        resp = requests.post(CREATE_URL, json=payload, headers=auth_headers)
        assert resp.status_code == 400
        body = resp.json()
        assert "code" in body
        assert "message" in body

    # ==================== 字段格式 / 值越界 ====================

    def test_create_name_too_long(self, auth_headers):
        """名称超过 20 字符返回 400"""
        payload = {
            "name": "a" * 21,
            "amount": 100,
            "threshold": 200,
            "total": 1000,
        }
        resp = requests.post(CREATE_URL, json=payload, headers=auth_headers)
        assert resp.status_code == 400

    def test_create_amount_below_minimum(self, auth_headers, unique_name):
        """面额 < 1 返回 400"""
        payload = {
            "name": unique_name,
            "amount": 0,
            "threshold": 0,
            "total": 1000,
        }
        resp = requests.post(CREATE_URL, json=payload, headers=auth_headers)
        assert resp.status_code == 400

    def test_create_amount_above_maximum(self, auth_headers, unique_name):
        """面额 > 1000 返回 400"""
        payload = {
            "name": unique_name,
            "amount": 1001,
            "threshold": 1001,
            "total": 1000,
        }
        resp = requests.post(CREATE_URL, json=payload, headers=auth_headers)
        assert resp.status_code == 400

    def test_create_threshold_negative(self, auth_headers, unique_name):
        """门槛为负数返回 400"""
        payload = {
            "name": unique_name,
            "amount": 100,
            "threshold": -1,
            "total": 1000,
        }
        resp = requests.post(CREATE_URL, json=payload, headers=auth_headers)
        assert resp.status_code == 400

    def test_create_total_below_minimum(self, auth_headers, unique_name):
        """总量 < 1 返回 400"""
        payload = {
            "name": unique_name,
            "amount": 100,
            "threshold": 200,
            "total": 0,
        }
        resp = requests.post(CREATE_URL, json=payload, headers=auth_headers)
        assert resp.status_code == 400

    def test_create_total_above_maximum(self, auth_headers, unique_name):
        """总量 > 100000 返回 400"""
        payload = {
            "name": unique_name,
            "amount": 100,
            "threshold": 200,
            "total": 100001,
        }
        resp = requests.post(CREATE_URL, json=payload, headers=auth_headers)
        assert resp.status_code == 400

    # ==================== 业务规则 ====================

    def test_create_name_duplicated(self, auth_headers, unique_name):
        """名称同商户重复返回 400，code=NAME_DUPLICATED"""
        payload = {
            "name": unique_name,
            "amount": 100,
            "threshold": 200,
            "total": 1000,
        }
        # 第一次创建 — 成功
        resp1 = requests.post(CREATE_URL, json=payload, headers=auth_headers)
        assert resp1.status_code == 201

        # 第二次创建同名 — 400
        resp2 = requests.post(CREATE_URL, json=payload, headers=auth_headers)
        assert resp2.status_code == 400
        assert resp2.json()["code"] == "NAME_DUPLICATED"

    def test_create_threshold_less_than_amount(self, auth_headers, unique_name):
        """门槛非 0 且 < 面额返回 400，code=THRESHOLD_INVALID"""
        payload = {
            "name": unique_name,
            "amount": 100,
            "threshold": 50,
            "total": 1000,
        }
        resp = requests.post(CREATE_URL, json=payload, headers=auth_headers)
        assert resp.status_code == 400
        assert resp.json()["code"] == "THRESHOLD_INVALID"
```

```
# test_claim_coupon.py
import os

import pytest
import requests

API_BASE_URL = os.environ.get("API_BASE_URL", "https://api.example.test")

CREATE_URL = f"{API_BASE_URL}/api/v1/coupons"


def _claim_url(coupon_id):
    return f"{API_BASE_URL}/api/v1/coupons/{coupon_id}/claim"


class TestClaimCoupon:
    """POST /api/v1/coupons/{id}/claim — 领取优惠券"""

    # ==================== 正向用例 ====================

    def test_claim_success(self, auth_headers, published_coupon):
        """正常领取已发布优惠券：返回 200，body 含 user_coupon_id"""
        coupon_id = published_coupon["id"]
        resp = requests.post(_claim_url(coupon_id), headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "user_coupon_id" in data

    # ==================== 认证相关 ====================

    def test_claim_without_auth_header(self, published_coupon):
        """未携带 Token 领取返回 401"""
        coupon_id = published_coupon["id"]
        resp = requests.post(_claim_url(coupon_id))
        assert resp.status_code == 401

    def test_claim_with_invalid_token(self, published_coupon):
        """携带无效 / 过期 Token 领取返回 401"""
        coupon_id = published_coupon["id"]
        headers = {"Authorization": "Bearer invalid_or_expired_token_xxx"}
        resp = requests.post(_claim_url(coupon_id), headers=headers)
        assert resp.status_code == 401

    # ==================== 券不存在 / 状态非已发布 ====================

    def test_claim_nonexistent_coupon(self, auth_headers):
        """领取不存在的券返回 404"""
        resp = requests.post(_claim_url("nonexistent_coupon_id_9999"), headers=auth_headers)
        assert resp.status_code == 404

    def test_claim_unpublished_coupon(self, auth_headers, create_coupon):
        """领取待发布（未发布）的券返回 404"""
        resp = create_coupon()
        assert resp.status_code == 201
        coupon_id = resp.json()["id"]

        resp = requests.post(_claim_url(coupon_id), headers=auth_headers)
        assert resp.status_code == 404

    # ==================== 超过限领数量 ====================

    def test_claim_exceed_limit(self, auth_headers, published_coupon):
        """每人限领 3 张，第 4 次领取返回 409

        前提假设：限领 3 张是针对同一张券的每人限制（待澄清）。
        若为全局限制，需使用不同用户账号避免用例间干扰。
        """
        coupon_id = published_coupon["id"]

        # 前 3 次领取 — 200
        for i in range(3):
            resp = requests.post(_claim_url(coupon_id), headers=auth_headers)
            assert resp.status_code == 200, (
                f"第 {i + 1} 次领取应成功，实际状态码: {resp.status_code}, 响应: {resp.text}"
            )

        # 第 4 次 — 409
        resp = requests.post(_claim_url(coupon_id), headers=auth_headers)
        assert resp.status_code == 409

    def test_claim_repeated_to_limit(self, auth_headers, published_coupon):
        """重复领取同一张券到上限后返回 409

        领取同一张券 3 次后，第 4 次返回 409（验证重复领取场景）。
        """
        coupon_id = published_coupon["id"]

        # 重复领取同一张券 3 次
        for i in range(3):
            resp = requests.post(_claim_url(coupon_id), headers=auth_headers)
            assert resp.status_code == 200, (
                f"第 {i + 1} 次领取应成功，实际状态码: {resp.status_code}"
            )

        # 第 4 次重复领取 — 409
        resp = requests.post(_claim_url(coupon_id), headers=auth_headers)
        assert resp.status_code == 409
```

```
# 待澄清清单
1. 发布接口：OpenAPI 文档仅包含「创建」和「领取」两个接口，创建后券状态为「待发布」，
   但领取测试需要「已发布」状态的券。代码中假设存在 POST /api/v1/coupons/{id}/publish
   发布接口，请确认实际接口路径与请求方式。

2. 登录接口：代码中假设 POST /api/v1/auth/login（body: {username, password}）
   用于获取 Bearer Token，请确认实际登录接口路径与请求/响应格式（token 字段名）。

3. 限领规则范围：「每人限领 3 张」是同一张券的每人限制，还是该用户全局总领取数限制？
   - 若为全局限制，不同测试用例间会互相干扰（同一测试账号领取次数累计），需要：
     a) 提供多个测试账号；或
     b) 提供重置用户领取记录的接口；或
     c) 在测试前清理/重置数据。
   - 当前代码按「同一张券每人限领 3 张」实现。

4. 优惠券删除/清理：是否提供删除优惠券或重置数据的接口？以便测试完成后清理
   NAME_DUPLICATED 等持久化数据，避免后续测试运行受影响。

5. 400 错误响应结构：OpenAPI 文档标注 400 响应 body 含 {code, message}，
   请确认 code 字段除 NAME_DUPLICATED / THRESHOLD_INVALID 外，参数校验类错误
   （如字段缺失、越界）的 code 值命名规范，以便补充断言。

6. 优惠券 ID 格式：路径参数 id 的类型为 string，请确认实际 ID 格式（UUID / 自增数字
   字符串等），以便构造不存在的 ID 测试用例更贴近真实场景。
```