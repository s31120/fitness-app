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
  const res = await fetch("/api/program/current");
  const data = await res.json();

  if (!data.program) {
    document.getElementById("today-sub").textContent = "Aucun programme choisi";
    document.getElementById("today-content").innerHTML =
      '<div class="empty">Va dans l\'onglet "Programme" pour en choisir un.</div>';
    return;
  }

  const statsRes = await fetch("/api/stats");
  const stats = await statsRes.json();

  document.getElementById("today-sub").textContent = `${data.program.name} — séance : ${data.next_day.name}`;

  if (stats.today_done) {
    document.getElementById("today-content").innerHTML =
      '<div class="card"><h2>Bravo</h2><div class="stat">Séance déjà loggée aujourd\'hui 💪</div></div>';
    return;
  }

  const exercisesHtml = data.next_day.exercises.map((ex, i) => `
    <div class="exercise">
      <input type="checkbox" id="ex-check-${i}">
      <div style="flex:1">
        <div class="name">${ex.name}</div>
        <div class="target">${ex.sets} × ${ex.reps} reps</div>
      </div>
      <input type="number" step="0.5" id="ex-weight-${i}" placeholder="kg">
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

  await fetch("/api/sessions", {
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
  await fetch("/api/weight", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ weight_kg: val }),
  });
  document.getElementById("weight-input").value = "";
  loadWeightChart();
}

let weightChartInstance;
async function loadWeightChart() {
  const res = await fetch("/api/weight");
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
async function loadDashboard() {
  const [statsRes, sessionsRes] = await Promise.all([fetch("/api/stats"), fetch("/api/sessions")]);
  const stats = await statsRes.json();
  const sessions = await sessionsRes.json();

  document.getElementById("dashboard-content").innerHTML = `
    <div class="stat-row">
      <div class="card"><h2>Streak</h2><div class="stat">${stats.streak_days} j</div></div>
      <div class="card"><h2>Séances totales</h2><div class="stat">${stats.total_sessions}</div></div>
    </div>
    <div class="card"><h2>Volume 7 derniers jours</h2><div class="stat">${stats.volume_7d.toLocaleString()} kg</div></div>
    <div class="card">
      <h2>Volume par séance</h2>
      <canvas id="volumeChart"></canvas>
    </div>
  `;

  const labels = sessions.slice().reverse().map((s) => s.date);
  const data = sessions.slice().reverse().map((s) =>
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

// --- Réglages / choix du programme ---
async function loadTemplates() {
  const [templatesRes, currentRes] = await Promise.all([fetch("/api/templates"), fetch("/api/program/current")]);
  const templates = await templatesRes.json();
  const current = await currentRes.json();
  const currentId = current.program ? current.program.id : null;

  document.getElementById("template-list").innerHTML = templates.map((t) => `
    <div class="card ${t.id === currentId ? "selected" : ""}" onclick="selectTemplate('${t.id}')">
      <h2>${t.name}</h2>
      <div>${t.description}</div>
    </div>
  `).join("");
}

async function selectTemplate(id) {
  await fetch("/api/program/select", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ template_id: id }),
  });
  loadTemplates();
  loadToday();
}

// --- Service worker (installabilité PWA) ---
if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("/service-worker.js");
}

loadToday();
