# DISTI

DISTI is a Raspberry Pi appliance using TimescaleDB, Flask, Grafana,
Mosquitto and nginx. Local I2C acquisition is deliberately isolated in the
`hardware-agent`; MQTT remains available for external modules and integrations,
but is not in the local acquisition path.

## Repository architecture

```text
backend/                 Shared Python image and code
├── disti/api/           Flask application factory and HTTP routes
├── disti/hardware/      Contracts, providers, Raspberry adapter composition
│   ├── adc/             ADC contract and ADS1115 adapter
│   └── onewire/         1-Wire contract and DS2484/DS18B20 protocol adapter
├── entrypoints/         API, hardware-agent, migration, and fixture executables
├── migrations/          TimescaleDB schema migrations
└── tests/               API, hardware, domain, and deployment tests
grafana/                 Active PostgreSQL datasource and dashboards
mosquitto/               MQTT broker
nginx/                    Appliance reverse proxy
watchdog/                 Independent container watchdog
piTerminal/               Raspberry Pi kiosk and rollout tooling
scripts/                  Operator update helpers
```

The `api` and `hardware-agent` services build the same `disti-backend` image
but run separate entrypoints. Acquisition failures therefore cannot restart the
API. The single production stack grants only `hardware-agent` access to
`/dev/i2c-1` and selects Raspberry hardware acquisition. Sensor
measurements and Grafana use PostgreSQL/TimescaleDB. MQTT remains an integration
boundary and is not part of local I2C acquisition.

## First-time setup

Raspberry I2C must be enabled before starting DISTI, and `/dev/i2c-1` must
exist because Compose maps that physical bus into the hardware agent:

```sh
sudo raspi-config nonint do_i2c 0
ls -l /dev/i2c-1
```

The canonical foreground startup command for the one supported stack is
`docker compose up --build`; use `docker compose up -d --build` when detached
operation is appropriate.

```sh
cp disti.env.example disti.env
nano disti.env                            # replace every change-me value
docker compose up -d --build postgres api
docker compose exec -T api python -m entrypoints.migrate
docker compose up -d
```

Migrations run inside the already allocated API container. Do not use
`docker compose run` for migrations: this stack assigns static service IPs, so
an extra one-off API container can collide with the running API container's
static IP.
The `--build` is also required because migrations are copied into the backend
image rather than bind-mounted from the checkout. Without it, `exec` can run an
older copy of `migrate.py` and its SQL even when the Git working tree is current.

After pulling a migration fix on an already-running QA controller, refresh the
shared backend image and API container before retrying it:

```sh
docker compose build api
docker compose up -d --no-deps --force-recreate api
docker compose exec -T api python -m entrypoints.migrate
docker compose up -d
```

On the ARM64 Pi, rebuild and recreate both Python runtime services without
restarting their dependencies:

```sh
docker compose up -d --build --no-deps --force-recreate api hardware-agent
```

Migrations run inside the already allocated API container. Do not use
`docker compose run` for migrations: this stack assigns static service IPs, so
an extra one-off API container can collide with the running API container's
static IP.

`disti.env` is the single device-local application configuration file. It is
ignored by Git and is never replaced by provisioning or rollout. Repository-root
`.env` is neither read nor required for normal DISTI operation. The tracked
`disti.env.example` is the canonical safe template. In particular,
`MQTT_USERNAME` and `MQTT_PASSWORD` are the only MQTT
credentials an operator maintains.

Grafana receives its native `GF_SECURITY_ADMIN_USER` and
`GF_SECURITY_ADMIN_PASSWORD` variables directly. Grafana datasource provisioning reads the same
PostgreSQL variables directly. Mosquitto receives the MQTT variables unchanged
and generates its hashed runtime-only password file before broker startup. Every MQTT client uses those same two variable names.

