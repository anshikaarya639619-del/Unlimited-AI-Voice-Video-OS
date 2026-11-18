# AI Switch OS — Acceptance Tests

Use these tests in a host that supports multiple provider integrations. No real provider call is needed to run the conceptual checks.

1. **Quota failover:** Provider A returns quota/rate-limit error. Router marks A cooldown and chooses eligible B without retrying A.
2. **Transient retry:** Provider A times out. Router retries A once, then selects B if it still fails.
3. **Auth failure:** Provider A returns 401/403. Router does not retry A; marks needs-auth and selects only an already-authorized B.
4. **Unsupported task:** Text provider rejects image task. Router chooses a configured image provider, not another text-only provider.
5. **No providers:** All eligible providers are unavailable. Router reports provider status and gives manual next step; it does not claim success.
6. **Paid provider:** A paid fallback is not used until the user has confirmed it.
7. **Sensitive file:** Private file is not forwarded to a new provider without user consent.
8. **Task recovery:** Provider B receives a handoff packet and continues from the last saved checkpoint, not from zero.
9. **Safety refusal:** A refusal is not routed to another provider to evade safety limits.
10. **Secrets:** API keys never appear in task logs, handoff packets, or committed files.
