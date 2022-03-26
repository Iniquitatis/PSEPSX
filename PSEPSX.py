import importlib
import json
import re
import shutil
import sys
import zlib
from collections import defaultdict
from configparser import ConfigParser
from dataclasses import dataclass
from pathlib import Path
from zipfile import ZipFile

import patch

from PySide6.QtCore import (
    Qt,
    Signal,
    QThread
)
from PySide6.QtGui import (
    QFont,
    QIcon
)
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget
)
from __feature__ import snake_case

#===============================================================================

APP_VERSION = (1, 1, 0)
GAME_KPF_NAME = "PowerslaveEX.kpf"
GAME_KPF_CRC32 = "BE91B2AF"
MOD_KPF_NAME = "PSEPSX.kpf"

#===============================================================================

def frozen_path(path):
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / path
    else:
        return Path(path)

def find_game_dir():
    import winreg

    for hkey in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
        for reg_path in ("SOFTWARE\\Valve\\Steam", "SOFTWARE\\Wow6432Node\\Valve\\Steam"):
            try:
                key = winreg.OpenKeyEx(hkey, reg_path)
                steam_dir = Path(winreg.QueryValueEx(key, "SteamPath")[0])

                if (game_dir := steam_dir / "steamapps/common/PowerSlave Exhumed").is_dir():
                    return game_dir.resolve()

            except OSError:
                continue

    return Path()

def find_mods_dir():
    if (game_dir := find_game_dir()).is_dir():
        return (game_dir / "mods").resolve()
    else:
        return Path()

def make_archive(result_path, root_dir):
    shutil.make_archive(result_path.with_suffix(""), "zip", root_dir)
    result_path.with_suffix(".zip").rename(result_path)

def exists_in_archive(archive, src_path):
    return src_path in archive.namelist()

def extract_file(archive, src_path, dst_path):
    with archive.open(src_path) as src_file, open(dst_path, "wb") as dst_file:
        shutil.copyfileobj(src_file, dst_file)

#===============================================================================

@dataclass
class Mod:
    id: str = ""
    name: str = ""
    category: str = ""
    short_description: str = ""
    long_description: str = ""
    definition: str = ""
    script: str = ""

@dataclass
class BuildParam:
    enabled: bool = False
    definition: str = ""
    script_name: str = ""

#===============================================================================

class Application(QApplication):
    def __init__(self, args):
        super().__init__(args)
        self.set_window_icon(QIcon(str(frozen_path("Resources/Icon.png"))))

        self._window = MainWindow()
        self._window.show()

