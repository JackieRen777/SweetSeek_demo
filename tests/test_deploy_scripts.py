from pathlib import Path
import subprocess


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


def test_release_has_explicit_gate_and_rollback():
    oneclick = (DEPLOY / "deploy_ecs_oneclick.sh").read_text(encoding="utf-8")
    assert "gate1|gate2" in oneclick
    assert "rollback_release.sh" in (DEPLOY / "activate_release.sh").read_text(encoding="utf-8")
    assert "900" in (DEPLOY / "verify_release.sh").read_text(encoding="utf-8")
    assert "gate1-observation.json" in (DEPLOY / "record_gate_observation.py").read_text(encoding="utf-8")


def test_rollback_restores_index_links_and_service_snapshot():
    activate = (DEPLOY / "activate_release.sh").read_text(encoding="utf-8")
    rollback = (DEPLOY / "rollback_release.sh").read_text(encoding="utf-8")
    assert "index-links.previous" in activate
    assert "index-links.previous" in rollback
    assert "sweetseek.service.previous-state" in activate
    assert "sweetseek.service.previous-state" in rollback
