const pages = {
  dashboard: "dashboardPage", master: "masterPage",
  ica: "icaPage", tpd: "tpdPage"
};

document.querySelectorAll(".nav").forEach(btn => {
  btn.onclick = () => {
    document.querySelectorAll(".nav").forEach(x => x.classList.remove("active"));
    btn.classList.add("active");
    Object.values(pages).forEach(id => document.getElementById(id).classList.add("hidden"));
    document.getElementById(pages[btn.dataset.page]).classList.remove("hidden");
    const titles = {dashboard:"State Dashboard",master:"Master Data Upload",ica:"ICA Weekly Report Upload",tpd:"TPD Weekly Report Upload"};
    document.getElementById("pageTitle").textContent = titles[btn.dataset.page];
  };
});

function rankHtml(items) {
  if (!items || !items.length) return "<p>No data available yet.</p>";
  return items.map((x,i) => `<div class="row"><span>${i+1}</span><span class="name">${x.name}</span><span class="score">${x.score}%</span></div>`).join("");
}

async function loadDashboard() {
  const status = document.getElementById("status");
  status.textContent = "Refreshing live data...";
  try {
    const r = await fetch("/api/dashboard/state");
    const d = await r.json();
    if (!r.ok) throw new Error(d.detail || "Dashboard error");
    const s = d.summary;
    document.getElementById("total").textContent = s.total_aww;
    document.getElementById("active").textContent = s.active_aww;
    document.getElementById("inactive").textContent = s.inactive_aww;
    document.getElementById("gold").textContent = s.gold;
    document.getElementById("silver").textContent = s.silver;
    document.getElementById("bronze").textContent = s.bronze;
    document.getElementById("rate").textContent = s.certification_rate + "%";
    document.getElementById("top").innerHTML = rankHtml(d.top_supervisors);
    document.getElementById("bottom").innerHTML = rankHtml(d.bottom_supervisors);
    document.getElementById("blocks").innerHTML = rankHtml(d.top_blocks);
    document.getElementById("systemInfo").textContent = `${s.total_aww} Master AWW records currently loaded. Live analytics is active.`;
    status.textContent = "Live data loaded successfully.";
  } catch(e) {
    status.textContent = "Could not load live data.";
    console.error(e);
  }
}

function showMessage(el, text, ok=true) {
  el.className = "message " + (ok ? "success" : "error");
  el.textContent = text;
}

document.getElementById("masterForm").onsubmit = async e => {
  e.preventDefault();
  const msg = document.getElementById("masterMsg");
  const fd = new FormData(e.target);
  try {
    const r = await fetch("/api/master/upload",{method:"POST",body:fd});
    const d = await r.json();
    if (!r.ok) throw new Error(d.detail || "Upload failed");
    showMessage(msg, `${d.message}. New: ${d.created}, Updated: ${d.updated}, Skipped: ${d.skipped}`);
    loadDashboard();
  } catch(err) { showMessage(msg, err.message, false); }
};

document.querySelectorAll(".reportForm").forEach(form => {
  form.onsubmit = async e => {
    e.preventDefault();
    const msg = form.parentElement.querySelector(".message");
    const fd = new FormData(form);
    fd.append("report_type", form.dataset.type);
    try {
      const r = await fetch("/api/report/upload",{method:"POST",body:fd});
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || "Upload failed");
      showMessage(msg, `${d.message}. Processed: ${d.processed}, Skipped: ${d.skipped}`);
      loadDashboard();
    } catch(err) { showMessage(msg, err.message, false); }
  };
});

loadDashboard();
