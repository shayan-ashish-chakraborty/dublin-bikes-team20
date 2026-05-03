/**
 * Stations map — bike prediction UI for Google Maps InfoWindows (MLbikes.js).
 * Expects: #stations-app with data-predict-range (default /api/stations/predict), global Chart.js.
 *
 * Request: GET /api/stations/predict?number=<id>&hours=48
 * (Backend: station_predict_from_request — batched weather + batched bike/dock models)
 *
 * Response JSON:
 *   {
 *     "number": 42,
 *     "times": ["2024-02-25 09:00", ...],
 *     "predicted_bikes": [12, 15, ...],
 *     "predicted_docks": [21, 18, ...]
 *   }
 */
(function (global) {
  "use strict";

  const APP_ROOT_ID = "stations-app";
  const JOURNEY_APP_ID = "app";
  const PREDICT_HOURS = 48;

  let iwBikesChart = null;
  let iwStandsChart = null;
  // Cache predictions per station to avoid repeat network requests.
  // Key: station id (string) → value: { times, bikes, stands, fetchedAtMs }
  const _predictionCache = new Map();
  const CACHE_TTL_MS = 5 * 60 * 1000; // 5 minutes

  function getAppRoot() {
    return (
      document.getElementById(APP_ROOT_ID) ||
      document.getElementById(JOURNEY_APP_ID)
    );
  }

  function getPredictRangeUrl() {
    const root = getAppRoot();
    const u = (root && root.dataset.predictRange) || "/api/stations/predict";
    return String(u).trim() || "/api/stations/predict";
  }

  /**
   * Hourly series: show at most `max` x labels, every 8 hours (0, 8, 16, …).
   * 48 points → six labels at 8h spacing; 5 gaps × 8h = 40h from first to last label.
   */
  function _xTickIndices(n, max) {
    if (n <= 0) return [];
    const cap = Math.min(n, Math.max(4, max));
    if (n <= cap) return Array.from({ length: n }, (_, i) => i);
    const stepHours = 8;
    const indices = [];
    for (let i = 0; i < n && indices.length < cap; i += stepHours) {
      indices.push(i);
    }
    return indices;
  }

  /**
   * Short X-axis labels for narrow InfoWindow + ~6 ticks at 8h steps (rest blank).
   */
  function chartLabelsFromTimes(times) {
    if (!Array.isArray(times)) return [];
    const strs = times.map((t) => String(t));
    const datePrefixes = strs.map((s) => (s.length >= 10 ? s.slice(0, 10) : ""));
    const sameDay =
      datePrefixes.length > 0 && datePrefixes.every((d) => d === datePrefixes[0]);
    const shortEach = strs.map((s) => {
      const timePart = s.length >= 16 ? s.slice(11, 16) : s;
      if (sameDay && timePart.length === 5) return timePart;
      // Cross-day: "MM-DD HH:mm" → "4/10 22:30" (shorter than "04-10 22:30")
      if (s.length >= 16) {
        const mo = parseInt(s.slice(5, 7), 10);
        const da = parseInt(s.slice(8, 10), 10);
        if (Number.isFinite(mo) && Number.isFinite(da)) {
          return `${mo}/${da} ${timePart}`;
        }
        return s.slice(5, 10) + " " + timePart;
      }
      return s;
    });
    const n = shortEach.length;
    const tickIdx = new Set(_xTickIndices(n, 6));
    return shortEach.map((label, i) => (tickIdx.has(i) ? label : ""));
  }

  function escapeHtml(s) {
    if (s == null) return "";
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function stationIwRootId(station) {
    const raw = station && station.number != null ? station.number : 0;
    const n = parseInt(String(raw), 10);
    return "iw-st-" + (Number.isFinite(n) ? n : 0);
  }

  function stationInfoHtml(station) {
    const bikes = station.available_bikes ?? 0;
    const stands =
      station.available_stands ?? station.available_bike_stands ?? 0;
    const status = station.status ? escapeHtml(station.status) : "";
    const rootId = stationIwRootId(station);
    return (
      `<div class="gm-iw" id="${rootId}">` +
      `<div class="gm-iw-inner">` +
      `<strong>${escapeHtml(station.name)}</strong>` +
      `<div class="iw-avail">` +
      `<span class="iw-tag iw-tag-bikes">🚲 ${bikes} bikes</span>` +
      `<span class="iw-tag iw-tag-stands">🅿 ${stands} stands</span>` +
      `</div>` +
      (status ? `<div class="iw-status">${status}</div>` : "") +
      `<button type="button" class="iw-more-btn">More information</button>` +
      `<div class="iw-charts" hidden>` +
      `<p class="iw-charts-title">Next ${PREDICT_HOURS} hours — predicted</p>` +
      `<p class="iw-chart-subtitle">Bikes</p>` +
      `<div class="iw-chart-wrap iw-chart-wrap-line"><canvas class="iw-canvas-bikes" aria-label="Predicted bikes"></canvas></div>` +
      `<p class="iw-chart-subtitle">Stands</p>` +
      `<div class="iw-chart-wrap iw-chart-wrap-line"><canvas class="iw-canvas-stands" aria-label="Predicted stands"></canvas></div>` +
      `<p class="iw-charts-error" hidden></p>` +
      `</div>` +
      `</div>` +
      `</div>`
    );
  }

  function destroyIwCharts() {
    if (iwBikesChart) {
      iwBikesChart.destroy();
      iwBikesChart = null;
    }
    if (iwStandsChart) {
      iwStandsChart.destroy();
      iwStandsChart = null;
    }
  }

  function lineChartOptions(yTitle, fullTimesForTooltip) {
    const full = Array.isArray(fullTimesForTooltip) ? fullTimesForTooltip : null;
    return {
      responsive: true,
      maintainAspectRatio: false,
      layout: {
        padding: { bottom: 8, left: 2, right: 2, top: 2 },
      },
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            title(items) {
              if (!items || !items.length) return "";
              const i = items[0].dataIndex;
              if (full && full[i] != null) return String(full[i]);
              return items[0].label || "";
            },
            label(context) {
              const v = context.parsed.y;
              const n = Number.isFinite(v) ? Math.round(v) : v;
              const name = context.dataset.label || "";
              return name ? `${name}: ${n}` : String(n);
            },
          },
        },
      },
      scales: {
        x: {
          title: { display: true, text: "Time", font: { size: 10 } },
          ticks: {
            minRotation: 45,
            maxRotation: 45,
            autoSkip: false,
            font: { size: 8 },
          },
        },
        y: {
          beginAtZero: true,
          title: { display: true, text: yTitle, font: { size: 10 } },
          ticks: {
            font: { size: 9 },
            callback(value) {
              return Number.isFinite(value) ? Math.round(value) : value;
            },
          },
        },
      },
    };
  }

  function drawIwBikesLineChart(canvas, labels, predictedBikes, fullTimes) {
    if (typeof Chart === "undefined") return;
    if (iwBikesChart) iwBikesChart.destroy();
    iwBikesChart = new Chart(canvas.getContext("2d"), {
      type: "line",
      data: {
        labels,
        datasets: [
          {
            label: "Bikes",
            data: predictedBikes,
            borderColor: "rgb(22, 163, 74)",
            backgroundColor: "rgba(22, 163, 74, 0.12)",
            borderWidth: 2,
            fill: false,
            tension: 0.25,
            pointRadius: 0,
            pointHitRadius: 6,
          },
        ],
      },
      options: lineChartOptions("Bikes", fullTimes),
    });
  }

  function drawIwStandsLineChart(canvas, labels, predictedStands, fullTimes) {
    if (typeof Chart === "undefined") return;
    if (iwStandsChart) iwStandsChart.destroy();
    iwStandsChart = new Chart(canvas.getContext("2d"), {
      type: "line",
      data: {
        labels,
        datasets: [
          {
            label: "Stands",
            data: predictedStands,
            borderColor: "rgb(37, 99, 235)",
            backgroundColor: "rgba(37, 99, 235, 0.1)",
            borderWidth: 2,
            fill: false,
            tension: 0.25,
            pointRadius: 0,
            pointHitRadius: 6,
          },
        ],
      },
      options: lineChartOptions("Stands", fullTimes),
    });
  }

  function setMoreButtonLabel(btn, chartsVisible, loaded) {
    if (!btn) return;
    if (!loaded) {
      btn.textContent = "More information";
      return;
    }
    btn.textContent = chartsVisible ? "Hide charts" : "Show charts";
  }

  function setupInfoWindowPrediction(station) {
    const rootId = stationIwRootId(station);
    const el = document.getElementById(rootId);
    if (!el) return;
    const btn = el.querySelector(".iw-more-btn");
    const chartsWrap = el.querySelector(".iw-charts");
    const errEl = el.querySelector(".iw-charts-error");
    if (!btn || !chartsWrap || !errEl) return;

    const predictUrl = getPredictRangeUrl();

    btn.addEventListener("click", () => {
      if (typeof Chart === "undefined") {
        chartsWrap.hidden = false;
        errEl.textContent = "Chart library failed to load.";
        errEl.hidden = false;
        return;
      }

      if (chartsWrap.dataset.loaded === "1") {
        chartsWrap.hidden = !chartsWrap.hidden;
        setMoreButtonLabel(btn, !chartsWrap.hidden, true);
        return;
      }

      if (chartsWrap.dataset.loading === "1") return;
      chartsWrap.dataset.loading = "1";
      btn.disabled = true;
      errEl.hidden = true;

      const sidRaw =
        station.station_id != null ? station.station_id : station.number;
      const sid = sidRaw != null ? String(sidRaw).trim() : "";
      if (!sid) {
        chartsWrap.hidden = false;
        errEl.textContent = "Missing station number for this station.";
        errEl.hidden = false;
        btn.disabled = false;
        chartsWrap.dataset.loading = "0";
        return;
      }

      const cached = _predictionCache.get(sid);
      const render = (times, bikes, stands) => {
        const labels = chartLabelsFromTimes(times);
        chartsWrap.hidden = false;
        errEl.hidden = true;
        requestAnimationFrame(() => {
          requestAnimationFrame(() => {
            const cBikes = el.querySelector(".iw-canvas-bikes");
            const cStands = el.querySelector(".iw-canvas-stands");
            destroyIwCharts();
            if (cBikes) drawIwBikesLineChart(cBikes, labels, bikes, times);
            if (cStands) drawIwStandsLineChart(cStands, labels, stands, times);
            chartsWrap.dataset.loaded = "1";
            setMoreButtonLabel(btn, true, true);
          });
        });
      };

      const nowMs = Date.now();
      const cacheFresh =
        cached &&
        Array.isArray(cached.times) &&
        typeof cached.fetchedAtMs === "number" &&
        nowMs - cached.fetchedAtMs < CACHE_TTL_MS;

      if (cacheFresh) {
        render(cached.times, cached.bikes, cached.stands);
        btn.disabled = false;
        chartsWrap.dataset.loading = "0";
        return;
      }

      const q = new URLSearchParams({ number: sid, hours: String(PREDICT_HOURS) });
      const sep = predictUrl.indexOf("?") >= 0 ? "&" : "?";

      fetch(predictUrl + sep + q.toString())
        .then(async (res) => {
          const data = await res.json().catch(() => ({}));
          if (!res.ok) {
            const msg = data.error || data.message || "bad status";
            throw new Error(msg);
          }
          return data;
        })
        .then((data) => {
          const times = data.times;
          const bikes = data.predicted_bikes;
          const stands = data.predicted_stands ?? data.predicted_docks;
          if (!Array.isArray(times) || !Array.isArray(bikes) || !Array.isArray(stands)) {
            throw new Error("bad payload");
          }
          if (data.number != null && String(data.number).trim() !== sid) {
            console.warn("StationML: API returned number=", data.number, "but requested number=", sid);
          }
          _predictionCache.set(sid, { times, bikes, stands, fetchedAtMs: Date.now() });
          render(times, bikes, stands);
        })
        .catch((e) => {
          chartsWrap.hidden = false;
          errEl.textContent =
            typeof e.message === "string" && e.message
              ? e.message
              : "Could not load predictions.";
          errEl.hidden = false;
        })
        .finally(() => {
          btn.disabled = false;
          chartsWrap.dataset.loading = "0";
        });
    });
  }

  global.StationML = {
    PREDICT_HOURS,
    destroyIwCharts,
    stationInfoHtml,
    setupInfoWindowPrediction,
  };
})(typeof window !== "undefined" ? window : this);
