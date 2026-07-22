// --- Authentification ---
const AUTH_KEY = "seeborg_auth";
const NAME_KEY = "seeborg_name";

function getStoredAuth() {
  return localStorage.getItem(AUTH_KEY);
}

function getStoredName() {
  return localStorage.getItem(NAME_KEY) || "";
}

async function apiFetch(url, options = {}) {
  const auth = getStoredAuth();
  const headers = { ...(options.headers || {}) };
  if (auth) headers["Authorization"] = auth;

  const resp = await fetch(url, { ...options, headers });
  if (resp.status === 401) {
    localStorage.removeItem(AUTH_KEY);
    localStorage.removeItem(NAME_KEY);
    showLogin();
    throw new Error("unauthorized");
  }
  return resp;
}

function switchAuthMode(mode) {
  document.getElementById("seg-login").classList.toggle("active", mode === "login");
  document.getElementById("seg-register").classList.toggle("active", mode === "register");
  document.getElementById("login-form").style.display = mode === "login" ? "flex" : "none";
  document.getElementById("register-form").style.display = mode === "register" ? "flex" : "none";
  document.getElementById("login-sub").textContent =
    mode === "login" ? "Connecte-toi pour accéder à ton suivi" : "Crée ton compte pour démarrer";
}

function showLogin() {
  document.getElementById("app-shell").classList.remove("visible");
  document.getElementById("screen-login").classList.add("active");
}

async function loginWithCredentials(user, pass) {
  const authHeader = "Basic " + btoa(`${user}:${pass}`);
  const resp = await fetch("/api/whoami", { headers: { Authorization: authHeader } });
  if (!resp.ok) throw new Error("bad credentials");
  const data = await resp.json();

  localStorage.setItem(AUTH_KEY, authHeader);
  localStorage.setItem(NAME_KEY, data.nom);

  document.getElementById("screen-login").classList.remove("active");
  document.getElementById("app-shell").classList.add("visible");
  startApp();
}

async function handleLogin(event) {
  event.preventDefault();
  const user = document.getElementById("login-user").value.trim();
  const pass = document.getElementById("login-pass").value;
  const errorEl = document.getElementById("login-error");
  const submitBtn = document.getElementById("login-submit");

  errorEl.textContent = "";
  submitBtn.disabled = true;
  submitBtn.textContent = "Connexion...";

  try {
    await loginWithCredentials(user, pass);
  } catch (e) {
    errorEl.textContent = "Identifiant ou mot de passe incorrect.";
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = "Se connecter";
  }
}

async function handleRegister(event) {
  event.preventDefault();
  const nom = document.getElementById("register-nom").value.trim();
  const user = document.getElementById("register-user").value.trim();
  const pass = document.getElementById("register-pass").value;
  const errorEl = document.getElementById("register-error");
  const submitBtn = document.getElementById("register-submit");

  errorEl.textContent = "";
  submitBtn.disabled = true;
  submitBtn.textContent = "Création...";

  try {
    const resp = await fetch("/api/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ nom, login: user, password: pass }),
    });
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      throw new Error(err.detail || "Impossible de créer le compte");
    }
    await loginWithCredentials(user, pass);
  } catch (e) {
    errorEl.textContent = e.message || "Impossible de créer le compte.";
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = "Créer mon compte";
  }
}

function handleLogout() {
  localStorage.removeItem(AUTH_KEY);
  localStorage.removeItem(NAME_KEY);
  location.reload();
}

function applyGreeting() {
  const nom = getStoredName();
  document.getElementById("today-greeting").textContent = nom ? `Bonjour ${nom}` : "Bonjour";
}

// --- Horloge (heure locale de l'appareil) ---
function updateClock() {
  const now = new Date();
  const dateStr = now.toLocaleDateString("fr-FR", { weekday: "short", day: "numeric", month: "short" });
  const timeStr = now.toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" });
  const el = document.getElementById("header-datetime");
  if (el) el.textContent = `${dateStr} · ${timeStr}`;
}

function startApp() {
  applyGreeting();
  updateClock();
  setInterval(updateClock, 30000);
  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("/service-worker.js");
  }
  loadToday();
}

