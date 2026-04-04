# IMPLEMENTATION_V8.md

## 1. Mục tiêu của tài liệu

Tài liệu này là **file triển khai duy nhất** cho V8, gộp:

- backlog thực thi (trước đây là `docs/planning/IMPLEMENTATION_TASKS_V8.md`)
- thứ tự PR/merge (trước đây là `docs/planning/IMPLEMENTATION_ORDER_V8.md`)

V8 theo hướng: “early-adopter baseline” → “long-running small-team baseline”, nên implementation doc này phải khóa đồng thời:

- lifecycle/retention assumptions
- observability/incident history
- external guardrails và flow control
- trust model (managed credentials là đường chính)
- operator maintenance workflows
- release closure (docs + package + gates đồng bộ)

---

## 2. Quy ước và nguyên tắc

### 2.1 Quy tắc phụ thuộc (không đổi)

- Lifecycle/retention **đi trước** observability persistence.
- Guardrails **đi trước** trust tightening.
- Maintenance workflows phải bám đúng lifecycle + auth + failure semantics đã khóa ở các PR trước.
- Release/support baseline chỉ claim phần nào đã có tests/smoke/docs/conformance tương ứng.

### 2.2 Sơ đồ phụ thuộc tổng thể

**F54 → F55 → F56 → F57 → F58 → F59**  
**PR56 → PR57 → PR58 → PR59 → PR60 → PR61**

Mapping:

- PR56 ↔ F54: Data lifecycle & retention discipline
- PR57 ↔ F55: Durable observability & incident history
- PR58 ↔ F56: External guardrails & flow control
- PR59 ↔ F57: Trust tightening & legacy path minimization
- PR60 ↔ F58: Operator maintenance workflows & hygiene automation
- PR61 ↔ F59: V8 release closure & baseline claims

---

## 3. Thứ tự PR (merge plan)

Nguyên tắc: **mỗi PR chỉ có một mục tiêu chính**, và phải demo/verify được trên baseline hiện có.

### PR56 (F54) — Data lifecycle & retention discipline

- **Mục tiêu:** chốt archive/retention/cleanup/export semantics cho các surface vận hành chính.
- **Điều kiện merge tối thiểu:**
  - có policy rõ cho ít nhất session/activity + public events + webhook deliveries
  - có ít nhất một archive hoặc cleanup path chạy end-to-end
  - cleanup không phá replay/debug/audit assumptions đã support
  - docs lifecycle/retention không mâu thuẫn nhau

### PR57 (F55) — Durable observability & incident history

- **Mục tiêu:** có incident history/telemetry summary đủ bền để đọc sau restart/handoff.
- **Điều kiện merge tối thiểu:**
  - có persistence hoặc export path cho signal/summary quan trọng (không chỉ process-local)
  - correlation giữa request/session/job/runtime/task/credential/delivery rõ hơn
  - operator có history/debug surface tối thiểu cho recent incidents

### PR58 (F56) — External surface guardrails & flow control

- **Mục tiêu:** guardrails giải thích được cho replay/SSE/webhooks (quota/rate/retention window/slow-consumer).
- **Điều kiện merge tối thiểu:**
  - guardrail rõ cho ít nhất replay/SSE và webhook paths
  - error/status mapping rõ + operator visibility (không chỉ timeout “âm thầm”)
  - docs/contract/conformance phản ánh đúng guardrails đã claim

### PR59 (F57) — Trust tightening & legacy path minimization

- **Mục tiêu:** managed credentials là supported path chính; thu hẹp bootstrap/legacy claims.
- **Điều kiện merge tối thiểu:**
  - docs/support matrix không over-claim so với behavior thật
  - managed credential path pass end-to-end trên supported surfaces
  - legacy/bootstrap path được thu hẹp hoặc gắn nhãn rõ (compatibility/dev-only)

### PR60 (F58) — Operator maintenance workflows & hygiene automation

- **Mục tiêu:** operator surface có maintenance flows định kỳ (không chỉ triage/recovery).
- **Điều kiện merge tối thiểu:**
  - có ít nhất một maintenance flow end-to-end (session/credential/webhook)
  - action path có confirmation/reason/audit + operator visibility rõ
  - UI/dashboard/runbook không mâu thuẫn

