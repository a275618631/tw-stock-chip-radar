let ratioChart = null;
let useLogScale = false;
let marketFilter = "ALL";
let currentWindow = 20;
let currentMetric = "netbuy"; // "netbuy" | "change"
let currentSide = "up";       // "up" | "down"
let radarPayload = null;

async function fetchJson(url) {
  const resp = await fetch(url);
  if (!resp.ok) {
    throw new Error(`HTTP ${resp.status}`);
  }
  return await resp.json();
}

function formatPct(x) {
  const v = Number.isFinite(x) ? x : 0;
  return v.toFixed(2);
}

function formatNumber(x) {
  const v = Number.isFinite(x) ? x : 0;
  return v.toLocaleString();
}

function signedNumber(x) {
  const v = Number.isFinite(x) ? x : 0;
  return (v > 0 ? "+" : "") + v.toLocaleString();
}

function netClass(x) {
  if (x > 0) return "net-positive";
  if (x < 0) return "net-negative";
  return "";
}

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function signedLots(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) return "—";
  const formatted = number.toLocaleString("zh-TW", { minimumFractionDigits: Number.isInteger(number) ? 0 : 3, maximumFractionDigits: 3 });
  return `${number > 0 ? "+" : ""}${formatted} 張`;
}

function signalText(label) {
  return { positive: "Positive", neutral: "Neutral", negative: "Negative", insufficient_data: "Insufficient" }[label] || "Missing";
}

function signalMarkup(label) {
  const safe = ["positive", "neutral", "negative", "insufficient_data"].includes(label) ? label : "missing";
  return `<span class="signal-pill ${safe}">${signalText(label)}</span>`;
}

function freshnessClass(status) {
  return { ok: "fresh-ok", partial: "fresh-partial", missing: "fresh-missing" }[status] || "fresh-missing";
}

function showDirectFileNotice() {
  document.querySelectorAll(".section").forEach((section) => {
    section.classList.remove("active");
  });
  document.querySelectorAll(".main-nav").forEach((nav) => {
    nav.hidden = true;
  });
  const notice = document.getElementById("directFileNotice");
  if (notice) {
    notice.hidden = false;
    notice.classList.add("active");
  }
}

// ========== Daily Radar ==========

function renderDailyRadar(payload) {
  const environment = payload.environment || {};
  const envNode = document.getElementById("radarEnvironment");
  envNode.className = `signal-pill ${environment.label || "insufficient_data"}`;
  envNode.innerHTML = signalText(environment.label);

  document.getElementById("radarGeneratedAt").textContent = `最後更新：${payload.generated_at || "missing"}`;
  const freshness = payload.freshness || {};
  const freshnessNode = document.getElementById("radarFreshness");
  freshnessNode.innerHTML = Object.entries({ institutional: "法人", broker: "分點", macro: "Macro" })
    .map(([key, label]) => `<div class="freshness-card ${freshnessClass(payload.status)}"><span>${label}</span><strong>${escapeHtml(freshness[key] || "missing")}</strong></div>`)
    .join("");

  document.getElementById("macroContextCards").innerHTML = (payload.macro || []).map((item) => `
    <div class="macro-card ${item.status === "ok" ? "" : "macro-missing"}">
      <h4>${escapeHtml(item.name)}</h4>
      <p class="macro-ticker">${escapeHtml(item.ticker)} · ${escapeHtml(item.latest_date || "missing")}</p>
      <strong class="macro-close">${escapeHtml(item.close == null ? "—" : Number(item.close).toLocaleString("zh-TW"))}</strong>
      <p class="macro-change">1D ${escapeHtml(item.change_1d_pct == null ? "—" : `${item.change_1d_pct}%`)} · 5D ${escapeHtml(item.change_5d_pct == null ? "—" : `${item.change_5d_pct}%`)}</p>
    </div>`).join("");

  const rows = (payload.watchlist || []).map((stock) => {
    const m = stock.institutional || {};
    const broker = stock.brokers || {};
    const brokerLabel = broker.available
      ? `買 ${((broker.top_buys || [])[0] || {}).broker_name || "有資料"}`
      : "分點：未追蹤";
    return `<tr data-stock-code="${escapeHtml(stock.code)}">
      <td><span class="badge">${escapeHtml(stock.code)}</span>${escapeHtml(stock.name)}<small>${escapeHtml(stock.date || "missing")}</small></td>
      <td>${signalMarkup(stock.status)}</td>
      <td class="${netClass(Number(m.foreign_5d))}">${signedLots(m.foreign_5d)}</td>
      <td class="${netClass(Number(m.trust_5d))}">${signedLots(m.trust_5d)}</td>
      <td class="${netClass(Number(m.dealer_5d))}">${signedLots(m.dealer_5d)}</td>
      <td>${escapeHtml(brokerLabel)}</td>
    </tr>`;
  }).join("");
  const tbody = document.querySelector("#watchlistTable tbody");
  tbody.innerHTML = rows || "<tr><td colspan='6'>目前沒有可用追蹤資料</td></tr>";
  tbody.querySelectorAll("tr[data-stock-code]").forEach((row) => {
    row.addEventListener("click", () => openInstitutionalStock(row.dataset.stockCode));
  });

  const limitations = [...new Set(payload.limitations || [])].slice(0, 3);
  document.getElementById("radarLimitations").textContent = limitations.join("；");
}

