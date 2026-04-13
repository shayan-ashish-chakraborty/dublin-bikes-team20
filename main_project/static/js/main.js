/**
 * main.js — Shared js file  (Shayan)
 * This file is loaded by base.html on EVERY page of the app.
 * It runs automatically when the page loads — no setup needed
 * in individual page templates.
 *
 * WHAT THIS FILE DOES:
 
 * 1. FOOTER YEAR
 *    Sets #footer-year to the current year automatically.
 *
 * 2. NAVBAR WEATHER CHIP  (#hdr-temp)
 *    Fetches the current temperature and shows it in the navbar.
 *    Primary:  GET /api/weather/db/current  (our MySQL DB)
 *    Fallback: Open-Meteo free public API   (no key needed)
 *
 * 3. HOME PAGE WEATHER STRIP
 *    Fills #hw-temp, #hw-feels, #hw-hum, #hw-wind on index.html.
 *    Only runs if those elements exist on the page (index.html).
 *
 * 4. AI CHATBOT
 *    Opens/closes the chatbot panel, sends messages to the
 *    Google Gemini API, and renders replies as chat bubbles.
 *    API KEY: The chatbot calls the Google API directly
 *      from the browser. You need to configure an API key
 *      on the Google side (or a proxy). Currently uses
 *      'google-dangerous-direct-browser-access' header for
 *      direct browser access (acceptable for prototyping only).
 *
 * 5. WEATHER PAGE  (#wx-temp)
 *    All logic for weather.html: utility helpers, Chart.js chart
 *    builders, data loading (OpenWeather → DB fallback), rendering,
 *    and 5-minute auto-refresh. Runs only on /weather.
 *    Wrapped in window.addEventListener('load') so Chart.js (loaded
 *    via {% block extra_js %} in weather.html) is available first.
 *
 *  TO ADD NEW SHARED BEHAVIOUR (runs on every page):
 *   Add your code at the bottom of this file.
 *   To run code only on a specific page, check for a unique
 *   element first:
 *     const el = document.getElementById('my-unique-id');
 *     if (!el) return;  // skip on other pages
 */
 
 
// 1. FOOTER YEAR 
// Finds #footer-year (in base.html footer) and sets it to today's year.
const _d    = new Date();
const el_yr = document.getElementById('footer-year');
if (el_yr) el_yr.textContent = _d.getFullYear();
 
 
//  2. NAVBAR WEATHER CHIP 
// Updates the temperature shown in the top-right weather chip on
// every page. Fails silently if the chip element isn't found.
(async function () {
  const chip = document.getElementById('hdr-temp');
  if (!chip) return;
 
  try {
    // live API via backend proxy (freshest reading)
    const res2 = await fetch('/api/weather/openweather/current').then(r => r.json());
    const w = res2.weather;
    if (w?.temp !== undefined) {
      chip.textContent = Math.round(w.temp) + '°C';
      return;
    }
  } catch (_) {}
 
  try {
    // fallback: our own database
    const res = await fetch('/api/weather/db/current?limit=1').then(r => r.json());
    const row = res.weather?.[0];
    if (row?.temp !== undefined) {
      chip.textContent = Math.round(row.temp) + '°C';
      return;
    }
  } catch (_) {}
})();
 
 
// 3. HOME PAGE WEATHER STRIP 
// Only runs on index.html (checks for #hw-temp first).
// Fills the four weather stat values in the weather strip section.
// If we want add more stat IDs to index.html, fill them here. 
(async function () {
  const el = document.getElementById('hw-temp');
  if (!el) return; // not on the home page — skip
 
  try {
    const res2 = await fetch('/api/weather/openweather/current').then(r => r.json());
    const w = res2.weather;
    if (w?.temp !== undefined) {
      document.getElementById('hw-temp').textContent   = Math.round(w.temp)        + '°C';
      document.getElementById('hw-feels').textContent  = Math.round(w.feels_like)  + '°C';
      document.getElementById('hw-hum').textContent    = Math.round(w.humidity)    + '%';
      document.getElementById('hw-wind').textContent   = (+w.wind_speed).toFixed(1) + ' m/s';
      return;
    }
  } catch (_) {}
 
  try {
    const res = await fetch('/api/weather/db/current?limit=1').then(r => r.json());
    const row = res.weather?.[0];
    if (row?.temp !== undefined) {
      document.getElementById('hw-temp').textContent   = Math.round(row.temp)         + '°C';
      document.getElementById('hw-feels').textContent  = Math.round(row.feels_like)   + '°C';
      document.getElementById('hw-hum').textContent    = row.humidity                 + '%';
      document.getElementById('hw-wind').textContent   = (+row.wind_speed).toFixed(1) + ' m/s';
      return;
    }
  } catch (_) {}
})();
 
 
 
