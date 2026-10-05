# STATE — AgentRouter 400 fix on opencode1-ar (handoff 2026-10-05)

Read order: `AGENTS.md` first (workspace rules), then `BRIEF.md` (rules + setup),
and `CLI-TEST.md` (approved — read FIRST for the loop phase); `PLAN.md` only when
technical history is needed.

## Status
**Setup phase complete and approved. Next session runs the CLI test loop:**
prompts 1–5 from `CLI-TEST.md`, one at a time, on ONE continued session.

## Approved (Samuel)
- proxy.py self-locating fix — `b0f3c55`.
- CLI-TEST.md workflow — `af8a6f3` + this commit; Undo section, Chromium/CDP
  pre-check, playwright preflight all incorporated. Ready to use as the loop
  recipe.

## Done
- Edit 1 (02:15): oc.json provider → `npm:@ai-sdk/anthropic`, baseURL root, backup `oc.json.bak`.
- Edit 2 (10:14): oc.json baseURL → `http://127.0.0.1:8787/v1`, backup `oc.json.bak2`, valid JSON.
- Edit 3 (22:04): proxy.py line 2 → `D = os.path.dirname(os.path.realpath(__file__))`
  (self-locating; `LOG = D + "/proxy.log"` unchanged), backup `proxy.py.bak`.
  Proof: restarted proxy → `#2 22:04:45 POST /v1/messages` → `resp: HTTP 200
  type=text/event-stream`, reply "test". py_compile OK.
- Docs migrated into this repo (`ar-proxy/`): PENDING.md → STATE.md; evidence → `ar-proxy/evidence/`.
- CLI test workflow designed and proven (see `CLI-TEST.md`).

## Findings
- `start.err` (2026-10-05 01:17): proxy.py crashed with `FileNotFoundError` opening
  `…/.opencode-guysoft/ar-proxy/proxy.log` (proxy.py:6). Cause: proxy started from agent
  shell where `~` = `.opencode-guysoft`. **Explained; do not re-investigate.** Edit 3
  (self-locating `D`) now prevents this class of crash entirely.
- Proxy was NOT running at 13:28 (port 8787 closed) although a stale process matched
  `pgrep -f ar-proxy/proxy.py`; restarted it. A fresh proxy start truncates proxy.log when
  it is >1 MB (proxy.py:3), which wiped the old 51828-line log (TUI evidence #3006–#3020
  is still recorded in this file's history below). Request numbering restarts at 1 per start.
- Agent shell env: `$HOME` → `.opencode-guysoft` AND `PREFIX` → `…/.opencode-guysoft-prefix`.
  `PREFIX` breaks opencode1's runtime probe (`~/.local/bin/opencode1` launcher line 16);
  remove it with `env -u PREFIX` (see CLI-TEST.md).
- **Baseline after the last proxy restart:** `#1` is a 404 from the agent's own curl
  `GET /v1/messages`; the baseline `grep -c "HTTP 4"` already counts it. Loop PASSes
  when the count does NOT rise above that baseline. Do not blame a 404 that is `#1`.

## CLI test result (agent, 13:30)
- Prompt 1 ("Say test and nothing else."): POST /v1/messages → `resp: HTTP 200 type=text/event-stream`
  (proxy.log #2, 13:30:02), reply "test". First run (13:29) failed with "Cannot connect to API"
  because the proxy was dead — invalid test, not a config failure.
- Continuation (13:37): second prompt via `--session ses_ef3f5…` → proxy.log #3, `n_messages: 3`,
  roles `["user","assistant","user"]` — prior history carried. Reply "test2".
- Zero HTTP 400. (The 404 at #1 is the agent's own curl, not opencode.)

## Next (loop phase, NEW session)
1. Per `CLI-TEST.md`: run prompts 1–5 in order, one at a time, continuing the
   session with `--session <id>` from the previous request's `x-session-id`.
2. Before prompts 2–4: if `curl -s -o /dev/null -w "%{http_code}\n" -m 5
   http://127.0.0.1:9222/json/version` is NOT `200`, START Chromium yourself:
   `HOME=/data/data/com.termux/files/home env -u PREFIX chromium-cdp start opencode1`,
   wait a few seconds, re-check; if still not 200 → STOP and tell Samuel.
   Never start a second Chromium when the check already returns 200. Never
   `pkill -f`; stop browsers only by PID.
3. Success gates: proxy.log shows `POST /v1/messages` + `resp: HTTP 200` JSON/SSE (never
   `text/html`), error count does not rise above baseline (which already includes #1 404).

## Cleanup (next session)
- `proxy.py.bak` — git history (this repo) replaces it; safe to delete once the
  loop is done. Verify `git status` clean before deleting anything.

## Stop reason
Setup phase complete: both edits approved, CLI-TEST.md finalized. Stopping per
Samuel's instruction; the loop runs in a fresh session.