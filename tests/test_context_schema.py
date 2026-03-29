"""上下文字段规范化测试。"""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.context_schema import normalize_context_payload, normalize_truth_file_key
from tools.truth_manager import TruthFiles
from models.context_package import GenerationContext


def test_normalize_truth_file_key_with_aliases():
    assert normalize_truth_file_key("current_state") == "current_state"
    assert normalize_truth_file_key("particle_ledger") == "ledger"
    assert normalize_truth_file_key("character_matrix") == "relationships"
    assert normalize_truth_file_key("ledger") == "ledger"
    assert normalize_truth_file_key("relationships") == "relationships"


def test_normalize_context_payload_builds_canonical_and_aliases():
    payload = {
        "current_state": "S",
        "particle_ledger": "L",
        "character_matrix": "R",
        "pending_hooks": "H",
    }

    out = normalize_context_payload(payload, include_aliases=True)

    assert out["current_state"] == "S"
    assert out["ledger"] == "L"
    assert out["relationships"] == "R"
    assert out["foreshadowing_summary"] == "H"

    # legacy aliases are still available
    assert out["particle_ledger"] == "L"
    assert out["character_matrix"] == "R"
    assert out["pending_hooks"] == "H"


def test_normalize_context_payload_with_canonical_only():
    payload = {
        "current_state": "S",
        "ledger": "L",
        "relationships": "R",
        "foreshadowing_summary": "H",
    }

    out = normalize_context_payload(payload, include_aliases=False)

    assert out["ledger"] == "L"
    assert out["relationships"] == "R"
    assert out["foreshadowing_summary"] == "H"
    assert "particle_ledger" not in out
    assert "character_matrix" not in out
    assert "pending_hooks" not in out


def test_truth_files_exposes_canonical_fields_with_legacy_aliases():
    truth = TruthFiles(current_state="S", ledger="L", relationships="R")

    assert truth.current_state == "S"
    assert truth.ledger == "L"
    assert truth.relationships == "R"
    assert truth.particle_ledger == "L"
    assert truth.character_matrix == "R"


def test_generation_context_prefers_canonical_truth_fields():
    context = GenerationContext(
        current_state="S",
        ledger="L",
        relationships="R",
    )

    assert context.current_state == "S"
    assert context.ledger == "L"
    assert context.relationships == "R"
    assert context.particle_ledger == "L"
    assert context.character_matrix == "R"
