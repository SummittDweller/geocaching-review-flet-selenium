import flet as ft
from app_refs import (
    bookmark_checkbox_ref,
    bookmark_name_ref,
    timed_pub_checkbox_ref,
    timed_pub_date_ref,
    timed_pub_time_ref,
    disable_with_same_message_checkbox_ref,
    status_text_ref,
    loading_status_ref,
    progress_bar_ref,
    go_button_ref,
    completion_message_ref,
)
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.firefox.options import Options as FirefoxOptions
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

# Function to DISABLE the current page with a log message pasted from the clipboard
# -----------------------------------------------------------------------------
def disable_with_same_message(driver, handle, review_tabs):

    driver.switch_to.window(handle)
    print(f"Switched to tab with URL: {driver.current_url}")

    # Click the link with ID 'ctl00_ContentBody_lnkDisable' to open the log
    disable_link = driver.find_element(By.ID, "ctl00_ContentBody_lnkDisable")
    disable_link.click( )

    # The above action will open a new "disable" log tab... switch to it
    disable_log = switch_to_new_tab(review_tabs, driver)
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "gc-md-editor_md")))

    # Move cursor to the text area and paste the clipboard contents
    text_area = driver.find_element(By.ID, "gc-md-editor_md")
    text_area.click( )
    driver.execute_script("document.execCommand('paste');")  # Paste the clipboard contents 
    driver.implicitly_wait(1)

    # Click the Post button with class 'gc-button-primary submit-button gc-button' to confirm the disable action
    post_button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CLASS_NAME, "gc-button-primary")))
    post_button.click( )
    driver.implicitly_wait(1)   

    # Close the disable log tab that we just used and switch back to the review tab
    driver.close( )
    driver.switch_to.window(handle)


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

    # Select the bookmark from the dropdown
    bookmark_dropdown = driver.find_element(By.ID, "ctl00_ContentBody_Bookmark_ddBookmarkList")
    bookmark_dropdown.click( )
    bookmark_name = (bookmark_name_ref.current.value or "").strip( )
    if not bookmark_name:
        driver.close( )
        raise ValueError("Bookmark list name is required but not set.")

    bookmark_options = driver.find_elements(
        By.XPATH, f"//option[normalize-space()='{bookmark_name}']"
    )
    if not bookmark_options:
        driver.close( )
        raise ValueError(f"Bookmark list '{bookmark_name}' not found.")

    bookmark_options[0].click( )
    
    # Now, create the bookmark 
    create_bookmark_button = driver.find_element(By.ID, "ctl00_ContentBody_Bookmark_btnCreate")
    create_bookmark_button.click( )
    driver.implicitly_wait(2)

    # Close the bookmarks tab that we just used and switch back to the review tab
    driver.close( )
    driver.switch_to.window(handle)


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

    pub_date = (timed_pub_date_ref.current.value or "").strip( )
    pub_time = (timed_pub_time_ref.current.value or "").strip( )

    if not pub_date or not pub_time:
        print("Timed publish date/time not set. Skipping timed publish.")
        driver.close( )
        return

    # Set the date for timed publication
    time_publish_date_input = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "timePublishDateInput"))
    )
    time_publish_date_input.clear( )
    time_publish_date_input.send_keys(pub_date)
    driver.implicitly_wait(1)

    # Set the time for timed publication
    time_publish_time_select = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "timePublishTimeSelect"))
    )
    time_publish_time_select.click( )
    time_publish_time_option = driver.find_element(
        By.XPATH, f"//option[normalize-space()='{pub_time}']"
    )
    time_publish_time_option.click( )
    driver.implicitly_wait(1)
    
    # Wait for the button with ID ctl00_ContentBody_timePublishButton and click it to confirm the timed publication
    confirm_timed_pub = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, "ctl00_ContentBody_timePublishButton")))
    confirm_timed_pub.click( )
    driver.implicitly_wait(1)

    # Close the tab we just processed and switch back to the review tab
    driver.close( )
    driver.switch_to.window(handle)

