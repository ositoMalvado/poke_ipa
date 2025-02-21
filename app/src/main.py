import flet as ft
import os
from datetime import datetime

DOWNLOAD_PATH = "/private/var/mobile/Containers/Data/Application/1DF36343-6CB2-4EB8-8B05-82B53EBE4E28/tmp/"


class DebugViewer(ft.Container):
    def add(self, value):
        self.content.value += f"{value}\n"
        self.content.update()

    def __init__(self):
        super().__init__()
        self.content = ft.TextField(read_only=True, multiline=True, expand=True)


class FilePick(ft.Container):
    def did_mount(self):
        self.page.overlay.append(self.fp)
        self.page.update()
        return super().did_mount()

    def __init__(self):
        super().__init__()
        self.fp = ft.FilePicker(on_result=self.pick_files_result)
        self.info_show = ft.Text()
        self.column = ft.Column(
            [
                ft.ElevatedButton(
                    "Pick files",
                    icon=ft.icons.UPLOAD_FILE,
                    on_click=lambda _: self.fp.pick_files(allow_multiple=True),
                ),
                self.info_show,
            ]
        )
        self.content = self.column
        self.expand = True

    def pick_files_result(self, e: ft.FilePickerResultEvent):
        data = f"{self.fp.result.files[0].path}" if self.fp.result else "User canceled!"
        print(data)
        self.info_show.value = data
        self.info_show.update()


def main(page: ft.Page):
    page.title = "Pokédex"
    page.theme_mode = ft.ThemeMode.DARK
    # page.window_width = 400
    # page.window_height = 800
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

    def click_float(e):
        dv.add("click")

    page.floating_action_button = ft.FloatingActionButton(
        icon=ft.icons.ADD,
        on_click=click_float,
    )

    dv = DebugViewer()
    fp = FilePick()

    page.add(
        ft.Column(
            [
                fp,
                dv,
            ],
            expand=True,
            scroll="auto",
        )
    )

    # i want to iterate over every file on DOWNLOAD_PATH with os and dv.add(file_path)
    try:
        for file in os.listdir(DOWNLOAD_PATH):
            dv.add(file)
            print(file)
    except:
        pass

    #  now i want to write actual datetime on a datetime.txt in DOWNLOAD_PATH
    print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "fecha")
    try:
        with open(DOWNLOAD_PATH + "datetime.txt", "w") as f:
            f.write(str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

    except:
        pass


ft.app(target=main, view=ft.AppView.WEB_BROWSER)
