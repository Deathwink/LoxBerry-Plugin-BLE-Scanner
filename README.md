# BLE Scanner MQTT per LoxBerry 4

Plugin LoxBerry 4 per rilevare advertising Bluetooth Low Energy con BlueZ e pubblicarli sul MQTT Gateway integrato.

## Caratteristiche

- Python 3 in un virtualenv privato; nessuna dipendenza Python 2.
- Scansione BLE tramite `bleak`/D-Bus e `bluez`.
- Broker, porta e credenziali letti automaticamente da `config/system/general.json`.
- Filtri per MAC, nome (regex) e RSSI minimo.
- Esclusione dei singoli MAC direttamente dalla lista dei dispositivi rilevati nella WebUI.
- Presenza con timeout configurabile.
- Payload JSON con nome, RSSI, TX power, UUID, manufacturer data e service data.
- Decoder Govee completo tramite la libreria `govee-ble` usata da Home Assistant.
- WebUI LoxBerry con configurazione, stato e log.

## Installazione

1. Configurare e abilitare il MQTT Gateway di LoxBerry.
2. Eseguire `./build.sh` oppure usare lo ZIP presente in `dist/`.
3. Caricare lo ZIP da **Gestione plugin → Installa plugin**.
4. Riavviare LoxBerry quando richiesto, aprire **BLE Scanner MQTT** e salvare i filtri desiderati.

L'installazione richiede accesso Internet per installare nel virtualenv `bleak==0.22.3` e `paho-mqtt==2.1.0`.

## Topic MQTT

Con topic base predefinito `loxberry/ble_scanner`:

| Topic | Contenuto | Retained |
| --- | --- | --- |
| `loxberry/ble_scanner/availability` | `online` / `offline` | sì |
| `loxberry/ble_scanner/events` | ultimo advertising in JSON | no |
| `.../device/aa_bb_cc_dd_ee_ff/json` | dati completi del dispositivo | sì |
| `.../device/aa_bb_cc_dd_ee_ff/rssi` | RSSI numerico in dBm | sì |
| `.../device/aa_bb_cc_dd_ee_ff/presence` | `1` presente, `0` assente | sì |
| `.../device/aa_bb_cc_dd_ee_ff/temperature` | temperatura decodificata in °C | sì |
| `.../device/aa_bb_cc_dd_ee_ff/humidity` | umidità relativa decodificata in % | sì |
| `.../device/aa_bb_cc_dd_ee_ff/battery` | batteria decodificata in % | sì |

I byte in manufacturer/service data sono rappresentati in esadecimale per produrre JSON stabile e trasportabile.

## Decoder Govee

Il plugin usa `govee-ble==1.2.0`, lo stesso parser dell'integrazione ufficiale Home Assistant. Supporta termometri, igrometri, sensori con sonde multiple, PM2.5, CO₂, movimento, presenza, porta/finestra, vibrazione, pressione e pulsanti Govee riconosciuti dalla libreria.

Il JSON del dispositivo riceve un oggetto `decoded` organizzato in valori numerici, valori binari ed eventi:

```json
{"decoder":"govee_ble","model":"H5075","device_name":"H5075 002B","values":{"temperature":{"value":33.0,"name":"Temperature","unit":"°C"},"humidity":{"value":48.4,"name":"Humidity","unit":"%"},"battery":{"value":100,"name":"Battery","unit":"%"}},"binary_values":{},"events":{}}
```

Ogni elemento di `values` e `binary_values` viene pubblicato automaticamente come topic retained sotto il dispositivo. Gli eventi vengono pubblicati senza retain sotto `event/<nome>`, per evitare di riprodurre pressioni di pulsanti o rilevamenti di movimento ormai trascorsi.

## Diagnostica

```sh
bluetoothctl show
systemctl status bluetooth
```

Se non compare un controller, verificare adattatore USB, passthrough (in VM) e blocchi RF con `rfkill`.

`pluginconfig.json` (inclusi i MAC esclusi) e `devices.json` vengono salvati e ripristinati dagli script di aggiornamento del plugin. La configurazione predefinita viene creata dal daemon solamente quando il file non esiste, evitando che un'installazione o un aggiornamento sovrascriva le scelte dell'utente. Il virtualenv è conservato nella directory privata `bin` del plugin, così il `postinstall` non deve scrivere nella directory di configurazione che potrebbe provenire da una versione precedente.
