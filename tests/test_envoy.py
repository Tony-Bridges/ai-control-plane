import subprocess
import pathlib
import pytest

ENVOY_CONFIG = pathlib.Path(__file__).parent.parent / "envoy" / "envoy.yaml"


class TestEnvoyConfig:
    def test_config_file_exists(self):
        assert ENVOY_CONFIG.exists()

    def test_config_is_valid_yaml(self):
        import yaml
        with open(ENVOY_CONFIG) as f:
            config = yaml.safe_load(f)
        assert "static_resources" in config
        assert "listeners" in config["static_resources"]
        assert "clusters" in config["static_resources"]
