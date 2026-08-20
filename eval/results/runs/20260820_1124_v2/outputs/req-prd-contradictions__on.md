# 需求模型

```yaml
requirement_model:
  goal:
    提升用户活跃与复购，建立积分获取与消耗闭环。
    evidence:
      level: E1
      source: PRD《会员积分体系》v0.9 - 目标
  scope:
    功能范围:
      - 积分获取（消费、签到、评价）
      - 积分消耗（兑换、抵现）
      - 积分状态与生命周期管理
      - 退款积分扣回机制
    非目标:
      - 未提及积分转赠功能
      - 未提及积分过期提醒功能
      - 未提及积分体系与其他平台互通
    evidence:
      level: E1
      source: PRD《会员积分体系》v0.9 - 全文边界
  roles:
    - 角色: 普通会员
      能做: 消费/签到/评价获取积分，兑换/抵现消耗积分
      不能做: 未知
    - 角色: 银卡会员
      能做: 同上，消费获取积分系数 1.2 倍
      不能做: 未知
    - 角色: 金卡会员
      能做: 同上，消费获取积分系数 2 倍
      不能做: 未知
    - 角色: 铂金会员
      能做: 同上，消费获取积分系数 3 倍
      不能做: 未知
    evidence:
      level: E1
      source: PRD《会员积分体系》v0.9 - 会员等级
  inputs:
    - 来源: 订单系统
      格式: 消费金额/退款事件
      约束: 消费1元=1积分（按等级倍数）
    - 来源: 用户前端
      格式: 签到动作
      约束: 每日+5，连续7天额外+50
    - 来源: 用户前端
      格式: 评价订单动作
      约束: +10/单，每日上限3单
    - 来源: 风控系统
      格式: 异常行为扣分指令
      约束: 未知
    evidence:
      level: E1
      source: PRD《会员积分体系》v0.9 - 获取/消耗/依赖
  outputs:
    - 去向: 用户账户
      格式: 积分余额及状态变更
      消费方: 用户
    - 去向: 订单系统
      格式: 抵现金额数据
      消费方: 订单结算
    - 去向: 积分商城
      格式: 兑换订单
      消费方: 仓储/发货系统
    evidence:
      level: E1
      source: PRD《会员积分体系》v0.9 - 消耗规则
  states:
    - 正常 --发起兑换--> 冻结
    - 冻结 --兑换成功--> 已消耗
    - 冻结 --兑换失败--> 正常
    - 正常 --年底清零(未裁决)/过期--> 已过期
    evidence:
      level: E1
      source: PRD《会员积分体系》v0.9 - 积分状态/积分有效期
  rules:
    - id: R1
      desc: 消费 1 元 = 1 积分，银卡 1.2 倍，金卡 2 倍，铂金 3 倍
      evidence:
        level: E1
        source: PRD《会员积分体系》v0.9 - 会员等级/积分获取
    - id: R2
      desc: 签到每日 +5 积分，连续 7 天额外 +50 积分
      evidence:
        level: E1
        source: PRD《会员积分体系》v0.9 - 积分获取
    - id: R3
      desc: 评价订单 +10 积分/单，每日上限 3 单
      evidence:
        level: E1
        source: PRD《会员积分体系》v0.9 - 积分获取
    - id: R4
      desc: 积分商城兑换按商品标定积分价兑换
      evidence:
        level: E1
        source: PRD《会员积分体系》v0.9 - 积分消耗
    - id: R5
      desc: 下单时 100 积分抵 1 元，单笔订单最高抵订单金额的 50%
      evidence:
        level: E1
        source: PRD《会员积分体系》v0.9 - 积分消耗
    - id: R6
      desc: 订单退款时，该订单获取的积分相应扣回；已消耗的积分不足扣回时，扣至 0 为止
      evidence:
        level: E1
        source: PRD《会员积分体系》v0.9 - 退款规则
    - id: R7
      desc: 每年 12 月 31 日对上年度获取的积分清零（与永久有效存在冲突，见待澄清项）
      evidence:
        level: E1
        source: PRD《会员积分体系》v0.9 - 积分有效期附注
  exceptions:
    - desc: 兑换失败 -> 积分解冻回正常状态
      evidence:
        level: E1
        source: PRD《会员积分体系》v0.9 - 积分状态
    - desc: 退款时积分不足扣回 -> 扣至 0 为止
      evidence:
        level: E1
        source: PRD《会员积分体系》v0.9 - 退款规则
  dependencies:
    - 上下游: 订单系统
      交互: 消费/退款事件触发积分加扣
      evidence:
        level: E1
        source: PRD《会员积分体系》v0.9 - 依赖
    - 上下游: 风控系统
      交互: 异常行为扣分
      evidence:
        level: E1
        source: PRD《会员积分体系》v0.9 - 依赖
  open_questions:
    - id: Q1
      question: 会员等级划分存在矛盾。前文描述为"普通、银卡、金卡三级"，后文出现"铂金会员为 3 倍"。
      impact: 无法确定积分获取系数的适用范围和等级体系。
      suggested_options: ["修正等级体系为四级", "删除铂金会员描述"]
      status: 待澄清
    - id: Q2
      question: 积分有效期规则冲突。正文写"积分永久有效"，附注写"每年12月31日对上年度获取的积分清零"。
      impact: 无法确定积分生命周期及状态流转中的过期分支。
      suggested_options: ["以永久有效为准", "以年底清零为准", "细化清零范围"]
      status: 待澄清
    - id: Q3
      question: 普通会员积分获取系数未明确。
      impact: 消费积分计算缺少基础系数。
      suggested_options: ["默认1倍"]
      status: 待澄清
    - id: Q4
      question: 签到"连续7天额外+50"的发放机制未明确。第7天发放55，还是第8天发放50？中断后如何重置？
      impact: 签到积分发放逻辑无法实现。
      suggested_options: ["第7天发55，中断重置", "第8天发50，中断重置"]
      status: 待澄清
    - id: Q5
      question: 订单退款若使用了积分抵现，抵扣的积分是否退还？
      impact: 退款积分扣回逻辑闭环不完整。
      status: 待澄清
    - id: Q6
      question: 风控系统异常行为扣分的规则、扣减上限及触发条件未定义。
      impact: 无法设计风控扣分相关的异常场景和状态流转。
      status: 待澄清
    - id: Q7
      question: 签到/评价积分获取是否受等级倍数影响？
      impact: 银卡/金卡/铂金会员的积分计算逻辑不明确。
      status: 待澄清
```