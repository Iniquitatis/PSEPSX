from PIL import Image

def apply(kpf_loader, temp_dir):
    temp_scarab_path = temp_dir / "gfx/scarab.png"

    kpf_loader("gfx/scarab.png", temp_scarab_path)

    with Image.open(temp_scarab_path) as scarab:
        clean_image = Image.new(scarab.mode, scarab.size, (0, 0, 0, 0))
        clean_image.save(temp_scarab_path)
