---
name: ai-switch-os
description: Route AI tasks across multiple available providers, detect quota or transient failures, and hand off to the next provider without losing task context. Use when an AI service hits a limit, is unavailable, or a task should be routed to another tool.
---

# AI Switch OS — Free-first failover skill

## Goal
Keep the user's task moving by selecting among providers the user can legitimately access. This skill does **not** bypass quotas, paywalls, CAPTCHA, login, or service restrictions. It only switches to another provider when that provider is configured and authorized.

## Routing workflow
1. Identify the task type: text/reasoning, coding, image generation, image-to-video, video editing, speech/audio, or research.
2. Read provider availability/configuration and choose the highest-ranked eligible provider for that task.
3. Send the task with a compact, explicit brief: goal, constraints, inputs, completed steps, current output, and requested format.
4. On success, validate the output against the task requirements and return it.
5. If failure occurs:
   - **Rate limit/quota (HTTP 429 or clear quota message):** mark provider as temporarily unavailable for this task; do not keep retrying. Switch to next configured provider.
   - **Transient service/network failure (5xx, timeout, connection):** at most one short retry, then switch.
   - **Auth/permission error (401/403):** do not retry or attempt to evade access controls; report that provider needs valid access and switch only to another already-authorized provider.
   - **Bad request/unsupported task (400/404/422):** do not repeat the same request unchanged. Adjust only if the error clearly indicates a fix; otherwise switch or ask for missing input.
   - **Safety refusal:** do not route the same prohibited request to another provider to get around a refusal. Offer a safe alternative.
6. Preserve task state in a handoff note so a fallback provider does not restart from scratch.
7. Stop when a valid output is produced or all configured providers are exhausted. Then clearly report what succeeded, what failed, and any user action required.

## Handoff packet
Use this template when switching providers:
- Task type:
- User goal:
- Constraints / output format:
- Inputs / source files:
- Work completed:
- Failure reason (brief):
- Remaining task:
- Validation checklist:

Do not include secret API keys, tokens, or credentials in handoff packets or logs.

## Provider configuration
Provider records should include:
- provider name
- supported task types
- access method (API, user-connected integration, or manual web/app workflow)
- credential status (configured / not configured; never expose credential values)
- availability state (ready / quota-limited / temporarily unavailable / needs auth)
- priority and cooldown expiry
- notes on data/privacy or output limitations

Only switch automatically when the next provider has an approved, working integration and the task can be sent safely. If a tool is app-only/manual and no integration exists, give the user a clear step to open/use it rather than claiming an automatic switch.

## Default selection
- Prefer free/local/open-source providers where practical and configured.
- Choose the provider that best matches the task, not merely the next item in a list.
- For tasks involving user files, respect the file's privacy and avoid uploading it to a new provider without user consent.
- Do not send personal, confidential, or sensitive data to third-party providers unless the user has explicitly approved that destination.
- For paid services, confirm before use if payment or paid quota may be consumed.

## Resilience rules
- Use exponential backoff only for transient errors; quota errors should trigger failover immediately.
- Maintain a per-provider cooldown to prevent repeated calls to a provider known to be blocked.
- Avoid duplicate billable calls; idempotency or job IDs should be used where available.
- Save intermediate artifacts and progress before a switch.
- For generated media, record prompt, settings, and output reference so the work can be resumed or recreated.

## Reporting
After the task, give a concise status:
- provider used
- fallback(s) attempted
- result and validation
- next step if providers were exhausted

## Current limitation
This Skill is instruction-based. It cannot by itself make Cloud AI invoke external services, access app-only tools, or detect a provider's hidden quota state. Automatic failover requires Cloud AI to have a supported integration/API and credentials/configuration for the backup providers. If the current host only reads Skills but cannot call APIs/tools, use the handoff instructions manually.
