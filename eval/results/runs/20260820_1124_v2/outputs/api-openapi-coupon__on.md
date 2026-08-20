## 文件: api-tests/requirements.txt
```text
pytest>=7.4
requests>=2.31
python-dotenv>=1.0
```

## 文件: api-tests/common/__init__.py
```python
```

## 文件: api-tests/common/client.py
```python
"""统一请求封装：超时、鉴权头、断言辅助。"""
import requests


class APIClient:
    def __init__(self, base_url, token=None, timeout=10):
        self.base_url = base_url
        self.timeout = timeout
        self.session = requests.Session()
        if token:
            self.session.headers.update({"Authorization": f"Bearer {token}"})

    def _url(self, path):
        return self.base_url + path

    def post(self, path, **kwargs):
        kwargs.setdefault("timeout", self.timeout)
        return self.session.post(self._url(path), **kwargs)

    def get(self, path, **kwargs):
        kwargs.setdefault("timeout", self.timeout)
        return self.session.get(self._url(path), **kwargs)

    def delete(self, path, **kwargs):
        kwargs.setdefault("timeout", self.timeout)
        return self.session.delete(self._url(path), **kwargs)


def assert_success(resp, status_code, **fields):
    """断言成功响应：状态码 + 关键字段（三件套之状态码 + 响应体）。"""
    assert resp.status_code == status_code, (
        f"预期状态码 {status_code}，实际 {resp.status_code}，响应: {resp.text}"
    )
    body = resp.json()
    for k, v in fields.items():
        assert body.get(k) == v, (
            f"字段 {k} 预期 {v!r}，实际 {body.get(k)!r}，完整响应: {body}"
        )
    return body


def assert_error(resp, status_code, code=None):
    """断言错误响应：状态码 + 业务码 + 响应体含 message（三件套）。"""
    assert resp.status_code == status_code, (
        f"预期状态码 {status_code}，实际 {resp.status_code}，响应: {resp.text}"
    )
    body = resp.json()
    assert "code" in body, f"响应体缺少 code 字段: {body}"
    assert "message" in body, f"响应体缺少 message 字段: {body}"
    if code is not None:
        assert body["code"] == code, (
            f"预期业务码 {code}，实际 {body.get('code')}，message: {body.get('message')}"
        )
    return body
```

## 文件: api-tests/conftest.py
```python
"""
API 测试公共 fixture。

环境变量（通过 .env 或 shell 注入，不硬编码）：
  API_BASE_URL   被测环境地址，如 https://api.example.test
  API_USER       测试账号
  API_PASSWORD   测试密码

登录接口、发布接口等未在 OpenAPI 中给出，相关假设见 TODO_CLARIFY.md。
"""
import os
import time
import uuid

import pytest
import requests
from dotenv import load_dotenv

from common.client import APIClient

load_dotenv()


def login(base_url, user, password):
    """登录获取 Token。端点 / 字段为假设，待澄清。"""
    resp = requests.post(
        f"{base_url}/api/v1/auth/login",
        json={"username": user, "password": password},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()["token"]


@pytest.fixture(scope="session")
def base_url():
    return os.environ["API_BASE_URL"]


@pytest.fixture(scope="session")
def auth_token(base_url):
    return login(base_url, os.environ["API_USER"], os.environ["API_PASSWORD"])


@pytest.fixture(scope="session")
def client(base_url, auth_token):
    return APIClient(base_url=base_url, token=auth_token)


@pytest.fixture(scope="session")
def no_auth_client(base_url):
    """无 Authorization 头的客户端，用于 401 测试。"""
    return APIClient(base_url=base_url, token=None)


@pytest.fixture(scope="session")
def expired_token_client(base_url):
    """携带无效 / 过期 Token 的客户端，用于 401 测试。"""
    return APIClient(base_url=base_url, token="expired_or_invalid_token_value")


@pytest.fixture
def unique_coupon_name():
    """每次生成唯一券名，避免同商户名称冲突导致 NAME_DUPLICATED。"""
    return f"test_{int(time.time())}_{uuid.uuid4().hex[:6]}"
```

