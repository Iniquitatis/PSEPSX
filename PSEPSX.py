import re
import shutil
import sys
from pathlib import Path
from zipfile import ZipFile

import patch

from PySide6.QtCore import (
    Qt,
    Signal,
    QThread
)
from PySide6.QtGui import (
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

MODS = (
    ("PSPSX_MAPS"               , "Maps"                   , "Replace vanilla maps by the PSX ones."),
    ("PSPSX_AMMO_COUNTS"        , "Ammo Counts"            , "Change the ammo count for some weapons."),
    ("PSPSX_M60_FIRE_TIMINGS"   , "M-60 Fire Timings"      , "Remove the delay after every third shot when firing the M-60."),
    ("PSPSX_EXPLOSION_SOUND"    , "Explosion Sound"        , "Restore a beefier explosion sound."),
    ("PSPSX_FLAMETHROWER_FLAME" , "Flamethrower Flame"     , "Disable fading of the flamethrower flame."),
    ("PSPSX_COBRA_STAFF"        , "Cobra Staff Animation"  , "Replace Cobra Staff animation by the PSX one."),
    ("PSPSX_MANACLE_BEHAVIOR"   , "Sacred Manacle Behavior", "Restore the Sacred Manacle lightning bolt behavior."),
    ("PSPSX_MANACLE_SOUND"      , "Sacred Manacle Sound"   , "Change the Sacred Manacle charging sound."),
    ("PSPSX_TELEPATHIC_RAMSES"  , "Telepathic Ramses"      , "Disable any mouth movement while Ramses speaks."),
    ("PSPSX_SCORPIONS"          , "Remove Spiders"         , "Replace red spiders by the blue scorpions."),
    ("PSPSX_ANUBIS_DEATH"       , "Extreme Anubis Death"   , "Replace Anubis death animation by the gibbing animation."),
    ("PSPSX_MUMMY_DEATH"        , "Extreme Mummy Death"    , "Replace Mummy death animation by the gibbing animation."),
    ("PSPSX_MANTIS_ATTACK"      , "Mantis Attack"          , "Change Mantis' attack so that it shoots three fireballs simultaneously instead of sequentially."),
    ("PSPSX_MANTIS_DECAPITATION", "Mantis Decapitation"    , "Replace Mantis' death by a decapitation."),
    ("PSPSX_ORB_SPAWN"          , "Delayed Orb Spawning"   , "Delay the orb spawning from the destroyed vases."),
)

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

        self._game_dir_editor, self._game_dir_layout = self._create_path_editor("Game Directory", QFileDialog.Directory, str(find_game_dir()))
        self._output_dir_editor, self._output_dir_layout = self._create_path_editor("Output Directory", QFileDialog.Directory, str(find_mods_dir()))

        self._mod_table = QTableWidget(len(MODS), 2)
        self._mod_table.set_column_hidden(0, True)
        self._mod_table.set_show_grid(False)
        self._mod_table.horizontal_header().hide()
        self._mod_table.horizontal_header().set_stretch_last_section(True)
        self._mod_table.vertical_header().hide()

        for i, (id, name, description) in enumerate(MODS):
            self._mod_table.set_item(i, 0, QTableWidgetItem(id))

            item = QTableWidgetItem(name)
            item.set_check_state(Qt.Checked)
            item.set_flags(item.flags() & ~(Qt.ItemIsEditable | Qt.ItemIsSelectable))
            item.set_tool_tip(description)
            self._mod_table.set_item(i, 1, item)

        self._build_button = QPushButton("Build")
        self._build_button.clicked.connect(self._on_build_button_clicked)

        self._layout = QVBoxLayout()
        self._layout.set_contents_margins(10, 10, 10, 10)
        self._layout.add_layout(self._game_dir_layout)
        self._layout.add_layout(self._output_dir_layout)
        self._layout.add_widget(self._mod_table)
        self._layout.add_widget(self._build_button)

        self._central = QWidget()
        self._central.set_layout(self._layout)
        self.set_central_widget(self._central)

        self._progress_label = QLabel("Ready")
        self.status_bar().add_widget(self._progress_label, 1)

    def _create_path_editor(self, name, mode, default = ""):
        editor = QLineEdit()
        editor.set_text(default)

        def on_open_button_clicked():
            path = Path(editor.text())
            start_dir = path.parent if path.is_file() else path if path.is_dir() else ""

            dialog = QFileDialog(self)
            dialog.set_directory(str(start_dir))
            dialog.set_file_mode(mode)

            if dialog.exec():
                editor.set_text(str(Path(dialog.selected_files()[0])))

        label = QLabel(name)
        label.set_minimum_size(120, 0)

        open_button = QPushButton("...")
        open_button.set_maximum_size(25, open_button.maximum_height())
        open_button.clicked.connect(on_open_button_clicked)

        layout = QHBoxLayout()
        layout.add_widget(label)
        layout.add_widget(editor)
        layout.add_widget(open_button)

        return editor, layout

    def _on_open_button_clicked(self):
        dialog = QFileDialog(self)
        dialog.set_file_mode(QFileDialog.Directory)

        if dialog.exec():
            self._path_editor.set_text(str(Path(dialog.selected_files()[0])))

    def _on_build_button_clicked(self):
        self._build_button.set_enabled(False)

        mod_table = self._mod_table
        get_cell = mod_table.item
        definitions = [(get_cell(i, 0).text(), get_cell(i, 1).check_state() == Qt.Checked) for i in range(mod_table.row_count())]

        self._builder = BuilderThread(
            game_kpf_path = Path(self._game_dir_editor.text()) / "PowerslaveEX.kpf",
            patch_dir = frozen_path("Patches"),
            temp_dir = frozen_path("Temp"),
            output_dir = Path(self._output_dir_editor.text()),
            definitions = definitions
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

class BuilderThread(QThread):
    statusUpdate = Signal(Path)

    def __init__(self, game_kpf_path, patch_dir, temp_dir, output_dir, definitions):
        super().__init__()
        self._game_kpf_path = game_kpf_path
        self._patch_dir = patch_dir
        self._temp_dir = temp_dir
        self._output_dir = output_dir
        self._definitions = definitions

    def run(self):
        self._game_kpf = ZipFile(self._game_kpf_path)

        self._output_dir.mkdir(parents = True, exist_ok = True)

        for diff_path in self._patch_dir.glob("*.diff"):
            self.statusUpdate.emit(f"Building {diff_path.with_suffix('.kpf')}...")
            self._make_mod(diff_path)

        self._game_kpf.close()

    def _make_mod(self, diff_path):
        self._temp_dir.mkdir(parents = True, exist_ok = True)

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

        self.statusUpdate.emit(f"Applying {diff_path.name}...")
        patch_set.apply(root = self._temp_dir)

        for text_file_path in self._temp_dir.rglob("*.txt"):
            self.statusUpdate.emit(f"Preprocessing {text_file_path}...")
            self._preprocess(text_file_path)

        output_path = self._output_dir / f"{diff_path.stem}.kpf"
        output_path.unlink(missing_ok = True)

        self.statusUpdate.emit(f"Packing {output_path}...")
        make_archive(output_path, self._temp_dir)

        shutil.rmtree(self._temp_dir)

    def _preprocess(self, path):
        with open(path, "rt") as file:
            text = file.read()

            for id, enabled in self._definitions:
                text = re.sub(id, str(1 if enabled else 0), text)

        with open(path, "wt") as file:
            file.write(text)

#===============================================================================

if __name__ == "__main__":
    app = Application(sys.argv)
    sys.exit(app.exec())