The same file supplies PostgreSQL initialization and every database client,
using one canonical contract: `POSTGRES_HOST`, `POSTGRES_DB`, `POSTGRES_USER`,
and `POSTGRES_PASSWORD`. Compose injects `disti.env` directly into PostgreSQL,
api, hardware-agent, watchdog, and Grafana, so normal operator commands do
not need `--env-file`:

```sh
docker compose up -d --build
docker compose down
docker compose ps
docker compose logs
```

Controllers configured with legacy credential names require a one-time edit of
`disti.env`: retain each existing value while renaming the PostgreSQL, Grafana,
and MQTT keys to the canonical names shown in `disti.env.example`. Then rebuild
and recreate the containers without removing the named database volume:

```sh
docker compose up -d --build --force-recreate
docker compose exec -T api python -m entrypoints.migrate
docker compose ps
```

PostgreSQL applies initialization variables only when its data directory is
first initialized. Renaming these environment keys while preserving their
values does not reinitialize PostgreSQL and does not require deleting the
volume. Never add `--volumes` to `docker compose down` for this procedure and
do not remove `disti_db_data`.

At every broker start, the DISTI Mosquitto entrypoint validates those variables
and uses `mosquitto_passwd` to create a mode-0600 hashed password file in a
unique temporary path under `/run/mosquitto`. It resolves the image's
`mosquitto` UID/GID at runtime, gives that user access, and atomically replaces
the configured file before handing off to the upstream entrypoint. Thus a
restart safely replaces the previous generated file and a container recreation
starts cleanly; no generated credential state is persisted. The plaintext
password is neither logged nor stored in a second host file. Mosquitto continues
to run with anonymous access disabled and `password_file` authentication
enabled.

nginx does not contain an `auth_basic` directive and does not read an
`.htpasswd`; its former mount was unused and has been removed. Browser login is
handled by Grafana at the `/` route. If HTTP Basic authentication is introduced
later, its credential provisioning must be designed explicitly rather than
committing an `.htpasswd`.

## Hardware modes

The production Compose service selects **raspberry** mode. The mock and replay
providers remain available for development and automated testing, but are not
separate production Compose configurations.

* **mock**: set `DISTI_HARDWARE_MODE=mock`. Deterministic elapsed-time
  temperature and EC curves are written every `DISTI_POLL_INTERVAL_SECONDS`.
  No devices or privileged containers are needed.
* **replay**: set `DISTI_HARDWARE_MODE=replay` and `DISTI_REPLAY_RUN_ID` to a
  recorded run UUID. `DISTI_REPLAY_SPEED=10` runs ten times faster; set
  `DISTI_REPLAY_PRESERVE_TIMING=false` to emit as quickly as possible.
* **raspberry** (production): uses the ADS1115 and DS2484 adapters. Only
  `hardware-agent` receives `/dev/i2c-1`; the rest of the stack is not privileged.

### ADS1115 Raspberry configuration and validation

The first two single-ended inputs are configured as follows: ADS1115 A0 is
`ec-1` (`ec`) from the DFRobot EC conversion board, and A1 is `ec-temp`
(`temperature`) from its separate PT1000 conversion board. A2 and A3 remain
electrically available but unassigned. DISTI stores the signed ADC count and
uncalibrated millivolts for both inputs. Because no validated EC or PT1000
formula exists yet, `value` is also the raw millivolt signal with unit `mV`,
and metadata explicitly says that engineering conversion is not configured.
Calibration and temperature compensation must remain downstream.

The device-local settings are:

```dotenv
DISTI_ADC_TYPE=ads1115
DISTI_I2C_BUS=1
DISTI_ADS1115_ADDRESS=0x48
DISTI_ADS1115_EC_CHANNEL=0
DISTI_ADS1115_PT1000_CHANNEL=1
DISTI_ADS1115_GAIN=1
DISTI_ADS1115_DATA_RATE=128
```

