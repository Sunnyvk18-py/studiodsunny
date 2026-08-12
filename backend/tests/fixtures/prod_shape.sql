-- Scrubbed production-shaped dump for migration tests.
-- Generated/scrubbed by scripts/scrub_dump.py — do not commit raw dumps.
-- PII replaced; IDs and foreign keys preserved.
-- Apply AFTER alembic upgrade head (INSERT-only). No alembic_version row.

BEGIN;

INSERT INTO organizations (id, name, slug, created_at, updated_at, timezone, currency)
VALUES (
  '3c8a1e90-7b2f-4d11-9c4a-0f6b2a8d1e55',
  'Scrubbed Name a1b2c3d4',
  'studio-sunny',
  NOW(),
  NOW(),
  'Asia/Kolkata',
  'INR'
);

INSERT INTO users (
  id, email, hashed_password, first_name, last_name, display_name,
  role_key, is_active, is_superadmin, email_verified, org_id, created_at, updated_at
) VALUES
(
  'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1',
  'user_founder01@example.invalid',
  '$argon2id$v=19$m=65536,t=3,p=4$c2NydWJiZWQk$scrubbedhashscrubbedhashscrub',
  'Scrubbed Name f001',
  'Scrubbed Name l001',
  'Scrubbed Name d001',
  'founder',
  TRUE,
  FALSE,
  TRUE,
  '3c8a1e90-7b2f-4d11-9c4a-0f6b2a8d1e55',
  NOW(),
  NOW()
),
(
  'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa2',
  'user_pm000002@example.invalid',
  '$argon2id$v=19$m=65536,t=3,p=4$c2NydWJiZWQk$scrubbedhashscrubbedhashscrub',
  'Scrubbed Name f002',
  'Scrubbed Name l002',
  'Scrubbed Name d002',
  'project_manager',
  TRUE,
  FALSE,
  TRUE,
  '3c8a1e90-7b2f-4d11-9c4a-0f6b2a8d1e55',
  NOW(),
  NOW()
),
(
  'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa3',
  'user_dev000003@example.invalid',
  '$argon2id$v=19$m=65536,t=3,p=4$c2NydWJiZWQk$scrubbedhashscrubbedhashscrub',
  'Scrubbed Name f003',
  'Scrubbed Name l003',
  'Scrubbed Name d003',
  'developer',
  TRUE,
  FALSE,
  TRUE,
  '3c8a1e90-7b2f-4d11-9c4a-0f6b2a8d1e55',
  NOW(),
  NOW()
);

INSERT INTO employees (
  id, user_id, job_title, employment_type, salary, salary_currency,
  weekly_capacity_hours, availability, skills, leave_balance_days, org_id, created_at, updated_at
) VALUES
(
  'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbb1',
  'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1',
  'Founder',
  'full_time',
  75000.00,
  'INR',
  40,
  'available',
  '[]'::json,
  12,
  '3c8a1e90-7b2f-4d11-9c4a-0f6b2a8d1e55',
  NOW(),
  NOW()
),
(
  'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbb2',
  'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa2',
  'Project Manager',
  'full_time',
  75000.00,
  'INR',
  40,
  'available',
  '[]'::json,
  12,
  '3c8a1e90-7b2f-4d11-9c4a-0f6b2a8d1e55',
  NOW(),
  NOW()
),
(
  'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbb3',
  'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa3',
  'Developer',
  'full_time',
  75000.00,
  'INR',
  40,
  'busy',
  '[]'::json,
  8,
  '3c8a1e90-7b2f-4d11-9c4a-0f6b2a8d1e55',
  NOW(),
  NOW()
);

INSERT INTO clients (
  id, business_name, slug, email, phone, status, lifetime_value,
  onboarding_step, onboarding_complete, org_id, created_at, updated_at
) VALUES (
  'cccccccc-cccc-cccc-cccc-ccccccccccc1',
  'Scrubbed Name client01',
  'scrubbed-client-01',
  'user_client01@example.invalid',
  '+15551234567',
  'active',
  0,
  1,
  FALSE,
  '3c8a1e90-7b2f-4d11-9c4a-0f6b2a8d1e55',
  NOW(),
  NOW()
);

INSERT INTO projects (
  id, name, slug, client_id, project_manager_id, project_type, status, health,
  priority, progress, tech_stack, hours_spent, is_pinned, budget_currency, org_id, created_at, updated_at
) VALUES (
  'dddddddd-dddd-dddd-dddd-ddddddddddd1',
  'Scrubbed Name project01',
  'scrubbed-project-01',
  'cccccccc-cccc-cccc-cccc-ccccccccccc1',
  'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa2',
  'Website',
  'in_progress',
  'healthy',
  'high',
  40,
  '[]'::json,
  12,
  FALSE,
  'INR',
  '3c8a1e90-7b2f-4d11-9c4a-0f6b2a8d1e55',
  NOW(),
  NOW()
);

INSERT INTO project_members (id, project_id, user_id, role_on_project, org_id, created_at, updated_at) VALUES
(
  'eeeeeeee-eeee-eeee-eeee-eeeeeeeeeee1',
  'dddddddd-dddd-dddd-dddd-ddddddddddd1',
  'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa2',
  'project_manager',
  '3c8a1e90-7b2f-4d11-9c4a-0f6b2a8d1e55',
  NOW(),
  NOW()
),
(
  'eeeeeeee-eeee-eeee-eeee-eeeeeeeeeee2',
  'dddddddd-dddd-dddd-dddd-ddddddddddd1',
  'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa3',
  'contributor',
  '3c8a1e90-7b2f-4d11-9c4a-0f6b2a8d1e55',
  NOW(),
  NOW()
);

INSERT INTO tasks (
  id, title, project_id, assignee_id, created_by_id, priority, status, tags, checklist,
  sort_order, org_id, created_at, updated_at
) VALUES
(
  'ffffffff-ffff-ffff-ffff-fffffffffff1',
  'Scrubbed Name task0001',
  'dddddddd-dddd-dddd-dddd-ddddddddddd1',
  'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa3',
  'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa2',
  'medium',
  'todo',
  '[]'::json,
  '[]'::json,
  0,
  '3c8a1e90-7b2f-4d11-9c4a-0f6b2a8d1e55',
  NOW(),
  NOW()
),
(
  'ffffffff-ffff-ffff-ffff-fffffffffff2',
  'Scrubbed Name task0002',
  'dddddddd-dddd-dddd-dddd-ddddddddddd1',
  'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa3',
  'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa2',
  'high',
  'in_progress',
  '[]'::json,
  '[]'::json,
  1,
  '3c8a1e90-7b2f-4d11-9c4a-0f6b2a8d1e55',
  NOW(),
  NOW()
);

INSERT INTO invoices (
  id, number, client_id, project_id, amount, tax, discount, currency, status, org_id, created_at, updated_at
) VALUES (
  '99999999-9999-9999-9999-999999999991',
  'INV-SCRUB-0001',
  'cccccccc-cccc-cccc-cccc-ccccccccccc1',
  'dddddddd-dddd-dddd-dddd-ddddddddddd1',
  250000.00,
  0,
  0,
  'INR',
  'sent',
  '3c8a1e90-7b2f-4d11-9c4a-0f6b2a8d1e55',
  NOW(),
  NOW()
);

COMMIT;