#===============================================================================

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.set_window_title("PSEPSX Builder")
        self.resize(640, 480)

        self._game_dir_editor = PathEdit("Game Directory", QFileDialog.Directory, str(find_game_dir()))
        self._output_dir_editor = PathEdit("Output Directory", QFileDialog.Directory, str(find_mods_dir()))

        self._mod_table = ModTableWidget()
        self._mod_table.modSelected.connect(self._on_mod_table_mod_selected)
        self._mod_table.load()

        self._description_box = QTextEdit()
        self._description_box.set_maximum_size(self._description_box.maximum_width(), 120)
        self._description_box.set_read_only(True)
        self._description_box.set_text("<i>Description will be shown here.</i>")

        self._build_button = QPushButton("Build")
        self._build_button.clicked.connect(self._on_build_button_clicked)

        self._layout = QVBoxLayout()
        self._layout.set_contents_margins(10, 10, 10, 10)
        self._layout.add_widget(self._game_dir_editor)
        self._layout.add_widget(self._output_dir_editor)
        self._layout.add_widget(self._mod_table)
        self._layout.add_widget(self._description_box)
        self._layout.add_widget(self._build_button)

        self._central = QWidget()
        self._central.set_layout(self._layout)
        self.set_central_widget(self._central)

        self._progress_label = QLabel("Ready")

        self._progress_bar = QProgressBar()
        self._progress_bar.set_alignment(Qt.AlignCenter)
        self._progress_bar.set_minimum(0)
        self._progress_bar.set_maximum(2 ** 30)
        self._progress_bar.hide()

        self._version_label = QLabel("v" + ".".join(str(x) for x in APP_VERSION))

        status_bar = self.status_bar()
        status_bar.set_style_sheet("QStatusBar::item { border: none; }")
        status_bar.add_widget(self._progress_label, 1)
        status_bar.add_permanent_widget(self._progress_bar)
        status_bar.add_permanent_widget(self._version_label)

    def close_event(self, event):
        self._mod_table.save()
        event.accept()

    def _validate_game_kpf(self):
        self._progress_label.set_text("Validating game data archive...")
        self._progress_bar.show()

        self._validator = FileValidatorThread(self._game_dir_editor.path() / GAME_KPF_NAME, GAME_KPF_CRC32)
        self._validator.progressed.connect(self._on_validation_progressed)
        self._validator.succeed.connect(self._on_validation_succeed)
        self._validator.failed.connect(self._on_validation_failed)
        self._validator.start()

    def _build_mod(self):
        self._progress_label.set_text("Building mod...")

        self._builder = BuilderThread(
            game_kpf_path = self._game_dir_editor.path() / GAME_KPF_NAME,
            patch_dir = frozen_path("Patches"),
            data_dir = frozen_path("Data"),
            build_dir = frozen_path("Build"),
            output_path = self._output_dir_editor.path() / MOD_KPF_NAME,
            build_params = self._mod_table.build_params()
        )
        self._builder.statusUpdated.connect(self._on_build_status_updated)
        self._builder.finished.connect(self._on_build_finished)
        self._builder.start()

    def _show_message_box(self, title, icon, text):
        msg_box = QMessageBox(self)
        msg_box.set_icon(icon)
        msg_box.set_standard_buttons(QMessageBox.Ok)
        msg_box.set_text(text)
        msg_box.set_window_title(title)
        msg_box.exec()

    def _on_mod_table_mod_selected(self, mod):
        self._description_box.set_text(mod.long_description)

    def _on_build_button_clicked(self):
        if not (self._game_dir_editor.path() / GAME_KPF_NAME).is_file():
            self._show_message_box(
                "Not Found",
                QMessageBox.Warning,
                f"{GAME_KPF_NAME} has not been found in the selected directory."
            )

            return

        self._build_button.set_enabled(False)

        self._validate_game_kpf()

    def _on_validation_progressed(self, pos, size):
        self._progress_bar.set_value(pos)
        self._progress_bar.set_maximum(size)

    def _on_validation_succeed(self, crc):
        self._progress_bar.hide()

        self._build_mod()

    def _on_validation_failed(self, crc):
        self._build_button.set_enabled(True)
        self._progress_label.set_text("Ready")
        self._progress_bar.hide()

        self._show_message_box(
            "Validation Failed",
            QMessageBox.Critical,
            f"Game data archive CRC-32 mismatch.<br><br>Calculated: <b>{crc}</b>, expected: <b>{GAME_KPF_CRC32}</b>."
        )

    def _on_build_status_updated(self, text):
        print(text)
        self._progress_label.set_text(text)

    def _on_build_finished(self):
        self._build_button.set_enabled(True)
        self._progress_label.set_text("Ready")

        self._show_message_box(
            "Build Finished",
            QMessageBox.Information,
            "Done."
        )

#===============================================================================

class PathEdit(QWidget):
    def __init__(self, name, mode, default = "", parent = None):
        super().__init__(parent)
        self._mode = mode

        self._editor = QLineEdit()
        self._editor.set_text(default)

        self._label = QLabel(name)
        self._label.set_minimum_size(120, 0)

        self._open_button = QPushButton("...")
        self._open_button.set_maximum_size(25, self._open_button.maximum_height())
        self._open_button.clicked.connect(self._on_open_button_clicked)

        self._layout = QHBoxLayout()
        self._layout.set_contents_margins(0, 0, 0, 0)
        self._layout.add_widget(self._label)
        self._layout.add_widget(self._editor)
        self._layout.add_widget(self._open_button)
        self.set_layout(self._layout)

    def path(self):
        return Path(self._editor.text())

    def _on_open_button_clicked(self):
        path = Path(self._editor.text())
        start_dir = path.parent if path.is_file() else path if path.is_dir() else ""

        dialog = QFileDialog(self)
        dialog.set_directory(str(start_dir))
        dialog.set_file_mode(self._mode)

        if dialog.exec():
            self._editor.set_text(str(Path(dialog.selected_files()[0])))

