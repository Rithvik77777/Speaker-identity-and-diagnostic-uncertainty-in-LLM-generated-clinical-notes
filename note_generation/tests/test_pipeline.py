"""Offline tests: no network, no API keys. Run: python -m pytest note_generation/tests -q"""
import argparse
import copy
import sys

import pandas as pd
import pytest

from note_generation import analyze, markers, run
from note_generation.common import (build_items, load_config, load_prompt, primary_prompt, prompt_versions,
                                    protocol_hash, render_user, run_id, run_prompts, strip_insertion)
from note_generation.providers import PermanentError, api_key
from note_generation.screen import screen_note
from note_generation.validate_inputs import check_inputs

CFG = load_config()


# ---------- gate 1 / data ----------

def test_gate1_passes_on_frozen_data():
    errors, stats = check_inputs(CFG)
    assert errors == []
    assert stats["encounters"] == 187 and stats["dev_encounters"] == 18 and stats["eval_encounters"] == 169


def test_strip_insertion_requires_exactly_one_line():
    assert strip_insertion("[doctor] a\n[patient] b", "[patient] b") == "[doctor] a"
    with pytest.raises(ValueError):
        strip_insertion("[doctor] a", "[patient] b")
    with pytest.raises(ValueError):
        strip_insertion("[patient] b\n[patient] b", "[patient] b")


@pytest.mark.parametrize("run_name,n", [("dev", 36), ("eval", 338), ("baseline", 169)])
def test_item_counts(run_name, n):
    items = build_items(CFG, run_name)
    assert len(items) == n
    ids = {run_id("v", "m", i["encounter_id"], i["speaker"], i["insertion"]) for i in items}
    assert len(ids) == n


def test_speakers_of_an_encounter_run_back_to_back():
    items = build_items(CFG, "dev")
    for a, b in zip(items[::2], items[1::2]):
        assert a["encounter_id"] == b["encounter_id"] and {a["speaker"], b["speaker"]} == {"doctor", "patient"}


def test_baseline_has_no_inserted_line():
    for it in build_items(CFG, "baseline")[:20]:
        assert it["condition"].lower() not in it["dialogue"].lower()


def test_protocol_hash_is_per_model():
    """Filling in another model's ID must not invalidate notes already made by this one."""
    other = copy.deepcopy(CFG)
    other["models"]["claude_a"]["model_id"] = "some-claude-id"
    assert protocol_hash(other, "gemini") == protocol_hash(CFG, "gemini")
    assert protocol_hash(other, "claude_a") != protocol_hash(CFG, "claude_a")
    assert protocol_hash(other) != protocol_hash(CFG)          # freeze still locks every model
    shared = copy.deepcopy(CFG)
    shared["generation"]["max_output_tokens"] += 1
    assert protocol_hash(shared, "gemini") != protocol_hash(CFG, "gemini")


def test_prompt_renders_dialogue_once_and_never_mentions_certainty():
    system, user = load_prompt(primary_prompt(CFG))
    rendered = render_user(user, "[doctor] {weird braces}\n[patient] hi")
    assert "{weird braces}" in rendered and "{dialogue}" not in rendered
    for word in ("certain", "hedge", "attribut", "diagnos"):
        assert word not in (system + user).lower(), f"baseline prompt must not mention '{word}'"


def test_guarded_prompt_is_v1_plus_one_paragraph():
    """Any v1/v2 difference in the notes must come from the added instruction alone."""
    assert primary_prompt(CFG) == "note_v1" and "note_v2_guarded" in prompt_versions(CFG)
    s1, u1 = load_prompt("note_v1")
    s2, u2 = load_prompt("note_v2_guarded")
    assert s1 == s2
    head, tail = u1.split("\n\nTRANSCRIPT:")
    assert u2.startswith(head + "\n\n") and u2.endswith("\n\nTRANSCRIPT:" + tail)
    added = u2[len(head) + 2: len(u2) - len("\n\nTRANSCRIPT:" + tail)]
    assert "\n\n" not in added and "certainty" in added and "doctor or the patient" in added
    assert "diagnos" not in added.lower()        # never points at the inserted condition


