const TZ = "Asia/Singapore";
const TAB_ORDER = ["ai", "women40", "pharma", "codexiq"];
const TAB_LABELS = {
  ai: "AI / LLM",
  pharma: "健康医药",
  women40: "40+ 女性",
  codexiq: "Codex IQ",
};

function $(sel) {
  return document.querySelector(sel);
}

function escapeHtml(str) {
  return String(str ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function formatDateLong(dateStr) {
  try {
    const d = new Date(`${dateStr}T12:00:00+08:00`);
    return new Intl.DateTimeFormat("zh-CN", {
      timeZone: TZ,
      year: "numeric",
      month: "long",
      day: "numeric",
      weekday: "long",
    }).format(d);
  } catch {
    return dateStr;
  }
}

function formatUpdatedAt(iso) {
  if (!iso) return "";
  try {
    return new Intl.DateTimeFormat("zh-CN", {
      timeZone: TZ,
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    }).format(new Date(iso));
  } catch {
    return iso;
  }
}

function todayInSingapore() {
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: TZ,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(new Date());
}

function getParams() {
  const params = new URLSearchParams(location.search);
  const date = params.get("date");
  let tab = params.get("tab") || location.hash.replace(/^#/, "");
  if (!TAB_ORDER.includes(tab)) tab = "ai";
  return {
    date: date && /^\d{4}-\d{2}-\d{2}$/.test(date) ? date : null,
    tab,
  };
}

function setParams({ date, tab }, replace = false) {
  const params = new URLSearchParams();
  if (date) params.set("date", date);
  if (tab && tab !== "ai") params.set("tab", tab);
  const qs = params.toString();
  const url = qs ? `/?${qs}` : "/";
  if (replace) history.replaceState(null, "", url);
  else history.pushState(null, "", url);
}

function setStatus(message, isError = false) {
  const el = $("#status");
  if (!message) {
    el.hidden = true;
    el.textContent = "";
    return;
  }
  el.hidden = false;
  el.textContent = message;
  el.classList.toggle("error", isError);
}

function renderSources(sources = []) {
  if (!sources.length) return "";
  return `<div class="sources">${sources
    .map(
      (s) =>
        `<a class="source-link" href="${escapeHtml(s.url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(
          s.label || "来源"
        )}</a>`
    )
    .join("")}</div>`;
}

function renderItem(item, index) {
  return `
    <li class="item">
      <div class="item-index">${index + 1}</div>
      <div class="item-body">
        <h2 class="item-title">${escapeHtml(item.title)}</h2>
        <p class="item-summary">${escapeHtml(item.summary)}</p>
        <div class="item-meta">
          ${item.date ? `<span class="item-date">${escapeHtml(item.date)}</span>` : ""}
          ${renderSources(item.sources)}
        </div>
      </div>
    </li>
  `;
}

function orderedSections(data) {
  const map = new Map((data.sections || []).map((s) => [s.id, s]));
  return TAB_ORDER.map((id) => map.get(id)).filter(Boolean);
}

function renderTabs(sections, activeId) {
  const nav = $("#topic-tabs");
  nav.innerHTML = sections
    .map((s) => {
      const active = s.id === activeId ? "active" : "";
      const count = (s.items || []).length;
      const label = TAB_LABELS[s.id] || s.title;
      return `<button type="button" class="tab ${active}" data-id="${escapeHtml(s.id)}" aria-selected="${
        s.id === activeId
      }">${escapeHtml(label)}<span class="count">${count}</span></button>`;
    })
    .join("");

  nav.querySelectorAll(".tab").forEach((btn) => {
    btn.addEventListener("click", () => {
      const tab = btn.dataset.id;
      const { date } = getParams();
      setParams({ date, tab });
      renderActiveTopic(window.__briefingData, tab);
    });
  });
}

function renderActiveTopic(data, tabId) {
  const sections = orderedSections(data);
  const section = sections.find((s) => s.id === tabId) || sections[0];
  if (!section) {
    $("#topic-panel").innerHTML = `<div class="empty">该日暂无内容。</div>`;
    return;
  }

  const items = section.items || [];
  $("#eyebrow").textContent = formatDateLong(data.date);
  $("#page-title").textContent = section.title;
  $("#hero-summary").textContent = section.summary || "";
  const updated = formatUpdatedAt(data.updatedAt);
  $("#hero-meta").textContent = `${items.length} 条全部展示${
    updated ? ` · 最近更新 ${updated}（新加坡时间）` : ""
  }`;

  const panel = $("#topic-panel");
  panel.dataset.id = section.id;
  if (!items.length) {
    panel.innerHTML = `<div class="empty">这一页暂时没有条目。</div>`;
  } else {
    panel.innerHTML = `<ol class="item-list">${items.map(renderItem).join("")}</ol>`;
  }

  renderTabs(sections, section.id);
  document.title = `${section.title} · Neuma 每日简报 · ${data.date}`;
  window.scrollTo({ top: 0, behavior: "instant" in window ? "instant" : "auto" });
}

async function fillDateSelect(activeDate) {
  const select = $("#date-select");
  try {
    const res = await fetch("/api/archive");
    const payload = await res.json();
    const dates = (payload.dates || []).map((d) => d.date);
    if (!dates.includes(activeDate)) dates.unshift(activeDate);
    const today = todayInSingapore();
    select.innerHTML = dates
      .map((d) => {
        const label = d === today ? `${d}（今天）` : d;
        return `<option value="${escapeHtml(d)}" ${d === activeDate ? "selected" : ""}>${escapeHtml(
          label
        )}</option>`;
      })
      .join("");
  } catch {
    select.innerHTML = `<option value="${escapeHtml(activeDate)}">${escapeHtml(activeDate)}</option>`;
  }

  select.onchange = () => {
    const date = select.value;
    const { tab } = getParams();
    const today = todayInSingapore();
    setParams({ date: date === today ? null : date, tab });
    loadBriefing();
  };
}

async function loadBriefing() {
  const panel = $("#topic-panel");
  panel.innerHTML = `<div class="skeleton"></div><div class="skeleton"></div><div class="skeleton"></div>`;
  setStatus("");

  const { date: queryDate, tab } = getParams();
  const url = queryDate ? `/api/day/${queryDate}` : "/api/latest";

  try {
    const res = await fetch(url);
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error || "加载失败");
    }
    const data = await res.json();
    window.__briefingData = data;
    const sections = orderedSections(data);
    const active = sections.some((s) => s.id === tab) ? tab : sections[0]?.id || "ai";
    if (active !== tab) setParams({ date: queryDate, tab: active }, true);
    renderActiveTopic(data, active);
    await fillDateSelect(data.date);
  } catch (err) {
    panel.innerHTML = "";
    $("#page-title").textContent = "Neuma 每日简报";
    $("#eyebrow").textContent = formatDateLong(queryDate || todayInSingapore());
    $("#hero-summary").textContent = "";
    $("#hero-meta").textContent = "";
    $("#topic-tabs").innerHTML = "";
    setStatus(err.message || "无法加载简报数据。", true);
  }
}

window.addEventListener("popstate", loadBriefing);
loadBriefing();
