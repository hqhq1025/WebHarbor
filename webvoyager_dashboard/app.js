const data = window.WEBVOYAGER_DASHBOARD_DATA;
const reviewData = window.MANUAL_REVIEW_DATA;
const variantPlaybook = window.TASK_VARIANT_PLAYBOOK || {};

const fmt = new Intl.NumberFormat("en-US");
const byteFmt = new Intl.NumberFormat("en-US", { maximumFractionDigits: 1 });
const $ = (sel) => document.querySelector(sel);

let siteMode = "quality";
let filteredTasks = [...data.tasks];
let selectedTaskId = "";
let visibleTaskCount = 80;
let selectedReviewSlug = "allrecipes";
let reviewQuery = "";

const themeStorageKey = "webvoyager-dashboard-theme";

function preferredTheme() {
  const saved = localStorage.getItem(themeStorageKey);
  if (saved === "light" || saved === "dark") return saved;
  return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

function applyTheme(theme) {
  document.documentElement.dataset.theme = theme;
  const icon = $(".theme-icon");
  const label = $(".theme-text");
  if (icon) icon.textContent = theme === "dark" ? "☾" : "☼";
  if (label) label.textContent = theme === "dark" ? "Dark" : "Light";
}

function setupTheme() {
  applyTheme(preferredTheme());
  $("#themeToggle").addEventListener("click", () => {
    const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
    localStorage.setItem(themeStorageKey, next);
    applyTheme(next);
  });
}

function bytes(n) {
  if (!n) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  let v = n;
  let i = 0;
  while (v >= 1024 && i < units.length - 1) {
    v /= 1024;
    i += 1;
  }
  return `${byteFmt.format(v)} ${units[i]}`;
}

function text(value) {
  return value == null || value === "" ? "none" : String(value);
}

function metric(label, value, sub = "") {
  return `<div class="metric"><span>${label}</span><strong>${value}</strong>${sub ? `<small>${sub}</small>` : ""}</div>`;
}

function barRow(label, value, max, color = "var(--green)") {
  const pct = max ? Math.max(2, (value / max) * 100) : 0;
  return `
    <div class="bar-row">
      <span>${label}</span>
      <div class="bar-track"><div class="bar-fill" style="width:${pct}%;background:${color}"></div></div>
      <b>${fmt.format(value)}</b>
    </div>
  `;
}

function tiny(label) {
  return `<span class="tiny">${label}</span>`;
}

function init() {
  setupTheme();
  $("#generatedAt").textContent = new Date(data.generated_at).toLocaleString();
  renderHero();
  renderMetrics();
  renderInfra();
  renderSites();
  renderPlaybook();
  renderVariantPlaybook();
  renderCharts();
  setupFilters();
  setupReviewSearch();
  renderTasks();
  renderEvidence();
  setupSiteMode();
}

function renderVariantPlaybook() {
  const sites = data.infra.sites.filter((site) => variantPlaybook[site.slug]);
  $("#variantShell").innerHTML = sites.map((site) => {
    const play = variantPlaybook[site.slug];
    return `
      <article class="variant-site">
        <div class="variant-site-head">
          <div>
            <p class="eyebrow">${site.display}</p>
            <h3>${play.title}</h3>
          </div>
          <div class="meta-line">
            ${tiny(`${site.task_count} tasks`)}
            ${tiny(`${site.code.routes} routes`)}
            ${tiny(`${site.db.tables} tables`)}
          </div>
        </div>
        <p class="variant-thesis">${escapeHtml(play.thesis)}</p>
        <div class="variant-grid">
          ${play.variants.map((variant) => `
            <section class="variant-card">
              <h4>${escapeHtml(variant.name)}</h4>
              <div class="variant-field">
                <b>可用基础设施</b>
                <p>${escapeHtml(variant.infrastructure)}</p>
              </div>
              <div class="variant-field">
                <b>可变参数</b>
                <div class="chip-row">${variant.knobs.map((k) => tiny(k)).join("")}</div>
              </div>
              <div class="variant-field">
                <b>示例题</b>
                <ol>${variant.examples.map((example) => `<li>${escapeHtml(example)}</li>`).join("")}</ol>
              </div>
              <div class="variant-field">
                <b>验证方式</b>
                <p>${escapeHtml(variant.verification)}</p>
              </div>
              <div class="variant-field caution">
                <b>注意事项</b>
                <p>${escapeHtml(variant.risks)}</p>
              </div>
            </section>
          `).join("")}
        </div>
      </article>
    `;
  }).join("");
}

function renderHero() {
  const ok = data.infra.docker.health.ok;
  $("#healthPill").textContent = ok ? "15 mirrors alive" : "health degraded";
  $("#healthPill").style.color = ok ? "var(--lime)" : "#ffd0c8";

  $("#miniTopology").innerHTML = data.infra.sites.map((s) => `
    <a class="node" href="${s.local_url}" target="_blank" rel="noreferrer">
      <b>${s.display}</b>
      <small><span class="live">${s.health?.alive ? "alive" : "down"}</span> · :${s.local_port}</small>
    </a>
  `).join("");
}

function renderMetrics() {
  const m = data.metrics;
  const align = data.infra.task_alignment;
  $("#metricStrip").innerHTML = [
    metric("tasks", fmt.format(m.task_count), "WebVoyager original set"),
    metric("sites", fmt.format(m.site_count), "local mirrors"),
    metric("golden", fmt.format(m.answer_types.golden || 0), "strict answers"),
    metric("possible", fmt.format(m.answer_types.possible || 0), "open answers"),
    metric("stateful", fmt.format(m.stateful_tasks), "login/save/book flows"),
    metric("ID aligned", align.ids_equal ? "YES" : "NO", `${align.question_diffs} question diffs`),
  ].join("");
}

function renderInfra() {
  const container = data.infra.docker.container || "";
  const image = data.infra.docker.image || "";
  const parts = container.split("|");
  const imageParts = image.split("|");
  $("#containerStatus").textContent = data.infra.docker.health.ok ? "healthy" : "check";
  $("#containerStatus").className = `tag ${data.infra.docker.health.ok ? "ok" : "warn"}`;
  $("#infraFacts").innerHTML = [
    ["container", parts[0] || "not running"],
    ["image", parts[1] || "unknown"],
    ["status", parts[2] || "unknown"],
    ["control", data.infra.control_plane.local],
    ["image id", imageParts[0]?.replace("sha256:", "").slice(0, 18) || "unknown"],
    ["image size", imageParts[1] ? bytes(Number(imageParts[1])) : "unknown"],
    ["webharbor", data.repos.webharbor.commit],
    ["webvoyager", data.repos.webvoyager.commit],
  ].map(([k, v]) => `<div class="kv"><span>${k}</span><b>${v}</b></div>`).join("");

  const a = data.infra.task_alignment;
  $("#alignmentTag").textContent = a.ids_equal && a.question_diffs === 0 ? "exact" : "drift";
  $("#alignmentBars").innerHTML = [
    barRow("WebHarbor", a.webharbor_tasks, Math.max(a.webharbor_tasks, a.webvoyager_tasks)),
    barRow("WebVoyager", a.webvoyager_tasks, Math.max(a.webharbor_tasks, a.webvoyager_tasks), "var(--blue)"),
    barRow("Q diffs", a.question_diffs, 20, "var(--red)"),
    barRow("URL diffs", a.upstream_diffs, 20, "var(--red)"),
  ].join("");

  const brokenSites = data.infra.sites.filter((s) => (s.browser?.brokenImages || 0) > 0 || (s.browser?.badResponses || []).length > 0);
  const noGolden = data.infra.sites.filter((s) => s.golden === 0);
  const externalHeavy = data.infra.sites.filter((s) => (s.browser?.externalLinks || 0) > 0).sort((a, b) => (b.browser.externalLinks || 0) - (a.browser.externalLinks || 0)).slice(0, 3);
  $("#riskList").innerHTML = [
    `<div class="risk ${brokenSites.length ? "high" : ""}"><b>资源完整性</b><br>${brokenSites.length ? `${brokenSites.map((s) => `${s.display}(${s.browser.brokenImages || 0})`).join(", ")} 有坏图或 4xx 响应。` : "首页抽测未发现坏图。"}</div>`,
    `<div class="risk"><b>答案口径</b><br>${noGolden.length ? `${noGolden.map((s) => s.display).join(", ")} 没有 golden answer，偏 open-ended。` : "所有站点都有至少一条 golden answer。"}</div>`,
    `<div class="risk"><b>离线性</b><br>${externalHeavy.map((s) => `${s.display}: ${s.browser.externalLinks || 0} external links`).join("; ") || "外链信号较少。"} 需做网络隔离复测。</div>`,
  ].join("");
}

function setupSiteMode() {
  document.querySelectorAll("[data-site-mode]").forEach((button) => {
    button.addEventListener("click", () => {
      siteMode = button.dataset.siteMode;
      document.querySelectorAll("[data-site-mode]").forEach((b) => b.classList.toggle("active", b === button));
      renderSites();
    });
  });
}

function renderSites() {
  $("#siteGrid").innerHTML = data.infra.sites.map((s) => {
    const b = s.browser || {};
    const code = s.code || {};
    const topTables = s.db.top_tables || [];
    const imgBytes = s.assets?.static_images?.bytes || 0;
    const extBytes = s.assets?.static_external_cache?.bytes || 0;
    let bars = "";
    if (siteMode === "quality") {
      bars = [
        barRow("tasks", s.task_count, 50),
        barRow("golden", s.golden, 35, "var(--blue)"),
        barRow("bad img", b.brokenImages || 0, 12, "var(--red)"),
      ].join("");
    } else if (siteMode === "data") {
      const maxRows = Math.max(...data.infra.sites.map((x) => (x.db.top_tables?.[0]?.[1] || 0)));
      bars = topTables.slice(0, 3).map(([name, count]) => barRow(name.slice(0, 12), count, maxRows, "var(--green)")).join("");
    } else {
      const maxLines = Math.max(...data.infra.sites.map((x) => x.code.app_lines || 0));
      bars = [
        barRow("routes", code.routes || 0, 90),
        barRow("templates", code.templates || 0, 55, "var(--blue)"),
        barRow("app lines", code.app_lines || 0, maxLines, "var(--amber)"),
      ].join("");
    }
    return `
      <article class="site-card">
        <div class="site-shot">${s.screenshot ? `<img src="${s.screenshot}" alt="${s.display} screenshot">` : ""}</div>
        <div class="site-card-body">
          <div class="panel-head">
            <h3>${s.display}</h3>
            <span class="tag ${s.health?.alive ? "ok" : "warn"}">${s.health?.alive ? "alive" : "down"}</span>
          </div>
          <div class="meta-line">
            ${tiny(`${s.task_count} tasks`)}
            ${tiny(`${s.golden} golden`)}
            ${tiny(`C${s.avg_complexity}`)}
            ${tiny(`:${s.local_port}`)}
          </div>
          <div class="meta-line">
            ${tiny(`${code.routes || 0} routes`)}
            ${tiny(`${s.db.tables || 0} tables`)}
            ${tiny(`${bytes(imgBytes + extBytes)} assets`)}
          </div>
          <div class="site-bars">${bars}</div>
          <a class="review-link" href="#playbook" data-review-jump="${s.slug}">查看网页审阅</a>
        </div>
      </article>
    `;
  }).join("");
  document.querySelectorAll("[data-review-jump]").forEach((link) => {
    link.addEventListener("click", () => {
      selectedReviewSlug = link.dataset.reviewJump;
      reviewQuery = "";
      $("#reviewSearchInput").value = "";
      renderPlaybook();
    });
  });
}

function renderPlaybook() {
  const sites = data.infra.sites;
  $("#reviewTabs").innerHTML = sites.map((s) => {
    const review = reviewData.sites[s.slug];
    const filteredCount = filteredReviewTasks(review).length;
    return `
      <button class="review-tab ${s.slug === selectedReviewSlug ? "active" : ""}" data-review-tab="${s.slug}" type="button">
        <span>${s.display}</span>
        <small>${filteredCount}/${review.tasks.length}</small>
      </button>
    `;
  }).join("");
  document.querySelectorAll("[data-review-tab]").forEach((button) => {
    button.addEventListener("click", () => {
      selectedReviewSlug = button.dataset.reviewTab;
      renderPlaybook();
    });
  });
  renderReviewReader();
}

function setupReviewSearch() {
  $("#reviewSearchInput").addEventListener("input", (event) => {
    reviewQuery = event.target.value.trim().toLowerCase();
    renderPlaybook();
  });
}

function filteredReviewTasks(review) {
  if (!reviewQuery) return review.tasks;
  return review.tasks.filter((task) => `${task.id} ${task.intent} ${task.recommendation}`.toLowerCase().includes(reviewQuery));
}

function renderReviewReader() {
  const site = data.infra.sites.find((s) => s.slug === selectedReviewSlug);
  const review = reviewData.sites[selectedReviewSlug];
  const tasks = filteredReviewTasks(review);
  $("#reviewReader").innerHTML = `
    <div class="review-hero">
      <div>
        <p class="eyebrow">Manual review component</p>
        <h3>${review.title}</h3>
        <div class="meta-line">
          ${tiny(`${review.tasks.length} task reviews`)}
          ${tiny(`${site.golden} golden`)}
          ${tiny(`${site.possible} possible`)}
          ${tiny(`${site.code.routes} routes`)}
          ${tiny(`${site.db.tables} db tables`)}
        </div>
      </div>
      <a class="review-open-site" href="${site.local_url}" target="_blank" rel="noreferrer">打开镜像站</a>
    </div>
    <div class="review-section">
      <h4>基础设施能力</h4>
      ${paragraphs(review.infrastructure)}
    </div>
    <div class="review-two-col">
      <div class="review-section compact">
        <h4>可泛化任务族</h4>
        ${bulletList(review.goodFamilies)}
      </div>
      <div class="review-section compact">
        <h4>站点特化场景</h4>
        ${bulletList(review.targetedFamilies)}
      </div>
    </div>
    <div class="review-section compact">
      <h4>扩容前需要补的基础设施</h4>
      ${bulletList(review.gaps)}
    </div>
    <div class="review-section">
      <div class="review-task-head">
        <h4>逐任务建议</h4>
        <span>${tasks.length} / ${review.tasks.length}</span>
      </div>
      <div class="review-task-list">
        ${tasks.map(reviewTaskCard).join("") || `<div class="empty-state">没有匹配的审阅建议。</div>`}
      </div>
    </div>
  `;
  document.querySelectorAll("[data-task-link]").forEach((button) => {
    button.addEventListener("click", () => {
      const taskId = button.dataset.taskLink;
      const task = data.tasks.find((t) => t.id === taskId);
      if (!task) return;
      $("#siteFilter").value = task.slug;
      $("#searchInput").value = taskId;
      applyTaskFilters();
      document.querySelector("#tasks").scrollIntoView({ behavior: "smooth", block: "start" });
    });
  });
}

function paragraphs(textValue) {
  return textValue.split(/\n\s*\n/).map((p) => `<p>${escapeHtml(p).replace(/\n/g, " ")}</p>`).join("");
}

function bulletList(items) {
  return `<ul>${items.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`;
}

function reviewTaskCard(task) {
  const original = data.tasks.find((t) => t.id === task.id);
  return `
    <article class="review-task-card">
      <div class="review-task-id">
        <b>${task.id}</b>
        ${original ? `<span>${original.answer_type} · C${original.complexity}</span>` : ""}
      </div>
      <div>
        <h5>${escapeHtml(task.intent)}</h5>
        <p>${escapeHtml(task.recommendation)}</p>
      </div>
      <button type="button" data-task-link="${task.id}">看原任务</button>
    </article>
  `;
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (ch) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  }[ch]));
}

