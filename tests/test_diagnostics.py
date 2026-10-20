from conftest import TOKEN, make_entry, setup_entry


async def test_diagnostics_redacts_token(hass, gateway):
    from custom_components.neore.diagnostics import async_get_config_entry_diagnostics

    entry = await setup_entry(hass, make_entry(TOKEN))
    diag = await async_get_config_entry_diagnostics(hass, entry)
    assert TOKEN not in str(diag)
    assert diag["entry"]["token"] == "**REDACTED**"
    assert diag["gateway_health"]["status"] == "ok"
    assert diag["failed_polls"] == 0
