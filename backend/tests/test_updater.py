from pathlib import Path


def test_update_scripts_restrict_channels_and_use_fast_forward():
    root = Path(__file__).parents[2]
    status = (root / "scripts/update-status.sh").read_text()
    update = (root / "scripts/safe-update.sh").read_text()
    assert "dev|qa|main" in status
    assert "merge-base --is-ancestor" in update
    assert "rolling back" in update
