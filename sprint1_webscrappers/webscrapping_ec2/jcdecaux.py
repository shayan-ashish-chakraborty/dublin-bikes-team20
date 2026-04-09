from sprint1_webscrappers.webscrapping_ec2.jc_decaux_text_to_db_dynamic import db_connection, jcdecaux_to_db
import time
engine = db_connection()
while True:
    with engine.begin() as conn:
        jcdecaux_to_db(engine)
    time.sleep(5*60)