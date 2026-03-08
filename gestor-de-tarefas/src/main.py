import flet as ft
import os
import duckdb as db
import pandas as pd
import json
from typing import Optional
from encryption import EncryptionManager

@ft.control
class Task(ft.Column):
    def __init__(self, task_name, on_status_change, on_delete, on_name_change, **kwargs):
        super().__init__(**kwargs)
        self.task_name = task_name
        self.on_status_change = on_status_change
        self.on_delete = on_delete
        self.on_name_change = on_name_change
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
        await self.on_name_change(self.edit_name.value) # notifica a mudança de nome
        self.update()

    async def status_changed(self, e):
        await self.on_status_change(e)

    async def delete_clicked(self, e):
        await self.on_delete(e)

@ft.control
class TodoApp(ft.Column):
    # application's root control is a Column containing all other controls
    def __init__(self, page: ft.Page, user_id: str, user_name: str):
        super().__init__(spacing=10)
        self._page = page
        self.user_id = user_id
        self.user_name = user_name
        # Responsive width based on screen size
        self.width = min(600, page.width * 0.9) if page.width else 600
        self.db_tasks: list[dict] = []  # Central list for task data
        # Initialize encryption manager
        self.encryption: Optional[EncryptionManager] = None
        try:
            self.encryption = EncryptionManager()
        except ValueError as e:
            print(f"Warning: {e}")
        self.new_task = ft.TextField(
            hint_text="Whats needs to be done?",
            expand=True,
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

    def _get_user_storage_key(self) -> str:
        return f"todo_tasks:{self.user_id}"

    def _get_user_parquet_path(self) -> str:
        safe_user_id = "".join(
            char if char.isalnum() or char in ("-", "_") else "_"
            for char in self.user_id
        )
        storage_dir = os.path.join("storage", "data")
        os.makedirs(storage_dir, exist_ok=True)
        return os.path.join(storage_dir, f"tasks_{safe_user_id}.parquet")

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
        user_storage_key = self._get_user_storage_key()
        parquet_path = self._get_user_parquet_path()
        
        # Convert to JSON string
        json_data = json.dumps(tasks_data)
        
        # Encrypt data if encryption is available
        if self.encryption:
            try:
                json_data = self.encryption.encrypt(json_data)
            except Exception as e:
                print(f"Encryption error: {e}")

        # Client-Side
        prefs = ft.SharedPreferences()
        await prefs.set(user_storage_key, json_data)

        # DuckDB (parquet) - store encrypted data
        if tasks_data:
            # Store as single encrypted string in parquet
            df = pd.DataFrame([{"encrypted_data": json_data}])
            db.execute(f"COPY df TO '{parquet_path}' (FORMAT 'PARQUET')")
        else: # Se não houver tarefas remove o arquivo parquet
            if os.path.exists(parquet_path):
                os.remove(parquet_path)
    
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
                async def on_name_change(new_name):
                    await self.task_name_change(d, new_name)
                return on_status_change, on_delete, on_name_change

            on_status_change_handler, on_delete_handler, on_name_change_handler = create_handlers(data)
            
            task_ui = Task(
                data["name"],
                on_status_change=on_status_change_handler,
                on_delete=on_delete_handler,
                on_name_change=on_name_change_handler,
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
        user_storage_key = self._get_user_storage_key()
        parquet_path = self._get_user_parquet_path()
        encrypted_data = None
        
        if os.path.exists(parquet_path):
            try:
                result = db.execute("SELECT * FROM 'tasks.parquet'").fetchall()
                if result and len(result) > 0:
                    # New encrypted format
                    encrypted_data = result[0][0]
            except Exception as e:
                print(f"Error loading from parquet: {e}")
                # Fallback to shared_preferences if parquet fails
                prefs = ft.SharedPreferences()
                encrypted_data = await prefs.get(user_storage_key)
        else:
            # Load from shared_preferences if parquet doesn't exist
            prefs = ft.SharedPreferences()
            encrypted_data = await prefs.get(user_storage_key)
        
        # Decrypt and parse data
        if encrypted_data:
            try:
                # Try to decrypt if encryption is available
                if self.encryption:
                    decrypted_data = self.encryption.decrypt(encrypted_data)
                    tasks_data = json.loads(decrypted_data)
                else:
                    # If no encryption available, try to parse as plain JSON
                    tasks_data = json.loads(encrypted_data)
            except Exception as e:
                print(f"Error decrypting/parsing data: {e}")
                # Try parsing as plain JSON (backward compatibility)
                try:
                    tasks_data = json.loads(encrypted_data)
                except:
                    tasks_data = []

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

    async def task_name_change(self, task_data, new_name):
        task_data['name'] = new_name
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
    page.padding = ft.padding.only(left=20, right=20, top=70, bottom=20)  # top padding (default on ios was too high)
    page.on_logout = None


    app_state: dict[str, Optional[TodoApp]] = {"app": None}

    github_client_id = os.getenv("GITHUB_CLIENT_ID")
    github_client_secret = os.getenv("GITHUB_CLIENT_SECRET")
    github_redirect_url = os.getenv("GITHUB_REDIRECT_URL", "http://localhost:8550/oauth_callback")

    oauth_provider: Optional[ft.auth.GitHubOAuthProvider] = None
    if github_client_id and github_client_secret:
        oauth_provider = ft.auth.GitHubOAuthProvider(
            client_id=github_client_id,
            client_secret=github_client_secret,
            redirect_url=github_redirect_url,
        )

    def _extract_user_name(user: object) -> str:
        for key in ("name", "login", "email"):
            try:
                value = getattr(user, key, None)
                if value:
                    return str(value)
            except Exception:
                pass
        return "User"

    def _get_auth_user() -> object | None:
        if not page.auth:
            return None
        return getattr(page.auth, "user", None)

    async def show_login_view(message: Optional[str] = None):
        app_state["app"] = None

        async def login_click(e):
            if oauth_provider:
                try:
                    await page.login(oauth_provider, scope=["read:user"])
                except NotImplementedError:
                    await show_login_view(
                        "OAuth is not supported in this runtime. Run: flet run -w -p 8550 src/main.py"
                    )

        login_button = ft.Button(
            "Login with GitHub",
            disabled=oauth_provider is None,
            on_click=login_click,
        )

        info_text = "Configure GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET in .env to enable OAuth login."
        if oauth_provider:
            info_text = "Authenticate with GitHub to access your tasks."

        controls: list[ft.Control] = [
            ft.Text("To-Do App", size=30, weight=ft.FontWeight.BOLD),
            ft.Text(info_text),
            login_button,
        ]

        if message:
            controls.insert(1, ft.Text(message, color=ft.Colors.RED_500))

        page.clean()
        page.add(
            ft.Container(
                content=ft.Column(
                    controls=controls,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=16,
                ),
                expand=True,
            )
        )
        page.update()

    async def show_todo_app():
        auth_user = _get_auth_user()
        if not auth_user:
            await show_login_view("Authentication required.")
            return

        current_user_id = str(getattr(auth_user, "id", ""))
        if not current_user_id:
            await show_login_view("Could not read authenticated user id.")
            return

        current_user_name = _extract_user_name(auth_user)

        app = TodoApp(page, user_id=current_user_id, user_name=current_user_name)
        app_state["app"] = app

        top_padding = 5 if page.platform in ("android", "ios") else 8

        page.clean()
        page.add(
            ft.Container(
                content=ft.Row(
                    controls=[
                        ft.Text(f"Signed in: {current_user_name}", size=14),
                        ft.IconButton(
                            icon=ft.Icons.LOGOUT,
                            icon_size=24,
                            on_click=lambda e: page.logout(),
                            tooltip="Logout",
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                padding=ft.padding.only(top=top_padding, left=10, right=10, bottom=5),
            ),
            app,
        )
        await app.load_tasks()  # Load user-specific tasks
        page.update()

    async def on_login(e: ft.LoginEvent):
        if e.error:
            await show_login_view(f"Login failed: {e.error}")
            return
        await show_todo_app()

    async def on_logout(e):
        await show_login_view("You have been logged out.")
    
    def on_resize(e):
        if app_state["app"]:
            app_state["app"].width = min(600, page.width * 0.9) if page.width else 600
            page.update()
    
    page.on_resize = on_resize

    page.on_login = on_login
    page.on_logout = on_logout

    if _get_auth_user():
        await show_todo_app()
    else:
        await show_login_view()

PORT = int(os.getenv("PORT") or os.getenv("REPL_PORT") or "8080")
HOST = os.getenv("HOST", "0.0.0.0")

ft.app(
    target=main,
    host=HOST,
    port=PORT,
    assets_dir="../assets",
)