async function loadDailyRadar() {
  const errorNode = document.getElementById("radarLoadError");
  try {
    radarPayload = await fetchJson("data/daily_radar.json");
    renderDailyRadar(radarPayload);
  } catch (err) {
    errorNode.hidden = false;
    errorNode.textContent = `Dashboard 資料讀取失敗：${err.message}。請確認 daily_radar.json 存在，或資料更新是否成功。`;
  }
}

// ========== Stock Chart ==========

async function loadStock(code) {
  const status = document.getElementById("statusText");
  const title = document.getElementById("chartTitle");
  const btn = document.getElementById("loadBtn");

  code = (code || "").trim();
  if (!code) return;

  btn.disabled = true;
  status.textContent = `載入 ${code}...`;

  const showForeign = document.getElementById("showForeign").checked;
  const showTrust = document.getElementById("showTrust").checked;
  const showDealer = document.getElementById("showDealer").checked;
  const showTotal = document.getElementById("showTotal").checked;

  try {
    const data = await fetchJson(`data/timeseries/${code}.json`);
    if (!data.length) {
      status.textContent = `找不到 ${code} 資料`;
      btn.disabled = false;
      return;
    }

    const name = data[0].name || "";
    const market = data[0].market || "";
    title.textContent = `${code} ${name}（${market}）`;

    const labels = data.map((d) => d.date);
    const foreignRatio = data.map((d) => d.foreign_ratio);
    const trustRatio = data.map((d) => d.trust_ratio);
    const dealerRatio = data.map((d) => d.dealer_ratio);
    const totalRatio = data.map((d) => d.three_inst_ratio);

    const datasets = [];
    if (showForeign) {
      datasets.push({
        label: "外資%",
        data: foreignRatio,
        borderColor: "#ff6b6b",
        backgroundColor: "rgba(255, 107, 107, 0.1)",
        borderWidth: 2,
        tension: 0.3,
        fill: true,
      });
    }
    if (showTrust) {
      datasets.push({
        label: "投信%",
        data: trustRatio,
        borderColor: "#4ecdc4",
        borderWidth: 2,
        borderDash: [5, 3],
        tension: 0.3,
      });
    }
    if (showDealer) {
      datasets.push({
        label: "自營商%",
        data: dealerRatio,
        borderColor: "#ffe66d",
        borderWidth: 2,
        borderDash: [2, 2],
        tension: 0.3,
      });
    }
    if (showTotal) {
      datasets.push({
        label: "三法人合計%",
        data: totalRatio,
        borderColor: "#a55eea",
        borderWidth: 3,
        pointRadius: 0,
        tension: 0.3,
      });
    }

    const ctx = document.getElementById("ratioChart").getContext("2d");
    if (ratioChart) {
      ratioChart.destroy();
    }

    ratioChart = new Chart(ctx, {
      type: "line",
      data: { labels, datasets },
      options: {
        responsive: true,
        interaction: { mode: "index", intersect: false },
        scales: {
          x: {
            ticks: { maxTicksLimit: 8, color: "#8b8b9e" },
            grid: { color: "rgba(255,255,255,0.05)" },
          },
          y: {
            type: useLogScale ? "logarithmic" : "linear",
            title: { display: true, text: "持股比重 (%)", color: "#8b8b9e" },
            ticks: { color: "#8b8b9e" },
            grid: { color: "rgba(255,255,255,0.05)" },
            min: 0,
          },
        },
        plugins: {
          legend: { position: "bottom", labels: { color: "#eaeaea" } },
        },
      },
    });

    const last = data[data.length - 1];
    status.textContent = `${last.date} | 三大法人 ${formatPct(last.three_inst_ratio)}%`;
  } catch (err) {
    console.error(err);
    status.textContent = `載入失敗：${err.message}`;
  } finally {
    btn.disabled = false;
  }
}