// --- Démarrage : vérifie si une session valide existe déjà ---
(async function init() {
  const auth = getStoredAuth();
  if (!auth) {
    showLogin();
    return;
  }
  try {
    const resp = await fetch("/api/whoami", { headers: { Authorization: auth } });
    if (!resp.ok) throw new Error("invalid session");
    const data = await resp.json();
    localStorage.setItem(NAME_KEY, data.nom);
    document.getElementById("screen-login").classList.remove("active");
    document.getElementById("app-shell").classList.add("visible");
    startApp();
  } catch (e) {
    localStorage.removeItem(AUTH_KEY);
    localStorage.removeItem(NAME_KEY);
    showLogin();
  }
})();

// --- Navigation entre écrans ---
function showScreen(name) {
  document.querySelectorAll(".screen").forEach((s) => s.classList.remove("active"));
  document.querySelectorAll("nav button").forEach((b) => b.classList.remove("active"));
  document.getElementById(`screen-${name}`).classList.add("active");
  document.querySelector(`nav button[data-screen="${name}"]`).classList.add("active");

  if (name === "dashboard") loadDashboard();
  if (name === "weight") loadWeightChart();
  if (name === "settings") loadTemplates();
}

// --- Aujourd'hui ---
async function loadToday() {
  const res = await apiFetch("/api/program/current");
  const data = await res.json();

  if (!data.program) {
    document.getElementById("today-sub").textContent = "Aucun programme choisi";
    document.getElementById("today-content").innerHTML =
      '<div class="empty">Va dans l\'onglet "Programme" pour en choisir un.</div>';
    return;
  }

  const statsRes = await apiFetch("/api/stats");
  const stats = await statsRes.json();

  document.getElementById("today-sub").textContent = `${data.program.name} — séance : ${data.next_day.name}`;

  if (stats.today_done) {
    document.getElementById("today-content").innerHTML =
      '<div class="card accent-green"><h2>Bravo</h2><div class="stat-message">Séance déjà loggée aujourd\'hui 💪</div></div>';
    return;
  }

  const exercisesHtml = data.next_day.exercises.map((ex, i) => `
    <div class="exercise">
      <label class="check-wrap">
        <input type="checkbox" id="ex-check-${i}">
      </label>
      <div style="flex:1">
        <div class="name">${ex.name}</div>
        <div class="target">${ex.sets} × ${ex.reps} reps</div>
      </div>
      <input type="number" step="0.5" inputmode="decimal" id="ex-weight-${i}" placeholder="kg">
    </div>
  `).join("");

  document.getElementById("today-content").innerHTML = `
    <div class="card">
      <h2>${data.next_day.name}</h2>
      ${exercisesHtml}
    </div>
    <button onclick='submitSession(${JSON.stringify(data.next_day.name)}, ${JSON.stringify(data.next_day.exercises)})'>Terminer la séance</button>
  `;
}

async function submitSession(dayName, exercisesTarget) {
  const exercises = exercisesTarget.map((ex, i) => {
    const checked = document.getElementById(`ex-check-${i}`).checked;
    const weight = parseFloat(document.getElementById(`ex-weight-${i}`).value) || 0;
    return checked ? { name: ex.name, sets: ex.sets, reps: ex.reps, weight_kg: weight } : null;
  }).filter(Boolean);

  if (!exercises.length) {
    alert("Coche au moins un exercice réalisé.");
    return;
  }

  await apiFetch("/api/sessions", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ day_name: dayName, exercises }),
  });

  loadToday();
}

// --- Poids ---
async function submitWeight() {
  const val = parseFloat(document.getElementById("weight-input").value);
  if (!val) return;
  await apiFetch("/api/weight", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ weight_kg: val }),
  });
  document.getElementById("weight-input").value = "";
  loadWeightChart();
}

let weightChartInstance;
async function loadWeightChart() {
  const res = await apiFetch("/api/weight");
  const rows = await res.json();
  const labels = rows.map((r) => r.date);
  const data = rows.map((r) => r.weight_kg);

  if (weightChartInstance) weightChartInstance.destroy();
  weightChartInstance = new Chart(document.getElementById("weightChart"), {
    type: "line",
    data: { labels, datasets: [{ label: "Poids (kg)", data, borderColor: "#4f8cff", backgroundColor: "rgba(79,140,255,0.15)", fill: true, tension: 0.3 }] },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { color: "#9199a8" }, grid: { color: "#262a33" } },
        y: { ticks: { color: "#9199a8" }, grid: { color: "#262a33" } },
      },
    },
  });
}

