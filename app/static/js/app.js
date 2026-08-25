const API = "/api/v1";

const state = {
  token: localStorage.getItem("careguard_token"),
  user: null,
  links: [],
  targetId: null,
};

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function showToast(message, type = "success") {
  const toast = document.createElement("div");
  toast.className = `toast ${type === "error" ? "error" : ""}`;
  toast.textContent = message;
  $("#toast-region").append(toast);
  window.setTimeout(() => toast.remove(), 4200);
}

async function request(path, options = {}) {
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  if (state.token) headers.Authorization = `Bearer ${state.token}`;
  const response = await fetch(`${API}${path}`, { ...options, headers });
  if (response.status === 204) return null;
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    if (response.status === 401 && state.token) logout(false);
    const error = new Error(data.message || "请求失败，请稍后重试");
    error.status = response.status;
    error.code = data.code;
    error.details = data.details;
    throw error;
  }
  return data;
}

function formJson(form) {
  return Object.fromEntries(new FormData(form).entries());
}

function formatDate(value, includeTime = true) {
  if (!value) return "";
  const date = new Date(value.endsWith?.("Z") ? value : `${value}Z`);
  if (Number.isNaN(date.valueOf())) return value;
  return new Intl.DateTimeFormat("zh-CN", {
    month: "long",
    day: "numeric",
    ...(includeTime ? { hour: "2-digit", minute: "2-digit" } : {}),
  }).format(date);
}

function emotionName(label) {
  return { positive: "积极", neutral: "中性", negative: "消极" }[label] || "尚未记录";
}

function showAuth() {
  $("#auth-view").classList.remove("hidden");
  $("#dashboard-view").classList.add("hidden");
  $("#logout-button").classList.add("hidden");
}

function showDashboardShell() {
  $("#auth-view").classList.add("hidden");
  $("#dashboard-view").classList.remove("hidden");
  $("#logout-button").classList.remove("hidden");
}

function logout(notify = true) {
  localStorage.removeItem("careguard_token");
  state.token = null;
  state.user = null;
  state.links = [];
  state.targetId = null;
  showAuth();
  switchAuthTab("login");
  if (notify) showToast("已安全退出");
}

function switchAuthTab(mode) {
  const login = mode === "login";
  $("#login-panel").classList.toggle("hidden", !login);
  $("#register-panel").classList.toggle("hidden", login);
  $("#login-tab").classList.toggle("active", login);
  $("#register-tab").classList.toggle("active", !login);
  $("#login-tab").setAttribute("aria-selected", String(login));
  $("#register-tab").setAttribute("aria-selected", String(!login));
  (login ? $("#login-phone") : $("#register-name")).focus();
}

function setupAccessibility() {
  let fontStep = Number(localStorage.getItem("careguard_font_step") || 0);
  const applyFont = () => {
    document.documentElement.style.setProperty("--base-font", `${18 + fontStep * 2}px`);
    localStorage.setItem("careguard_font_step", String(fontStep));
  };
  $("#font-up").addEventListener("click", () => { fontStep = Math.min(3, fontStep + 1); applyFont(); });
  $("#font-down").addEventListener("click", () => { fontStep = Math.max(-1, fontStep - 1); applyFont(); });
  applyFont();

  const contrast = localStorage.getItem("careguard_contrast") === "true";
  document.body.classList.toggle("high-contrast", contrast);
  $("#contrast-toggle").setAttribute("aria-pressed", String(contrast));
  $("#contrast-toggle").addEventListener("click", (event) => {
    const enabled = !document.body.classList.contains("high-contrast");
    document.body.classList.toggle("high-contrast", enabled);
    event.currentTarget.setAttribute("aria-pressed", String(enabled));
    localStorage.setItem("careguard_contrast", String(enabled));
  });

  $$(".password-toggle").forEach((button) => button.addEventListener("click", () => {
    const input = document.getElementById(button.dataset.target);
    const visible = input.type === "text";
    input.type = visible ? "password" : "text";
    button.textContent = visible ? "显示" : "隐藏";
    button.setAttribute("aria-label", visible ? "显示密码" : "隐藏密码");
  }));
}

