"""S1 B2 thin real browser + JSON API over typed SchemaStore.

Local-only test host; user identities are host fixtures, not enterprise SSO.
All draft mutations from the human UI and external Agent tool call Store.mutate.
"""
from __future__ import annotations

import hmac
import json
import secrets
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlsplit

from schema_core import Actor, Rejected, SchemaStore, canon

LOGIN = """<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<title>OpenAILCAP B2 · 研究型设计器登录</title></head>
<body><main><h1>OpenAILCAP B2 原型</h1>
<form action="/editor/login" method="post"><label>研究密码
<input id="password" name="password" type="password" autocomplete="off" required></label>
<button id="login" type="submit">登录</button></form>
<p>仅本机隔离研究，未实现生产身份管理。</p>
</main></body></html>"""

EDITOR = """<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<title>B2 · DataModel / Form / View / Workflow 研究设计器</title>
<style nonce="__NONCE__">
body{font:16px system-ui,sans-serif;max-width:900px;margin:30px auto;color:#1b2533;background:#f2f5f9}
main{padding:26px;border:1px solid #dce2eb;background:#fff;border-radius:12px}
textarea{width:100%;box-sizing:border-box;font:14px monospace;min-height:235px}
input{padding:8px;width:260px}button{padding:8px 14px;cursor:pointer;margin:10px 8px 6px 0}
small{color:#5c6675}#message{font-weight:600;color:#224c85}
.meta{display:flex;gap:25px;padding:6px 0}pre{white-space:pre-wrap;overflow-wrap:break-word}
</style></head><body><main>
<h1>B2 · 应用模型与人工 / Agent 协同</h1>
<p><small>受控域 Schema + Manifest，全部变更经同一应用级 CAS；发布快照不可变。</small></p>
<div class="meta"><div>草稿版本 <strong id="revision">未加载</strong></div>
<div>发布版本 <strong id="published-version">未发布</strong></div></div>
<label for="resource-id">资源 ID</label>
<input id="resource-id" value="form.contracts" autocomplete="off">
<button id="select" type="button">选择资源</button>
<button id="reload" type="button">重新加载</button>
<p id="resources"></p>
<label for="definition">JSON 定义（model / form / view / workflow）</label>
<textarea id="definition" spellcheck="false"></textarea>
<div><button id="save">保存当前资源</button><button id="publish">发布当前草稿</button></div>
<p id="message" role="status" aria-live="polite">加载中…</p>
<hr><h2>运行态预览（当前发布快照）</h2>
<button id="view">读取合同列表</button>
<pre id="runtime-output">—</pre>
</main><script nonce="__NONCE__">
"use strict";
const csrf=__CSRF__;
const base="/v2/apps/app-a";
let snapshot=null;
const el=id=>document.getElementById(id);
const show=t=>{el("message").textContent=t;};
function selectedId(){return el("resource-id").value.trim();}
function renderEditor(){
  if(!snapshot) return;
  const rid=selectedId(), entry=snapshot.resources[rid];
  el("definition").value=entry?JSON.stringify(entry.definition,null,2):"";
  el("revision").textContent=String(snapshot.appRevision);
  el("published-version").textContent=snapshot.publishedVersion===null?"未发布":String(snapshot.publishedVersion);
  el("resources").textContent="已注册: "+Object.keys(snapshot.resources).sort().join("、");
}
async function load(){
  const r=await fetch(base+"/draft",{credentials:"same-origin"});
  const data=await r.json();
  if(!r.ok){show("读取失败："+data.error);return;}
  snapshot=data;renderEditor();show("已加载草稿 revision="+data.appRevision);
}
function cid(){return "web_"+crypto.randomUUID().replaceAll("-","");}
async function post(path,body){
  const response=await fetch(base+path,{
    method:"POST",credentials:"same-origin",
    headers:{"Content-Type":"application/json","X-CSRF-Token":csrf},
    body:JSON.stringify(body)
  });
  return {status:response.status,result:await response.json()};
}
el("select").addEventListener("click",renderEditor);
el("reload").addEventListener("click",()=>load().catch(()=>show("读取失败")));
el("save").addEventListener("click",async()=>{
  if(!snapshot) return;
  const rid=selectedId();
  let definition;
  try {definition=JSON.parse(el("definition").value);}
  catch {show("JSON 语法错误");return;}
  const existing=snapshot.resources[rid]||null;
  const body={changeId:cid(),resourceId:rid,
    expectedAppRevision:snapshot.appRevision,
    expectedRevision:existing?existing.revision:null,
    baseContentHash:existing?existing.contentHash:null,definition};
  try{
    const {status,result}=await post("/commands",body);
    if(status===409){show("409 "+result.error+"，请手动重新加载最新草稿");return;}
    if(status!==200){show(status+" "+result.error);return;}
    await load();show("保存成功：appRevision="+result.appRevision);
  }catch{show("网络故障：写入结果未知，禁止用新 changeId 自动重试");}
});
el("publish").addEventListener("click",async()=>{
  if(!snapshot) return;
  try{
    const {status,result}=await post("/publish",{
      changeId:cid(),expectedAppRevision:snapshot.appRevision,
      manifestHash:snapshot.manifestHash});
    if(status!==200){show(status+" "+result.error);return;}
    await load();show("发布成功：version="+result.version);
  }catch{show("网络故障：发布结果未知");}
});
el("view").addEventListener("click",async()=>{
  try{
    const r=await fetch(base+"/runtime/views/view.contracts",{credentials:"same-origin"});
    const value=await r.json();
    el("runtime-output").textContent=JSON.stringify(value,null,2);
  }catch{el("runtime-output").textContent="读取失败";}
});
load().catch(()=>show("读取失败"));
</script></body></html>"""


