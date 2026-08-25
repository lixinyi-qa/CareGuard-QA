# CareGuard QA 最终核验摘要

核验时间：2026-08-24（Asia/Shanghai）
环境：Windows、Python 3.13.5、FastAPI 0.141.1、SQLAlchemy 2.0、MySQL Community Server 8.4.11（隔离端口 3307）、SQLite 内存隔离库、Chrome 151、JMeter 5.6.3、Newman 6.2.1

## 结论

项目已在本机真实 MySQL 8.4.11 上完成数据库合约、Postman 端到端接口、Playwright 浏览器流程、24 项 SQL 一致性检查和 JMeter 并发基准。API/域/结构 48 条、MySQL 合约 5 条、真实浏览器 7 条、Postman 28 请求/114 断言、AI 基准 30 条、JMeter 340 样本均为最终全绿。执行过程中发现并修复 1 个真实前端异步缺陷（BUG-011）和 1 个 Postman 沙箱变量兼容问题。

MySQL 采用官方免安装包运行在 `127.0.0.1:3307`，未覆盖或升级电脑原有的 MySQL 5.6，也未注册 Windows 服务。数据库为专用的 `careguard_test`，7 张业务表全部为 InnoDB、`utf8mb4_0900_ai_ci`。

## 实际结果

| 维度 | 结果 | 证据 |
|---|---|---|
| pytest 快速回归 | 48 passed，1 UI module skipped，5 MySQL tests deselected | `api-test-report.xml` |
| 覆盖率 | 90.67%，门槛 75% | `coverage-html/index.html` |
| MySQL 8.4 合约 | 5/5 passed；版本、InnoDB/utf8mb4、唯一约束/外键、中文 Emoji、事务回滚、孤儿数据拒绝 | `mysql-contract-junit.xml` |
| Playwright + MySQL | 7/7 passed，真实本机 Chrome | `ui-mysql-test-report.xml` |
| Postman/Newman + MySQL | 28 requests，56 test scripts，114 assertions，0 failed，平均 54ms | `newman-mysql-junit.xml`、`newman-mysql-report.json` |
| SQL 数据一致性 | DQ-001—DQ-024 全部 `issue_count=0`，在 API/UI/压测写入后复查 | `mysql-consistency-results.txt` |
| AI 评估 | 30/30，Accuracy 1.0，Macro-F1 1.0，高关注召回 1.0 | `ai-evaluation.json` |
| JMeter + MySQL | 20 用户 × 5 循环，340 样本，错误率 0%，吞吐 12.51 samples/s | `jmeter-mysql-html/index.html` |
| MySQL JMeter P90 | 总体 55.9ms；情绪 53ms；统计 15ms；提醒 53ms；注册 551.3ms | `jmeter-mysql-html/statistics.json` |
| 视觉 | 登录、老人首页、情绪历史、家属首页均已生成并人工检查 | `screenshots/` |

## AI 结果边界

30 条数据是均衡的小型策划回归集，不是临床数据或独立盲测集。1.0 指标只能说明当前规则完整覆盖这份基线；反讽、方言、长篇混合情绪与真实分布仍是已知限制。情绪结果不构成医疗诊断或治疗建议。

## 可用于简历的保守表述

> 独立设计并实现 CareGuard QA 适老化关怀平台质量工程，使用 Python/FastAPI/MySQL 8.4、pytest、Playwright、Postman、SQL、JMeter 与 GitHub Actions；设计 50 条功能用例和 11 份缺陷报告。本地回归实现 48 条 API/域测试、5 条 MySQL 合约测试与 7 条 UI 测试全通过，应用覆盖率 90.67%；MySQL 端到端 Postman 28 请求/114 断言 0 失败，24 项数据一致性检查全为 0，JMeter 20 用户基准 340 样本错误率 0%。

性能数字仅代表本机隔离测试环境，不应表述为生产容量或 SLA。
