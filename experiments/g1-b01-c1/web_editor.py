"""G1-B01 B1: real, human-operable browser UI over existing C1 domain command API.

LAB ONLY. No internet bind, no production authentication, no plugin sandbox.
All edits call C1's Store.apply via the same /v1/.../changes HTTP endpoint
used by Agent and plugin, not a new persistence path.
"""
from __future__ import annotations

import hmac
import json
import secrets
from http.server import ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

from service import GateError, make_handler

LOGIN_HTML = """<!doctype html>
<html lang="zh-CN">
<head><meta charset="utf-8"><title>B1 研究型人工设计器 - 登录</title></head>
<body><main><h1>B1 人工设计器（研究环境）</h1>
<form action="/editor/login" method="post"><label for="password">实验账号密码</label>
<input id="password" name="password" type="password" required autocomplete="off">
<button id="login" type="submit">登录</button></form>
<p>仅本机实验，不得公开部署或用于生产环境。</p></main></body></html>"""

EDITOR_HTML = """<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><title>B1 研究型人工设计器</title>
<style nonce="__NONCE__">
body{font-family:system-ui,"Microsoft YaHei",sans-serif;background:#f7f9fb;color:#1f2937;margin:2rem auto;max-width:720px}
main{background:white;border:1px solid #dce2ea;padding:24px;border-radius:10px}
label{display:block;margin:12px 0 4px}input,select,button{font:inherit;padding:8px}
input{width:90%}button{cursor:pointer;margin:12px 10px 0 0}
#message{min-height:28px;font-weight:600}code{overflow-wrap:anywhere}
</style></head><body><main>
<h1>OpenAILCAP B1 · 人工设计器研究原型</h1>
<p>同一资源由 Web、Agent 工具和插件调用者共享受治理写入接口。</p>
<div>当前版本 <strong id="revision">未加载</strong>；
字段标签 <strong id="label-current">未加载</strong>；
状态 <strong id="status-current">未加载</strong></div>
<form id="edit-form">
<label for="field">修改字段</label><select id="field" name="field">
<option value="label">字段标签</option><option value="status">状态</option></select>
<label for="value">新值</label><input name="value" id="value" type="text" required maxlength="120">
<button type="submit" id="save">保存变更</button><button type="button" id="reload">重新加载版本</button>
</form>
<p id="message" role="status" aria-live="polite">读取资源中…</p>
<p><small>独立旧标签页不会自动刷新，冲突时明确 409，不会静默覆盖。</small></p>
</main><script nonce="__NONCE__">
"use strict";
const csrf = __CSRF_JSON__;
const endpoint = "/v1/apps/app-a/resources/field.title";
const changeEndpoint = "/v1/apps/app-a/changes";
let snapshot = null;
const message = document.getElementById("message");
function show(text){ message.textContent = text; }
async function refresh() {
  const response = await fetch(endpoint, {credentials: "same-origin"});
  const payload = await response.json();
  if (!response.ok) {show("无法读取: " + payload.error);return;}
  snapshot = payload;
  document.getElementById("revision").textContent = String(payload.revision);
  document.getElementById("label-current").textContent = payload.content.label;
  document.getElementById("status-current").textContent = payload.content.status;
  show("已读取 revision=" + payload.revision);
}
document.getElementById("reload").addEventListener("click", () => {
  refresh().catch(() => show("读取失败"));
});
document.getElementById("edit-form").addEventListener("submit", async event => {
  event.preventDefault();
  if (!snapshot) {show("没有可提交的版本");return;}
  const field = document.getElementById("field").value;
  const value = document.getElementById("value").value;
  const payload = {
    changeId: "web_" + crypto.randomUUID().replaceAll("-", ""),
    resourceId: snapshot.resourceId, expectedRevision: snapshot.revision,
    baseContentHash: snapshot.contentHash,
    operations: [{op:"replace",path:"/" + field,value:value}]
  };
  const response = await fetch(changeEndpoint, {
    method:"POST",credentials:"same-origin",
    headers: {"Content-Type":"application/json","X-CSRF-Token":csrf},
    body:JSON.stringify(payload)
  });
  const result = await response.json();
  if (response.status === 409) {
    show("409 " + result.error + "：内容已变化，请手动重新加载后编辑");
    return;
  }
  if (!response.ok) {show(String(response.status) + " " + result.error);return;}
  await refresh();
  show("保存成功：revision=" + result.revision);
});
refresh().catch(() => show("读取失败"));
</script></body></html>"""


