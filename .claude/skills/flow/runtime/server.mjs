import http from "node:http";
import { createHash } from "node:crypto";
import { execFileSync } from "node:child_process";
import { existsSync, readFileSync, readdirSync, renameSync, statSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { STAGES, stageState, taskState } from "./viewer/model.js";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const DOCS = path.resolve(HERE, "..");
const VIEWER = path.join(HERE, "viewer");
const DEFAULT_PORT = 4317;
const LEGACY_EXT = new Set([".md", ".html"]);
const TYPES = {
  ".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".css": "text/css; charset=utf-8",
  ".json": "application/json; charset=utf-8", ".md": "text/markdown; charset=utf-8", ".xml": "application/xml; charset=utf-8",
  ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".gif": "image/gif", ".svg": "image/svg+xml",
  ".webp": "image/webp", ".txt": "text/plain; charset=utf-8",
};

function git(...args) {
  try {
    return execFileSync("git", args, { cwd: DOCS, stdio: ["ignore", "pipe", "ignore"] }).toString().trim();
  } catch {
    return "";
  }
}

const hash = (text) => createHash("sha1").update(text).digest("hex");
const readText = (file) => readFileSync(file, "utf8");
const readJson = (file) => JSON.parse(readText(file));
const isDir = (p) => existsSync(p) && statSync(p).isDirectory();

function inside(rel) {
  const abs = path.resolve(DOCS, rel);
  return abs === DOCS || abs.startsWith(DOCS + path.sep) ? abs : null;
}

function taskFiles(dir) {
  const t = path.join(dir, "tasks");
  return isDir(t) ? readdirSync(t).filter((f) => f.endsWith(".json")).sort() : [];
}

function domainDirs() {
  return readdirSync(DOCS).filter((n) => !n.startsWith(".") && existsSync(path.join(DOCS, n, "domain.json"))).sort();
}

function legacyFiles() {
  const out = [];
  const walk = (dir, depth) => {
    for (const name of readdirSync(dir).sort()) {
      if (name.startsWith(".")) continue;
      const abs = path.join(dir, name);
      const rel = path.relative(DOCS, abs);
      if (statSync(abs).isDirectory()) {
        if (depth === 0 && existsSync(path.join(abs, "domain.json"))) continue;
        if (depth < 4) walk(abs, depth + 1);
      } else if (LEGACY_EXT.has(path.extname(name))) out.push(rel.split(path.sep).join("/"));
    }
  };
  walk(DOCS, 0);
  return out;
}

function tree() {
  const domains = domainDirs().map((id) => {
    const dir = path.join(DOCS, id);
    const domain = readJson(path.join(dir, "domain.json"));
    const tasks = taskFiles(dir).map((f) => {
      const t = readJson(path.join(dir, "tasks", f));
      return {
        id: t.id, title: t.title, type: t.type || "", state: taskState(t),
        stages: STAGES.map(([k, title]) => ({ key: k, title, ...stageState(t, k) })),
      };
    });
    return { id, title: domain.title || id, tasks };
  });
  return {
    repo: path.basename(git("rev-parse", "--show-toplevel") || path.dirname(DOCS)),
    branch: git("branch", "--show-current") || git("rev-parse", "--short", "HEAD"),
    domains,
    legacy: legacyFiles(),
  };
}

function entry(file) {
  const text = readText(file);
  return { path: path.relative(DOCS, file).split(path.sep).join("/"), hash: hash(text), data: JSON.parse(text) };
}

function domainData(id) {
  const dir = path.join(DOCS, id);
  if (!/^[\w.-]+$/.test(id) || !existsSync(path.join(dir, "domain.json"))) return null;
  const screens = path.join(dir, "screens.json");
  return {
    id,
    domain: entry(path.join(dir, "domain.json")),
    screens: existsSync(screens) ? entry(screens) : null,
    tasks: taskFiles(dir).map((f) => entry(path.join(dir, "tasks", f))),
  };
}

function version() {
  const h = createHash("sha1");
  for (const id of domainDirs()) {
    const dir = path.join(DOCS, id);
    const files = ["domain.json", "screens.json", ...taskFiles(dir).map((f) => `tasks/${f}`)];
    for (const f of files) {
      const p = path.join(dir, f);
      if (existsSync(p)) h.update(`${id}/${f}:${statSync(p).mtimeMs};`);
    }
  }
  return h.digest("hex");
}

function writable(rel) {
  const parts = rel.split("/");
  if (parts.length < 2 || !existsSync(path.join(DOCS, parts[0], "domain.json"))) return null;
  const ok = (parts.length === 2 && ["domain.json", "screens.json"].includes(parts[1]))
    || (parts.length === 3 && parts[1] === "tasks" && /^[\w.-]+\.json$/.test(parts[2]));
  const abs = ok ? inside(rel) : null;
  return abs && existsSync(abs) ? abs : null;
}

function save(body) {
  const results = [];
  const files = body.files || [];
  for (const f of files) {
    const abs = writable(f.path || "");
    if (!abs) return [400, { error: `쓸 수 없는 경로: ${f.path}` }];
    const now = hash(readText(abs));
    if (now !== f.hash) return [409, { error: "conflict", path: f.path }];
  }
  for (const f of files) {
    const abs = writable(f.path);
    const text = JSON.stringify(f.data, null, 2) + "\n";
    const tmp = `${abs}.${process.pid}.tmp`;
    writeFileSync(tmp, text);
    renameSync(tmp, abs);
    results.push({ path: f.path, hash: hash(text) });
  }
  return [200, { saved: results }];
}

function send(res, code, body, type) {
  const data = typeof body === "string" || Buffer.isBuffer(body) ? body : JSON.stringify(body);
  res.writeHead(code, { "content-type": type || "application/json; charset=utf-8", "cache-control": "no-store" });
  res.end(data);
}

function sendFile(res, abs) {
  if (!abs || !existsSync(abs) || statSync(abs).isDirectory()) return send(res, 404, { error: "없는 파일" });
  send(res, 200, readFileSync(abs), TYPES[path.extname(abs).toLowerCase()] || "application/octet-stream");
}

function readBody(req) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    req.on("data", (c) => chunks.push(c));
    req.on("end", () => {
      try { resolve(JSON.parse(Buffer.concat(chunks).toString("utf8") || "{}")); } catch (e) { reject(e); }
    });
    req.on("error", reject);
  });
}

