# 会议室预约：首次测试设计练习 / Room booking: first-task brief

虚构产品说明；这是公开入门材料，与维护者私有评测任务池无关。没有被测应用或可执行接口。
Fictional product brief, separate from the private evaluation task pool. No running application or API is provided.

## 业务规则 / Rules

1. 登录用户可预约同一天、未来时间的会议室。开始时间必须早于结束时间。
   Signed-in users can book a room for a future time on the same day. Start must precede end.
2. 最短预约 30 分钟，最长 120 分钟，允许恰好达到边界。
   Duration is 30–120 minutes inclusive.
3. 同一会议室的两个预约不允许重叠，前一预约结束时刻可作为后一预约开始时刻。
   Bookings for the same room cannot overlap. One may start exactly when another ends.
4. 普通用户只能取消自己的预约，管理员可以取消任何预约。
   Users can cancel their own bookings; administrators can cancel any booking.
5. 同时提交冲突预约时最多一个成功；不能产生重复占用。
   At most one conflicting concurrent booking succeeds; double occupancy is not allowed.

## 故意留待澄清 / Questions intentionally unresolved

- 系统采用哪个时区？当天以用户还是服务端时间为准？
  Which time zone defines a day: the user's or the server's?
- 已开始的预约是否允许取消？
  Can an in-progress booking be cancelled?
- 页面入口、角色账号和冲突提示是什么？当前没有运行环境，不能虚构这些信息。
  What are the UI entry point, role accounts and conflict response? No running environment is provided; do not invent them.
