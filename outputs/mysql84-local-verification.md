# CareGuard QA — MySQL 8.4 本机实测报告

实测时间：2026-08-24（Asia/Shanghai）

结论：**PASS**

## 安装与隔离

- 来源：MySQL 官方 CDN，MySQL Community Server 8.4.11 LTS Windows x64 ZIP。
- 文件大小：281,191,914 bytes。
- MD5：`2e833921898a9a030ea6bfe81bd811bc`。
- SHA-256：`a492371d687d2bab088b0062581144a0044b8964baefdf4faa579292b423d25c`。
- 服务地址：`127.0.0.1:3307`，未占用默认 3306。
- 数据库：`careguard_test`；应用账号：`careguard@127.0.0.1`。
- 未覆盖电脑原有 MySQL 5.6，未注册 Windows 服务，二进制与数据均位于 Git 忽略的 `work/mysql-runtime/`。

数据库实际返回：

```text
version=8.4.11
port=3307
database=careguard_test
current_user=careguard@127.0.0.1
character_set=utf8mb4
collation=utf8mb4_0900_ai_ci
storage_engines=InnoDB
table_count=7
```

## 实测矩阵

| 测试层 | 实际执行 | 结果 |
|---|---:|---:|
| MySQL pytest 合约 | 5 cases | 5 passed |
| Postman/Newman 端到端 API | 28 requests / 114 assertions | 0 failed |
| Playwright + Chrome UI | 7 cases | 7 passed |
| SQL 一致性 | DQ-001—DQ-024 | 24/24 零问题 |
| JMeter + MySQL | 20 users × 5 loops / 340 samples | 0 errors |

MySQL 合约覆盖版本与连接、InnoDB/utf8mb4、唯一约束与外键、中文及 Emoji 往返、事务回滚，以及孤儿外键写入拒绝。

## Newman 结果

- 总请求：28，失败 0。
- 断言：114，失败 0。
- 平均响应：54ms；最小 6ms；最大 469ms。
- 覆盖注册认证、授权绑定、情绪三分类、家属原文隔离、提醒、联系人脱敏、告警、审计、隐私导出和模型卡。

## JMeter 结果

| 事务 | 样本 | 错误率 | 平均 | P90 | P95 | 最大 |
|---|---:|---:|---:|---:|---:|---:|
| 总体 | 340 | 0% | 47.27ms | 55.9ms | 390ms | 987ms |
| 情绪写入 | 100 | 0% | 26.96ms | 53ms | 57.85ms | 92ms |
| 情绪统计 | 100 | 0% | 13.39ms | 15ms | 17.95ms | 92ms |
| 提醒写入 | 100 | 0% | 25.92ms | 53ms | 56ms | 86ms |
| 注册 | 20 | 0% | 421.6ms | 551.3ms | 564ms | 564ms |

总体吞吐为 12.51 samples/s。总体最大 987ms 来自 JMeter 内部的账号唯一值生成采样器，不是业务 HTTP 端点。压测结束后再次运行 24 项 SQL 检查，结果仍全部为 0。

## 证据文件

- `mysql-contract-junit.xml`
- `newman-mysql-junit.xml`
- `newman-mysql-report.json`
- `ui-mysql-test-report.xml`
- `mysql-consistency-results.txt`
- `jmeter-mysql-results.jtl`
- `jmeter-mysql-html/index.html`

## 边界

这是单机隔离环境的质量与性能基线，不是生产容量测试，不承诺公网部署的 SLA。正式上线仍需在目标硬件、生产等价网络、独立压测数据与监控环境中复测。
