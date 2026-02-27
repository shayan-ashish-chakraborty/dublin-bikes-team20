from sprint1_webscrappers.webscrapping.jc_decaux_text_to_db_dynamic import data_config, jcdecaux_to_db
import time

while True:
    engine = data_config()
    jcdecaux_to_db(engine)
    time.sleep(5*60)