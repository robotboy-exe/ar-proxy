# STATE — AgentRouter 400 fix on opencode1-ar (handoff 2026-10-05)

Read order: `AGENTS.md` first (workspace rules), then `BRIEF.md` (rules + setup),
and `CLI-TEST.md` if it exists; `PLAN.md` only when technical history is needed.

## Status
**Edit 2 CLI-tested: PASS. Waiting for USER's go to run TUI prompt 1.**

## Done
- Edit 1 (02:15): oc.json provider → `npm:@ai-sdk/anthropic`, baseURL root, backup `oc.json.bak`.
- Edit 2 (10:14): oc.json baseURL → `http://127.0.0.1:8787/v1`, backup `oc.json.bak2`, valid JSON.
- Edit 3 (22:04): proxy.py line 2 → `D = os.path.dirname(os.path.realpath(__file__))`
  (self-locating; `LOG = D + "/proxy.log"` unchanged), backup `proxy.py.bak`.
  Proven: restarted proxy → log line `#2 22:04:45 POST /v1/messages` → `resp: HTTP 200
  type=text/event-stream`, reply "test". py_compile OK.
- Docs migrated into this repo (`ar-proxy/`): PENDING.md → STATE.md; evidence → `ar-proxy/evidence/`.
- CLI test workflow designed and proven (see `CLI-TEST.md`).

## Findings
- `start.err` (2026-10-05 01:17): proxy.py crashed with `FileNotFoundError` opening
  `…/.opencode-guysoft/ar-proxy/proxy.log` (proxy.py:6). Cause: proxy started from agent
  shell where `~` = `.opencode-guysoft`. **Explained; do not re-investigate.** Start proxy
  with `HOME=/data/data/com.termux/files/home` (AGENTS.md).
- Proxy was NOT running at 13:28 (port 8787 closed) although a stale process matched
  `pgrep -f ar-proxy/proxy.py`; restarted it. A fresh proxy start truncates proxy.log when
  it is >1 MB (proxy.py:3), which wiped the old 51828-line log (TUI evidence #3006–#3020
  is still recorded in this file's history below). Request numbering restarts at 1 per start.
- Agent shell env: `$HOME` → `.opencode-guysoft` AND `PREFIX` → `…/.opencode-guysoft-prefix`.
  `PREFIX` breaks opencode1's runtime probe (`~/.local/bin/opencode1` launcher line 16);
  remove it with `env -u PREFIX` (see CLI-TEST.md).

## CLI test result (agent, 13:30)
- Prompt 1 ("Say test and nothing else."): POST /v1/messages → `resp: HTTP 200 type=text/event-stream`
  (proxy.log #2, 13:30:02), reply "test". First run (13:29) failed with "Cannot connect to API"
  because the proxy was dead — invalid test, not a config failure.
- Continuation (13:37): second prompt via `--session ses_ef3f5…` → proxy.log #3, `n_messages: 3`,
  roles `["user","assistant","user"]` — prior history carried. Reply "test2".
- Zero HTTP 400. (`HTTP 404` at #1 is the agent's own curl `GET /v1/messages`, not opencode.)

## Next
1. USER final TUI pass: fresh `oc1` session, prompt list per `TUI-TEST.md`.
2. Success gates: proxy.log shows `POST /v1/messages` + `resp: HTTP 200` JSON/SSE (never
   `text/html`), zero `HTTP 400` / `Invalid schema` / `content[].thinking`.

## Stop reason
CLI test passed; docs committed. Waiting for USER go-ahead. proxy.py unchanged (`_fix_schema`
active; `_fix_reasoning` dormant on Anthropic bodies — see PLAN.md).