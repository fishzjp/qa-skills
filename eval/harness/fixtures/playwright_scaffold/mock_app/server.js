// Mock 被测应用：图券商城控制台「项目管理」（E2E 执行环境的固定被测系统）
// 与 e2e-markmap-to-spec 任务「材料 3 页面结构说明」严格一致；无依赖，纯 Node http。
const http = require('http');
const crypto = require('crypto');

const PORT = parseInt(process.env.E2E_PORT || '8931', 10);

const state = { projects: [], seq: 1 };
['示例项目-Alpha', '示例项目-Beta'].forEach((n) => {
  state.projects.push({ id: state.seq++, name: n });
});

const PAGE = `<!DOCTYPE html>
<html lang="zh"><head><meta charset="utf-8"><title>控制台</title>
<style>body{font-family:sans-serif;margin:24px}.card{border:1px solid #ccc;border-radius:8px;padding:12px;margin:8px 0;display:flex;justify-content:space-between;align-items:center}.menu{position:relative}.menu-list{display:none;position:absolute;right:0;background:#fff;border:1px solid #ccc;border-radius:4px;min-width:80px;z-index:9}.menu-list button{display:block;width:100%;border:0;background:none;padding:8px;cursor:pointer}dialog{border:1px solid #ccc;border-radius:8px;padding:20px}input{padding:6px;margin:6px 0}</style>
</head><body>
<div id="app"></div>
<script>
const PAGE_NAME = location.pathname === '/console/projects' ? 'projects' : 'login';
async function api(method, url, body) {
  const r = await fetch(url, {method, headers: body ? {'Content-Type':'application/json'} : undefined, body: body ? JSON.stringify(body) : undefined});
  const data = await r.json().catch(() => ({}));
  return {status: r.status, data};
}
function renderProjects() {
  const q = (document.getElementById('search') && document.getElementById('search').value || '').trim();
  const esc = (s) => String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const list = __PROJECTS__.filter(p => !q || p.name.includes(q));
  document.getElementById('app').innerHTML = \`
    <h1>控制台 → 项目</h1>
    <input id="search" placeholder="搜索项目" value="\${esc(q)}">
    <button id="create-btn">新建项目</button>
    <div id="cards">\${list.map(p => \`
      <div class="project-card" data-id="\${p.id}">
        <span class="project-name">\${esc(p.name)}</span>
        <span class="menu"><button class="more-btn" aria-haspopup="menu">更多</button>
          <span class="menu-list" role="menu"><button class="delete-btn" role="menuitem">删除</button></span></span>
      </div>\`).join('')}
    </div>
    <dialog id="create-dialog"><p>新建项目</p>
      <input id="project-name" placeholder="请输入项目名称"><br>
      <button id="confirm-create">确定</button></dialog>
    <dialog id="delete-dialog"><p>确认删除该项目？</p><button id="confirm-delete">删除</button></dialog>\`;
  document.getElementById('search').addEventListener('keydown', e => { if (e.key === 'Enter') renderProjects(); });
  document.getElementById('create-btn').onclick = () => document.getElementById('create-dialog').showModal();
  document.querySelectorAll('.more-btn').forEach(b => b.onclick = () => {
    const listEl = b.nextElementSibling; const open = listEl.style.display === 'block';
    document.querySelectorAll('.menu-list').forEach(x => x.style.display = 'none');
    listEl.style.display = open ? 'none' : 'block';
  });
  document.getElementById('confirm-create').onclick = async () => {
    const name = document.getElementById('project-name').value;
    const {status, data} = await api('POST', '/api/projects', {name});
    if (status === 201) { document.getElementById('create-dialog').close(); await refresh(); }
    else { alert((data && data.message) || '创建失败'); }
  };
  document.querySelectorAll('.delete-btn').forEach(b => b.onclick = () => {
    window.__deleting = b.closest('.project-card').dataset.id;
    document.getElementById('delete-dialog').showModal();
  });
  document.getElementById('confirm-delete').onclick = async () => {
    await api('DELETE', '/api/projects/' + window.__deleting);
    document.getElementById('delete-dialog').close(); await refresh();
  };
}
async function refresh() {
  const {data} = await api('GET', '/api/projects');
  window.__PROJECTS__ = data.projects; renderProjects();
}
if (PAGE_NAME === 'login') {
  document.getElementById('app').innerHTML = \`
    <h1>登录</h1>
    <input id="username" placeholder="请输入用户名"><br>
    <input id="password" type="password" placeholder="请输入密码"><br>
    <button id="login-btn">登录</button><div id="err"></div>\`;
  document.getElementById('login-btn').onclick = async () => {
    const r = await api('POST', '/login', {username: document.getElementById('username').value, password: document.getElementById('password').value});
    if (r.status === 200) location.href = '/console';
    else document.getElementById('err').textContent = '用户名或密码错误';
  };
} else if (PAGE_NAME === 'projects') {
  window.__PROJECTS__ = __PROJECTS_BOOT__; renderProjects();
  setTimeout(refresh, 50);  // 模拟真实 SPA：数据在 load 之后异步加载
} else {
  document.getElementById('app').innerHTML = '<h1>控制台</h1><a href="/console/projects">项目管理</a>';
}
</script></body></html>`;

