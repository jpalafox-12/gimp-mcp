from pathlib import Path

from gimp_mcp.backend.mock import MockBackend
from gimp_mcp.config import set_mode


def test_new_ops_and_pipeline(tmp_path: Path):
    set_mode("mock")
    b = MockBackend()
    s = b.seed_demo()
    iid = s["image"]["id"]

    assert b.thumbnail(iid, 200, 200)["ok"]
    assert b.sharpen(iid, 120, 1.0)["ok"]
    assert b.brightness(iid, 1.1)["ok"]
    assert b.contrast(iid, 1.1)["ok"]
    assert b.auto_orient(iid)["ok"]

    pipe = b.pipeline(
        iid,
        [
            {"op": "thumbnail", "max_width": 160, "max_height": 90},
            {"op": "desaturate"},
            {"op": "text", "text": "hi", "x": 5, "y": 5, "size": 16, "color": "#fff"},
        ],
    )
    assert pipe["ok"] is True
    assert "desaturate" in pipe["applied"]
    assert pipe["image"]["width"] <= 160

    out = tmp_path / "p.jpg"
    exp = b.export(iid, str(out), "JPEG")
    assert exp["ok"] is True
    assert out.is_file()

    closed = b.close_image(iid)
    assert closed["ok"] is True
    assert b.list_images() == []


def test_process_cli_mock(tmp_path: Path):
    from typer.testing import CliRunner

    from gimp_mcp.cli import app
    from PIL import Image

    src = tmp_path / "photo.jpg"
    Image.new("RGB", (800, 600), "#336699").save(src, quality=90)
    out = tmp_path / "run"
    runner = CliRunner()
    r = runner.invoke(
        app,
        ["process", str(src), "--out-dir", str(out), "--mode", "mock", "--watermark", "TEST"],
    )
    assert r.exit_code == 0, r.stdout
    assert "process" in r.stdout
    assert list(out.glob("*_processed.png")), r.stdout