function renderCharts() {
  const actions = Object.entries(data.metrics.actions).slice(0, 10);
  const maxAction = Math.max(...actions.map(([, v]) => v));
  $("#actionChart").innerHTML = actions.map(([k, v]) => barRow(k, v, maxAction)).join("");

  const golden = data.metrics.answer_types.golden || 0;
  const possible = data.metrics.answer_types.possible || 0;
  const angle = Math.round((golden / (golden + possible)) * 360);
  $("#answerChart").innerHTML = `
    <div class="donut" style="--angle:${angle}deg"></div>
    <div class="legend">
      <div class="legend-row"><span>golden</span><b>${fmt.format(golden)}</b></div>
      <div class="legend-row"><span>possible</span><b>${fmt.format(possible)}</b></div>
      <div class="legend-row"><span>golden ratio</span><b>${Math.round((golden / (golden + possible)) * 100)}%</b></div>
    </div>
  `;

  const hist = Object.entries(data.metrics.complexity_histogram);
  const maxHist = Math.max(...hist.map(([, v]) => v));
  $("#complexityChart").innerHTML = hist.map(([k, v]) => `
    <div class="hist-col">
      <div class="hist-bar" style="height:${Math.max(5, (v / maxHist) * 160)}px"></div>
      <span>${k}</span>
    </div>
  `).join("");
}

