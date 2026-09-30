"""Raw data are immutable: derived-data writers must refuse data/raw."""

import pandas as pd
import pytest

from srl.utils.config import get_path
from srl.utils.io import RawDataWriteError, write_table


@pytest.mark.parametrize("relative", ["_should_not_exist.csv", "some_source/2026-01-01/x.parquet"])
def test_write_table_refuses_raw_directory(relative):
    target = get_path("data.raw") / relative
    with pytest.raises(RawDataWriteError):
        write_table(pd.DataFrame({"a": [1]}), target)
    assert not target.exists()