Gain 1 (±4.096 V full scale) and 128 samples/second are conservative initial
defaults, not final electrical design choices. Confirm that the conversion
boards' full output range cannot exceed the selected PGA range, and confirm
noise/settling at the installed sample rate, before physical sign-off. The
configured address is authoritative; `0x48` is merely the expected address
when ADS1115 ADDR is tied to ground. Use a common ground and appropriate I2C
level adaptation; connect EC analog output to A0 and PT1000-board analog output
to A1. Never apply an analog input outside ADS1115 supply/absolute limits.

On the Pi, enable I2C and validate the host before starting DISTI:

```sh
ls -l /dev/i2c-1
sudo apt-get install -y i2c-tools              # if i2cdetect is absent
i2cdetect -y 1                                 # expect 48 unless configured otherwise
nano disti.env                                 # confirm ADC settings
docker compose up --build
curl http://127.0.0.1:8081/healthz
docker compose logs --tail=100 hardware-agent
docker compose exec -T postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  -c "SELECT time,sensor_id,measurement_type,raw_value,raw_mv,value,unit,quality,metadata FROM sensor_measurements WHERE sensor_id IN ('ec-1','ec-temp') ORDER BY time DESC LIMIT 10;"
```

Run the `psql` command from a shell where the device-local values have been
exported, or substitute its configured database/user values. Healthy Raspberry
status reports I2C availability, ADS1115 reachability, acquisition state, and
the last successful read. A missing bus/device or transient read changes health
to degraded with `last_error`; the process backs off and retries, and the ADC
adapter reopens the bus after a read error rather than requiring a stack restart.
Mock and replay acquisition remain development/testing options outside the
canonical production Compose configuration.

### DS2484 and DS18B20 configuration

Production temperature acquisition uses the Adafruit ADA5976 DS2484
I2C-to-1-Wire adapter,
**not** Raspberry GPIO/kernel w1 and never `/sys/bus/w1/devices`. The DS2484 and
ADS1115 are independent clients of the same `/dev/i2c-1` device exposed to the
hardware agent by the production Compose configuration. The ADA5976 breakout
connects to the Raspberry Pi I2C bus alongside the ADS1115 and exposes the
DS2484 1-Wire port for the DS18B20 bus.

```text
Raspberry Pi
    |
    +-- I2C -- ADS1115
    |              +-- A0 -- ec-1
    |              +-- A1 -- ec-temp
    |
    +-- I2C -- DS2484 (Adafruit ADA5976)
                       |
                       +-- 1-Wire -- vapor-temp / cooler-temp / reserve-temp
```

Up to three DS18B20s share the bridge's single 1-Wire bus. Their physical ROM
IDs are mapped device-locally to stable logical roles. Empty values are valid:

```dotenv
DISTI_ONEWIRE_TYPE=ds2484
DISTI_DS2484_I2C_BUS=1
DISTI_DS2484_ADDRESS=0x18
DISTI_ONEWIRE_VAPOR_ID=
DISTI_ONEWIRE_COOLER_ID=
DISTI_ONEWIRE_RESERVE_ID=
```

`0x18` is the documented ADA5976 default address. The breakout address jumpers
can select `0x18` through `0x1b`; verify the actual board with
`i2cdetect -y 1` and override it when needed. Discovery retains every valid
DS18B20 ROM. It never assigns an unknown device automatically. Health reports
configured assignments, newly discovered
unassigned ROMs, and configured-but-missing ROMs separately. Thus replacing a
probe means discovering its new ROM and updating only the corresponding local
variable; the logical `vapor-temp`, `cooler-temp`, or `reserve-temp` identity
and its history remain stable. A missing optional/reserve probe does not stop
ADC acquisition.

