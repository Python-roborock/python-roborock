"""Tests for firmware / OTA endpoints."""

from roborock.web_api import RoborockApiClient


async def test_get_firmware_info():
    """Test that we can get firmware/OTA info for a device."""
    api = RoborockApiClient(username="test_user@gmail.com")
    ud = await api.pass_login("password")
    fw = await api.get_firmware_info(ud, "abc123")
    assert fw.version == "1.2.3"
    assert fw.current_version == "1.2.0"
    assert fw.updatable is True
    assert fw.desc == "Bug fixes and improvements"
    assert fw.release_time == "2026-05-01"
    assert fw.force_update is False


async def test_start_firmware_update():
    """Test that we can trigger a firmware update for a device."""
    api = RoborockApiClient(username="test_user@gmail.com")
    ud = await api.pass_login("password")
    # Should not raise when the API reports success.
    await api.start_firmware_update(ud, "abc123")


async def test_set_silent_ota():
    """Test that we can toggle automatic firmware updates for a device."""
    api = RoborockApiClient(username="test_user@gmail.com")
    ud = await api.pass_login("password")
    # Should not raise when the API reports success.
    await api.set_silent_ota(ud, "abc123", True)
    await api.set_silent_ota(ud, "abc123", False)