async function handleLogin(event) {
  event.preventDefault();
  const data = formJson(event.currentTarget);
  try {
    const result = await request("/auth/login", { method: "POST", body: JSON.stringify(data) });
    state.token = result.access_token;
    localStorage.setItem("careguard_token", state.token);
    showToast("登录成功，欢迎回来");
    await loadDashboard();
  } catch (error) {
    showToast(error.message, "error");
  }
}

async function handleRegister(event) {
  event.preventDefault();
  const raw = formJson(event.currentTarget);
  const data = { ...raw, consent: raw.consent === "on" };
  try {
    const result = await request("/auth/register", { method: "POST", body: JSON.stringify(data) });
    state.token = result.access_token;
    localStorage.setItem("careguard_token", state.token);
    showToast("账号创建成功");
    await loadDashboard();
  } catch (error) {
    showToast(error.message, "error");
  }
}

function configureRoleView() {
  const isFamily = state.user.role === "family";
  $("#nav-user-name").textContent = state.user.name;
  $("#welcome-name").textContent = state.user.name;
  $("#user-avatar").textContent = state.user.name.slice(0, 1);
  $("#nav-user-role").textContent = isFamily ? "家属端" : "老人端";
  $("#quick-mood-card").classList.toggle("hidden", isFamily);
  $("#link-create-card").classList.toggle("hidden", !isFamily);
  $("#target-picker-wrap").classList.toggle("hidden", !isFamily);
  $("#today-label").textContent = new Intl.DateTimeFormat("zh-CN", { dateStyle: "full" }).format(new Date());
}

async function loadDashboard() {
  showDashboardShell();
  try {
    state.user = await request("/auth/me");
    state.links = await request("/care-links");
    configureRoleView();
    configureTargets();
    renderLinks();
    renderPendingLinks();
    await loadTargetData();
  } catch (error) {
    if (error.status !== 401) showToast(error.message, "error");
  }
}

function activeLinks() {
  return state.links.filter((link) => link.status === "active");
}

function configureTargets() {
  if (state.user.role === "elderly") {
    state.targetId = state.user.id;
    return;
  }
  const links = activeLinks();
  if (!links.some((link) => link.elderly_id === state.targetId)) {
    state.targetId = links[0]?.elderly_id || null;
  }
  const picker = $("#target-picker");
  picker.innerHTML = links.length
    ? links.map((link) => `<option value="${link.elderly_id}" ${link.elderly_id === state.targetId ? "selected" : ""}>${escapeHtml(link.elderly_name)}</option>`).join("")
    : '<option value="">请先绑定老人账号</option>';
  picker.disabled = links.length === 0;
}

function renderPendingLinks() {
  const wrap = $("#pending-links");
  const pending = state.links.filter((link) => link.status === "pending" && link.elderly_id === state.user.id);
  wrap.classList.toggle("hidden", pending.length === 0);
  wrap.innerHTML = pending.map((link) => `
    <div class="pending-invite">
      <div><strong>${escapeHtml(link.family_name)} 请求与您建立家庭关怀绑定</strong><div>确认后，对方可看情绪分类、提醒和关怀消息，但看不到原始心情文字。</div></div>
      <button class="primary-button" type="button" data-action="accept-link" data-id="${link.id}">确认绑定</button>
    </div>`).join("");
}

function renderLinks() {
  const target = $("#link-list");
  if (!state.links.length) {
    target.className = "item-list empty-state";
    target.textContent = "暂无家庭绑定";
    return;
  }
  target.className = "item-list";
  target.innerHTML = state.links.map((link) => {
    const otherName = state.user.role === "family" ? link.elderly_name : link.family_name;
    const statusText = { pending: "待确认", active: "已绑定", revoked: "已解除" }[link.status];
    return `<div class="list-item"><div class="list-item-main"><strong>${escapeHtml(otherName)}</strong><small>${state.user.role === "family" ? "老人" : "家属"} · ${statusText}</small></div><div class="list-actions"><span class="status-chip ${link.status}">${statusText}</span>${link.status !== "revoked" ? `<button class="small-button danger-button" type="button" data-action="revoke-link" data-id="${link.id}">解除</button>` : ""}</div></div>`;
  }).join("");
}

