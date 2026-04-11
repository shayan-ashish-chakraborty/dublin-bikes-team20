(function () {
  "use strict";

  const root = document.getElementById("stations-app");
  if (!root) {
    return;
  }

  const STATIONS_API_URL =
    root.dataset.stationsApi ||
    new URL("/api/stations", window.location.origin).pathname;

  /**if cannot get the user location, use the default center */
  const DEFAULT_CENTER = { lat: 53.3498, lng: -6.2603 };
  const MAP_ZOOM_DEFAULT = 13;
  const MAP_ZOOM_DESTINATION = 15;
  const RADIUS_2KM_M = 2000;

  let stations = [];
  let userLocation = null;
  let destination = null;

  let map = null;
  let destinationMarker = null;
  let userLocationMarker = null;
  const stationMarkers = [];
  let infoWindow = null;
  /** 避免点标记后地图 click 立刻关掉刚打开的 InfoWindow */
  let suppressMapClickClose = false;

  /** Backend format_station (main_project/station/routes.py) uses top-level lat/lng. */
  function stationLatLng(station) {
    if (!station) return null;
    if (typeof station.lat === "number" && typeof station.lng === "number") {
      return { lat: station.lat, lng: station.lng };
    }
    if (
      station.position &&
      typeof station.position.lat === "number" &&
      typeof station.position.lng === "number"
    ) {
      return { lat: station.position.lat, lng: station.position.lng };
    }
    return null;
  }
  /**choose the destination */
  function getReferencePoint() {
    return destination || userLocation;
  }
 
  /**calculate the distance */
  function distanceMeters(ref, pos) {
    const dx = pos.lat - ref.lat;
    const dy = pos.lng - ref.lng;
    return Math.sqrt(dx * dx + dy * dy) * 111000;
  }


  function computeNearbyStations() {
    const ref = getReferencePoint();
    const withDistance = stations.map((station) => {
      const pos = stationLatLng(station);
      if (!ref || !pos) {
        return { ...station, distance: null };
      }
      const distance = distanceMeters(ref, pos);
      return { ...station, distance };
    });

    return withDistance
      .filter((s) => s.available_bikes >= 2)
      .sort((a, b) => (a.distance ?? Infinity) - (b.distance ?? Infinity))
      .slice(0, 5);
  }

  /** warning if no stations within 2km radius */
  function hasRecommendedStationWithin2km(ref) {
    if (!ref || !stations.length) return false;
    for (let i = 0; i < stations.length; i++) {
      const s = stations[i];
      if ((s.available_bikes ?? 0) < 2) continue;
      const pos = stationLatLng(s);
      if (!pos) continue;
      if (distanceMeters(ref, pos) <= RADIUS_2KM_M) return true;
    }
    return false;
  }

  /**warning situations */
  function renderSidebar() {
    const nearby = computeNearbyStations();
    const noRef = !userLocation && !destination;
    const ref = getReferencePoint();
    const dataReady = stations.length > 0;
    const warnLoc = document.getElementById("warn-no-location");
    const warnEmpty = document.getElementById("warn-no-stations");
    const warn2km = document.getElementById("warn-no-2km");
    const listEl = document.getElementById("station-list");

    if (warnLoc) warnLoc.hidden = !noRef;
    if (warnEmpty) {
      warnEmpty.hidden = noRef || nearby.length !== 0 || !userLocation;
    }
    if (warn2km) {
      const show2km =
        ref && dataReady && !hasRecommendedStationWithin2km(ref);
      warn2km.hidden = !show2km;
    }

    if (!listEl) return;
    listEl.innerHTML = "";
    if (noRef) return;
    nearby.forEach((station) => {
      const block = document.createElement("div");
      block.className = "station-block";
      const distText =
        station.distance != null
          ? Math.round(station.distance) + " m"
          : "Unknown";
      /**estimate the walking time */
      const walkText =
        station.distance != null
          ? Math.round(station.distance / 80) + " min"
          : "Unknown";
      
      /**information in the sidebar */
      block.innerHTML = `
        <div class="station-inner">
          <div class="station-name"></div>
          <div class="station-availability">
            <span class="avail-badge bikes">🚲 ${station.available_bikes} bikes</span>
            <span class="avail-badge stands">🅿 ${station.available_bike_stands ?? station.available_stands ?? 0} stands</span>
          </div>
          <div class="station-meta">📍 ${distText} &nbsp;·&nbsp; 🚶 ${walkText}</div>
        </div>`;
      block.querySelector(".station-name").textContent = station.name;
      block.addEventListener("click", () => {
        if (!map || !window.google || !google.maps) return;
        const marker = stationMarkers.find((m) => m.getTitle() === station.name);
        if (marker) google.maps.event.trigger(marker, "click");
      });
      listEl.appendChild(block);
    });
  }

  function centerMarkerLow(marker) {
    const projection = map.getProjection();
    if (!projection) {
      map.panTo(marker.getPosition());
      return;
    }
    const scale     = Math.pow(2, map.getZoom());
    const worldPt   = projection.fromLatLngToPoint(marker.getPosition());
    const newCenter = projection.fromPointToLatLng(
      new google.maps.Point(worldPt.x, worldPt.y - 250 / scale)
    );
    map.panTo(newCenter);
  }

  function destroyMlChartsIfPresent() {
    if (window.StationML && typeof window.StationML.destroyIwCharts === "function") {
      window.StationML.destroyIwCharts();
    }
  }

  /** Reduce default InfoWindow top padding (Maps often sets inline styles). */
  function applyStationsInfoWindowLayoutFix() {
    try {
      _applyStationsInfoWindowLayoutFixInner();
    } catch (err) {
      console.warn("InfoWindow layout fix:", err);
    }
  }

  function _applyStationsInfoWindowLayoutFixInner() {
    const app = document.getElementById("stations-app");
    if (!app) return;
    const gmIw = app.querySelector(".gm-style-iw-d .gm-iw");
    if (!gmIw) return;
    const iwD = gmIw.closest(".gm-style-iw-d");
    if (iwD) {
      iwD.style.setProperty("padding", "12px 0 6px 12px", "important");
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
  }

  /** Basic InfoWindow when MLbikes.js is not loaded. */
  function stationInfoHtmlBasic(station) {
    const bikes = station.available_bikes ?? 0;
    const stands =
      station.available_stands ?? station.available_bike_stands ?? 0;
    return (
      `<div class="gm-iw">` +
      `<div class="gm-iw-inner">` +
      `<strong>${String(station.name || "").replace(/</g, "&lt;")}</strong>` +
      `<div class="iw-avail">` +
      `<span class="iw-tag iw-tag-bikes">🚲 ${bikes} bikes</span>` +
      `<span class="iw-tag iw-tag-stands">🅿 ${stands} stands</span>` +
      `</div></div></div>`
    );
  }

  /** Journey.js marker colours: green / amber / red by bike count. */
  function stationMarkerFillColor(station) {
    const bikes = station.available_bikes ?? 0;
    if (bikes >= 5) return "#16a34a";
    if (bikes >= 1) return "#d97706";
    return "#dc2626";
  }

  function clearStationMarkers() {
    stationMarkers.forEach((m) => m.setMap(null));
    stationMarkers.length = 0;
  }

  function updateStationMarkers() {
    if (!map || !window.google || !google.maps) return;
    clearStationMarkers();
    if (!Array.isArray(stations)) return;

    stations.forEach((station) => {
      const pos = stationLatLng(station);
      if (!pos) return;
      const fillColor = stationMarkerFillColor(station);
      const marker = new google.maps.Marker({
        position: pos,
        map,
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
        destroyMlChartsIfPresent();
        suppressMapClickClose = true;
        centerMarkerLow(marker);
        google.maps.event.addListenerOnce(map, "idle", () => {
          const ml = window.StationML;
          if (ml && typeof ml.stationInfoHtml === "function") {
            infoWindow.setContent(ml.stationInfoHtml(station));
            infoWindow.open({ map, anchor: marker });
            google.maps.event.addListenerOnce(infoWindow, "domready", () => {
              applyStationsInfoWindowLayoutFix();
              ml.setupInfoWindowPrediction(station);
            });
          } else {
            console.warn("StationML missing");
            infoWindow.setContent(stationInfoHtmlBasic(station));
            infoWindow.open({ map, anchor: marker });
            google.maps.event.addListenerOnce(infoWindow, "domready", () => {
              applyStationsInfoWindowLayoutFix();
            });
          }
          window.setTimeout(() => {
            suppressMapClickClose = false;
          }, 400);
        });
      });
      stationMarkers.push(marker);
    });
  }
  
  /**show the user location */
  function updateDestinationMarker() {
    if (!map || !window.google) return;
    if (destinationMarker) {
      destinationMarker.setMap(null);
      destinationMarker = null;
    }
    if (!destination) return;
    destinationMarker = new google.maps.Marker({
      map,
      position: destination,
      icon: "http://maps.google.com/mapfiles/ms/icons/blue-dot.png",
    });
  }

  /** Show where the browser geolocation placed the user (distinct from search pin). */
  function updateUserLocationMarker() {
    if (!map || !window.google || !google.maps) return;
    if (userLocationMarker) {
      userLocationMarker.setMap(null);
      userLocationMarker = null;
    }
    if (!userLocation) return;
    userLocationMarker = new google.maps.Marker({
      map,
      position: userLocation,
      title: "Your location",
      zIndex: (google.maps.Marker.MAX_ZINDEX || 1000) + 1,
      icon: {
        path: google.maps.SymbolPath.CIRCLE,
        scale: 10,
        fillColor: "#1a7340",
        fillOpacity: 1,
        strokeColor: "#ffffff",
        strokeWeight: 2,
      },
    });
  }

  function placeLocationToLatLng(loc) {
    if (!loc) return null;
    return {
      lat: typeof loc.lat === "function" ? loc.lat() : loc.lat,
      lng: typeof loc.lng === "function" ? loc.lng() : loc.lng,
    };
  }

  async function initMap() {
    await google.maps.importLibrary("maps");
    const { PlaceAutocompleteElement } =
      await google.maps.importLibrary("places");

    const el = document.getElementById("map");
    map = new google.maps.Map(el, {
      center: DEFAULT_CENTER,
      zoom: MAP_ZOOM_DEFAULT,
    });

    infoWindow = new google.maps.InfoWindow();

    const oldInput = document.getElementById("places-search");
    const host = document.createElement("div");
    host.id = "places-search-host";
    if (oldInput) {
      host.className = oldInput.className;
      oldInput.replaceWith(host);
    }

    const placeAutocomplete = new PlaceAutocompleteElement({});
    placeAutocomplete.classList.add("stations-place-autocomplete");
    placeAutocomplete.placeholder = "Where are you going";
    placeAutocomplete.style.width = "100%";
    host.appendChild(placeAutocomplete);

    function syncAutocompleteBias() {
      const b = map.getBounds();
      if (b) placeAutocomplete.locationBias = b;
    }
    map.addListener("bounds_changed", syncAutocompleteBias);
    map.addListener("idle", syncAutocompleteBias);

    placeAutocomplete.addEventListener("gmp-select", async (ev) => {
      const placePrediction = ev.placePrediction;
      if (!placePrediction) return;
      const place = placePrediction.toPlace();
      await place.fetchFields({
        fields: ["location", "viewport"],
      });
      const loc = placeLocationToLatLng(place.location);
      if (!loc) return;
      destination = loc;

      if (place.viewport) {
        map.fitBounds(place.viewport);
      } else {
        map.panTo(loc);
        map.setZoom(MAP_ZOOM_DESTINATION);
      }
      updateDestinationMarker();
      renderSidebar();
    });

    map.addListener("click", () => {
      if (suppressMapClickClose) {
        return;
      }
      if (infoWindow) {
        destroyMlChartsIfPresent();
        infoWindow.close();
      }
    });

    infoWindow.addListener("closeclick", () => {
      destroyMlChartsIfPresent();
    });

    const myLocBtn = document.getElementById("btn-my-location");
    if (myLocBtn) {
      myLocBtn.addEventListener("click", goToMyLocation);
    }

    updateStationMarkers();
    updateDestinationMarker();
    updateUserLocationMarker();
    if (userLocation && !destination) {
      map.panTo(userLocation);
      map.setZoom(15);
    }
  }

  function loadStations() {
    fetch(STATIONS_API_URL)
      .then((res) => {
        if (!res.ok) throw new Error("stations " + res.status);
        return res.json();
      })
      .then((data) => {
        stations = Array.isArray(data) ? data : [];
        updateStationMarkers();
        renderSidebar();
      })
      .catch((err) => {
        console.error("Failed to load stations from API:", err);
        stations = [];
        updateStationMarkers();
        renderSidebar();
      });
  }

  /** go back to user location */
  function goToMyLocation() {
    if (!navigator.geolocation) {
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (position) => {
        userLocation = {
          lat: position.coords.latitude,
          lng: position.coords.longitude,
        };
        destination = null;
        if (map) {
          updateDestinationMarker();
          updateUserLocationMarker();
          map.panTo(userLocation);
          map.setZoom(15);
        }
        renderSidebar();
      },
      () => {},
      { enableHighAccuracy: true, timeout: 12000, maximumAge: 0 }
    );
  }

  function loadUserLocation() {
    if (!navigator.geolocation) {
      renderSidebar();
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (position) => {
        userLocation = {
          lat: position.coords.latitude,
          lng: position.coords.longitude,
        };
        if (map) {
          updateUserLocationMarker();
          if (!destination) {
            map.panTo(userLocation);
            map.setZoom(15);
          }
        }
        renderSidebar();
      },
      () => {
        renderSidebar();
      },
      { enableHighAccuracy: true, timeout: 12000, maximumAge: 60000 }
    );
  }

  function startAppAfterMapsReady() {
    function run() {
      initMap()
        .then(function () {
          loadStations();
          loadUserLocation();
        })
        .catch(function (err) {
          console.error(err);
        });
    }
    if (typeof google.maps.importLibrary === "function") {
      run();
      return;
    }
    var tries = 0;
    var id = setInterval(function () {
      tries++;
      if (
        typeof google !== "undefined" &&
        google.maps &&
        typeof google.maps.importLibrary === "function"
      ) {
        clearInterval(id);
        run();
      } else if (tries > 120) {
        clearInterval(id);
        console.error("google.maps.importLibrary not available.");
      }
    }, 50);
  }

  function injectMapsScript(apiKey) {
    const existing = document.querySelector('script[data-stations-maps="1"]');
    if (existing) return;

    window.stationsPageMapsCallback = function () {
      startAppAfterMapsReady();
    };

    const s = document.createElement("script");
    s.dataset.stationsMaps = "1";
    s.src =
      "https://maps.googleapis.com/maps/api/js?key=" +
      encodeURIComponent(apiKey) +
      "&callback=stationsPageMapsCallback&loading=async&v=weekly";
    s.async = true;
    s.onerror = function () {
      console.error("Cannot load Google Maps.");
    };
    document.head.appendChild(s);
  }

  function bootstrapStationsPage() {
    const existing = document.querySelector('script[data-stations-maps="1"]');
    if (existing) return;

    const apiKey = (root && root.dataset.mapsKey) || "";
    if (!apiKey) {
      console.error(
        "Google Maps API key missing: set GOOGLE_MAPS_API_KEY in .env (loaded into app config)."
      );
      return;
    }

    injectMapsScript(apiKey);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bootstrapStationsPage);
  } else {
    bootstrapStationsPage();
  }
})();
