import sys, os, ctypes, subprocess, shutil, time, json, psutil, tempfile
from ctypes import wintypes
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton,
    QListWidget, QFileDialog, QSystemTrayIcon, QMenu,
    QMessageBox, QStyle, QLabel, QCheckBox, QStatusBar
)
from PySide6.QtGui import QIcon, QAction, QPixmap, QFont
from PySide6.QtCore import Qt, QSettings, QTimer

# Directory to store wallpaper videos
VIDEO_DIR = os.path.join(os.getcwd(), "Wallpapers")
os.makedirs(VIDEO_DIR, exist_ok=True)

current_process = None  # Wallpaper process
preview_process = None  # Preview process
is_muted = True
is_looping = True
mpv_socket = None  # MPV IPC socket path
last_mute_state = None  # Track last mute state
pending_mute = None  # Track pending mute state
audio_control_enabled = True  # Flag for audio control
temp_log_file = os.path.join(tempfile.gettempdir(), "mpv_debug.log")  # Temporary MPV log file

def terminate_lingering_mpv():
    """
    Terminate any lingering MPV processes to avoid socket conflicts.
    """
    print("[DEBUG] Checking for lingering MPV processes")
    for proc in psutil.process_iter(['name', 'pid']):
        if proc.info['name'].lower() == 'mpv.exe' and proc.pid != (current_process.pid if current_process else -1):
            print(f"[INFO] Terminating lingering MPV process: PID {proc.pid}")
            proc.terminate()
            try:
                proc.wait(timeout=3)
                print(f"[INFO] MPV process {proc.pid} terminated successfully")
            except psutil.TimeoutExpired:
                print(f"[WARNING] MPV process {proc.pid} did not terminate gracefully, killing")
                proc.kill()

def check_pipe_availability(pipe_name):
    """
    Check if the named pipe is available.
    """
    try:
        import win32file
        import win32pipe
        from win32con import GENERIC_READ, GENERIC_WRITE, OPEN_EXISTING
        handle = win32file.CreateFile(
            pipe_name,
            GENERIC_READ | GENERIC_WRITE,
            0,
            None,
            OPEN_EXISTING,
            win32file.FILE_FLAG_OVERLAPPED,
            None
        )
        win32file.CloseHandle(handle)
        print(f"[INFO] Named pipe {pipe_name} is accessible")
        return True
    except Exception as e:
        print(f"[DEBUG] Named pipe {pipe_name} not accessible: {e}")
        return False

def is_desktop_active():
    """
    Check if the desktop is currently active (no other apps in foreground).
    """
    foreground_window = ctypes.windll.user32.GetForegroundWindow()
    if not foreground_window:
        print("[DEBUG] No foreground window detected, assuming desktop is active")
        return True
    
    desktop = ctypes.windll.user32.GetDesktopWindow()
    shell = ctypes.windll.user32.FindWindowW("Progman", None)
    worker_w = get_desktop_handle()
    
    class_name = ctypes.create_string_buffer(256)
    ctypes.windll.user32.GetClassNameW(foreground_window, class_name, 256)
    class_str = class_name.value.decode('utf-8', errors='ignore')
    
    title = ctypes.create_string_buffer(256)
    ctypes.windll.user32.GetWindowTextW(foreground_window, title, 256)
    title_str = title.value.decode('utf-8', errors='ignore')
    
    is_desktop = (
        foreground_window == desktop or
        foreground_window == shell or
        (worker_w and foreground_window == worker_w) or
        class_str in ["Progman", "WorkerW", "Shell_TrayWnd"] or
        title_str.lower() in ["", "program manager"]
    )
    
    print(f"[DEBUG] Foreground window: {foreground_window}, Class: {class_str}, Title: {title_str}, Is Desktop: {is_desktop}")
    return is_desktop

