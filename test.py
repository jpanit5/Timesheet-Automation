from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

# -------------------------
# CONFIGURATION
# -------------------------
USERNAME = "" # input your credentials here
PASSWORD = "" # input your credentials here
TIMESHEET_URL = "" # input timesheet portal URL here
# -------------------------

def launch_edge():
    """Launches Edge browser."""
    options = webdriver.EdgeOptions()
    options.add_argument("--start-maximized")
    driver = webdriver.Edge(options=options)
    return driver

def login(driver):
    print("Navigating to timesheet portal...")
    driver.get(TIMESHEET_URL)

    wait = WebDriverWait(driver, 20)
    wait.until(lambda d: d.execute_script("return document.readyState") == "complete")
    print("Page loaded.")

    try:
        username_input = wait.until(EC.presence_of_element_located((By.ID, "userid")))
        password_input = wait.until(EC.presence_of_element_located((By.ID, "pwd")))
        print("Found login fields.")

        username_input.clear()
        username_input.send_keys(USERNAME)
        password_input.clear()
        password_input.send_keys(PASSWORD)

        sign_in_button = wait.until(EC.element_to_be_clickable((By.NAME, "Submit")))
        sign_in_button.click()
        print("Credentials entered and login submitted.")
    except Exception as e:
        print(f"Login failed: {e}")

