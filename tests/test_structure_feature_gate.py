import os
import subprocess
import sys


def test_disabled_structure_tools_are_not_imported_or_registered():
    script = """
import sys
sys.modules['services.md_builder_api'] = None
sys.modules['services.docking_api'] = None
from app import app
routes = {rule.rule for rule in app.url_map.iter_rules()}
assert not any(route.startswith('/api/docking') for route in routes), routes
assert not any(route.startswith('/api/md-builder') for route in routes), routes
print('STRUCTURE_TOOLS_DISABLED_OK')
"""
    environment = {
        **os.environ,
        "STRUCTURE_TOOLS_ENABLED": "false",
        "RAG_EAGER_INIT": "false",
        "RAG_ALLOW_AUTO_BUILD": "false",
    }
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=os.getcwd(),
        env=environment,
        text=True,
        capture_output=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "STRUCTURE_TOOLS_DISABLED_OK" in result.stdout
