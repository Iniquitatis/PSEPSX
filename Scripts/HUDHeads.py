from PIL import Image

def apply(kpf_open, build_dir):
    output_path = build_dir / "gfx/head_left.png"
    output_path.parent.mkdir(parents = True, exist_ok = True)

    with kpf_open("gfx/head_right.png") as head_right_file:
        head_right = Image.open(head_right_file)

        head_left = head_right.transpose(Image.FLIP_LEFT_RIGHT)
        head_left.save(output_path)
