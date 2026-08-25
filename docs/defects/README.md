# 缺陷注入与回归演练索引

BUG-001 至 BUG-010 是个人 QA 项目的可复现实验：先定义一个高风险错误模式，在隔离分支/基线中注入或模拟该错误，再修复并固化自动化回归。它们不是生产事故，也不冒充真实客户缺陷。BUG-011 是执行真实 Chromium 自动化时发现的预发布缺陷。当前 `main` 目标状态均为 **Verified**。

| ID | 标题 | 严重度 | 回归证据 |
|---|---|---|---|
| BUG-001 | 已绑定家属可读取老人情绪原文 | S1 | `test_linked_family_sees_label_but_not_raw_text` |
| BUG-002 | pending 绑定提前获得数据权限 | S1 | `test_unlinked_family_cannot_read_moods` |
| BUG-003 | 同一家庭关系可重复创建 | S2 | `test_duplicate_link_is_rejected` |
| BUG-004 | 高关注告警文案复制原始敏感文本 | S1 | `test_high_risk_checkin_creates_generic_alert_without_leaking_text` |
| BUG-005 | 注册/资料响应暴露完整手机号 | S1 | `test_register_success_returns_masked_profile` / `test_me_never_exposes_full_phone` |
| BUG-006 | 已确认告警可被重复确认 | S2 | `test_alert_can_be_acknowledged_once` |
| BUG-007 | 未绑定家属可为任意老人创建提醒 | S1 | `test_unlinked_family_cannot_create_reminder` |
| BUG-008 | 全空格情绪文本可写入 | S2 | `MoodCreate.not_blank` + TC-023 |
| BUG-009 | 连续消极每次打卡重复生成告警 | S2 | `test_three_negative_checkins_create_one_streak_alert` |
| BUG-010 | 页面缺少关键浏览器安全响应头 | S2 | `test_security_headers_are_present` |
| BUG-011 | 异步提交成功后表单不重置且页面不刷新 | S2 | `test_elderly_can_submit_mood_and_view_history` |
