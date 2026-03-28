"""USF dbt Adapter — bridge between dbt Semantic Layer and USF SDL."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import requests
import yaml

from usf_dbt.converter import dbt_metric_to_sdl
from usf_dbt.models import DbtMetric


class USFDbtAdapter:
    """Bridge between dbt Semantic Layer and USF SDL.

    Reads dbt schema.yml metric definitions and converts them
    to USF SDL YAML format, ready to POST to usf-sdl /compile.
    """

    def __init__(self, dbt_project_path: str, usf_api_url: str | None = None):
        self.project_path = Path(dbt_project_path)
        self.usf_api_url = usf_api_url

    def discover_metrics(self) -> list[DbtMetric]:
        """Scan dbt project for schema.yml files, extract metric definitions."""
        metrics: list[DbtMetric] = []
        for yml_file in self.project_path.rglob("schema.yml"):
            content = yaml.safe_load(yml_file.read_text())
            if not content:
                continue
            for metric_data in content.get("metrics", []):
                metrics.append(DbtMetric(**metric_data))
        return metrics

    def convert_to_sdl(
        self,
        metric: DbtMetric,
        ontology_class: str = "rdfs:Resource",
    ) -> dict[str, Any]:
        """Convert a dbt metric definition to USF SDL metric format."""
        return dbt_metric_to_sdl(metric, ontology_class=ontology_class)

    def export_sdl_yaml(self, output_path: str | None = None) -> str:
        """Convert all discovered metrics to SDL YAML. Optionally write to file."""
        metrics = self.discover_metrics()
        sdl_doc = {
            "version": "1.0",
            "metrics": [dbt_metric_to_sdl(m) for m in metrics],
        }
        yaml_str = yaml.dump(sdl_doc, default_flow_style=False, sort_keys=False)

        if output_path:
            Path(output_path).write_text(yaml_str)

        return yaml_str

    def sync_to_usf(self, tenant_id: str, context: str = "default") -> dict[str, Any]:
        """POST converted SDL to usf-sdl /compile endpoint.

        Returns compilation result from the USF SDL service.
        """
        if not self.usf_api_url:
            raise ValueError("usf_api_url is required for sync_to_usf")

        sdl_yaml = self.export_sdl_yaml()
        resp = requests.post(
            f"{self.usf_api_url}/compile",
            json={
                "tenant_id": tenant_id,
                "context": context,
                "sdl": sdl_yaml,
            },
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()
