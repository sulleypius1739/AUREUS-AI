const http = require('http');
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const url = require('url');

const PORT = Number(process.env.PORT || 8000);
const ROOT = __dirname;
const AUTH_DIR = path.join(ROOT, 'data', 'auth');
const USERS_FILE = path.join(AUTH_DIR, 'users.json');
const AUDIT_FILE = path.join(AUTH_DIR, 'audit.json');
const SESSION_TTL_MS = 1000 * 60 * 60 * 12;
const IS_HTTPS = String(process.env.AUREUS_HTTPS || '').toLowerCase() === 'true';

function ensureStore() {
  fs.mkdirSync(AUTH_DIR, { recursive: true });
  if (!fs.existsSync(USERS_FILE)) fs.writeFileSync(USERS_FILE, '[]');
  if (!fs.existsSync(AUDIT_FILE)) fs.writeFileSync(AUDIT_FILE, '[]');
  const users = readJson(USERS_FILE);
  if (users.length === 0) {
    const email = (process.env.ADMIN_EMAIL || 'president@aureus.local').toLowerCase();
    const password = process.env.ADMIN_PASSWORD || randomPassword(16);
    const admin = createUserRecord({ name: 'AUREUS President', email, password, role: 'PRESIDENT' });
    writeJson(USERS_FILE, [admin]);
    appendAudit('SYSTEM', 'INITIAL_ADMIN_CREATED', email);
    if (!process.env.ADMIN_PASSWORD) {
      console.log('\n====================================================');
      console.log('AUREUS FIRST-RUN PRESIDENT ACCOUNT');
      console.log(`Email:    ${email}`);
      console.log(`Password: ${password}`);
      console.log('Change this password after your first login.');
      console.log('====================================================\n');
    }
  }
}

function readJson(file) { try { return JSON.parse(fs.readFileSync(file, 'utf8')); } catch { return []; } }
function writeJson(file, data) { fs.writeFileSync(file, JSON.stringify(data, null, 2)); }
function randomPassword(length) { return crypto.randomBytes(Math.ceil(length * 0.75)).toString('base64url').slice(0, length); }
function hashPassword(password, salt = crypto.randomBytes(16).toString('hex')) {
  const derived = crypto.scryptSync(password, salt, 64).toString('hex');
  return { salt, hash: derived };
}
function verifyPassword(password, user) {
  const derived = crypto.scryptSync(password, user.salt, 64).toString('hex');
  return crypto.timingSafeEqual(Buffer.from(derived, 'hex'), Buffer.from(user.hash, 'hex'));
}
function createUserRecord({ name, email, password, role = 'USER' }) {
  const { salt, hash } = hashPassword(password);
  return { id: crypto.randomUUID(), name, email: email.toLowerCase(), role, active: true, salt, hash, createdAt: new Date().toISOString() };
}
function publicUser(user) { return { id: user.id, name: user.name, email: user.email, role: user.role, active: user.active, createdAt: user.createdAt }; }
function appendAudit(actor, action, target='') {
  const audit = readJson(AUDIT_FILE);
  audit.unshift({ id: crypto.randomUUID(), actor, action, target, time: new Date().toISOString() });
  writeJson(AUDIT_FILE, audit.slice(0, 250));
}

const sessions = new Map();
function parseCookies(req) {
  const header = req.headers.cookie || '';
  return Object.fromEntries(header.split(';').filter(Boolean).map(part => {
    const idx = part.indexOf('=');
    return [part.slice(0, idx).trim(), decodeURIComponent(part.slice(idx + 1).trim())];
  }));
}
function setSession(res, user) {
  const sid = crypto.randomBytes(32).toString('hex');
  sessions.set(sid, { userId: user.id, expires: Date.now() + SESSION_TTL_MS });
  const secure = IS_HTTPS ? '; Secure' : '';
  res.setHeader('Set-Cookie', `aureus_session=${sid}; Path=/; HttpOnly; SameSite=Lax; Max-Age=${Math.floor(SESSION_TTL_MS/1000)}${secure}`);
}
function clearSession(res, sid) {
  sessions.delete(sid);
  res.setHeader('Set-Cookie', 'aureus_session=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0');
}
function currentUser(req) {
  const sid = parseCookies(req).aureus_session;
  const session = sid && sessions.get(sid);
  if (!session || session.expires < Date.now()) return null;
  const user = readJson(USERS_FILE).find(u => u.id === session.userId && u.active);
  return user || null;
}