def test_runs_use_the_right_prompts():
    assert run_prompts(CFG, "eval") == ["note_v1", "note_v2_guarded"]
    assert run_prompts(CFG, "dev") == ["note_v1", "note_v2_guarded"]
    assert run_prompts(CFG, "baseline") == ["note_v1"]


def test_freeze_locks_every_prompt(monkeypatch):
    from note_generation import common, freeze
    h = freeze.current_hashes(CFG)
    assert set(h["prompts_sha256"]) == {"note_v1", "note_v2_guarded"}
    real = common.load_prompt
    monkeypatch.setattr(common, "load_prompt", lambda v: (real(v)[0], real(v)[1] + " edited") if v == "note_v2_guarded" else real(v))
    assert freeze.current_hashes(CFG)["prompts_sha256"] != h["prompts_sha256"]


# ---------- markers ----------

def _rec(**kw):
    base = dict(status="ok", note_text="CHIEF COMPLAINT\nx\n" * 30, finish_reason="stop", model_returned="model-x",
                reasoning_tokens=None, synonyms="gout", condition="gout", insertion=True)
    base.update(kw)
    return base


MODEL = {"provider": "anthropic", "model_id": "model-x"}


@pytest.mark.parametrize("kw,flag", [
    (dict(finish_reason="length"), "TRUNCATED"),
    (dict(finish_reason="refusal"), "REFUSAL"),
    (dict(note_text=""), "EMPTY"),
    (dict(model_returned="other-model"), "MODEL_MISMATCH"),
    (dict(note_text="[patient] says hi " * 20), "RAW_SPEAKER_TAGS"),
    (dict(note_text="**Plan** " * 40), "MARKDOWN"),
    (dict(insertion=False, note_text="possible gout " * 20), "CONDITION_IN_BASELINE"),
    (dict(synonyms="uti", condition="uti", note_text="likely uti " * 30), "SHORT_SYNONYM"),
    (dict(reasoning_tokens=int(0.9 * CFG["generation"]["max_output_tokens"])), "HEAVY_REASONING"),
    (dict(status="error", note_text=None), "ERROR"),
])
def test_markers(kw, flag):
    assert flag in markers.compute(_rec(**kw), MODEL, CFG)


def test_exclude_markers_make_note_unscorable():
    assert not markers.is_scorable(["TRUNCATED"])
    assert markers.is_scorable(["MISSING_HEADINGS", "MARKDOWN"])


def test_model_version_suffix_is_not_a_mismatch():
    assert "MODEL_MISMATCH" not in markers.compute(_rec(model_returned="models/model-x-2026-10"), MODEL, CFG)


# ---------- run barriers ----------

def _run_main(monkeypatch, argv, cfg=None):
    monkeypatch.setattr(sys, "argv", ["run", *argv])
    if cfg is not None:
        monkeypatch.setattr(run, "load_config", lambda: cfg)
    return run.main()


@pytest.fixture(autouse=True)
def _no_real_api_calls(monkeypatch):
    """Tests must never reach a real provider, whatever config.yaml currently holds."""
    real = run.get_generate

    def guarded(provider):
        if provider != "mock":
            raise AssertionError(f"test tried to call the real {provider!r} API")
        return real(provider)
    monkeypatch.setattr(run, "get_generate", guarded)


def test_barrier_todo_model_id(monkeypatch):
    cfg = copy.deepcopy(CFG)
    cfg["models"]["claude_a"]["model_id"] = "TODO_CLAUDE_MODEL_A"
    assert _run_main(monkeypatch, ["--model", "claude_a", "--run", "dev"], cfg) == 2


def test_barrier_baseline_has_no_guarded_prompt(monkeypatch):
    assert _run_main(monkeypatch, ["--model", "claude_a", "--run", "baseline", "--prompt", "note_v2_guarded",
                                   "--dry-run"]) == 2


