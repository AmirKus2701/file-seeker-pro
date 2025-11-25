import sys
import os
import string
import subprocess
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLineEdit, QLabel, QListWidget, QCheckBox, 
                             QPushButton, QProgressBar, QMenu, QFileDialog, QGridLayout, 
                             QFrame, QComboBox, QMessageBox)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QDir, QPoint, QTimer
from PyQt6.QtGui import QPalette, QColor, QAction

# --- ПОТОК ПОИСКА (Обновлены сообщения о статусе) ---
class SearchThread(QThread):
    update_results = pyqtSignal(list)
    update_status = pyqtSignal(str) 
    finished = pyqtSignal()

    def __init__(self, search_term, extensions, root_dir):
        super().__init__()
        self.search_term = search_term.lower()
        self.extensions = extensions
        self.root_dir = root_dir

    def run(self):
        results = []
        processed_count = 0
        
        # Проверка, существует ли диск вообще
        if not os.path.exists(self.root_dir):
            self.update_status.emit(f"❌ Ошибка: Путь {self.root_dir} не найден!") # <-- RU
            self.finished.emit()
            return

        for root, dirs, files in os.walk(self.root_dir):
            if self.isInterruptionRequested():
                return
            
            # Пропускаем системные/скрытые папки
            dirs[:] = [d for d in dirs if not d.startswith('.') and '$' not in d]

            for file in files:
                if self.isInterruptionRequested():
                    return
                
                processed_count += 1
                if processed_count % 200 == 0: 
                    self.update_status.emit(f"Сканирование {self.root_dir}... ({processed_count} файлов)") # <-- RU

                file_lower = file.lower()
                
                match_name = self.search_term in file_lower
                match_ext = True
                if self.extensions:
                    match_ext = any(file_lower.endswith(ext) for ext in self.extensions)
                
                if match_name and match_ext:
                    full_path = os.path.join(root, file)
                    results.append(f"{file} | {full_path}")

        self.update_results.emit(results)
        self.update_status.emit(f"✅ Найдено {len(results)} файлов в {self.root_dir}") # <-- RU
        self.finished.emit()

