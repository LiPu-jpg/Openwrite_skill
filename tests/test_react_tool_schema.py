"""ReAct tool schema contract tests."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.agent.react import OPENWRITE_TOOLS


def test_update_truth_file_tool_schema_uses_canonical_names():
    tool = next(t for t in OPENWRITE_TOOLS if t.name == "update_truth_file")
    desc = tool.parameters["properties"]["file_name"]["description"]

    assert "current_state/ledger/relationships" in desc
    assert "particle_ledger" not in desc
    assert "character_matrix" not in desc