def get_desktop_handle():
    """
    Retrieve the handle of the WorkerW window for the desktop wallpaper.
    """
    print("[DEBUG] Attempting to find desktop handle")
    progman = ctypes.windll.user32.FindWindowW("Progman", None)
    if not progman:
        print("[ERROR] Progman window not found.")
        return None

    ctypes.windll.user32.SendMessageW(progman, 0x052C, 0, 0)

    worker_w = ctypes.windll.user32.FindWindowExW(progman, 0, "WorkerW", None)
    if worker_w:
        print(f"[INFO] Found WorkerW window handle (fallback): {worker_w}")
        return worker_w

    def enum_windows_proc(hwnd, lParam):
        if ctypes.windll.user32.IsWindowVisible(hwnd):
            class_name = ctypes.create_string_buffer(256)
            ctypes.windll.user32.GetClassNameW(hwnd, class_name, 256)
            class_str = class_name.value.decode('utf-8')
            print(f"[DEBUG] Checking window: {hwnd}, Class: {class_str}")
            if class_name.value == b"WorkerW":
                shell_dll = ctypes.windll.user32.FindWindowExW(hwnd, 0, "SHELLDLL_DefView", None)
                if not shell_dll:
                    print(f"[INFO] Found potential wallpaper window: {hwnd}")
                    lParam.contents.value = hwnd
                    return False
        return True

    max_attempts = 3
    for attempt in range(max_attempts):
        lParam = ctypes.pointer(ctypes.c_int(0))
        ENUM_WINDOWS_PROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, ctypes.POINTER(ctypes.c_int))
        ctypes.windll.user32.EnumWindows(ENUM_WINDOWS_PROC(enum_windows_proc), lParam)
        wallpaper_hwnd = lParam.contents.value
        if wallpaper_hwnd:
            print(f"[INFO] Found wallpaper window handle: {wallpaper_hwnd}")
            return wallpaper_hwnd
        print(f"[WARNING] Attempt {attempt + 1}/{max_attempts}: WorkerW window not found")
        time.sleep(0.2)

    print("[ERROR] Fallback to WorkerW failed.")
    return None

def stop_video(is_preview=False):
    """
    Stop the currently playing video (wallpaper or preview).
    """
    global current_process, preview_process, mpv_socket, pending_mute, audio_control_enabled
    if is_preview and preview_process:
        print("[INFO] Stopping preview video.")
        preview_process.terminate()
        preview_process = None
    elif not is_preview and current_process:
        print("[INFO] Stopping wallpaper video.")
        current_process.terminate()
        current_process = None
        if mpv_socket and os.path.exists(mpv_socket):
            os.remove(mpv_socket)
            mpv_socket = None
        pending_mute = None
        audio_control_enabled = True
        if os.path.exists(temp_log_file):
            os.remove(temp_log_file)
            print(f"[INFO] Removed temporary MPV log file: {temp_log_file}")

def send_mpv_command(command, retries=5, delay=0.7):
    """
    Send a command to MPV via Windows named pipe with retries.
    """
    global mpv_socket, current_process, audio_control_enabled
    if not audio_control_enabled:
        print("[INFO] Audio control disabled due to previous socket failure")
        return False

    if not mpv_socket:
        print("[ERROR] MPV socket path not set")
        return False

    if not current_process or current_process.poll() is not None:
        print("[ERROR] MPV process is not running")
        return False

    try:
        import win32file
        import win32pipe
        from win32con import GENERIC_READ, GENERIC_WRITE, OPEN_EXISTING
    except ImportError as e:
        print(f"[ERROR] Failed to import pywin32 modules: {e}")
        print("[ERROR] Ensure pywin32 is installed (pip install pywin32).")
        audio_control_enabled = False
        QMessageBox.critical(None, "Error", "Failed to import pywin32 modules. Audio controls disabled. Ensure pywin32 is installed (pip install pywin32).")
        return False

    for attempt in range(retries):
        try:
            handle = win32file.CreateFile(
                mpv_socket,
                GENERIC_READ | GENERIC_WRITE,
                0,
                None,
                OPEN_EXISTING,
                win32file.FILE_FLAG_OVERLAPPED,
                None
            )
            cmd = json.dumps({"command": command}) + "\n"
            win32file.WriteFile(handle, cmd.encode('utf-8'))
            result, response = win32file.ReadFile(handle, 1024)
            win32file.CloseHandle(handle)
            print(f"[INFO] Sent MPV command: {command}, Response: {response.decode('utf-8')}")
            return True
        except Exception as e:
            print(f"[ERROR] Failed to send MPV command (attempt {attempt + 1}/{retries}): {e}")
            if attempt < retries - 1:
                time.sleep(delay)
    
    print(f"[ERROR] MPV socket {mpv_socket} unavailable after {retries} attempts")
    audio_control_enabled = False
    QMessageBox.warning(None, "Warning", f"Failed to initialize MPV audio controls due to socket failure: {mpv_socket}. Try running as administrator, reinstalling MPV, or checking for conflicting software.")
    return False

