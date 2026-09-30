"""Step 09 - estimate model specifications marked `ready` in config/models.yaml.

Input : data/processed/panel_partner_year.parquet
Output: outputs/models/<spec>.txt, outputs/models/<spec>_meta.json,
        outputs/tables/<spec>_coefficients.csv
"""

import _bootstrap  # noqa: F401

from srl.models.estimate import fit_spec, save_result
from srl.models.specs import load_model_specs
from srl.utils.cli import run_step
from srl.utils.config import get_path
from srl.utils.io import read_table


def main(args, logger) -> None:
    specs = load_model_specs()
    for spec in specs:
        logger.info("%-32s %-5s status=%s", spec.name, spec.hypothesis, spec.status)
    ready = [s for s in specs if s.status == "ready"]
    if not ready:
        raise NotImplementedError(
            "No model spec has status `ready` in config/models.yaml. Bind placeholder variables "
            "to panel columns and mark specs ready once the panel exists."
        )
    panel = read_table(get_path("processed.panel"))
    for spec in ready:
        result = fit_spec(panel, spec)
        paths = save_result(result, spec)
        logger.info("%s: nobs=%d -> %s", spec.name, int(result.nobs), paths["summary"].name)


if __name__ == "__main__":
    run_step("09_run_models", main)
