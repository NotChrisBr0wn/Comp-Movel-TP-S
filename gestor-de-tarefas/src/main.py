import flet as ft
import os
import duckdb as db
import pandas as pd
import json
from dataclasses import field
from typing import Callable


@ft.control
class Task(ft.Column):
    def __init__(self, task_name, on_status_change, on_delete, **kwargs):
        super().__init__(**kwargs)
        self.task_name = task_name
        self.on_status_change = on_status_change
        self.on_delete = on_delete
        self.completed = False
        self.display_task = ft.Checkbox(
            value=False,
            label=self.task_name,
            on_change=self.status_changed,
            adaptive=True,
        )
        self.edit_name = ft.TextField(expand=1, adaptive=True)
        self.display_view = ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                self.display_task,
                ft.Row(
                    spacing=0,
                    controls=[
                        ft.IconButton(
                            icon=ft.Icons.CREATE_OUTLINED,
                            tooltip="Edit To-Do",
                            on_click=self.edit_clicked,
                            adaptive=True,
                        ),
                        ft.IconButton(
                            ft.Icons.DELETE_OUTLINE,
                            tooltip="Delete To-Do",
                            on_click=self.delete_clicked,
                            adaptive=True,
                        ),
                    ],
                ),
            ],
        )

        self.edit_view = ft.Row(
            visible=False,
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                self.edit_name,
                ft.IconButton(
                    icon=ft.Icons.DONE_OUTLINE_OUTLINED,
                    icon_color=ft.Colors.GREEN,
                    tooltip="Update To-Do",
                    on_click=self.save_clicked,
                    adaptive=True,
                ),
            ],
        )
        self.controls = [self.display_view, self.edit_view]


    def edit_clicked(self, e):
        self.edit_name.value = self.display_task.label
        self.display_view.visible = False
        self.edit_view.visible = True
        self.update()

    async def save_clicked(self, e):
        self.display_task.label = self.edit_name.value 
        self.display_view.visible = True
        self.edit_view.visible = False
        await self.on_status_change() # notifica a mudança de estado
        self.update()

    async def status_changed(self, e):
        await self.on_status_change(e)

    async def delete_clicked(self, e):
        await self.on_delete(e)

