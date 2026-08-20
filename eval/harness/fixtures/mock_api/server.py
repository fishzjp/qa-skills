#!/usr/bin/env python3
"""Mock API 服务：优惠券接口（api-openapi-coupon 任务的固定被测系统）。

严格实现任务材料中的 OpenAPI 契约与业务规则：
- POST /api/v1/coupons：创建（必填/类型/边界校验、名称同商户唯一 400 NAME_DUPLICATED、
  门槛非 0 且 < 面额 400 THRESHOLD_INVALID）
- POST /api/v1/coupons/{id}/claim：领取（Bearer 鉴权 401、不存在/已结束 404、
  每人限领 3 张 409）
- 登录（兼容常见路径）→ Bearer Token
无第三方依赖，纯标准库。
"""
import json
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = int(__import__("os").environ.get("API_PORT", "8932"))

_lock = threading.Lock()
_state = {"coupons": {}, "claims": {}, "seq": 1}
# 预置一张已发布的券与一张已结束的券，供 404/领取场景使用
_state["coupons"]["coupon-base"] = {"id": "coupon-base", "name": "预置可用券", "amount": 10,
                                    "threshold": 0, "total": 100, "status": "已发布"}
_state["coupons"]["coupon-ended"] = {"id": "coupon-ended", "name": "已结束券", "amount": 5,
                                     "threshold": 0, "total": 100, "status": "已结束"}

TOKENS = {"tok-admin": "admin"}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):  # 静默
        pass

    def _json_body(self):
        n = int(self.headers.get("Content-Length") or 0)
        try:
            return json.loads(self.rfile.read(n) or b"{}")
        except Exception:  # noqa: BLE001
            return {}

    def _send(self, code, payload):
        body = json.dumps(payload, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _auth_user(self):
        h = self.headers.get("Authorization") or ""
        m = re.match(r"Bearer\s+(.+)", h.strip())
        return TOKENS.get(m.group(1)) if m else None

    def do_POST(self):
        path = self.path.split("?")[0].rstrip("/")
        if path in ("/api/v1/login", "/api/v1/auth/login", "/auth/token", "/api/login", "/login"):
            b = self._json_body()
            if b.get("username") == "admin" and b.get("password") == "pass":
                return self._send(200, {"token": "tok-admin", "expires_in": 3600})
            return self._send(401, {"code": "UNAUTHORIZED", "message": "账号或密码错误"})
        user = self._auth_user()
        if user is None:
            return self._send(401, {"code": "UNAUTHORIZED", "message": "未认证或 Token 无效"})
        if path == "/api/v1/coupons":
            b = self._json_body()
            for f in ("name", "amount", "threshold", "total"):
                if f not in b or b[f] is None:
                    return self._send(400, {"code": f"{f.upper()}_REQUIRED", "message": f"{f} 必填"})
            if not isinstance(b["name"], str) or len(b["name"]) > 20:
                return self._send(400, {"code": "NAME_INVALID", "message": "名称需为不超 20 字符的字符串"})
            if not isinstance(b["amount"], int) or isinstance(b["amount"], bool) or not (1 <= b["amount"] <= 1000):
                return self._send(400, {"code": "AMOUNT_INVALID", "message": "面额需为 1-1000 的整数"})
            if not isinstance(b["threshold"], int) or isinstance(b["threshold"], bool) or b["threshold"] < 0:
                return self._send(400, {"code": "THRESHOLD_INVALID", "message": "门槛需为非负整数"})
            if b["threshold"] != 0 and b["threshold"] < b["amount"]:
                return self._send(400, {"code": "THRESHOLD_INVALID", "message": "使用门槛不能低于面额"})
            if not isinstance(b["total"], int) or isinstance(b["total"], bool) or not (1 <= b["total"] <= 100000):
                return self._send(400, {"code": "TOTAL_INVALID", "message": "发放总量需为 1-100000 的整数"})
            with _lock:
                if any(c["name"] == b["name"] for c in _state["coupons"].values()):
                    return self._send(400, {"code": "NAME_DUPLICATED", "message": "名称已存在"})
                cid = f"coupon-{_state['seq']}"
                _state["seq"] += 1
                _state["coupons"][cid] = {**b, "id": cid, "status": "待发布"}
                return self._send(201, _state["coupons"][cid])
        m = re.match(r"^/api/v1/coupons/([^/]+)/claim$", path)
        if m:
            cid = m.group(1)
            with _lock:
                c = _state["coupons"].get(cid)
                if not c or c.get("status") != "已发布":
                    return self._send(404, {"code": "NOT_FOUND", "message": "券不存在或已结束"})
                got = _state["claims"].setdefault(cid, {}).get(user, 0)
                if got >= 3:
                    return self._send(409, {"code": "CLAIM_LIMIT", "message": "超过每人限领数量"})
                _state["claims"][cid][user] = got + 1
                return self._send(200, {"user_coupon_id": f"uc-{cid}-{user}-{got + 1}"})
        return self._send(404, {"code": "NOT_FOUND", "message": "not found"})

    def do_GET(self):
        path = self.path.split("?")[0].rstrip("/")
        if path == "/api/v1/coupons":
            return self._send(200, {"coupons": list(_state["coupons"].values())})
        m = re.match(r"^/api/v1/coupons/([^/]+)$", path)
        if m:
            c = _state["coupons"].get(m.group(1))
            return self._send(200, c) if c else self._send(404, {"code": "NOT_FOUND"})
        return self._send(404, {"code": "NOT_FOUND", "message": "not found"})

    def do_DELETE(self):
        m = re.match(r"^/api/v1/coupons/([^/]+)$", self.path.split("?")[0].rstrip("/"))
        if m and self._auth_user():
            _state["coupons"].pop(m.group(1), None)
            return self._send(200, {"deleted": True})
        return self._send(404, {"code": "NOT_FOUND"})


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
