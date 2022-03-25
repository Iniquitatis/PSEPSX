import importlib
import json
import re
import shutil
import sys
from collections import defaultdict, namedtuple
from configparser import ConfigParser
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

def frozen_path(path):
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / path
    else:
        return Path(path)

def find_game_dir():
    import winreg

    for reg_path in ["SOFTWARE\\Valve\\Steam", "SOFTWARE\\Wow6432Node\\Valve\\Steam"]:
        try:
            key = winreg.OpenKeyEx(winreg.HKEY_CURRENT_USER, reg_path)
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
        self.status_bar().add_widget(self._progress_label, 1)

    def close_event(self, event):
        self._mod_table.save()
        event.accept()

    def _on_open_button_clicked(self):
        dialog = QFileDialog(self)
        dialog.set_file_mode(QFileDialog.Directory)

        if dialog.exec():
            self._path_editor.set_text(str(Path(dialog.selected_files()[0])))

    def _on_mod_table_mod_selected(self, mod):
        self._description_box.set_text(mod.long_description)

    def _on_build_button_clicked(self):
        self._build_button.set_enabled(False)

        self._builder = BuilderThread(
            game_kpf_path = self._game_dir_editor.path() / "PowerslaveEX.kpf",
            patch_dir = frozen_path("Patches"),
            data_dir = frozen_path("Data"),
            temp_dir = frozen_path("Temp"),
            output_dir = self._output_dir_editor.path(),
            build_params = self._mod_table.build_params()
        )
        self._builder.statusUpdate.connect(self._on_status_update)
        self._builder.finished.connect(self._on_build_finished)
        self._builder.start()

    def _on_status_update(self, text):
        print(text)
        self._progress_label.set_text(text)

    def _on_build_finished(self):
        self._build_button.set_enabled(True)

        self._progress_label.set_text("Ready")

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
    Mod = namedtuple("Mod", "id name category short_description long_description definition script", defaults = [""] * 7)
    BuildParam = namedtuple("BuildParam", "enabled definition script_name")

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

                mod = self.Mod(**mod_data)
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
        return [
            self.BuildParam(
                self.item(i, 0).check_state() == Qt.Checked,
                user_data.definition,
                user_data.script
            )
            for i in range(self.row_count())
            if (user_data := self.item(i, 0).data(Qt.UserRole)) != "CATEGORY"
        ]

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

            for i in range(self.row_count()):
                item = self.item(i, 0)
                user_data = item.data(Qt.UserRole)
                enabled = item.check_state() == Qt.Checked

                if user_data != "CATEGORY":
                    config.set("mods", user_data.id, str(enabled).lower())

            config.write(config_file)

    def _on_cell_changed(self, row, column):
        user_data = self.item(row, 0).data(Qt.UserRole)

        if user_data != "CATEGORY":
            self.modSelected.emit(user_data)

#===============================================================================

class BuilderThread(QThread):
    statusUpdate = Signal(Path)

    def __init__(self, game_kpf_path, patch_dir, data_dir, temp_dir, output_dir, build_params):
        super().__init__()
        self._game_kpf_path = game_kpf_path
        self._patch_dir = patch_dir
        self._data_dir = data_dir
        self._temp_dir = temp_dir
        self._output_dir = output_dir
        self._build_params = build_params

    def run(self):
        self._game_kpf = ZipFile(self._game_kpf_path)

        self._output_dir.mkdir(parents = True, exist_ok = True)
        self._temp_dir.mkdir(parents = True, exist_ok = True)

        self._make_mod()

        shutil.rmtree(self._temp_dir)

        self._game_kpf.close()

    def _make_mod(self):
        self._patch_files()
        self._copy_files()
        self._preprocess_files()
        self._apply_scripts()

        output_path = self._output_dir / f"PSEPSX.kpf"
        output_path.unlink(missing_ok = True)

        self.statusUpdate.emit(f"Packing {output_path}...")
        make_archive(output_path, self._temp_dir)

    def _patch_files(self):
        for diff_path in self._patch_dir.glob("*.diff"):
            self.statusUpdate.emit(f"Applying {diff_path}...")
            self._apply_patch(diff_path)

    def _copy_files(self):
        for file_path in filter(Path.is_file, self._data_dir.rglob("*")):
            self.statusUpdate.emit(f"Copying {file_path}...")
            rel_path = file_path.relative_to(self._data_dir)
            result_path = self._temp_dir / rel_path
            result_path.parent.mkdir(parents = True, exist_ok = True)
            shutil.copy2(file_path, result_path)

    def _preprocess_files(self):
        for text_file_path in self._temp_dir.rglob("*.txt"):
            self.statusUpdate.emit(f"Preprocessing {text_file_path}...")
            self._preprocess(text_file_path)

    def _apply_scripts(self):
        def kpf_loader(src_path, dst_path):
            dst_path.parent.mkdir(parents = True, exist_ok = True)
            extract_file(self._game_kpf, src_path, dst_path)

        for bp in self._build_params:
            if not bp.enabled or bp.script_name == "":
                continue

            self.statusUpdate.emit(f"Applying script {bp.script_name}...")
            script = importlib.import_module(f"Scripts.{bp.script_name}")
            script.apply(kpf_loader, self._temp_dir)

    def _apply_patch(self, diff_path):
        patch_set = patch.fromfile(diff_path)

        for item in patch_set.items:
            src_path = item.source.decode("utf-8")
            dst_path = self._temp_dir / Path(item.target.decode("utf-8"))
            dst_path.parent.mkdir(parents = True, exist_ok = True)

            if src_path == "dev/null":
                self.statusUpdate.emit(f"Creating {dst_path}...")

                with open(dst_path, "w") as dst_file:
                    for hunk in item.hunks:
                        for line in hunk.text:
                            line = line.decode("utf-8").strip("\n\r")[1:]
                            dst_file.write(f"{line}\n")

            elif dst_path == "dev/null":
                self.statusUpdate.emit(f"Removing {dst_path}...")

                if dst_path.exists():
                    dst_path.unlink()

            elif exists_in_archive(self._game_kpf, src_path):
                self.statusUpdate.emit(f"Extracting {src_path}...")
                extract_file(self._game_kpf, src_path, dst_path)

        patch_set.apply(root = self._temp_dir)

    def _preprocess(self, path):
        with open(path, "rt") as file:
            text = file.read()

            for bp in self._build_params:
                if bp.definition == "":
                    continue

                text = re.sub(bp.definition, str(1 if bp.enabled else 0), text)

        with open(path, "wt") as file:
            file.write(text)

#===============================================================================

if __name__ == "__main__":
    app = Application(sys.argv)
    sys.exit(app.exec())
