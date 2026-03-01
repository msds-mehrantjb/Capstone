import os
from agent.utils.powershell import run_powershell_script


class DomainControllerCollector:

    def __init__(self):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.script_path = os.path.join(base_dir, "dc_metadata.ps1")

    def collect(self) -> dict:
        """
        Executes PowerShell metadata collection.
        """
        metadata = run_powershell_script(self.script_path)

        # Add agent classification
        metadata["agent_context"] = {
            "system_type": "DomainController",
            "criticality": "High",
            "iso_scope_candidate": True
        }

        return metadata
