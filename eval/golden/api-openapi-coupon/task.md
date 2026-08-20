# 任务：为优惠券接口编写 API 自动化测试

你是测试工程师。请根据下方的 OpenAPI 文档与业务规则，编写**可执行的 API 自动化测试脚本**（pytest + requests），并直接输出全部代码文件内容（每个文件给出文件名）。

测试环境：base URL 为 `https://api.example.test`（用环境变量 `API_BASE_URL` 注入，测试账号用环境变量 `API_USER` / `API_PASSWORD` 登录获取 Token）。只需编写脚本，无需运行。

---

## 输入材料

### 材料 1：OpenAPI 片段

```yaml
paths:
  /api/v1/coupons:
    post:
      summary: 创建优惠券
      security: [{ bearerAuth: [] }]
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required: [name, amount, threshold, total]
              properties:
                name:    { type: string, maxLength: 20 }
                amount:  { type: integer, minimum: 1, maximum: 1000 }
                threshold: { type: integer, minimum: 0 }
                total:   { type: integer, minimum: 1, maximum: 100000 }
      responses:
        "201": { description: 创建成功（body 含 id/status=待发布） }
        "400": { description: 参数错误（body: {code, message}） }
        "401": { description: 未认证 }
  /api/v1/coupons/{id}/claim:
    post:
      summary: 领取优惠券
      security: [{ bearerAuth: [] }]
      parameters:
        - name: id
          in: path
          required: true
          schema: { type: string }
      responses:
        "200": { description: 领取成功（body 含 user_coupon_id） }
        "404": { description: 券不存在或已结束 }
        "409": { description: 超过每人限领数量 }
```

### 材料 2：业务规则

- 创建：名称同商户唯一（重复返回 400，code=NAME_DUPLICATED）；门槛非 0 时必须 ≥ 面额（否则 400，code=THRESHOLD_INVALID）
- 领取：每人限领 3 张（超领 409）；券状态非已发布返回 404；重复领取同一张券到上限后 409
- 领取接口要求登录态（Bearer Token），未携带或过期返回 401