function setupFilters() {
  const siteSelect = $("#siteFilter");
  siteSelect.innerHTML = `<option value="">全部站点</option>` + data.infra.sites.map((s) => `<option value="${s.slug}">${s.display}</option>`).join("");
  const actions = [...new Set(data.tasks.flatMap((t) => t.actions))].sort();
  $("#actionFilter").innerHTML = `<option value="">全部动作</option>` + actions.map((a) => `<option value="${a}">${a}</option>`).join("");
  ["searchInput", "siteFilter", "answerFilter", "actionFilter", "stateFilter"].forEach((id) => {
    $(`#${id}`).addEventListener("input", applyTaskFilters);
    $(`#${id}`).addEventListener("change", applyTaskFilters);
  });
  $("#loadMoreBtn").addEventListener("click", () => {
    visibleTaskCount += 80;
    renderTasks();
  });
}

function applyTaskFilters() {
  const query = $("#searchInput").value.trim().toLowerCase();
  const site = $("#siteFilter").value;
  const answer = $("#answerFilter").value;
  const action = $("#actionFilter").value;
  const state = $("#stateFilter").value;

  filteredTasks = data.tasks.filter((t) => {
    const hay = `${t.id} ${t.site} ${t.question} ${t.answer}`.toLowerCase();
    if (query && !hay.includes(query)) return false;
    if (site && t.slug !== site) return false;
    if (answer && t.answer_type !== answer) return false;
    if (action && !t.actions.includes(action)) return false;
    if (state === "state" && !t.requires_state) return false;
    if (state === "stateless" && t.requires_state) return false;
    return true;
  });

  selectedTaskId = "";
  visibleTaskCount = 80;
  renderTasks();
}

