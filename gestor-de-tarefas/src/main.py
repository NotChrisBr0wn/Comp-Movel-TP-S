from dataclasses import field
from typing import Callable

import flet as ft


@ft.control
class Task(ft.Column):
    def __init__(self, task_name, on_status_change, on_delete, **kwargs):
        super().__init__(**kwargs)
        self.task_name = task_name
        self.on_status_change = on_status_change
        self.on_delete = on_delete
        self.completed = False
        self.display_task = ft.Checkbox(
            value=False, label=self.task_name, on_change=self.status_changed
        )
        self.edit_name = ft.TextField(expand=1)
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
                        ),
                        ft.IconButton(
                            ft.Icons.DELETE_OUTLINE,
                            tooltip="Delete To-Do",
                            on_click=self.delete_clicked,
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
        self.display_task.label =self.edit_name.value # atualiza o estado interno
        self.display_view.visible = True
        self.edit_view.visible = False
        await self.on_status_change() # notifica a mudança de estado
        self.update()

    async def status_changed(self, e):
        self.completed = self.display_task.value
        await self.on_status_change()

    async def delete_clicked(self, e):
        await self.on_delete(self)


@ft.control
class TodoApp(ft.Column):
    # application's root control is a Column containing all other controls
    def __init__(self, page: ft.Page):
        super().__init__()
        self._page = page
        self.new_task = ft.TextField(hint_text="Whats needs to be done?", expand=True)
        self.tasks = ft.Column()

        self.filter = ft.TabBar(
            scrollable=False,
            tabs=[
                ft.Tab(label="All"),
                ft.Tab(label="Active"),
                ft.Tab(label="Completed"),
            ],
        )

        self.items_left = ft.Text("0 items left")

        self.filter_tabs = ft.Tabs(
            length=3,
            selected_index=0,
            on_change=lambda e: self.update(),
            content=self.filter,
        )

        self.width = 600
        self.controls = [
            ft.Row(
                controls=[
                    self.new_task,
                    ft.FloatingActionButton(
                        icon=ft.Icons.ADD, on_click=self.add_clicked
                    ),
                ],
            ),
            ft.Column(
                spacing=25,
                controls=[
                    self.filter_tabs,
                    self.tasks,
                ],
            ),
            ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    self.items_left,
                    ft.OutlinedButton(
                        "Clear Completed",
                        on_click=self.clear_completed,
                    )
                ],
            ),
        ]

        self.load_tasks()

    async def save_task(self):
        # Guardar as tarefas no client storage e duckDB (parquet)
        tasks_data = [
            {"name": task.display_task.label, "completed": task.completed}
            for task in self.tasks.controls
        ]

        # Client-Side
        await self._page.shared_preferences.set("todo_tasks", json.dumps(tasks_data))

        # DuckDB (parquet)
        if tasks_data:
            df = pd.DataFrame(tasks_data)
            db.execute("COPY df TO 'tasks.parquet' (FORMAT 'PARQUET')")
        else: # Se não houver tarefas remove o arquivo parquet
            if os.path.exists("tasks.parquet"):
                os.remove("tasks.parquet")
    
    async def load_tasks(self):
        # Carregar tarefas do client storage
        tasks_data = []
        if os.path.exists("tasks.parquet"):
            try:
                tasks_data = db.execute("SELECT * FROM 'tasks.parquet'").fetchall() # Tenta carregar do parquet
                tasks_data = [{"name": t[0], "completed": t[1]} for t in tasks_data]
            except Exception:
                raw_data = await self._page.shared_preferences.get("todo_tasks") # Fallback para client storage se houver algum problema com o parquet
                tasks_data = json.loads(raw_data) if raw_data else []
        else:
            raw_data = await self._page.shared_preferences.get("todo_tasks") # Fallback para client storage se o parquet não existir
            tasks_data = json.loads(raw_data) if raw_data else []

        # Limpa as tarefas atuais antes de carregar as novas
        self.tasks.controls.clear()

        # Constroi a UI com as tarefas carregadas
        for task in tasks_data:
            new_task = Task(
                task_name=task["name"],
                on_status_change=self.task_status_change,
                on_delete=self.task_delete,
            )
            new_task.completed = task["completed"]
            new_task.display_task.value = task["completed"]
            self.tasks.controls.append(new_task)
        self.update()


    async def add_clicked(self, e):
        if self.new_task.value:
            task = Task(task = Task(self.new_task.value, self.task_status_change, self.task_delete))
            self.tasks.controls.append(task)
            self.new_task.value = ""
            self.save_task()
            self.update()

    async def task_status_change(self):
        await self.save_task()
        self.update()

    async def task_delete(self, task):
        self.tasks.controls.remove(task)
        await self.save_task()
        self.update()

    async def clear_completed(self, e):
        self.tasks.controls = [
            task for task in self.tasks.controls if not task.completed
        ]
        await self.save_task()
        self.update()

    def before_update(self):
        status = self.filter.tabs[self.filter_tabs.selected_index].label.lower()
        active_tasks = 0
        for task in self.tasks.controls:
            task.visible = (
                status == "all"
                or (status == "active" and not task.completed)
                or (status == "completed" and task.completed)
            )
            if not task.completed:
                active_tasks += 1
        
        self.items_left.value = f"{active_tasks} active item(s) left"

async def main(page: ft.Page):
    page.title = "To-Do App"
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    app = TodoApp(page)
    page.add(app)

ft.run(main)