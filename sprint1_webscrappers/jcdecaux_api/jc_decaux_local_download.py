####################DOWNLOAD from JCDECAUX###############
import requests
import traceback
import datetime
import time
import os
from dotenv import load_dotenv


# Data are in dbinfo.py


# Will be used to store text in a file
def write_to_file(text):
   
    # I first need to create a folder data where the files will be stored.
    
    if not os.path.exists('data'):
        os.mkdir('data')
        print("Folder 'data' created!")
    else:
        print("Folder 'data' already exists.")

    # now is a variable from datetime, which will go in {}.
    # replace is replacing white spaces with underscores in the file names
    now = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    with open(f"data/bikes_{now}.json", "w") as f:
        f.write(text)

# Empty for now
def write_to_db(text):
    return 0

def main():
    while True:
        load_dotenv(dotenv_path="var.env")
        try:
            r = requests.get(os.getenv('STATIONS_URI'), params={"apiKey": os.getenv('JCDECAUX_API_KEY'), "contract": os.getenv('CITY')})
            print(r)
            write_to_file(r.text)
            time.sleep(5*60)
        except:
            print(traceback.format_exc())

# CTRL + Z to stop it
main()    