## 文件: api-tests/test_coupon_create.py
```python
"""
创建优惠券接口  POST /api/v1/coupons

参数矩阵（逐参数 × 逐属性）：
  name      string  必填  maxLength=20   同商户唯一
  amount    integer 必填  1..1000
  threshold integer 必填  >=0            非零时必须 >= amount
  total     integer 必填  1..100000

错误码：
  400 NAME_DUPLICATED     名称同商户重复
  400 THRESHOLD_INVALID   门槛非零且小于面额
  400 (通用)              参数缺失 / 类型错误 / 越界
  401                     未认证
"""
from common.client import assert_success, assert_error


# ========== 正向 ==========

def test_TC_01_创建成功_所有字段最小值(client, unique_coupon_name):
    """边界：amount=1（最小）、total=1（最小）、threshold=0（最小且豁免）。"""
    payload = {"name": unique_coupon_name, "amount": 1, "threshold": 0, "total": 1}
    body = assert_success(client.post("/api/v1/coupons", json=payload), 201, status="待发布")
    assert "id" in body


def test_TC_02_创建成功_amount最大值(client, unique_coupon_name):
    payload = {"name": unique_coupon_name, "amount": 1000, "threshold": 0, "total": 100}
    assert_success(client.post("/api/v1/coupons", json=payload), 201, status="待发布")


def test_TC_03_创建成功_total最大值(client, unique_coupon_name):
    payload = {"name": unique_coupon_name, "amount": 10, "threshold": 0, "total": 100000}
    body = assert_success(client.post("/api/v1/coupons", json=payload), 201, status="待发布")
    assert "id" in body


def test_TC_04_创建成功_threshold等于amount(client, unique_coupon_name):
    """边界：threshold == amount（等于视为合法）。"""
    payload = {"name": unique_coupon_name, "amount": 500, "threshold": 500, "total": 100}
    assert_success(client.post("/api/v1/coupons", json=payload), 201, status="待发布")


def test_TC_05_创建成功_threshold大于amount(client, unique_coupon_name):
    payload = {"name": unique_coupon_name, "amount": 100, "threshold": 200, "total": 100}
    assert_success(client.post("/api/v1/coupons", json=payload), 201, status="待发布")


def test_TC_06_创建成功_name含特殊字符且读回一致(client, unique_coupon_name):
    """边界：emoji、引号、<script>、全半角混合；写入后读回一致。"""
    special = "🎉<script>'\"ＡＢＣ"
    payload = {"name": special, "amount": 10, "threshold": 0, "total": 100}
    body = assert_success(client.post("/api/v1/coupons", json=payload), 201, status="待发布")
    assert body.get("name") == special, f"name 读回不一致: {body.get('name')!r}"


def test_TC_11_创建成功_name边界20字符(client, unique_coupon_name):
    payload = {"name": "a" * 20, "amount": 10, "threshold": 0, "total": 100}
    assert_success(client.post("/api/v1/coupons", json=payload), 201, status="待发布")


def test_TC_26_threshold为零时豁免面额校验(client, unique_coupon_name):
    """业务规则：门槛非零时才校验 >= amount；threshold=0 豁免。"""
    payload = {"name": unique_coupon_name, "amount": 1000, "threshold": 0, "total": 100}
    assert_success(client.post("/api/v1/coupons", json=payload), 201, status="待发布")


def test_TC_36_写后读回全字段一致(client, unique_coupon_name):
    """数据一致性：创建后响应体回显各字段。"""
    payload = {"name": unique_coupon_name, "amount": 88, "threshold": 100, "total": 50}
    body = assert_success(client.post("/api/v1/coupons", json=payload), 201, status="待发布")
    assert body.get("name") == payload["name"]
    assert body.get("amount") == payload["amount"]
    assert body.get("threshold") == payload["threshold"]
    assert body.get("total") == payload["total"]
    assert "id" in body


# ========== name 参数 ==========

def test_TC_07_name缺失_必填报错(client, unique_coupon_name):
    payload = {"name": unique_coupon_name, "amount": 10, "threshold": 0, "total": 100}
    del payload["name"]
    assert_error(client.post("/api/v1/coupons", json=payload), 400)


def test_TC_08_name空串_报错(client, unique_coupon_name):
    payload = {"name": "", "amount": 10, "threshold": 0, "total": 100}
    assert_error(client.post("/api/v1/coupons", json=payload), 400)


def test_TC_09_name纯空格_报错(client, unique_coupon_name):
    payload = {"name": "   ", "amount": 10, "threshold": 0, "total": 100}
    assert_error(client.post("/api/v1/coupons", json=payload), 400)


def test_TC_10_name超长21字符_报错(client, unique_coupon_name):
    payload = {"name": "a" * 21, "amount": 10, "threshold": 0, "total": 100}
    assert_error(client.post("/api/v1/coupons", json=payload), 400)


def test_TC_12_name同商户重复_NAME_DUPLICATED(client, unique_coupon_name):
    """幂等 / 唯一性：同一业务键重复提交不重复创建。"""
    payload = {"name": unique_coupon_name, "amount": 10, "threshold": 0, "total": 100}
    assert_success(client.post("/api/v1/coupons", json=payload), 201, status="待发布")
    assert_error(client.post("/api/v1/coupons", json=payload), 400, "NAME_DUPLICATED")


def test_TC_37_name重复后改名重试成功(client, unique_coupon_name):
    """失败 -> 重试 -> 恢复：名称冲突后改名应成功。"""
    payload = {"name": unique_coupon_name, "amount": 10, "threshold": 0, "total": 100}
    assert_success(client.post("/api/v1/coupons", json=payload), 201, status="待发布")
    assert_error(client.post("/api/v1/coupons", json=payload), 400, "NAME_DUPLICATED")
    payload["name"] = f"{unique_coupon_name}_v2"
    assert_success(client.post("/api/v1/coupons", json=payload), 201, status="待发布")


# ========== amount 参数 ==========

def test_TC_13_amount缺失_报错(client, unique_coupon_name):
    payload = {"name": unique_coupon_name, "threshold": 0, "total": 100}
    assert_error(client.post("/api/v1/coupons", json=payload), 400)


def test_TC_14_amount为零_报错(client, unique_coupon_name):
    payload = {"name": unique_coupon_name, "amount": 0, "threshold": 0, "total": 100}
    assert_error(client.post("/api/v1/coupons", json=payload), 400)


def test_TC_15_amount为负_报错(client, unique_coupon_name):
    payload = {"name": unique_coupon_name, "amount": -5, "threshold": 0, "total": 100}
    assert_error(client.post("/api/v1/coupons", json=payload), 400)


def test_TC_16_amount超最大1001_报错(client, unique_coupon_name):
    payload = {"name": unique_coupon_name, "amount": 1001, "threshold": 0, "total": 100}
    assert_error(client.post("/api/v1/coupons", json=payload), 400)


def test_TC_17_amount为小数_报错(client, unique_coupon_name):
    payload = {"name": unique_coupon_name, "amount": 0.5, "threshold": 0, "total": 100}
    assert_error(client.post("/api/v1/coupons", json=payload), 400)


def test_TC_18_amount类型错误_报错(client, unique_coupon_name):
    payload = {"name": unique_coupon_name, "amount": "abc", "threshold": 0, "total": 100}
    assert_error(client.post("/api/v1/coupons", json=payload), 400)


def test_TC_19_amount超大数_报错(client, unique_coupon_name):
    payload = {"name": unique_coupon_name, "amount": 10**10, "threshold": 0, "total": 100}
    assert_error(client.post("/api/v1/coupons", json=payload), 400)


def test_TC_20_amount为null_报错(client, unique_coupon_name):
    payload = {"name": unique_coupon_name, "amount": None, "threshold": 0, "total": 100}
    assert_error(client.post("/api/v1/coupons", json=payload), 400)


# ========== threshold 参数 ==========

def test_TC_21_threshold缺失_报错(client, unique_coupon_name):
    payload = {"name": unique_coupon_name, "amount": 10, "total": 100}
    assert_error(client.post("/api/v1/coupons", json=payload), 400)


def test_TC_22_threshold为负_报错(client, unique_coupon_name):
    payload = {"name": unique_coupon_name, "amount": 10, "threshold": -1, "total": 100}
    assert_error(client.post("/api/v1/coupons", json=payload), 400)


def test_TC_23_threshold为小数_报错(client, unique_coupon_name):
    payload = {"name": unique_coupon_name, "amount": 10, "threshold": 1.5, "total": 100}
    assert_error(client.post("/api/v1/coupons", json=payload), 400)


def test_TC_24_threshold类型错误_报错(client, unique_coupon_name):
    payload = {"name": unique_coupon_name, "amount": 10, "threshold": "x", "total": 100}
    assert_error(client.post("/api/v1/coupons", json=payload), 400)


def test_TC_25_threshold小于amount且非零_THRESHOLD_INVALID(client, unique_coupon_name):
    """业务规则：门槛非零时必须 >= amount。"""
    payload = {"name": unique_coupon_name, "amount": 500, "threshold": 100, "total": 100}
    assert_error(client.post("/api/v1/coupons", json=payload), 400, "THRESHOLD_INVALID")


def test_TC_38_threshold报错后改正重试成功(client, unique_coupon_name):
    """失败 -> 重试 -> 恢复：门槛非法后修正应成功。"""
    payload = {"name": unique_coupon_name, "amount": 500, "threshold": 100, "total": 100}
    assert_error(client.post("/api/v1/coupons", json=payload), 400, "THRESHOLD_INVALID")
    payload["threshold"] = 500
    assert_success(client.post("/api/v1/coupons", json=payload), 201, status="待发布")


# ========== total 参数 ==========

def test_TC_27_total缺失_报错(client, unique_coupon_name):
    payload = {"name": unique_coupon_name, "amount": 10, "threshold": 0}
    assert_error(client.post("/api/v1/coupons", json=payload), 400)


def test_TC_28_total为零_报错(client, unique_coupon_name):
    payload = {"name": unique_coupon_name, "amount": 10, "threshold": 0, "total": 0}
    assert_error(client.post("/api/v1/coupons", json=payload), 400)


def test_TC_29_total为负_报错(client, unique_coupon_name):
    payload = {"name": unique_coupon_name, "amount": 10, "threshold": 0, "total": -1}
    assert_error(client.post("/api/v1/coupons", json=payload), 400)


def test_TC_30_total超最大100001_报错(client, unique_coupon_name):
    payload = {"name": unique_coupon_name, "amount": 10, "threshold": 0, "total": 100001}
    assert_error(client.post("/api/v1/coupons", json=payload), 400)


def test_TC_31_total为小数_报错(client, unique_coupon_name):
    payload = {"name": unique_coupon_name, "amount": 10, "threshold": 0, "total": 1.5}
    assert_error(client.post("/api/v1/coupons", json=payload), 400)


def test_TC_32_total类型错误_报错(client, unique_coupon_name):
    payload = {"name": unique_coupon_name, "amount": 10, "threshold": 0, "total": "abc"}
    assert_error(client.post("/api/v1/coupons", json=payload), 400)


def test_TC_33_total超大数_报错(client, unique_coupon_name):
    payload = {"name": unique_coupon_name, "amount": 10, "threshold": 0, "total": 10**10}
    assert_error(client.post("/api/v1/coupons", json=payload), 400)


# ========== 鉴权 ==========

def test_TC_34_无Token_401(no_auth_client, unique_coupon_name):
    payload = {"name": unique_coupon_name, "amount": 10, "threshold": 0, "total": 100}
    resp = no_auth_client.post("/api/v1/coupons", json=payload)
    assert resp.status_code == 401


def test_TC_35_过期Token_401(expired_token_client, unique_coupon_name):
    payload = {"name": unique_coupon_name, "amount": 10, "threshold": 0, "total": 100}
    resp = expired_token_client.post("/api/v1/coupons", json=payload)
    assert resp.status_code == 401
```