// ========== Institutional Ranking ==========

function applyMarketFilter(rows) {
  return rows.filter((row) => marketFilter === "ALL" || row.market === marketFilter);
}

function bindRowClick(tr, code) {
  tr.addEventListener("click", () => {
    document.getElementById("stockInput").value = code;
    loadStock(code);
  });
}

async function loadRanking() {
  if (currentMetric === "netbuy") {
    await loadNetbuyRanking();
  } else {
    await loadChangeRanking();
  }
}

// 三大法人 N 日買賣超排行（官方日買賣超加總，單位：張，可對照富邦驗證）
async function loadNetbuyRanking() {
  const head = document.getElementById("rankHead");
  const tbody = document.querySelector("#rankTable tbody");
  const title = document.getElementById("rankTitle");
  const subtitle = document.getElementById("rankSubtitle");

  title.textContent = currentSide === "up" ? "📈 三大法人買超排名" : "📉 三大法人賣超排名";
  head.innerHTML =
    "<tr><th>#</th><th>股票</th><th>市場</th><th>外資</th><th>投信</th><th>自營</th><th>合計(張)</th></tr>";
  tbody.innerHTML = "<tr><td colspan='7'>載入中...</td></tr>";

  try {
    const payload = await fetchJson(
      `data/top_three_inst_netbuy_${currentWindow}_${currentSide}.json`
    );
    const rows = payload.data || [];
    const range = payload.date_range
      ? `${payload.date_range.start} ~ ${payload.date_range.end}`
      : "";
    subtitle.textContent =
      `最近 ${payload.trading_days || currentWindow} 個交易日三大法人累計買賣超（張）` +
      (range ? `｜${range}` : "") +
      "｜5/10/30 日可對照富邦驗證";

    const filtered = applyMarketFilter(rows);
    tbody.innerHTML = "";
    if (!filtered.length) {
      tbody.innerHTML = "<tr><td colspan='7'>無資料</td></tr>";
      return;
    }
    filtered.slice(0, 50).forEach((row, idx) => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>${idx + 1}</td>
        <td><span class="badge">${row.code}</span>${row.name || ""}</td>
        <td>${row.market || ""}</td>
        <td class="${netClass(row.foreign)}">${signedNumber(row.foreign)}</td>
        <td class="${netClass(row.trust)}">${signedNumber(row.trust)}</td>
        <td class="${netClass(row.dealer)}">${signedNumber(row.dealer)}</td>
        <td class="${netClass(row.total)}"><strong>${signedNumber(row.total)}</strong></td>
      `;
      bindRowClick(tr, row.code);
      tbody.appendChild(tr);
    });
  } catch (err) {
    console.error(err);
    tbody.innerHTML = `<tr><td colspan='7'>載入失敗：${err.message}</td></tr>`;
  }
}

// 三大法人持股比重變化排行（投信/自營為模型估計值，僅供研究）
async function loadChangeRanking() {
  const head = document.getElementById("rankHead");
  const tbody = document.querySelector("#rankTable tbody");
  const title = document.getElementById("rankTitle");
  const subtitle = document.getElementById("rankSubtitle");

  title.textContent = "📊 三大法人持股比重變化排名";
  head.innerHTML =
    "<tr><th>#</th><th>股票</th><th>市場</th><th>持股%</th><th>ΔChange</th></tr>";
  subtitle.textContent =
    "按選定視窗之三大法人合計持股比重變化排序（投信／自營為模型估計值，僅供研究）";
  tbody.innerHTML = "<tr><td colspan='5'>載入中...</td></tr>";

  try {
    const list = await fetchJson(
      `data/top_three_inst_change_${currentWindow}_${currentSide}.json`
    );
    const filtered = applyMarketFilter(list);
    tbody.innerHTML = "";
    if (!filtered.length) {
      tbody.innerHTML = "<tr><td colspan='5'>無資料</td></tr>";
      return;
    }
    filtered.slice(0, 50).forEach((row, idx) => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>${idx + 1}</td>
        <td><span class="badge">${row.code}</span>${row.name || ""}</td>
        <td>${row.market || ""}</td>
        <td>${formatPct(row.three_inst_ratio)}</td>
        <td class="${netClass(row.change)}">${row.change >= 0 ? "+" : ""}${formatPct(row.change)}</td>
      `;
      bindRowClick(tr, row.code);
      tbody.appendChild(tr);
    });
  } catch (err) {
    console.error(err);
    tbody.innerHTML = `<tr><td colspan='5'>載入失敗：${err.message}</td></tr>`;
  }
}

