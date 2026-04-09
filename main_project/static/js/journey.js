// ── State ─────────────────────────────────────────────────────────────────────

const state = {
  map: null,
  infoWindow: null,
  stations: [],
  routeData: null,
  polylines: [],
  markers: [],
  stationMarkers: [],
};

// ── Helpers ───────────────────────────────────────────────────────────────────

async function apiFetch(path, options = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: res.statusText }));
    throw new Error(err.error || "Request failed");
  }
  return res.json();
}

function formatDistance(meters) {
  if (meters >= 1000) return (meters / 1000).toFixed(1) + " km";
  return meters + " m";
}

function formatDuration(seconds) {
  const mins = Math.round(seconds / 60);
  if (mins < 60) return mins + " min";
  const h = Math.floor(mins / 60);
  const m = mins % 60;
  return m > 0 ? `${h}h ${m}min` : `${h}h`;
}

// ── Initialisation ────────────────────────────────────────────────────────────

(async function bootstrap() {
  try {
    const { googleMapsApiKey } = await apiFetch("journey/api/config"); 
    injectMapsScript(googleMapsApiKey);
  } catch (e) {
    showError("Failed to load configuration. Please refresh the page.");
  }
})();

function injectMapsScript(key) {
  const script = document.createElement("script");
  script.src = `https://maps.googleapis.com/maps/api/js?key=${key}&loading=async&callback=initMap&libraries=geometry,places`;
  script.async = true;
  script.defer = true;
  document.head.appendChild(script);
}

window.initMap = function () {
  state.map = new google.maps.Map(document.getElementById("map"), {
    center: { lat: 53.3498, lng: -6.2603 },
    zoom: 14,
    mapTypeControl: false,
    fullscreenControl: true,
    streetViewControl: false,
  });

  state.infoWindow = new google.maps.InfoWindow();

  setDefaultDateTime();
  attachEventListeners();
  fetchAndRenderStations();
  googleAutoRefill();  
};

function setDefaultDateTime() {
  const now = new Date();
  const dateStr = now.toISOString().slice(0, 10);
  const timeStr = now.toTimeString().slice(0, 5);

  const max48h = new Date(now.getTime() + 48 * 60 * 60 * 1000);
  const maxDateStr = max48h.toISOString().slice(0, 10);

  const dateInput = document.getElementById("date-input");
  dateInput.value = dateStr;
  dateInput.min = dateStr;
  dateInput.max = maxDateStr;

  document.getElementById("time-input").value = timeStr;
}

function attachEventListeners() {
  document.getElementById("navigate-btn").addEventListener("click", handleNavigate);
  document.getElementById("refresh-btn").addEventListener("click", fetchAndRenderStations);

  ["start-input", "end-input"].forEach(id => {
    document.getElementById(id).addEventListener("keydown", e => {
      if (e.key === "Enter") handleNavigate();
    });
  });
}

// ── Station Layer ─────────────────────────────────────────────────────────────

async function fetchAndRenderStations() {
  const date = document.getElementById("date-input").value;
  const time = document.getElementById("time-input").value;
  const btn = document.getElementById("refresh-btn");
  btn.disabled = true;
  btn.textContent = "Refreshing…";
  clearError();

  // Clear inputs and route
  document.getElementById("start-input").value = "";
  document.getElementById("end-input").value = "";
  clearRouteLayer();
  document.getElementById("route-summary").classList.add("hidden");
  document.getElementById("station-cards").classList.add("hidden");
  document.getElementById("directions-panel").classList.add("hidden");

  try {
    const stations = await apiFetch(`/journey/api/availability?date=${date}&time=${time}`); 
    state.stations = stations;
    renderStationMarkers(stations);
    btn.textContent = "✓ Refreshed";
    setTimeout(() => { btn.innerHTML = "&#x21BB; Refresh"; }, 1500);
  } catch (e) {
    showError("Could not load station data: " + e.message);
    btn.innerHTML = "&#x21BB; Refresh";
  } finally {
    btn.disabled = false;
  }
}

