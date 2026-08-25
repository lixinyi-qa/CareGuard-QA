# CareGuard QA 功能测试用例（50 条）

统一测试数据均为虚构信息；除特别说明外，API 基址为 `http://127.0.0.1:8000`，数据库为空且服务健康。`A-xx` 表示 pytest 自动化，`P-xx` 表示 Postman 顺序回归，`UI-xx` 表示 Playwright。

| ID | 模块 | 用例标题 | 前置条件 | 步骤/数据 | 预期结果 | 优先级 | 自动化 |
|---|---|---|---|---|---|---|---|
| TC-001 | 注册 | 老人合法注册 | 手机号未使用 | 提交姓名、`13900000009`、`Hello123`、elderly、同意隐私 | 201；返回令牌；角色正确；手机号脱敏；无密码字段 | P0 | A-02/P-03/UI-04 |
| TC-002 | 注册 | 家属合法注册 | 手机号未使用 | 角色选 family，其余合法 | 201；角色为 family；进入家属端 | P0 | A-02/P-04/UI-06 |
| TC-003 | 注册 | 重复手机号 | 已有老人账号 | 用相同手机号再次注册 | 409 `PHONE_EXISTS`；原账号不变化 | P1 | A-03 |
| TC-004 | 注册 | 弱密码仅字母 | 无 | 密码 `onlyletters` | 422 `VALIDATION_ERROR` | P1 | A-04 |
| TC-005 | 注册 | 弱密码仅数字 | 无 | 密码 `12345678` | 422；说明密码规则 | P1 | A-04 |
| TC-006 | 注册 | 未同意隐私 | 无 | consent=false | 422；不创建账号 | P0 | A-04 |
| TC-007 | 注册 | 手机号格式错误 | 无 | 手机号 `123` | 422；字段定位到 phone | P1 | A-04 |
| TC-008 | 登录 | 正确账号密码 | 已注册 | POST `/auth/login` | 200；JWT 和过期秒数有效；记录成功审计 | P0 | A-05 |
| TC-009 | 登录 | 密码错误防枚举 | 已注册 | 错误密码登录 | 401 `INVALID_CREDENTIALS`；响应不含手机号/账号存在性 | P0 | A-06 |
| TC-010 | 登录 | 未带令牌访问本人资料 | 无 | GET `/auth/me` | 401 `AUTH_REQUIRED`，结构化错误含 request_id | P0 | A-07 |
| TC-011 | 登录 | 资料接口隐私 | 已登录 | GET `/auth/me` | 手机号只显示前三后四；无 password/hash | P0 | A-08/P-05 |
| TC-012 | 绑定 | 家属发起邀请 | 双角色账号 | 家属提交老人手机号 | 201；状态 pending；记录邀请人 | P0 | A-09/P-06 |
| TC-013 | 绑定 | 老人不能发起邀请 | 老人登录 | 老人 POST `/care-links` | 403 `FAMILY_ONLY` | P1 | A-10 |
| TC-014 | 绑定 | 老人确认本人邀请 | 存在本人 pending 邀请 | POST `/care-links/{id}/accept` | 200；active；accepted_at 非空 | P0 | A-11/P-08 |
| TC-015 | 绑定 | 第三方不能确认 | 存在其他老人的邀请 | 未关联账号确认 | 403；关系保持 pending | P0 | A-12 |
| TC-016 | 绑定 | 重复绑定 | 已存在任意状态同组合 | 再次邀请 | 409 `LINK_EXISTS`；不新增记录 | P1 | A-13 |
| TC-017 | 绑定 | 成员解除绑定 | active 关系 | 老人 DELETE link | 204；状态 revoked；共享权限立即消失 | P0 | A-14 |
| TC-018 | 绑定 | 非成员解除绑定 | active 关系 | 第三方 DELETE link | 403；关系保持 active | P0 | API 负向集 |
| TC-019 | 情绪 | 积极分类 | 老人登录 | 文本“今天很开心” | 201；positive；置信提示 55–95；有免责声明 | P0 | A-15/P-10/UI-05 |
| TC-020 | 情绪 | 中性分类 | 老人登录 | 文本“今天在家看电视” | 201；neutral | P1 | A-15/P-11 |
| TC-021 | 情绪 | 消极分类 | 老人登录 | 文本“失眠，很难过” | 201；negative；不返回诊断结论 | P0 | A-15/P-12 |
| TC-022 | 情绪 | 否定词修正 | 无需登录的域测试 | “并不糟糕，已经顺利解决” | positive，不被“糟糕”单词误判 | P1 | 单元参数集 |
| TC-023 | 情绪 | 空白文本 | 老人登录 | text 为全空格 | 422；不写入记录 | P1 | A/BUG-008 |
| TC-024 | 情绪 | 超长文本 | 老人登录 | 501 字 | 422；不截断写入 | P2 | schema 自动化 |
| TC-025 | 情绪 | 家属替老人打卡 | 家属登录 | POST `/moods` | 403 `ELDERLY_ONLY` | P0 | A-16 |
| TC-026 | 隐私 | 未绑定家属读取情绪 | 老人已有记录 | 未绑定家属查询 owner_id | 403 `MOOD_FORBIDDEN`；写拒绝审计 | P0 | A-17 |
| TC-027 | 隐私 | 已绑定家属读取情绪 | active 关系 | 家属 GET moods | 200；分类/时间可见；每条 `text=null` | P0 | A-18/P-16 |
| TC-028 | 隐私 | 老人读取本人原文 | 老人已有记录 | 老人 GET moods | 200；原始文字完整，仅本人可见 | P0 | A-19/P-15 |
| TC-029 | 告警 | 连续三条消极 | 老人登录 | 连续提交 3 条消极 | 只生成 1 条 medium `negative_streak` | P0 | A-20/P-12~14 |
| TC-030 | 告警 | 连续消极七日去重 | 已有 7 日内 open streak | 再满足连续三条 | 不新增同类 open 告警 | P1 | 服务自动化 |
| TC-031 | 告警 | 高关注表达 | 老人登录 | 提交高关注词句 | negative、is_high_risk=true；生成 high 告警 | P0 | A-21/P-15 |
| TC-032 | 告警 | 告警不泄露原文 | 已产生高关注告警 | 家属 GET alerts | 文案为通用关怀语，不含原文/诊断词 | P0 | A-21/P-24 |
| TC-033 | 统计 | 三类数量守恒 | 近 30 天有多类记录 | GET stats | positive+neutral+negative=total；latest 正确 | P1 | A-22/P-17 |
| TC-034 | 提醒 | 老人新增用药提醒 | 老人登录 | 合法标题、时间、medication | 201；owner/creator 均为本人 | P0 | A-23 |
| TC-035 | 提醒 | 未绑定家属新增提醒 | 无 active 关系 | 家属指定老人 owner_id | 403；不写入数据库 | P0 | A-24 |
| TC-036 | 提醒 | 已绑定家属新增日程 | active 关系 | family 创建 weekly schedule | 201；owner 为老人，created_by 为家属 | P0 | A-25/P-18 |
| TC-037 | 提醒 | 完成提醒 | 有未完成提醒 | PATCH is_completed=true | 200；状态已完成；列表排序到未完成之后 | P1 | A-26/P-20 |
| TC-038 | 提醒 | 删除不存在提醒 | 老人登录 | DELETE id=9999 | 404 `REMINDER_NOT_FOUND` | P2 | A-27 |
| TC-039 | 提醒 | 非法枚举 | 老人登录 | type=`diagnosis` 或 recurrence=`hourly` | 422；不写入 | P1 | schema 自动化 |
| TC-040 | 联系人 | 新增后立即脱敏 | 老人登录 | 姓名王小爱、13912345678 | 201；`王**`、`139****5678`；无原字段 | P0 | A-28/P-21 |
| TC-041 | 联系人 | 未绑定家属读取 | 无 active 关系 | GET contacts?owner_id | 403 | P0 | A-29 |
| TC-042 | 联系人 | 已绑定家属读取 | active 关系，有联系人 | 家属 GET contacts | 200；仅脱敏值；关系/优先级可见 | P0 | P-22 |
| TC-043 | 告警 | 首次确认关怀 | active 关系，有 open 告警 | 家属 POST acknowledge | 200；status acknowledged；确认人和时间落库 | P0 | A-30/P-25 |
| TC-044 | 告警 | 重复确认冲突 | 告警已确认 | 再次 acknowledge | 409 `ALREADY_ACKNOWLEDGED` | P1 | A-30 |
| TC-045 | 数据权利 | 本人导出 | 老人有多类数据 | GET `/privacy/export` | JSON 包含本人身份、情绪、提醒、联系人，不包含他人数据 | P1 | A-31/P-27 |
| TC-046 | 审计 | 本人读取审计 | 已执行情绪/提醒操作 | GET `/audit-logs/me` | 仅返回当前 actor；动作、资源、结果、时间完整 | P1 | A-32/P-26 |
| TC-047 | AI 治理 | 模型卡公开 | 无 | GET `/ai/model-card` | 三标签、用途、医疗禁用范围、限制、隐私声明齐全 | P0 | A-33/P-28 |
| TC-048 | 安全 | 响应安全头 | 服务可用 | GET `/health` 并传 X-Request-ID | 原 ID 回传；CSP、nosniff、DENY 均存在 | P1 | A-34 |
| TC-049 | 适老化 | 字号与高对比 | 打开首页 | 键盘触发 A+、高对比 | 根字号增大；aria-pressed 更新；焦点可见 | P1 | UI-02/UI-03 |
| TC-050 | 会话 | UI 安全退出 | 已登录 | 点击退出后刷新 | 返回登录页；本地令牌清除；刷新不能回到仪表盘 | P0 | UI-07 |

## 结果记录规则

执行时追加实际结果、执行人、构建号、证据路径和缺陷 ID。自动化映射并不代表当前执行已通过，只有 `outputs/` 中对应运行报告才能作为通过证据。