@ft.control
class TodoApp(ft.Column):
    # application's root control is a Column containing all other controls
    def __init__(self, page: ft.Page):
        super().__init__(spacing=10)
        self._page = page
        # Responsive width based on screen size
        self.width = min(600, page.width * 0.9) if page.width else 600
        self.db_tasks: list[dict] = []  # Central list for task data
        self.new_task = ft.TextField(
            hint_text="Whats needs to be done?",
            expand=True,
            adaptive=True,
        )

        # The main views for tasks
        self.tasks_view = ft.Column(spacing=5, controls=[])
        self.active_tasks_view = ft.Column(spacing=5, controls=[])
        self.completed_tasks_view = ft.Column(spacing=5, controls=[])
        
        # Current view tracker
        self.current_view = 0
        
        # Tab buttons
        self.all_tab = ft.TextButton("All", on_click=lambda e: self.switch_tab(0))
        self.active_tab = ft.TextButton("Active", on_click=lambda e: self.switch_tab(1))
        self.completed_tab = ft.TextButton("Completed", on_click=lambda e: self.switch_tab(2))
        
        # Container to hold the current view
        self.view_container = ft.Container(
            content=self.tasks_view,
            expand=True,
        )

        self.items_left = ft.Text("0 active item(s) left")

        self.controls = [
            ft.Row(
                controls=[
                    self.new_task,
                    ft.FloatingActionButton(
                        icon=ft.Icons.ADD,
                        on_click=self.add_clicked,
                    ),
                ],
            ),
            ft.Row(
                controls=[
                    self.all_tab,
                    self.active_tab,
                    self.completed_tab,
                ],
                spacing=10,
            ),
            self.view_container,
            ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                wrap=True,
                controls=[
                    self.items_left,
                    ft.OutlinedButton(
                        "Clear Completed",
                        on_click=self.clear_completed,
                        adaptive=True,
                    )
                ],
            ),
        ]

    async def did_mount(self):
        await self.load_tasks()

    def switch_tab(self, index):
        self.current_view = index
        if index == 0:
            self.view_container.content = self.tasks_view
        elif index == 1:
            self.view_container.content = self.active_tasks_view
        elif index == 2:
            self.view_container.content = self.completed_tasks_view
        self.update()

    async def save_task(self):
        # Guardar as tarefas no client storage e duckDB (parquet)
        tasks_data = self.db_tasks

        # Client-Side (using new SharedPreferences API)
        prefs = ft.SharedPreferences(self._page)
        await prefs.set("todo_tasks", json.dumps(tasks_data))

        # DuckDB (parquet)
        if tasks_data:
            df = pd.DataFrame(tasks_data)
            db.execute("COPY df TO 'tasks.parquet' (FORMAT 'PARQUET')")
        else: # Se não houver tarefas remove o arquivo parquet
            if os.path.exists("tasks.parquet"):
                os.remove("tasks.parquet")
    
    def _update_views(self):
        self.tasks_view.controls.clear()
        self.active_tasks_view.controls.clear()
        self.completed_tasks_view.controls.clear()
        
        active_tasks_count = 0

        # A function to create a Task UI instance for a given data dict
        def create_task_ui(data):
            # Closure to capture the data for the handlers
            def create_handlers(d):
                async def on_status_change(e):
                    await self.task_status_change(d, e.control.value)
                async def on_delete(e):
                    await self.task_delete(d)
                return on_status_change, on_delete

            on_status_change_handler, on_delete_handler = create_handlers(data)
            
            task_ui = Task(
                data["name"],
                on_status_change=on_status_change_handler,
                on_delete=on_delete_handler,
            )
            task_ui.display_task.value = data["completed"]
            return task_ui

        for task_data in self.db_tasks:
            # Create an instance for the "All" view
            self.tasks_view.controls.append(create_task_ui(task_data))

            # Create another instance for the "Active" or "Completed" view
            if task_data["completed"]:
                self.completed_tasks_view.controls.append(create_task_ui(task_data))
            else:
                active_tasks_count += 1
                self.active_tasks_view.controls.append(create_task_ui(task_data))
        
        self.items_left.value = f"{active_tasks_count} active item(s) left"
        self.update()

    async def load_tasks(self):
        # Carregar tarefas do client storage
        tasks_data = []
        parquet_path = "tasks.parquet"
        
        if os.path.exists(parquet_path):
            try:
                result = db.execute("SELECT * FROM 'tasks.parquet'").fetchall()
                tasks_data = [{"name": t[0], "completed": t[1]} for t in result]
            except Exception as e:
                # Fallback to shared_preferences if parquet fails
                prefs = ft.SharedPreferences(self._page)
                raw_data = await prefs.get("todo_tasks")
                tasks_data = json.loads(raw_data) if raw_data else []
        else:
            # Load from shared_preferences if parquet doesn't exist
            prefs = ft.SharedPreferences(self._page)
            raw_data = await prefs.get("todo_tasks")
            tasks_data = json.loads(raw_data) if raw_data else []

        self.db_tasks = tasks_data
        self._update_views()


    async def add_clicked(self, e):
        if self.new_task.value:
            # Create a new task as a dictionary
            new_task_data = {"name": self.new_task.value, "completed": False}
            # Add it to our central data list
            self.db_tasks.append(new_task_data)
            # Clear the input field
            self.new_task.value = ""
            # Save the updated list of tasks
            await self.save_task()
            # Re-render the UI from the data
            self._update_views()

    async def task_status_change(self, task_data, completed):
        task_data['completed'] = completed
        await self.save_task()
        self._update_views()

    async def task_delete(self, task_data):
        self.db_tasks.remove(task_data)
        await self.save_task()
        self._update_views()

    async def clear_completed(self, e):
        self.db_tasks = [task for task in self.db_tasks if not task["completed"]]
        await self.save_task()
        self._update_views()

async def main(page: ft.Page):
    page.title = "To-Do App"
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.scroll = ft.ScrollMode.ADAPTIVE
    page.padding = 20
    
    # Update app width on window resize
    def on_resize(e):
        if hasattr(page, 'controls') and page.controls:
            app = page.controls[0]
            app.width = min(600, page.width * 0.9) if page.width else 600
            page.update()
    
    page.on_resize = on_resize
    
    app = TodoApp(page)
    page.add(app)
    await app.load_tasks()  # Load tasks after adding to page

ft.run(main)