function renderStationMarkers(stations) {
  state.stationMarkers.forEach(m => m.setMap(null));
  state.stationMarkers = [];

  stations.forEach(station => {
    const bikes = station.available_bikes;
    const fillColor = bikes >= 5 ? "#16a34a" : bikes >= 1 ? "#d97706" : "#dc2626";

    const marker = new google.maps.Marker({
      position: { lat: station.lat, lng: station.lng },
      map: state.map,
      title: station.name,
      icon: {
        path: google.maps.SymbolPath.CIRCLE,
        scale: 7,
        fillColor,
        fillOpacity: 0.9,
        strokeColor: "#ffffff",
        strokeWeight: 1.5,
      },
    });

    marker.addListener("click", () => {
      state.infoWindow.setContent(
        `<div class="gm-iw">
          <strong>${station.name}</strong>
          <div class="iw-avail">
            <span style="color:#16a34a">🚲 ${station.available_bikes} bikes</span>
            <span style="color:#2563eb">🅿 ${station.available_stands} stands</span>
          </div>
        </div>`
      );
      state.infoWindow.open(state.map, marker);
    });

    state.stationMarkers.push(marker);
  });
}

// ── Route Flow ────────────────────────────────────────────────────────────────

function handleNavigate() {
  const start   = document.getElementById("start-input").value.trim();
  const end     = document.getElementById("end-input").value.trim();
  const dateStr = document.getElementById("date-input").value;
  const timeStr = document.getElementById("time-input").value;

  if (!start || !end) {
    showError("Please enter both a start and end address.");
    return;
  }

  // Validate selected time is within 48 hours
  const selectedDt  = new Date(`${dateStr}T${timeStr}:00`);
  const now         = new Date();
  const diffHours   = (selectedDt - now) / (1000 * 60 * 60);

  if (diffHours < -(1 / 60)) {          // allow up to 1 min in the past
    showError("Please select a time in the future.");
    return;
  }

  if (diffHours > 48) {
    showError("Please select a time within the next 48 hours.");
    return;
  }

  clearError();

  // > 1 hour in the future → use prediction endpoint
  const usePrediction = diffHours > 1;
  const timeForApi    = `${dateStr} ${timeStr}:00`;
  fetchRoute(start, end, usePrediction ? timeForApi : null);
}

async function fetchRoute(start, end, timeStr = null) {
  const btn = document.getElementById("navigate-btn");
  btn.disabled = true;
  btn.textContent = "Finding route…";
  document.getElementById("map-loading").classList.remove("hidden");

  const endpoint = timeStr ? "journey/api/route/predict" : "journey/api/route";
  const body     = timeStr ? { start, end, time: timeStr } : { start, end };

  try {
    const data = await apiFetch(endpoint, {
      method: "POST",
      body: JSON.stringify(body),
    });
    state.routeData = data;
    renderRoute(data);
  } catch (e) {
    showError(e.message || "Could not calculate route. Please try again.");
  } finally {
    btn.disabled = false;
    btn.innerHTML = "Navigate &#x2192;";
    document.getElementById("map-loading").classList.add("hidden");
  }
}

function renderRoute(data) {
  clearRouteLayer();
  drawPolylines(data.legs);
  placeRouteMarkers(data);
  renderStationCards(data);
  renderSummary(data.summary);
  renderDirections(data.legs);
  fitMapToBounds(data);

  // Prediction banner
  const banner = document.getElementById("prediction-banner");
  if (data.prediction_mode) {
    let msg = "The journey plan is based on prediction data, not live data.";
    if (data.weather_warning) msg += ` (${data.weather_warning})`;
    banner.textContent = msg;
    banner.classList.remove("hidden");
  } else {
    banner.classList.add("hidden");
  }

  document.getElementById("route-summary").classList.remove("hidden");
  document.getElementById("station-cards").classList.remove("hidden");
  document.getElementById("directions-panel").classList.remove("hidden");
}

// ── Map Drawing ───────────────────────────────────────────────────────────────

