# PLAN: fix AgentRouter 400s on opencode1-ar (deepseek-v4-flash)

Status: SUPERSEDED — see "REVISION 2 (2026-10-05)" below. Original proxy-only plan was
approved and implemented, then routing discovery showed the endpoint-family switch is the
correct fix; the proxy rewrites are now dormant/inert.

## Constraints (from BRIEF.md)
- Probe first; no edits until a probe shows the cause.
- Before any edit: back up the file and show the exact change.
- Never open/print ~/.local/share/opencode1/opencode/auth.json.
- Do not touch v2 (plain `opencode`) or Guysoft's own config.
- Termux has no /tmp. Use ~.
- Evidence dir: ~/ar-proxy/evidence/. Never delete.
- Model is only agentrouter/deepseek-v4-flash. Do NOT use gpt-5.6-sol / build provider.
- Sandbox note: this environment can reach agentrouter.org (HTTP 200) and the proxy port
  127.0.0.1:8787, but `opencode1 run` defaulted to build/gpt-5.6-sol which bypasses the
  proxy. Live TUI verification must be run by the user in their Termux (`oc1`).

## Root causes (established, evidence-backed)

### Failure 1: "Invalid schema ... 'playwright-cdp_browser_close': null is not of type \"array\"" (HTTP 400)
- playwright MCP `browser_close` = `z6.object({})` (empty schema). It advertises
  `{"type":"object","properties":{},"$schema":"...2020-12...","additionalProperties":false}`
  with NO `required` (verified via MCP `tools/list`; source coreBundle.js:67617).