// --- Dashboard ---
let dashboardSessions = [];
let weekOffset = 0;

async function loadDashboard() {
  const [statsRes, sessionsRes] = await Promise.all([apiFetch("/api/stats"), apiFetch("/api/sessions")]);
  const stats = await statsRes.json();
  dashboardSessions = await sessionsRes.json();
  weekOffset = 0;

  document.getElementById("dashboard-content").innerHTML = `
    <div class="stat-row">
      <div class="card accent-orange"><h2>Streak</h2><div class="stat">${stats.streak_days} j</div></div>
      <div class="card accent-purple"><h2>Séances totales</h2><div class="stat">${stats.total_sessions}</div></div>
    </div>
    <div class="card accent-blue"><h2>Volume 7 derniers jours</h2><div class="stat">${stats.volume_7d.toLocaleString()} kg</div></div>
    <div class="card">
      <h2>Vue hebdomadaire</h2>
      <div id="week-view"></div>
    </div>
    <div class="card">
      <h2>Volume par séance</h2>
      <canvas id="volumeChart"></canvas>
    </div>
  `;

  renderWeekView();

  const labels = dashboardSessions.slice().reverse().map((s) => s.date);
  const data = dashboardSessions.slice().reverse().map((s) =>
    s.exercises.reduce((sum, ex) => sum + ex.sets * ex.reps * ex.weight_kg, 0)
  );

  new Chart(document.getElementById("volumeChart"), {
    type: "bar",
    data: { labels, datasets: [{ label: "Volume (kg)", data, backgroundColor: "#4f8cff" }] },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { color: "#9199a8" }, grid: { color: "#262a33" } },
        y: { ticks: { color: "#9199a8" }, grid: { color: "#262a33" } },
      },
    },
  });
}

function getWeekBounds(offset) {
  const now = new Date();
  const day = now.getDay();
  const diffToMonday = day === 0 ? -6 : 1 - day;
  const monday = new Date(now);
  monday.setDate(now.getDate() + diffToMonday + offset * 7);
  monday.setHours(0, 0, 0, 0);
  const sunday = new Date(monday);
  sunday.setDate(monday.getDate() + 6);
  return { monday, sunday };
}

function isoDate(d) {
  return d.toISOString().slice(0, 10);
}

function renderWeekView() {
  const container = document.getElementById("week-view");
  if (!container) return;

  const { monday, sunday } = getWeekBounds(weekOffset);
  const mondayIso = isoDate(monday);
  const sundayIso = isoDate(sunday);
  const weekSessions = dashboardSessions.filter((s) => s.date >= mondayIso && s.date <= sundayIso);
  const volume = weekSessions.reduce(
    (sum, s) => sum + s.exercises.reduce((a, ex) => a + ex.sets * ex.reps * ex.weight_kg, 0), 0
  );
  const doneDates = new Set(weekSessions.map((s) => s.date));
  const todayIso = isoDate(new Date());

  const dayLabels = ["L", "M", "M", "J", "V", "S", "D"];
  let cellsHtml = "";
  for (let i = 0; i < 7; i++) {
    const d = new Date(monday);
    d.setDate(monday.getDate() + i);
    const iso = isoDate(d);
    const active = doneDates.has(iso);
    const isToday = iso === todayIso;
    cellsHtml += `<div class="week-day${active ? " active" : ""}${isToday ? " today" : ""}"><span>${dayLabels[i]}</span></div>`;
  }

  const rangeLabel = weekOffset === 0
    ? "Cette semaine"
    : `${monday.toLocaleDateString("fr-FR", { day: "numeric", month: "short" })} – ${sunday.toLocaleDateString("fr-FR", { day: "numeric", month: "short" })}`;

  container.innerHTML = `
    <div class="week-nav">
      <button class="icon-btn" onclick="changeWeek(-1)">‹</button>
      <span class="week-range">${rangeLabel}</span>
      <button class="icon-btn" onclick="changeWeek(1)" ${weekOffset >= 0 ? "disabled" : ""}>›</button>
    </div>
    <div class="week-days">${cellsHtml}</div>
    <div class="week-stats">
      <div><span class="week-stat-value">${weekSessions.length}</span><span class="week-stat-label">séance${weekSessions.length > 1 ? "s" : ""}</span></div>
      <div><span class="week-stat-value">${Math.round(volume).toLocaleString()}</span><span class="week-stat-label">kg de volume</span></div>
    </div>
  `;
}