def web_handler(store, bearer_tokens, browser_sessions, human, password):
    """Compose C1's exact HTTP API with HTML; no separate write implementation."""
    parent = make_handler(store, bearer_tokens, browser_sessions)

    class Handler(parent):
        def _html(self, status, html, *, session_id=None, nonce=None):
            encoded = html.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("Referrer-Policy", "no-referrer")
            if nonce:
                self.send_header(
                    "Content-Security-Policy",
                    "default-src 'none'; script-src 'nonce-" + nonce +
                    "'; style-src 'nonce-" + nonce +
                    "'; connect-src 'self'; form-action 'self'; frame-ancestors 'none'; "
                    "base-uri 'none'; object-src 'none'")
            else:
                self.send_header(
                    "Content-Security-Policy",
                    "default-src 'none'; form-action 'self'; frame-ancestors 'none'")
            if session_id:
                self.send_header("Set-Cookie",
                                 "sid=" + session_id +
                                 "; HttpOnly; SameSite=Strict; Path=/")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

        def _login_redirect(self, session_id):
            self.send_response(303)
            self.send_header("Location", "/editor/app-a/field.title")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Set-Cookie",
                             "sid=" + session_id + "; HttpOnly; SameSite=Strict; Path=/")
            self.send_header("Content-Length", "0")
            self.end_headers()

        def do_GET(self):
            route = urlsplit(self.path).path
            if route == "/editor/login":
                self._html(200, LOGIN_HTML)
                return
            if route == "/editor/app-a/field.title":
                try:
                    principal = self._principal(write=False)
                    store.authorize(principal, "app-a", "field.title")
                    self._principal(write=False)  # session is checked by C1 core
                    if principal.role != "browser":
                        raise GateError(403, "BROWSER_SESSION_REQUIRED")
                    sid = self.headers.get("Cookie", "").split("sid=")[-1].split(";")[0]
                    session = browser_sessions.get(sid)
                    if not session or session[0] != principal:
                        raise GateError(401, "AUTH_REQUIRED")
                    nonce = secrets.token_urlsafe(18)
                    html = (EDITOR_HTML.replace("__NONCE__", nonce)
                            .replace("__CSRF_JSON__", json.dumps(session[1])))
                    self._html(200, html, nonce=nonce)
                except GateError:
                    self.send_response(303)
                    self.send_header("Location", "/editor/login")
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                return
            super().do_GET()

        def do_POST(self):
            if urlsplit(self.path).path == "/editor/login":
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                except ValueError:
                    length = 0
                if not (0 < length < 4096):
                    self._html(422, "登录请求非法")
                    return
                body = parse_qs(self.rfile.read(length).decode("utf-8", "strict"))
                candidate = body.get("password", [""])[0]
                if not hmac.compare_digest(candidate.encode("utf-8"),
                                           password.encode("utf-8")):
                    self._html(403, "实验密码无效")
                    return
                sid, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
                browser_sessions[sid] = (human, csrf)
                self._login_redirect(sid)
                return
            super().do_POST()

    return Handler


def serve_b1(store, bearer_tokens, browser_sessions, human, password, port=0):
    """One localhost-only process for all B1 browser/Agent/plugin HTTP clients."""
    if not password or len(password) < 24:
        raise ValueError("Use an ephemeral high-entropy test login password")
    return ThreadingHTTPServer(
        ("127.0.0.1", port),
        web_handler(store, bearer_tokens, browser_sessions, human, password)
    )
