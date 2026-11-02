"""Tests for the 'which tool is the prompt for' option."""
import pytest

import app as appmod

TXT = ("a.txt", b"hello", "text/plain")
NAMED = [t for t in appmod.TARGETS if t]


def post(client, **data):
    return client.post("/api/prompt", files={"file": TXT}, data=data)


def sent(backends):
    return backends.calls[0][1]["json"]["messages"][1]["content"]


def test_default_has_no_target_text(client, backends):
    r = post(client)
    assert r.status_code == 200 and r.json()["target"] == ""
    assert "Target tool" not in sent(backends)


@pytest.mark.parametrize("target", NAMED)
def test_each_target_is_sent_to_the_model(client, backends, target):
    r = post(client, target=target)
    assert r.status_code == 200 and r.json()["target"] == target
    assert appmod.TARGETS[target] in sent(backends)


def test_target_is_case_and_space_insensitive(client, backends):
    r = post(client, target="  MidJourney ")
    assert r.status_code == 200 and r.json()["target"] == "midjourney"


def test_unknown_target_rejected_before_any_work(client, backends):
    r = post(client, target="photoshop")
    assert r.status_code == 400 and "midjourney" in r.json()["detail"]
    assert not backends.calls


def test_target_and_note_together(client, backends):
    post(client, target="video", note="keep it under 10 seconds")
    content = sent(backends)
    assert appmod.TARGETS["video"] in content and "under 10 seconds" in content


def test_every_target_is_offered_on_the_page(client):
    page = client.get("/").text
    for target in NAMED:
        assert f'value="{target}"' in page
