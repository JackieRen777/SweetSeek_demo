import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEPLOY = ROOT / "scripts" / "maintenance" / "deploy"


def test_deploy_shell_scripts_parse():
    scripts = sorted(DEPLOY.glob("*.sh")) + sorted((ROOT / "scripts" / "docking").glob("*.sh"))
    assert scripts
    for script in scripts:
        subprocess.run(["bash", "-n", str(script)], check=True)


def test_atomic_deploy_does_not_overwrite_live_tree():
    oneclick = (DEPLOY / "deploy_ecs_oneclick.sh").read_text(encoding="utf-8")
    prepare = (DEPLOY / "prepare_release.sh").read_text(encoding="utf-8")
    activate = (DEPLOY / "activate_release.sh").read_text(encoding="utf-8")
    combined = oneclick + prepare + activate
    assert "pkill" not in combined
    assert "git reset" not in combined
    assert "rsync -az --delete" not in combined
    assert "/www/sweetseek/current" in (DEPLOY / "systemd" / "sweetseek.service").read_text()


def test_git_release_has_canary_rollback_and_observation():
    deploy = (DEPLOY / "deploy_from_git.sh").read_text(encoding="utf-8")
    observe = (DEPLOY / "observe_git_release.sh").read_text(encoding="utf-8")
    recorder = (DEPLOY / "record_release_observation.py").read_text(encoding="utf-8")
    assert "127.0.0.1:5002" in deploy
    assert "rollback_git_release.sh" in deploy
    assert "STRUCTURE_TOOLS_ENABLED=false" in deploy
    assert "--preflight-only" in deploy
    assert "awk -v load_value=" in deploy
    assert "awk -v load=" not in deploy
    assert "http://127.0.0.1:5001/api/live" in deploy
    assert "http://127.0.0.1:5001/api/health" in deploy
    assert "--background" in deploy
    assert "CPUQuota=120%" in deploy
    assert "MemoryMax=2600M" in deploy
    assert "MemoryHigh=1600M" in deploy
    assert "MemoryMax=2000M" in deploy
    assert deploy.index('preflight_json="$(preflight)"') < deploy.index('mkdir -p "$BASE/incoming"')
    assert "legacy Gunicorn did not stop within 30 seconds" in deploy
    assert "sleep 1800" in observe
    assert "activation-rag.json" in observe
    assert "release-observation.json" in recorder
    assert "sustained_swap_growth" in recorder


def test_production_service_matches_low_memory_server_budget():
    service = (DEPLOY / "systemd" / "sweetseek.service").read_text(encoding="utf-8")
    assert "MemoryHigh=1900M" in service
    assert "MemoryMax=2300M" in service
    assert "--workers 1" not in service  # worker count is fixed in gunicorn_config.py


def test_rollback_restores_index_links_and_service_snapshot():
    activate = (DEPLOY / "activate_release.sh").read_text(encoding="utf-8")
    rollback = (DEPLOY / "rollback_release.sh").read_text(encoding="utf-8")
    assert "index-links.previous" in activate
    assert "index-links.previous" in rollback
    assert "sweetseek.service.previous-state" in activate
    assert "sweetseek.service.previous-state" in rollback