## 文件: api-tests/test_coupon_claim.py
```python
"""
领取优惠券接口  POST /api/v1/coupons/{id}/claim

错误码：
  404  券不存在或已结束（含未发布）
  409  超过每人限领数量
  401  未认证

前置依赖（待澄清，见 TODO_CLARIFY.md）：
  - published_coupon fixture 创建并发布一张券；
    发布接口未在 OpenAPI 中给出，假设为 POST /api/v1/coupons/{id}/publish。
  - 「每人限领 3 张」口径假设为「每张券每人 3 张」，每用例新建独立券保证独立性。
"""
from concurrent.futures import ThreadPoolExecutor

import pytest
import requests

from common.client import assert_success


PUBLISH_PATH = "/api/v1/coupons/{}/publish"


@pytest.fixture
def published_coupon(client, unique_coupon_name):
    """造数：创建 + 发布一张可领取的券。"""
    payload = {"name": unique_coupon_name, "amount": 10, "threshold": 0, "total": 100}
    create = client.post("/api/v1/coupons", json=payload)
    body = assert_success(create, 201, status="待发布")
    coupon_id = body["id"]
    pub = client.post(PUBLISH_PATH.format(coupon_id))
    assert pub.status_code in (200, 204), f"发布失败: {pub.status_code} {pub.text}"
    return coupon_id


# ========== 正向 ==========

def test_TC_51_领取成功(client, published_coupon):
    body = assert_success(client.post(f"/api/v1/coupons/{published_coupon}/claim"), 200)
    assert "user_coupon_id" in body


# ========== 路径参数 / 券状态 ==========

def test_TC_52_券不存在_404(client):
    resp = client.post("/api/v1/coupons/non_existent_coupon_id_xyz/claim")
    assert resp.status_code == 404


def test_TC_53_券未发布_404(client, unique_coupon_name):
    """创建后不发布直接领取 -> 404。"""
    payload = {"name": unique_coupon_name, "amount": 10, "threshold": 0, "total": 100}
    create = client.post("/api/v1/coupons", json=payload)
    body = assert_success(create, 201, status="待发布")
    coupon_id = body["id"]
    resp = client.post(f"/api/v1/coupons/{coupon_id}/claim")
    assert resp.status_code == 404


# ========== 限领 / 幂等 ==========

def test_TC_54_每人限领3张_第4次409(client, published_coupon):
    """同一张券每人限领 3 张：前 3 次成功，第 4 次 409。"""
    for i in range(3):
        r = client.post(f"/api/v1/coupons/{published_coupon}/claim")
        assert r.status_code == 200, f"第{i+1}次领取应成功，实际 {r.status_code}: {r.text}"
    r4 = client.post(f"/api/v1/coupons/{published_coupon}/claim")
    assert r4.status_code == 409


# ========== 并发 ==========

def test_TC_55_并发领取不超发(base_url, auth_token, unique_coupon_name):
    """total=1 的券，10 并发领取，应至多 1 个成功（不超发，无中间态互相覆盖）。"""
    headers = {"Authorization": f"Bearer {auth_token}"}
    payload = {"name": unique_coupon_name, "amount": 10, "threshold": 0, "total": 1}
    create = requests.post(f"{base_url}/api/v1/coupons", json=payload, headers=headers, timeout=10)
    coupon_id = assert_success(create, 201, status="待发布")["id"]
    pub = requests.post(f"{base_url}{PUBLISH_PATH.format(coupon_id)}", headers=headers, timeout=10)
    assert pub.status_code in (200, 204), f"发布失败: {pub.status_code}"

    def claim():
        r = requests.post(
            f"{base_url}/api/v1/coupons/{coupon_id}/claim",
            headers=headers, timeout=10,
        )
        return r.status_code

    with ThreadPoolExecutor(max_workers=10) as ex:
        futures = [ex.submit(claim) for _ in range(10)]
        results = [f.result() for f in futures]

    success = results.count(200)
    assert success <= 1, (
        f"并发领取超发：total=1 但成功 {success} 次；结果分布 "
        f"{ {s: results.count(s) for s in set(results)} }"
    )


# ========== 鉴权 ==========

def test_TC_56_无Token_401(no_auth_client, published_coupon):
    resp = no_auth_client.post(f"/api/v1/coupons/{published_coupon}/claim")
    assert resp.status_code == 401


def test_TC_57_过期Token_401(expired_token_client, published_coupon):
    resp = expired_token_client.post(f"/api/v1/coupons/{published_coupon}/claim")
    assert resp.status_code == 401
```

