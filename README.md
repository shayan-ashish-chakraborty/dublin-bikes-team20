# Dublin Bikes Forecasting & Journey Planner

A full-stack web application that integrates real-time Dublin Bikes station data, live weather conditions, and machine learning forecasts to help users plan cycling journeys across the city.

## Features

- **Interactive Map** — View all Dublin Bikes stations with live availability indicators. Search by location or detect your current position, with the five nearest stations highlighted automatically.
- **Journey Planner** — Enter start and end locations and a preferred ride time to generate a full route with walking and cycling segments, estimated travel times, and smart station selection.
- **Bike & Dock Forecasting** — Hourly predictions of available bikes and docking spaces at any station for up to 48 hours ahead, powered by a trained Random Forest model.
- **Weather Module** — Real-time Dublin weather via OpenWeatherMap, with 3-hour interval forecasts, rain probability charts, and wind speed indicators.
- **User Authentication** — Register, log in, and log out with email and 6-digit PIN, with full input validation and error handling.
- **AI Chatbot** — A Gemini-powered conversational assistant available across all pages to answer questions and help with journey planning.

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python, Flask, Flask Blueprints |
| Frontend | HTML, CSS, JavaScript |
| Database | MySQL (hosted on AWS EC2) |
| Machine Learning | scikit-learn (Random Forest) |
| External APIs | JCDecaux Bikes API, OpenWeatherMap API, Google Maps API, Grok API |
| Deployment | AWS EC2 |

## Project Structure

```
dublin-bikes-team20/
├── app.py
├── var.env                                          ✗ ignore
├── requirement.txt
├── README.md
│
│
├── main_project/
│   ├── __init__.py
│   ├── config.py
│   ├── db.py
│   ├── auth/
│   │   ├── __init__.py
│   │   └── auth.py
│   ├── home/
│   │   ├── __init__.py
│   │   └── home.py
│   ├── journey/
│   │   ├── __init__.py
│   │   ├── api.py
│   │   ├── routes.py
│   │   └── services.py
│   ├── station/
│   │   ├── __init__.py
│   │   ├── bikes_original.py
│   │   ├── routes.py
│   │   └── services.py
│   ├── weather/
│   │   ├── __init__.py
│   │   ├── routes.py
│   │   └── services.py
│   ├── chat/
│   │   ├── __init__.py
│   │   └── chat.py
│   ├── bike_forecast/
│   │   ├── __init__.py
│   │   ├── routes.py
│   │   └── models/
│   │       ├── forecast.py
│   │       ├── model_meta.json                      ✗ ignored
│   │       ├── bike_model.pkl                       ✗ ignored
│   │       ├── docks_model.pkl                      ✗ ignored
│   │       ├── weather_humidity.pkl                 ✗ ignored
│   │       ├── weather_pressure.pkl                 ✗ ignored
│   │       ├── weather_rain.pkl                     ✗ ignored
│   │       └── weather_temp.pkl                     ✗ ignored
│   ├── notebooks/
│   │   ├── bike_forecasting.ipynb
│   │   ├── sktime_forecasting.ipynb
│   │   └── final_merged_data.csv                   ✗ ignored
│   ├── bash_scripts/
│   │   ├── create_db.sh
│   │   └── scrapper.sh
│   ├── static/
│   │   ├── css/
│   │   │   ├── style.css
│   │   │   ├── journey.css
│   │   │   ├── stations.css
│   │   │   └── ml.css
│   │   ├── js/
│   │   │   ├── main.js
│   │   │   ├── journey.js
│   │   │   ├── stations.js
│   │   │   └── MLbikes.js
│   │   └── images/
│   │       ├── loginbg.png
│   │       └── icons/
│   │           ├── bike.svg
│   │           ├── chatbot.svg
│   │           ├── cloud.svg
│   │           ├── journey.svg
│   │           ├── live.svg
│   │           ├── map.svg
│   │           ├── stations.svg
│   │           ├── weather.svg
│   │           ├── weather-cloud.svg
│   │           ├── weather-partly.svg
│   │           ├── weather-rain.svg
│   │           ├── weather-rain-heavy.svg
│   │           ├── weather-snow.svg
│   │           └── weather-sun.svg
│   └── templates/
│       ├── base.html
│       ├── index.html
│       ├── login.html
│       ├── register.html
│       ├── stations.html
│       ├── Journey.html
│       └── weather.html
│
├── sprint1_webscrappers/
├── sprint2_flask_cd/
└── sprint3_frontend_react_wjl/
```


### Clone the repository

```bash
git clone <repository-url>
cd project
```
### Install Python dependencies

```bash
pip install -r requirements.txt
```

### Configure environment variables

JCDECAUX_API_KEY=your_key
OPENWEATHER_API_KEY=your_key
GOOGLE_MAPS_API_KEY=your_key
GROK_API_KEY=your_key
DB_HOST=your_db_host
DB_PORT=3306
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_NAME=your_db_name

### Run the application

```bash
python main_project/app.py
```

## Training the Models

To retrain the machine learning models from scratch, open and run the notebook:

```bash
jupyter notebook notebooks/bike_forecasting.ipynb
```
The notebook will save all `.pkl` model files and `model_meta.json` to `main_project/bike_forecast/models/`.

## Deployment

The application is deployed on **AWS EC2**. The MySQL database is also hosted on the same EC2 instance using **AWS RDS**. The Flask app is configured to serve external requests in the cloud environment.