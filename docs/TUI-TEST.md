# TUI test for opencode1-ar (run by Samuel, not the agent)

The agent cannot use the TUI. Samuel sends these prompts himself
and the agent only reads the log afterwards.

## Before starting
- Run: termux-wake-lock
- Count existing errors: grep -c "HTTP 4" ~/ar-proxy/proxy.log
- Start opencode1-ar and choose model deepseek-v4-flash.
- Wait at most 2 minutes per prompt. If no spinner or reply,
  press ctrl+c and check the log.

## Prompts (send one at a time, in order)
1. Say test and nothing else.
   (No tools. Checks the route works at all. If it fails, stop.)
2. Open https://example.com with the browser tool and tell me the
   page title.
   (One tool call. The "thinking" 400 first appeared here.)
3. Now go to https://example.org, tell me the main heading, then
   close the browser.
   (Several tool calls, ending with browser_close, the tool named
   in the schema error.)
4. Open https://example.com again, tell me what the page says, then
   close it.
   (Reopen after a close, with a longer history.)
5. Compare the two pages you visited and tell me which has more
   text. Explain your reasoning.
   (Reasoning-heavy answer, no tools.)

## After the last prompt
- grep -c "HTTP 4" ~/ar-proxy/proxy.log
- tail -n 30 ~/ar-proxy/proxy.log

## Pass
- Error count unchanged from before the test.
- Log shows POST /v1/messages (not /messages) and resp: HTTP 200
  with type=text/event-stream.
- ODD[no-choices] lines are expected and harmless (proxy.py is
  unchanged, so it flags Anthropic-format lines).

## Fail signs
- type=text/html in resp: wrong path, AgentRouter returned its web
  console page.
- 401 "unauthorized client": client identification not accepted.
- New 400 or 422: copy the exact error text and the log tail.
- Browser tool fails to launch while the log is clean: Playwright
  problem, not this fix.

## Undo
cp ~/ar-proxy/oc.json.bak ~/ar-proxy/oc.json
(oc.json.bak2 holds the version before the /v1 edit.)
