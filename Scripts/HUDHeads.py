from PIL import Image

def apply(kpf_loader, temp_dir):
    temp_head_left_path = temp_dir / "gfx/head_left.png"
    temp_head_right_path = temp_dir / "gfx/head_right.png"

    kpf_loader("gfx/head_right.png", temp_head_right_path)

    with Image.open(temp_head_right_path) as head_right:
        head_left = head_right.transpose(Image.FLIP_LEFT_RIGHT)
        head_left.save(temp_head_left_path)

    temp_head_right_path.unlink()
