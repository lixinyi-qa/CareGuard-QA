-- CareGuard QA MySQL data consistency checks
-- Expected result: every query returns issue_count = 0.
-- Run: mysql -h 127.0.0.1 -ucareguard -pcareguard_dev careguard < sql/consistency_checks.sql

SELECT 'DQ-001 duplicate user phone' AS check_name, COUNT(*) AS issue_count
FROM (SELECT phone FROM users GROUP BY phone HAVING COUNT(*) > 1) AS duplicate_phone;

SELECT 'DQ-002 invalid user role' AS check_name, COUNT(*) AS issue_count
FROM users WHERE role NOT IN ('elderly', 'family', 'admin');

SELECT 'DQ-003 invalid phone format' AS check_name, COUNT(*) AS issue_count
FROM users WHERE phone NOT REGEXP '^1[3-9][0-9]{9}$';

SELECT 'DQ-004 orphan care-link elderly' AS check_name, COUNT(*) AS issue_count
FROM care_links cl LEFT JOIN users u ON u.id = cl.elderly_id WHERE u.id IS NULL;

SELECT 'DQ-005 care-link role mismatch' AS check_name, COUNT(*) AS issue_count
FROM care_links cl
JOIN users elderly ON elderly.id = cl.elderly_id
JOIN users family ON family.id = cl.family_id
WHERE elderly.role <> 'elderly' OR family.role <> 'family';

SELECT 'DQ-006 duplicate care link' AS check_name, COUNT(*) AS issue_count
FROM (
  SELECT elderly_id, family_id FROM care_links
  GROUP BY elderly_id, family_id HAVING COUNT(*) > 1
) AS duplicate_link;

SELECT 'DQ-007 invalid care-link status' AS check_name, COUNT(*) AS issue_count
FROM care_links WHERE status NOT IN ('pending', 'active', 'revoked');

SELECT 'DQ-008 active link missing accepted time' AS check_name, COUNT(*) AS issue_count
FROM care_links WHERE status = 'active' AND accepted_at IS NULL;

SELECT 'DQ-009 orphan mood record' AS check_name, COUNT(*) AS issue_count
FROM mood_checkins m LEFT JOIN users u ON u.id = m.user_id WHERE u.id IS NULL;

SELECT 'DQ-010 mood owner role mismatch' AS check_name, COUNT(*) AS issue_count
FROM mood_checkins m JOIN users u ON u.id = m.user_id WHERE u.role <> 'elderly';

SELECT 'DQ-011 invalid emotion label' AS check_name, COUNT(*) AS issue_count
FROM mood_checkins WHERE emotion NOT IN ('positive', 'neutral', 'negative');

SELECT 'DQ-012 confidence out of range' AS check_name, COUNT(*) AS issue_count
FROM mood_checkins WHERE confidence < 0 OR confidence > 100;

SELECT 'DQ-013 blank raw mood text' AS check_name, COUNT(*) AS issue_count
FROM mood_checkins WHERE text IS NULL OR CHAR_LENGTH(TRIM(text)) = 0;

SELECT 'DQ-014 orphan reminder owner' AS check_name, COUNT(*) AS issue_count
FROM reminders r LEFT JOIN users u ON u.id = r.owner_id WHERE u.id IS NULL;

SELECT 'DQ-015 reminder owner role mismatch' AS check_name, COUNT(*) AS issue_count
FROM reminders r JOIN users u ON u.id = r.owner_id WHERE u.role <> 'elderly';

SELECT 'DQ-016 invalid reminder enum' AS check_name, COUNT(*) AS issue_count
FROM reminders
WHERE reminder_type NOT IN ('medication', 'schedule')
   OR recurrence NOT IN ('once', 'daily', 'weekly');

SELECT 'DQ-017 unauthorized reminder creator' AS check_name, COUNT(*) AS issue_count
FROM reminders r
JOIN users creator ON creator.id = r.created_by
LEFT JOIN care_links cl
  ON cl.elderly_id = r.owner_id
 AND cl.family_id = r.created_by
 AND cl.status = 'active'
WHERE r.created_by <> r.owner_id
  AND creator.role <> 'admin'
  AND cl.id IS NULL;

SELECT 'DQ-018 invalid contact priority' AS check_name, COUNT(*) AS issue_count
FROM emergency_contacts WHERE priority < 1 OR priority > 5;

SELECT 'DQ-019 invalid contact phone' AS check_name, COUNT(*) AS issue_count
FROM emergency_contacts WHERE phone NOT REGEXP '^1[3-9][0-9]{9}$';

SELECT 'DQ-020 alert source mismatch' AS check_name, COUNT(*) AS issue_count
FROM alerts a
JOIN mood_checkins m ON m.id = a.source_mood_id
WHERE m.user_id <> a.owner_id;

SELECT 'DQ-021 invalid alert status' AS check_name, COUNT(*) AS issue_count
FROM alerts WHERE status NOT IN ('open', 'acknowledged');

SELECT 'DQ-022 acknowledged alert incomplete' AS check_name, COUNT(*) AS issue_count
FROM alerts
WHERE status = 'acknowledged'
  AND (acknowledged_at IS NULL OR acknowledged_by IS NULL);

SELECT 'DQ-023 audit missing outcome' AS check_name, COUNT(*) AS issue_count
FROM audit_logs WHERE outcome NOT IN ('success', 'denied', 'failure');

SELECT 'DQ-024 orphan audit actor' AS check_name, COUNT(*) AS issue_count
FROM audit_logs a LEFT JOIN users u ON u.id = a.actor_id
WHERE a.actor_id IS NOT NULL AND u.id IS NULL;
