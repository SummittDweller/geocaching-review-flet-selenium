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
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchWindowException
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.firefox.service import Service as FirefoxService
from dotenv import load_dotenv
import os
import time

try:
    from webdriver_manager.firefox import GeckoDriverManager
except Exception:
    GeckoDriverManager = None


def get_env_value(*keys):
    """Return the first configured environment value from the provided keys."""
    load_dotenv()
    for key in keys:
        value = os.getenv(key)
        if value:
            return value
    return ""


def get_configured_queue_url():
    """Return the configured queue URL used for startup and queue scraping."""
    default_queue_url = "https://www.geocaching.com/admin/queue.aspx?filter=AllHolds&stateid=16&pagesize=-1"
    queue_url = (get_env_value("GEOCACHING_SCRAPE_QUEUE_URL") or default_queue_url).strip()
    return queue_url or default_queue_url


def _ensure_queue_filter_value(driver, desired_value, timeout=10):
    """Set queue filter dropdown to the desired value when present.

    Filter values observed in the queue UI:
    - 1: All Caches Not On Hold (startup/default workflow)
    - 3: All Caches I'm Holding (dump on-hold CSV workflow)
    """
    desired = str(desired_value)
    try:
        filter_select = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.ID, "ctl00_ContentBody_ddFilter"))
        )
    except TimeoutException:
        return False

    current = (filter_select.get_attribute("value") or "").strip()
    if current == desired:
        return True

    original_select = filter_select

    try:
        Select(filter_select).select_by_value(desired)
    except Exception:
        # Fallback for non-standard select behavior.
        driver.execute_script(
            """
            const sel = arguments[0];
            const val = arguments[1];
            sel.value = val;
            sel.dispatchEvent(new Event('input', { bubbles: true }));
            sel.dispatchEvent(new Event('change', { bubbles: true }));
            """,
            filter_select,
            desired,
        )

    try:
        WebDriverWait(driver, timeout).until(
            lambda d: (d.find_element(By.ID, "ctl00_ContentBody_ddFilter").get_attribute("value") or "").strip() == desired
        )
    except Exception:
        pass

    try:
        filter_button = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((By.ID, "ctl00_ContentBody_btnFilter"))
        )
        filter_button.click()
    except Exception:
        driver.execute_script(
            "document.getElementById(arguments[0])?.click();",
            "ctl00_ContentBody_btnFilter",
        )

    try:
        WebDriverWait(driver, timeout).until(EC.staleness_of(original_select))
    except Exception:
        try:
            WebDriverWait(driver, timeout).until(
                lambda d: (d.find_element(By.ID, "ctl00_ContentBody_ddFilter").get_attribute("value") or "").strip() == desired
            )
        except Exception:
            pass

    return True


def _get_queue_filter_info(driver):
    """Return current queue filter `(value, label)` when available."""
    try:
        filter_select = driver.find_element(By.ID, "ctl00_ContentBody_ddFilter")
        value = (filter_select.get_attribute("value") or "").strip()
        label = (Select(filter_select).first_selected_option.text or "").strip()
        return value, label
    except Exception:
        return "", ""

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