function clearTargetData() {
  $("#latest-mood").textContent = "尚未选择";
  $("#mood-total").textContent = "绑定后查看趋势";
  $("#pending-reminders").textContent = "0 项";
  $("#open-alerts").textContent = "0 条";
  ["#overview-reminders", "#overview-alerts", "#mood-history", "#reminder-list", "#contact-list"].forEach((selector) => {
    $(selector).className = selector === "#mood-history" ? "timeline empty-state" : "item-list empty-state";
    $(selector).textContent = "请先选择已绑定的老人账号";
  });
}

async function loadTargetData() {
  if (!state.targetId) {
    clearTargetData();
    return;
  }
  const query = `?owner_id=${state.targetId}`;
  try {
    const [moods, stats, reminders, alerts, contacts] = await Promise.all([
      request(`/moods${query}`),
      request(`/moods/stats${query}`),
      request(`/reminders${query}`),
      request(`/alerts${query}`),
      request(`/contacts${query}`),
    ]);
    renderMoods(moods, stats);
    renderReminders(reminders);
    renderAlerts(alerts);
    renderContacts(contacts);
  } catch (error) {
    showToast(error.message, "error");
  }
}

function renderMoods(moods, stats) {
  $("#latest-mood").textContent = emotionName(stats.latest_emotion);
  $("#mood-total").textContent = `近 30 天 ${stats.total} 次打卡`;
  $("#mood-stats").innerHTML = [
    ["positive", "积极", stats.positive], ["neutral", "中性", stats.neutral], ["negative", "消极", stats.negative],
  ].map(([label, name, count]) => `<article class="metric-card"><span class="metric-icon" aria-hidden="true">${label === "positive" ? "☺" : label === "negative" ? "◡" : "•"}</span><div><small>${name}</small><strong>${count} 次</strong><span>近 30 天</span></div></article>`).join("");

  const history = $("#mood-history");
  if (!moods.length) {
    history.className = "timeline empty-state";
    history.textContent = "还没有心情记录";
    return;
  }
  history.className = "timeline";
  history.innerHTML = moods.map((mood) => `<div class="timeline-item"><span class="timeline-dot"></span><div class="timeline-copy"><strong>${formatDate(mood.checked_at)} · <span class="status-chip ${mood.emotion}">${mood.emotion_display}</span></strong><p>${mood.text ? escapeHtml(mood.text) : "原始文字受隐私保护，仅老人本人可见"}</p><small>置信提示 ${mood.confidence}% · ${escapeHtml(mood.disclaimer)}</small></div></div>`).join("");
}

function reminderLabel(reminder) {
  return reminder.reminder_type === "medication" ? "用药" : "日程";
}

function renderReminders(reminders) {
  const pending = reminders.filter((item) => !item.is_completed);
  $("#pending-reminders").textContent = `${pending.length} 项`;
  const overview = $("#overview-reminders");
  overview.className = pending.length ? "item-list" : "item-list empty-state";
  overview.innerHTML = pending.length ? pending.slice(0, 3).map((r) => `<div class="list-item"><div class="list-item-main"><strong>${escapeHtml(r.title)}</strong><small>${reminderLabel(r)} · ${formatDate(r.due_at)}</small></div><span class="status-chip">待完成</span></div>`).join("") : "暂无提醒";

  const list = $("#reminder-list");
  list.className = reminders.length ? "item-list" : "item-list empty-state";
  list.innerHTML = reminders.length ? reminders.map((r) => `<div class="list-item"><div class="list-item-main"><strong>${escapeHtml(r.title)}</strong><small>${reminderLabel(r)} · ${formatDate(r.due_at)} · ${r.recurrence === "daily" ? "每天" : r.recurrence === "weekly" ? "每周" : "单次"}</small></div><div class="list-actions">${!r.is_completed ? `<button class="small-button" type="button" data-action="complete-reminder" data-id="${r.id}">完成</button>` : '<span class="status-chip">已完成</span>'}<button class="small-button danger-button" type="button" data-action="delete-reminder" data-id="${r.id}">删除</button></div></div>`).join("") : "暂无提醒";
}

