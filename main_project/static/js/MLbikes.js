/**
 * Stations map — bike prediction UI for Google Maps InfoWindows (MLbikes.js).
 * Expects: #stations-app with data-predict-range (default /api/bikes/predict), global Chart.js.
 *
 * Request: GET /api/bikes/predict?number=<id>
 *   (<id> from station.station_id or station.number)
 *
 * Response JSON (teammate contract):
 *   {
 *     "number": 42,
 *     "times": ["2024-02-25 09:00", "2024-02-25 10:00", ...],
 *     "predicted_bikes": [12, 15, 14, ...],
 *     "predicted_stands": [21, 18, 19, ...]
 *   }
 * Arrays must be the same length; `number` should match the requested station (optional check).
 */
(function (global) {
  "use strict";

  const APP_ROOT_ID = "stations-app";
  const PREDICT_HOURS = 6;

  let iwBikesChart = null;
  let iwStandsChart = null;

  function getAppRoot() {
    return document.getElementById(APP_ROOT_ID);
  }

  function getPredictRangeUrl() {
    const root = getAppRoot();
    const u = (root && root.dataset.predictRange) || "/api/bikes/predict";
    return String(u).trim() || "/api/bikes/predict";
  }

  /** Shorten "YYYY-MM-DD HH:mm" for chart X axis inside narrow InfoWindow. */
  function chartLabelsFromTimes(times) {
    if (!Array.isArray(times)) return [];
    const strs = times.map((t) => String(t));
    const datePrefixes = strs.map((s) => (s.length >= 10 ? s.slice(0, 10) : ""));
    const sameDay =
      datePrefixes.length > 0 && datePrefixes.every((d) => d === datePrefixes[0]);
    return strs.map((s) => {
      const timePart = s.length >= 16 ? s.slice(11, 16) : s;
      if (sameDay && timePart.length === 5) return timePart;
      if (s.length >= 16) return s.slice(5, 10) + " " + timePart;
      return s;
    });
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
      `<strong>${escapeHtml(station.name)}</strong>` +
      `<div class="iw-avail">` +
      `<span style="color:#16a34a">🚲 ${bikes} bikes</span>` +
      `<span style="color:#2563eb">🅿 ${stands} stands</span>` +
      `</div>` +
      (status ? `<div class="iw-status">${status}</div>` : "") +
      `<button type="button" class="iw-more-btn">More information</button>` +
      `<div class="iw-charts" hidden>` +
      `<p class="iw-charts-title">Next ${PREDICT_HOURS} hours (predicted)</p>` +
      `<div class="iw-chart-wrap"><canvas class="iw-canvas-bikes" aria-label="Predicted bikes"></canvas></div>` +
      `<div class="iw-chart-wrap"><canvas class="iw-canvas-stands" aria-label="Predicted stands"></canvas></div>` +
      `<p class="iw-charts-error" hidden></p>` +
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

  function iwChartBaseOptions(yTitle, fullTimesForTooltip) {
    const fullTimes = Array.isArray(fullTimesForTooltip)
      ? fullTimesForTooltip
      : null;
    return {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: true,
          labels: { boxWidth: 10, font: { size: 10 } },
        },
        tooltip: {
          callbacks: {
            title(items) {
              if (!items || !items.length) return "";
              const i = items[0].dataIndex;
              if (fullTimes && fullTimes[i] != null) return String(fullTimes[i]);
              return items[0].label || "";
            },
          },
        },
      },
      scales: {
        x: {
          title: { display: true, text: "Time", font: { size: 10 } },
          ticks: { maxRotation: 50, font: { size: 9 } },
        },
        y: {
          beginAtZero: true,
          title: { display: true, text: yTitle, font: { size: 10 } },
          ticks: { font: { size: 9 } },
        },
      },
    };
  }

  function drawIwBikesChart(canvas, labels, predictedBikes, fullTimes) {
    if (typeof Chart === "undefined") return;
    if (iwBikesChart) iwBikesChart.destroy();
    iwBikesChart = new Chart(canvas.getContext("2d"), {
      type: "bar",
      data: {
        labels,
        datasets: [
          {
            label: "Predicted bikes",
            data: predictedBikes,
            backgroundColor: "rgba(22, 163, 74, 0.65)",
            borderWidth: 1,
          },
        ],
      },
      options: iwChartBaseOptions("Bikes", fullTimes),
    });
  }

  function drawIwStandsChart(canvas, labels, predictedStands, fullTimes) {
    if (typeof Chart === "undefined") return;
    if (iwStandsChart) iwStandsChart.destroy();
    iwStandsChart = new Chart(canvas.getContext("2d"), {
      type: "bar",
      data: {
        labels,
        datasets: [
          {
            label: "Predicted stands",
            data: predictedStands,
            backgroundColor: "rgba(37, 99, 235, 0.55)",
            borderWidth: 1,
          },
        ],
      },
      options: iwChartBaseOptions("Stands", fullTimes),
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

      const q = new URLSearchParams({ number: sid });
      const sep = predictUrl.indexOf("?") >= 0 ? "&" : "?";

      fetch(predictUrl + sep + q.toString())
        .then((res) => {
          if (!res.ok) throw new Error("bad status");
          return res.json();
        })
        .then((data) => {
          const times = data.times;
          const bikes = data.predicted_bikes;
          const stands = data.predicted_stands;
          if (
            !Array.isArray(times) ||
            !Array.isArray(bikes) ||
            !Array.isArray(stands)
          ) {
            throw new Error("bad payload");
          }
          if (
            data.number != null &&
            String(data.number).trim() !== sid
          ) {
            console.warn(
              "StationML: API returned number=",
              data.number,
              "but requested number=",
              sid
            );
          }
          const labels = chartLabelsFromTimes(times);
          chartsWrap.hidden = false;
          errEl.hidden = true;
          requestAnimationFrame(() => {
            requestAnimationFrame(() => {
              const cBikes = el.querySelector(".iw-canvas-bikes");
              const cStands = el.querySelector(".iw-canvas-stands");
              destroyIwCharts();
              if (cBikes) drawIwBikesChart(cBikes, labels, bikes, times);
              if (cStands) drawIwStandsChart(cStands, labels, stands, times);
              chartsWrap.dataset.loaded = "1";
              setMoreButtonLabel(btn, true, true);
            });
          });
        })
        .catch(() => {
          chartsWrap.hidden = false;
          errEl.textContent = "Could not load predictions.";
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
