# Volkszaehler Energy (Home Assistant custom integration)

A lightweight custom integration that reads power data from a Volkszaehler middleware instance and exposes power and derived energy sensors in Home Assistant.

## Requirements
- Home Assistant (core or OS/Supervised) with custom components enabled.
- Reachable Volkszaehler middleware endpoint (`middleware.php`) over HTTP or HTTPS.
- One or more channel UUIDs available from your Volkszaehler setup.

## Installation
1. Copy this repository into your Home Assistant `custom_components` directory as `volkszaehler_energy`.
2. Restart Home Assistant so it loads the new integration.

## Configuration (UI)
1. In Home Assistant, go to **Settings → Devices & Services → + Add Integration** and search for **Volkszaehler Energy**.
2. Enter your Volkszaehler host and port (defaults: `localhost`, `80`). If you include a scheme (e.g., `https://vz.example.com`), it will be used; otherwise HTTP is assumed.
3. Submit. The flow will attempt to reach `http(s)://<host>:<port>/middleware.php` and will create the entry if it returns HTTP 200 or 400.

### Adding channels
After the entry is created:
1. Open the integration entry → **Configure**.
2. Add channels one at a time by providing a **Channel name** (friendly label) and **Channel UUID** from Volkszaehler.
3. Save; repeat to add more channels. Existing channels are shown in the dialog for reference.

## Entities created
For each configured channel UUID:
- Power sensor: current power in watts, fetched from `/middleware.php/data/<uuid>.json?from=now-10min&rows=1`.
- Energy sensor: derived from the power sensor using Home Assistant's integration sensor (kWh, left integration, 2 decimal places).

## Notes and limitations
- Connection test is a simple GET to `middleware.php`; it treats HTTP 200 or 400 as success.
- SSL verification uses Home Assistant defaults; ensure your certificate chain is trusted if you use HTTPS.
