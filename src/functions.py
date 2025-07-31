import flet as ft
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from dotenv import load_dotenv
import os

# Function to switch to a new tab that is not in the review_tabs list
# -----------------------------------------------------------------------------
def switch_to_new_tab(review_tabs, driver):
    all_tabs = driver.window_handles
    first_tab = all_tabs[0]
    all_tabs.pop(0)  # Remove the first handle from the list
  
    # Loop on all_tabs looking for any that does NOT exist in review_tabs and select it
    for handle in all_tabs:
        if handle not in review_tabs:
            print(f"Switching to tab with handle: {handle}")
            # Switch to the new tab       
            driver.switch_to.window(handle)
            print(f"Switched to tab with URL: {driver.current_url}")
            return handle 


# Function to assign the current page to a bookmark list
# -----------------------------------------------------------------------------
def assign_to_bookmark_list(driver, handle, review_tabs):

    driver.switch_to.window(handle)
    print(f"Switched to tab with URL: {driver.current_url}")

    # Click the link with ID 'ctl00_ContentBody_lnkBookmark' to bookmark the page
    bookmark_link = driver.find_element(By.ID, "ctl00_ContentBody_lnkBookmark")
    bookmark_link.click( )

    # The above action will create a new bookmark list tab... switch to it
    bookmarks = switch_to_new_tab(review_tabs, driver)
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "ctl00_ContentBody_Bookmark_ddBookmarkList")))

    # Select the 'HNS 2025' bookmark from the dropdown
    bookmark_dropdown = driver.find_element(By.ID, "ctl00_ContentBody_Bookmark_ddBookmarkList")
    bookmark_dropdown.click( )
    bookmark_option = driver.find_element(By.XPATH, "//option[text()='HNS 2025']")
    bookmark_option.click( )
    
    # Now, create the bookmark 
    create_bookmark_button = driver.find_element(By.ID, "ctl00_ContentBody_Bookmark_btnCreate")
    create_bookmark_button.click( )
    driver.implicitly_wait(2)

    # Close the bookmarks tab that we just used
    driver.close( )


# Function to set the current page for timed publication
# -----------------------------------------------------------------------------
def set_timed_pub(driver, handle, review_tabs):

    driver.switch_to.window(handle)
    print(f"Switched to tab with URL: {driver.current_url}")

    # Wait for the button titled 'Time publish' and click it
    timed_pub_button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CLASS_NAME, "time-publish-btn")))
    timed_pub_button.click( )
    driver.implicitly_wait(1)

    # The above action will open a timed pub pop-up.  Click the ctl00_ContentBody_timePublishButton there.
    # id="timePublishDateInput"
    # id="timePublishTimeSelect"

    # # Wait for the input with ID timePublishDateInput, set its value to '2025-09-20'
    # time_publish_date_input = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "timePublishDateInput")))
    # time_publish_date_input.clear( )
    # time_publish_date_input.send_keys("2025-09-20") # Set the date for timed publication
    # driver.implicitly_wait(1)

    # # Wait for the select with ID timePublishTimeSelect, set its value to '9:00 AM'
    # time_publish_time_select = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "timePublishTimeSelect")))
    # time_publish_time_select.click( )
    # time_publish_time_option = driver.find_element(By.XPATH, "//option[text()='9:00 AM']")
    # time_publish_time_option.click( )
    # driver.implicitly_wait(1)
    
    # Wait for the button with ID ctl00_ContentBody_timePublishButton and click it to confirm the timed publication
    confirm_timed_pub = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, "ctl00_ContentBody_timePublishButton")))
    confirm_timed_pub.click( )
    driver.implicitly_wait(1)

    # Close the tab we just processed
    driver.close( )

# Function to initialize the Selenium WebDriver and perform login
# -----------------------------------------------------------------------------
def initialize_driver( ):

    load_dotenv( )     # Load environment variables from .env file
    password = os.getenv("PASSWORD")

    driver = webdriver.Firefox( )  # Or webdriver.Chrome(), webdriver.Safari()

    # Open the geocaching.com site
    driver.get("https://www.geocaching.com/admin")

    # Store the handle of the main window
    main_window_handle = driver.current_window_handle

    # Wait for the new window to appear (adjust timeout as needed)
    # WebDriverWait(driver, 10).until(EC.number_of_windows_to_be(2))

    # Get all window handles
    all_window_handles = driver.window_handles

    # Now you're in the cookies pop-up window, locate and interact with the NECESSARY/decline button
    popup_button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, "CybotCookiebotDialogBodyButtonDecline")))
    popup_button.click( )

    # Now, fill in necessary login information
    username_field = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "UsernameOrEmail")))
    username_field.send_keys("Iowa.Landmark")
    password_field = driver.find_element(By.ID, "Password")
    password_field.send_keys(password)

    # Click the login button
    login_button = driver.find_element(By.ID, "SignIn")
    login_button.click( )

    # After interacting with the pop-up, switch back to the main window
    driver.switch_to.window(main_window_handle)

    # Open the review queue page and interact with it to open desired tabs
    driver.get("https://www.geocaching.com/admin/queue.aspx?filter=NotHeld&stateid=16&pagesize=20")

    # Return the initialized driver
    return driver