async function body(req) {
  return await new Promise((resolve, reject) => {
    let data = ''; req.on('data', c => { data += c; if (data.length > 1_000_000) req.destroy(); });
    req.on('end', () => { try { resolve(data ? JSON.parse(data) : {}); } catch (e) { reject(e); } });
    req.on('error', reject);
  });
}
function json(res, status, payload) {
  res.writeHead(status, { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store' });
  res.end(JSON.stringify(payload));
}
function authRequired(req, res) {
  const user = currentUser(req);
  if (!user) { json(res, 401, { message: 'Authentication required.' }); return null; }
  return user;
}
function presidentRequired(req, res) {
  const user = authRequired(req, res);
  if (!user) return null;
  if (user.role !== 'PRESIDENT') { json(res, 403, { message: 'President access required.' }); return null; }
  return user;
}
function validatePassword(password) {
  return typeof password === 'string' && password.length >= 10;
}

async function api(req, res, pathname) {
  try {
    if (req.method === 'GET' && pathname === '/api/auth/me') {
      const user = currentUser(req); return json(res, 200, { user: user ? publicUser(user) : null });
    }
    if (req.method === 'POST' && pathname === '/api/auth/login') {
      const { email, password } = await body(req);
      const users = readJson(USERS_FILE);
      const user = users.find(u => u.email === String(email || '').toLowerCase());
      if (!user || !user.active || !verifyPassword(String(password || ''), user)) return json(res, 401, { message: 'Invalid email or password.' });
      setSession(res, user); appendAudit(user.email, 'LOGIN'); return json(res, 200, { user: publicUser(user) });
    }
    if (req.method === 'POST' && pathname === '/api/auth/logout') {
      const actor = currentUser(req); const sid = parseCookies(req).aureus_session; if (actor) appendAudit(actor.email, 'LOGOUT'); clearSession(res, sid); return json(res, 200, { ok: true });
    }
    if (req.method === 'POST' && pathname === '/api/auth/register') {
      const { name, email, password } = await body(req);
      if (!name || !email || !validatePassword(password)) return json(res, 400, { message: 'Name, valid email and a password of at least 10 characters are required.' });
      const users = readJson(USERS_FILE); const normalized = String(email).toLowerCase();
      if (users.some(u => u.email === normalized)) return json(res, 409, { message: 'An account with that email already exists.' });
      const user = createUserRecord({ name: String(name).trim(), email: normalized, password, role: 'USER' });
      users.push(user); writeJson(USERS_FILE, users); appendAudit(normalized, 'REGISTER'); return json(res, 201, { email: normalized });
    }
    if (req.method === 'GET' && pathname === '/api/admin/users') {
      const actor = presidentRequired(req, res); if (!actor) return; return json(res, 200, { users: readJson(USERS_FILE).map(publicUser) });
    }
    if (req.method === 'GET' && pathname === '/api/admin/audit') {
      const actor = presidentRequired(req, res); if (!actor) return; return json(res, 200, { audit: readJson(AUDIT_FILE).slice(0, 80).map(a => ({ actor: a.actor, action: a.action, target: a.target, time: new Date(a.time).toLocaleString() })) });
    }
    if (req.method === 'POST' && pathname === '/api/admin/users') {
      const actor = presidentRequired(req, res); if (!actor) return;
      const { name, email, password, role } = await body(req); if (!name || !email || !validatePassword(password)) return json(res, 400, { message: 'Name, email and 10+ character password required.' });
      const allowed = new Set(['USER', 'ANALYST', 'ADMIN']); const safeRole = allowed.has(role) ? role : 'USER'; const users = readJson(USERS_FILE); const normalized = String(email).toLowerCase();
      if (users.some(u => u.email === normalized)) return json(res, 409, { message: 'Email already exists.' });
      users.push(createUserRecord({ name: String(name).trim(), email: normalized, password, role: safeRole })); writeJson(USERS_FILE, users); appendAudit(actor.email, 'CREATE_USER', normalized); return json(res, 201, { ok: true });
    }
    const toggleMatch = pathname.match(/^\/api\/admin\/users\/([^/]+)\/toggle$/);
    if (req.method === 'POST' && toggleMatch) {
      const actor = presidentRequired(req, res); if (!actor) return; const id = toggleMatch[1]; const users = readJson(USERS_FILE); const user = users.find(u => u.id === id);
      if (!user) return json(res, 404, { message: 'User not found.' }); if (user.role === 'PRESIDENT') return json(res, 400, { message: 'The President account cannot be disabled.' });
      user.active = !user.active; writeJson(USERS_FILE, users); appendAudit(actor.email, user.active ? 'ENABLE_USER' : 'DISABLE_USER', user.email); return json(res, 200, { ok: true });
    }
    return json(res, 404, { message: 'Not found.' });
  } catch (err) {
    console.error(err); return json(res, 500, { message: 'Server error.' });
  }
}

function safePath(requestPath) {
  const decoded = decodeURIComponent(requestPath.split('?')[0]);
  const clean = path.normalize(decoded === '/' ? '/index.html' : decoded).replace(/^\.\.(\/|\\)/, '');
  const full = path.join(ROOT, clean);
  return full.startsWith(ROOT) ? full : path.join(ROOT, 'index.html');
}
function staticFile(req, res) {
  const file = safePath(req.url);
  fs.stat(file, (err, stat) => {
    if (err || !stat.isFile()) return json(res, 404, { message: 'Not found.' });
    const ext = path.extname(file).toLowerCase();
    const mime = { '.html':'text/html; charset=utf-8', '.js':'text/javascript; charset=utf-8', '.css':'text/css; charset=utf-8', '.json':'application/json; charset=utf-8', '.png':'image/png', '.jpg':'image/jpeg', '.svg':'image/svg+xml' }[ext] || 'application/octet-stream';
    res.writeHead(200, { 'Content-Type': mime, 'Cache-Control': ext === '.html' ? 'no-store' : 'public, max-age=300' });
    fs.createReadStream(file).pipe(res);
  });
}

ensureStore();
const server = http.createServer((req, res) => {
  const parsed = url.parse(req.url); const pathname = parsed.pathname;
  if (pathname.startsWith('/api/')) return api(req, res, pathname);
  if (req.method !== 'GET' && req.method !== 'HEAD') return json(res, 405, { message: 'Method not allowed.' });
  staticFile(req, res);
});
server.listen(PORT, () => {
  console.log(`AUREUS web server running at http://localhost:${PORT}`);
});
