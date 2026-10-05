# STATE — AgentRouter 400 fix on opencode1-ar (handoff 2026-10-05)

Read order: `AGENTS.md` first (workspace rules), then `BRIEF.md` (rules + setup),
and `CLI-TEST.md` if it exists; `PLAN.md` only when technical history is needed.

## Status
**Edit 2 applied, not yet tested.**

## Done
- Edit 1 (02:15): oc.json provider → `npm:@ai-sdk/anthropic`, baseURL root, backup `oc.json.bak`.
- Edit 2 (10:14): oc.json baseURL → `http://127.0.0.1:8787/v1`, backup `oc.json.bak2`, valid JSON.
- Docs migrated into this repo (`ar-proxy/`): PENDING.md → STATE.md; evidence → `ar-proxy/evidence/`.

## Last test result
TUI test 04:40 → FAILED (prompt 1): opencode1 spoke Anthropic protocol but posted to
`{baseURL}/messages` (no `/v1`); proxy forwarded to agentrouter.org/messages → AgentRouter
admin-console HTML (HTTP 200, `type=text/html`, 1586 B). 15 attempts, proxy.log #3006–#3020
(04:39:44–04:40:22). Edit 2 fixed the path to proven-working `/v1/messages`; no retest since.

## Next
1. Agent CLI test with `--model agentrouter/deepseek-v4-flash` (no new proxy.log line = invalid test).
2. USER final TUI pass: fresh `oc1` session, prompt list per `TUI-TEST.md`.
3. Success gates: proxy.log shows `POST /v1/messages` + `resp: HTTP 200` JSON/SSE (never
   `text/html`), zero `HTTP 400` / `Invalid schema` / `content[].thinking`.

## Stop reason
Docs-only session; stopping after the two commits. Next real test = CLI test of Edit 2. proxy.py
unchanged (`_fix_schema` active; `_fix_reasoning` dormant on Anthropic bodies — see PLAN.md).