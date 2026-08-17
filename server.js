const http = require("http");
const fs = require("fs");
const path = require("path");
const { URL } = require("url");

const PORT = process.env.PORT || 3000;
const UPDATE_TOKEN = process.env.UPDATE_TOKEN || "changeme";
const DATA_DIR = path.join(__dirname, "data");
const PUBLIC_DIR = path.join(__dirname, "public");

if (!fs.existsSync(DATA_DIR)) {
  fs.mkdirSync(DATA_DIR, { recursive: true });
}

const MIME = {
  ".html": "text/html; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".js": "application/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".svg": "image/svg+xml",
  ".png": "image/png",
  ".ico": "image/x-icon",
  ".woff2": "font/woff2",
};

function sendJson(res, status, payload) {
  const body = JSON.stringify(payload);
  res.writeHead(status, {
    "Content-Type": "application/json; charset=utf-8",
    "Content-Length": Buffer.byteLength(body),
  });
  res.end(body);
}

function sendText(res, status, text, type = "text/plain; charset=utf-8") {
  res.writeHead(status, { "Content-Type": type });
  res.end(text);
}

function isValidDate(date) {
  return /^\d{4}-\d{2}-\d{2}$/.test(date);
}

function dataPath(date) {
  return path.join(DATA_DIR, `${date}.json`);
}

function listAvailableDates() {
  return fs
    .readdirSync(DATA_DIR)
    .filter((f) => /^\d{4}-\d{2}-\d{2}\.json$/.test(f))
    .map((f) => f.replace(/\.json$/, ""))
    .sort()
    .reverse();
}

function readDay(date) {
  const file = dataPath(date);
  if (!fs.existsSync(file)) return null;
  return JSON.parse(fs.readFileSync(file, "utf8"));
}

function safeJoin(root, reqPath) {
  const decoded = decodeURIComponent(reqPath.split("?")[0]);
  const cleaned = path.normalize(decoded).replace(/^(\.\.[/\\])+/, "");
  const full = path.join(root, cleaned);
  if (!full.startsWith(root)) return null;
  return full;
}

function serveStatic(req, res, urlPath) {
  let filePath = safeJoin(PUBLIC_DIR, urlPath === "/" ? "/index.html" : urlPath);
  if (!filePath) {
    sendText(res, 400, "Bad path");
    return true;
  }
  if (!fs.existsSync(filePath) || fs.statSync(filePath).isDirectory()) {
    return false;
  }
  const ext = path.extname(filePath).toLowerCase();
  const type = MIME[ext] || "application/octet-stream";
  res.writeHead(200, { "Content-Type": type });
  fs.createReadStream(filePath).pipe(res);
  return true;
}

function readBody(req) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    let size = 0;
    req.on("data", (chunk) => {
      size += chunk.length;
      if (size > 2 * 1024 * 1024) {
        reject(new Error("Body too large"));
        req.destroy();
        return;
      }
      chunks.push(chunk);
    });
    req.on("end", () => resolve(Buffer.concat(chunks).toString("utf8")));
    req.on("error", reject);
  });
}

async function handleApi(req, res, pathname) {
  if (req.method === "GET" && pathname === "/api/latest") {
    const dates = listAvailableDates();
    if (!dates.length) return sendJson(res, 404, { error: "暂无简报数据" });
    return sendJson(res, 200, readDay(dates[0]));
  }

  if (req.method === "GET" && pathname.startsWith("/api/day/")) {
    const date = pathname.slice("/api/day/".length);
    if (!isValidDate(date)) {
      return sendJson(res, 400, { error: "日期格式应为 YYYY-MM-DD" });
    }
    const data = readDay(date);
    if (!data) return sendJson(res, 404, { error: "该日暂无简报" });
    return sendJson(res, 200, data);
  }

  if (req.method === "GET" && pathname === "/api/archive") {
    const dates = listAvailableDates().map((date) => {
      const day = readDay(date);
      return {
        date,
        updatedAt: day?.updatedAt || null,
        sectionTitles: (day?.sections || []).map((s) => s.title),
      };
    });
    return sendJson(res, 200, { dates });
  }

  if (req.method === "POST" && pathname === "/api/update") {
    const auth = req.headers.authorization || "";
    const token = auth.startsWith("Bearer ") ? auth.slice(7) : "";
    if (token !== UPDATE_TOKEN) {
      return sendJson(res, 401, { error: "未授权" });
    }
    try {
      const raw = await readBody(req);
      const body = JSON.parse(raw || "{}");
      if (!body.date || !isValidDate(body.date) || !Array.isArray(body.sections)) {
        return sendJson(res, 400, {
          error: "请求体需包含 date (YYYY-MM-DD) 与 sections 数组",
        });
      }
      const payload = {
        ...body,
        updatedAt: body.updatedAt || new Date().toISOString(),
      };
      fs.writeFileSync(dataPath(body.date), JSON.stringify(payload, null, 2), "utf8");
      return sendJson(res, 200, { ok: true, date: body.date });
    } catch (err) {
      return sendJson(res, 400, { error: err.message || "无效 JSON" });
    }
  }

  return false;
}

const server = http.createServer(async (req, res) => {
  try {
    const host = req.headers.host || "localhost";
    const url = new URL(req.url || "/", `http://${host}`);
    const pathname = url.pathname;

    if (pathname.startsWith("/api/")) {
      const handled = await handleApi(req, res, pathname);
      if (handled === false) {
        sendJson(res, 404, { error: "未找到接口" });
      }
      return;
    }

    if (serveStatic(req, res, pathname)) return;

    // SPA-style fallback for client routes
    const indexPath = path.join(PUBLIC_DIR, "index.html");
    if (fs.existsSync(indexPath)) {
      res.writeHead(200, { "Content-Type": "text/html; charset=utf-8" });
      fs.createReadStream(indexPath).pipe(res);
      return;
    }

    sendText(res, 404, "Not found");
  } catch (err) {
    sendJson(res, 500, { error: "服务器错误", detail: String(err.message || err) });
  }
});

server.listen(PORT, () => {
  console.log(`Daily briefing listening on port ${PORT}`);
});
