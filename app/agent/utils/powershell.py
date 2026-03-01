import subprocess
import json


def run_powershell_script(script_path: str) -> dict:
    """
    Executes PowerShell script and returns parsed JSON.
    """

    result = subprocess.run(
        ["powershell", "-ExecutionPolicy", "Bypass", "-File", script_path],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        raise RuntimeError(f"PowerShell Error:\n{result.stderr}")

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON output: {e}")
