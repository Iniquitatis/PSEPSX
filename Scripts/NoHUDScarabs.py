from PIL import Image

def apply(kpf_open, build_dir):
    output_path = build_dir / "gfx/scarab.png"
    output_path.parent.mkdir(parents = True, exist_ok = True)

    with kpf_open("gfx/scarab.png") as scarab_file:
        scarab = Image.open(scarab_file)

        clean_image = Image.new(scarab.mode, scarab.size, (0, 0, 0, 0))
        clean_image.save(output_path)