# Function to scrape geocaching queue and dump to CSV
# ============================================================================
def scrape_queue_to_csv(firefox_profile_path=None, status_callback=None, driver=None):
    """
    Scrape the geocaching queue page and save to CSV.
    
    Args:
        firefox_profile_path: Optional path to Firefox profile for fallback browser launch
        status_callback: Optional callback function to update UI with status messages
                        Should accept a string status message and optional color (ft.Colors)
        driver: Optional existing Selenium WebDriver. When provided, scraping runs in
                the already-open Firefox session instead of launching a new one.
    
    Returns:
        Tuple of (success: bool, message: str, csv_path: str or None)
    """
    import csv
    import re
    from pathlib import Path
    from datetime import datetime

    load_dotenv()
    
    managed_driver = driver
    using_existing_driver = managed_driver is not None
    original_window_handle = None
    scrape_window_handle = None
    
    def update_status(msg, color=None):
        """Helper to update UI status if callback provided"""
        if status_callback:
            status_callback(msg, color)
        print(msg)
    
    def clean_text(value):
        if not value:
            return ""
        return " ".join(value.split())

    def normalize_header(value):
        return clean_text(value).strip().lower()

    def extract_publish_from_text(value):
        if not value:
            return ""
        match = re.search(
            r"Set\s+to\s+publish\s+at\s+(\d{1,2}:\d{2})\s+\w+\s+Time\s+on\s+(\d{1,2}\.[A-Za-z]{3}\.\d{4})",
            value,
            flags=re.IGNORECASE,
        )
        if not match:
            return ""
        return f"{match.group(2)} {match.group(1)}"

    def parse_datetime_for_sort(datetime_str):
        if not datetime_str:
            return datetime.max

        normalized = clean_text(datetime_str)

        formats = [
            "%m/%d/%Y %I:%M %p",
            "%m/%d/%Y %H:%M",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %I:%M %p",
            "%d.%b.%Y %H:%M",
            "%d.%b.%Y %I:%M %p",
        ]

        for fmt in formats:
            try:
                return datetime.strptime(normalized, fmt)
            except ValueError:
                continue

        extracted = extract_publish_from_text(normalized)
        if extracted:
            try:
                return datetime.strptime(extracted, "%d.%b.%Y %H:%M")
            except ValueError:
                pass

        print(f"Warning: Could not parse datetime '{datetime_str}'")
        return datetime.max

    try:
        if using_existing_driver:
            update_status("Using existing logged-in Firefox session for queue scraping...")
            original_window_handle = managed_driver.current_window_handle
            managed_driver.switch_to.new_window("tab")
            scrape_window_handle = managed_driver.current_window_handle
        else:
            update_status("Starting Firefox for queue scraping...")

            # Setup Firefox with the provided profile
            options = FirefoxOptions()
            if firefox_profile_path and Path(firefox_profile_path).exists():
                options.profile = webdriver.FirefoxProfile(firefox_profile_path)
                update_status(f"Using profile: {firefox_profile_path}")

            # Initialize webdriver
            service = None
            if GeckoDriverManager is not None:
                try:
                    managed_driver_path = GeckoDriverManager().install()
                    service = FirefoxService(executable_path=managed_driver_path)
                except Exception as exc:
                    print(f"Warning: Could not use managed geckodriver: {exc}")

            if service is not None:
                managed_driver = webdriver.Firefox(options=options, service=service)
            else:
                managed_driver = webdriver.Firefox(options=options)
        
        queue_url = get_configured_queue_url()

        update_status(f"Navigating to queue: {queue_url}")
        managed_driver.get(queue_url)

        # Dump to CSV is specifically for "All Caches I'm Holding" (filter value 3).
        update_status("Selecting queue filter: All Caches I'm Holding...")
        _ensure_queue_filter_value(managed_driver, "3")
        active_filter_value, active_filter_label = _get_queue_filter_info(managed_driver)
        if active_filter_label:
            update_status(f"Queue filter active: {active_filter_label} (value {active_filter_value})")

        if "account/signin" in (managed_driver.current_url or ""):
            update_status(
                "Queue page redirected to sign-in. Use Start to log in first, then retry dump.",
                ft.Colors.RED,
            )
            return (False, "Queue scraping requires an authenticated session.", None)
        
        update_status("Waiting for table to load...")
        try:
            WebDriverWait(managed_driver, 30).until(
                EC.presence_of_all_elements_located((By.TAG_NAME, "table"))
            )
        except TimeoutException:
            update_status("Page load timeout - checking content anyway...", ft.Colors.ORANGE)
        
        update_status(f"Page title: {managed_driver.title}")
        
        # Find the queue table and parse using actual semantics:
        # - ID cell contains GC code and (D/T)
        # - Title cell contains title and "Set to publish at ..."
        header_aliases = {
            "ID": {"id", "gc code", "code", "geocache code", "waypoint"},
            "Title": {"title", "cache title", "name", "cache name"},
            "Owner": {"owner", "placed by", "owner/placed by", "submitted by", "by"},
        }

        def extract_title_without_publish(text):
            if not text:
                return ""
            parts = re.split(r"Set\s+to\s+publish\s+at", text, maxsplit=1, flags=re.IGNORECASE)
            return clean_text(parts[0])

        queue_table = None
        queue_rows = []
        best_score = -1

        tables = managed_driver.find_elements(By.CSS_SELECTOR, "table")
        for table in tables:
            rows = table.find_elements(By.CSS_SELECTOR, "tbody tr")
            if not rows:
                # Fallback to data rows only when tbody is missing.
                rows = table.find_elements(By.XPATH, "./tr[td]")

            gc_count = 0
            publish_count = 0
            for row in rows[:400]:
                row_text = row.text or ""
                if re.search(r"\bGC[A-Z0-9]{4,}\b", row_text):
                    gc_count += 1
                if re.search(r"Set\s+to\s+publish\s+at", row_text, flags=re.IGNORECASE):
                    publish_count += 1

            score = gc_count + publish_count
            if score > best_score:
                best_score = score
                queue_table = table
                queue_rows = rows

        if queue_table is None or not queue_rows:
            update_status("Could not find queue table rows", ft.Colors.RED)
            return (False, "Could not find queue table rows", None)

        # Build optional index map for ID/Title/Owner when headers are available
        column_map = {}
        header_cells = queue_table.find_elements(By.CSS_SELECTOR, "thead th")
        if not header_cells:
            # Fallback to first-row headers when thead is absent.
            header_cells = queue_table.find_elements(By.XPATH, "./tbody/tr[1]/th | ./tr[1]/th")
        headers = [normalize_header(cell.text) for cell in header_cells]
        for idx, header in enumerate(headers):
            for output_name, aliases in header_aliases.items():
                if header in aliases and output_name not in column_map:
                    column_map[output_name] = idx

        update_status(f"Selected queue table score={best_score}, column map={column_map}")

        data = []
        parsed_listing_rows = 0
        for idx, row in enumerate(queue_rows):
            try:
                cells = row.find_elements(By.CSS_SELECTOR, "td")
                if not cells:
                    continue

                full_text = row.text or ""
                normalized_full_text = clean_text(full_text)

                # Source texts per semantic column
                id_source = ""
                title_source = ""
                owner_source = ""

                if "ID" in column_map and column_map["ID"] < len(cells):
                    id_source = cells[column_map["ID"]].text or ""
                if "Title" in column_map and column_map["Title"] < len(cells):
                    title_source = cells[column_map["Title"]].text or ""
                if "Owner" in column_map and column_map["Owner"] < len(cells):
                    owner_source = cells[column_map["Owner"]].text or ""

                if not id_source:
                    for cell in cells:
                        txt = cell.text or ""
                        if re.search(r"\bGC[A-Z0-9]{4,}\b", txt):
                            id_source = txt
                            break

                if not title_source:
                    for cell in cells:
                        txt = cell.text or ""
                        if re.search(r"Set\s+to\s+publish\s+at", txt, flags=re.IGNORECASE):
                            title_source = txt
                            break

                if not id_source:
                    id_source = full_text
                if not title_source:
                    title_source = full_text

                id_match = re.search(r"\bGC[A-Z0-9]{4,}\b", id_source)
                if not id_match:
                    id_match = re.search(r"\bGC[A-Z0-9]{4,}\b", full_text)

                # Ignore non-listing rows
                if not id_match:
                    continue
                parsed_listing_rows += 1

                dt_match = re.search(r"\((\d+(?:\.\d+)?)/(\d+(?:\.\d+)?)\)", id_source)
                if not dt_match:
                    dt_match = re.search(r"\((\d+(?:\.\d+)?)/(\d+(?:\.\d+)?)\)", full_text)

                set_to_publish = extract_publish_from_text(title_source)
                if not set_to_publish:
                    set_to_publish = extract_publish_from_text(full_text)

                title_value = extract_title_without_publish(title_source)
                if not title_value:
                    title_match = re.search(
                        r"!\s*(.*?)\s*Set\s+to\s+publish\s+at",
                        full_text,
                        flags=re.IGNORECASE | re.DOTALL,
                    )
                    if title_match:
                        title_value = "!" + clean_text(title_match.group(1))

                row_data = {
                    "ID": id_match.group(0),
                    "Set to publish": clean_text(set_to_publish),
                    "D": dt_match.group(1) if dt_match else "",
                    "T": dt_match.group(2) if dt_match else "",
                    "Title": clean_text(title_value),
                    "Owner": clean_text(owner_source),
                }

                data.append(row_data)
            except Exception as e:
                print(f"  Warning: Could not parse row {idx}: {e}")
                continue

        # Ensure one row per listing ID
        deduped_data = {}
        for item in data:
            listing_id = item.get("ID", "")
            if not listing_id:
                continue
            deduped_data[listing_id] = item
        data = list(deduped_data.values())

        unique_count = len(data)
        duplicate_count = max(parsed_listing_rows - unique_count, 0)
        missing_publish_count = sum(1 for item in data if not (item.get("Set to publish") or "").strip())
        missing_dt_count = sum(
            1
            for item in data
            if not (item.get("D") or "").strip() or not (item.get("T") or "").strip()
        )
        
        if not data:
            update_status("No valid data extracted from rows", ft.Colors.RED)
            return (False, "Could not extract data from table rows", None)
        
        update_status(
            f"Extracted {unique_count} unique IDs (raw rows: {parsed_listing_rows}, duplicates collapsed: {duplicate_count}). Sorting by date..."
        )

        try:
            data = sorted(data, key=lambda x: parse_datetime_for_sort(x["Set to publish"]))
            update_status("Data sorted successfully")
        except Exception as e:
            update_status(f"Warning: Could not sort data: {e}", ft.Colors.ORANGE)
        
        # Write to CSV in the project root
        output_path = Path(__file__).parent.parent / "geocaching_queue.csv"
        update_status(f"Writing CSV to: {output_path}")
        
        fieldnames = ['ID', 'Set to publish', 'D', 'T', 'Title', 'Owner']
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)
        
        summary_parts = [
            f"Exported {unique_count} unique IDs",
            f"missing publish: {missing_publish_count}",
            f"missing D/T: {missing_dt_count}",
        ]
        summary_text = " | ".join(summary_parts)

        if missing_publish_count > 0 or missing_dt_count > 0:
            update_status(
                f"✓ Created {output_path.name}. {summary_text}",
                ft.Colors.ORANGE,
            )
        else:
            update_status(
                f"✓ Created {output_path.name}. {summary_text}",
                ft.Colors.GREEN,
            )

        return (
            True,
            f"Created {output_path.name}. {summary_text}",
            str(output_path),
        )
        
    except Exception as e:
        error_msg = f"Error during scraping: {str(e)}"
        update_status(error_msg, ft.Colors.RED)
        print(f"Exception: {e}")
        import traceback
        traceback.print_exc()
        return (False, error_msg, None)
    finally:
        if managed_driver:
            if using_existing_driver:
                # Keep the main browser session alive; only close the temporary scrape tab.
                try:
                    if scrape_window_handle and scrape_window_handle in managed_driver.window_handles:
                        managed_driver.switch_to.window(scrape_window_handle)
                        managed_driver.close()
                except (NoSuchWindowException, Exception):
                    pass

                try:
                    if original_window_handle and original_window_handle in managed_driver.window_handles:
                        managed_driver.switch_to.window(original_window_handle)
                except (NoSuchWindowException, Exception):
                    pass
            else:
                try:
                    managed_driver.quit()
                except (NoSuchWindowException, Exception):
                    pass


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

    # Accept confirmation dialog if one appears (dismiss would cancel)
    try:
        alert = WebDriverWait(driver, 3).until(EC.alert_is_present())
        print("Confirmation alert detected, accepting...")
        alert.accept()
        time.sleep(0.5)
    except Exception:
        pass

    # Wait for submission to complete (textarea becomes stale or disappears)
    try:
        WebDriverWait(driver, 10).until(EC.staleness_of(text_area))
        print("Submission completed (editor stale)")
    except Exception:
        # If not stale, continue but warn
        print("Warning: editor did not go stale after post; submission may not have completed yet")

    time.sleep(1)

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
def initialize_driver(page, username=None, password=None):

    load_dotenv( )     # Load environment variables from .env file
    expected_user = (username or get_env_value("USERNAME", "GEOCACHING_USERNAME") or "").strip( )
    effective_password = password if password is not None else get_env_value("PASSWORD")

    queue_url = get_configured_queue_url()

    if not expected_user:
        raise ValueError("Startup halted: Geocaching username is required.")

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
    import glob
    ui_profile = None
    if firefox_profile_path_ref.current:
        ui_profile = (firefox_profile_path_ref.current.value or "").strip()
    preferred_profile = ui_profile or get_env_value("FIREFOX_PROFILE_PATH", "GEOCACHING_FIREFOX_PROFILE")
    if preferred_profile and os.path.exists(preferred_profile):
        options.profile = webdriver.FirefoxProfile(preferred_profile)
        source = "UI" if ui_profile else "env"
        print(f"Using Firefox profile ({source}): {preferred_profile}")
    elif os.path.exists(profile_path):
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

    service = None
    if GeckoDriverManager is not None:
        try:
            managed_driver_path = GeckoDriverManager().install()
            service = FirefoxService(executable_path=managed_driver_path)
            print(f"Using managed geckodriver: {managed_driver_path}")
        except Exception as exc:
            print(f"Warning: failed to resolve managed geckodriver, falling back to PATH. {exc}")

    if service is not None:
        driver = webdriver.Firefox(options=options, service=service)
    else:
        driver = webdriver.Firefox(options=options)

    # Close noisy extension tabs (Tampermonkey changes/changelog) opened at startup
    _close_tampermonkey_changes_tabs(driver)

    # Update progress
    progress_bar_ref.current.value = 0.5
    loading_status_ref.current.value = "Loading geocaching.com..."
    progress_bar_ref.current.update()
    loading_status_ref.current.update()

    # Open geocaching after initial browser startup tab cleanup
    driver.get("https://www.geocaching.com/admin")

    # Store the handle of the main window
    main_window_handle = driver.current_window_handle

    # Update progress
    progress_bar_ref.current.value = 0.7
    loading_status_ref.current.value = "Dismissing cookie banner and logging in..."
    progress_bar_ref.current.update()
    loading_status_ref.current.update()

    # Dismiss the cookie banner if present
    _dismiss_cookie_banner(driver)

    # Ensure expected geocaching identity is active
    active_user = _ensure_expected_geocaching_user(driver, expected_user, effective_password)
    if active_user != expected_user:
        raise RuntimeError(
            f"Startup halted: expected account '{expected_user}' but detected '{active_user or 'unknown'}'."
        )
    driver._gc_active_user = active_user

    # Update progress
    progress_bar_ref.current.value = 0.85
    progress_bar_ref.current.update()

    # Cleanup any extension tabs that may have appeared during login
    _close_tampermonkey_changes_tabs(driver)

    # Update progress
    progress_bar_ref.current.value = 0.95
    loading_status_ref.current.value = "Loading configured queue..."
    progress_bar_ref.current.update()
    loading_status_ref.current.update()

    # Open the configured queue page from .env
    driver.get(queue_url)

    # Normal startup workflow should open "All Caches Not On Hold" (filter value 1).
    _ensure_queue_filter_value(driver, "1")
    active_filter_value, active_filter_label = _get_queue_filter_info(driver)
    if active_filter_label:
        loading_status_ref.current.value = f"Queue filter active: {active_filter_label} (value {active_filter_value})"
        loading_status_ref.current.update()

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


