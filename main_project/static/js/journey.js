// ── State ─────────────────────────────────────────────────────────────────────

const state = {
  map: null,
  infoWindow: null,
  stations: [],
  routeData: null,
  polylines: [],
  markers: [],
  stationMarkers: [],
  suppressMapClickClose: false,
  routePickupMarker: null,
  routeDropoffMarker: null,
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

  state.map.addListener("click", () => {
    if (state.suppressMapClickClose) return;
    journeyDestroyMlChartsIfPresent();
    state.infoWindow.close();
  });
  state.infoWindow.addListener("closeclick", journeyDestroyMlChartsIfPresent);

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
  setDefaultDateTime();
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
  state.infoWindow.close();
  const puM = document.getElementById("journey-pickup-more");
  const doM = document.getElementById("journey-dropoff-more");
  if (puM) puM.classList.add("hidden");
  if (doM) doM.classList.add("hidden");
  document.getElementById("route-summary").classList.add("hidden");
  document.getElementById("station-cards").classList.add("hidden");
  document.getElementById("directions-panel").classList.add("hidden");
  const hint = document.querySelector(".form-hint");
  if (hint) hint.classList.remove("hidden");

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
      journeyOpenStationMlInfoWindow(marker, station);
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
  let selectedDt  = new Date(`${dateStr}T${timeStr}:00`);
  const now         = new Date();
  let diffHours   = (selectedDt - now) / (1000 * 60 * 60);

  // If user selected a past time, silently snap to now and use live data
  if (diffHours < -(1 / 60)) {
    setDefaultDateTime();
    selectedDt = new Date();
    diffHours  = 0;
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
  const hint = document.querySelector(".form-hint");
  if (hint) hint.classList.add("hidden");
}

// ── Map Drawing ───────────────────────────────────────────────────────────────

function clearRouteLayer() {
  journeyDestroyMlChartsIfPresent();
  state.routePickupMarker = null;
  state.routeDropoffMarker = null;
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
  pickupMarker.addListener("click", () => {
    journeyOpenStationMlInfoWindow(pickupMarker, pickup_station);
  });
  state.markers.push(pickupMarker);
  state.routePickupMarker = pickupMarker;

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
  dropoffMarker.addListener("click", () => {
    journeyOpenStationMlInfoWindow(dropoffMarker, dropoff_station);
  });
  state.markers.push(dropoffMarker);
  state.routeDropoffMarker = dropoffMarker;
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

  [".station-card.pickup", ".station-card.dropoff"].forEach((sel) => {
    const card = document.querySelector(sel);
    if (!card) return;
    const existing = card.querySelector(".predicted-label");
    if (data.prediction_mode) {
      if (!existing) {
        const label = document.createElement("span");
        label.className = "predicted-label";
        label.textContent = "predicted";
        card.appendChild(label);
      }
    } else if (existing) {
      existing.remove();
    }
  });

  const puCard = document.querySelector(".station-card.pickup");
  const doCard = document.querySelector(".station-card.dropoff");
  if (puCard) {
    puCard.onclick = () => {
      if (state.routePickupMarker && typeof google !== "undefined" && google.maps) {
        google.maps.event.trigger(state.routePickupMarker, "click");
      }
    };
  }
  if (doCard) {
    doCard.onclick = () => {
      if (state.routeDropoffMarker && typeof google !== "undefined" && google.maps) {
        google.maps.event.trigger(state.routeDropoffMarker, "click");
      }
    };
  }
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

// ── Journey: InfoWindow ML (parity with Stations map — MLbikes.js) ────────────

function journeyDestroyMlChartsIfPresent() {
  if (window.StationML && typeof window.StationML.destroyIwCharts === "function") {
    window.StationML.destroyIwCharts();
  }
}


/**
 * Centers the map so the marker sits in the lower portion of the viewport,
 * leaving ~250px of room above it for the info window to render fully.
 */
function journeyCenterMarkerLow(marker) {
  const projection = state.map.getProjection();
  if (!projection) {
    state.map.panTo(marker.getPosition());
    return;
  }
  const scale     = Math.pow(2, state.map.getZoom());
  const worldPt   = projection.fromLatLngToPoint(marker.getPosition());
  // Shift center 250 screen-pixels north so marker sits in lower area
  const newCenter = projection.fromPointToLatLng(
    new google.maps.Point(worldPt.x, worldPt.y - 250 / scale)
  );
  state.map.panTo(newCenter);
}

function journeyApplyIwLayoutFix() {
  try {
    const app = document.getElementById("app");
    if (!app) return;
    const gmIw = app.querySelector(".gm-style-iw-d .gm-iw");
    if (!gmIw) return;
    const iwD = gmIw.closest(".gm-style-iw-d");
    if (iwD) {
      iwD.style.setProperty("padding", "12px", "important");
    }
    const shell = gmIw.closest(".gm-style-iw-c");
    if (!shell) return;
    shell.style.setProperty("padding", "0", "important");
    const chr = shell.querySelector(".gm-style-iw-chr");
    if (chr) {
      chr.style.setProperty("height", "0", "important");
      chr.style.setProperty("min-height", "0", "important");
      chr.style.setProperty("max-height", "0", "important");
      chr.style.setProperty("padding", "0", "important");
      chr.style.setProperty("overflow", "visible", "important");
    }
    const toolbar = shell.querySelector(".gm-style-iw-t");
    if (toolbar) {
      toolbar.style.setProperty("min-height", "0", "important");
      toolbar.style.setProperty("padding", "0", "important");
    }
    const tbc = shell.querySelector(".gm-style-iw-tc");
    if (tbc) {
      tbc.style.setProperty("padding-top", "0", "important");
      tbc.style.setProperty("min-height", "0", "important");
    }
  } catch (err) {
    console.warn("InfoWindow layout fix:", err);
  }
}

function journeyStationInfoHtmlBasic(station) {
  const bikes = station.available_bikes ?? 0;
  const stands =
    station.available_stands ?? station.available_bike_stands ?? 0;
  const name = String(station.name || "").replace(/</g, "&lt;");
  return (
    `<div class="gm-iw"><div class="gm-iw-inner">` +
    `<strong>${name}</strong>` +
    `<div class="iw-avail">` +
    `<span class="iw-tag iw-tag-bikes">🚲 ${bikes} bikes</span>` +
    `<span class="iw-tag iw-tag-stands">🅿 ${stands} stands</span>` +
    `</div></div></div>`
  );
}

function journeyOpenStationMlInfoWindow(marker, station) {
  journeyDestroyMlChartsIfPresent();
  state.suppressMapClickClose = true;
  journeyCenterMarkerLow(marker);

  // Wait for the smooth pan to finish before opening the info window
  google.maps.event.addListenerOnce(state.map, "idle", () => {
    const ml = window.StationML;
    if (ml && typeof ml.stationInfoHtml === "function") {
      state.infoWindow.setContent(ml.stationInfoHtml(station));
      state.infoWindow.open({ map: state.map, anchor: marker });
      google.maps.event.addListenerOnce(state.infoWindow, "domready", () => {
        journeyApplyIwLayoutFix();
        ml.setupInfoWindowPrediction(station);
      });
    } else {
      state.infoWindow.setContent(journeyStationInfoHtmlBasic(station));
      state.infoWindow.open({ map: state.map, anchor: marker });
      google.maps.event.addListenerOnce(state.infoWindow, "domready", () => {
        journeyApplyIwLayoutFix();
      });
    }
    window.setTimeout(() => {
      state.suppressMapClickClose = false;
    }, 400);
  });
}
