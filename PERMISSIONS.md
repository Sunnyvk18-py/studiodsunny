# SunnyHQ — Authorization Matrix

**This file is the source of truth. Tests are derived from it; it is not derived from the code.**
If a route's behavior disagrees with this table, the route is wrong until this file is deliberately changed.

## Roles

| Role | Intent |
| --- | --- |
| `founder` | Full access. The only role that sees cash, audit, and admin. |
| `pm` | Runs projects and clients. No money, no admin, no audit. |
| `developer` | Works inside assigned projects. Read-only on people and clients. |
| `designer` | Same surface as `developer`. |

`ALL` = every authenticated role. Add roles here first, then to the tests.

**Code mapping:** `pm` means `project_manager` (and `operations_manager` where noted in tests). Other seeded roles (`sales`, `marketing`, `finance`, `freelancer`, `automation_engineer`) are treated as non-founder/non-pm unless this file is updated.

## Response semantics — test all three, they are different bugs

| Situation | Expected |
| --- | --- |
| No session / expired session | **401** |
| Valid session, wrong role | **403** |
| Valid session, right role, not a member of that resource | **404** (never 403 — a 403 confirms the record exists) |
| Valid session, resource genuinely absent | **404** |

The last two must be **indistinguishable**: same status, same body, same timing. If a non-member gets 404 and a nonexistent id gets 404 with a different message, that's an enumeration oracle.

`OWN` in the table below means the check is ownership/membership-based, not role-based — a `developer` may PATCH a task assigned to them but not one on a project they aren't on.

---

## Public — no session required

| Method | Path | Notes |
| --- | --- | --- |
| GET | `/health` | Must expose no version, no dependency status, no DB hostname. |
| POST | `/api/v1/auth/login` | Rate limit per IP **and** per email. Constant-time response whether or not the email exists. |
| POST | `/api/v1/auth/refresh` | Requires refresh cookie. Rotation + reuse detection. |
| POST | `/api/v1/auth/logout` | Idempotent — 204 even with no session. |
| GET | `/api/v1/auth/providers` | Must not reveal whether a given email uses SSO. |
| POST | `/api/v1/auth/2fa/verify` | **Requires a pending-2FA token from `/login`.** Never a raw user id/email. Rate limit hard: 5 attempts then invalidate the pending token. |
| GET | `/api/v1/auth/google/start` | Must set a `state` param. |
| GET | `/api/v1/auth/google/callback` | Must reject a missing/mismatched `state`. Must reject an email outside the allowed domain. |
| POST | `/api/v1/auth/forgot-password` | Always 204, even for unknown emails. Same response time either way. |
| POST | `/api/v1/auth/reset-password` | Single-use token, ≤30min TTL, revokes all existing sessions on success. |
| GET | `/api/v1/auth/invite/{token}` | 404 on expired/used/unknown — never 410, never a distinct message. |
| POST | `/api/v1/auth/accept-invite` | Single-use. Second call → 404. |

---

## Session-only — any authenticated role, acting on self

| Method | Path | Roles | Deny |
| --- | --- | --- | --- |
| GET | `/api/v1/auth/me` | ALL | 401 |
| POST | `/api/v1/auth/logout-all` | ALL | 401 |
| POST | `/api/v1/auth/change-password` | ALL | 401 |
| POST | `/api/v1/auth/2fa/setup` | ALL | 401 |
| POST | `/api/v1/auth/2fa/enable` | ALL | 401 |
| POST | `/api/v1/auth/2fa/disable` | ALL | 401 |
| GET | `/api/v1/auth/sessions` | ALL | 401 |
| DELETE | `/api/v1/auth/sessions/{id}` | OWN | 404 |

`change-password` and `2fa/disable` must **require the current password** even with a valid session — otherwise a stolen session becomes permanent account takeover. `change-password` must revoke all other sessions.

---

## Workspace

| Method | Path | Roles | Deny | Notes |
| --- | --- | --- | --- | --- |
| GET | `/api/v1/dashboard` | ALL | 401 | **Payload must vary by role** — no cash figures for non-founders. Test the response body, not just the status. |
| GET | `/api/v1/desk` | ALL | 401 | Scoped to caller's own assignments. |
| GET | `/api/v1/calendar/events` | ALL | 401 | Must not leak titles of events on projects the caller isn't on. |
| GET | `/api/v1/activity` | ALL | 401 | Filter by resource visibility, not just recency. |
| GET | `/api/v1/search` | ALL | 401 | **See the dedicated search test below.** |
| GET | `/api/v1/notifications` | ALL | 401 | Own only. |
| POST | `/api/v1/notifications/{id}/read` | OWN | 404 | Another user's notification id → 404. |
| POST | `/api/v1/notifications/read-all` | ALL | 401 | Own only. |
| GET | `/api/v1/ai/briefing` | ALL | 401 | Must not summarize records the caller can't read. |
| POST | `/api/v1/ai/ask` | ALL | 401 | RAG retrieval must be permission-filtered **before** the model sees it. |

