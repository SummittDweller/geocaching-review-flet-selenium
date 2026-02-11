import flet as ft
from app_refs import (
    bookmark_checkbox_ref,
    bookmark_name_ref,
    timed_pub_checkbox_ref,
    timed_pub_date_ref,
    timed_pub_time_ref,
    timed_pub_increment_ref,
    disable_with_same_message_checkbox_ref,
    disable_with_same_message_text_ref,
    firefox_profile_path_ref,
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
from selenium.common.exceptions import TimeoutException, NoSuchWindowException
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from dotenv import load_dotenv
import os

# Global counter and tracker for timed publishing group
# Tracks which listing in the current timed publishing group is being processed
timed_pub_group_counter = 0
timed_pub_last_actual_time = None  # Tracks the last actual published datetime

# Helper: Convert 12-hour AM/PM time to 24-hour military format
# -----------------------------------------------------------------------------
def _convert_to_military_time(time_str_12hr):
    """Convert '8:00 AM' or '8:00 PM' to '08:00' or '20:00'"""
    from datetime import datetime
    try:
        time_obj = datetime.strptime(time_str_12hr.strip(), "%I:%M %p")
        return time_obj.strftime("%H:%M")
    except ValueError:
        # If format doesn't match, return as-is
        return time_str_12hr


# Helper: Convert military time to 12-hour AM/PM format
# -----------------------------------------------------------------------------
def _convert_to_12hr_format(time_military):
    """Convert '08:00' or '20:00' to '8:00 AM' or '8:00 PM'"""
    from datetime import datetime
    try:
        time_obj = datetime.strptime(time_military.strip(), "%H:%M")
        return time_obj.strftime("%I:%M %p").lstrip("0")
    except ValueError:
        return time_military


# Helper: Check if time is in blackout window (10 PM to 6 AM)
# -----------------------------------------------------------------------------
def _is_in_blackout_window(hour):
    """Returns True if hour is between 22 (10 PM) and 5 (before 6 AM)"""
    return hour >= 22 or hour < 6


# Helper: Calculate next publish time with increment, avoiding blackout window
# -----------------------------------------------------------------------------
def _calculate_next_publish_time(current_date_str, current_time_military, increment_str, list_index, last_actual_datetime=None):
    """
    Calculate the publish time for a listing based on increment.
    Ensures no publishing between 10 PM (22:00) and 6 AM (06:00).
    
    Args:
        current_date_str: Date in YYYY-MM-DD format
        current_time_military: Time in HH:MM format (military/24-hour)
        increment_str: Increment string like "30 minutes", "1 Hour", etc.
        list_index: Which listing in the group (0-based)
        last_actual_datetime: The actual datetime of the last published item (for chaining increments)
    
    Returns:
        Tuple of (date_str, time_military, datetime_obj) for when this item should be published
    """
    from datetime import datetime, timedelta
    
    # Parse increment string to timedelta
    increment_map = {
        "30 minutes": timedelta(minutes=30),
        "1 Hour": timedelta(hours=1),
        "2 Hours": timedelta(hours=2),
        "4 Hours": timedelta(hours=4),
        "6 Hours": timedelta(hours=6),
        "12 Hours": timedelta(hours=12),
        "1 Day": timedelta(days=1),
    }
    
    def _normalize_date_str(date_str):
        try:
            # Handle ISO datetime like 2026-02-11T00:00:00
            return datetime.fromisoformat(date_str).date().isoformat()
        except ValueError:
            return date_str

    normalized_date = _normalize_date_str(current_date_str)

    if increment_str == "None" or list_index == 0:
        # First item uses the specified time, no increment
        target_dt = datetime.strptime(f"{normalized_date} {current_time_military}", "%Y-%m-%d %H:%M")
    else:
        # For subsequent items, add increment to the last actual published time
        if last_actual_datetime is None:
            # Fallback if no last time provided
            target_dt = datetime.strptime(f"{normalized_date} {current_time_military}", "%Y-%m-%d %H:%M")
        else:
            increment = increment_map.get(increment_str, timedelta(0))
            target_dt = last_actual_datetime + increment
    
    # Check if target time is in blackout window (10 PM - 6 AM)
    # If so, adjust to 6 AM of the appropriate day
    while _is_in_blackout_window(target_dt.hour):
        if target_dt.hour >= 22:  # After or at 10 PM, move to 6 AM next day
            target_dt = target_dt.replace(hour=6, minute=0, second=0) + timedelta(days=1)
        else:  # Before 6 AM, move to 6 AM today
            target_dt = target_dt.replace(hour=6, minute=0, second=0)
    
    return (target_dt.strftime("%Y-%m-%d"), target_dt.strftime("%H:%M"), target_dt)


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

    # Record the current tabs before clicking disable
    tabs_before = set(driver.window_handles)
    
    # Click the link with ID 'ctl00_ContentBody_lnkDisable' to open the log
    try:
        disable_link = driver.find_element(By.ID, "ctl00_ContentBody_lnkDisable")
        print("Found disable link, clicking it...")
        disable_link.click( )
    except Exception as e:
        print(f"ERROR: Could not find or click disable link: {e}")
        raise

    # Wait for new tab to appear
    import time
    time.sleep(1)
    
    # Find the NEW tab that was opened and pick the correct one
    tabs_after = set(driver.window_handles)
    new_tabs = list(tabs_after - tabs_before)
    
    if not new_tabs:
        print("ERROR: No new tab appeared after clicking disable link")
        raise Exception("Disable log tab did not open")
    
    disable_log_handle = None
    deadline = time.time() + 12
    while time.time() < deadline and not disable_log_handle:
        for h in new_tabs:
            try:
                driver.switch_to.window(h)
                url = driver.current_url
                if "geocaching.com" in url and "log?logType=22" in url:
                    disable_log_handle = h
                    break
                # If URL not ready, try detecting the editor
                if driver.find_elements(By.ID, "gc-md-editor_md"):
                    disable_log_handle = h
                    break
            except Exception:
                continue
        if not disable_log_handle:
            time.sleep(0.5)
    
    # Fallback: use the first new tab
    if not disable_log_handle:
        disable_log_handle = new_tabs[0]
    
    print(f"New tab found: {disable_log_handle}")
    driver.switch_to.window(disable_log_handle)
    print(f"Switched to disable log tab: {driver.current_url}")
    
    # Wait for the page to actually load (not just about:blank)
    time.sleep(2)
    
    # Dismiss any alert dialogs
    try:
        alert = WebDriverWait(driver, 2).until(EC.alert_is_present())
        print("Alert detected, dismissing it...")
        alert.dismiss()
        time.sleep(0.5)
    except:
        # No alert, continue
        pass
    
    # Wait for the text area to load - retry a few times as page may take time to load
    text_area = None
    for attempt in range(5):
        try:
            WebDriverWait(driver, 3).until(EC.presence_of_element_located((By.ID, "gc-md-editor_md")))
            text_area = driver.find_element(By.ID, "gc-md-editor_md")
            print(f"Text area found on attempt {attempt + 1}")
            break
        except Exception as e:
            current_url = driver.current_url
            print(f"Attempt {attempt + 1}: Text area not found yet. URL: {current_url}")
            if "about:blank" in current_url:
                print("Page still loading, waiting...")
                time.sleep(1)
            else:
                if attempt == 4:  # Last attempt
                    raise
    
    if not text_area:
        raise Exception("Could not locate text area after retries")

    # Move cursor to the text area and paste the provided message
    try:
        text_area.click( )
        print("Text area clicked")
    except Exception as e:
        print(f"ERROR: Could not click text area: {e}")
        raise
    
    disable_message = (disable_with_same_message_text_ref.current.value or "").strip( )
    if not disable_message:
        driver.close( )
        raise ValueError("Disable message is required when 'Disable with Same Message' is selected.")

    text_area.clear( )
    text_area.send_keys(disable_message)
    print(f"Message entered: {len(disable_message)} chars")
    driver.implicitly_wait(1)

    # Click the Post button with class 'gc-button-primary submit-button gc-button' to confirm the disable action
    try:
        post_button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CLASS_NAME, "gc-button-primary")))
        print("Post button found, clicking it...")
        post_button.click( )
        print("Post button clicked")
    except Exception as e:
        print(f"ERROR: Could not find or click post button: {e}")
        raise
    
    time.sleep(2)

    # Close the disable log tab that we just used and switch back to the review tab
    try:
        driver.close( )
        print("Disable tab closed")
    except Exception as e:
        print(f"Warning: Could not close disable tab: {e}")
    
    try:
        driver.switch_to.window(handle)
        print("Switched back to review tab")
    except Exception as e:
        print(f"Warning: Could not switch back to review tab: {e}")
        # Try to switch to any remaining window
        if driver.window_handles:
            driver.switch_to.window(driver.window_handles[0])


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
    global timed_pub_group_counter, timed_pub_last_actual_time

    driver.switch_to.window(handle)
    print(f"Switched to tab with URL: {driver.current_url}")

    pub_date = (timed_pub_date_ref.current.value or "").strip( )
    pub_time = (timed_pub_time_ref.current.value or "").strip( )
    pub_increment = (timed_pub_increment_ref.current.value or "None").strip( )

    if not pub_date or not pub_time:
        message = "Timed publish date/time not set. Skipping timed publish."
        print(message)
        status_text_ref.current.value = message
        status_text_ref.current.color = "orange"
        status_text_ref.current.update()
        driver.close( )
        return

    # Convert 12-hour AM/PM format to 24-hour military format
    pub_time_military = _convert_to_military_time(pub_time)
    print(f"Converted time from '{pub_time}' to military format '{pub_time_military}'")
    
    # Calculate the actual publish time based on increment and listing position
    calc_date, calc_time_military, actual_dt = _calculate_next_publish_time(
        pub_date, pub_time_military, pub_increment, timed_pub_group_counter, timed_pub_last_actual_time
    )
    
    # Update the last actual time for chaining increments
    timed_pub_last_actual_time = actual_dt
    timed_pub_group_counter += 1
    
    # Convert calculated military time back to 12-hour format for display
    calc_time_12hr = _convert_to_12hr_format(calc_time_military)
    
    print(f"Calculated publish time for listing #{timed_pub_group_counter}: {calc_date} {calc_time_military} ({calc_time_12hr})")
    
    # Wait for the button titled 'Time publish' and click it
    status_text_ref.current.value = "Looking for Time Publish button..."
    status_text_ref.current.update()
    
    timed_pub_button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CLASS_NAME, "time-publish-btn")))
    driver.execute_script("arguments[0].scrollIntoView(true);", timed_pub_button)
    import time
    time.sleep(0.5)
    timed_pub_button.click( )
    print("Time Publish button clicked")
    status_text_ref.current.value = "Time Publish popup opened..."
    status_text_ref.current.update()
    driver.implicitly_wait(1)

    # Set the date for timed publication
    status_text_ref.current.value = f"Setting publish date to {calc_date}..."
    status_text_ref.current.update()
    
    # Flatpickr uses a wrapper, find the visible input
    date_input = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.NAME, "ctl00$ContentBody$timePublishDateInput"))
    )
    
    # Use JavaScript to set the value since it's a date picker
    driver.execute_script("""
        const input = arguments[0];
        input.value = arguments[1];
        const event = new Event('input', { bubbles: true });
        input.dispatchEvent(event);
        const changeEvent = new Event('change', { bubbles: true });
        input.dispatchEvent(changeEvent);
    """, date_input, calc_date)
    print(f"Date set to {calc_date}")
    time.sleep(0.5)
    driver.implicitly_wait(1)

    # Set the time for timed publication
    status_text_ref.current.value = f"Setting publish time to {calc_time_12hr}..."
    status_text_ref.current.update()
    
    time_publish_time_select = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.ID, "timePublishTimeSelect"))
    )
    driver.execute_script("arguments[0].scrollIntoView(true);", time_publish_time_select)
    time.sleep(0.3)
    time_publish_time_select.click( )
    print("Time dropdown clicked")
    time.sleep(0.3)
    
    # Get all available options to debug
    all_options = driver.find_elements(By.XPATH, "//select[@id='timePublishTimeSelect']/option")
    available_times = [opt.text for opt in all_options]
    print(f"Available time options: {available_times}")
    print(f"Looking for: '{calc_time_military}'")
    
    # Try to find matching option
    time_publish_time_option = None
    for opt in all_options:
        if opt.text.strip() == calc_time_military.strip():
            time_publish_time_option = opt
            break
    
    if time_publish_time_option:
        time_publish_time_option.click( )
        print(f"Time set to {time_publish_time_option.text}")
    else:
        raise ValueError(f"Time option '{pub_time_military}' not found. Available: {available_times}")
    
    driver.implicitly_wait(1)
    
    # Click confirm button
    status_text_ref.current.value = "Confirming timed publish..."
    status_text_ref.current.update()
    
    confirm_timed_pub = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, "ctl00_ContentBody_timePublishButton")))
    driver.execute_script("arguments[0].scrollIntoView(true);", confirm_timed_pub)
    time.sleep(0.3)
    confirm_timed_pub.click( )
    print("Timed publish confirmed")
    driver.implicitly_wait(1)

    # Close the tab we just processed and switch back to the review tab
    driver.close( )
    try:
        driver.switch_to.window(handle)
    except NoSuchWindowException:
        # The browsing context may be discarded after closing, but the operation succeeded
        print("Warning: Browsing context discarded (harmless - operation completed successfully)")
    
    print("Timed publish operation completed")
    status_text_ref.current.value = "Timed publish completed for this cache."
    status_text_ref.current.update()

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
    
    # Find the profile directory
    if os.path.exists(profile_path):
        import glob
        ui_profile = None
        if firefox_profile_path_ref.current:
            ui_profile = (firefox_profile_path_ref.current.value or "").strip()
        preferred_profile = ui_profile or os.getenv("GEOCACHING_FIREFOX_PROFILE")
        if preferred_profile and os.path.exists(preferred_profile):
            options.profile = webdriver.FirefoxProfile(preferred_profile)
            source = "UI" if ui_profile else "env"
            print(f"Using Firefox profile ({source}): {preferred_profile}")
        else:
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

    # Now, fill in necessary login information (if login form is present)
    try:
        username_field = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.ID, "UsernameOrEmail"))
        )
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
    except TimeoutException:
        # Likely already logged in or login form changed
        if status_text_ref.current:
            status_text_ref.current.value = "Login form not found; continuing..."
            status_text_ref.current.color = "orange"
            status_text_ref.current.update()

    # After interacting with the pop-up, switch back to the main window
    driver.switch_to.window(main_window_handle)

    # Close any extra tabs that may have opened (e.g., Tampermonkey changelog, etc.)
    main_handle = main_window_handle
    for handle in driver.window_handles:
        if handle != main_handle:
            try:
                driver.switch_to.window(handle)
                driver.close()
            except Exception as e:
                print(f"Warning: Could not close extra tab: {e}")
    
    # Switch back to main window
    driver.switch_to.window(main_handle)

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
        import time
        # Try to find and click the decline button multiple times if needed
        for attempt in range(3):
            try:
                popup_button = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.ID, "CybotCookiebotDialogBodyButtonDecline"))
                )
                popup_button.click()
                print(f"Cookie banner decline button clicked (attempt {attempt + 1})")
                break
            except TimeoutException:
                if attempt == 2:
                    raise
                time.sleep(1)
        
        # Wait for the banner to become invisible
        WebDriverWait(driver, 10).until(
            EC.invisibility_of_element_located((By.ID, "CybotCookiebotDialog"))
        )
        
        # Extra wait to ensure overlay is gone
        time.sleep(2)
        
    except TimeoutException:
        # Banner not present or already dismissed
        print("Cookie banner not found or already dismissed")
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
    global timed_pub_group_counter, timed_pub_last_actual_time
    
    # Reset the timed publishing group counter and time tracker for this batch
    timed_pub_group_counter = 0
    timed_pub_last_actual_time = None
    
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
            listing_number = review_tabs.index(handle) + 1
            
            if bookmark_checkbox_ref.current.value:
                print(f"\n[Listing {listing_number}] Adding to bookmark...")
                assign_to_bookmark_list(driver, handle, review_tabs)
                print(f"[Listing {listing_number}] Bookmark added successfully")
                
            if timed_pub_checkbox_ref.current.value:
                print(f"\n[Listing {listing_number}] Setting timed publish...")
                set_timed_pub(driver, handle, review_tabs)
                print(f"[Listing {listing_number}] Timed publish set successfully")
                
            if disable_with_same_message_checkbox_ref.current.value:
                print(f"\n[Listing {listing_number}] Disabling with message...")
                disable_with_same_message(driver, handle, review_tabs)
                print(f"[Listing {listing_number}] Disabled successfully")
                
        except Exception as exc:
            message = f"Listing {listing_number} Error: {exc}"
            print(f"ERROR: {message}")
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
            
            # STOP processing further listings on error
            # Update button to CLOSE
            def on_close_click(e):
                try:
                    driver.quit()
                except Exception:
                    pass
                page.window_close()

            go_button_ref.current.text = "CLOSE"
            go_button_ref.current.on_click = on_close_click
            go_button_ref.current.update()
            
            # Show error completion message
            completion_message_ref.current.value = "Error encountered. Click CLOSE to close Firefox. Use the red circle (upper left) to close this app."
            completion_message_ref.current.update()
            
            # Stop processing further listings
            break

    # Switch back to the original first tab
    # driver.switch_to.window(first_tab)
    # print(f"Switched back to original tab with URL: {driver.current_url}")

    # Close any leftover tabs that were opened during processing (keep review/admin tabs)
    try:
        current_tabs = driver.window_handles
        for handle in list(current_tabs):
            try:
                driver.switch_to.window(handle)
                url = driver.current_url
            except Exception:
                continue

            # Keep admin/review tabs; close others (e.g., log pages, script tabs)
            if "geocaching.com/admin/review.aspx" in url or "geocaching.com/admin" in url:
                continue
            
            try:
                driver.close()
            except Exception as e:
                print(f"Warning: Could not close extra tab: {e}")

        # Switch back to main tab if possible
        if driver.window_handles:
            driver.switch_to.window(driver.window_handles[0])
    except Exception as e:
        print(f"Warning during tab cleanup: {e}")

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
    completion_message_ref.current.value = "Processing complete. Click CLOSE to close Firefox. Use the red circle (upper left) to close this app."
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

    appText = "The app should have opened your Review Queue page in a new browser window. In THAT window be sure to load only the tabs that you wish to perform bulk functions on."

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