# Function to initialize the Selenium WebDriver and perform login
# -----------------------------------------------------------------------------
def initialize_driver(page):

    load_dotenv( )     # Load environment variables from .env file
    password = os.getenv("PASSWORD")

    # Update progress
    progress_bar_ref.current.value = 0.1
    loading_status_ref.current.value = "Configuring Firefox..."
    progress_bar_ref.current.update()
    loading_status_ref.current.update()

    # Configure Firefox to use the default profile (which has extensions)
    options = FirefoxOptions()
    options.profile = webdriver.FirefoxProfile()
    
    # Use the default Firefox profile that has extensions installed
    # This allows the Selenium driver to load with your existing extensions
    import platform
    if platform.system() == "Darwin":  # macOS
        profile_path = os.path.expanduser("~/Library/Application Support/Firefox/Profiles")
    elif platform.system() == "Windows":
        profile_path = os.path.expanduser("~/AppData/Roaming/Mozilla/Firefox/Profiles")
    else:  # Linux
        profile_path = os.path.expanduser("~/.mozilla/firefox")
    
    # Find the default profile directory
    if os.path.exists(profile_path):
        import glob
        profiles = glob.glob(os.path.join(profile_path, "*.default*"))
        if profiles:
            default_profile = profiles[0]
            options.profile = webdriver.FirefoxProfile(default_profile)
            print(f"Using Firefox profile: {default_profile}")

    # Update progress
    progress_bar_ref.current.value = 0.3
    loading_status_ref.current.value = "Starting Firefox browser..."
    progress_bar_ref.current.update()
    loading_status_ref.current.update()

    driver = webdriver.Firefox(options=options)

    # Update progress
    progress_bar_ref.current.value = 0.5
    loading_status_ref.current.value = "Loading geocaching.com admin page..."
    progress_bar_ref.current.update()
    loading_status_ref.current.update()

    # Open the geocaching.com site
    driver.get("https://www.geocaching.com/admin")

    # Store the handle of the main window
    main_window_handle = driver.current_window_handle

    # Wait for the new window to appear (adjust timeout as needed)
    # WebDriverWait(driver, 10).until(EC.number_of_windows_to_be(2))

    # Get all window handles
    all_window_handles = driver.window_handles

    # Update progress
    progress_bar_ref.current.value = 0.7
    loading_status_ref.current.value = "Dismissing cookie banner and logging in..."
    progress_bar_ref.current.update()
    loading_status_ref.current.update()

    # Dismiss the cookie banner if present
    _dismiss_cookie_banner(driver)

    # Now, fill in necessary login information
    username_field = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "UsernameOrEmail")))
    username_field.send_keys("Iowa.Landmark")
    password_field = driver.find_element(By.ID, "Password")
    password_field.send_keys(password)

    # Update progress
    progress_bar_ref.current.value = 0.85
    progress_bar_ref.current.update()

    # Click the login button - wait for it to be clickable and not obscured
    login_button = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.ID, "SignIn"))
    )
    # Double-check that the button is not obscured by scrolling into view
    driver.execute_script("arguments[0].scrollIntoView(true);", login_button)
    import time
    time.sleep(0.5)
    login_button.click( )

    # After interacting with the pop-up, switch back to the main window
    driver.switch_to.window(main_window_handle)

    # Update progress
    progress_bar_ref.current.value = 0.95
    loading_status_ref.current.value = "Loading review queue..."
    progress_bar_ref.current.update()
    loading_status_ref.current.update()

    # Open the review queue page and interact with it to open desired tabs
    driver.get("https://www.geocaching.com/admin/queue.aspx?filter=NotHeld&stateid=16&pagesize=20")

    # Final progress update
    progress_bar_ref.current.value = 1.0
    progress_bar_ref.current.update()

    # Return the initialized driver
    return driver


# Helper: dismiss cookie banner if it is blocking clicks
# -----------------------------------------------------------------------------
def _dismiss_cookie_banner(driver):
    try:
        popup_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "CybotCookiebotDialogBodyButtonDecline"))
        )
        popup_button.click( )

        # Wait for the banner/overlay to go away - check for the container to become invisible
        WebDriverWait(driver, 10).until(
            EC.invisibility_of_element_located((By.ID, "CybotCookiebotDialogBodyButtonDecline"))
        )
        
        # Also wait for the entire dialog to be gone
        try:
            WebDriverWait(driver, 10).until(
                EC.invisibility_of_element_located((By.ID, "CybotCookiebotDialog"))
            )
        except TimeoutException:
            pass
        
        # Extra wait to ensure the overlay is truly gone
        import time
        time.sleep(1)
        
    except TimeoutException:
        # Banner not present or already dismissed
        pass


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


