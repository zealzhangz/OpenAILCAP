/* ============ 静态文件服务器（原型为纯前端 SPA，数据存 localStorage） ============ */
import http from 'http';
import { readFile } from 'fs/promises';
import { extname, join } from 'path';
import { fileURLToPath } from 'url';

const ROOT = join(fileURLToPath(import.meta.url), '..', 'public');
const MIME = { '.html':'text/html', '.css':'text/css', '.js':'text/javascript', '.json':'application/json', '.png':'image/png', '.svg':'image/svg+xml', '.ico':'image/x-icon' };
const PORT = process.env.PORT || 3000;

http.createServer(async (req, res) => {
  let p = req.url === '/' ? '/index.html' : req.url.split('?')[0];
  try {
    const file = await readFile(join(ROOT, p));
    res.writeHead(200, { 'Content-Type': MIME[extname(p)] || 'application/octet-stream' });
    res.end(file);
  } catch {
    res.writeHead(404, { 'Content-Type': 'text/plain; charset=utf-8' });
    res.end('Not Found');
  }
}).listen(PORT, () => {
  console.log(`\n🚀 OpenAILCAP MVP 2.0 交互原型已启动`);
  console.log(`📍 访问: http://localhost:${PORT}`);
  console.log(`📦 17 个功能页面 · 全前端 SPA · 数据存 localStorage（右上角可重置于控制台: Store.reset()）\n`);
});
