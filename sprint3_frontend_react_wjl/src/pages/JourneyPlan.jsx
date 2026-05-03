import { useEffect, useState } from "react";
import MapView from "../components/MapView";

function JourneyPlan() {

  const [stations, setStations] = useState([]);
  const [userLocation, setUserLocation] = useState(null);
  const [destination, setDestination] = useState(null);

  useEffect(() => {

    fetch("http://127.0.0.1:8000/api/bikes/stations")
      .then(res => res.json())
      .then(data => {
        console.log("stations data:", data);
        setStations(data);
      });

  }, []);
  
  useEffect(() => {
    navigator.geolocation.getCurrentPosition((position) => {
      setUserLocation({
        lat: position.coords.latitude,
        lng: position.coords.longitude
      });
    });
  }, []);
  
  const referencePoint = destination || userLocation;
  const nearbyStations = stations
  .map((station) => {

    if (!referencePoint || !station.position){
      return {
        ...station,
        distance: null
      };
    }

    const dx = station.position.lat - referencePoint.lat;
    const dy = station.position.lng - referencePoint.lng;
    const distance = Math.sqrt(dx * dx + dy * dy) * 111000;

    return {
      ...station,
      distance
    };

  })
  .filter((station) => station.available_bikes >= 2) // recommend situation
  .sort((a, b) => (a.distance ?? Infinity) - (b.distance ?? Infinity))
  .slice(0, 3);
  
  return (
  <div
    style={{
      width: "1510px",
      height: "1024px",
      display: "flex",
      flexDirection: "column",
      fontFamily: "Arial"
    }}
  >

    {/* ===== TOP NAV BAR ===== */}

    <div
        style={{
          width: "125px",
        }}
    >
    </div>

    {/* ===== MAIN CONTENT ===== */}

    <div style={{ display: "flex", flex: 1 }}>

      {/* ===== LEFT SIDEBAR ===== */}

      <div
        style={{
          width: "358px",
          height:"899px",
          background: "#064E19",
          color: "white",
        }}
      >

        {/* PLAN BUTTON */}
        <div
          style={{
            background: "#C6F9A5",
            color: "black",
            padding: "15px",
            borderRadius: "20px",
            fontWeight: "bold",
            fontSize: "32px",
            marginBottom: "40px",
            textAlign: "center",
            border:"0,30px,0,0",
          }}
        >
          Plan Your Journey
        </div>


        {/* NEARBY STATIONS TITLE */}
        <h2 style={{ marginLeft: "20px" }}>
          Nearby Stations
        </h2>


        {/* LOCATION WARNING */}
        {!userLocation && !destination && (
          <div style={{ marginTop: "20px", marginLeft: "20px", color: "#FFD700" }}>
            Sorry, there are no recommended stations nearby. <br/>
            Please enable location services to see nearby stations.
          </div>
        )}

        {userLocation && nearbyStations.length === 0 && (
          <div style={{ marginTop: "20px", marginLeft: "20px", color: "#FFD700" }}>
            Sorry, there are no recommended stations nearby.
          </div>
        )}


        {/* STATION LIST */}

        {nearbyStations.map((station) => (

          <div
            key={station.number}
            style={{
              marginTop: "20px",
              borderBottom: "1px solid rgba(255,255,255,0.3)",
              paddingBottom: "25px",
            }}
          >
            <div style={{ marginLeft: "20px" }}>

            <div style={{ fontWeight: "bold" }}>
              {station.name}
            </div>

            <div>Available Bikes: {station.available_bikes}</div>

            <div>
              Distance: {station.distance ? Math.round(station.distance) + " m" : "Unknown"}
            </div>

            <div>
              Walking Time: {station.distance ? Math.round(station.distance / 80) + " min" : "Unknown"}
            </div>

          </div>
        </div>
        ))}

      </div>



      {/* ===== MAP AREA ===== */}

      <div
        style={{
          flex: 1,
          position: "relative"
        }}
      >


        {/* GOOGLE MAP */}

        <MapView 
          stations={stations} 
          nearbyStations={nearbyStations}
          userLocation={userLocation}
          setDestination={setDestination}
          destination={destination}
        />

      </div>

    </div>

  </div>
 );
};

export default JourneyPlan;
