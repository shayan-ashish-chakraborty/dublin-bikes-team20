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
    // our own database (fastest, most accurate for Dublin)
    const res = await fetch('/api/weather/db/current?limit=1').then(r => r.json());
    const row = res.weather?.[0];
    if (row?.temp !== undefined) {
      chip.textContent = Math.round(row.temp) + '°C';
      return;
    }
  } catch (_) {}

  try {
    // fallback: OpenWeather via backend proxy
    const res2 = await fetch('/api/weather/openweather/current').then(r => r.json());
    const w = res2.weather;
    if (w?.temp !== undefined) {
      chip.textContent = Math.round(w.temp) + '°C';
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

  try {
    const res2 = await fetch('/api/weather/openweather/current').then(r => r.json());
    const w = res2.weather;
    if (w?.temp !== undefined) {
      document.getElementById('hw-temp').textContent   = Math.round(w.temp)        + '°C';
      document.getElementById('hw-feels').textContent  = Math.round(w.feels_like)  + '°C';
      document.getElementById('hw-hum').textContent    = Math.round(w.humidity)    + '%';
      document.getElementById('hw-wind').textContent   = (+w.wind_speed).toFixed(1) + ' m/s';
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