// ========== Broker Functions ==========

async function loadBrokerRanking() {
  const tbody = document.querySelector("#brokerRankTable tbody");
  const updateTime = document.getElementById("brokerUpdateTime");

  if (!tbody) return;
  tbody.innerHTML = "<tr><td colspan='6'>載入中...</td></tr>";

  try {
    const data = await fetchJson("data/broker_ranking.json");
    tbody.innerHTML = "";

    if (updateTime && data.updated) {
      updateTime.textContent = `更新：${new Date(data.updated).toLocaleString("zh-TW")}`;
    }

    if (!data.data || data.data.length === 0) {
      tbody.innerHTML = "<tr><td colspan='6'>尚無券商數據</td></tr>";
      return;
    }

    data.data.slice(0, 50).forEach((row, idx) => {
      const netVol = row.total_net_vol || 0;
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>${idx + 1}</td>
        <td>${row.broker_name || ""}</td>
        <td class="${netVol > 0 ? 'net-positive' : 'net-negative'}">${formatNumber(netVol)}</td>
        <td>${row.buy_count || 0}</td>
        <td>${row.sell_count || 0}</td>
        <td>${row.stocks_traded || 0}</td>
      `;
      tbody.appendChild(tr);
    });
  } catch (err) {
    console.error(err);
    tbody.innerHTML = `<tr><td colspan='6'>載入失敗：${err.message}</td></tr>`;
  }
}

async function loadBrokerTrades() {
  const tbody = document.querySelector("#brokerTradesTable tbody");
  const status = document.getElementById("brokerTradesStatus");

  if (!tbody) return;
  tbody.innerHTML = "";
  status.textContent = "載入中...";

  try {
    const data = await fetchJson("data/broker_trades_latest.json");

    if (!data.data || data.data.length === 0) {
      status.textContent = "尚無交易數據";
      return;
    }

    status.textContent = `共 ${data.count || 0} 筆交易`;

    data.data.slice(0, 100).forEach((row) => {
      const netVol = row.net_vol || 0;
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>${row.date || ""}</td>
        <td><span class="badge">${row.stock_code}</span></td>
        <td>${row.broker_name || ""}</td>
        <td>${formatNumber(row.buy_vol || 0)}</td>
        <td>${formatNumber(row.sell_vol || 0)}</td>
        <td class="${netVol > 0 ? 'net-positive' : 'net-negative'}">${formatNumber(netVol)}</td>
        <td>${formatPct(row.pct || 0)}%</td>
      `;
      tbody.appendChild(tr);
    });
  } catch (err) {
    console.error(err);
    status.textContent = `載入失敗：${err.message}`;
  }
}