def _close_tampermonkey_changes_tabs(driver):
    """Close Tampermonkey changelog/changes tabs if they open at browser startup."""
    try:
        handles = list(driver.window_handles)
    except Exception:
        return

    if not handles:
        return

    current_handle = driver.current_window_handle

    def _is_tampermonkey_tab(url, title):
        url_l = (url or "").lower()
        title_l = (title or "").lower()
        return (
            "tampermonkey" in url_l
            or "tampermonkey" in title_l
            or "changes" in title_l and "userscript" in url_l
            or "changelog" in url_l and "tampermonkey" in url_l
        )

    for handle in list(handles):
        try:
            driver.switch_to.window(handle)
            url = driver.current_url
            title = driver.title
            if _is_tampermonkey_tab(url, title) and len(driver.window_handles) > 1:
                print(f"Closing Tampermonkey tab: {title} ({url})")
                driver.close()
        except Exception as exc:
            print(f"Warning: Could not inspect/close startup tab: {exc}")

    # Ensure we are focused on a live window
    remaining = driver.window_handles
    if not remaining:
        driver.switch_to.new_window('tab')
        return

    try:
        if current_handle in remaining:
            driver.switch_to.window(current_handle)
        else:
            driver.switch_to.window(remaining[0])
    except Exception:
        driver.switch_to.window(remaining[0])