# --- ОСНОВНОЕ ОКНО (Переведен весь интерфейс) ---
class FileSearcherApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Профессиональный Поиск Файлов v5.0") # <-- RU
        self.resize(1000, 750)

        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.interval = 500
        self.search_timer.timeout.connect(self.start_search_real)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout()

        # Header
        header = QLabel("🔎 Универсальный Поиск Файлов") # <-- RU
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setStyleSheet("font-size: 24px; font-weight: bold; color: #4CAF50; margin: 10px;")
        main_layout.addWidget(header)

        # БЛОК ВЫБОРА ДИСКА
        drive_layout = QHBoxLayout()
        
        drive_label = QLabel("Искать в:") # <-- RU
        drive_label.setStyleSheet("color: #ddd; font-weight: bold;")
        drive_layout.addWidget(drive_label)

        self.drive_combo = QComboBox()
        self.drive_combo.setStyleSheet("""
            QComboBox { background-color: #333; color: white; padding: 5px; border: 1px solid #555; }
            QComboBox QAbstractItemView { background-color: #333; color: white; selection-background-color: #4CAF50; }
        """)
        self.drive_combo.currentIndexChanged.connect(self.on_drive_changed)
        drive_layout.addWidget(self.drive_combo)

        # Кнопка Обновить диски
        refresh_btn = QPushButton("🔄")
        refresh_btn.setToolTip("Обновить список дисков") # <-- RU
        refresh_btn.setFixedWidth(40)
        refresh_btn.clicked.connect(self.populate_drives)
        refresh_btn.setStyleSheet("background-color: #444; color: white; border: none; padding: 5px;")
        drive_layout.addWidget(refresh_btn)

        # Кнопка выбора конкретной папки
        browse_btn = QPushButton("📂 Выбрать Папку...") # <-- RU
        browse_btn.clicked.connect(self.select_custom_folder)
        browse_btn.setStyleSheet("background-color: #2196F3; color: white; border: none; padding: 5px 15px; border-radius: 4px;")
        drive_layout.addWidget(browse_btn)

        main_layout.addLayout(drive_layout)
        # -----------------------------------

        # Search input
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Введите часть имени файла...") # <-- RU
        self.search_edit.textChanged.connect(self.restart_timer)
        self.search_edit.setStyleSheet("""
            QLineEdit { 
                background-color: #333; color: #fff; 
                border: 2px solid #555; border-radius: 6px; 
                padding: 10px; font-size: 16px; margin-top: 10px;
            }
            QLineEdit:focus { border: 2px solid #4CAF50; }
        """)
        main_layout.addWidget(self.search_edit)

        # Filters Grid (Переведены названия категорий)
        filter_group = QFrame()
        filter_group.setStyleSheet("background-color: #2a2a2a; border-radius: 8px; padding: 5px;")
        filter_layout = QGridLayout()
        
        # Переведенный словарь категорий
        self.categories = {
            "📄 Документы (Word, PDF)": ['.docx', '.doc', '.pdf', '.txt', '.rtf', '.odt'], # <-- RU
            "📊 Таблицы и Данные": ['.xlsx', '.xls', '.csv', '.pbix', '.pbit', '.xml'], # <-- RU
            "📢 Презентации": ['.pptx', '.ppt', '.key', '.odp'], # <-- RU
            "📦 Архивы": ['.zip', '.rar', '.7z', '.tar', '.gz', '.iso'], # <-- RU
            "🖼️ Изображения": ['.jpg', '.jpeg', '.png', '.webp', '.svg', '.psd', '.ai'], # <-- RU
            "🎬 Видео / Аудио": ['.mp4', '.avi', '.mov', '.mp3', '.wav', '.mkv'], # <-- RU
            "🐍 Код и Веб": ['.py', '.js', '.html', '.css', '.json', '.sql', '.cpp'] # <-- RU
        }

        self.ext_checkboxes = {}
        row, col = 0, 0
        max_cols = 4
        
        for name, exts in self.categories.items():
            cb = QCheckBox(name)
            cb.setStyleSheet("font-weight: bold; color: #ddd; padding: 5px;")
            cb.stateChanged.connect(self.start_search_real)
            self.ext_checkboxes[name] = {'cb': cb, 'exts': exts}
            filter_layout.addWidget(cb, row, col)
            col += 1
            if col >= max_cols:
                col = 0
                row += 1

        filter_group.setLayout(filter_layout)
        main_layout.addWidget(filter_group)

        # Results list
        self.results_list = QListWidget()
        self.results_list.setStyleSheet("""
            QListWidget { background-color: #2b2b2b; color: #eee; border: none; font-size: 14px; }
            QListWidget::item { padding: 8px; border-bottom: 1px solid #333; }
            QListWidget::item:selected { background-color: #4CAF50; color: white; }
        """)
        self.results_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.results_list.customContextMenuRequested.connect(self.show_context_menu)
        main_layout.addWidget(self.results_list)

        # Status Bar
        self.status_label = QLabel("Готов к работе") # <-- RU
        self.status_label.setStyleSheet("color: #aaa; font-family: monospace;")
        main_layout.addWidget(self.status_label)

        central_widget.setLayout(main_layout)
        self.apply_dark_theme()
        
        self.root_dir = "C:\\"
        self.populate_drives()
        
        self.search_thread = None

    def apply_dark_theme(self):
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(45, 45, 45))
        palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.Base, QColor(30, 30, 30))
        palette.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.Button, QColor(45, 45, 45))
        palette.setColor(QPalette.ColorRole.ButtonText, Qt.GlobalColor.white)
        self.setPalette(palette)

    # --- ЛОГИКА ДИСКОВ ---
    def populate_drives(self):
        """Сканирует систему на наличие дисков"""
        self.drive_combo.blockSignals(True)
        self.drive_combo.clear()
        
        drives = []
        if os.name == 'nt':
            drives = [f"{d}:\\" for d in string.ascii_uppercase if os.path.exists(f"{d}:\\")]
        else:
            drives = ["/"]

        self.drive_combo.addItems(drives)
        
        index = self.drive_combo.findText(self.root_dir)
        if index >= 0:
            self.drive_combo.setCurrentIndex(index)
        
        self.drive_combo.blockSignals(False)

    def on_drive_changed(self, index):
        """Когда пользователь меняет диск в списке"""
        self.root_dir = self.drive_combo.currentText()
        self.start_search_real()

    def select_custom_folder(self):
        """Если нужна конкретная папка, а не весь диск"""
        dir = QFileDialog.getExistingDirectory(self, "Выбрать Корневую Папку", self.root_dir) # <-- RU
        if dir:
            dir = os.path.normpath(dir)
            self.root_dir = dir
            
            self.drive_combo.blockSignals(True)
            # Если папка уже есть в списке, не добавляем
            if self.drive_combo.findText(dir) == -1:
                self.drive_combo.addItem(dir)
            
            self.drive_combo.setCurrentIndex(self.drive_combo.findText(dir))
            self.drive_combo.blockSignals(False)
            
            self.start_search_real()
    # -----------------------------

    def restart_timer(self):
        self.search_timer.start()

    def start_search_real(self):
        if self.search_thread and self.search_thread.isRunning():
            self.search_thread.requestInterruption()
            self.search_thread.wait()

        search_term = self.search_edit.text()
        
        active_extensions = []
        for key, value in self.ext_checkboxes.items():
            if value['cb'].isChecked():
                active_extensions.extend(value['exts'])

        if not search_term and not active_extensions:
            self.results_list.clear()
            self.status_label.setText("Готов к работе") # <-- RU
            return

        self.results_list.clear()
        self.status_label.setText(f"🚀 Идет поиск в {self.root_dir}...") # <-- RU

        self.search_thread = SearchThread(search_term, active_extensions, self.root_dir)
        self.search_thread.update_results.connect(self.update_results_list)
        self.search_thread.update_status.connect(self.status_label.setText)
        self.search_thread.start()

    def update_results_list(self, results):
        self.results_list.clear()
        self.results_list.addItems(results)

    def show_context_menu(self, position: QPoint):
        indexes = self.results_list.selectedIndexes()
        if indexes:
            item = self.results_list.itemFromIndex(indexes[0])
            if item:
                text = item.text()
                if ' | ' in text:
                    full_path = text.split(' | ')[-1]
                    menu = QMenu()
                    open_action = menu.addAction("📂 Открыть в Проводнике") # <-- RU
                    open_action.triggered.connect(lambda: self.open_in_explorer(full_path))
                    menu.exec(self.results_list.mapToGlobal(position))

    def open_in_explorer(self, full_path):
        full_path = os.path.normpath(full_path)
        if not os.path.exists(full_path):
            return
        if os.name == 'nt':
            subprocess.Popen(['explorer', '/select,', full_path])
        elif sys.platform == 'darwin':
            subprocess.Popen(['open', '-R', full_path])
        else:
            dir_path = os.path.dirname(full_path)
            subprocess.Popen(['xdg-open', dir_path])

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = FileSearcherApp()
    window.show()
    sys.exit(app.exec())