def handler_for(store: SchemaStore, tokens: dict, sessions: dict,
                web_actor: Actor, login_password: str):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass  # don't write bearer, cookie or test password to CI

        def _write(self, status, content, content_type="application/json; charset=utf-8",
                   *, csp=None, sid=None):
            data = content.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")
            if csp:
                self.send_header("Content-Security-Policy", csp)
            if sid:
                self.send_header("Set-Cookie",
                                 "sid="+sid+"; Path=/; SameSite=Strict; HttpOnly")
            self.end_headers()
            self.wfile.write(data)

        def _json(self, status, obj):
            self._write(status, canon(obj))

        def _session(self):
            pieces = self.headers.get("Cookie", "").split(";")
            cookies = dict(piece.strip().split("=", 1) for piece in pieces
                           if "=" in piece)
            return sessions.get(cookies.get("sid"))

        def _actor(self, *, write=False):
            auth = self.headers.get("Authorization", "")
            if auth.startswith("Bearer "):
                actor = tokens.get(auth[7:])
                if actor is None or not actor.active:
                    raise Rejected(401, "AUTH_REQUIRED")
                return actor
            session = self._session()
            if not session:
                raise Rejected(401, "AUTH_REQUIRED")
            actor, csrf = session
            if write and not hmac.compare_digest(
                self.headers.get("X-CSRF-Token", ""), csrf
            ):
                raise Rejected(403, "CSRF_REQUIRED")
            if not actor.active:
                raise Rejected(401, "AUTH_REQUIRED")
            return actor

        def _body(self):
            if self.headers.get("Content-Type", "").split(";")[0].strip() != "application/json":
                raise Rejected(415, "JSON_REQUIRED")
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                raise Rejected(422, "INVALID_JSON")
            if not 0 < length <= 32768:
                raise Rejected(422, "INVALID_JSON")
            try:
                return json.loads(self.rfile.read(length))
            except (UnicodeDecodeError, json.JSONDecodeError):
                raise Rejected(422, "INVALID_JSON")

        def _parts(self):
            return [unquote(s) for s in urlsplit(self.path).path.split("/") if s]

        def do_GET(self):
            try:
                path = urlsplit(self.path).path
                if path == "/health":
                    self._json(200, {"scope": "S1_B2_RESEARCH_ONLY", "status": "OK"})
                    return
                if path == "/editor/login":
                    self._write(200, LOGIN, "text/html; charset=utf-8",
                                csp="default-src 'none'; form-action 'self'")
                    return
                if path == "/editor/app-a":
                    session = self._session()
                    if not session or session[0].role if False else False:
                        pass
                    if not session or session[0].name != web_actor.name or not session[0].active:
                        self.send_response(303)
                        self.send_header("Location", "/editor/login")
                        self.send_header("Content-Length", "0")
                        self.end_headers()
                        return
                    nonce = secrets.token_urlsafe(18)
                    html = EDITOR.replace("__NONCE__", nonce).replace(
                        "__CSRF__", json.dumps(session[1]))
                    self._write(200, html, "text/html; charset=utf-8",
                                csp="default-src 'none'; "
                                "script-src 'nonce-"+nonce+"'; "
                                "style-src 'nonce-"+nonce+"'; "
                                "connect-src 'self'; form-action 'self'; "
                                "frame-ancestors 'none'; base-uri 'none'")
                    return
                parts = self._parts()
                if parts[:2] != ["v2", "apps"] or len(parts) < 4:
                    raise Rejected(404, "ROUTE_NOT_FOUND")
                app = parts[2]
                actor = self._actor()
                if len(parts) == 4 and parts[3] == "draft":
                    self._json(200, store.draft(actor, app))
                elif len(parts) == 5 and parts[3:] == ["releases", "current"]:
                    self._json(200, store.release(actor, app))
                elif len(parts) == 6 and parts[3:5] == ["runtime", "views"]:
                    self._json(200, store.view_rows(actor, app, parts[5]))
                else:
                    raise Rejected(404, "ROUTE_NOT_FOUND")
            except Rejected as e:
                self._json(e.status, {"error": e.code})

        def do_POST(self):
            try:
                path = urlsplit(self.path).path
                if path == "/editor/login":
                    try:
                        length = int(self.headers.get("Content-Length", "0"))
                    except ValueError:
                        length = 0
                    if not 0 < length < 2048:
                        raise Rejected(422, "INVALID_LOGIN")
                    data = parse_qs(self.rfile.read(length).decode("utf-8", "strict"))
                    supplied = data.get("password", [""])[0]
                    if not hmac.compare_digest(supplied.encode(), login_password.encode()):
                        raise Rejected(403, "LOGIN_FAILED")
                    sid, csrf = secrets.token_urlsafe(30), secrets.token_urlsafe(30)
                    sessions[sid] = (web_actor, csrf)
                    self.send_response(303)
                    self.send_header("Location", "/editor/app-a")
                    self.send_header("Set-Cookie",
                                     "sid="+sid+"; Path=/; HttpOnly; SameSite=Strict")
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return
                parts = self._parts()
                if parts[:2] != ["v2", "apps"] or len(parts) < 4:
                    raise Rejected(404, "ROUTE_NOT_FOUND")
                actor = self._actor(write=True)
                app = parts[2]
                body = self._body()
                if len(parts) == 4 and parts[3] == "commands":
                    result = store.mutate(actor, app, body)
                elif len(parts) == 4 and parts[3] == "publish":
                    result = store.publish(actor, app, body)
                elif len(parts) == 4 and parts[3] == "rollback":
                    result = store.rollback(actor, app, body)
                elif len(parts) == 7 and parts[3:5] == ["runtime", "forms"] and parts[6] == "records":
                    result = store.submit_form(actor, app, parts[5], body)
                elif (len(parts) == 9 and parts[3:5] == ["runtime", "workflows"] and
                      parts[6] == "records" and parts[8] == "advance"):
                    if not isinstance(body, dict) or set(body) != {"action", "expectedVersion"}:
                        raise Rejected(422, "INVALID_ACTION")
                    result = store.advance(actor, app, parts[5], parts[7],
                                           body["action"], body["expectedVersion"])
                else:
                    raise Rejected(404, "ROUTE_NOT_FOUND")
                self._json(200, result)
            except Rejected as e:
                self._json(e.status, {"error": e.code})
    return Handler


def serve_local(store, tokens, sessions, human, password, port=0):
    if not isinstance(password, str) or len(password) < 24:
        raise ValueError("Ephemeral test password required")
    return ThreadingHTTPServer(
        ("127.0.0.1", port),
        handler_for(store, tokens, sessions, human, password)
    )
