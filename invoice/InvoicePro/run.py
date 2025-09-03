from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
import time

# Path to chromedriver
service = Service(r"C:\Users\Aravind M\Downloads\chromedriver-win64\chromedriver-win64\chromedriver.exe")

driver = webdriver.Chrome(service=service)

# Step 1: Open site
driver.get("http://127.0.0.1:5004/")

time.sleep(2)  # wait for page load

# Step 2: Enter login details
try:
    username = driver.find_element(By.NAME, "admin")  # change if your input field has different 'name' or 'id'
    password = driver.find_element(By.NAME, " RevolutionaryAI2025!")  # adjust locator if needed

    username.send_keys("your_username")
    password.send_keys("your_password")

    # Step 3: Click login button
    login_btn = driver.find_element(By.XPATH, "//button[contains(text(),'Login')]")
    login_btn.click()

    print("✅ Logged in successfully")
except Exception as e:
    print("❌ Login failed:", e)

time.sleep(3)  # wait for redirect after login

# Step 4: Example actions after login
try:
    # Click a button
    some_button = driver.find_element(By.XPATH, "//button[contains(text(),'Upload Song')]")
    some_button.click()
    print("✅ Upload Song button clicked")
except:
    print("❌ Upload Song button not found")

try:
    # Click a link
    some_link = driver.find_element(By.LINK_TEXT, "Home")  # link by text
    some_link.click()
    print("✅ Navigated to Home")
except:
    print("❌ Home link not found")

time.sleep(5)  # keep browser open

driver.quit()