function renderAlerts(alerts) {
  const open = alerts.filter((item) => item.status === "open");
  $("#open-alerts").textContent = `${open.length} 条`;
  const list = $("#overview-alerts");
  list.className = alerts.length ? "item-list" : "item-list empty-state";
  list.innerHTML = alerts.length ? alerts.slice(0, 5).map((alert) => `<div class="list-item"><div class="list-item-main"><strong><span class="status-chip ${alert.severity}">${alert.severity === "high" ? "优先" : "关注"}</span> ${escapeHtml(alert.message)}</strong><small>${formatDate(alert.created_at)} · ${alert.status === "open" ? "待关怀" : "已处理"}</small></div>${alert.status === "open" ? `<button class="small-button" type="button" data-action="ack-alert" data-id="${alert.id}">我已关怀</button>` : ""}</div>`).join("") : "当前没有待处理的关怀消息";
}

function renderContacts(contacts) {
  const list = $("#contact-list");
  list.className = contacts.length ? "item-list" : "item-list empty-state";
  list.innerHTML = contacts.length ? contacts.map((c) => `<div class="list-item"><div class="list-item-main"><strong>${escapeHtml(c.name_masked)} · ${escapeHtml(c.relationship)}</strong><small>${escapeHtml(c.phone_masked)}</small></div><span class="status-chip">第 ${c.priority} 联系人</span></div>`).join("") : "暂无联系人";
}

async function createMood(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const text = $("#quick-mood-text").value.trim();
  if (!text) return;
  try {
    const mood = await request("/moods", { method: "POST", body: JSON.stringify({ text }) });
    form.reset();
    showToast(`记录成功：${mood.emotion_display}`);
    await loadTargetData();
  } catch (error) { showToast(error.message, "error"); }
}

async function createReminder(event) {
  event.preventDefault();
  const form = event.currentTarget;
  if (!state.targetId) return showToast("请先绑定并选择老人账号", "error");
  const value = $("#reminder-time").value;
  const payload = {
    owner_id: state.targetId,
    title: $("#reminder-title").value.trim(),
    reminder_type: $("#reminder-type").value,
    due_at: new Date(value).toISOString(),
    recurrence: $("#reminder-repeat").value,
    notes: $("#reminder-notes").value.trim() || null,
  };
  try {
    await request("/reminders", { method: "POST", body: JSON.stringify(payload) });
    form.reset();
    showToast("提醒已保存");
    await loadTargetData();
  } catch (error) { showToast(error.message, "error"); }
}

async function createLink(event) {
  event.preventDefault();
  const form = event.currentTarget;
  try {
    await request("/care-links", { method: "POST", body: JSON.stringify({ elderly_phone: $("#elderly-phone").value.trim() }) });
    form.reset();
    showToast("绑定邀请已发送，等待老人确认");
    await refreshLinks();
  } catch (error) { showToast(error.message, "error"); }
}

async function refreshLinks() {
  state.links = await request("/care-links");
  configureTargets();
  renderLinks();
  renderPendingLinks();
}

async function createContact(event) {
  event.preventDefault();
  const form = event.currentTarget;
  if (!state.targetId) return showToast("请先绑定并选择老人账号", "error");
  const payload = {
    owner_id: state.targetId,
    name: $("#contact-name").value.trim(),
    phone: $("#contact-phone").value.trim(),
    relationship: $("#contact-relation").value.trim(),
    priority: Number($("#contact-priority").value),
  };
  try {
    await request("/contacts", { method: "POST", body: JSON.stringify(payload) });
    form.reset();
    showToast("紧急联系人已保存并脱敏展示");
    await loadTargetData();
  } catch (error) { showToast(error.message, "error"); }
}

