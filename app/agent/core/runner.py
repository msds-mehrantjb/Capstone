from agent.collectors.dc_collector import DomainControllerCollector
import json
from datetime import datetime


class AgentRunner:

    def __init__(self):
        self.collector = DomainControllerCollector()

    def execute(self):

        metadata = self.collector.collect()

        metadata["collection_info"] = {
            "collected_at": datetime.utcnow().isoformat(),
            "collector_version": "1.0.0"
        }

        return metadata
