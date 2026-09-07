# DISTI

DISTI uses a Raspberry Pi controller, TimescaleDB, Flask, Next.js, Grafana,
Mosquitto and nginx. Local I2C acquisition is deliberately isolated in the
`hardware-agent`; MQTT remains available for external modules and integrations,
but is not in the local acquisition path.

## First-time setup

```sh
cp disti.env.example disti.env       # replace every change-me value
docker compose up -d postgres
docker compose run --rm backend python migrate.py
docker compose up -d
```

`disti.env`, `mosquitto/password.txt`, and `nginx/.htpasswd` are device-local
and ignored. Existing files are not removed or rotated. On an existing device,
keep those files in place; migrate values into the expanded `disti.env` only
when convenient.

## Hardware modes

* **mock** (default): set `DISTI_HARDWARE_MODE=mock`. Deterministic elapsed-time
  temperature and EC curves are written every `DISTI_POLL_INTERVAL_SECONDS`.
  No devices or privileged containers are needed.
* **replay**: set `DISTI_HARDWARE_MODE=replay` and `DISTI_REPLAY_RUN_ID` to a
  recorded run UUID. `DISTI_REPLAY_SPEED=10` runs ten times faster; set
  `DISTI_REPLAY_PRESERVE_TIMING=false` to emit as quickly as possible.
* **raspberry**: currently an intentional provider stub. Once drivers exist,
  start with the `docker-compose.raspberry.yaml` overlay. Only hardware-agent
  receives `/dev/i2c-1`; neither the stack nor frontend is privileged.

The agent's health endpoint is `http://controller:8081`; backend health is
`/health`. Raw ADC counts and millivolts are always persisted alongside
uncorrected/calibrated values and calibration identity.

## Release and update channels

The immutable promotion path is `dev -> qa -> main`: developer controllers
track `dev`, the hardware validation controller tracks `qa`, and delivered
devices track `main`. Set `DISTI_UPDATE_BRANCH` locally. The legacy
`development` branch is not an update channel and is untouched.

`scripts/update-status.sh` fetches and compares the configured remote commit.
`scripts/safe-update.sh` refuses dirty or non-fast-forward updates, records the
previous commit, builds and restarts Compose, applies additive migrations,
waits for health, and rolls the application checkout/containers back on
failure. Database migrations are forward-compatible and are not destructively
rolled back.

## API and engineering data

The Flask API supports sensor discovery and calibration history/activation,
run start/stop, fraction boundaries and manual cuts. The
`measurement_derivatives` view provides d/dt and d²/dt² for temperature and EC;
`distillation_timeline` combines readings, fractions, cuts, and actuator events
for direct Grafana queries.

## Reference implementation note

VENTI was requested as the updater reference, but no VENTI checkout, Git remote,
or repository instructions were present in this environment, and network access
to the presumed repository was denied. The updater is therefore a conservative
minimal implementation of the specified behavior rather than a claim of exact
file-level parity. Before rollout, compare these two scripts with VENTI and
adopt any deployment-specific service names or hooks that differ.

## Remaining physical hardware work

Implement and bench-test concrete `ADCReader`, `TemperatureProvider`, and
`FractionCollector` adapters for ADS1115, DS2482-100/PT1000 and the selected I2C
stepper controller. Confirm gain/reference voltage, EC compensation/model,
1-Wire topology, I2C addresses, HOME interlocks, position limits, recovery after
brownouts, and Raspberry group/device permissions before enabling raspberry
mode. Mock and replay modes intentionally make none of these assumptions.
