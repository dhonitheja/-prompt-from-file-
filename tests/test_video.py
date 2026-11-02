"""Videos must reach the model as ONE contact sheet with video-style instructions."""
import shutil
import subprocess

import pytest

import app as appmod

pytestmark = pytest.mark.skipif(
    not (shutil.which("ffmpeg") and shutil.which("ffprobe")), reason="ffmpeg is not installed"
)


@pytest.fixture(scope="module")
def clip(tmp_path_factory):
    path = tmp_path_factory.mktemp("vid") / "clip.mp4"
    subprocess.run(
        ["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "testsrc=duration=3:size=320x240:rate=10",
         "-pix_fmt", "yuv420p", "-y", str(path)],
        check=True,
    )
    return path.read_bytes()


def post(client, clip, **data):
    return client.post("/api/prompt", files={"file": ("clip.mp4", clip, "video/mp4")}, data=data)


def sent(backends):
    msg = backends.calls[0][1]["json"]["messages"][1]
    return msg["content"], msg.get("images", [])


def test_video_is_sent_as_one_image(client, backends, clip):
    r = post(client, clip)
    assert r.status_code == 200
    _, images = sent(backends)
    assert len(images) == 1  # not one image per frame


def test_contact_sheet_is_a_real_wide_jpeg(client, backends, clip, monkeypatch):
    seen = {}
    real = appmod.video_sheet

    def spy(data, suffix):
        seen["sheet"], seen["n"] = real(data, suffix)
        return seen["sheet"], seen["n"]

    monkeypatch.setattr(appmod, "video_sheet", spy)
    post(client, clip)
    assert seen["sheet"][:2] == b"\xff\xd8"  # JPEG
    assert seen["n"] == appmod.VIDEO_FRAMES
    # 3 columns of 512px plus padding is far wider than any single sampled frame
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "stream=width,height", "-of", "csv=p=0", "-"],
        input=seen["sheet"], capture_output=True, check=True,
    ).stdout.decode().strip()
    width, height = (int(v) for v in out.split(","))
    assert width > 1400 and height > 300


def test_instruction_says_it_is_a_video(client, backends, clip):
    content, _ = sent(backends) if post(client, clip) else (None, None)
    assert "ONE video" in content and "not a photo" in content and "time order" in content


def test_video_defaults_to_video_style_prompt(client, backends, clip):
    post(client, clip)
    content, _ = sent(backends)
    assert appmod.TARGETS["video"] in content


def test_explicit_target_overrides_video_default(client, backends, clip):
    r = post(client, clip, target="midjourney")
    content, _ = sent(backends)
    assert r.json()["target"] == "midjourney"
    assert appmod.TARGETS["midjourney"] in content and appmod.TARGETS["video"] not in content


def test_images_are_not_given_the_video_default(client, backends):
    png = b"\x89PNG\r\n\x1a\n" + b"0" * 32
    client.post("/api/prompt", files={"file": ("p.png", png, "image/png")})
    content, _ = sent(backends)
    assert "Target tool" not in content


def test_notes_explain_the_contact_sheet(client, backends, clip):
    notes = post(client, clip).json()["notes"]
    assert any("contact sheet" in n for n in notes)
