import difflib
import shutil
from argparse import ArgumentParser
from pathlib import Path
from zipfile import ZipFile

import patch

def exists_in_archive(archive_path, src_path):
    with ZipFile(archive_path) as archive:
        return src_path in archive.namelist()

def extract_file(archive_path, src_path, dst_path):
    with ZipFile(archive_path) as archive:
        with archive.open(src_path) as src_file, open(dst_path, "wb") as dst_file:
            shutil.copyfileobj(src_file, dst_file)

def make_archive(result_path, root_dir):
    shutil.make_archive(result_path.with_suffix(""), "zip", root_dir)
    result_path.with_suffix(".zip").rename(result_path)

def make_mod(diff_path, game_kpf_path, temp_dir, output_dir):
    temp_dir.mkdir(parents = True, exist_ok = True)

    patch_set = patch.fromfile(diff_path)

    for item in patch_set.items:
        src_path = item.source.decode("utf-8")
        dst_path = temp_dir / Path(item.target.decode("utf-8"))
        dst_path.parent.mkdir(parents = True, exist_ok = True)

        if src_path == "dev/null":
            print(f"Creating {dst_path}...")

            with open(dst_path, "w") as dst_file:
                for hunk in item.hunks:
                    for line in hunk.text:
                        line = line.decode("utf-8").strip("\n\r")[1:]
                        dst_file.write(f"{line}\n")

        elif dst_path == "dev/null":
            print(f"Removing {dst_path}...")

            if dst_path.exists():
                dst_path.unlink()

        elif exists_in_archive(game_kpf_path, src_path):
            print(f"Extracting {src_path}...")
            extract_file(game_kpf_path, src_path, dst_path)

    print(f"Applying {diff_path.name}...")
    patch_set.apply(root = temp_dir)

    output_path = output_dir / f"{diff_path.stem}.kpf"

    print(f"Packing {output_path}...")
    make_archive(output_path, temp_dir)

    shutil.rmtree(temp_dir)

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("-g", "--game-kpf-path",
        type = Path,
        metavar = "PATH",
        required = True
    )
    parser.add_argument("-p", "--patch-dir",
        type = Path,
        metavar = "PATH",
        default = "Patches"
    )
    parser.add_argument("-t", "--temp-dir",
        type = Path,
        metavar = "PATH",
        default = "Temp"
    )
    parser.add_argument("-o", "--output-dir",
        type = Path,
        metavar = "PATH",
        default = "Mods"
    )

    args = parser.parse_args()

    if args.output_dir.exists():
        shutil.rmtree(args.output_dir)

    args.output_dir.mkdir(parents = True, exist_ok = True)

    for diff_path in Path(args.patch_dir).glob("*.diff"):
        make_mod(diff_path, args.game_kpf_path, args.temp_dir, args.output_dir)

    print("Done.")