def test_barrier_eval_requires_freeze(monkeypatch, tmp_path):
    cfg = copy.deepcopy(CFG)
    cfg["models"]["claude_a"]["model_id"] = "real-model"
    monkeypatch.setattr(run, "FREEZE_FILE", tmp_path / "missing.json")
    assert _run_main(monkeypatch, ["--model", "claude_a", "--run", "eval"], cfg) == 2


def test_barrier_placeholder_api_key(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "your-anthropic-api-key-here")
    with pytest.raises(PermanentError):
        api_key("anthropic")


def test_barrier_unknown_model(monkeypatch):
    assert _run_main(monkeypatch, ["--model", "gpt", "--run", "dev"]) == 2


# ---------- screen ----------

def test_screen_finds_hedge_attribution_and_section():
    note = ("CHIEF COMPLAINT\nAnkle pain.\n\nHISTORY OF PRESENT ILLNESS\nThe patient wonders whether this could be gout.\n\n"
            "ASSESSMENT AND PLAN\nAnkle sprain. Will check uric acid to rule out gout.")
    s = screen_note(note, ["gout"])
    assert s["auto_mention"] == "present" and s["auto_n_mentions"] == 2
    assert "patient wonders" in s["auto_patient_attr_cues"]
    assert "could" in s["auto_hedge_cues"]
    assert s["auto_sections"] == "subjective;assessment_plan"
    assert "check" in s["auto_plan_cues"]


def test_screen_omitted():
    assert screen_note("CHIEF COMPLAINT\nAnkle pain.", ["gout"])["auto_mention"] == "omitted"


# ---------- analysis ----------

def _labels_and_key(tmp_path):
    lab, key = [], []
    for e in range(40):
        for spk in ("doctor", "patient"):
            iid = f"I{e:03d}{spk[0]}"
            definite = spk == "patient"          # synthetic: patient copies always hardened
            lab.append(dict(item_id=iid, mention="present", certainty="definite" if definite else "hedged",
                            attribution="correct", section="subjective", plan_action="no", evidence_span="x"))
            key.append(dict(item_id=iid, run_id=iid, model_key="m", encounter_id=f"E{e}", speaker=spk,
                            split="test1", config="aci", template_id="T1"))
    lp, kp = tmp_path / "labels.csv", tmp_path / "key.csv"
    pd.DataFrame(lab).to_csv(lp, index=False)
    pd.DataFrame(key).to_csv(kp, index=False)
    return lp, kp


def test_metrics_gap_and_ci(tmp_path, monkeypatch):
    lp, kp = _labels_and_key(tmp_path)
    monkeypatch.setattr(analyze, "OUT", tmp_path)
    args = argparse.Namespace(run="eval", labels=str(lp), key=str(kp), by=None, n_boot=500, allow_partial=False)
    assert analyze.cmd_metrics(args) == 0
    res = pd.read_csv(tmp_path / "analysis" / "eval_metrics.csv")
    hr = res[res.metric == "hardening_rate"].iloc[0]
    assert hr.gap_patient_minus_doctor == pytest.approx(1.0)
    assert hr.ci95_lo == pytest.approx(1.0) and hr.mcnemar_p < 0.001
    mr = res[res.metric == "mention_rate"].iloc[0]
    assert mr.gap_patient_minus_doctor == pytest.approx(0.0)


def test_metrics_refuse_dirty_labels(tmp_path, monkeypatch):
    lp, kp = _labels_and_key(tmp_path)
    df = pd.read_csv(lp)
    df.loc[0, "certainty"] = "kinda sure"
    df.to_csv(lp, index=False)
    monkeypatch.setattr(analyze, "OUT", tmp_path)
    args = argparse.Namespace(run="eval", labels=str(lp), key=str(kp), by=None, n_boot=100, allow_partial=False)
    assert analyze.cmd_metrics(args) == 1


def test_mcnemar_and_kappa():
    assert analyze.mcnemar_exact(0, 0) == 1.0
    assert analyze.mcnemar_exact(0, 10) < 0.01
    a = pd.Series(["x", "y", "x", "y"])
    assert analyze.cohen_kappa(a, a) == pytest.approx(1.0)