async function loadTargetBrokers() {
  const container = document.getElementById("targetBrokersContent");
  if (!container) return;

  container.innerHTML = "<p>載入中...</p>";

  try {
    const data = await fetchJson("data/target_broker_trades.json");

    if (!data.brokers || Object.keys(data.brokers).length === 0) {
      container.innerHTML = "<p>尚無目標券商數據</p>";
      return;
    }

    container.innerHTML = "";

    Object.entries(data.brokers).forEach(([brokerName, trades]) => {
      const totalNet = trades.reduce((sum, t) => sum + (t.net_vol || 0), 0);
      const netClass = totalNet > 0 ? "net-positive" : "net-negative";

      const card = document.createElement("div");
      card.className = "broker-card";
      card.innerHTML = `
        <h4>
          ${brokerName}
          <span class="${netClass}">${formatNumber(totalNet)} 張</span>
        </h4>
        <div class="trades-list">
          ${trades.slice(0, 8).map(t => {
        const sideClass = t.net_vol > 0 ? "buy-text" : "sell-text";
        return `<span class="badge">${t.stock_code}</span><span class="${sideClass}">${formatNumber(t.net_vol)}</span> `;
      }).join("")}
          ${trades.length > 8 ? `<br><small style="color:#8b8b9e">+${trades.length - 8} 筆</small>` : ""}
        </div>
      `;
      container.appendChild(card);
    });
  } catch (err) {
    console.error(err);
    container.innerHTML = `<p>載入失敗：${err.message}</p>`;
  }
}

// ========== Broker Trend Chart ==========

let brokerTrendChart = null;
let brokerTrendsData = null;

async function loadBrokerTrends() {
  const select = document.getElementById("brokerSelect");
  if (!select) return;

  try {
    brokerTrendsData = await fetchJson("data/broker_trends.json");

    if (!brokerTrendsData.brokers || Object.keys(brokerTrendsData.brokers).length === 0) {
      return;
    }

    // Populate broker select
    select.innerHTML = '<option value="ALL">全部目標券商</option>';
    Object.keys(brokerTrendsData.brokers).forEach(broker => {
      const option = document.createElement("option");
      option.value = broker;
      option.textContent = broker;
      select.appendChild(option);
    });

    // Add event listener
    select.addEventListener("change", () => {
      renderBrokerTrendChart(select.value);
    });

    // Initial render
    renderBrokerTrendChart("ALL");
  } catch (err) {
    console.error("Failed to load broker trends:", err);
  }
}