def click_my_time_reports(driver):
    print("Looking for 'My Time Reports'...")
    wait = WebDriverWait(driver, 15)
    try:
        my_time_reports = wait.until(
            EC.element_to_be_clickable((By.XPATH, "//*[text()='My Time Reports']"))
        )
        my_time_reports.click()
        print("Clicked 'My Time Reports' successfully!")
    except Exception as e:
        print(f"Could not click 'My Time Reports': {e}")
        with open("page_snapshot_my_time.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)

def click_add(driver):
    print("Looking for 'Add' button in iframes...")
    wait = WebDriverWait(driver, 20)
    frames = driver.find_elements(By.TAG_NAME, "iframe")
    print(f"Found {len(frames)} iframes. Searching each for Add button...")

    add_clicked = False
    for frame in frames:
        driver.switch_to.frame(frame)
        try:
            add_button = wait.until(
                EC.element_to_be_clickable((By.ID, "PTS_CFG_CL_WRK_PTS_ADD_BTN"))
            )
            add_button.click()
            print("Clicked 'Add' button successfully!")
            add_clicked = True
            driver.switch_to.default_content()
            break
        except:
            driver.switch_to.default_content()
            continue

    if not add_clicked:
        print("Could not find 'Add' button in any iframe.")
        with open("page_snapshot_add.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)

def click_open_blank_timesheet(driver):
    print("Looking for 'Open a Blank Time Report' button in iframes...")
    wait = WebDriverWait(driver, 20)
    frames = driver.find_elements(By.TAG_NAME, "iframe")
    print(f"Found {len(frames)} iframes. Searching each for Open a Blank Time Report button...")

    open_clicked = False
    for frame in frames:
        driver.switch_to.frame(frame)
        try:
            open_button = wait.until(
                EC.element_to_be_clickable((By.ID, "EX_ICLIENT_WRK_OK_PB"))
            )
            open_button.click()
            print("Clicked 'Open a Blank Time Report' button successfully!")
            open_clicked = True
            driver.switch_to.default_content()
            break
        except:
            driver.switch_to.default_content()
            continue

    if not open_clicked:
        print("Could not find 'Open a Blank Time Report' button in any iframe.")
        with open("page_snapshot_add.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)

def fill_training_hours(driver):
    print("Searching for 'Training' row in all iframes...")
    wait = WebDriverWait(driver, 20)
    driver.switch_to.default_content()

    frames = driver.find_elements(By.TAG_NAME, "iframe")
    print(f"Found {len(frames)} iframes. Searching for Training inputs...")

    success = False
    for frame in frames:
        driver.switch_to.frame(frame)
        try:
            test_input = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.ID, "POL_TIME2$1"))
            )
            print("Found Training input field in this iframe.")
            success = try_fill_training_inputs(driver, wait)
            driver.switch_to.default_content()
            break
        except:
            driver.switch_to.default_content()
            continue

    if not success:
        print("Could not find Training row in any iframe.")
        with open("page_snapshot_training.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)

def try_fill_training_inputs(driver, wait):
    try:
        input_ids = ["POL_TIME2$1", "POL_TIME3$1", "POL_TIME4$1", "POL_TIME5$1", "POL_TIME6$1"]
        public_holidays_ids = ["POL_TIME2$16", "POL_TIME3$16", "POL_TIME4$16", "POL_TIME5$16", "POL_TIME6$16"]
        vacation_leaves_ids = ["POL_TIME2$17", "POL_TIME3$17", "POL_TIME4$17", "POL_TIME5$17", "POL_TIME6$17"]
        sick_leaves_ids = ["POL_TIME2$18", "POL_TIME3$18", "POL_TIME4$18", "POL_TIME5$18", "POL_TIME6$18"]
        exam_study_leaves_ids = ["POL_TIME2$20", "POL_TIME3$20", "POL_TIME4$20", "POL_TIME5$20", "POL_TIME6$20"]
        bereavement_leaves_ids = ["POL_TIME2$21", "POL_TIME3$21", "POL_TIME4$21", "POL_TIME5$21", "POL_TIME6$21"]
        legal_reasons_leaves_ids = ["POL_TIME2$22", "POL_TIME3$22", "POL_TIME4$22", "POL_TIME5$22", "POL_TIME6$22"]
        marriage_leaves_ids = ["POL_TIME2$23", "POL_TIME3$23", "POL_TIME4$23", "POL_TIME5$23", "POL_TIME6$23"]
        paternity_leaves_ids = ["POL_TIME2$24", "POL_TIME3$24", "POL_TIME4$24", "POL_TIME5$24", "POL_TIME6$24"]
        administrative_leaves_ids = ["POL_TIME2$25", "POL_TIME3$25", "POL_TIME4$25", "POL_TIME5$25", "POL_TIME6$25"]
        unpaid_leaves_ids = ["POL_TIME2$26", "POL_TIME3$26", "POL_TIME4$26", "POL_TIME5$26", "POL_TIME6$26"]
        carer_leaves_ids = ["POL_TIME2$27", "POL_TIME3$27", "POL_TIME4$27", "POL_TIME5$27", "POL_TIME6$27"]
        family_member_leaves_ids = ["POL_TIME2$28", "POL_TIME3$28", "POL_TIME4$28", "POL_TIME5$28", "POL_TIME6$28"]
        paid_parental_leaves_ids = ["POL_TIME2$29", "POL_TIME3$29", "POL_TIME4$29", "POL_TIME5$29", "POL_TIME6$29"]

        for i in range(len(input_ids)):
            leave_filled = False
            public_holiday_box = wait.until(EC.presence_of_element_located((By.ID, public_holidays_ids[i])))
            if public_holiday_box.get_attribute("value").strip():
                leave_filled = True

            vacation_box = wait.until(EC.presence_of_element_located((By.ID, vacation_leaves_ids[i])))
            if vacation_box.get_attribute("value").strip():
                leave_filled = True
            
            sick_box = wait.until(EC.presence_of_element_located((By.ID, sick_leaves_ids[i])))
            if sick_box.get_attribute("value").strip():
                leave_filled = True
            
            exam_study_box = wait.until(EC.presence_of_element_located((By.ID, exam_study_leaves_ids[i])))
            if exam_study_box.get_attribute("value").strip():
                leave_filled = True
            
            bereavement_leave_box = wait.until(EC.presence_of_element_located((By.ID, bereavement_leaves_ids[i])))
            if bereavement_leave_box.get_attribute("value").strip():
                leave_filled = True
            
            legal_reasons_box = wait.until(EC.presence_of_element_located((By.ID, legal_reasons_leaves_ids[i])))
            if legal_reasons_box.get_attribute("value").strip():
                leave_filled = True
            
            marriage_box = wait.until(EC.presence_of_element_located((By.ID, marriage_leaves_ids[i])))
            if marriage_box.get_attribute("value").strip():
                leave_filled = True
            
            paternity_box = wait.until(EC.presence_of_element_located((By.ID, paternity_leaves_ids[i])))
            if paternity_box.get_attribute("value").strip():
                leave_filled = True
            
            administrative_box = wait.until(EC.presence_of_element_located((By.ID, administrative_leaves_ids[i])))
            if administrative_box.get_attribute("value").strip():   
                leave_filled = True
            
            unpaid_box = wait.until(EC.presence_of_element_located((By.ID, unpaid_leaves_ids[i])))
            if unpaid_box.get_attribute("value").strip():
                leave_filled = True
            
            carer_box = wait.until(EC.presence_of_element_located((By.ID, carer_leaves_ids[i])))
            if carer_box.get_attribute("value").strip():
                leave_filled = True
            
            family_member_box = wait.until(EC.presence_of_element_located((By.ID, family_member_leaves_ids[i])))
            if family_member_box.get_attribute("value").strip():
                leave_filled = True
            
            paid_parental_box = wait.until(EC.presence_of_element_located((By.ID, paid_parental_leaves_ids[i])))
            if paid_parental_box.get_attribute("value").strip():
                leave_filled = True
            
            if leave_filled:
                continue

            input_box = wait.until(EC.presence_of_element_located((By.ID, input_ids[i])))
            input_box.clear()
            input_box.send_keys("8")
            print(f"Filled 8 hours for input ID: {input_ids[i]}")
        
        return True
    except Exception as e:
        print(f"Error filling training inputs: {e}")
        return False

def refresh_page_clicked(driver):
    print("Looking for 'Refresh' button in iframes...")
    wait = WebDriverWait(driver, 20)
    frames = driver.find_elements(By.TAG_NAME, "iframe")
    print(f"Found {len(frames)} iframes. Searching each for Refresh button...")

    refresh_page_clicked = False
    for frame in frames:
        driver.switch_to.frame(frame)
        try:
            refresh_page_clicked = wait.until(
                EC.element_to_be_clickable((By.ID, "UC_EX_WRK_REFRESH"))
            )
            refresh_page_clicked.click()
            print("Clicked 'Refresh' button successfully!")
            refresh_page_clicked = True
            driver.switch_to.default_content()
            break
        except:
            driver.switch_to.default_content()
            continue

    if not refresh_page_clicked:
        print("Could not find 'Refresh' button in any iframe.")
        with open("page_snapshot_add.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)

def submit_time_sheet(driver):
    print("Looking for 'Submit' button in iframes...")
    wait = WebDriverWait(driver, 20)
    frames = driver.find_elements(By.TAG_NAME, "iframe")
    print(f"Found {len(frames)} iframes. Searching each for Submit button...")

    submit_time_sheet = False
    for frame in frames:
        driver.switch_to.frame(frame)
        try:
            submit_time_sheet = wait.until(
                EC.element_to_be_clickable((By.ID, "EX_TIME_HDR_WRK_PB_SUBMIT"))
            )
            submit_time_sheet.click()
            print("Clicked 'Open a Blank Time Report' button successfully!")
            submit_time_sheet = True
            driver.switch_to.default_content()
            break
        except:
            driver.switch_to.default_content()
            continue

    if not submit_time_sheet:
        print("Could not find 'Submit' button in any iframe.")
        with open("page_snapshot_add.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)

def main():
    driver = launch_edge()
    login(driver)
    time.sleep(5)
    click_my_time_reports(driver)
    time.sleep(1)
    click_add(driver)
    time.sleep(1)
    click_open_blank_timesheet(driver)
    time.sleep(2)
    fill_training_hours(driver)
    time.sleep(3)
    refresh_page_clicked(driver)
    time.sleep(3)
    submit_time_sheet(driver)
    time.sleep(30)
    print("Please review or add first the other details you need(eg. hazard pay, OT).")
    time.sleep(60)
    print("Script finished. Browser remains open for inspection.")
    driver.quit()

if __name__ == "__main__":
    main()