- Every other playwright tool has a real non-empty `required:[...]`; only browser_close is empty.
- When opencode1 serializes that empty schema it sometimes emits `"required": null`
  (20:31/20:47 sessions). A strict upstream backend rejects it; laxer ones accept it
  (proxy-tail.log: #4 vs #5 byte-identical `bytes=51042` -> 400 vs 200). Nondeterministic
  because AgentRouter fans requests to different backends.
- 21:39 session (evidence/req_1..3.json) had NO `required:null` anywhere and returned 200s —
  the null may already be gone, but recurrence is possible; proxy must defend anyway.

### Failure 2: "The `content[].thinking` in the thinking mode must be passed back to the API." (HTTP 400)
- resp_2.txt: the stream carries 53 deltas with non-null `reasoning_content` -> deepseek model reasons.
- opencode echoes reasoning as top-level `reasoning_content` on assistant messages
  (`content:""` + `tool_calls`) — DeepSeek-native-correct (evidence/req_2.json, req_3.json).
- One backend/adapter is Anthropic-style thinking mode and demands the echo inside
  `content[].thinking`; opencode's DeepSeek-style echo fails its validator.
- req_3 (roles system,user,assistant,tool,assistant,tool) is the only thinking-failure sample;
  structurally identical requests returned 200 at 20:47 (#7) -> likely the same
  nondeterministic-backend signature. Only one data point; wait for TUI verification.

## Implementation (proxy-only, no opencode config changes unless fallback)

File: ~/ar-proxy/proxy.py  (backup -> ~/ar-proxy/proxy.py.bak before editing)

Inside the existing parse block in `_go()` (after the `req body` log line, BEFORE the
AR_DEBUG write so saved req_N.json shows the fixed body), insert:

```python
            def _fix_schema(o):
                d = False
                if isinstance(o, dict):
                    for k, v in list(o.items()):
                        if v is None and k in ("required", "prefixItems", "enum", "allOf", "anyOf", "oneOf"):
                            o[k] = []; d = True
                        elif isinstance(v, (dict, list)):
                            d |= _fix_schema(v)
                elif isinstance(o, list):
                    for v in o:
                        d |= _fix_schema(v)
                return d

            def _fix_reasoning(j):
                d = False
                for m in j.get("messages") or []:
                    if not isinstance(m, dict) or m.get("role") != "assistant":
                        continue
                    parts = m.get("content") if isinstance(m.get("content"), list) else m.get("content")
                    if isinstance(parts, list) and any(isinstance(p, dict) and p.get("type") == "thinking" for p in parts):
                        continue
                    rc = m.pop("reasoning_content", None)
                    if not rc:
                        continue
                    blocks = []
                    if isinstance(parts, list):
                        blocks = [p for p in parts if not (isinstance(p, dict) and p.get("type") == "text" and not p.get("text"))]
                    elif parts:
                        blocks = [{"type": "text", "text": parts}]
                    m["content"] = [{"type": "thinking", "thinking": rc}] + blocks
                    d = True
                return d

            if isinstance(j, dict):
                if _fix_schema(j) or _fix_reasoning(j):
                    body = json.dumps(j, ensure_ascii=False).encode()
                    log(f"  FIXED request body (schema nulls / thinking echo)")
```

- `_fix_schema` fixes Failure 1: any null array-schema keyword -> `[]`.
- `_fix_reasoning` fixes Failure 2: assistant reasoning echo -> Anthropic-style `content[].thinking`.
  Idempotent; leaves non-reasoning messages untouched.
- Only re-encodes body when something actually changed.

## Steps (fresh chat continues here)
1. Backup + edit proxy.py (exact change above). `python3 -m py_compile ~/ar-proxy/proxy.py`.
2. Kill running proxy and restart: `pkill -f ar-proxy/proxy.py; AR_DEBUG=1 nohup python ~/ar-proxy/proxy.py >/dev/null 2>&1 &`
   (or let opencode1-ar auto-start it). Keep AR_DEBUG=1 during verification.
3. Spot check with evidence: replay req_3.json through the proxy twice and confirm the
   transformed body returns 200 (proves both rewrites work end-to-end).
   Use the replay tool (reads AGENTROUTER_API_KEY from env, never prints it):
   `AGENTROUTER_API_KEY=... python ~/ar-proxy/replay.py ~/ar-proxy/evidence/req_3.json 2`
   - DONE, part 1: transform verified structurally (AR_DEBUG file: `content[].thinking` blocks,
     no `reasoning_content`, no `required: null`; `FIXED request body` logged).
   - DONE, part 2: authenticated replay from the sandbox could NOT complete (env key the sandbox
     inherited is rejected by agentrouter, 401; the same key in the user's shell returns 200).
     Resolution: user runs the replay line above in their own shell for true HTTP 200 x2, or
     proceeds straight to the TUI test.
4. USER runs the "Done when" test in the TUI: `oc1`, deepseek-v4-flash, use playwright-cdp
   tools (open a page, then close it), several turns. Expect zero `HTTP 400` / `Invalid schema`
   / `content[].thinking` in ~/ar-proxy/proxy.log.

## Fallback (only if TUI test shows a regression)
- If a DeepSeek-native backend now 400s on array `content` (unlikely but possible), disable
  `_fix_reasoning` and instead: (a) reproduce 2-3 AR_DEBUG captures to confirm the strict
  backend is the only one failing, then (b) decide between transforming only when needed or
  toggling reasoning off in opencode1 config (provider/model options in
  ~/ar-proxy/oc.json or ~/.config/opencode1/opencode/opencode.jsonc).

## REVISION 2 (2026-10-05): switch endpoint family — root-cause fix

### Why the original proxy plan was insufficient
Replaying the F2 sample through the fixed proxy produced
`422 messages[2]: unknown variant "thinking", expected one of "text","image_url","file"`
(OpenAI-native serde backend). Evidence: the OpenAI path (`/v1/chat/completions`) fans to
channels with **contradictory** thinking conventions: one demands `content[].thinking`
(the original F2 400), another rejects `thinking` content parts. No single request body can
satisfy all of them. Retries also hit **503** = "no available channel" (wrong/offline model),
not a client bug.

### Routing facts (from agentrouter.org/docs/opencode.html, verified live)
- Endpoint family is chosen STATICALLY by provider `npm` + `baseURL`, no per-request pin:
  - `@ai-sdk/anthropic`, baseURL **without** `/v1` → `POST /v1/messages`, `x-api-key`.
  - `@ai-sdk/openai-compatible`, baseURL **with** `/v1` → `POST /v1/chat/completions`, Bearer.
  - Docs: "两类方法并行，不要混用" (run in parallel, don't mix).
- `deepseek-v4-flash` supports **both** families (`/v1/models → supported_endpoint_types`).
  General models default to the OpenAI gateway, but Anthropic is fully supported.
- Live tiny tests, `POST /v1/messages` (through the proxy), all HTTP 200:
  minimal request (returns Anthropic extended-thinking `content[].thinking` + `signature`),
  and reasoning turns passed back WITH and WITHOUT a signature. So the Anthropic family has one
  consistent thinking-echo contract and preserves full reasoning for multi-turn.

### Edit 1 — APPLIED 2026-10-05 02:15, backup `~/ar-proxy/oc.json.bak`
`oc.json`: provider `agentrouter` → `"npm":"@ai-sdk/anthropic"`,
`"baseURL":"http://127.0.0.1:8787"` (no `/v1`), added
`"models":{"deepseek-v4-flash":{"name":"DeepSeek V4 Flash"}}`. Valid JSON. proxy.py UNCHANGED
(Option A): `_fix_schema` kept as harmless guard; `_fix_reasoning` inert on Anthropic bodies.

### TUI test 04:40 — FAILED (prompt 1), cause diagnosed
opencode1 v1.18.33 bundled `@ai-sdk/anthropic` posts to `{baseURL}/messages` (it appends
`/messages`, NOT `/v1/messages`). With baseURL at root (`…:8787`) → proxy got `POST /messages`
(proxy.log #3006–#3020), forwarded to `agentrouter.org/messages` → returns the admin console
HTML (`type=text/html`, 1586 B, HTTP 200) → opencode sees garbage, prompt fails.

### Next action (PROPOSED, awaiting user go) — Edit 2
`oc.json` baseURL → `http://127.0.0.1:8787/v1` so the anthropic provider's `/messages` suffix
yields the proven-working `/v1/messages`. Then restart proxy (AR_DEBUG optional; remember the
explicit real `HOME=` when starting from the agent shell) and USER reruns the TUI prompt list.
Success = proxy.log shows `POST /v1/messages` + `resp: HTTP 200` JSON/SSE (never `text/html`)
and zero `HTTP 400` / `Invalid schema` / `content[].thinking`.

## Files/state facts for the next chat
- Proxy: ~/ar-proxy/proxy.py (port 127.0.0.1:8787), log ~/ar-proxy/proxy.log, AR_DEBUG=1 writes req_N.json/resp_N.txt (numbered from 1 per proxy start).
- Replay tool (authenticated spot checks): ~/ar-proxy/replay.py — `AGENTROUTER_API_KEY=... python ~/ar-proxy/replay.py <req.json> [count]`. Key from env only, never printed/logged. Env is inherited by the process that launches opencode, so the sandbox may hold a different/stale key than the user's shell.
- Override: ~/ar-proxy/oc.json (agentrouter baseURL -> proxy). Launcher: ~/.local/bin/opencode1-ar (alias `oc1`).
- opencode1 config: ~/.config/opencode1/opencode/opencode.jsonc (playwright-cdp MCP).
- opencode1 runtime: /data/data/com.termux/files/usr/lib/opencode1/runtime/opencode.
- playwright MCP pkg: ~/.npm/_npx/381cec31605a419a/node_modules/@playwright/mcp (v0.0.83); browser_close schema at playwright-core/lib/coreBundle.js:67617.