## 文件: api-tests/TODO_CLARIFY.md
```markdown
# 待澄清清单

以下问题在 OpenAPI 片段与业务规则中未明确，脚本以假设实现，需与开发确认后调整。

## 接口缺失

1. **登录接口**：conftest.login() 假设端点 `POST /api/v1/auth/login`，请求体 `{username, password}`，响应体字段 `token`。需确认实际端点与字段名。
2. **优惠券发布接口**：领取测试需要「已发布」状态的券，但 OpenAPI 未提供发布接口。published_coupon fixture 假设 `POST /api/v1/coupons/{id}/publish`，成功状态码 200/204。需确认端点或提供其他置为已发布的方式。
3. **券删除 / 清理接口**：创建测试会累积券数据，无清理接口。需确认是否有删除接口，或测试环境是否接受数据堆积、是否需要独立可写旁路环境。
4. **用户券撤销接口**：领取测试会产生 user_coupon 数据，无法清理。若「每人限领」为全局口径，跨用例累积会影响后续用例。需确认清理方式或提供独立账号。

## 业务规则歧义

5. **「每人限领 3 张」口径**：是「每张券每人 3 张」还是「全局每人 3 张」？当前脚本假设为前者（每用例新建独立券保证独立性）。若为后者，需为每个限领用例提供独立测试账号，否则 TC_54 / TC_55 之间存在顺序依赖与状态污染。
6. **threshold=0 豁免语义**：业务规则「门槛非 0 时必须 >= 面额」，threshold=0 是否完全豁免该校验？当前假设是（TC_26）。
7. **同商户唯一性**：测试账号所属商户是否固定？如何测试跨商户名称重复（需第二个商户账号）？当前只用单一账号测同商户重复（TC_12）。
8. **库存不足的返回码**：total 扣减为 0 后继续领取，返回 404（视为已结束）还是 409 或其他？OpenAPI 仅列 404/409，未明确库存场景。并发测试 TC_55 只断言「不超发」，未断言失败请求的具体状态码。

## 响应体结构

9. **401 响应体**：OpenAPI 只标注 401 未认证，未给出 body 结构。当前只断言状态码（TC_34/35/56/57）。
10. **404 / 409 响应体**：领取接口的 404/409 是否含 `{code, message}`？当前只断言状态码，未断言业务码。需确认后补断言。
11. **创建成功响应体**：文档说「body 含 id / status=待发布」，是否回显 name/amount/threshold/total？TC_36 假设回显并断言读回一致。需确认。
12. **name 特殊字符处理**：emoji、`<script>`、引号等是否原样存储与回显？是否会被过滤 / 转义？TC_06 假设原样回显。

## 校验路径

13. **二阶交叉（写入路径 × 校验规则）**：当前仅有创建一条写入路径。若存在编辑 / 重新提交 / 导入等路径，同一条校验规则（maxLength、范围、threshold>=amount、名称唯一）需在每条路径上分别验证。需确认是否存在其他写入路径，若有则补充对应用例。
```