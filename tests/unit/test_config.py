from app import config, get_config


def test_config():
    assert get_config()
    assert config
