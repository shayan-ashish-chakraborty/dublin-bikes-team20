import { GoogleMap, LoadScript, Marker, InfoWindow, Autocomplete } from "@react-google-maps/api";
import { useState, useEffect } from "react";

const containerStyle = {
  width: "100%",
  height: "899px"
};

const center = {
  lat: 53.3498,
  lng: -6.2603
};

function MapView({ stations, userLocation, setDestination, destination }) {

  const [selectedStation, setSelectedStation] = useState(null);
  const [autocomplete, setAutocomplete] = useState(null);
  const [map, setMap] = useState(null);

  useEffect(() => {
    if (map && userLocation) {
      map.panTo(userLocation);
    }
  }, [userLocation, map]);

  const onLoad = (autoC) => {
    setAutocomplete(autoC);
  };

  const onPlaceChanged = () => {

  if (!autocomplete) return;

  const place = autocomplete.getPlace();

  if (!place.geometry) return;

  const location = {
    lat: place.geometry.location.lat(),
    lng: place.geometry.location.lng()
  };

  setDestination(location);

  if (map) {
    map.panTo(location);
    map.setZoom(15);
  }

};

  return (

    <LoadScript
      googleMapsApiKey="AIzaSyD-tvR7Cp5JQ5PIf4K76WJ1esge3oST1xo"
      libraries={["places"]}
    >

    <GoogleMap
      mapContainerStyle={containerStyle}
      center={center}
      zoom={13}
      onLoad={(mapInstance) => setMap(mapInstance)}
    >

        {/* SEARCH BAR */}
        <Autocomplete
          onLoad={onLoad}
          onPlaceChanged={onPlaceChanged}
        >
          <input
            type="text"
            placeholder="Where are you going"
            style={{
              position: "absolute",
              top: "30px",
              left: "50%",
              transform: "translateX(-50%)",
              width: "450px",
              padding: "15px",
              borderRadius: "30px",
              border: "1px solid #ccc",
              fontSize: "16px",
              zIndex: 10
            }}
          />
        </Autocomplete>


        {/* MARKERS */}
        {Array.isArray(stations) &&
          stations.map((station) => {

            if (!station.position) return null;

            return (
              <Marker
                key={station.number}
                position={{
                  lat: station.position.lat,
                  lng: station.position.lng
                }}
                onClick={() => setSelectedStation(station)}
              />
            );
          })
        }


      {/* DESTINATION MARKER */}
      {destination && (
        <Marker
          position={destination}
          icon="http://maps.google.com/mapfiles/ms/icons/blue-dot.png"
        />
      )}


        {/* INFO WINDOW */}
        {selectedStation && (
          <InfoWindow
            position={{
              lat: selectedStation.position.lat,
              lng: selectedStation.position.lng
            }}
            onCloseClick={() => setSelectedStation(null)}
          >
            <div style={{ minWidth: "200px" }}>

              <h3>{selectedStation.name}</h3>

              <p><b>Capacity:</b> {selectedStation.bike_stands}</p>

              <p><b>Available Bikes:</b> {selectedStation.available_bikes}</p>

              <p><b>Available Docks:</b> {selectedStation.available_bike_stands}</p>

              <p>
                <b>Status:</b>{" "}
                <span
                  style={{
                    color: selectedStation.status === "OPEN" ? "green" : "red",
                    fontWeight: "bold"
                  }}
                >
                  {selectedStation.status}
                </span>
              </p>

            </div>
          </InfoWindow>
        )}

      </GoogleMap>

    </LoadScript>

  );
}

export default MapView;