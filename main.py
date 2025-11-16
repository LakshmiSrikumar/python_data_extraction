import csv
import re

from supabase_client import supabase

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

service=Service(executable_path="chromedriver.exe")
driver=webdriver.Chrome(service=service)
wait = WebDriverWait(driver, 15)
driver.maximize_window()

contest_link="https://www3.shoalhaven.nsw.gov.au/masterviewUI/modules/ApplicationMaster/Default.aspx"

driver.get(contest_link)


#Step 1 - Step 4
agree_btn = driver.find_element(By.ID,"ctl00_cphContent_ctl01_btnOk")
agree_btn.click()

da_btn = driver.find_element(By.XPATH, "//li[@class='rmItem']//span[normalize-space()='DA Tracking']")
da_btn.click()

adv_search_btn = driver.find_element(By.XPATH, "//span[@class='rtsTxt' and text()='Advanced Search']")
adv_search_btn.click()

from_date_btn = driver.find_element(By.ID, "ctl00_cphContent_ctl00_ctl03_dateInput_text")
from_date_btn.send_keys("01/09/2025")

to_date_btn = driver.find_element(By.ID,"ctl00_cphContent_ctl00_ctl05_dateInput_text")
to_date_btn.send_keys("30/09/2025")

search_btn = driver.find_element(By.ID, "ctl00_cphContent_ctl00_btnSearch")
search_btn.click()

#######

# Functions for scraping, cleaning, and saving into csv
applications=[]

def scrape_link(link):
    driver.get(link)
    da_number = driver.find_element(By.ID, "ctl00_cphContent_ctl00_lblApplicationHeader")
    details_text = driver.find_element(By.ID, "lblDetails").text.strip()
    decision_text = driver.find_element(By.ID, "lblDecision")
    categories_text = driver.find_element(By.ID, "lblCat")
    properties_text = driver.find_element(By.ID, "lblProp")
    people_text = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "lblPeople"))).get_attribute("textContent").strip()
    progress_text = driver.find_element(By.CLASS_NAME,"shTableHead")
    fees_elem=driver.find_element(By.ID, "lblFees")
    fees_text = fees_elem.get_attribute("textContent").strip()
    documents_text = driver.find_element(By.ID, "lblDocs")
    contact_council_text = driver.find_element(By.ID, "lbl91").text.strip()

    # Data cleaning Rules
    if fees_text == "No fees recorded against this application.":
        fees_text = "Not required"
    else:
        try:
            total_element = driver.find_element(By.XPATH, "//tr[@class='shTableAlt']//td[@align='right']")
            fees_text = driver.execute_script("return arguments[0].childNodes[0].textContent.trim();", total_element)
        except:
            fees_text = "Not found"

    if contact_council_text == "Application Is Not on exhibition, please call Council on 1300 293 111 if you require assistance.":
        contact_council_text = "Not required"

    lines = details_text.split("\n")
    clean_description = re.sub(r'(?i)description\s*:\s*', '', lines[0]).strip()
    submitted_date = ""
    if len(lines) > 1:
        match = re.search(r"(\d{1,2}/\d{1,2}/\d{4})", lines[1])
        if match:
            submitted_date = match.group(1)

    app_data = {
    "DA_Number": da_number.text.strip(),
    "Detail_URL": link,
    "Description": clean_description,
    "Submitted_Date": submitted_date,
    "Decision": decision_text.text.strip(),
    "Categories": categories_text.text.strip(),
    "Property_Address": properties_text.text.strip(),
    "Applicant": people_text.replace("Applicant: ",""),
    "Progress": progress_text.text.strip(),
    "Fees": fees_text,
    "Documents": documents_text.text.strip(),
    "Contact_Council": contact_council_text
    }
    return app_data

def save_to_csv(filename="output.csv"):
    if not applications:
        print("No data to save.")
        return

    headers = ["DA_Number","Detail_URL","Description","Submitted_Date","Decision","Categories","Property_Address","Applicant","Progress","Fees","Documents","Contact_Council"]

    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(applications)

    print(f"Saved {len(applications)} records to {filename}")


def insert_into_supabase(app_data):
    supabase.table("da_records").insert(app_data).execute()

###################

#Step 5 : Loading Data
record_links = []
page = 1

while True:
    print(f"Extracting links from page {page}...")
    show_buttons = wait.until(
        EC.presence_of_all_elements_located(
            (By.XPATH, "//a[img[@alt='Click here to view full details']]")
        )
    )
    for btn in show_buttons:
        href = btn.get_attribute("href")
        if href:
            record_links.append(href.strip())

    # Go to next page if available
    try:
        next_btn = driver.find_element(By.XPATH,"//input[@title='Next Page']")
        if not next_btn.is_enabled():
            break
        next_btn.click()
        wait.until(EC.staleness_of(show_buttons[0]))
        page += 1
    except Exception:
        break
total = len(record_links)
print(f"Extracted {total} unique record URLs.")

# Step 6 : Scraping and cleaning data
for index, link in enumerate(record_links, start=1):
    try:
        print(f"\nScraping {index}/{total}: {link}")
        data = scrape_link(link)
        applications.append(data)
        supabase.table("da_records").insert([data]).execute()

    except Exception as e:
        print(f"Error scraping {index}: {link} --> {e}")


#TC1 =scrape_link("https://www3.shoalhaven.nsw.gov.au/masterviewUI/modules/ApplicationMaster/default.aspx?page=wrapper&key=734852&propkey=29524")
#TC2 =scrape_link("https://www3.shoalhaven.nsw.gov.au/masterviewUI/modules/ApplicationMaster/default.aspx?page=wrapper&key=732614&propkey=78731")
#print(TC1)

#Step 7: Saving into CSV
save_to_csv()
#insert_into_supabase(applications)
driver.quit()