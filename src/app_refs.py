# app_refs.py
import flet as ft

# Define your Flet Ref declarations
# -----------------------------------------------------------------------------
bookmark_checkbox_ref = ft.Ref[ft.Checkbox]( )
bookmark_name_ref = ft.Ref[ft.TextField]( )
timed_pub_checkbox_ref = ft.Ref[ft.Checkbox]( )
timed_pub_date_ref = ft.Ref[ft.TextField]( )
timed_pub_time_ref = ft.Ref[ft.TextField]( )
disable_with_same_message_checkbox_ref = ft.Ref[ft.Checkbox]( )
status_text_ref = ft.Ref[ft.Text]( )
loading_status_ref = ft.Ref[ft.Text]( )
progress_bar_ref = ft.Ref[ft.ProgressBar]( )
go_button_ref = ft.Ref[ft.CupertinoFilledButton]( )
completion_message_ref = ft.Ref[ft.Text]( )
