import requests
import json
import sqlalchemy as sqla
from sqlalchemy import create_engine
import traceback
import glob
import os
from pprint import pprint
import simplejson as json
import time
from IPython.display import display
from dotenv import load_dotenv

if os.path.exists("var.env"):
    load_dotenv(dotenv_path="var.env")

USER = os.getenv("DB_USER")
PASSWORD = os.getenv("DB_PASSWORD")
PORT = os.getenv("DB_PORT")
DB = os.getenv("DB_NAME_JCDECAUX")
URI = os.getenv("DB_HOST")

connection_string = "mysql+pymysql://{}:{}@{}:{}".format(USER, PASSWORD, URI, PORT)

engine = create_engine(connection_string, echo = True)

sql = """
CREATE DATABASE IF NOT EXISTS {};
""".format(DB)

engine.execute(sql)

for res in engine.execute("SHOW VARIABLES;"):
    print(res)