function changeWeek(delta) {
  weekOffset = Math.min(0, weekOffset + delta);
  renderWeekView();
}

// --- Réglages / choix du programme ---
let muscleGroupsCache = null;
let customDays = [];

async function getMuscleGroups() {
  if (!muscleGroupsCache) {
    const res = await apiFetch("/api/muscle-groups");
    muscleGroupsCache = await res.json();
  }
  return muscleGroupsCache;
}

function switchProgramMode(mode) {
  document.getElementById("seg-templates").classList.toggle("active", mode === "templates");
  document.getElementById("seg-custom").classList.toggle("active", mode === "custom");
  document.getElementById("templates-panel").style.display = mode === "templates" ? "flex" : "none";
  document.getElementById("custom-panel").style.display = mode === "custom" ? "block" : "none";
  if (mode === "custom" && customDays.length === 0) addCustomDay();
}

async function loadTemplates() {
  const [templatesRes, currentRes] = await Promise.all([apiFetch("/api/templates"), apiFetch("/api/program/current")]);
  const templates = await templatesRes.json();
  const current = await currentRes.json();
  const currentId = current.program ? current.program.id : null;

  document.getElementById("templates-panel").innerHTML = templates.map((t) => `
    <div class="card ${t.id === currentId ? "selected" : ""}" onclick="selectTemplate('${t.id}')">
      <h2>${t.name}</h2>
      <div>${t.description}</div>
    </div>
  `).join("");

  if (currentId === "custom") {
    switchProgramMode("custom");
    if (current.program.days) {
      customDays = current.program.days.map((d) => ({ name: d.name, muscle_groups: d.muscle_groups }));
      renderCustomDays();
    }
  }
}

async function selectTemplate(id) {
  await apiFetch("/api/program/select", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ template_id: id }),
  });
  loadTemplates();
  loadToday();
}

async function addCustomDay() {
  customDays.push({ name: `Jour ${customDays.length + 1}`, muscle_groups: [] });
  await renderCustomDays();
}

function removeCustomDay(index) {
  customDays.splice(index, 1);
  renderCustomDays();
}

function toggleMuscleGroup(dayIndex, groupId) {
  const day = customDays[dayIndex];
  const pos = day.muscle_groups.indexOf(groupId);
  if (pos === -1) day.muscle_groups.push(groupId);
  else day.muscle_groups.splice(pos, 1);
  renderCustomDays();
}

function renameCustomDay(index, value) {
  customDays[index].name = value;
}

async function renderCustomDays() {
  const groups = await getMuscleGroups();
  const container = document.getElementById("custom-days");

  container.innerHTML = customDays.map((day, i) => `
    <div class="card">
      <div class="day-header">
        <input type="text" class="day-name-input" value="${day.name}" oninput="renameCustomDay(${i}, this.value)">
        <button class="icon-btn" onclick="removeCustomDay(${i})">✕</button>
      </div>
      <div class="chip-row">
        ${groups.map((g) => `
          <button class="chip ${day.muscle_groups.includes(g.id) ? "selected" : ""}" onclick="toggleMuscleGroup(${i}, '${g.id}')">${g.name}</button>
        `).join("")}
      </div>
    </div>
  `).join("");
}

async function saveCustomProgram() {
  const validDays = customDays.filter((d) => d.muscle_groups.length > 0);
  if (!validDays.length) {
    alert("Sélectionne au moins un groupe musculaire pour au moins un jour.");
    return;
  }
  await apiFetch("/api/program/custom", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ days: validDays }),
  });
  await loadTemplates();
  loadToday();
  alert("Programme personnalisé enregistré !");
}

// Le démarrage (service worker, loadToday, horloge) est géré par startApp() après connexion.