// 4. AI CHATBOT 
// Self-contained IIFE so chatbot variables don't pollute global scope.
// All chatbot HTML is in base.html (chatbot-fab, chatbot-panel, etc.)
(function () {
  const fab   = document.getElementById('chatbot-fab');
  const panel = document.getElementById('chatbot-panel');
  const close = document.getElementById('chat-close');
  const input = document.getElementById('chat-input');
  const send  = document.getElementById('chat-send');
  const msgs  = document.getElementById('chat-messages');
  if (!fab) return; // chatbot HTML not present — skip
 
  // Open / close chatbot panel
  fab.addEventListener('click', () => {
    panel.classList.toggle('visible');
    if (panel.classList.contains('visible')) input.focus();
  });
  close.addEventListener('click', () => panel.classList.remove('visible'));
 
  // Send on Enter key or send button click
  input.addEventListener('keydown', e => { if (e.key === 'Enter') sendMsg(); });
  send.addEventListener('click', sendMsg);
 
  // Conversation history — sent with each message so Claude has context.
  // Grows throughout the session (cleared on page refresh).
  const history = [];
 
  // System prompt — defines the chatbot's persona and knowledge scope.
  const SYSTEM =
    'You are a helpful assistant for Dublin Bike Share. ' +
    'Help with finding stations, cycling routes, weather tips, and pricing (€35/year, first 30 min free). ' +
    'Keep replies short and friendly. Use emojis occasionally.';
 
  /**
   * Sends a message to the Gemini API and renders the reply.
   * @param {string} [text] - optional text override (used by chip buttons)
   */
  async function sendMsg(text) {
    const msg = (text || input.value).trim();
    if (!msg) return;
 
    input.value = '';
    document.getElementById('chat-chips').style.display = 'none'; // hide suggestion chips after first message
    send.disabled = input.disabled = true;
 
    addBubble('user', msg);
    history.push({ role: 'user', content: msg });
    const typing = addTyping(); // show "..." animation while waiting
 
    try {
      // POST to our backend proxy endpoint (no API key in browser)
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          systemInstruction: SYSTEM,
          messages: history,
        }),
      });
 
      if (!res.ok) {
        const err = await res.text();
        throw new Error(`Chat endpoint error: ${res.status} ${err}`);
      }
 
      typing.remove();
      const data = await res.json();
      const reply = data.reply || "Sorry, couldn't get a response.";
      history.push({ role: 'assistant', content: reply });
      addBubble('bot', reply);
    } catch (error) {
      typing.remove();
      console.error('Chatbot error:', error);
      addBubble('bot', 'Chatbot not connected. Check server logs and GEMINI_API_KEY.');
    }
 
    send.disabled = input.disabled = false;
    input.focus();
  }
 
  // sendSuggestion is called by the chip buttons in base.html:
  //   <button onclick="sendSuggestion(this)">Best time to cycle?</button>
  // Must be on window so the inline handler can find it.
  window.sendSuggestion = btn => sendMsg(btn.textContent.trim());
 
  /** Creates and appends a chat bubble div to #chat-messages. */
  function addBubble(role, text) {
    const div = document.createElement('div');
    div.className = 'chat-msg ' + role;
    div.innerHTML = `<div class="chat-bubble">${text.replace(/\n/g, '<br>')}</div>`;
    msgs.appendChild(div);
    msgs.scrollTop = msgs.scrollHeight; // auto-scroll to latest message
    return div;
  }
 
  /** Creates and appends the animated "..." typing indicator. */
  function addTyping() {
    const div = document.createElement('div');
    div.className = 'chat-msg bot';
    div.innerHTML = `<div class="chat-bubble">
      <div class="chat-dots">
        <div class="chat-dot"></div>
        <div class="chat-dot"></div>
        <div class="chat-dot"></div>
      </div>
    </div>`;
    msgs.appendChild(div);
    msgs.scrollTop = msgs.scrollHeight;
    return div;
  }
})();
 
 
// 5. WEATHER PAGE 
// Self-contained IIFE — only runs on weather.html (guards on #wx-temp).
// Wrapped in window 'load' event so Chart.js (from the CDN <script> tag in
// weather.html's {% block extra_js %}) is guaranteed to be parsed and ready.
//
// Function map:
//   parseInstant(ts)            → normalises unix / ISO timestamps → Date
//   fmtTime(ts)                 → "HH:MM AM/PM" in Europe/Dublin
//   fmtDT(ts)                   → "Mon 31 Mar HH:MM AM/PM" in Europe/Dublin
//   cyclingScore(t,w,r)         → 0-100 score from temp / wind / rain
//   cyclingLabel(score)         → { label, color } for the score band
//   guessCondition(t,r)         → plain-text condition label
//   conditionIconHtml(cond)     → <span> with <img> from #wx-icon-map paths
//   buildTempChart(...)         → draws / redraws the 40-h temp line chart
//   buildRainChart(...)         → draws / redraws the rain bar chart
//   buildTemp7Chart(...)        → draws / redraws the 7-step mini chart
//   fetchCurrentWeatherRow()    → fetches current row (used for "Now" point)
//   rainMmPerHFromHourlyRow(r)  → normalises rain_3h / rain_1h → mm/h
//   rowTimeMs(r)                → ms for a forecast row
//   forecastSlotKey(tMs)        → aligns to ~3h slots for dedup
//   mergeHourlyPreferDb(...)    → merges DB + API rows, DB preferred per slot
//   loadCurrent()               → fetches current, calls renderCurrent()
//   renderCurrent(...)          → fills all stat spans in the left card
//   loadHourly(currentRow)      → fills right card + both full-width charts
//   refreshWeather()            → loadCurrent then loadHourly; runs on load
//                                 + every 5 minutes
//
// Data sources (in priority order):
//   1. /api/weather/openweather/current    (live API via backend proxy)
//   2. /api/weather/db/current             (local DB fallback)
window.addEventListener('load', function () {
  if (!document.getElementById('wx-temp')) return; // not on the weather page — skip
 
  // Read server-rendered icon paths from the hidden #wx-icon-map element.
  // These are set by Jinja url_for() in weather.html and cannot live in a
  // plain .js file.
  const _iconMap = document.getElementById('wx-icon-map').dataset;
  const WX_COND_ICON_SRC = {
    'Heavy Rain':   _iconMap.heavyRain,
    'Light Rain':   _iconMap.lightRain,
    'Freezing':     _iconMap.freezing,
    'Cold':         _iconMap.cold,
    'Warm & Sunny': _iconMap.warmSunny,
    'Partly Cloudy':_iconMap.partlyCloudy,
  };
 
  // Chart.js instance references — destroyed and recreated on each refresh.
  let tempChart  = null;
  let rainChart  = null;
  let temp7Chart = null;
 
  // ── UTILITY FUNCTIONS ────────────────────────────────────────────────────
 
  // Parses DB ISO strings (Europe/Dublin offset from API), unix seconds, or legacy GMT strings.
  function parseInstant(ts) {
    if (ts == null || ts === '') return new Date(NaN);
    if (typeof ts === 'number' && Number.isFinite(ts)) return new Date(ts * 1000);
    return new Date(ts);
  }
 
  // Converts a timestamp (Unix seconds or ISO string) to "HH:MM AM/PM" in Europe/Dublin
  function fmtTime(ts) {
    const d = parseInstant(ts);
    return d.toLocaleTimeString('en-IE', {
      hour: '2-digit',
      minute: '2-digit',
      hour12: true,
      timeZone: 'Europe/Dublin',
    });
  }
 
  // Converts a timestamp to "Mon 31 Mar HH:MM AM/PM" (Dublin)
  function fmtDT(ts) {
    const d = parseInstant(ts);
    return (
      d.toLocaleDateString('en-IE', {
        weekday: 'short',
        day: 'numeric',
        month: 'short',
        timeZone: 'Europe/Dublin',
      }) +
      ' ' +
      fmtTime(ts)
    );
  }
 
  // Calculates a cycling suitability score (0–100) from weather values.
  // Deductions: cold temps, high wind, rain.
  // Adjust the thresholds here if you want to tune the scoring.
  function cyclingScore(temp, wind, rain) {
    let s = 100;
    if (temp < 5) s -= 40; else if (temp < 10) s -= 20; else if (temp < 15) s -= 5;
    if (temp > 28) s -= 20;
    if (wind > 10) s -= 20; else if (wind > 7) s -= 10; else if (wind > 5) s -= 5;
    if (rain > 2) s -= 40; else if (rain > 0.5) s -= 25; else if (rain > 0) s -= 10;
    return Math.max(0, Math.min(100, s));
  }
 
  // Returns a label + colour for the cycling score band.
  function cyclingLabel(score) {
    if (score >= 80) return { label: 'Excellent', color: '#007A33' };
    if (score >= 60) return { label: 'Good',      color: '#5a9e00' };
    if (score >= 40) return { label: 'Fair',       color: '#e6bc00' };
    if (score >= 20) return { label: 'Poor',       color: '#e07b00' };
    return                  { label: 'Bad',        color: '#c0392b' };
  }
 
  // Returns a plain-text weather condition label from temp + rain.
  function guessCondition(temp, rain) {
    if (rain > 2)   return 'Heavy Rain';
    if (rain > 0.5) return 'Light Rain';
    if (temp < 2)   return 'Freezing';
    if (temp < 8)   return 'Cold';
    if (temp > 22)  return 'Warm & Sunny';
    return                 'Partly Cloudy';
  }
 
  // Returns an icon <span> for the given condition label.
  // Icon src values come from WX_COND_ICON_SRC (read from #wx-icon-map above).
  function conditionIconHtml(cond) {
    const src = WX_COND_ICON_SRC[cond] || WX_COND_ICON_SRC['Partly Cloudy'];
    const esc = String(cond).replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;');
    return `<span class="h-cond h-cond-icon" title="${esc}" aria-label="${esc}">
      <img src="${src}" alt="" width="24" height="24" class="h-cond-img" decoding="async" role="presentation">
    </span>`;
  }
 
  // ── CHART BUILDERS ───────────────────────────────────────────────────────
 
  // Draws (or redraws) the 40-hour temperature line chart.
  // labels = array of time strings, temps/feels = arrays of °C values.
  function buildTempChart(labels, temps, feels) {
    const ctx = document.getElementById('tempChart').getContext('2d');
    if (tempChart) tempChart.destroy(); // destroy old chart before redrawing
    tempChart = new Chart(ctx, {
      type: 'line',
      data: {
        labels,
        datasets: [
          { label: 'Temp (°C)',       data: temps, borderColor: '#007A33', backgroundColor: 'rgba(0,122,51,0.08)', borderWidth: 2, fill: true, tension: 0.4, pointRadius: 2 },
          { label: 'Feels Like (°C)', data: feels, borderColor: '#FFD100', borderWidth: 2, borderDash: [5,4], tension: 0.4, pointRadius: 0 }
        ]
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: true } },
        scales: { y: { ticks: { callback: v => v + '°C' } } }
      }
    });
  }
 
  function buildRainChart(labels, rainMmPerH) {
    const el = document.getElementById('rainChart');
    if (!el) return;
    const ctx = el.getContext('2d');
    if (rainChart) rainChart.destroy();
    rainChart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels,
        datasets: [
          { label: 'Rain (mm/h)', data: rainMmPerH, backgroundColor: 'rgba(0,122,51,0.25)', borderColor: '#007A33', borderWidth: 1 }
        ]
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: true } },
        scales: {
          y: { beginAtZero: true, ticks: { callback: v => v + ' mm' } }
        }
      }
    });
  }
 
  function buildTemp7Chart(labels, temps) {
    const el = document.getElementById('temp7Chart');
    if (!el) return;
    const ctx = el.getContext('2d');
    if (temp7Chart) temp7Chart.destroy();
    temp7Chart = new Chart(ctx, {
      type: 'line',
      data: {
        labels,
        datasets: [
          { label: 'Temp (°C)', data: temps, borderColor: '#007A33', backgroundColor: 'rgba(0,122,51,0.08)', borderWidth: 2, fill: true, tension: 0.35, pointRadius: 2 }
        ]
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { ticks: { maxRotation: 0, autoSkip: true } },
          y: { ticks: { callback: v => v + '°C' } }
        }
      }
    });
  }
 
  // ── DATA HELPERS ─────────────────────────────────────────────────────────
 
  /** Same sources as loadCurrent — used to prepend a "Now" point on forecast charts. */
  async function fetchCurrentWeatherRow() {
    try {
      // PRIMARY: live OpenWeather API via backend proxy
      const res2 = await fetch('/api/weather/openweather/current').then(r => r.json());
      const w = res2.weather;
      if (w && w.temp !== undefined) return w;
    } catch (_) {}
    try {
      // FALLBACK: our own MySQL DB
      const res = await fetch('/api/weather/db/current?limit=1').then(r => r.json());
      const d = res.weather?.[0] ?? null;
      if (d && d.temp !== undefined) return d;
    } catch (_) {}
    return null;
  }
 
  function rainMmPerHFromHourlyRow(r) {
    const v3 = r.rain_3h;
    const v1 = r.rain_1h;
    if (v1 != null) return +(+v1).toFixed(2);
    if (v3 != null) return +((+v3) / 3).toFixed(2);
    return 0;
  }
 
  /** ms for a forecast row (OpenWeather + DB hourly shapes). */
  function rowTimeMs(r) {
    return parseInstant(r.dt ?? r.future_dt).getTime();
  }
 
  /** Align to ~OpenWeather 3h steps so DB hourly rows merge with API rows. */
  function forecastSlotKey(tMs) {
    return Math.floor(tMs / (3 * 60 * 60 * 1000));
  }
 
  /**
   * DB may return fewer than requested rows (ETL partial / stale). Merge with API:
   * same 3h slot → keep DB row; other slots → fill from API.
   */
  function mergeHourlyPreferDb(dbRows, apiRows, nowMs) {
    const skew = 60 * 1000;
    const map = new Map();
    const put = (r, fromDb) => {
      const t = rowTimeMs(r);
      if (!Number.isFinite(t) || t < nowMs - skew) return;
      const k = forecastSlotKey(t);
      const prev = map.get(k);
      if (!prev) map.set(k, { r, fromDb });
      else if (fromDb) map.set(k, { r, fromDb: true });
    };
    (apiRows || []).forEach((r) => put(r, false));
    (dbRows  || []).forEach((r) => put(r, true));
    return [...map.values()]
      .map((x) => x.r)
      .sort((a, b) => rowTimeMs(a) - rowTimeMs(b));
  }
 
  // ── DATA LOADING ─────────────────────────────────────────────────────────
 
  // Loads current weather and fills the left card.
  // Tries live OpenWeather API first; falls back to our DB.
  // Returns the row used (for loadHourly charts) or null.
  async function loadCurrent() {
    let d = null;
 
    try {
      //  PRIMARY: live OpenWeather API via backend proxy 
      const res2 = await fetch('/api/weather/openweather/current').then(r => r.json());
      const w = res2.weather;
      if (w && w.temp !== undefined) {
        renderCurrent(w.temp, w.feels_like, w.humidity, w.wind_speed, w.rain_1h ?? 0, w.dt);
        if (w.weather_desc) {
          document.getElementById('wx-cond-label').textContent = w.weather_desc
            .split(' ')
            .map(s => s ? s[0].toUpperCase() + s.slice(1) : s)
            .join(' ');
        }
        return w;
      }
    } catch(_) {}
 
    try {
      //  FALLBACK: our own MySQL DB 
      const res = await fetch('/api/weather/db/current?limit=1').then(r => r.json());
      d = res.weather?.[0] ?? null;
    } catch(_) {}
 
    if (d && d.temp !== undefined) {
      renderCurrent(d.temp, d.feels_like, d.humidity, d.wind_speed, d.rain_1h ?? 0, d.dt);
      return d;
    }
    return null;
  }
 
  // Fills all the stat spans in the "Current Conditions" card.
  function renderCurrent(temp, feels, hum, wind, rain, dt) {
    const condLabel = guessCondition(temp, rain);
    const score = cyclingScore(temp, wind, rain);
    const cl    = cyclingLabel(score);
 
    document.getElementById('wx-temp').textContent       = Math.round(temp) + '°C';
    document.getElementById('wx-cond-label').textContent  = condLabel;
    document.getElementById('wx-feels').textContent      = Math.round(feels) + '°C';
    document.getElementById('wx-hum').textContent        = Math.round(hum) + '%';
    document.getElementById('wx-wind').textContent       = (+wind).toFixed(1) + ' m/s';
    document.getElementById('wx-rain').textContent       = (+rain).toFixed(2) + ' mm';
    document.getElementById('wx-updated').textContent    = fmtDT(dt);
 
    // Cycling score elements
    document.getElementById('score-circle').textContent         = score;
    document.getElementById('score-fill').style.width           = score + '%';
    document.getElementById('score-fill').style.backgroundColor  = cl.color;
    document.getElementById('score-text').textContent           = cl.label;
    document.getElementById('score-text').style.color           = cl.color;
 
    // Also update the navbar weather chip (defined in base.html)
    const chip = document.getElementById('hdr-temp');
    if (chip) chip.textContent = Math.round(temp) + '°C';
  }
 
  // Loads hourly forecast data and fills the right card + chart + ML card.
  // When current weather is available, prepends a "Now" point to temp/rain charts.
  // Pass currentRow from loadCurrent() to avoid a duplicate API call.
  async function loadHourly(currentRow) {
    const current = currentRow != null ? currentRow : await fetchCurrentWeatherRow();
 
    const HOURLY_LIMIT = 24;
    /** If DB has fewer future rows than this after filtering, merge in OpenWeather. */
    const MIN_HOURLY_ROWS = 16;
 
    let rows = [];
    try {
      //  PRIMARY: live OpenWeather 3-hour forecast 
      const res2 = await fetch(`/api/weather/openweather/forecast3h?limit=${HOURLY_LIMIT}`).then(r => r.json());
      rows = (res2.hourly ?? []);
      if (res2.error) console.error('OpenWeather 3-hour error', res2);
    } catch(e) {
      console.error('OpenWeather 3-hour fetch failed', e);
    }
 
    if (!rows.length) {
      try {
        //  FALLBACK: our DB 
        const res = await fetch(`/api/weather/db/hourly?limit=${HOURLY_LIMIT}`).then(r => r.json());
        rows = (res.hourly ?? []);
      } catch(e) {
        console.error('DB hourly fetch failed', e);
      }
    }
 
    if (!rows.length) {
      const el = document.getElementById('hourly-list');
      if (el) el.innerHTML = `<p class="loading-msg">No hourly data available (DB empty + API failed). Check console for details.</p>`;
      return;
    }
 
    // Ensure we start from "now".
    const now = Date.now();
    const toMs = (ts) => {
      if (ts == null) return NaN;
      return parseInstant(ts).getTime();
    };
    rows = rows
      .slice()
      .sort((a, b) => toMs(a.dt ?? a.future_dt) - toMs(b.dt ?? b.future_dt))
      .filter(r => {
        const t = toMs(r.dt ?? r.future_dt);
        return Number.isFinite(t) && t >= now - 60 * 1000; // allow slight clock skew
      })
      .slice(0, HOURLY_LIMIT);
 
    if (rows.length < MIN_HOURLY_ROWS) {
      try {
        const res3 = await fetch(`/api/weather/db/hourly?limit=${HOURLY_LIMIT}`).then(r => r.json());
        const dbRows = res3.hourly ?? [];
        if (dbRows.length) {
          // API rows are preferred per 3h slot
          rows = mergeHourlyPreferDb(rows, dbRows, now)
            .filter((r) => {
              const t = toMs(r.dt ?? r.future_dt);
              return Number.isFinite(t) && t >= now - 60 * 1000;
            })
            .slice(0, HOURLY_LIMIT);
        }
      } catch (e) {
        console.error('DB merge for sparse API rows failed', e);
      }
    }
 
    if (!rows.length) {
      const el = document.getElementById('hourly-list');
      if (el) el.innerHTML = `<p class="loading-msg">No future hourly points available.</p>`;
      return;
    }
 
    const stripN = current && current.temp != null ? 6 : 7;
    const stripForecast = rows.slice(0, stripN);
 
    if (current && current.temp != null) {
      const t0 = +Number(current.temp).toFixed(1);
      buildTemp7Chart(
        ['Now', ...stripForecast.map(r => fmtTime(r.dt ?? r.future_dt))],
        [t0, ...stripForecast.map(r => (r.temp != null ? +(+r.temp).toFixed(1) : null))]
      );
    } else {
      buildTemp7Chart(
        rows.slice(0, 7).map(r => fmtTime(r.dt ?? r.future_dt)),
        rows.slice(0, 7).map(r => (r.temp != null ? +(+r.temp).toFixed(1) : null))
      );
    }
 
    function hourRowHtml(r) {
      const rain = r.rain_3h ?? r.rain_1h ?? 0;
      const score = cyclingScore(r.temp, r.wind_speed, rain);
      const cl = cyclingLabel(score);
      const cond = guessCondition(r.temp, rain);
      return `<div class="hour-row">
        <span class="h-time">${fmtTime(r.dt ?? r.future_dt)}</span>
        ${conditionIconHtml(cond)}
        <span class="h-temp">${Math.round(r.temp)}&deg;C</span>
        <div class="h-bar-track"><div class="h-bar-fill" style="width:${score}%;background:${cl.color}"></div></div>
      </div>`;
    }
 
    let listHtml = '';
    if (current && current.temp != null) {
      const cr = current.rain_1h ?? 0;
      const wsp = current.wind_speed ?? 0;
      const cs = cyclingScore(current.temp, wsp, cr);
      const ccl = cyclingLabel(cs);
      const ccond = guessCondition(current.temp, cr);
      listHtml += `<div class="hour-row hour-row-now">
        <span class="h-time">Now</span>
        ${conditionIconHtml(ccond)}
        <span class="h-temp">${Math.round(current.temp)}&deg;C</span>
        <div class="h-bar-track"><div class="h-bar-fill" style="width:${cs}%;background:${ccl.color}"></div></div>
      </div>`;
    }
    listHtml += stripForecast.map(hourRowHtml).join('');
    document.getElementById('hourly-list').innerHTML = listHtml;
 
    const lbls  = rows.map(r => fmtTime(r.dt ?? r.future_dt));
    const temps = rows.map(r => (r.temp != null ? +r.temp.toFixed(1) : null));
    const feels = rows.map(r => (r.feels_like != null ? +r.feels_like.toFixed(1) : null));
    const rains = rows.map(rainMmPerHFromHourlyRow);
 
    if (current && current.temp != null) {
      const t0 = +Number(current.temp).toFixed(1);
      const f0 = current.feels_like != null ? +Number(current.feels_like).toFixed(1) : t0;
      const r0 = current.rain_1h != null && current.rain_1h !== ''
        ? +Number(current.rain_1h).toFixed(2)
        : 0;
      buildTempChart(['Now', ...lbls], [t0, ...temps], [f0, ...feels]);
      buildRainChart(['Now', ...lbls], [r0, ...rains]);
    } else {
      buildTempChart(lbls, temps, feels);
      buildRainChart(lbls, rains);
    }
  }
 
  // ── AUTO-REFRESH ─────────────────────────────────────────────────────────
  // RUN ON PAGE LOAD — current first, then hourly (reuses current for "Now" on charts)
  async function refreshWeather() {
    const cur = await loadCurrent();
    await loadHourly(cur);
  }
  refreshWeather();
  setInterval(refreshWeather, 5 * 60 * 1000);
});