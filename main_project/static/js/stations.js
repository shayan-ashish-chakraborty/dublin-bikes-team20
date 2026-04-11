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
      .filter((s) => (s.available_bikes ?? 0) >= 1)  // Show stations with at least 1 bike
      .sort((a, b) => (a.distance ?? Infinity) - (b.distance ?? Infinity))
      .slice(0, 10);  // Show top 10 instead of 5
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

  // ML Forecast variables for sidebar predictions
  let _wx = { temp: 12.0, humidity: 80.0, pressure: 1013.0 };

  /** Get current weather for sidebar ML forecast */
  async function getWeatherForML() {
    try {
      const res = await fetch('/api/weather/db/current?limit=1').then(r => r.json());
      const d = res.weather?.[0] ?? null;
      if (d && d.temp !== undefined) {
        _wx = { temp: d.temp, humidity: d.humidity, pressure: d.pressure ?? 1013.0 };
      }
    } catch(_) {}
  }

  /** Haversine formula to calculate distance between two coordinates in km */
  function calculateDistance(lat1, lon1, lat2, lon2) {
    const R = 6371; // Earth radius in km
    const dLat = (lat2 - lat1) * Math.PI / 180;
    const dLon = (lon2 - lon1) * Math.PI / 180;
    const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
              Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
              Math.sin(dLon / 2) * Math.sin(dLon / 2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    return R * c;
  }

  /** Load ML forecast for nearby stations */
  async function loadNearbyMLForecast() {
    const mlEl = document.getElementById('ml-stations');
    if (!mlEl) return;
    
    if (!navigator.geolocation) {
      const errorTemplate = document.getElementById('message-error-template');
      if (errorTemplate) {
        const clone = errorTemplate.content.cloneNode(true);
        clone.querySelector('.message-text').textContent = 'Geolocation not supported';
        mlEl.innerHTML = '';
        mlEl.appendChild(clone);
      } else {
        mlEl.innerHTML = '<p style="color:#c0392b; font-size: 12px; text-align: center;">Geolocation not supported</p>';
      }
      return;
    }

    const loadingTemplate = document.getElementById('message-loading-template');
    if (loadingTemplate) {
      const clone = loadingTemplate.content.cloneNode(true);
      clone.querySelector('.message-text').textContent = 'Detecting location...';
      mlEl.innerHTML = '';
      mlEl.appendChild(clone);
    } else {
      mlEl.innerHTML = '<p style="color: #999; font-size: 12px; text-align: center;">Detecting location&hellip;</p>';
    }

    navigator.geolocation.getCurrentPosition(async (position) => {
      try {
        const userLat = position.coords.latitude;
        const userLon = position.coords.longitude;

        // Fetch all stations
        const allStations = await fetch('/api/stations').then(r => r.json());
        
        // Calculate distances and take top 6 nearest
        const stationsWithDistance = allStations
          .filter(s => s.bike_stands > 0 && s.lat && s.lng)
          .map(s => ({
            station_id: s.number,
            capacity: s.bike_stands,
            name: s.name,
            distance: calculateDistance(userLat, userLon, s.lat, s.lng)
          }))
          .sort((a, b) => a.distance - b.distance)
          .slice(0, 6);

        if (stationsWithDistance.length === 0) {
          const errorTemplate = document.getElementById('message-error-template');
          if (errorTemplate) {
            const clone = errorTemplate.content.cloneNode(true);
            clone.querySelector('.message-text').textContent = 'No nearby stations';
            mlEl.innerHTML = '';
            mlEl.appendChild(clone);
          } else {
            mlEl.innerHTML = '<p style="color: #999; font-size: 12px; text-align: center;">No nearby stations</p>';
          }
          return;
        }

        // Get current weather
        await getWeatherForML();

        // Build query for ML endpoint
        const params = new URLSearchParams({
          stations: JSON.stringify(stationsWithDistance.map(s => ({
            station_id: s.station_id,
            capacity: s.capacity,
            name: s.name
          }))),
          hour: new Date().getHours(),
          avg_temp: _wx.temp.toFixed(1),
          avg_humidity: _wx.humidity.toFixed(1),
          avg_pressure: _wx.pressure.toFixed(1),
        });

        // Call ML endpoint
        const mlData = await fetch('/api/ml/forecast?' + params).then(r => r.json());
        if (mlData.error) throw new Error(mlData.error);

        // Render nearby stations with distance info (compact sidebar format)
        const predictions = mlData.predictions;
        const mlTemplate = document.getElementById("ml-prediction-template");
        if (!mlTemplate) {
          const errorTemplate = document.getElementById('message-error-template');
          if (errorTemplate) {
            const clone = errorTemplate.content.cloneNode(true);
            clone.querySelector('.message-text').textContent = 'Template not found';
            mlEl.innerHTML = '';
            mlEl.appendChild(clone);
          } else {
            mlEl.innerHTML = '<p style="color:#c0392b; font-size: 12px; text-align: center;">Template not found</p>';
          }
          return;
        }
        
        mlEl.innerHTML = "";
        stationsWithDistance.forEach((s, i) => {
          const pred = predictions[i];
          const col = pred.pct >= 60 ? '#007A33' : pred.pct >= 30 ? '#e6bc00' : '#c0392b';
          const pctDisplay = pred.pct >= 60 ? '' : pred.pct >= 30 ? '' : '';
          
          const clone = mlTemplate.content.cloneNode(true);
          const rootDiv = clone.firstElementChild;
          
          rootDiv.style.setProperty('--color', col);
          rootDiv.style.setProperty('--percentage', pred.pct + '%');
          
          clone.querySelector("[data-station-name]").textContent = pred.name;
          clone.querySelector("[data-distance]").textContent = (s.distance).toFixed(1);
          clone.querySelector("[data-icon]").textContent = pctDisplay;
          clone.querySelector("[data-bikes-pred]").textContent = pred.predicted_bikes;
          clone.querySelector("[data-capacity]").textContent = pred.capacity;
          
          mlEl.appendChild(clone);
        });

      } catch (err) {
        const errorTemplate = document.getElementById('message-error-template');
        if (errorTemplate) {
          const clone = errorTemplate.content.cloneNode(true);
          clone.querySelector('.message-text').textContent = err.message;
          mlEl.innerHTML = '';
          mlEl.appendChild(clone);
        } else {
          mlEl.innerHTML = `<p style="color:#c0392b; font-size: 12px; text-align: center;">${err.message}</p>`;
        }
      }
    }, (error) => {
      const errorTemplate = document.getElementById('message-error-template');
      if (errorTemplate) {
        const clone = errorTemplate.content.cloneNode(true);
        clone.querySelector('.message-text').textContent = 'Enable location for predictions';
        mlEl.innerHTML = '';
        mlEl.appendChild(clone);
      } else {
        mlEl.innerHTML = '<p style="color: #999; font-size: 12px; text-align: center;">Enable location for predictions</p>';
      }
    });
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
    
    // Render stations directly without template for now
    nearby.forEach((station) => {
      const block = document.createElement("div");
      block.className = "station-block";
      const distText =
        station.distance != null
          ? Math.round(station.distance) + " m"
          : "Unknown";
      const walkText =
        station.distance != null
          ? Math.round(station.distance / 80) + " min"
          : "Unknown";
      
      block.innerHTML = `
        <div class="station-inner">
          <div class="station-name" style="font-weight: 600;">${station.name}</div>
          <div style="font-size: 13px;">Available Bikes: ${station.available_bikes}</div>
          <div style="font-size: 13px;">Distance: ${distText}</div>
          <div style="font-size: 13px;">Walking Time: ${walkText}</div>
          </div>`;
      listEl.appendChild(block);
    });
  }

  function destroyMlChartsIfPresent() {
    if (window.StationML && typeof window.StationML.destroyIwCharts === "function") {
      window.StationML.destroyIwCharts();
    }
  }



  /** Basic InfoWindow - uses template from stations.html */
  function stationInfoHtmlBasic(station) {
    const bikes = station.available_bikes ?? 0;
    const stands = station.available_stands ?? station.available_bike_stands ?? 0;
    
    const template = document.getElementById('station-infowindow-template');
    if (!template) {
      // Fallback
      return `<div class="gm-iw"><strong>${String(station.name || "").replace(/</g, "&lt;")}</strong><div class="iw-avail"><span style="color:#16a34a">🚲 ${bikes} bikes</span><span style="color:#2563eb">🅿 ${stands} stands</span></div></div>`;
    }
    
    // Use a wrapper to handle DocumentFragment properly
    const wrapper = document.createElement('div');
    const clone = template.content.cloneNode(true);
    wrapper.appendChild(clone);
    
    wrapper.querySelector('.iw-station-name').textContent = String(station.name || "").replace(/</g, "&lt;");
    wrapper.querySelector('.iw-bikes-count').textContent = bikes;
    wrapper.querySelector('.iw-stands-count').textContent = stands;
    
    return wrapper.innerHTML;
  }

  /** Map marker colours based on bike capacity: green for high, amber for medium, red for low */
  function stationMarkerFillColor(station) {
    const capacity = station.bike_stands ?? station.available_bike_stands ?? 0;
    if (capacity >= 30) return "#16a34a";      // Green: High capacity
    if (capacity >= 15) return "#d97706";      // Amber: Medium capacity
    return "#dc2626";                           // Red: Low capacity
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
        const ml = window.StationML;
        if (ml && typeof ml.stationInfoHtmlWithPredictions === "function") {
          // Load predictions and show in info window
          const loadingTemplate = document.getElementById('message-loading-template');
          let loadingHtml = '<div style="padding: 0.5rem; min-width: 280px;"><p style="color: #999; font-size: 12px; text-align: center;">Loading predictions...</p></div>';
          if (loadingTemplate) {
            const clone = loadingTemplate.content.cloneNode(true);
            const wrapper = document.createElement('div');
            wrapper.style.padding = '0.5rem';
            wrapper.style.minWidth = '280px';
            wrapper.appendChild(clone);
            loadingHtml = wrapper.innerHTML;
          }
          infoWindow.setContent(loadingHtml);
          infoWindow.open({ map, anchor: marker });
          
          ml.stationInfoHtmlWithPredictions(station).then(html => {
            infoWindow.setContent(html);
          }).catch(err => {
            console.error("Error loading predictions:", err);
            infoWindow.setContent(stationInfoHtmlBasic(station));
          });
        } else {
          infoWindow.setContent(stationInfoHtmlBasic(station));
          infoWindow.open({ map, anchor: marker });
        }
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