def _detect_geocaching_username(driver, expected_username=None):
    """Best-effort detection of active geocaching username from page source."""
    try:
        # Prefer direct DOM lookup of the signed-in username badge when available.
        username_nodes = driver.find_elements(By.CSS_SELECTOR, "span.username")
        for node in username_nodes:
            txt = (node.text or "").strip()
            if not txt:
                continue
            if expected_username and txt.lower() == expected_username.lower():
                return expected_username
            return txt
    except Exception:
        pass

    source = (driver.page_source or "").lower()
    if expected_username and expected_username.lower() in source:
        return expected_username
    if "iowa.landmark" in source:
        return "Iowa.Landmark"
    if "summittdweller" in source:
        return "SummittDweller"
    return None


def _perform_geocaching_login(driver, username, password):
    """Fill the sign-in form and submit credentials."""
    username_field = WebDriverWait(driver, 8).until(
        EC.presence_of_element_located((By.ID, "UsernameOrEmail"))
    )
    username_field.clear()
    username_field.send_keys(username)

    password_field = driver.find_element(By.ID, "Password")
    password_field.clear()
    password_field.send_keys(password or "")

    login_button = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.ID, "SignIn"))
    )
    driver.execute_script("arguments[0].scrollIntoView(true);", login_button)
    time.sleep(0.5)
    login_button.click( )


