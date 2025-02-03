import flet as ft
from pokeclient import AsyncPokeAPI
import asyncio


class PokeImage(ft.Container):

    async def handle_get(self, index):
        await self.api.get_pokemon(index)
        await self.api.get_image(index)

    def load_near_pokemons(self):
        tasks = []
        current_index = self.index
        max_index = self.max_index  # Asegúrate de que max_index es 649

        # Generar índices desde current -5 hasta current +5 (11 índices en total)
        for i in range(
            current_index - 5, current_index + 6
        ):  # +6 porque range es exclusivo al final
            # Ajustar cada índice usando módulo para que esté entre 1 y max_index
            adjusted_i = (i - 1) % max_index + 1
            tasks.append(self.handle_get(adjusted_i))

        # Ejecutar todas las tareas asincrónicas
        asyncio.gather(*tasks)

    async def set_pokemon(self, index=1):
        self.ring.visible = True
        self.ring.update()
        await self.handle_get(index)
        self.img_container.content = ft.Image(src=f"assets/poke_cache/images/{index}.png")
        self.img_container.update()
        self.ring.visible = False
        self.ring.update()
        self.index = index
        self.load_near_pokemons()
        self.tf_number.value = str(index)
        self.tf_number.update()

    async def will_unmount(self):
        if self.api:
            await self.api.close()

    def did_mount(self):
        self.api = AsyncPokeAPI()

        self.page.run_task(self.api.ensure_session)
        self.page.run_task(self.set_pokemon, self.index)
        return super().did_mount()

    def nav_button(self, e):
        #  i need to go from 1 to 649 and then 1 or from 649 to 1
        # never 0, or 1 or max_index
        if e.control.data == "prev":
            final_index = self.index - 1 if self.index > 1 else self.max_index
            self.page.run_task(self.set_pokemon, final_index)
        elif e.control.data == "next":
            final_index = self.index + 1 if self.index < self.max_index else 1
            self.page.run_task(self.set_pokemon, final_index)

    def __init__(self, index: int = 1, max_index: int = 649):
        if index < 1 or index > 649:
            raise ValueError("index must be between 1 and 649")
        super().__init__()
        self.api = None  # Inicializar después en did_mount
        self.initiated = False
        self.index = index
        self.max_index = max_index
        self.alignment = ft.alignment.center
        self.img_container = ft.Container(
            alignment=ft.alignment.center,
            width=300,
            height=300,
        )
        self.ring = ft.ProgressRing(
            visible=False, expand=True, width=300, height=300, stroke_width=10
        )
        def generate_range_regex(max_index):
            if max_index < 0:
                raise ValueError("max_index no puede ser negativo")
            
            # Casos especiales: 0 o 1
            if max_index == 0:
                return r"^$|^0$"  # Solo permite "" o "0"
            elif max_index == 1:
                return r"^$|^[01]$"  # Permite "", "0", "1"
            
            max_str = str(max_index)
            length = len(max_str)
            patterns = []
            
            # Patrones para números con menos dígitos que max_index (1 a 9, 10 a 99, etc.)
            for i in range(1, length):
                if i == 1:
                    patterns.append("[1-9]")  # 1-9
                else:
                    patterns.append(f"[1-9]\\d{{0,{i-1}}}")  # 10-99, 100-999, etc.
            
            # Patrones para números con la misma cantidad de dígitos que max_index
            same_length_pattern = []
            for i in range(length):
                digit = int(max_str[i])
                prefix = max_str[:i]
                min_digit = 1 if i == 0 else 0  # Evitar ceros a la izquierda
                
                if i < length - 1:
                    if digit > min_digit:
                        # Rango válido para dígitos no finales (ej. 1[0-2]\\d para 100-129 si max=135)
                        same_length_pattern.append(f"{prefix}[{min_digit}-{digit-1}]\\d{{{length-i-1}}}")
                else:
                    # Último dígito: rango completo (ej. 13[0-5] para 130-135)
                    same_length_pattern.append(f"{prefix}[{min_digit}-{digit}]")
            
            if same_length_pattern:
                patterns.append("|".join(same_length_pattern))
            
            # Combinar todo y añadir opciones para "" y "0"
            numbers_1_to_max = "|".join(patterns)
            return f"^$|^0$|^({numbers_1_to_max})$"
        
        
        def blur(e):
            if self.tf_number.value == "":
                self.tf_number.value = str(self.index)
                self.tf_number.update()
                
        def change(e):
            try:
                new_index = int(self.tf_number.value)
                if new_index != self.index:
                    self.page.run_task(self.set_pokemon, new_index)
            except ValueError:
                self.tf_number.value = str(self.index)
                self.tf_number.update()
        
        self.tf_number = ft.TextField(
            label="",
            value=str(self.index),
            width=90,
            input_filter=ft.InputFilter(regex_string=generate_range_regex(self.max_index)),
            on_blur=blur,
            on_change=change
        )
        self.controls = ft.Container(
            expand=True,
            height=300,
            alignment=ft.alignment.top_center,
            content=ft.Row(
                alignment=ft.MainAxisAlignment.CENTER,
                controls=[
                    ft.IconButton(
                        icon=ft.Icons.ARROW_LEFT_ROUNDED,
                        on_click=self.nav_button,
                        data="prev",
                    ),
                    self.tf_number,
                    ft.IconButton(
                        icon=ft.Icons.ARROW_RIGHT_ROUNDED,
                        on_click=self.nav_button,
                        data="next",
                    ),
                ],
            ),
        )
        self.content = ft.Stack(
            [
                ft.Column(
                    [
                        ft.Stack(
                            controls=[
                                self.img_container,
                                self.ring,
                            ],
                            expand=True,
                            alignment=ft.alignment.center,
                        ),
                        self.controls,
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    expand=True,
                ),
            ],
            expand=True,
            alignment=ft.alignment.center,
        )


async def main(page: ft.Page):

    page.title = "Pokedex"
    page.window.width = 600
    page.window.height = 600

    page.add(PokeImage(1))


ft.app(main, view=ft.AppView.WEB_BROWSER, assets_dir="assets")