#===============================================================================

class ModTableWidget(QTableWidget):
    modSelected = Signal(Mod)

    def __init__(self, parent = None):
        super().__init__(parent)
        self.set_column_count(1)
        self.set_show_grid(False)
        self.horizontal_header().hide()
        self.horizontal_header().set_stretch_last_section(True)
        self.vertical_header().hide()
        self.currentCellChanged.connect(self._on_cell_changed)

    def load(self):
        config = self._load_config()

        with open(frozen_path("Resources/Mods.json"), "r") as json_file:
            categories = defaultdict(list)

            for mod_data in json.load(json_file):
                description = mod_data.pop("description", "")

                if isinstance(description, list):
                    mod_data["short_description"] = description[0].removesuffix("<br>")
                    mod_data["long_description"] = "".join(description)
                else:
                    mod_data["short_description"] = description
                    mod_data["long_description"] = description

                mod = Mod(**mod_data)
                categories[mod.category].append(mod)

            category_font = QFont()
            category_font.set_bold(True)

            for category_name, category in categories.items():
                row = self._append_row()

                item = QTableWidgetItem(category_name)
                item.set_data(Qt.UserRole, "CATEGORY")
                item.set_flags(item.flags() & ~(Qt.ItemIsEditable | Qt.ItemIsSelectable))
                item.set_font(category_font)
                self.set_item(row, 0, item)

                for mod in category:
                    row = self._append_row()

                    item = QTableWidgetItem(mod.name)
                    item.set_check_state(Qt.Checked if config.get(mod.id, True) else Qt.Unchecked)
                    item.set_data(Qt.UserRole, mod)
                    item.set_flags(item.flags() & ~(Qt.ItemIsEditable | Qt.ItemIsSelectable))
                    item.set_tool_tip(mod.short_description)
                    self.set_item(row, 0, item)

    def save(self):
        self._save_config()

    def build_params(self):
        return [BuildParam(enabled, mod.definition, mod.script) for enabled, mod in self._mods()]

    def _append_row(self):
        self.insert_row(self.row_count())
        return self.row_count() - 1

    def _load_config(self):
        if not Path("Settings.ini").exists():
            return dict()

        with open("Settings.ini", "r") as config_file:
            config = ConfigParser()
            config.read_file(config_file)

            if not config.has_section("mods"):
                return dict()

            return {key: config.getboolean("mods", key) for key in config.options("mods")}

    def _save_config(self):
        with open("Settings.ini", "w") as config_file:
            config = ConfigParser()
            config.add_section("mods")

            for enabled, mod in self._mods():
                config.set("mods", mod.id, str(enabled).lower())

            config.write(config_file)

    def _mods(self):
        return (
            (item.check_state() == Qt.Checked, item.data(Qt.UserRole))
            for i in range(self.row_count())
            if (item := self.item(i, 0)).data(Qt.UserRole) != "CATEGORY"
        )

    def _on_cell_changed(self, row, column):
        user_data = self.item(row, 0).data(Qt.UserRole)

        if user_data != "CATEGORY":
            self.modSelected.emit(user_data)

#===============================================================================

class FileValidatorThread(QThread):
    progressed = Signal(int, int)
    succeed = Signal(str)
    failed = Signal(str)

    def __init__(self, path, expected_crc):
        super().__init__()
        self._path = path
        self._expected_crc = expected_crc

    def run(self):
        crc, pos, size = 0, 0, self._path.stat().st_size

        with open(self._path, "rb") as file:
            while chunk := file.read(65536):
                crc = zlib.crc32(chunk, crc)
                pos += len(chunk)

                self.progressed.emit(pos, size)

        if (crc_str := f"{crc:08X}") == self._expected_crc:
            self.succeed.emit(crc_str)
        else:
            self.failed.emit(crc_str)