# The GO! callback function
# -----------------------------------------------------------------------------
def go(driver, page):
    # Clear status
    status_text_ref.current.value = "Processing..."
    status_text_ref.current.color = "yellow"
    status_text_ref.current.update()

    review_tabs = start_selenium(driver)

    if bookmark_checkbox_ref.current.value:
        bookmark_name = (bookmark_name_ref.current.value or "").strip( )
        if not bookmark_name:
            message = "Bookmark list name is required when 'Add to Bookmark List' is selected."
            print(message)
            status_text_ref.current.value = f"ERROR: {message}"
            status_text_ref.current.color = "red"
            status_text_ref.current.update()
            return

    # Iterate through the remaining handles skipping the first one
    for handle in review_tabs:
        print(f"Switching to tab with handle: {handle}")
        # Switch to the new tab       
        driver.switch_to.window(handle)
        print(f"Switched to tab with URL: {driver.current_url}")

        # Skip tabs that are not review detail pages
        if "review.aspx" not in driver.current_url:
            print(f"Skipping non-review tab: {driver.current_url}")
            continue

        # Fetch all links in the current tab
        links = driver.find_elements("tag name", "a")
        print(f"Found {len(links)} links in the current tab.")  
        # for link in links:
        #     print(f"Link text: {link.text}, URL: {link.get_attribute('href')}")

        # Perform actions on the links or other elements here
        try:
            if bookmark_checkbox_ref.current.value: 
                assign_to_bookmark_list(driver, handle, review_tabs)
            if timed_pub_checkbox_ref.current.value: 
                set_timed_pub(driver, handle, review_tabs)
            if disable_with_same_message_checkbox_ref.current.value:
                disable_with_same_message(driver, handle, review_tabs)
        except Exception as exc:
            message = f"Error: {exc}"
            print(message)
            status_text_ref.current.value = message
            status_text_ref.current.color = "red"
            status_text_ref.current.update()
            # Try to switch back to a valid window
            try:
                all_handles = driver.window_handles
                if all_handles:
                    driver.switch_to.window(all_handles[0])
            except Exception as inner_exc:
                print(f"Error during error handling: {inner_exc}")
            
            # Update button to CLOSE
            def on_close_click(e):
                try:
                    driver.quit()
                except Exception:
                    pass
                import sys
                sys.exit(0)

            go_button_ref.current.text = "CLOSE"
            go_button_ref.current.on_click = on_close_click
            go_button_ref.current.update()
            
            return

    # Switch back to the original first tab
    # driver.switch_to.window(first_tab)
    # print(f"Switched back to original tab with URL: {driver.current_url}")

    # Success
    status_text_ref.current.value = "All done!"
    status_text_ref.current.color = "green"
    status_text_ref.current.update()

    # Update button to CLOSE and change its handler
    def on_close_click(e):
        try:
            driver.quit()
        except Exception:
            pass
        import sys
        sys.exit(0)

    go_button_ref.current.text = "CLOSE"
    go_button_ref.current.on_click = on_close_click
    go_button_ref.current.update()

    # Show completion message
    completion_message_ref.current.value = "Processing complete. Click CLOSE to exit. (The app must be restarted if additional operations are needed.)"
    completion_message_ref.current.update()
    # driver.quit( )

# Functions to check the state of each checkbox
# -----------------------------------------------------------------------------
def bookmark_checkbox_state(e):
    if bookmark_checkbox_ref.current.value:
        print("Bookmark checkbox is checked!")
        return True
    else:
        print("Bookmark checkbox is unchecked.")
        return False

def timed_pub_checkbox_state(e):
    if timed_pub_checkbox_ref.current.value:
        print("Timed pub checkbox is checked!")
        return True
    else:
        print("Timed pub checkbox is unchecked.")
        return False

def disable_with_same_message_checkbox_state(e):
    if disable_with_same_message_checkbox_ref.current.value:
        print("Disable with same message checkbox is checked!")
        return True
    else:
        print("Disable with same message checkbox is unchecked.")
        return False


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