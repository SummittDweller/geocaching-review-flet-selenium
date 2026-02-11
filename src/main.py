import flet as ft
import functions as fn
from datetime import date as dt_date
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

# Main function to run the Flet app
# --------------------------------------------------------------------------------
def main(page: ft.Page):

    # Setup the Flet page
    page.title = "geocaching-review-flet-selenium"
    page.vertical_alignment = ft.MainAxisAlignment.START
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER    
    page.theme_mode = ft.ThemeMode.DARK
    page.scroll = ft.ScrollMode.AUTO

    # Show explanatory text
    page.add(
        ft.Text(
            "This app is a work in progress to demonstrate how to use Flet with Selenium for geocaching review tasks.",
            size=20,
            text_align=ft.TextAlign.CENTER,
            color=ft.Colors.WHITE,
        )
    )

    # Load persisted values for splash screen
    stored_firefox_profile_path = page.client_storage.get("firefox_profile_path") or ""

    # Create the start button (will be added after profile selector)
    start_button = ft.CupertinoFilledButton(
        "Start",
        disabled=not stored_firefox_profile_path,
    )

    def on_profile_pick(e: ft.FilePickerResultEvent):
        if e.path:
            firefox_profile_path_ref.current.value = e.path
            firefox_profile_path_ref.current.update()
            page.client_storage.set("firefox_profile_path", e.path)
            start_button.disabled = False
            start_button.update()

    # Firefox profile selector - shown on splash screen
    firefox_profile_path_field = ft.TextField(
        label="Firefox profile folder (paste full path here)",
        value=stored_firefox_profile_path,
        ref=firefox_profile_path_ref,
        read_only=False,
        on_change=lambda e: (
            page.client_storage.set("firefox_profile_path", e.control.value),
            setattr(start_button, "disabled", not e.control.value.strip()),
            start_button.update()
        ),
        width=480,
    )
    page.add(firefox_profile_path_field)

    # Start button (enabled only after profile selection)
    def on_start_click(e):
        # Hide splash screen controls
        page.clean()
        
        # Add loading status and progress bar
        loading_status = ft.Text(
            "Loading Firefox with your profile... Please be patient.",
            ref=loading_status_ref,
            size=14,
            text_align=ft.TextAlign.CENTER,
            color=ft.Colors.LIGHT_BLUE,
        )
        page.add(loading_status)

        progress_bar = ft.ProgressBar(
            ref=progress_bar_ref,
            width=300,
            value=0.0,
            color=ft.Colors.BLUE,
        )
        page.add(progress_bar)
        
        # Load remaining persisted values
        stored_bookmark_name = page.client_storage.get("bookmark_name") or ""
        stored_pub_date = page.client_storage.get("timed_pub_date") or ""
        stored_pub_time = page.client_storage.get("timed_pub_time") or ""
        stored_pub_increment = page.client_storage.get("timed_pub_increment") or "None"
        stored_disable_message = page.client_storage.get("disable_with_same_message_text") or ""

        # Launch the Selenium driver and login      
        driver = fn.initialize_driver(page)

        # Show the main content of the app
        create_expansion_tile = fn.create_expansion_tile(ft)
        page.add(create_expansion_tile)

        # Update loading status
        loading_status_ref.current.value = "Firefox loaded successfully! Ready to review."
        loading_status_ref.current.color = ft.Colors.GREEN
        progress_bar_ref.current.visible = False
        loading_status_ref.current.update()
        progress_bar_ref.current.update()

        # Continue with the rest of the app initialization
        # Add checkboxes to the page for various actions
        bookmark_checkbox = ft.Checkbox(label="Add to Bookmark List", value=False, ref=bookmark_checkbox_ref)
        page.add(bookmark_checkbox)

        # Bookmark name input (persistent)
        bookmark_name_field = ft.TextField(
            label="Bookmark name",
            value=stored_bookmark_name,
            ref=bookmark_name_ref,
            on_change=lambda e: page.client_storage.set("bookmark_name", e.control.value),
            width=420,
        )
        page.add(bookmark_name_field)

        timed_pub_checkbox = ft.Checkbox(label="Add to Timed Publishing", value=False, ref=timed_pub_checkbox_ref)
        page.add(timed_pub_checkbox)

        # Timed publish date/time pickers (persistent)
        def on_date_change(e):
            if e.control.value:
                date_str = e.control.value.isoformat( )
                timed_pub_date_ref.current.value = date_str
                timed_pub_date_ref.current.update( )
                page.client_storage.set("timed_pub_date", date_str)

        def _format_time_value(value):
            if not value:
                return ""
            time_str = value.strftime("%I:%M %p").lstrip("0")
            return time_str

        def on_time_change(e):
            if e.control.value:
                time_str = _format_time_value(e.control.value)
                timed_pub_time_ref.current.value = time_str
                timed_pub_time_ref.current.update( )
                page.client_storage.set("timed_pub_time", time_str)

        date_picker = ft.DatePicker(on_change=on_date_change)
        time_picker = ft.TimePicker(on_change=on_time_change)
        page.overlay.extend([date_picker, time_picker])

        if stored_pub_date:
            try:
                date_picker.value = dt_date.fromisoformat(stored_pub_date)
            except ValueError:
                date_picker.value = None

        timed_pub_date_field = ft.TextField(
            label="Publish date (YYYY-MM-DD)",
            value=stored_pub_date,
            ref=timed_pub_date_ref,
            read_only=True,
            width=260,
        )

        timed_pub_time_field = ft.TextField(
            label="Publish time",
            value=stored_pub_time,
            ref=timed_pub_time_ref,
            read_only=True,
            width=160,
        )

        page.add(
            ft.Row(
                controls=[
                    timed_pub_date_field,
                    ft.IconButton(icon=ft.Icons.CALENDAR_MONTH, on_click=lambda e: page.open(date_picker)),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
            )
        )

        page.add(
            ft.Row(
                controls=[
                    timed_pub_time_field,
                    ft.IconButton(icon=ft.Icons.ACCESS_TIME, on_click=lambda e: page.open(time_picker)),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
            )
        )

        # Timed publish time increment dropdown
        timed_pub_increment_dropdown = ft.Dropdown(
            label="Publish time increment",
            value=stored_pub_increment,
            options=[
                ft.dropdown.Option("None"),
                ft.dropdown.Option("30 minutes"),
                ft.dropdown.Option("1 Hour"),
                ft.dropdown.Option("2 Hours"),
                ft.dropdown.Option("4 Hours"),
                ft.dropdown.Option("6 Hours"),
                ft.dropdown.Option("12 Hours"),
                ft.dropdown.Option("1 Day"),
            ],
            ref=timed_pub_increment_ref,
            on_change=lambda e: page.client_storage.set("timed_pub_increment", e.control.value),
            width=260,
        )
        page.add(timed_pub_increment_dropdown)

        disable_with_same_message_text = ft.TextField(
            label="Disable message",
            value=stored_disable_message,
            ref=disable_with_same_message_text_ref,
            on_change=lambda e: page.client_storage.set("disable_with_same_message_text", e.control.value),
            multiline=True,
            min_lines=6,
            max_lines=12,
            width=520,
            visible=False,
        )

        def _toggle_disable_message_input(e):
            disable_with_same_message_text.visible = bool(e.control.value)
            disable_with_same_message_text.update()

        disable_with_same_message_checkbox = ft.Checkbox(
            label="Disable with Same Message",
            value=False,
            ref=disable_with_same_message_checkbox_ref,
            on_change=_toggle_disable_message_input,
        )
        page.add(disable_with_same_message_checkbox)
        page.add(disable_with_same_message_text)

        # Add GO button to the page
        def on_go_click(e):
            fn.go(driver, page)

        go_button = ft.CupertinoFilledButton(
            "GO!",
            on_click=on_go_click,
            ref=go_button_ref,
        )
        page.add(go_button)

        # Add completion message
        completion_message = ft.Text(
            "",
            ref=completion_message_ref,
            size=12,
            color=ft.Colors.ORANGE,
            text_align=ft.TextAlign.CENTER,
        )
        page.add(completion_message)

        # Add status text at the bottom
        status_text = ft.Text(
            "",
            ref=status_text_ref,
            size=14,
            color=ft.Colors.YELLOW,
            text_align=ft.TextAlign.CENTER,
        )
        page.add(status_text)

    start_button.on_click = on_start_click
    page.add(start_button)

ft.app(target=main)