### PR61 (F59) — V8 release closure & long-running small-team baseline

- **Mục tiêu:** chốt V8 thành release/support baseline đồng bộ: docs + package + gates.
- **Điều kiện merge tối thiểu:**
  - có release notes + upgrade notes cho V8
  - có ít nhất một release candidate/baseline đóng gói lại được
  - release gate chạy lại được theo docs; manifest/docs không drift

---

## 4. Backlog chi tiết (feature slices)

## F54. Data lifecycle và retention discipline

**Phụ thuộc:** F53  
**Mở khóa:** F55  
**Module chính:** `app/api/sessions.py`, `app/services/session_events.py`, `app/services/transcript_export.py`, `app/services/public_event_stream.py`, `app/services/outbound_webhooks.py`, repository lifecycle/retention mới nếu cần, tests retention/cleanup mới nếu cần, `docs/operations/RUNBOOK.md`, `docs/operations/DEPLOYMENT.md`, `docs/reference/DB_SCHEMA.md`

### Việc cần làm
1. Chốt lifecycle policy cho:
   - session và session-adjacent data
   - session activity và transcript exports
   - artifacts
   - public events/subscriptions
   - outbound webhook deliveries
2. Chuẩn hóa archive-first + cleanup semantics:
   - path nào archive
   - path nào expire/prune
   - path nào export-before-prune
   - path nào tuyệt đối không xóa cứng trong baseline V8
3. Thêm retention/cleanup execution path tối thiểu:
   - cleanup cadence hoặc manual operator path
   - config/env defaults cho packaged baseline
   - visibility cho retention backlog và items ngoài retention window
4. Làm rõ audit/recovery assumptions (backup-before-prune, rollback notes).
5. Viết tests + docs cho archive/cleanup happy path và failure explanation path.

### Kết quả đầu ra
- lifecycle/retention assumptions rõ và không drift
- có ít nhất một archive/cleanup path chạy thật và operator đọc được

### Điều kiện hoàn thành
- có policy rõ cho các surface tối thiểu đã nêu
- có archive/cleanup path end-to-end + tests/regression
- docs/runbook/deployment không mâu thuẫn nhau

---

## F55. Durable observability và incident history

**Phụ thuộc:** F54  
**Mở khóa:** F56  
**Module chính:** `app/services/system_status.py`, `app/services/system_telemetry.py`, `app/services/operator_dashboard.py`, `app/services/operator_realtime.py`, repositories liên quan, `docs/operations/OBSERVABILITY.md`, `docs/operations/RUNBOOK.md`

### Việc cần làm
1. Lưu bền (hoặc export) signal/summary quan trọng thay vì chỉ in-memory.
2. Correlation keys rõ hơn giữa request/session/job/runtime/task/credential/delivery.
3. History/debug surface đủ để đọc “recent incidents” sau restart.
4. Docs/runbook giải thích cách đọc signals + assumptions retention của history.

### Kết quả đầu ra
- operator có incident history bền hơn qua restart/handoff
- debug theo thời gian dễ hơn (không phụ thuộc live state)

### Điều kiện hoàn thành
- có đường đọc history sau restart (không trống)
- tests cover các signal/summary trọng yếu
- runbook/observability docs bám đúng behavior

---

## F56. External surface guardrails và flow control

**Phụ thuộc:** F55  
**Mở khóa:** F57  
**Module chính:** `app/services/public_event_stream.py`, `app/services/realtime_transport.py`, `app/services/outbound_webhooks.py`, `app/api/a2a_events.py`, `app/api/a2a_public.py`, docs A2A/public events nếu cần

### Việc cần làm
1. Thêm guardrails/quota nhẹ nhưng rõ cho các external paths phù hợp.
2. Chốt replay/SSE retention window + slow-consumer/cursor-gap semantics.
3. Guardrails cho webhook deliveries: delivery limits, retry visibility, receiver-failure expectations.
4. Update docs/contract/tests/conformance theo đúng guardrails mới.

### Kết quả đầu ra
- failure semantics giải thích được (operator/client thấy “vì sao” và “phục hồi thế nào”)
- replay/SSE/webhooks ít mơ hồ hơn dưới pressure/retention gaps

