import os
import requests
import json
from dotenv import load_dotenv

if os.path.exists("var.env"):
    load_dotenv(dotenv_path="var.env")

r = requests.get(os.getenv('STATION_URI'), params={"apiKey": os.getenv('JCDECAUX_API_KEY'), "contract": os.getenv('CITY')})

data = json.loads(r.text)
print(json.dumps(data, indent=4))