#===============================================================================

class BuilderThread(QThread):
    statusUpdated = Signal(Path)

    def __init__(self, game_kpf_path, patch_dir, data_dir, build_dir, output_path, build_params):
        super().__init__()
        self._game_kpf_path = game_kpf_path
        self._patch_dir = patch_dir
        self._data_dir = data_dir
        self._build_dir = build_dir
        self._output_path = output_path
        self._build_params = build_params

    def run(self):
        with ZipFile(self._game_kpf_path) as self._game_kpf:
            self._build_dir.mkdir(parents = True, exist_ok = True)

            self._output_path.parent.mkdir(parents = True, exist_ok = True)
            self._output_path.unlink(missing_ok = True)

            self._patch_files()
            self._copy_files()
            self._preprocess_files()
            self._apply_scripts()
            self._pack_kpf()

            shutil.rmtree(self._build_dir)

    def _patch_files(self):
        for diff_path in self._patch_dir.glob("*.diff"):
            self._apply_patch(diff_path)

    def _copy_files(self):
        for file_path in filter(Path.is_file, self._data_dir.rglob("*")):
            self._copy_file(file_path)

    def _preprocess_files(self):
        for text_file_path in self._build_dir.rglob("*.txt"):
            self._preprocess(text_file_path)

    def _apply_scripts(self):
        for bp in filter(lambda x: x.enabled and x.script_name != "", self._build_params):
            self._apply_script(bp.script_name)

    def _pack_kpf(self):
        self.statusUpdated.emit(f"Packing {self._output_path}...")

        make_archive(self._output_path, self._build_dir)

    def _apply_patch(self, diff_path):
        self.statusUpdated.emit(f"Applying {diff_path}...")

        patch_set = patch.fromfile(diff_path)

        for item in patch_set.items:
            src_path = item.source.decode("utf-8")
            dst_path = self._build_dir / item.target.decode("utf-8")

            if src_path == "dev/null":
                self.statusUpdated.emit(f"Creating {dst_path}...")

                dst_path.parent.mkdir(parents = True, exist_ok = True)

                with open(dst_path, "w") as dst_file:
                    for hunk in item.hunks:
                        for line in hunk.text:
                            line = line.decode("utf-8").strip("\n\r")[1:]
                            dst_file.write(f"{line}\n")

            elif dst_path == "dev/null":
                self.statusUpdated.emit(f"Removing {dst_path}...")

                dst_path.unlink(missing_ok = True)

            elif exists_in_archive(self._game_kpf, src_path):
                self.statusUpdated.emit(f"Extracting {src_path}...")

                dst_path.parent.mkdir(parents = True, exist_ok = True)

                extract_file(self._game_kpf, src_path, dst_path)

        patch_set.apply(root = self._build_dir)

    def _copy_file(self, path):
        self.statusUpdated.emit(f"Copying {path}...")

        rel_path = path.relative_to(self._data_dir)

        result_path = self._build_dir / rel_path
        result_path.parent.mkdir(parents = True, exist_ok = True)

        shutil.copy2(path, result_path)

    def _preprocess(self, path):
        self.statusUpdated.emit(f"Preprocessing {path}...")

        with open(path, "rt") as file:
            text = file.read()

        for bp in filter(lambda x: x.definition != "", self._build_params):
            text = re.sub(bp.definition, str(1 if bp.enabled else 0), text)

        with open(path, "wt") as file:
            file.write(text)

    def _apply_script(self, script_name):
        self.statusUpdated.emit(f"Applying script {script_name}...")

        script = importlib.import_module(f"Scripts.{script_name}")
        script.apply(self._game_kpf.open, self._build_dir)

#===============================================================================

if __name__ == "__main__":
    app = Application(sys.argv)
    sys.exit(app.exec())