---

## Clients & cash — founder-gated

| Method | Path | Roles | Deny |
| --- | --- | --- | --- |
| GET | `/api/v1/clients` | founder, pm | 403 |
| GET | `/api/v1/clients/{id}` | founder, pm | 404 |
| POST | `/api/v1/clients` | founder, pm | 403 |
| PATCH | `/api/v1/clients/{id}` | founder, pm | 404 |
| POST | `/api/v1/clients/{id}/archive` | founder, pm | 404 |
| GET | `/api/v1/leads` | founder, pm | 403 |
| GET | `/api/v1/invoices` | **founder** | 403 |
| POST | `/api/v1/invoices` | **founder** | 403 |
| PATCH | `/api/v1/invoices/{id}` | **founder** | 404 |
| GET | `/api/v1/reports` | **founder** | 403 |

Decide deliberately: **should `developer`/`designer` see the client list at all?** Names of prospective clients are often the most sensitive data in a studio. Current setting says no.

---

## Projects & tasks

| Method | Path | Roles | Deny |
| --- | --- | --- | --- |
| GET | `/api/v1/projects` | ALL | 401 (list scoped to membership) |
| GET | `/api/v1/projects/{id}` | OWN (member) | 404 |
| POST | `/api/v1/projects` | founder, pm | 403 |
| PATCH | `/api/v1/projects/{id}` | founder, pm | 404 |
| POST | `/api/v1/projects/{id}/archive` | founder, pm | 404 |
| POST | `/api/v1/projects/{id}/milestones` | founder, pm | 404 |
| GET | `/api/v1/tasks` | ALL | 401 (scoped to member projects) |
| GET | `/api/v1/tasks/{id}` | OWN (project member) | 404 |
| POST | `/api/v1/tasks` | ALL | 403 if not a member of the target project |
| PATCH | `/api/v1/tasks/{id}` | founder, pm, or assignee | 404 |
| POST | `/api/v1/tasks/{id}/archive` | founder, pm, or assignee | 404 |
| GET | `/api/v1/tasks/{id}/comments` | OWN (project member) | 404 |
| POST | `/api/v1/tasks/{id}/comments` | OWN (project member) | 404 |
| PATCH | `/api/v1/tasks/{id}/comments/{comment_id}` | founder, or author | 404 |
| DELETE | `/api/v1/tasks/{id}/comments/{comment_id}` | founder, or author | 404 |

`POST /tasks` is the sneaky one: role check passes, then `project_id` in the body points at a project the caller isn't on. Test explicitly.

---

## People

| Method | Path | Roles | Deny |
| --- | --- | --- | --- |
| GET | `/api/v1/employees` | ALL | 401 |
| GET | `/api/v1/employees/{id}` | ALL | 404 |
| GET | `/api/v1/employees/departments` | ALL | 401 |
| GET | `/api/v1/employees/roles` | ALL | 401 |
| POST | `/api/v1/employees` | **founder** | 403 |
| POST | `/api/v1/employees/invite` | founder, pm | 403 |
| PATCH | `/api/v1/employees/{id}` | founder, or self | 404 |
| DELETE | `/api/v1/employees/{id}` | **founder** | 403 |

`DELETE /employees/{id}` soft-deactivates the employee (`deleted_at`, `is_active=false`) and **revokes every active session** for that user.

Two required tests here:
- A non-founder PATCHing **their own** record must not be able to change `role`, `salary`, `department`, or `is_active` — field-level, not route-level. This is the most common privilege-escalation path in an app shaped like this.
- `GET /employees/{id}` must return a **reduced payload** for non-founders — no salary, no home address, no personal phone. Assert on absent keys.

---

## Chat

| Method | Path | Roles | Deny |
| --- | --- | --- | --- |
| GET | `/api/v1/chat/channels` | ALL | 401 (only channels the caller is in) |
| GET | `/api/v1/chat/channels/{slug}/messages` | OWN (member) | 404 |
| POST | `/api/v1/chat/channels/{slug}/messages` | OWN (member) | 404 |
| PATCH | `/api/v1/chat/channels/{slug}/messages/{id}` | founder, or author | 404 |
| DELETE | `/api/v1/chat/channels/{slug}/messages/{id}` | founder, or author | 404 |
| WS | `/api/v1/chat/ws` | ALL | reject handshake, or close `4401` / `4403` |