const server = http.createServer((req, res) => {
  const url = new URL(req.url, `http://127.0.0.1:${PORT}`);
  const send = (code, body, type = 'application/json') => {
    res.writeHead(code, {'Content-Type': type}); res.end(typeof body === 'string' ? body : JSON.stringify(body));
  };
  if (req.method === 'GET' && (url.pathname === '/login' || url.pathname === '/console' || url.pathname === '/console/projects')) {
    const boot = JSON.stringify(state.projects).replace(/</g, '\\u003c');  // 防 </script> 逃逸
    const html = PAGE.replace('__PROJECTS_BOOT__', boot)
      .replace(/__PROJECTS__/g, 'window.__PROJECTS__');
    return send(200, html, 'text/html; charset=utf-8');
  }
  if (url.pathname === '/api/projects' && req.method === 'GET') {
    return send(200, {projects: state.projects});
  }
  if (url.pathname === '/api/projects' && req.method === 'POST') {
    let body = ''; req.on('data', (c) => (body += c)); req.on('end', () => {
      let parsed;
      try { parsed = JSON.parse(body || '{}'); } catch (e) { return send(400, {code: 'BAD_JSON', message: '请求体不是合法 JSON'}); }
      const {name} = parsed;
      if (!name || !name.trim()) return send(400, {code: 'NAME_REQUIRED', message: '项目名称不能为空'});
      if (state.projects.some((p) => p.name === name)) return send(400, {code: 'NAME_DUPLICATED', message: '名称已存在'});
      const p = {id: state.seq++, name};
      state.projects.unshift(p);
      return send(201, p);
    });
    return;
  }
  const del = url.pathname.match(/^\/api\/projects\/(\d+)$/);
  if (del && req.method === 'DELETE') {
    state.projects = state.projects.filter((p) => p.id !== Number(del[1]));
    return send(200, {deleted: true});
  }
  if (url.pathname === '/login' && req.method === 'POST') {
    let body = ''; req.on('data', (c) => (body += c)); req.on('end', () => {
      let parsed;
      try { parsed = JSON.parse(body || '{}'); } catch (e) { return send(400, {code: 'BAD_JSON', message: '请求体不是合法 JSON'}); }
      const {username, password} = parsed;
      if (username === 'admin' && password === 'pass') return send(200, {ok: true, token: 't-' + crypto.randomUUID()});
      return send(401, {message: '用户名或密码错误'});
    });
    return;
  }
  send(404, {message: 'not found'});
});

server.listen(PORT, '127.0.0.1', () => console.log(`mock app on ${PORT}`));