The address and command details above follow the
[Adafruit ADA5976 product documentation](https://www.adafruit.com/product/5976)
and the [Analog Devices DS2484 data sheet](https://www.analog.com/media/en/technical-documentation/data-sheets/ds2484.pdf).

Each polling cycle performs a ROM search, starts one broadcast Convert T, waits
the DS18B20 12-bit worst-case 750 ms, and then addresses each assigned/present
probe to read its scratchpad. ROM and scratchpad Dallas CRC-8 are validated;
bad data is never emitted. One broadcast conversion avoids a separate 750 ms
wait per assigned sensor while keeping the existing sequential agent simple.

Exact Raspberry Pi bring-up and validation procedure:

```sh
sudo raspi-config nonint do_i2c 0
ls -l /dev/i2c-1
sudo apt-get update && sudo apt-get install -y i2c-tools
i2cdetect -y 1                         # expect ADS1115 and configured DS2484 addresses
nano disti.env                         # set raspberry mode, bridge address, leave ROM IDs empty
docker compose up -d --build
curl -s http://127.0.0.1:8081/healthz | python3 -m json.tool
# Copy each onewire_unassigned_devices ROM into its intended DISTI_ONEWIRE_*_ID.
docker compose up -d --force-recreate hardware-agent
curl -s http://127.0.0.1:8081/healthz | python3 -m json.tool
docker compose logs --tail=100 hardware-agent
docker compose exec -T postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  -c "SELECT time,sensor_id,value,unit,metadata FROM sensor_measurements WHERE sensor_id IN ('vapor-temp','cooler-temp','reserve-temp') ORDER BY time DESC LIMIT 12;"
```

Expected health includes `onewire_enabled: true`, `ds2484_reachable: true`,
`onewire_bus_available: true`, the discovered count, assignment/unassigned/
missing collections, `last_successful_onewire_read`, and a sanitized
`onewire_last_error`. Before physical sign-off confirm the ADA5976's detected
DS2484 address, DS2484 power mode, 1-Wire pull-up/power arrangement,
cable-length reliability, and the printed ROM-to-probe/role correspondence.

The agent's health endpoint is `http://127.0.0.1:8081/healthz` on the host and
`http://hardware-agent:8081/healthz` inside Compose; backend health is
`http://127.0.0.1:5000/healthz`. Raw ADC counts and millivolts are always
persisted alongside uncorrected/calibrated values and calibration identity.

Seed a complete fixed 91-minute engineering run with:

```sh
docker compose exec -T api python -m entrypoints.seed_mock_run
```

The seed is idempotent and includes BoilerTop, raw and placeholder-calibrated
EC, sensor temperature, stable and late-run phases, three fractions, a manual
HEART cut, and fraction-collector events.

## Release and update channels

The immutable promotion path is `dev -> qa -> main`: `dev` is development-only,
the hardware validation controller automatically tracks `qa`, and delivered
devices automatically track `main`. The installed updater independently rejects
`dev`. The legacy `development` branch is not an update channel and is untouched.

`scripts/update-status.sh` fetches and compares the device-local configured
remote commit. `scripts/safe-update.sh` delegates to the VENTI-parity runtime
updater, which refuses tracked changes, deploys the exact remote commit,
validates and restarts Compose, applies additive migrations, waits for
`/healthz`, and fully revalidates the previous application revision after a
failure. Database migrations are forward-compatible and are not destructively
rolled back.

## API and engineering data

The Flask API supports sensor discovery and calibration history/activation,
run start/stop, fraction boundaries and manual cuts. The
calibration API retains its `offset` field for client compatibility and maps it
to the database's non-reserved `calibration_offset` column. The
`measurement_derivatives` view provides d/dt and d²/dt² for temperature and EC;
`distillation_timeline` combines readings, fractions, cuts, and actuator events
for direct Grafana queries.

## Reference implementation note

The VENTI technical handoff is the rollout and provisioning reference. DISTI
preserves its TimescaleDB, hardware-agent, Grafana, and local-I2C architecture;
it intentionally does not port ChirpStack, Panstamp, or local-hardware MQTT coupling.

## Remaining physical hardware work

Bench-test the ADS1115 and Adafruit ADA5976 DS2484 adapter and implement concrete
`FractionCollector` hardware for later hardware. Confirm gain/reference voltage,
EC compensation/model,
1-Wire topology, I2C addresses, HOME interlocks, position limits, recovery after
brownouts, and Raspberry group/device permissions before enabling raspberry
mode. Mock and replay modes intentionally make none of these assumptions.

## Raspberry client provisioning

Provisioning follows the VENTI client pattern while retaining DISTI's Compose
and hardware architecture. Automatic clients accept only `qa` and `main`; the
default is `main`. The `dev` branch is never accepted by the installed updater.

Before provisioning, place the client WireGuard file at the ignored path
`piTerminal/client-configs/wg0.conf`. For the owner's QA controller run:

```sh
sudo ./piTerminal/setup_client.sh --rollout-branch qa
```

For a delivered production controller run:

```sh
sudo ./piTerminal/setup_client.sh
```

Both commands install the single supported Raspberry Compose stack. Docker,
WireGuard, graphical kiosk, and rollout are installed by default;
`--skip-docker`, `--skip-wireguard`, `--no-kiosk`, and `--no-rollout` support
pre-provisioned or headless clients. Huawei-compatible USB modem recovery is
opt-in through `--usb-modem-recovery`.

The rollout installer copies the runtime updater outside the checkout to
`/usr/local/sbin/disti-update`, creates the preserved device-local
`/etc/disti-update.conf`, and enables a persistent, randomized systemd timer.
The installer creates `disti.env` from the safe example only when it is absent
and otherwise preserves it. The updater requires that repository-root file.
`.disti-local/` is retained in `.gitignore` only so data left by older
installations cannot be committed; the current rollout owns no files there.
Existing `/etc/disti-update.conf` files are preserved unless `--replace-config`
is requested.

On a controller upgraded from the older layout, copy the active values from
`.disti-local/disti.env` to the repository-root `disti.env`, then rerun
`setup_rollout.sh --replace-config` with the controller's existing branch
selection. After successful startup, remove the obsolete local MQTT password
and nginx htpasswd copies. Updates reset only tracked files, so the root
`disti.env` and any ignored migration leftovers are not overwritten.

Useful diagnostics:

```sh
sudo -u pi /usr/local/sbin/disti-update
systemctl list-timers disti-update.timer
journalctl -u disti-update.service --since today
curl http://127.0.0.1:5000/healthz
curl http://127.0.0.1:5000/watchdog/status
```

The kiosk is installed in the user's graphical session using labwc, LXDE, or
XDG autostart. `/etc/disti-kiosk.conf` is created once and remains local. Its
launcher waits for nginx, uses a nonblocking per-session lock, and starts either
`chromium` or `chromium-browser`; an outer loop retries ten seconds after exit.
The default URL is the operational nginx/Grafana entry point; nginx and the
kiosk both use the Grafana route at `/`.

## Watchdog security and behavior

`disti-watchdog` monitors Flask liveness, aggregate PostgreSQL/hardware-agent
status, and measurement freshness. Before a targeted restart it rechecks
transient backend failures and records container state and recent logs. Restarts
are bounded by per-service cooldown and a shared hourly budget. The watchdog
requires `/var/run/docker.sock`; this grants host-level Docker control and is an
explicit deployment tradeoff inherited from VENTI.

## ntfy notification transport

DISTI includes a fire-and-forget ntfy transport for future application events;
it is not connected to alarms or hardware acquisition. Set
`DISTI_NTFY_ENABLED=true`, `DISTI_NTFY_BASE_URL`, and a private
`DISTI_NTFY_TOPIC` in the device-local `disti.env`, then restart the API. To
send a manual test from the running stack, use:

```sh
docker compose exec api python -c "from disti.notifications import send_notification; send_notification('DISTI test', 'Notification transport is working')"
```

Delivery runs in a daemon thread with a finite network timeout. Missing
configuration and delivery failures are logged without interrupting callers.