function renderTasks() {
  $("#taskCount").textContent = `${fmt.format(filteredTasks.length)} / ${fmt.format(data.tasks.length)}`;
  const visible = filteredTasks.slice(0, visibleTaskCount);
  $("#taskList").innerHTML = visible.map((t) => taskRow(t)).join("") || `<div class="empty-state">当前筛选没有任务。</div>`;
  $("#loadMoreBtn").hidden = filteredTasks.length <= visibleTaskCount;
  $("#loadMoreBtn").textContent = `显示更多任务 (${Math.min(visibleTaskCount, filteredTasks.length)} / ${filteredTasks.length})`;

  document.querySelectorAll("[data-task-id]").forEach((row) => {
    row.addEventListener("click", () => {
      selectedTaskId = selectedTaskId === row.dataset.taskId ? "" : row.dataset.taskId;
      renderTasks();
    });
  });
}

function taskRow(t) {
  const expanded = t.id === selectedTaskId;
  return `
    <article class="task-row ${expanded ? "active" : ""}" data-task-id="${t.id}">
      <div class="task-row-id">${t.id}</div>
      <div class="task-row-site">${t.site}<br>${t.answer_type}</div>
      <div class="task-row-question">${t.question}</div>
      <div class="task-row-score">C${t.complexity}<br>${t.requires_state ? "state" : "read"}</div>
      ${expanded ? taskExpanded(t) : ""}
    </article>
  `;
}

