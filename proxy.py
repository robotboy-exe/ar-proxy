import http.server, http.client, json, os, time, threading, itertools
D = os.path.expanduser("~/ar-proxy"); LOG = D + "/proxy.log"
open(LOG, "w").close() if os.path.exists(LOG) and os.path.getsize(LOG) > 1_000_000 else None
n = itertools.count(1); lock = threading.Lock()
def log(s):
    with lock, open(LOG, "a") as f: f.write(s + "\n")
SECRET = ("authorization", "x-api-key", "cookie", "set-cookie")
class H(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def _go(self):
        i = next(n)
        body = self.rfile.read(int(self.headers.get("Content-Length") or 0))
        h = {k: v for k, v in self.headers.items() if k.lower() not in ("host", "accept-encoding", "connection", "content-length")}
        h["Accept-Encoding"] = "identity"
        log(f"#{i} {time.strftime('%H:%M:%S')} {self.command} {self.path}")
        log("  req headers: " + json.dumps({k: ("<redacted>" if k.lower() in SECRET else v) for k, v in h.items()}))
        try:
            j = json.loads(body); ms = j.get("messages", [])
            log("  req body: " + json.dumps({"keys": list(j), "model": j.get("model"), "stream": j.get("stream"), "stream_options": j.get("stream_options"), "n_messages": len(ms), "roles": [m.get("role") for m in ms][:6], "n_tools": len(j.get("tools") or []), "tool_choice": j.get("tool_choice"), "temperature": j.get("temperature"), "max_tokens": j.get("max_tokens") or j.get("max_completion_tokens"), "bytes": len(body)}))
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
                    log("  FIXED request body (schema nulls / thinking echo)")
            if os.environ.get("AR_DEBUG"): open(f"{D}/req_{i}.json", "wb").write(body)
        except Exception:
            log(f"  req body: non-JSON {len(body)} bytes")
        c = http.client.HTTPSConnection("agentrouter.org", timeout=180)
        try:
            c.request(self.command, self.path, body=body or None, headers=h); r = c.getresponse()
        except Exception as e:
            log(f"  upstream error: {e!r}"); self.send_error(502); return
        self.send_response(r.status)
        for k, v in r.getheaders():
            if k.lower() not in ("transfer-encoding", "content-length", "connection"): self.send_header(k, v)
        self.end_headers()
        raw = b""; buf = b""; dropped = 0
        sse = "text/event-stream" in (r.getheader("content-type") or "")
        try:
            while True:
                d = r.read1(4096)
                if not d: break
                raw += d
                if not sse:
                    self.wfile.write(d); self.wfile.flush(); continue
                buf += d
                *done, buf = buf.split(b"\n")
                keep = [l for l in done if l.strip() != b"data: null"]
                dropped += len(done) - len(keep)
                if keep: self.wfile.write(b"\n".join(keep) + b"\n"); self.wfile.flush()
        except Exception as e:
            log(f"  relay error: {e!r}")
        if buf: self.wfile.write(buf); self.wfile.flush()
        if dropped: log(f"  DROPPED {dropped} 'data: null' line(s) before forwarding")
        if os.environ.get("AR_DEBUG"): open(f"{D}/resp_{i}.txt", "wb").write(raw)
        lines = [l for l in raw.decode("utf-8", "replace").splitlines() if l.strip()]
        odd = []
        for l in lines:
            if not l.startswith("data:"):
                odd.append(("non-data-line", l)); continue
            p = l[5:].strip()
            if p == "[DONE]": continue
            try: v = json.loads(p)
            except Exception: odd.append(("bad-json", l)); continue
            if not isinstance(v, dict): odd.append(("not-object", l))
            elif v.get("error"): odd.append(("error", l))
            elif not v.get("choices") and "usage" not in v: odd.append(("no-choices", l))
        log(f"  resp: HTTP {r.status} type={r.getheader('content-type')} enc={r.getheader('content-encoding')} bytes={len(raw)} lines={len(lines)}")
        for why, l in odd[:10]: log(f"  ODD[{why}]: {l[:300]}")
        for l in lines[-3:]: log(f"  tail: {l[:300]}")
        if r.status != 200: log("  body: " + raw[:400].decode("utf-8", "replace"))
    do_GET = do_POST = _go
http.server.ThreadingHTTPServer(("127.0.0.1", 8787), H).serve_forever()
