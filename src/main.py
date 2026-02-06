import flet as ft
import functions as fn
from datetime import date as dt_date
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

# Main function to run the Flet app
# --------------------------------------------------------------------------------
def main(page: ft.Page):

    # Setup the Flet page
    page.title = "geocaching-review-flet-selenium"
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER    
    page.theme_mode = ft.ThemeMode.DARK

    # Show explanatory text
    page.add(
        ft.Text(
            "This app is a work in progress to demonstrate how to use Flet with Selenium for geocaching review tasks.",
            size=20,
            text_align=ft.TextAlign.CENTER,
            color=ft.Colors.WHITE,
        )
    )

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

    # Load persisted values
    stored_bookmark_name = page.client_storage.get("bookmark_name") or ""
    stored_pub_date = page.client_storage.get("timed_pub_date") or ""
    stored_pub_time = page.client_storage.get("timed_pub_time") or ""

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
    disable_with_same_message_checkbox = ft.Checkbox(label="Disable with Same Message", value=False, ref=disable_with_same_message_checkbox_ref)
    page.add(disable_with_same_message_checkbox)

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

ft.app(target=main)



    # # Add buttons to the page for various actions
    # page.add(
    #     ft.Column(
    #         [
    #             ft.CupertinoFilledButton(
    #                 "Create Bookmark",
    #                 on_click=lambda e: fn.assign_bookmarks(driver)
    #             ),
    #             ft.CupertinoFilledButton(
    #                 "Set Timed Publication",
    #                 on_click=lambda e: fn.timed_pub(driver)
    #             )
    #         ],
    #         alignment=ft.MainAxisAlignment.CENTER,
    #         spacing=20,
    #     )
    # )   


    # counter = ft.Text("0", size=50, data=0)

    # def increment_click(e):
    #     counter.data += 1
    #     counter.value = str(counter.data)
    #     counter.update()

    # page.floating_action_button = ft.FloatingActionButton(
    #     icon=ft.Icons.ADD, on_click=increment_click
    # )
    # page.add(
    #     ft.SafeArea(
    #         ft.Container(
    #             counter,
    #             alignment=ft.alignment.center,
    #         ),
    #         expand=True,
    #     )
    # )

# ===============================================================================
# Launch the Flet app
# ===============================================================================

ft.app(main)