function clearRouteLayer() {
  [...state.polylines, ...state.markers].forEach(item => item.setMap(null));
  state.polylines = [];
  state.markers = [];
}

const LEG_COLORS = {
  walk_to_bike: "#4a90d9",
  cycle: "#27ae60",
  walk_from_bike: "#e67e22",
};

function drawPolylines(legs) {
  Object.entries(LEG_COLORS).forEach(([key, color]) => {
    if (!legs[key] || !legs[key].polyline) return;
    const path = google.maps.geometry.encoding.decodePath(legs[key].polyline);
    const polyline = new google.maps.Polyline({
      path,
      map: state.map,
      strokeColor: color,
      strokeWeight: 5,
      strokeOpacity: 0.85,
    });
    state.polylines.push(polyline);
  });
}

function placeRouteMarkers(data) {
  const { start, end, pickup_station, dropoff_station } = data;

  const startMarker = new google.maps.Marker({
    position: { lat: start.lat, lng: start.lng },
    map: state.map,
    title: "Start: " + start.address,
    label: { text: "A", color: "white", fontWeight: "bold" },
    icon: {
      path: google.maps.SymbolPath.CIRCLE,
      scale: 12,
      fillColor: "#1a7340",
      fillOpacity: 1,
      strokeColor: "#ffffff",
      strokeWeight: 2,
    },
  });
  addInfoWindow(startMarker, `<div class="gm-iw"><strong>Start</strong>${start.address}</div>`);
  state.markers.push(startMarker);

  const endMarker = new google.maps.Marker({
    position: { lat: end.lat, lng: end.lng },
    map: state.map,
    title: "End: " + end.address,
    label: { text: "B", color: "white", fontWeight: "bold" },
    icon: {
      path: google.maps.SymbolPath.CIRCLE,
      scale: 12,
      fillColor: "#dc2626",
      fillOpacity: 1,
      strokeColor: "#ffffff",
      strokeWeight: 2,
    },
  });
  addInfoWindow(endMarker, `<div class="gm-iw"><strong>End</strong>${end.address}</div>`);
  state.markers.push(endMarker);

  const pickupMarker = new google.maps.Marker({
    position: { lat: pickup_station.lat, lng: pickup_station.lng },
    map: state.map,
    title: "Pickup: " + pickup_station.name,
    icon: {
      path: google.maps.SymbolPath.CIRCLE,
      scale: 10,
      fillColor: "#4a90d9",
      fillOpacity: 1,
      strokeColor: "#ffffff",
      strokeWeight: 2,
    },
  });
  addInfoWindow(pickupMarker,
    `<div class="gm-iw"><strong>🚲 Pickup Station</strong>${pickup_station.name}
      <div class="iw-avail">
        <span style="color:#16a34a">🚲 ${pickup_station.available_bikes} bikes</span>
        <span style="color:#2563eb">🅿 ${pickup_station.available_stands} stands</span>
      </div>
    </div>`
  );
  state.markers.push(pickupMarker);

  const dropoffMarker = new google.maps.Marker({
    position: { lat: dropoff_station.lat, lng: dropoff_station.lng },
    map: state.map,
    title: "Dropoff: " + dropoff_station.name,
    icon: {
      path: google.maps.SymbolPath.CIRCLE,
      scale: 10,
      fillColor: "#e67e22",
      fillOpacity: 1,
      strokeColor: "#ffffff",
      strokeWeight: 2,
    },
  });
  addInfoWindow(dropoffMarker,
    `<div class="gm-iw"><strong>🚩 Dropoff Station</strong>${dropoff_station.name}
      <div class="iw-avail">
        <span style="color:#16a34a">🚲 ${dropoff_station.available_bikes} bikes</span>
        <span style="color:#2563eb">🅿 ${dropoff_station.available_stands} stands</span>
      </div>
    </div>`
  );
  state.markers.push(dropoffMarker);
}

function addInfoWindow(marker, content) {
  marker.addListener("click", () => {
    state.infoWindow.setContent(content);
    state.infoWindow.open(state.map, marker);
  });
}