### Điều kiện hoàn thành
- guardrail rõ cho ít nhất replay/SSE + webhook paths
- docs/governance phản ánh đúng claims
- tests guardrail/failure path pass

---

## F57. Trust tightening và legacy path minimization

**Phụ thuộc:** F56  
**Mở khóa:** F58  
**Module chính:** `app/core/config.py`, `app/core/middleware.py`, `app/api/dependencies.py`, `app/services/access_boundary.py`, `app/services/authz_service.py`, `app/services/integration_credentials.py`, docs deployment/runbook/a2a nếu claim thay đổi

### Việc cần làm
1. Chốt trust model long-running baseline:
   - managed credentials là path chính
   - bootstrap token giữ cho use cases nào
   - actor header paths nào supported vs compatibility/dev-only
2. Thu hẹp support claims + viết migration/handoff notes cho adopter.
3. Enrich failure explanations + operator visibility cho auth failures.
4. Giữ backward path hợp lý cho local/dev (không phá smoke/demo).
5. Tests + docs cho managed credential preferred path + legacy path labeling.

### Kết quả đầu ra
- trust model sạch hơn, claims khớp behavior thật
- managed credentials là đường chính rõ ràng

### Điều kiện hoàn thành
- managed credential path pass end-to-end
- legacy/bootstrap claims bị thu hẹp + gắn nhãn rõ
- regression tests access boundary/credentials pass

---

## F58. Operator maintenance workflows và hygiene automation

**Phụ thuộc:** F57  
**Mở khóa:** F59  
**Module chính:** `app/api/operator_dashboard.py`, `app/api/operator_actions.py`, `app/services/operator_dashboard.py`, `app/services/operator_actions.py`, `app/services/integration_credentials.py`, `app/services/outbound_webhooks.py`, `docs/operator/OPERATOR_UI.md`, `docs/operations/RUNBOOK.md`

### Việc cần làm
1. Chốt tập maintenance workflows tối thiểu:
   - archive/cleanup session-related data (khi phù hợp)
   - credential hygiene: rotate/revoke/expire/disable
   - webhook hygiene: disable/inspect/recover
2. Operator visibility theo hướng maintenance:
   - retention backlog, expired/disabled credentials, outbound hygiene summaries, stale warnings
3. Chuẩn hóa action semantics: confirmation/reason/audit + recovery notes.
4. Đồng bộ UI/dashboard/runbook theo workflows thật.
5. Tests cho maintenance happy path + guardrail + failure/recovery + audit rendering.

### Kết quả đầu ra
- operator có “bề mặt làm việc” cho maintenance định kỳ
- hygiene states quan trọng dễ thấy/triage hơn

### Điều kiện hoàn thành
- có ít nhất một maintenance flow end-to-end
- UI/dashboard/runbook không mâu thuẫn
- regression tests operator surface pass

---

## F59. V8 release closure và long-running small-team baseline

**Phụ thuộc:** F58  
**Mở khóa:** roadmap sau V8  
**Module chính:** `docs/planning/STATUS.md`, `README.md`, `docs/operations/*`, `docs/releases/RELEASE_NOTES_V8.md`, `docs/releases/UPGRADE_NOTES_V8.md`, `scripts/release.ps1`, `scripts/package_release.ps1`, `app/services/release_packaging.py`, `tests/unit/test_release_packaging.py`

### Việc cần làm
1. Chốt V8 thành release/support baseline rõ (versioning + tag/candidate strategy).
2. Đồng bộ docs giữa code/package/support assumptions (status/readme/deployment/local setup/runbook).
3. Chuẩn hóa release gate: smoke/release verification, docs registry, package manifest checks, conformance path nếu cần.
4. Viết tests + docs cho packaging/manifest + release metadata + upgrade notes + checklist.

### Kết quả đầu ra
- V8 trở thành baseline release rõ cho long-running small-team deployment
- docs/package/gates không drift

### Điều kiện hoàn thành
- có release notes + upgrade notes rõ
- release gate chạy lại được theo docs
- manifest/docs/support assumptions đồng bộ