async function handle(req, res) {
  const url = new URL(req.url, "http://localhost");
  const p = decodeURIComponent(url.pathname);
  try {
    if (p === "/api/ping") return send(res, 200, { docs: DOCS });
    if (p === "/api/tree") return send(res, 200, tree());
    if (p === "/api/version") return send(res, 200, { version: version() });
    if (p.startsWith("/api/domain/")) {
      const d = domainData(p.slice("/api/domain/".length));
      return d ? send(res, 200, d) : send(res, 404, { error: "없는 도메인" });
    }
    if (p === "/api/save" && req.method === "POST") {
      const [code, body] = save(await readBody(req));
      return send(res, code, body);
    }
    if (p.startsWith("/_flow/")) return sendFile(res, path.join(VIEWER, path.normalize(p.slice(7)).replace(/^(\.\.[/\\])+/, "")));
    if (p.startsWith("/files/")) return sendFile(res, inside(p.slice(7)));
    return sendFile(res, path.join(VIEWER, "index.html"));
  } catch (e) {
    console.error(e);
    return send(res, 500, { error: String(e.message || e) });
  }
}

const gitDir = git("rev-parse", "--absolute-git-dir");
const stateFile = gitDir ? path.join(gitDir, "flow-server.json") : null;

async function running() {
  if (!stateFile || !existsSync(stateFile)) return null;
  try {
    const { port } = readJson(stateFile);
    const r = await fetch(`http://127.0.0.1:${port}/api/ping`, { signal: AbortSignal.timeout(800) });
    const body = await r.json();
    return body.docs === DOCS ? port : null;
  } catch {
    return null;
  }
}

function listen(port, tries) {
  const server = http.createServer(handle);
  server.once("error", (e) => {
    if (e.code === "EADDRINUSE" && tries > 0) listen(port + 1, tries - 1);
    else { console.error(e.message); process.exit(1); }
  });
  server.listen(port, "127.0.0.1", () => {
    if (stateFile) writeFileSync(stateFile, JSON.stringify({ port, docs: DOCS, pid: process.pid }) + "\n");
    console.log(`flow: http://127.0.0.1:${port}/  (docs: ${DOCS})`);
  });
}

const arg = process.argv.indexOf("--port");
const wanted = Number(arg > 0 ? process.argv[arg + 1] : process.env.FLOW_PORT) || DEFAULT_PORT;
const existing = await running();
if (existing && !process.argv.includes("--new")) {
  console.log(`flow: http://127.0.0.1:${existing}/  (이미 실행 중 — docs: ${DOCS})`);
} else {
  listen(wanted, 30);
}