function fitMapToBounds(data) {
  const bounds = new google.maps.LatLngBounds();
  bounds.extend({ lat: data.start.lat, lng: data.start.lng });
  bounds.extend({ lat: data.end.lat, lng: data.end.lng });
  bounds.extend({ lat: data.pickup_station.lat, lng: data.pickup_station.lng });
  bounds.extend({ lat: data.dropoff_station.lat, lng: data.dropoff_station.lng });
  state.map.fitBounds(bounds, { top: 40, right: 40, bottom: 40, left: 40 });
}

// ── UI Rendering ──────────────────────────────────────────────────────────────

function renderStationCards(data) {
  const { pickup_station: p, dropoff_station: d } = data;

  document.getElementById("pickup-name").textContent   = p.name;
  document.getElementById("pickup-bikes").textContent  = `🚲 ${p.available_bikes} bikes`;
  document.getElementById("pickup-stands").textContent = `🅿 ${p.available_stands} stands`;

  document.getElementById("dropoff-name").textContent   = d.name;
  document.getElementById("dropoff-bikes").textContent  = `🚲 ${d.available_bikes} bikes`;
  document.getElementById("dropoff-stands").textContent = `🅿 ${d.available_stands} stands`;

  const showTag = data.prediction_mode ? "" : "hidden";
  document.getElementById("pickup-predict-tag").className  = `predict-tag ${showTag}`.trim();
  document.getElementById("dropoff-predict-tag").className = `predict-tag ${showTag}`.trim();
}

function renderSummary(summary) {
  document.getElementById("summary-distance").textContent = formatDistance(summary.total_distance);
  document.getElementById("summary-duration").textContent = formatDuration(summary.total_duration_s);
}

function renderDirections(legs) {
  const legConfig = [
    { key: "walk_to_bike", metaId: "leg1-meta", stepsId: "leg1-steps" },
    { key: "cycle",        metaId: "leg2-meta", stepsId: "leg2-steps" },
    { key: "walk_from_bike", metaId: "leg3-meta", stepsId: "leg3-steps" },
  ];

  legConfig.forEach(({ key, metaId, stepsId }) => {
    const leg = legs[key];
    if (!leg) return;

    document.getElementById(metaId).textContent =
      `${leg.distance_text} · ${leg.duration_text}`;

    const list = document.getElementById(stepsId);
    list.innerHTML = "";
    leg.steps.forEach(step => {
      const li = document.createElement("li");
      // instruction comes from html_instructions (Google), use innerHTML for bold street names
      li.innerHTML = `${step.instruction}<span class="step-meta">${step.distance} · ${step.duration}</span>`;
      list.appendChild(li);
    });
  });
}
// ── Google Auto Refill ────────────────────────────────────────────────────────────
function googleAutoRefill() {
  
  const dublinBounds = new google.maps.LatLngBounds(
      new google.maps.LatLng(53.2719, -6.3854),  
      new google.maps.LatLng(53.4109, -6.1067)   
  );

  const options = {
      bounds: dublinBounds,
      componentRestrictions: { country: "ie" },  
      fields: ["geometry", "name", "formatted_address"],
  };

  const originInput = document.getElementById('start-input');
  const destinationInput = document.getElementById('end-input');

  const originAutocomplete = new google.maps.places.Autocomplete(originInput, options);
  const destinationAutocomplete = new google.maps.places.Autocomplete(destinationInput, options);

  originAutocomplete.addListener('place_changed', function() {
      const place = originAutocomplete.getPlace();
      console.log('Starting Point：', place.geometry.location.lat(), place.geometry.location.lng());
  });

  destinationAutocomplete.addListener('place_changed', function() {
      const place = destinationAutocomplete.getPlace();
      console.log('Destination：', place.geometry.location.lat(), place.geometry.location.lng());
  });

}



// ── Error / Status ────────────────────────────────────────────────────────────

function showError(message) {
  const el = document.getElementById("status-message");
  el.textContent = message;
  el.classList.remove("hidden");
}

function clearError() {
  document.getElementById("status-message").classList.add("hidden");
}
