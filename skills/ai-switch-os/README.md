# AI Switch OS Skill

A reusable instruction skill for free-first multi-provider routing and graceful failover.

## Install
Copy the `skills/ai-switch-os/SKILL.md` into the Skill directory supported by your AI host, or add this repository/skill to the host's skill import flow.

## Files
- `SKILL.md`: routing, failure detection, handoff, privacy, and reporting instructions.
- `providers.example.yaml`: sample provider registry (placeholders only; no secrets).

## Important
A skill provides instructions; it does not magically create API access. Auto-switching requires the host to support provider integrations/tool calls and each fallback to be configured and authorized. Web/app-only tools are marked manual. This skill does not bypass rate limits or access controls.
