from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import smtplib
import traceback
import requests
import time
import re


class TimesheetBot:
    def __init__(self):
        # Email
        self.SENDER_EMAIL = "Input sender email"
        self.SENDER_PASSWORD = "Input generated password"
        self.RECEIVER_EMAIL = "Input receiver email"
        self.SMTP_SERVER = "smtp.gmail.com"
        self.SMTP_PORT = 587

        # PSA credentials
        self.USERNAME = "input username"
        self.PASSWORD = "input password"
        self.TIMESHEET_URL = "URL for the timesheet(PSA)"

        # Cache
        self.HOLIDAYS_CACHE = {}
        self.PUBLIC_HOLIDAY_ROW_INDEX = 16

        # Driver
        self.driver = None

    # Browser / Login
    def launch_edge(self):
        options = webdriver.EdgeOptions()
        options.add_argument("--start-maximized")
        self.driver = webdriver.Edge(options=options)
        print("Launched Edge browser")

    def login(self):
        driver = self.driver
        print("Navigating to timesheet portal...")
        driver.get(self.TIMESHEET_URL)
        wait = WebDriverWait(driver, 20)
        wait.until(lambda d: d.execute_script("return document.readyState") == "complete")

        try:
            username_input = wait.until(EC.presence_of_element_located((By.ID, "userid")))
            password_input = wait.until(EC.presence_of_element_located((By.ID, "pwd")))
            username_input.clear()
            username_input.send_keys(self.USERNAME)
            password_input.clear()
            password_input.send_keys(self.PASSWORD)
            sign_in_button = wait.until(EC.element_to_be_clickable((By.NAME, "Submit")))
            sign_in_button.click()
            print("Logged in successfully.")
        except Exception as e:
            print(f"Login failed: {e}")

    def get_holidays_from_nager(self, year):
        if year in self.HOLIDAYS_CACHE:
            return self.HOLIDAYS_CACHE[year]
        url = f"https://date.nager.at/api/v3/PublicHolidays/{year}/PH"
        try:
            resp = requests.get(url, timeout=20)
            resp.raise_for_status()
            data = resp.json()
            dates = {item['date'] for item in data}
            self.HOLIDAYS_CACHE[year] = dates
            return dates
        except Exception as e:
            print(f"Nager API failed: {e}")
            return set()

    def get_holidays_from_gazette(self):
        url = "https://www.officialgazette.gov.ph/nationwide-holidays/"
        try:
            resp = requests.get(url, timeout=20)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, 'html.parser')
            text = soup.get_text(" ", strip=True)
            date_matches = re.findall(r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}", text)
            parsed = set()
            for d in date_matches:
                try:
                    parsed.add(datetime.strptime(d, "%B %d, %Y").date().isoformat())
                except:
                    continue
            return parsed
        except Exception as e:
            print(f"Gazette fetch failed: {e}")
            return set()

    def get_combined_holidays(self, year):
        nager = self.get_holidays_from_nager(year)
        gazette = self.get_holidays_from_gazette()
        return nager.union(gazette)

    def click_element_in_iframes(self, element_id):
        driver = self.driver
        wait = WebDriverWait(driver, 15)
        frames = driver.find_elements(By.TAG_NAME, "iframe")
        for frame in frames:
            driver.switch_to.frame(frame)
            try:
                btn = wait.until(EC.element_to_be_clickable((By.ID, element_id)))
                btn.click()
                driver.switch_to.default_content()
                return True
            except:
                driver.switch_to.default_content()
                continue
        return False

    def click_my_time_reports(self):
        print("Clicking 'My Time Reports'...")
        wait = WebDriverWait(self.driver, 20)
        my_time_reports = wait.until(
            EC.element_to_be_clickable((By.XPATH, "//*[text()='My Time Reports']"))
        )
        my_time_reports.click()

    def click_add(self):
        print("Clicking 'Add' button...")
        if not self.click_element_in_iframes("PTS_CFG_CL_WRK_PTS_ADD_BTN"):
            print("Could not find Add button.")

    def click_open_blank_timesheet(self):
        print("Clicking 'Open Blank Time Report'...")
        if not self.click_element_in_iframes("EX_ICLIENT_WRK_OK_PB"):
            print("Could not find 'Open Blank Time Report' button.")


    def fill_training_hours(self):
        driver = self.driver
        wait = WebDriverWait(driver, 20)
        driver.switch_to.default_content()

        frames = driver.find_elements(By.TAG_NAME, "iframe")
        target_frame = None
        for frame in frames:
            driver.switch_to.frame(frame)
            try:
                if driver.find_elements(By.ID, "POL_TIME2$1"):
                    target_frame = frame
                    driver.switch_to.default_content()
                    break
            except:
                driver.switch_to.default_content()
                continue

        if not target_frame:
            print("Could not find Training iframe.")
            return False

        wait.until(EC.frame_to_be_available_and_switch_to_it(target_frame))
        today = datetime.now().date()
        start_of_week = today - timedelta(days=today.weekday())
        holidays = self.get_combined_holidays(today.year)

        training_ids = [f"POL_TIME{2+i}$1" for i in range(5)]
        holiday_ids = [f"POL_TIME{2+i}$16" for i in range(5)]
        leave_groups = [
            [f"POL_TIME{2+i}${j}" for i in range(5)]
            for j in range(17, 30)
        ]

        for i in range(5):
            current_day = start_of_week + timedelta(days=i)
            current_iso = current_day.isoformat()

            # skip weekends
            if current_day.weekday() >= 5:
                continue

            # check leave
            leave_found = False
            for leave_ids in leave_groups:
                try:
                    el = driver.find_element(By.ID, leave_ids[i])
                    if el.get_attribute("value").strip():
                        leave_found = True
                        print(f"{current_day}: Leave detected, skipping.")
                        break
                except:
                    continue

            if leave_found:
                continue

            # fill depending on holiday
            try:
                if current_iso in holidays:
                    el = wait.until(EC.presence_of_element_located((By.ID, holiday_ids[i])))
                    el.clear()
                    el.send_keys("8")
                    print(f"{current_day}: Public holiday — filled 8 on {holiday_ids[i]}")
                else:
                    el = wait.until(EC.presence_of_element_located((By.ID, training_ids[i])))
                    el.clear()
                    el.send_keys("8")
                    print(f"{current_day}: Workday — filled 8 on {training_ids[i]}")
            except Exception as e:
                print(f"Could not fill for {current_day}: {e}")

        driver.switch_to.default_content()
        return True


    def refresh_page(self):
        print("Clicking 'Refresh' button...")
        self.click_element_in_iframes("UC_EX_WRK_REFRESH")

    def submit_timesheet(self):
        print("Submitting timesheet...")
        self.click_element_in_iframes("EX_TIME_HDR_WRK_PB_SUBMIT")

    def confirm_ok(self):
        print("Confirming OK...")
        self.click_element_in_iframes("#ICSave")


    def send_email(self, subject, body):
        try:
            msg = MIMEMultipart()
            msg["From"] = self.SENDER_EMAIL
            msg["To"] = self.RECEIVER_EMAIL
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain"))

            with smtplib.SMTP(self.SMTP_SERVER, self.SMTP_PORT) as server:
                server.starttls()
                server.login(self.SENDER_EMAIL, self.SENDER_PASSWORD)
                server.send_message(msg)
            print(f"Email sent successfully to {self.RECEIVER_EMAIL}")
        except Exception as e:
            print(f"Failed to send email: {e}")

    def run(self):
        try:
            self.launch_edge()
            self.login()
            time.sleep(5)
            self.click_my_time_reports()
            time.sleep(1)
            self.click_add()
            time.sleep(1)
            self.click_open_blank_timesheet()
            time.sleep(2)
            self.fill_training_hours()
            time.sleep(3)
            self.refresh_page()
            time.sleep(3)
            self.submit_timesheet()
            time.sleep(30)
            self.confirm_ok()
            time.sleep(5)
            print("Timesheet auto-filled successfully!")
            self.send_email(
                "Timesheet Automation Successful",
                "Your timesheet has been successfully submitted for this week."
            )
        except Exception:
            error_msg = traceback.format_exc()
            print(error_msg)
            self.send_email("Timesheet Auto-Fill Failed", error_msg)
        finally:
            print("Closing browser.")
            if self.driver:
                self.driver.quit()


if __name__ == "__main__":
    bot = TimesheetBot()
    bot.run()