async function handleAction(button) {
  const action = button.dataset.action;
  const id = button.dataset.id;
  try {
    if (action === "accept-link") {
      await request(`/care-links/${id}/accept`, { method: "POST" });
      showToast("已确认家庭关怀绑定");
      await refreshLinks();
      await loadTargetData();
    } else if (action === "revoke-link") {
      if (!window.confirm("确认解除这条家庭关怀绑定吗？")) return;
      await request(`/care-links/${id}`, { method: "DELETE" });
      showToast("绑定已解除");
      await refreshLinks();
      await loadTargetData();
    } else if (action === "complete-reminder") {
      await request(`/reminders/${id}`, { method: "PATCH", body: JSON.stringify({ is_completed: true }) });
      showToast("已标记为完成");
      await loadTargetData();
    } else if (action === "delete-reminder") {
      if (!window.confirm("确认删除这条提醒吗？")) return;
      await request(`/reminders/${id}`, { method: "DELETE" });
      showToast("提醒已删除");
      await loadTargetData();
    } else if (action === "ack-alert") {
      await request(`/alerts/${id}/acknowledge`, { method: "POST" });
      showToast("已记录本次关怀");
      await loadTargetData();
    }
  } catch (error) { showToast(error.message, "error"); }
}

function navigate(sectionName) {
  $$(".content-section").forEach((section) => section.classList.add("hidden"));
  $$(".nav-item").forEach((item) => item.classList.toggle("active", item.dataset.section === sectionName));
  const section = $(`#section-${sectionName}`);
  section.classList.remove("hidden");
  section.focus();
  if (sectionName === "privacy") loadPrivacy();
}

async function loadPrivacy() {
  try {
    const logs = await request("/audit-logs/me?limit=30");
    const list = $("#audit-list");
    list.className = logs.length ? "item-list" : "item-list empty-state";
    const labels = { login: "登录", register: "注册", create: "新增", update: "更新", delete: "删除", read: "读取", invite: "邀请绑定", accept: "确认绑定", revoke: "解除绑定", acknowledge: "确认关怀", export: "导出数据" };
    list.innerHTML = logs.length ? logs.map((log) => `<div class="list-item"><div class="list-item-main"><strong>${labels[log.action] || escapeHtml(log.action)} · ${escapeHtml(log.resource_type)}</strong><small>${formatDate(log.created_at)} · ${log.outcome === "success" ? "成功" : "已拒绝"}</small></div></div>`).join("") : "暂无操作记录";
  } catch (error) { showToast(error.message, "error"); }
}

async function exportData() {
  try {
    const data = await request("/privacy/export");
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `careguard-my-data-${new Date().toISOString().slice(0, 10)}.json`;
    link.click();
    URL.revokeObjectURL(url);
    showToast("个人数据已导出");
    await loadPrivacy();
  } catch (error) { showToast(error.message, "error"); }
}

function bindEvents() {
  $("#login-tab").addEventListener("click", () => switchAuthTab("login"));
  $("#register-tab").addEventListener("click", () => switchAuthTab("register"));
  $("#login-form").addEventListener("submit", handleLogin);
  $("#register-form").addEventListener("submit", handleRegister);
  $("#logout-button").addEventListener("click", () => logout());
  $("#quick-mood-form").addEventListener("submit", createMood);
  $("#reminder-form").addEventListener("submit", createReminder);
  $("#link-form").addEventListener("submit", createLink);
  $("#contact-form").addEventListener("submit", createContact);
  $("#export-button").addEventListener("click", exportData);
  $("#target-picker").addEventListener("change", async (event) => {
    state.targetId = Number(event.target.value) || null;
    await loadTargetData();
  });
  document.addEventListener("click", (event) => {
    const actionButton = event.target.closest("[data-action]");
    if (actionButton) handleAction(actionButton);
    const navButton = event.target.closest("[data-section]");
    if (navButton) navigate(navButton.dataset.section);
    const goButton = event.target.closest("[data-go]");
    if (goButton) navigate(goButton.dataset.go);
  });
}

async function start() {
  setupAccessibility();
  bindEvents();
  if (state.token) await loadDashboard();
  else showAuth();
}

start();