def check_audio_track(video_path):
    """
    Check if the video has an audio track using ffprobe or MPV.
    """
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_streams", "-select_streams", "a", "-print_format", "json", video_path],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0 and json.loads(result.stdout).get("streams"):
            print("[INFO] Video has an audio track (ffprobe).")
            return True
        print(f"[WARNING] No audio track detected by ffprobe. ffprobe stderr: {result.stderr}")
    except FileNotFoundError:
        print("[INFO] ffprobe not found, falling back to MPV for audio check")
    except Exception as e:
        print(f"[ERROR] ffprobe failed to check audio track: {e}")

    command = [
        "mpv",
        "--no-video",
        "--audio-only",
        "--quiet",
        video_path
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("[INFO] Video has an audio track (MPV).")
            return True
        else:
            print(f"[WARNING] Video has no audio track or MPV failed to process it. MPV stderr: {result.stderr}")
            return False
    except Exception as e:
        print(f"[ERROR] MPV failed to check audio track: {e}")
        return False

def play_video_as_wallpaper(video_path, mute=True, loop=True):
    """
    Play the specified video as the desktop wallpaper using MPV.
    """
    global current_process, mpv_socket, last_mute_state, pending_mute, audio_control_enabled
    stop_video(is_preview=False)
    terminate_lingering_mpv()
    
    has_audio = check_audio_track(video_path)
    if not has_audio:
        print("[WARNING] Selected video may not have an audio track. Audio controls may not work.")
        QMessageBox.warning(None, "Warning", "Selected video may not have an audio track. Try a different video for audio controls.")
    
    hwnd = get_desktop_handle()
    if not hwnd:
        print("[ERROR] Failed to find a valid desktop handle.")
        QMessageBox.critical(None, "Error", "❌ Failed to find desktop window.")
        return False

    width = ctypes.windll.user32.GetSystemMetrics(0)
    height = ctypes.windll.user32.GetSystemMetrics(1)

    # Try simple socket name first, fallback to unique name
    socket_names = ["mpvpipe", f"mpv_socket_{os.getpid()}_{int(time.time())}"]
    for socket_name in socket_names:
        mpv_socket = f"\\\\.\\pipe\\{socket_name}"
        command = [
            "mpv",
            f"--wid={hwnd}",
            "--loop" if loop else "--no-loop",
            "--no-border",
            f"--mute={'yes' if mute else 'no'}",
            f"--geometry={width}x{height}",
            f"--input-ipc-server={mpv_socket}",
            "--hwdec=dxva2",  # Force DXVA2 for Windows
            "--vo=gpu",
            "--profile=low-latency",
            f"--log-file={temp_log_file}",
            video_path
        ]

        print(f"[INFO] Wallpaper MPV Command: {' '.join(map(str, command))}")
        try:
            current_process = subprocess.Popen(command, stderr=subprocess.PIPE, text=True)
            # Wait for socket to be created
            for _ in range(30):  # Try for up to 15 seconds
                if check_pipe_availability(mpv_socket):
                    print(f"[INFO] MPV socket {mpv_socket} created successfully")
                    audio_control_enabled = True
                    break
                time.sleep(0.5)
            else:
                print(f"[ERROR] MPV socket {mpv_socket} not created after 15 seconds")
                continue  # Try next socket name
            
            # Read initial MPV debug output
            try:
                _, stderr = current_process.communicate(timeout=15)
                print(f"[ERROR] MPV stderr: {stderr}")
            except subprocess.TimeoutExpired:
                print("[ERROR] Timeout reading MPV stderr after 15 seconds")
            
            # Read log file
            if os.path.exists(temp_log_file):
                with open(temp_log_file, 'r', encoding='utf-8') as f:
                    print(f"[DEBUG] MPV log file contents: {f.read()}")
            
            last_mute_state = mute
            pending_mute = None
            print("[INFO] Wallpaper MPV launched successfully.")
            return True
        except FileNotFoundError:
            print("[ERROR] MPV not found.")
            QMessageBox.critical(None, "Error", "❌ MPV not found. Please install it and add to PATH.")
            return False
    
    # All socket names failed
    print("[ERROR] All MPV socket attempts failed, disabling audio controls")
    command = [
        "mpv",
        f"--wid={hwnd}",
        "--loop" if loop else "--no-loop",
        "--no-border",
        f"--mute={'yes' if mute else 'no'}",
        f"--geometry={width}x{height}",
        "--hwdec=dxva2",
        "--vo=gpu",
        "--profile=low-latency",
        f"--log-file={temp_log_file}",
        video_path
    ]
    try:
        current_process = subprocess.Popen(command, stderr=subprocess.PIPE, text=True)
        print("[INFO] Wallpaper MPV launched without IPC")
        # Read log file
        if os.path.exists(temp_log_file):
            with open(temp_log_file, 'r', encoding='utf-8') as f:
                print(f"[DEBUG] MPV log file contents: {f.read()}")
        audio_control_enabled = False
        last_mute_state = mute
        pending_mute = None
        QMessageBox.warning(None, "Warning", "Failed to initialize MPV audio controls. Wallpaper will play without audio toggling. Try running as administrator or reinstalling MPV.")
        return True
    except FileNotFoundError:
        print("[ERROR] MPV not found.")
        QMessageBox.critical(None, "Error", "❌ MPV not found. Please install it and add to PATH.")
        return False

def play_preview_video(video_path, widget, mute=True, loop=True):
    """
    Play the specified video in the preview widget using MPV.
    """
    global preview_process
    stop_video(is_preview=True)
    hwnd = widget.winId()
    command = [
        "mpv",
        f"--wid={hwnd}",
        "--loop" if loop else "--no-loop",
        "--no-border",
        f"--mute={'yes' if mute else 'no'}",
        "--geometry=100%",
        "--hwdec=dxva2",
        "--vo=gpu",
        "--profile=low-latency",
        video_path
    ]

    print(f"[INFO] Preview MPV Command: {' '.join(map(str, command))}")
    try:
        preview_process = subprocess.Popen(command)
        print("[INFO] Preview MPV launched successfully.")
        return True
    except FileNotFoundError:
        print("[ERROR] MPV not found for preview.")
        QMessageBox.critical(None, "Error", "❌ MPV not found for preview. Please install it and add to PATH.")
        return False

class LiveWallpaperApp(QWidget):
    def __init__(self):
        super().__init__()
        self.settings = QSettings("TeamEmogi", "LiveWallpaper")
        self.setWindowTitle("Live Wallpaper By Emogi")
        self.setMinimumSize(400, 500)
        self.resize(450, 600)

        self.setStyleSheet("""
            QWidget {
                background-color: #1e1e2f;
                color: #d4d4d4;
                font-family: 'Roboto', Arial, sans-serif;
            }
            QStatusBar {
                background-color: #252537;
                color: #d4d4d4;
                font-size: 12px;
            }
            QPushButton {
                background-color: #3b82f6;
                border: none;
                color: white;
                padding: 8px 16px;
                font-size: 14px;
                border-radius: 4px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #60a5fa;
            }
            QPushButton:pressed {
                background-color: #2563eb;
            }
            QListWidget {
                background-color: #252537;
                border: 1px solid #3b3b4f;
                color: #d4d4d4;
                font-size: 13px;
                border-radius: 4px;
            }
            QListWidget::item {
                padding: 5px;
            }
            QListWidget::item:selected {
                background-color: #3b82f6;
                color: white;
            }
            QListWidget::item:hover {
                background-color: #3b3b4f;
            }
            QLabel {
                font-size: 13px;
                color: #d4d4d4;
            }
            QCheckBox {
                color: #d4d4d4;
                font-size: 13px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
            }
        """)

        layout = QVBoxLayout()

        self.logo_label = QLabel()
        logo_path = "logo.png"
        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path).scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.logo_label.setPixmap(pixmap)
        else:
            self.logo_label.setText("Team Emogi Logo")
            self.logo_label.setStyleSheet("font-size: 16px; font-weight: bold; padding: 10px;")
        self.logo_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.logo_label)

        self.status_bar = QStatusBar()
        self.status_bar.setStyleSheet("padding: 5px;")
        self.status_bar.showMessage("Ready")
        layout.addWidget(self.status_bar)

        self.listbox = QListWidget()
        self.listbox.currentItemChanged.connect(self.show_preview)
        layout.addWidget(self.listbox)

        self.preview_widget = QWidget()
        self.preview_widget.setFixedHeight(150)
        self.preview_widget.setStyleSheet("background-color: #252537; border: 1px solid #3b3b4f; border-radius: 4px;")
        layout.addWidget(self.preview_widget)

        self.add_btn = QPushButton("Add Video")
        self.add_btn.setIcon(self.style().standardIcon(QStyle.SP_FileDialogNewFolder))
        self.add_btn.clicked.connect(self.add_video)
        layout.addWidget(self.add_btn)

        self.set_btn = QPushButton("Set Wallpaper")
        self.set_btn.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.set_btn.clicked.connect(self.set_wallpaper)
        layout.addWidget(self.set_btn)

        self.stop_btn = QPushButton("Stop Wallpaper")
        self.stop_btn.setIcon(self.style().standardIcon(QStyle.SP_MediaStop))
        self.stop_btn.clicked.connect(self.stop_wallpaper)
        layout.addWidget(self.stop_btn)

        self.mute_checkbox = QCheckBox("Mute Video")
        self.mute_checkbox.setChecked(True)
        self.mute_checkbox.stateChanged.connect(self.toggle_mute)
        layout.addWidget(self.mute_checkbox)

        self.loop_checkbox = QCheckBox("Loop Video")
        self.loop_checkbox.setChecked(True)
        self.loop_checkbox.stateChanged.connect(self.toggle_loop)
        layout.addWidget(self.loop_checkbox)

        self.footer_label = QLabel("Made by Ritesh, CEO of Team Emogi")
        self.footer_label.setAlignment(Qt.AlignCenter)
        self.footer_label.setStyleSheet("font-size: 11px; color: #6b7280; padding: 5px;")
        layout.addWidget(self.footer_label)

        self.setLayout(layout)
        self.refresh_list()

        self.load_settings()

        icon = QIcon("icon.ico") if os.path.exists("icon.ico") else self.style().standardIcon(QStyle.SP_ComputerIcon)
        self.tray_icon = QSystemTrayIcon(icon, self)
        self.tray_icon.setToolTip("Live Wallpaper Pro")

        menu = QMenu()
        open_action = QAction("Open", self)
        open_action.triggered.connect(self.show_normal)
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.exit_app)

        menu.addAction(open_action)
        menu.addSeparator()
        menu.addAction(exit_action)

        self.tray_icon.setContextMenu(menu)
        self.tray_icon.activated.connect(self.on_tray_icon_activated)
        self.tray_icon.show()

        self.desktop_timer = QTimer()
        self.desktop_timer.timeout.connect(self.check_desktop_state)
        self.desktop_timer.start(1000)

    def load_settings(self):
        """
        Load saved wallpaper and settings from QSettings.
        """
        last_wallpaper = self.settings.value("last_wallpaper", "")
        mute_state = self.settings.value("mute_state", True, type=bool)
        loop_state = self.settings.value("loop_state", True, type=bool)

        self.mute_checkbox.setChecked(mute_state)
        self.loop_checkbox.setChecked(loop_state)
        global is_muted, is_looping
        is_muted = mute_state
        is_looping = loop_state

        if last_wallpaper and os.path.exists(last_wallpaper):
            for i in range(self.listbox.count()):
                if os.path.join(VIDEO_DIR, self.listbox.item(i).text()) == last_wallpaper:
                    self.listbox.setCurrentRow(i)
                    self.set_wallpaper()
                    break

    def save_settings(self):
        """
        Save current wallpaper and settings to QSettings.
        """
        selected = self.listbox.currentItem()
        if selected:
            self.settings.setValue("last_wallpaper", os.path.join(VIDEO_DIR, selected.text()))
        self.settings.setValue("mute_state", self.mute_checkbox.isChecked())
        self.settings.setValue("loop_state", self.loop_checkbox.isChecked())

    def refresh_list(self):
        """
        Refresh the list of available wallpapers in the listbox.
        """
        self.listbox.clear()
        for file in os.listdir(VIDEO_DIR):
            if file.lower().endswith(('.mp4', '.mkv', '.avi', '.mov', '.webm')):
                self.listbox.addItem(file)
        print("[INFO] Refreshed video list")
        self.status_bar.showMessage("Ready" if not current_process else f"Playing: {self.listbox.currentItem().text() if self.listbox.currentItem() else 'Unknown'}")
        stop_video(is_preview=True)

    def add_video(self):
        """
        Add a new video to the wallpapers directory.
        """
        file_path, _ = QFileDialog.getOpenFileName(self, "Choose a Video", "", "Video Files (*.mp4 *.mkv *.avi *.mov *.webm)")
        if file_path:
            dest = os.path.join(VIDEO_DIR, os.path.basename(file_path))
            if not os.path.exists(dest):
                shutil.copy(file_path, dest)
                print(f"[INFO] Copied video: {file_path} to {dest}")
                QMessageBox.information(self, "Success", f"Added {os.path.basename(file_path)}")
            else:
                print(f"[WARNING] Video already exists: {dest}")
                QMessageBox.warning(self, "Warning", "Video already exists in Wallpapers directory.")
            self.refresh_list()

    def show_preview(self, current, previous):
        """
        Automatically play the selected video in the preview widget.
        """
        stop_video(is_preview=True)
        if current and not self.isHidden():
            video_path = os.path.join(VIDEO_DIR, current.text())
            self.status_bar.showMessage(f"Selected: {current.text()}")
            play_preview_video(video_path, self.preview_widget, mute=True, loop=self.loop_checkbox.isChecked())
        else:
            self.status_bar.showMessage("Ready")

    def set_wallpaper(self):
        """
        Set the selected video as the desktop wallpaper.
        """
        global is_muted, last_mute_state, pending_mute, audio_control_enabled
        selected = self.listbox.currentItem()
        if selected:
            video_path = os.path.join(VIDEO_DIR, selected.text())
            print(f"[INFO] Setting wallpaper: {video_path}")
            should_mute = is_muted or not is_desktop_active()
            if play_video_as_wallpaper(video_path, mute=should_mute, loop=self.loop_checkbox.isChecked()):
                self.status_bar.showMessage(f"Playing: {selected.text()}")
                QMessageBox.information(self, "Success", f"Set {selected.text()} as wallpaper")
                self.save_settings()
            else:
                self.status_bar.showMessage("Error setting wallpaper")
                last_mute_state = None
                pending_mute = None
                audio_control_enabled = True

    def stop_wallpaper(self):
        """
        Stop the current wallpaper and update status.
        """
        global last_mute_state, pending_mute, audio_control_enabled
        stop_video(is_preview=False)
        self.status_bar.showMessage("Ready")
        print("[INFO] Wallpaper stopped")
        QMessageBox.information(self, "Success", "Wallpaper stopped")
        self.save_settings()
        last_mute_state = None
        pending_mute = None
        audio_control_enabled = True

    def toggle_mute(self):
        """
        Toggle mute state for the current wallpaper and preview.
        """
        global is_muted, last_mute_state, pending_mute, audio_control_enabled
        is_muted = self.mute_checkbox.isChecked()
        print(f"[INFO] Mute state changed to: {is_muted}")
        self.save_settings()
        if current_process and audio_control_enabled:
            should_mute = is_muted or not is_desktop_active()
            if should_mute != last_mute_state:
                if send_mpv_command(["set_property", "mute", should_mute]):
                    last_mute_state = should_mute
                    pending_mute = None
                    print(f"[INFO] Audio {'muted' if should_mute else 'unmuted'} via toggle_mute")
                else:
                    pending_mute = should_mute
                    print(f"[WARNING] Failed to toggle audio, will retry in next check")
        if preview_process:
            self.show_preview(self.listbox.currentItem(), None)

    def toggle_loop(self):
        """
        Toggle loop state for the current wallpaper and preview.
        """
        global is_looping
        is_looping = self.loop_checkbox.isChecked()
        print(f"[INFO] Loop state changed to: {is_looping}")
        self.save_settings()
        if current_process:
            selected = self.listbox.currentItem()
            if selected:
                video_path = os.path.join(VIDEO_DIR, selected.text())
                self.set_wallpaper()
        if preview_process:
            self.show_preview(self.listbox.currentItem(), None)

    def check_desktop_state(self):
        """
        Check if desktop is active and adjust wallpaper audio.
        """
        global is_muted, last_mute_state, pending_mute, audio_control_enabled
        if current_process and audio_control_enabled:
            should_mute = is_muted or not is_desktop_active()
            if pending_mute is not None:
                should_mute = pending_mute
            if should_mute != last_mute_state:
                if send_mpv_command(["set_property", "mute", should_mute]):
                    last_mute_state = should_mute
                    pending_mute = None
                    print(f"[INFO] Audio {'muted' if should_mute else 'unmuted'} due to desktop state: {is_desktop_active()}")
                else:
                    pending_mute = should_mute
                    print(f"[WARNING] Failed to toggle audio, will retry in next check")

    def closeEvent(self, event):
        """
        Hide the window instead of closing it, keep wallpaper running.
        """
        global last_mute_state, pending_mute, audio_control_enabled
        self.hide()
        event.ignore()
        print("[INFO] Window minimized to tray")
        if current_process and audio_control_enabled:
            should_mute = is_muted or not is_desktop_active()
            if should_mute != last_mute_state:
                if send_mpv_command(["set_property", "mute", should_mute]):
                    last_mute_state = should_mute
                    pending_mute = None
                    print(f"[INFO] Audio {'muted' if should_mute else 'unmuted'} on minimize")
                else:
                    pending_mute = should_mute
                    print(f"[WARNING] Failed to toggle audio on minimize, will retry in next check")

    def on_tray_icon_activated(self, reason):
        """
        Show the window when the tray icon is clicked.
        """
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.show_normal()

    def show_normal(self):
        """
        Show and activate the window, update audio state.
        """
        global last_mute_state, pending_mute, audio_control_enabled
        self.show()
        self.raise_()
        self.activateWindow()
        print("[INFO] Window restored from tray")
        if current_process and audio_control_enabled:
            should_mute = is_muted or not is_desktop_active()
            if should_mute != last_mute_state:
                if send_mpv_command(["set_property", "mute", should_mute]):
                    last_mute_state = should_mute
                    pending_mute = None
                    print(f"[INFO] Audio {'muted' if should_mute else 'unmuted'} on restore")
                else:
                    pending_mute = should_mute
                    print(f"[WARNING] Failed to toggle audio on restore, will retry in next check")
            self.status_bar.showMessage(f"Playing: {self.listbox.currentItem().text() if self.listbox.currentItem() else 'Unknown'}")

    def exit_app(self):
        """
        Stop the wallpaper and preview, then exit the application.
        """
        global last_mute_state, pending_mute, audio_control_enabled
        stop_video(is_preview=False)
        stop_video(is_preview=True)
        self.tray_icon.hide()
        self.save_settings()
        last_mute_state = None
        pending_mute = None
        audio_control_enabled = True
        QApplication.quit()
        print("[INFO] Application exited")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setFont(QFont("Roboto", 10))
    window = LiveWallpaperApp()
    window.show()
    sys.exit(app.exec())