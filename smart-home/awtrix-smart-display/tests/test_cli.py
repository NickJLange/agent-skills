from unittest.mock import patch
import pytest

def test_cli_parser():
    from awtrix_display.cli import main
    with patch("sys.argv", ["awtrix", "-h"]):
        with pytest.raises(SystemExit) as excinfo:
            main()
        assert excinfo.value.code == 0
