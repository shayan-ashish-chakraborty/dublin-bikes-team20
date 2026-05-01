#  Dublin Bikes 
 
A full-stack web application for real-time Dublin Bikes station data, journey planning, weather forecasting, and AI-powered assistance, deployed on AWS EC2.
 
---
 
##  Quick Links
 
| Resource | Link |
|---|---|
|  Live Application | [https://18.201.183.91/](https://18.201.183.91/) |
|  Figma Mockup | [Initial Project Mockup](https://www.figma.com/design/hTWVkDQys1NVg8Z7n2yyXK/Software-Engineering?node-id=0-1&p=f&t=4nAaHxQFGe30qwF2-0) |
|  Project Documents | [User Personas, Interviews, PRD & Backlog](https://drive.google.com/drive/folders/1maMOySvNugMCGIAmODOntPJsiAVLn2Hl?usp=sharing) |
|  Sphinx Documentation | [https://shayan-ashish-chakraborty.github.io/dublin-bikes-team20/](https://shayan-ashish-chakraborty.github.io/dublin-bikes-team20/) |
 
---
 
##  Table of Contents
 
- [Overview](#overview)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Environment Variables](#environment-variables)
- [Setup & Installation](#setup--installation)
- [Running the App](#running-the-app)
- [Team Logs](#team-logs)
---
 
## Overview
 
Dublin Bikes is a software engineering group project that provides Dublin citizens and tourists with a unified platform to:
 
- View **live station availability** for all JCDecaux Dublin Bikes stations on an interactive map
- Check **current weather** and a **5-day forecast** powered by OpenWeatherMap
- Plan **journeys** from station to station with Google Maps routing
- Get **AI-powered bike availability forecasts** using machine learning
- Chat with an **AI assistant** (Gemini / Grok) for bike and city queries
---
 
## Features
 
-  **Live Station Map** — Real-time bike and stand availability across all Dublin stations
-  **Weather Integration** — Current conditions and 3-hour/5-day forecasts
-  **Journey Planner** — Route planning with pickup/drop-off station suggestions
-  **ML Forecasting** — Predicted station availability using trained scikit-learn models
-  **AI Chatbot** — Conversational assistant powered by Google Gemini and Grok
-  **User Authentication** — Register/login with session management (Flask-WTF + Werkzeug)
---
 
## Tech Stack
 
| Layer | Technology |
|---|---|
| Backend | Python 3, Flask 3.1 |
| Database | MySQL (via SQLAlchemy + PyMySQL) |
| Frontend | HTML/CSS/JavaScript, Jinja2 templates |
| Maps | Google Maps JavaScript API |
| Bike Data | JCDecaux API |
| Weather | OpenWeatherMap API |
| ML | scikit-learn, pandas, numpy |
| AI Chat | Google Gemini API, Grok API |
| Deployment | AWS EC2 |
| Docs | Sphinx |
 
---
 
## Project Structure
 
```
dublin-bikes-team20/
│
├── app.py                          # Application entry point (Flask factory + CORS)
├── requirement.txt                 # Python dependencies
├── environment_conda.yml           # Conda environment definition
├── ec2_conect.txt                  # EC2 SSH connection notes
│
├── main_project/                   # Core application package
│   ├── __init__.py                 # App factory (create_app)
│   ├── config.py                   # Centralised config (reads var.env / .env)
│   ├── db.py                       # SQLAlchemy database setup
│   ├── var.env                     # Environment variables (see section below)
│   │
│   ├── auth/                       # User authentication blueprint
│   │   ├── auth.py                 # Login, register, logout routes
│   │   ├── create_auth_db.py       # Auth DB initialisation script
│   │   └── __init__.py
│   │
│   ├── home/                       # Home page blueprint
│   │   ├── home.py                 # Index route
│   │   └── __init__.py
│   │
│   ├── station/                    # Bike station blueprint
│   │   ├── routes.py               # Station map routes
│   │   ├── services.py             # JCDecaux API service layer
│   │   ├── bikes_original.py       # Original scraper/legacy helpers
│   │   └── __init__.py
│   │
│   ├── weather/                    # Weather blueprint
│   │   ├── routes.py               # Weather page routes
│   │   ├── services.py             # OpenWeatherMap service layer
│   │   └── __init__.py
│   │
│   ├── journey/                    # Journey planner blueprint
│   │   ├── routes.py               # Journey planning routes
│   │   ├── api.py                  # Journey API endpoints
│   │   ├── services.py             # Route/station calculation logic
│   │   └── __init__.py
│   │
│   ├── bike_forecast/              # ML availability forecast blueprint
        ├── models/                 # All ML model stored
│   │   ├── routes.py               # Forecast API routes
│   │   └── __init__.py
│   │
│   ├── chat/                       # AI chatbot blueprint
│   │   ├── chat_gemini.py          # Google Gemini integration
│   │   ├── chat_grok.py            # Grok/Groq integration
│   │   ├── var.env                 # Chat-specific env overrides
│   │   └── __init__.py
│   │
│   ├── templates/                  # Jinja2 HTML templates
│   │   ├── base.html               # Base layout with nav/footer
│   │   ├── index.html              # Home / station map page
│   │   ├── stations.html           # Station list view
│   │   ├── weather.html            # Weather page
│   │   ├── Journey.html            # Journey planner page
│   │   ├── login.html              # Login form
│   │   └── register.html           # Registration form
│   │
│   ├── static/
│   │   ├── css/
│   │   │   ├── style.css           # Global styles
│   │   │   ├── stations.css        # Station map styles
│   │   │   ├── journey.css         # Journey planner styles
│   │   │   └── ml.css              # ML forecast styles
│   │   ├── js/
│   │   │   ├── main.js             # Shared JS utilities
│   │   │   ├── stations.js         # Station map logic
│   │   │   ├── journey.js          # Journey planner logic
│   │   │   └── MLbikes.js          # ML forecast UI
│   │   └── images/
│   │       ├── loginbg.png
│   │       └── icons/              # SVG icons (bike, weather, map, etc.)
│   │
│   ├── notebooks/                  # Data science & model training
│   │   ├── bike_forecasting.ipynb  # Main forecasting notebook
│   │   ├── sktime_forecasting.ipynb
│   │   └── final_merged_data.csv   # Merged training dataset
│   │
│   └── bash_scripts/
│       ├── create_db.sh            # DB creation helper script
│       └── scrapper.sh             # Data scraping cron script
│
├── sprint1_webscrappers/           # Sprint 1 JCDecaux scraper prototypes
│   └── jcdecaux_api/
│       ├── create-db-jcdecaux.py
│       ├── get-station.py
│       ├── jc_decaux_extract_info_from_json.py
│       ├── jc_decaux_local_download.py
│       ├── jc_decaux_text_to_db_dynamic.py
│       ├── jc_decaux_text_to_db_static.py
│       └── python-basic-db.py
│
├── main_project/ec2/
│   └── dublin-bike.pem             # EC2 SSH key (keep private — do not commit)
│
└── Logs/                           # Individual team member dev logs
    ├── Jialin/
    ├── Leah/
    ├── Sean/
    └── Shayan/
```
 
---
 
## Environment Variables
 
The application reads configuration from `main_project/var.env`. **Never commit real credentials to version control**.
 
```env
#  DATABASE CONFIG 
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_HOST=127.0.0.1
DB_PORT=3306
DB_NAME_JCDECAUX=local_databasejcdecaux
DB_NAME_WEATHER=local_databaseopenweather
 
#  EXTERNAL API KEYS 
JCDECAUX_API_KEY=your_jcdecaux_api_key
OPENWEATHER_API_KEY=your_openweather_api_key
GOOGLE_MAPS_API_KEY=your_google_maps_api_key
 
#  JCDECAUX ENDPOINTS 
STATIONS_URI=https://api.jcdecaux.com/vls/v1/stations
 
#  OPENWEATHERMAP ENDPOINTS 
CITY=Dublin
LAT=53.3498
LON=-6.2603
CURRENT_WEATHER_URI=https://api.openweathermap.org/data/2.5/weather
FORECAST_WEATHER_URI=https://api.openweathermap.org/data/2.5/forecast
 
#  FLASK 
FLASK_SECRET_KEY=your_random_secret_key
FLASK_ENV=development          # set to "production" on EC2
 
# AI CHATBOT 
GEMINI_API_KEY=your_gemini_api_key
GROQ_API_KEY=your_groq_api_key
```
 
| Variable | Description |
|---|---|
| `DB_USER` / `DB_PASSWORD` | MySQL credentials |
| `DB_HOST` / `DB_PORT` | MySQL host (use `127.0.0.1` locally) |
| `DB_NAME_JCDECAUX` | Database storing station data |
| `DB_NAME_WEATHER` | Database storing weather data |
| `JCDECAUX_API_KEY` | From [developer.jcdecaux.com](https://developer.jcdecaux.com) |
| `OPENWEATHER_API_KEY` | From [openweathermap.org](https://openweathermap.org/api) |
| `GOOGLE_MAPS_API_KEY` | From [Google Cloud Console](https://console.cloud.google.com) |
| `FLASK_SECRET_KEY` | Any long random string for session signing |
| `GEMINI_API_KEY` | Powers the Gemini AI chatbot |
| `GROQ_API_KEY` | Powers the Grok AI chatbot |
| `CORS_ORIGINS` | Restrict API CORS origins (defaults to `*`) |
 
---
 
## Setup & Installation
 
### Prerequisites
 
- Python 3.10+
- MySQL 8+
- Git
### 1. Clone the repository
 
```bash
git clone https://github.com/shayan-ashish-chakraborty/dublin-bikes-team20.git
cd dublin-bikes-team20
```
 
### 2. Create and activate a virtual environment
 
```bash
# Using venv
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
 
# Or using Conda
conda env create -f environment_conda.yml
conda activate dublin-bikes
```
 
### 3. Install dependencies
 
```bash
pip install -r requirement.txt
```
 
### 4. Configure environment variables
 
```bash
cp main_project/var.env.example main_project/var.env
# Edit main_project/var.env and fill in your credentials
```
 
### 5. Initialise the databases
 
```bash
# Create MySQL databases
bash main_project/bash_scripts/create_db.sh
 
# Create the auth (users) database
python main_project/auth/create_auth_db.py
```
 
---
 
## Running the App
 
```bash
# From the project root
python app.py
```
 
The app will start on `http://0.0.0.0:8000` by default. You can override the host and port:
 
```bash
HOST=127.0.0.1 PORT=5000 python app.py
```
 
---
 
## Team Logs
 
Individual development logs are stored per-member under the `Logs/` directory:
 
- `Logs/Jialin/`
- `Logs/Leah/`
- `Logs/Sean/`
- `Logs/Shayan/`
---
 
##  License
 
This project was developed as part of the UCD Software Engineering module. All rights reserved by Team 20.