WebSocket auth must be checked **before** `accept()`, and re-checked on every channel subscribe — a socket opened while the user was a member must stop delivering after they're removed.

---

## Docs

| Method | Path | Roles | Deny |
| --- | --- | --- | --- |
| GET | `/api/v1/docs` | ALL | 401 (visibility-scoped) |
| GET | `/api/v1/docs/{id}` | OWN (visibility) | 404 |
| POST | `/api/v1/docs` | ALL | 401 |
| PATCH | `/api/v1/docs/{id}` | founder, or author/editor | 404 |
| DELETE | `/api/v1/docs/{id}` | founder, or author | 404 |
| GET | `/api/v1/docs/{id}/yjs` | same as GET doc | 404 |
| WS | `/api/v1/docs/{id}/collab` | same as PATCH doc | close `4403` |

The Yjs endpoints are the easy miss — **a doc's read permission and its CRDT state must be gated identically.** A user denied `GET /docs/{id}` who can still open `/docs/{id}/collab` reads and writes the entire document. Test both together, always.

---

## Files

| Method | Path | Roles | Deny |
| --- | --- | --- | --- |
| GET | `/api/v1/files` | ALL | 401 (scoped) |
| GET | `/api/v1/files/{id}` | OWN | 404 |
| POST | `/api/v1/files` | ALL | 401 |
| PATCH | `/api/v1/files/{id}` | founder, or uploader | 404 |
| DELETE | `/api/v1/files/{id}` | founder, or uploader | 404 |
| GET | `/api/v1/files/{id}/download` | OWN | 404 |

`/download` needs its own attention: if it redirects to a presigned URL, that URL must be short-lived (≤5 min) and generated per-request. If it streams bytes, confirm the permission check happens before the stream opens. Also test upload of a `.svg` and an `.html` — served inline from your own origin, both are stored XSS. Force `Content-Disposition: attachment` and a non-renderable content type.

---

## Admin & audit — founder only, no exceptions

| Method | Path | Roles | Deny |
| --- | --- | --- | --- |
| GET | `/api/v1/audit` | founder | 403 |
| GET | `/api/v1/admin/settings` | founder | 403 |
| PATCH | `/api/v1/admin/settings` | founder | 403 |
| GET | `/api/v1/admin/permissions` | founder | 403 |
| PUT | `/api/v1/admin/permissions/overrides` | founder | 403 |
| GET | `/api/v1/admin/integrations` | founder | 403 |
| GET | `/api/v1/admin/templates` | founder, pm | 403 |
| POST | `/api/v1/admin/templates` | founder, pm | 403 |
| PATCH | `/api/v1/admin/templates/{id}` | founder, pm | 404 |
| DELETE | `/api/v1/admin/templates/{id}` | founder | 404 |
| GET | `/api/v1/debug/boom` | founder | 403 | Deliberate 500 for Sentry verification. Never enable anonymously. |

`GET /admin/integrations` must never return secrets — API keys, tokens, webhook signing secrets. Return `"connected": true` and a masked hint (`sk-...4f2a`) only. Assert no value in the response matches anything in your secrets store.

---

## Tests that don't fit the matrix

**1. Route coverage guard.** Walk `app.routes`; fail if any route is absent from this file. Without it, a new endpoint ships untested.

**2. Search isolation.** Seed a doc, file, client, lead, and task the caller cannot access, each containing the nonce `ZZQX7`. Search `ZZQX7` as every non-founder role. Assert zero results, and assert the nonce appears nowhere in the response body — including in counts, facets, or "did you mean" suggestions.

**3. Override escalation.** After `PUT /admin/permissions/overrides`, assert no override grants a non-founder access to `/audit`, `/invoices`, `/reports`, or `/admin/*`.

**4. Enumeration timing.** For each `{id}` route, compare response time for a nonexistent id vs. a real id the caller can't see. A consistent delta is a leak.

**5. Mass assignment.** For every PATCH/POST, send the full model including `id`, `created_at`, `role`, `org_id`, `is_active`, `owner_id`. Assert the server ignores every field not in its write schema.

**6. IDOR sweep.** For every `{id}` route, substitute an id belonging to a different user/project/client. This is the single highest-yield test in the file.

## Known gaps in the current API

- ~~No deactivate/delete for **employees**~~ — `DELETE /employees/{id}` (soft deactivate + session revoke).
- ~~No archive/delete for **clients**, **projects**, or **tasks**~~ — `POST …/archive` soft-archives via `deleted_at`.
- ~~No session list or per-session revoke~~ — `GET/DELETE /auth/sessions`.
- ~~No `PATCH`/`DELETE` for **comments** or **chat messages**~~ — author or founder.
- Reports remain read-only; invoices support founder write (create/patch).