function renderBrokerTrendChart(selectedBroker) {
  const ctx = document.getElementById("brokerTrendChart");
  if (!ctx || !brokerTrendsData) return;

  // Destroy existing chart
  if (brokerTrendChart) {
    brokerTrendChart.destroy();
  }

  const brokers = brokerTrendsData.brokers;
  const datasets = [];

  // Define colors for different brokers
  const colors = [
    "#ff6b6b", "#4ecdc4", "#ffe66d", "#a55eea", "#45aaf2",
    "#fed330", "#26de81", "#fd9644", "#eb3b5a", "#2bcbba"
  ];

  let colorIndex = 0;
  let allDates = new Set();

  // Collect all dates
  Object.values(brokers).forEach(data => {
    data.forEach(d => allDates.add(d.date));
  });
  const sortedDates = Array.from(allDates).sort();

  // Build datasets
  Object.entries(brokers).forEach(([brokerName, data]) => {
    if (selectedBroker !== "ALL" && brokerName !== selectedBroker) {
      return;
    }

    // Create date -> cumulative map
    const dateMap = {};
    data.forEach(d => {
      dateMap[d.date] = d.cumulative;
    });

    // Fill in missing dates with last known value
    const values = [];
    let lastValue = 0;
    sortedDates.forEach(date => {
      if (dateMap[date] !== undefined) {
        lastValue = dateMap[date];
      }
      values.push(lastValue);
    });

    datasets.push({
      label: brokerName,
      data: values,
      borderColor: colors[colorIndex % colors.length],
      backgroundColor: "transparent",
      borderWidth: 2,
      tension: 0.3,
      pointRadius: selectedBroker === "ALL" ? 0 : 3,
    });

    colorIndex++;
  });

  brokerTrendChart = new Chart(ctx, {
    type: "line",
    data: {
      labels: sortedDates,
      datasets: datasets,
    },
    options: {
      responsive: true,
      interaction: { mode: "index", intersect: false },
      scales: {
        x: {
          ticks: { maxTicksLimit: 10, color: "#8b8b9e" },
          grid: { color: "rgba(255,255,255,0.05)" },
        },
        y: {
          title: { display: true, text: "累計買賣超 (張)", color: "#8b8b9e" },
          ticks: { color: "#8b8b9e" },
          grid: { color: "rgba(255,255,255,0.05)" },
        },
      },
      plugins: {
        legend: {
          position: "bottom",
          labels: { color: "#eaeaea", boxWidth: 12 },
        },
      },
    },
  });
}

// ========== Navigation ==========

function activateSection(targetSection) {
  const navBtns = document.querySelectorAll(".nav-btn");
  const sections = document.querySelectorAll(".section");

  navBtns.forEach((btn) => btn.classList.toggle("active", btn.dataset.section === targetSection));
  sections.forEach((section) => section.classList.toggle("active", section.id === targetSection));

  if (targetSection === "broker") {
    loadBrokerRanking();
    loadBrokerTrades();
    loadTargetBrokers();
    loadBrokerTrends();
  }
}

function openInstitutionalStock(code) {
  const input = document.getElementById("stockInput");
  if (input) input.value = code;
  activateSection("institutional");
  loadStock(code);
}

function initNavigation() {
  const navBtns = document.querySelectorAll(".nav-btn");

  navBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      activateSection(btn.dataset.section);
    });
  });
}

// ========== Initialization ==========

document.addEventListener("DOMContentLoaded", () => {
  if (window.location.protocol === "file:") {
    showDirectFileNotice();
    return;
  }

  const input = document.getElementById("stockInput");
  const btn = document.getElementById("loadBtn");
  const marketSel = document.getElementById("marketFilter");
  const windowSel = document.getElementById("windowFilter");
  const metricSel = document.getElementById("metricFilter");
  const sideSel = document.getElementById("sideFilter");
  const logCb = document.getElementById("logScaleCheckbox");
  const showForeign = document.getElementById("showForeign");
  const showTrust = document.getElementById("showTrust");
  const showDealer = document.getElementById("showDealer");
  const showTotal = document.getElementById("showTotal");

  btn.addEventListener("click", () => loadStock(input.value));
  input.addEventListener("keyup", (e) => {
    if (e.key === "Enter") loadStock(input.value);
  });

  marketSel.addEventListener("change", () => {
    marketFilter = marketSel.value;
    loadRanking();
  });

  windowSel.addEventListener("change", () => {
    currentWindow = parseInt(windowSel.value, 10);
    loadRanking();
  });

  metricSel.addEventListener("change", () => {
    currentMetric = metricSel.value;
    loadRanking();
  });

  sideSel.addEventListener("change", () => {
    currentSide = sideSel.value;
    loadRanking();
  });

  logCb.addEventListener("change", () => {
    useLogScale = logCb.checked;
    loadStock(input.value || "2330");
  });

  [showForeign, showTrust, showDealer, showTotal].forEach((cb) => {
    cb.addEventListener("change", () => loadStock(input.value || "2330"));
  });

  // Initialize navigation
  initNavigation();

  // Load initial data
  input.value = "2330";
  loadDailyRadar();
  loadStock("2330");
  loadRanking();
});