def _ensure_expected_geocaching_user(driver, expected_username, password):
    """Ensure expected geocaching identity is active, re-auth only when needed."""
    if status_text_ref.current:
        status_text_ref.current.value = f"Checking active login for {expected_username}..."
        status_text_ref.current.color = "orange"
        status_text_ref.current.update()

    # Normalize browser state first
    _close_tampermonkey_changes_tabs(driver)

    # Fast path: if already signed in as the expected user, skip explicit login.
    driver.get("https://www.geocaching.com/admin")
    _dismiss_cookie_banner(driver)
    detected_user = _detect_geocaching_username(driver, expected_username=expected_username)
    if detected_user == expected_username:
        print(f"Already signed in as {expected_username}; skipping explicit login.")
        return expected_username

    if not password:
        raise RuntimeError(
            "Startup halted: password is required because an explicit login is needed."
        )

    if status_text_ref.current:
        status_text_ref.current.value = f"Signing in as {expected_username}..."
        status_text_ref.current.color = "orange"
        status_text_ref.current.update()

    # Visit geocaching domain, clear cookies/storage, and force sign-out to avoid sticky profile sessions
    driver.get("https://www.geocaching.com")
    _dismiss_cookie_banner(driver)
    try:
        driver.delete_all_cookies()
    except Exception:
        pass
    try:
        driver.execute_script("window.localStorage.clear(); window.sessionStorage.clear();")
    except Exception:
        pass

    driver.get("https://www.geocaching.com/account/signout")
    time.sleep(1)

    # Explicit sign-in with provided credentials
    driver.get("https://www.geocaching.com/account/signin?returnUrl=%2Fadmin")
    _dismiss_cookie_banner(driver)
    _perform_geocaching_login(driver, expected_username, password)

    # Wait for navigation away from sign-in screen
    try:
        WebDriverWait(driver, 12).until(lambda d: "account/signin" not in (d.current_url or ""))
    except TimeoutException:
        raise RuntimeError("Startup halted: login did not complete; check credentials and MFA prompts.")

    # Verify resulting account on admin page
    driver.get("https://www.geocaching.com/admin")
    _dismiss_cookie_banner(driver)
    detected_user = _detect_geocaching_username(driver, expected_username=expected_username)
    if detected_user != expected_username:
        raise RuntimeError(
            f"Startup halted: login completed but account verification failed (detected '{detected_user or 'unknown'}')."
        )

    return expected_username