# Start the Selenium driver and perform initial actions
# -----------------------------------------------------------------------------
def start_selenium(driver):
    # Ensure the driver is initialized and the main window is set
    if not driver:
        print("Driver is not initialized. Please run initialize_driver first.")
        return
    
    # Ensure the driver is on the correct page
    if driver.current_url != "https://www.geocaching.com/admin/queue.aspx?filter=NotHeld&stateid=16&pagesize=20":
        print("Driver is not on the correct page. Please navigate to the review queue page first.") 
        return
    
    # Your automation code here (e.g., finding elements, clicking buttons, entering text)
    current_handle = driver.current_window_handle
    review_tabs = driver.window_handles
    first_tab = review_tabs[0]
    review_tabs.pop(0)  # Remove the first handle from the list

    # Return the list of review tabs and the first tab handle
    print(f"Current handle: {current_handle}")
    print(f"Review tabs: {review_tabs}")
    return review_tabs


# Callback function to assign open review tabs to a bookmark list
# -----------------------------------------------------------------------------
def assign_bookmarks(driver):
    review_tabs = start_selenium(driver)

    # Iterate through the remaining handles skipping the first one
    for handle in review_tabs:
        print(f"Switching to tab with handle: {handle}")
        # Switch to the new tab       
        driver.switch_to.window(handle)
        print(f"Switched to tab with URL: {driver.current_url}")

        # Fetch all links in the current tab
        links = driver.find_elements("tag name", "a")
        print(f"Found {len(links)} links in the current tab.")  
        # for link in links:
        #     print(f"Link text: {link.text}, URL: {link.get_attribute('href')}")

        # Perform actions on the links or other elements here
        assign_to_bookmark_list(driver, handle, review_tabs)
        # set_timed_pub(driver, handle, review_tabs)

    # Switch back to the original first tab
    # driver.switch_to.window(first_tab)
    # print(f"Switched back to original tab with URL: {driver.current_url}")

    # Close the window
    driver.execute_script('alert("All done!")')
    # driver.quit( )


# Callback function to set timed pub for all open review tabs
# -----------------------------------------------------------------------------
def timed_pub(driver):
    review_tabs = start_selenium(driver)

    # Iterate through the remaining handles skipping the first one
    for handle in review_tabs:
        print(f"Switching to tab with handle: {handle}")
        # Switch to the new tab       
        driver.switch_to.window(handle)
        print(f"Switched to tab with URL: {driver.current_url}")

        # Fetch all links in the current tab
        links = driver.find_elements("tag name", "a")
        print(f"Found {len(links)} links in the current tab.")  
        # for link in links:
        #     print(f"Link text: {link.text}, URL: {link.get_attribute('href')}")

        # Perform actions on the links or other elements here
        # assign_to_bookmark_list(driver, handle, review_tabs)
        set_timed_pub(driver, handle, review_tabs)

    # Switch back to the original first tab
    # driver.switch_to.window(first_tab)
    # print(f"Switched back to original tab with URL: {driver.current_url}")

    # Close the window
    driver.execute_script('alert("All done!")')
    # driver.quit( )

# Create an expansion tile for the Flet app
# -----------------------------------------------------------------------------
def create_expansion_tile(ft):
    name = "Main ExpansionTile"

    appText = "The app should have opened your Review Queue page in a new browser window. \n" \
                "In THAT window be sure to load only the tabs that you wish to perform bulk functions on.  If your function requires data, like Timed Pub or Bookmarking, be sure to process one tab using that information, close ALL listing tabs, and reload them all BEFORE you click the action button! \n" \

    return ft.Column(
        controls=[
            ft.ExpansionTile(
                title=ft.Text("Review Queue"),
                subtitle=ft.Text("Click to expand or contract instructions"),
                affinity=ft.TileAffinity.PLATFORM,
                maintain_state=True,
                collapsed_text_color=ft.Colors.RED,
                text_color=ft.Colors.RED,
                controls=[ft.ListTile(title=ft.Text(appText))],
            )
        ],
    )    