function taskExpanded(t) {
  return `
    <div class="task-expanded">
      <div class="detail-block">
        <p class="eyebrow">Reference answer</p>
        <p class="detail-answer">${text(t.answer)}</p>
      </div>
      <div class="detail-block">
        <p class="eyebrow">Task profile</p>
        <div class="meta-line">
          ${tiny(`complexity ${t.complexity}`)}
          ${tiny(`${t.constraint_count} constraints`)}
          ${tiny(t.requires_state ? "stateful" : "stateless")}
        </div>
        <div class="meta-line">${t.actions.map(tiny).join("")}</div>
        <div class="detail-links">
          <a href="${t.local_url}" target="_blank" rel="noreferrer">Local Mirror</a>
          <a href="${t.upstream_url}" target="_blank" rel="noreferrer">Original Site</a>
        </div>
      </div>
    </div>
  `;
}

function renderEvidence() {
  const homes = data.infra.sites.slice(0, 8).map((s) => ({
    title: `${s.display} home`,
    subtitle: `${s.browser?.chars || 0} chars · ${s.browser?.brokenImages || 0} broken images`,
    img: s.screenshot,
  }));
  const scenarios = data.infra.browser_scenarios.slice(0, 8).map((s) => ({
    title: s.name,
    subtitle: s.ok ? "scenario reached target page" : "scenario failed",
    img: `assets/audit_screens/${s.name}.png`,
  }));
  $("#evidenceGrid").innerHTML = [...homes, ...scenarios].filter((x) => x.img).map((e) => `
    <article class="evidence-card">
      <img src="${e.img}" alt="${e.title}">
      <div><b>${e.title}</b><small>${e.subtitle}</small></div>
    </article>
  `).join("");
}

init();
