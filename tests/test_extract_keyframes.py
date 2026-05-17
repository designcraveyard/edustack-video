from pathlib import Path
from PIL import Image


def test_slice_panel_2x2_into_keyframes(tmp_path: Path):
    # Build a 1024x768 panel where each cell is a uniform color.
    img = Image.new("RGB", (1024, 768))
    px = img.load()
    palette = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0)]
    cells = [(0, 0, 512, 384), (512, 0, 1024, 384), (0, 384, 512, 768), (512, 384, 1024, 768)]
    for color, (x0, y0, x1, y1) in zip(palette, cells):
        for x in range(x0, x1):
            for y in range(y0, y1):
                px[x, y] = color

    panel = tmp_path / "panel.png"
    img.save(panel)

    # Use the slicer directly
    from scripts.phase_storyboard import slice_panel
    out = slice_panel(panel, rows=2, cols=2, out_dir=tmp_path / "kf", beat_ids=[1, 2, 3, 4])
    assert len(out) == 4
    for p, expected in zip(out, palette):
        cell = Image.open(p)
        # Sample middle pixel
        mid = cell.getpixel((cell.width // 2, cell.height // 2))
        assert mid == expected, f"{p.name} mid={mid} expected={expected}"