# Start the Selenium driver and perform initial actions
# -----------------------------------------------------------------------------
def start_selenium(driver):
    # Ensure the driver is initialized and the main window is set
    if not driver:
        print("Driver is not initialized. Please run initialize_driver first.")
        return
    
    current_url = (driver.current_url or "").lower()

    # Ensure the driver is on a queue page; filter/query may vary by workflow.
    if "geocaching.com/admin/queue.aspx" not in current_url:
        expected_queue_url = get_configured_queue_url()
        print(f"Driver is not on a queue page ({expected_queue_url}). Please navigate to the review queue page first.")
        return

    active_filter_value, active_filter_label = _get_queue_filter_info(driver)
    if active_filter_label:
        print(f"Active queue filter before tab processing: {active_filter_label} (value {active_filter_value})")
    else:
        print("Active queue filter before tab processing: unknown")
    
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

        # Fetch relevant links in the current tab for diagnostics.
        all_links = driver.find_elements("tag name", "a")
        links = [
            link for link in all_links
            if "review.aspx" in ((link.get_attribute("href") or "").lower())
            or "/admin" in ((link.get_attribute("href") or "").lower())
        ]
        print(f"Found {len(links)} relevant links in the current tab (from {len(all_links)} total).")
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
                completion_message_ref.current.value = "Firefox closed. To close this app, click the red button in the app window."
                completion_message_ref.current.color = ft.Colors.ORANGE
                completion_message_ref.current.update()

            go_button_ref.current.text = "CLOSE"
            go_button_ref.current.on_click = on_close_click
            go_button_ref.current.update()
            
            # Show error completion message
            completion_message_ref.current.value = "Error encountered. Click CLOSE to close Firefox. To close this app, click the red button in the app window."
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
        completion_message_ref.current.value = "Firefox closed. To close this app, click the red button in the app window."
        completion_message_ref.current.color = ft.Colors.ORANGE
        completion_message_ref.current.update()

    go_button_ref.current.text = "CLOSE"
    go_button_ref.current.on_click = on_close_click
    go_button_ref.current.update()

    # Show completion message
    completion_message_ref.current.value = "Processing complete. Click CLOSE to close Firefox. To close this app, click the red button in the app window."
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