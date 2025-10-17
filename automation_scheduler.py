import schedule
import time
from main import main

def run_main_script():
    main()


schedule.every().friday.at("9:00").do(run_main_script)
while True:
    schedule.run_pending()
    time.sleep(1)