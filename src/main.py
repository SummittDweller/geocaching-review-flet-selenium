import flet as ft
import functions as fn

# Main function to run the Flet app
# --------------------------------------------------------------------------------
def main(page: ft.Page):

    # Setup the Flet page
    page.title = "geocaching-review-flet-selenium"
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER    
    page.theme_mode = ft.ThemeMode.DARK

    # Create ft.Ref placeholders
    bookmark_checkbox_ref = ft.Ref[ft.Checkbox]()
    timed_pub_checkbox_ref = ft.Ref[ft.Checkbox]()

    # Show explanatory text
    page.add(
        ft.Text(
            "This app is a work in progress to demonstrate how to use Flet with Selenium for geocaching review tasks.",
            size=20,
            text_align=ft.TextAlign.CENTER,
            color=ft.Colors.WHITE,
        )
    )   

    # Launch the Selenium driver and login      
    driver = fn.initialize_driver( )

    # Show the main content of the app
    create_expansion_tile = fn.create_expansion_tile(ft)
    page.add(create_expansion_tile)

    # Add checkboxes to the page for various actions
    bookmark_checkbox = ft.Checkbox(label="Add to Bookmark List", value=False, ref=bookmark_checkbox_ref)
    page.add(bookmark_checkbox)
    timed_pub_checkbox = ft.Checkbox(label="Add to Timed Publishing", value=False, ref=timed_pub_checkbox_ref)
    page.add(timed_pub_checkbox)

    # Add GO button to the page
    page.add(
        ft.CupertinoFilledButton(
            "GO!",
            on_click=lambda e: fn.go(driver)
        ),
    )

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
