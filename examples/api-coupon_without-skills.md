--- conftest.py ---
```python
import pytest
import requests
import os
import random
import string

@pytest.fixture(scope="session")
def api_base_url():
    return os.environ.get("API_BASE_URL", "https://api.example.test")

@pytest.fixture(scope="session")
def auth_token(api_base_url):
    username = os.environ.get("API_USER")
    password = os.environ.get("API_PASSWORD")
    if not username or not password:
        pytest.skip("API_USER and API_PASSWORD environment variables required")
    resp = requests.post(f"{api_base_url}/api/v1/auth/login", json={"username": username, "password": password})
    resp.raise_for_status()
    return resp.json()["token"]

@pytest.fixture(scope="session")
def auth_headers(auth_token):
    return {"Authorization": f"Bearer {auth_token}"}

@pytest.fixture(scope="function")
def random_name():
    return "test_" + ''.join(random.choices(string.ascii_letters, k=8))

@pytest.fixture(scope="function")
def created_coupon_id(auth_headers, api_base_url, random_name):
    payload = {
        "name": random_name,
        "amount": 100,
        "threshold": 0,
        "total": 1000
    }
    resp = requests.post(f"{api_base_url}/api/v1/coupons", json=payload, headers=auth_headers)
    resp.raise_for_status()
    return resp.json()["id"]

@pytest.fixture(scope="function")
def published_coupon_id(created_coupon_id, auth_headers, api_base_url):
    resp = requests.post(f"{api_base_url}/api/v1/coupons/{created_coupon_id}/publish", headers=auth_headers)
    resp.raise_for_status()
    return created_coupon_id
```

--- test_coupons.py ---
```python
import requests
import pytest

class TestCoupons:
    @pytest.fixture(autouse=True)
    def setup(self, api_base_url):
        self.base_url = api_base_url

    # 辅助方法
    def create_coupon(self, headers, **kwargs):
        default = {"name": "test_default", "amount": 100, "threshold": 0, "total": 1000}
        default.update(kwargs)
        return requests.post(f"{self.base_url}/api/v1/coupons", json=default, headers=headers)

    # 创建优惠券测试
    def test_create_success(self, auth_headers, random_name):
        resp = self.create_coupon(auth_headers, name=random_name)
        assert resp.status_code == 201
        data = resp.json()
        assert "id" in data
        assert data["status"] == "待发布"

    def test_create_duplicate_name(self, auth_headers, random_name):
        payload = {"name": random_name, "amount": 100, "threshold": 0, "total": 1000}
        resp1 = requests.post(f"{self.base_url}/api/v1/coupons", json=payload, headers=auth_headers)
        assert resp1.status_code == 201
        resp2 = requests.post(f"{self.base_url}/api/v1/coupons", json=payload, headers=auth_headers)
        assert resp2.status_code == 400
        assert resp2.json()["code"] == "NAME_DUPLICATED"

    def test_create_name_empty(self, auth_headers):
        resp = self.create_coupon(auth_headers, name="")
        assert resp.status_code == 400
        assert resp.json()["code"] == "NAME_INVALID"

    def test_create_name_blank(self, auth_headers):
        resp = self.create_coupon(auth_headers, name="   ")
        assert resp.status_code == 400
        assert resp.json()["code"] == "NAME_INVALID"

    def test_create_amount_below_min(self, auth_headers, random_name):
        resp = self.create_coupon(auth_headers, name=random_name, amount=0)
        assert resp.status_code == 400

    def test_create_amount_above_max(self, auth_headers, random_name):
        resp = self.create_coupon(auth_headers, name=random_name, amount=1001)
        assert resp.status_code == 400

    def test_create_threshold_invalid(self, auth_headers, random_name):
        resp = self.create_coupon(auth_headers, name=random_name, threshold=10, amount=5)
        assert resp.status_code == 400
        assert resp.json()["code"] == "THRESHOLD_INVALID"

    def test_create_threshold_zero(self, auth_headers, random_name):
        resp = self.create_coupon(auth_headers, name=random_name, threshold=0, amount=10)
        assert resp.status_code == 201

    def test_create_total_below_min(self, auth_headers, random_name):
        resp = self.create_coupon(auth_headers, name=random_name, total=0)
        assert resp.status_code == 400

    def test_create_total_above_max(self, auth_headers, random_name):
        resp = self.create_coupon(auth_headers, name=random_name, total=100001)
        assert resp.status_code == 400

    def test_create_unauthorized(self, random_name):
        resp = self.create_coupon({}, name=random_name)
        assert resp.status_code == 401

    # 发布优惠券测试
    def test_publish_success(self, created_coupon_id, auth_headers):
        resp = requests.post(f"{self.base_url}/api/v1/coupons/{created_coupon_id}/publish", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "已发布"

    def test_publish_idempotent(self, published_coupon_id, auth_headers):
        resp = requests.post(f"{self.base_url}/api/v1/coupons/{published_coupon_id}/publish", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "已发布"

    def test_publish_ended_coupon(self, auth_headers):
        resp = requests.post(f"{self.base_url}/api/v1/coupons/coupon-ended/publish", headers=auth_headers)
        assert resp.status_code == 404

    def test_publish_not_found(self, auth_headers):
        resp = requests.post(f"{self.base_url}/api/v1/coupons/nonexistent-id/publish", headers=auth_headers)
        assert resp.status_code == 404

    def test_publish_unauthorized(self, created_coupon_id):
        resp = requests.post(f"{self.base_url}/api/v1/coupons/{created_coupon_id}/publish", headers={})
        assert resp.status_code == 401

    # 领取优惠券测试
    def test_claim_success(self, published_coupon_id, auth_headers):
        resp = requests.post(f"{self.base_url}/api/v1/coupons/{published_coupon_id}/claim", headers=auth_headers)
        assert resp.status_code == 200
        assert "user_coupon_id" in resp.json()

    def test_claim_unpublished(self, created_coupon_id, auth_headers):
        resp = requests.post(f"{self.base_url}/api/v1/coupons/{created_coupon_id}/claim", headers=auth_headers)
        assert resp.status_code == 404

    def test_claim_ended_coupon(self, auth_headers):
        resp = requests.post(f"{self.base_url}/api/v1/coupons/coupon-ended/claim", headers=auth_headers)
        assert resp.status_code == 404

    def test_claim_not_found(self, auth_headers):
        resp = requests.post(f"{self.base_url}/api/v1/coupons/nonexistent-id/claim", headers=auth_headers)
        assert resp.status_code == 404

    def test_claim_exceed_limit(self, published_coupon_id, auth_headers):
        coupon_id = published_coupon_id
        for i in range(3):
            resp = requests.post(f"{self.base_url}/api/v1/coupons/{coupon_id}/claim", headers=auth_headers)
            assert resp.status_code == 200, f"第{i+1}次领取失败"
        resp = requests.post(f"{self.base_url}/api/v1/coupons/{coupon_id}/claim", headers=auth_headers)
        assert resp.status_code == 409

    def test_claim_unauthorized(self):
        resp = requests.post(f"{self.base_url}/api/v1/coupons/dummy-coupon-id/claim", headers={})
        assert resp.status_code == 401
```