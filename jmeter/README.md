# JMeter performance scenario

Default workload: 20 virtual users, 20-second ramp-up, five business loops per user. Each user registers once and then executes mood check-in → mood statistics → reminder creation with random 200–700 ms think time.

```bash
jmeter -n -t jmeter/CareGuard-Smoke-Load.jmx \
  -Jusers=20 -Jramp=20 -Jloops=5 \
  -l test-results/jmeter/results.jtl \
  -e -o test-results/jmeter/html
```

Quality gates embedded in the plan:

- registration/mood/reminder status codes must match 201;
- statistics must return 200;
- mood and reminder requests must finish within 1,500 ms;
- statistics must finish within 1,000 ms;
- the mood response must contain `emotion=positive`.

Run this against dedicated test data only. The command creates one elderly account per thread and five reminders per default thread.
