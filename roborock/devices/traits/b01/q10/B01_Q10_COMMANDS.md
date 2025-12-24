## Roborock Q10 (B01/Q10) DP command reference

This document is derived from the Roborock Android app Hermes dump under:

- `RR_API\hermes\no_package\Roborock Q10 Series\output\module_940.js` (Q10 command implementations)
- `RR_API\hermes\no_package\Roborock Q10 Series\output\module_981.js` (DP id mapping / `YXCommonDP`)

It documents the **command functions** the app calls, which DP they write, and the **expected value/params shape** as implied by the app.
This is AI generated and not all data may be fully accurate but it is grounded with some reverse engineered code.
## Transport / payload model

Q10-series devices in this dump are controlled by **publishing DP updates** via `RRDevice.deviceIOT.publishDps(...)`.

Two patterns appear:

- **Direct DP write**: publish `{ <dpId>: <value> }` (the app uses `sendCmdWithDp(dpId, value)`).
- **Public command wrapper**: publish `{ dpCommon(101): { <dpId>: <value> } }` (the app uses `sendPublicCmd({ <dpId>: <value> })`).

## Common enumerations

These enums come from `python-roborock/roborock/data/b01_q10/b01_q10_code_mappings.py` and match what the app UI exposes:

### `YXFanLevel`

- **UNKNOWN**: `-1` (`unknown`)
- **CLOSE**: `0` (`close`)
- **QUITE**: `1` (`quite`)
- **NORMAL**: `2` (`normal`)
- **STRONG**: `3` (`strong`)
- **MAX**: `4` (`max`)
- **SUPER**: `5` (`super`)

### `YXWaterLevel`

- **UNKNOWN**: `-1` (`unknown`)
- **CLOSE**: `0` (`close`)
- **LOW**: `1` (`low`)
- **MIDDLE**: `2` (`middle`)
- **HIGH**: `3` (`high`)

### `YXCleanLine`

- **FAST**: `0` (`fast`)
- **DAILY**: `1` (`daily`)
- **FINE**: `2` (`fine`)

### `YXRoomMaterial`

- **HORIZONTAL_FLOOR_BOARD**: `0` (`horizontalfloorboard`)
- **VERTICAL_FLOOR_BOARD**: `1` (`verticalfloorboard`)
- **CERAMIC_TILE**: `2` (`ceramictile`)
- **OTHER**: `255` (`other`)

### `YXCleanType`

- **UNKNOWN**: `-1` (`unknown`)
- **BOTH_WORK**: `1` (`bothwork`)
- **ONLY_SWEEP**: `2` (`onlysweep`)
- **ONLY_MOP**: `3` (`onlymop`)

### `YXDeviceState`

- **UNKNOWN**: `-1` (`unknown`)
- **SLEEP_STATE**: `2` (`sleepstate`)
- **STANDBY_STATE**: `3` (`standbystate`)
- **CLEANING_STATE**: `5` (`cleaningstate`)
- **TO_CHARGE_STATE**: `6` (`tochargestate`)
- **REMOTEING_STATE**: `7` (`remoteingstate`)
- **CHARGING_STATE**: `8` (`chargingstate`)
- **PAUSE_STATE**: `10` (`pausestate`)
- **FAULT_STATE**: `12` (`faultstate`)
- **UPGRADE_STATE**: `14` (`upgradestate`)
- **DUSTING**: `22` (`dusting`)
- **CREATING_MAP_STATE**: `29` (`creatingmapstate`)
- **MAP_SAVE_STATE**: `99` (`mapsavestate`)
- **RE_LOCATION_STATE**: `101` (`relocationstate`)
- **ROBOT_SWEEPING**: `102` (`robotsweeping`)
- **ROBOT_MOPING**: `103` (`robotmoping`)
- **ROBOT_SWEEP_AND_MOPING**: `104` (`robotsweepandmoping`)
- **ROBOT_TRANSITIONING**: `105` (`robottransitioning`)
- **ROBOT_WAIT_CHARGE**: `108` (`robotwaitcharge`)

### `YXBackType`

- **UNKNOWN**: `-1` (`unknown`)
- **IDLE**: `0` (`idle`)
- **BACK_DUSTING**: `4` (`backdusting`)
- **BACK_CHARGING**: `5` (`backcharging`)

### `YXDeviceWorkMode`

- **UNKNOWN**: `-1` (`unknown`)
- **BOTH_WORK**: `1` (`bothwork`)
- **ONLY_SWEEP**: `2` (`onlysweep`)
- **ONLY_MOP**: `3` (`onlymop`)
- **CUSTOMIZED**: `4` (`customized`)
- **SAVE_WORRY**: `5` (`saveworry`)
- **SWEEP_MOP**: `6` (`sweepmop`)

### `YXDeviceCleanTask`

- **UNKNOWN**: `-1` (`unknown`)
- **IDLE**: `0` (`idle`)
- **SMART**: `1` (`smart`)
- **ELECTORAL**: `2` (`electoral`)
- **DIVIDE_AREAS**: `3` (`divideareas`)
- **CREATING_MAP**: `4` (`creatingmap`)
- **PART**: `5` (`part`)

### `YXDeviceDustCollectionFrequency`

- **DAILY**: `0` (`daily`)
- **INTERVAL_15**: `15` (`interval_15`)
- **INTERVAL_30**: `30` (`interval_30`)
- **INTERVAL_45**: `45` (`interval_45`)
- **INTERVAL_60**: `60` (`interval_60`)

## Commands

Notes:

- Many methods take parameters; the Hermes decompiler replaces some argument names with placeholders. In this doc:
  - `<arg0>`, `<arg1>`, ... refer to the call arguments to the app-side function.
- Any command that serializes into `<base64_blob>` is a **binary blob** packed into bytes and then base64-encoded by the app before sending.

### `startClean`

- **Target DP**: `dpStartClean` (`201`)
- **Transport**: `sendCmdWithDp` (direct DP write)
- **Value / params**:

```json
{
  "cmd": 1
}
```

### `startElectoralClean`

- **Target DP**: `dpStartClean` (`201`)
- **Transport**: `sendCmdWithDp` (direct DP write)
- **Value / params**:

```json
{
  "cmd": 2,
  "clean_paramters": <arg0>
}
```

### `fastCreateMap`

- **Target DP**: `dpStartClean` (`201`)
- **Transport**: `sendCmdWithDp` (direct DP write)
- **Value / params**:

```json
{
  "cmd": 4
}
```

### `continueClean`

- **Target DP**: `dpResume` (`205`)
- **Transport**: `sendCmdWithDp` (direct DP write)
- **Value / params**:
  - `0`

### `stopClean`

- **Target DP**: `dpStop` (`206`)
- **Transport**: `sendCmdWithDp` (direct DP write)
- **Value / params**:
  - `0`

### `partClean`

- **Target DP**: `dpStartClean` (`201`)
- **Transport**: `sendCmdWithDp` (direct DP write)
- **Value / params**:

```json
{
  "cmd": 5
}
```

### `goCharge`

- **Target DP**: `dpStartBack` (`202`)
- **Transport**: `sendCmdWithDp` (direct DP write)
- **Value / params**:
  - `5`

### `pause`

- **Target DP**: `dpPause` (`204`)
- **Transport**: `sendCmdWithDp` (direct DP write)
- **Value / params**:
  - `0`

### `setFunSuction`

- **Target DP**: `dpfunLevel` (`123`)
- **Transport**: `sendCmdWithDp` (direct DP write)
- **Value / params**:
  - `r1`
- **Notes**:
  - Value is converted via `toFunLevelNumber(...)` before sending.

### `setWaterLevel`

- **Target DP**: `dpWaterLevel` (`124`)
- **Transport**: `sendCmdWithDp` (direct DP write)
- **Value / params**:
  - `<arg0>`

### `setCleanCount`

- **Target DP**: `dpCleanCount` (`136`)
- **Transport**: `sendCmdWithDp` (direct DP write)
- **Value / params**:
  - `<arg0>`

### `setCleaningPreferences`

- **Target DP**: `dpCleanMode` (`137`)
- **Transport**: `sendCmdWithDp` (direct DP write)
- **Value / params**:
  - `<arg0>`

### `seekDevice`

- **Target DP**: `dpSeek` (`11`)
- **Transport**: `sendPublicCmd` (wrapped through `dpCommon` / DP 101)
- **Value / params**:
  - `<see module_940.js section>`

### `remoteTurnLeft`

- **Target DP**: `dpRemote` (`12`)
- **Transport**: `sendPublicCmd` (wrapped through `dpCommon` / DP 101)
- **Value / params**:
  - `<see module_940.js section>`

### `remoteTurnRight`

- **Target DP**: `dpRemote` (`12`)
- **Transport**: `sendPublicCmd` (wrapped through `dpCommon` / DP 101)
- **Value / params**:
  - `<see module_940.js section>`

### `remoteForward`

- **Target DP**: `dpRemote` (`12`)
- **Transport**: `sendPublicCmd` (wrapped through `dpCommon` / DP 101)
- **Value / params**:
  - `<see module_940.js section>`

### `remoteStop`

- **Target DP**: `dpRemote` (`12`)
- **Transport**: `sendPublicCmd` (wrapped through `dpCommon` / DP 101)
- **Value / params**:
  - `<see module_940.js section>`

### `remoteExit`

- **Target DP**: `dpRemote` (`12`)
- **Transport**: `sendPublicCmd` (wrapped through `dpCommon` / DP 101)
- **Value / params**:
  - `<see module_940.js section>`

### `resetMap`

- **Target DP**: `dpMapReset` (`13`)
- **Transport**: `sendPublicCmd` (wrapped through `dpCommon` / DP 101)
- **Value / params**:
  - `<see module_940.js section>`

### `resetSideBrush`

- **Target DP**: `dpResetSideBrush` (`18`)
- **Transport**: `sendPublicCmd` (wrapped through `dpCommon` / DP 101)
- **Value / params**:
  - `<see module_940.js section>`

### `resetMainBrush`

- **Target DP**: `dpResetMainBrush` (`20`)
- **Transport**: `sendPublicCmd` (wrapped through `dpCommon` / DP 101)
- **Value / params**:
  - `<see module_940.js section>`

### `resetFilterBrush`

- **Target DP**: `dpResetFilter` (`22`)
- **Transport**: `sendPublicCmd` (wrapped through `dpCommon` / DP 101)
- **Value / params**:
  - `<see module_940.js section>`

### `resetSensor`

- **Target DP**: `dpResetSensor` (`68`)
- **Transport**: `sendPublicCmd` (wrapped through `dpCommon` / DP 101)
- **Value / params**:
  - `<see module_940.js section>`

### `resetRag`

- **Target DP**: `dpResetRagLife` (`24`)
- **Transport**: `sendPublicCmd` (wrapped through `dpCommon` / DP 101)
- **Value / params**:
  - `<see module_940.js section>`

### `notDisturbSwitch`

- **Target DP**: `dpNotDisturb` (`25`)
- **Transport**: `sendPublicCmd` (wrapped through `dpCommon` / DP 101)
- **Value / params**:
  - `<see module_940.js section>`

### `requsetNotDisturbData`

- **Target DP**: `dpRequsetNotDisturbData` (`75`)
- **Transport**: `sendPublicCmd` (wrapped through `dpCommon` / DP 101)
- **Value / params**:
  - `<see module_940.js section>`

### `volumeSet`

- **Target DP**: `dpVolume` (`26`)
- **Transport**: `sendPublicCmd` (wrapped through `dpCommon` / DP 101)
- **Value / params**:
  - `<see module_940.js section>`

### `breakCleanSwitch`

- **Target DP**: `dpBeakClean` (`27`)
- **Transport**: `sendPublicCmd` (wrapped through `dpCommon` / DP 101)
- **Value / params**:
  - `<see module_940.js section>`

### `requestCleanRecordList`

- **Target DP**: `dpCleanRecord` (`52`)
- **Transport**: `sendPublicCmd` (wrapped through `dpCommon` / DP 101)
- **Value / params**:
  - `<see module_940.js section>`

### `requestCleanRecordDetail`

- **Target DP**: `dpCleanRecord` (`52`)
- **Transport**: `sendPublicCmd` (wrapped through `dpCommon` / DP 101)
- **Value / params**:
  - `<see module_940.js section>`

### `requestRemoveCleanRecord`

- **Target DP**: `dpCleanRecord` (`52`)
- **Transport**: `sendPublicCmd` (wrapped through `dpCommon` / DP 101)
- **Value / params**:
  - `<see module_940.js section>`

### `setVirtualWalls`

- **Target DP**: `dpVirtualWall` (`56`)
- **Transport**: `sendPublicCmd` (wrapped through `dpCommon` / DP 101)
- **Value / params**:
  - `<base64_blob>`
- **Notes**:
  - Payload is a base64-encoded binary blob (built from a `Uint8Array`, then `fromByteArray(...)`).
  - Uses `.points` with `{x, y}` entries; coordinates are multiplied by 10 before packing into 2 bytes.

### `setForbiddenAreas`

- **Target DP**: `dpRestrictedZone` (`54`)
- **Transport**: `sendPublicCmd` (wrapped through `dpCommon` / DP 101)
- **Value / params**:
  - `<base64_blob>`
- **Notes**:
  - Payload is a base64-encoded binary blob (built from a `Uint8Array`, then `fromByteArray(...)`).
  - Uses `.points` with `{x, y}` entries; coordinates are multiplied by 10 before packing into 2 bytes.
  - Uses `.oriModel` (seen fields: `.type`, `.name`).

### `setAreaClean`

- **Target DP**: `dpStartClean` (`201`)
- **Transport**: `sendPublicCmd` (wrapped through `dpCommon` / DP 101)
- **Value / params**:
  - `<base64_blob>`
- **Notes**:
  - Payload is a base64-encoded binary blob (built from a `Uint8Array`, then `fromByteArray(...)`).
  - Uses `.points` with `{x, y}` entries; coordinates are multiplied by 10 before packing into 2 bytes.
  - Uses `.oriModel` (seen fields: `.type`, `.name`).

### `requestAllDps`

- **Target DP**: `dpRequetdps` (`102`)
- **Transport**: `sendCmdWithDp` (direct DP write)
- **Value / params**:
  - `1`

### `autoSaveMapSwitch`

- **Target DP**: `dpMapSaveSwitch` (`51`)
- **Transport**: `sendPublicCmd` (wrapped through `dpCommon` / DP 101)
- **Value / params**:
  - `<see module_940.js section>`

### `enableMultiMap`

- **Target DP**: `dpMultiMapSwitch` (`60`)
- **Transport**: `sendPublicCmd` (wrapped through `dpCommon` / DP 101)
- **Value / params**:
  - `<see module_940.js section>`
- **Device support**:
  - Requires multi-map support enabled on the device.

### `saveMultiMap`

- **Target DP**: `dpMultiMap` (`61`)
- **Transport**: `sendPublicCmd` (wrapped through `dpCommon` / DP 101)
- **Value / params**:
  - `<see module_940.js section>`
- **Device support**:
  - Requires multi-map support enabled on the device.

### `requestMultiMapList`

- **Target DP**: `dpMultiMap` (`61`)
- **Transport**: `sendPublicCmd` (wrapped through `dpCommon` / DP 101)
- **Value / params**:
  - `<see module_940.js section>`
- **Device support**:
  - Requires multi-map support enabled on the device.

### `requestMultiMapDetail`

- **Target DP**: `dpMultiMap` (`61`)
- **Transport**: `sendPublicCmd` (wrapped through `dpCommon` / DP 101)
- **Value / params**:
  - `<see module_940.js section>`
- **Device support**:
  - Requires multi-map support enabled on the device.

### `deleteMultiMap`

- **Target DP**: `dpMultiMap` (`61`)
- **Transport**: `sendPublicCmd` (wrapped through `dpCommon` / DP 101)
- **Value / params**:
  - `<see module_940.js section>`
- **Device support**:
  - Requires multi-map support enabled on the device.

### `useMultiMap`

- **Target DP**: `dpMultiMap` (`61`)
- **Transport**: `sendPublicCmd` (wrapped through `dpCommon` / DP 101)
- **Value / params**:
  - `<see module_940.js section>`
- **Device support**:
  - Requires multi-map support enabled on the device.

### `renameMultiMap`

- **Target DP**: `dpMultiMap` (`61`)
- **Transport**: `sendPublicCmd` (wrapped through `dpCommon` / DP 101)
- **Value / params**:
  - `<see module_940.js section>`
- **Device support**:
  - Requires multi-map support enabled on the device.

### `getCarpetList`

- **Target DP**: `dpGetCarpet` (`64`)
- **Transport**: `sendPublicCmd` (wrapped through `dpCommon` / DP 101)
- **Value / params**:
  - `<see module_940.js section>`
- **Device support**:
  - Requires carpet recognition / carpet config support.

### `saveCarpet`

- **Target DP**: `dpGetCarpet` (`64`)
- **Transport**: `sendPublicCmd` (wrapped through `dpCommon` / DP 101)
- **Value / params**:
  - `<see module_940.js section>`
- **Device support**:
  - Requires carpet recognition / carpet config support.

### `getSelfIdentifyingCarpetList`

- **Target DP**: `dpSelfIdentifyingCarpet` (`66`)
- **Transport**: `sendPublicCmd` (wrapped through `dpCommon` / DP 101)
- **Value / params**:
  - `<see module_940.js section>`
- **Device support**:
  - Requires carpet recognition / carpet config support.

### `saveSelfIdentifyingCarpet`

- **Target DP**: `dpSelfIdentifyingCarpet` (`66`)
- **Transport**: `sendPublicCmd` (wrapped through `dpCommon` / DP 101)
- **Value / params**:
  - `<see module_940.js section>`
- **Device support**:
  - Requires carpet recognition / carpet config support.

### `requestCustomerClean`

- **Target DP**: `dpCustomerCleanRequest` (`63`)
- **Transport**: `sendPublicCmd` (wrapped through `dpCommon` / DP 101)
- **Value / params**:
  - `<see module_940.js section>`

### `setCustomerClean`

- **Target DP**: `dpCustomerClean` (`62`)
- **Transport**: `sendPublicCmd` (wrapped through `dpCommon` / DP 101)
- **Value / params**:
  - `<base64_blob>`
- **Notes**:
  - Payload is a base64-encoded binary blob (built from a `Uint8Array`, then `fromByteArray(...)`).
  - References room ids.

### `setNotDisturb`

- **Target DP**: `dpNotDisturbData` (`33`)
- **Transport**: `sendPublicCmd` (wrapped through `dpCommon` / DP 101)
- **Value / params**:
  - `<base64_blob>`
- **Notes**:
  - Payload is a base64-encoded binary blob (built from a `Uint8Array`, then `fromByteArray(...)`).

### `dustSwitch`

- **Target DP**: `dpDustSwitch` (`37`)
- **Transport**: `sendPublicCmd` (wrapped through `dpCommon` / DP 101)
- **Value / params**:
  - `<see module_940.js section>`
- **Device support**:
  - Likely requires an auto-empty dock / dust collection hardware.

### `dustSetting`

- **Target DP**: (not detected)
- **Transport**: `sendPublicCmd` (wrapped through `dpCommon` / DP 101)
- **Value / params**:
  - `<see module_940.js section>`
- **Device support**:
  - Likely requires an auto-empty dock / dust collection hardware.

### `valleyPointChargingSwitch`

- **Target DP**: `dpValleyPointCharging` (`105`)
- **Transport**: `sendPublicCmd` (wrapped through `dpCommon` / DP 101)
- **Value / params**:
  - `<see module_940.js section>`

### `setValleyPointChargingSetting`

- **Target DP**: `dpValleyPointChargingDataUp` (`106`)
- **Transport**: `sendPublicCmd` (wrapped through `dpCommon` / DP 101)
- **Value / params**:
  - `<base64_blob>`
- **Notes**:
  - Payload is a base64-encoded binary blob (built from a `Uint8Array`, then `fromByteArray(...)`).
- **Device support**:
  - Only available if the device firmware supports valley/off-peak charging.

### `requestTimer`

- **Target DP**: `dpRequestTimer` (`69`)
- **Transport**: `sendPublicCmd` (wrapped through `dpCommon` / DP 101)
- **Value / params**:
  - `<see module_940.js section>`

### `createTimer`

- **Target DP**: `dpTimer` (`32`)
- **Transport**: `sendPublicCmd` (wrapped through `dpCommon` / DP 101)
- **Value / params**:
  - `<base64_blob>`
- **Notes**:
  - Payload is a base64-encoded binary blob (built from a `Uint8Array`, then `fromByteArray(...)`).

### `editTimer`

- **Target DP**: `dpTimer` (`32`)
- **Transport**: `sendPublicCmd` (wrapped through `dpCommon` / DP 101)
- **Value / params**:
  - `<base64_blob>`
- **Notes**:
  - Payload is a base64-encoded binary blob (built from a `Uint8Array`, then `fromByteArray(...)`).

### `removeTimer`

- **Target DP**: `dpTimer` (`32`)
- **Transport**: `sendPublicCmd` (wrapped through `dpCommon` / DP 101)
- **Value / params**:
  - `<base64_blob>`
- **Notes**:
  - Payload is a base64-encoded binary blob (built from a `Uint8Array`, then `fromByteArray(...)`).

### `timerSwitch`

- **Target DP**: `dpTimer` (`32`)
- **Transport**: `sendPublicCmd` (wrapped through `dpCommon` / DP 101)
- **Value / params**:
  - `<base64_blob>`
- **Notes**:
  - Payload is a base64-encoded binary blob (built from a `Uint8Array`, then `fromByteArray(...)`).

### `robotVoiceLanguageSetting`

- **Target DP**: `dpVoicePackage` (`35`)
- **Transport**: `sendPublicCmd` (wrapped through `dpCommon` / DP 101)
- **Value / params**:
  - `<base64_blob>`
- **Notes**:
  - Payload is a base64-encoded binary blob (built from a `Uint8Array`, then `fromByteArray(...)`).

### `startDockTask`

- **Target DP**: `dpStartDockTask` (`203`)
- **Transport**: `sendCmdWithDp` (direct DP write)
- **Value / params**:
  - `<arg0>`

### `roomMerge`

- **Target DP**: `dpRoomMerge` (`72`)
- **Transport**: `sendPublicCmd` (wrapped through `dpCommon` / DP 101)
- **Value / params**:
  - `<base64_blob>`
- **Notes**:
  - Payload is a base64-encoded binary blob (built from a `Uint8Array`, then `fromByteArray(...)`).

### `roomSplit`

- **Target DP**: `dpRoomSplit` (`73`)
- **Transport**: `sendPublicCmd` (wrapped through `dpCommon` / DP 101)
- **Value / params**:
  - `<base64_blob>`
- **Notes**:
  - Payload is a base64-encoded binary blob (built from a `Uint8Array`, then `fromByteArray(...)`).

### `resetRoomName`

- **Target DP**: `dpResetRoomName` (`74`)
- **Transport**: `sendPublicCmd` (wrapped through `dpCommon` / DP 101)
- **Value / params**:
  - `<base64_blob>`
- **Notes**:
  - Payload is a base64-encoded binary blob (built from a `Uint8Array`, then `fromByteArray(...)`).
  - References room ids.

### `resetOneRoomName`

- **Target DP**: `dpResetRoomName` (`74`)
- **Transport**: `sendPublicCmd` (wrapped through `dpCommon` / DP 101)
- **Value / params**:
  - `<base64_blob>`
- **Notes**:
  - Payload is a base64-encoded binary blob (built from a `Uint8Array`, then `fromByteArray(...)`).

### `getRemoveZonedList`

- **Target DP**: `dpRemoveZoned` (`70`)
- **Transport**: `sendPublicCmd` (wrapped through `dpCommon` / DP 101)
- **Value / params**:
  - `<see module_940.js section>`

### `saveRemoveZoned`

- **Target DP**: `dpRemoveZoned` (`70`)
- **Transport**: `sendPublicCmd` (wrapped through `dpCommon` / DP 101)
- **Value / params**:
  - `<see module_940.js section>`

### `setCarpetCleanType`

- **Target DP**: `dpCarpetCleanType` (`76`)
- **Transport**: `sendPublicCmd` (wrapped through `dpCommon` / DP 101)
- **Value / params**:
  - `<see module_940.js section>`
- **Device support**:
  - Requires carpet recognition / carpet config support.

### `setButtonLightSwitch`

- **Target DP**: `dpButtonLightSwitch` (`77`)
- **Transport**: `sendPublicCmd` (wrapped through `dpCommon` / DP 101)
- **Value / params**:
  - `<see module_940.js section>`

### `setCleanLine`

- **Target DP**: `dpCleanLine` (`78`)
- **Transport**: `sendPublicCmd` (wrapped through `dpCommon` / DP 101)
- **Value / params**:
  - `<see module_940.js section>`

### `setTimeZoneToRobot`

- **Target DP**: `dpTimeZone` (`79`)
- **Transport**: `sendPublicCmd` (wrapped through `dpCommon` / DP 101)
- **Value / params**:
  - `<see module_940.js section>`

### `setChildLockSwitch`

- **Target DP**: `dpChildLock` (`47`)
- **Transport**: `sendPublicCmd` (wrapped through `dpCommon` / DP 101)
- **Value / params**:
  - `<see module_940.js section>`

### `setAreaUnit`

- **Target DP**: `dpAreaUnit` (`80`)
- **Transport**: `sendPublicCmd` (wrapped through `dpCommon` / DP 101)
- **Value / params**:
  - `<see module_940.js section>`

### `setCleanOrder`

- **Target DP**: `dpCleanOrder` (`82`)
- **Transport**: `sendPublicCmd` (wrapped through `dpCommon` / DP 101)
- **Value / params**:
  - `<base64_blob>`
- **Notes**:
  - Payload is a base64-encoded binary blob (built from a `Uint8Array`, then `fromByteArray(...)`).

### `setRobotLog`

- **Target DP**: `dpLogSwitch` (`84`)
- **Transport**: `sendPublicCmd` (wrapped through `dpCommon` / DP 101)
- **Value / params**:
  - `<see module_940.js section>`

### `setFloorMaterial`

- **Target DP**: `dpFloorMaterial` (`85`)
- **Transport**: `sendPublicCmd` (wrapped through `dpCommon` / DP 101)
- **Value / params**:
  - `<base64_blob>`
- **Notes**:
  - Payload is a base64-encoded binary blob (built from a `Uint8Array`, then `fromByteArray(...)`).
  - References room ids.

### `setAutoBoostSwitch`

- **Target DP**: `dpAutoBoost` (`45`)
- **Transport**: `sendPublicCmd` (wrapped through `dpCommon` / DP 101)
- **Value / params**:
  - `<see module_940.js section>`

### `setLineLaserObstacleAvoidance`

- **Target DP**: `dpLineLaserObstacleAvoidance` (`86`)
- **Transport**: `sendPublicCmd` (wrapped through `dpCommon` / DP 101)
- **Value / params**:
  - `<see module_940.js section>`

### `setIgnoreObstacle`

- **Target DP**: `dpIgnoreObstacle` (`89`)
- **Transport**: `sendPublicCmd` (wrapped through `dpCommon` / DP 101)
- **Value / params**:
  - `<see module_940.js section>`

### `setLastCleanRecordReaded`

- **Target DP**: `dpRecendCleanRecord` (`53`)
- **Transport**: `sendPublicCmd` (wrapped through `dpCommon` / DP 101)
- **Value / params**:
  - `<see module_940.js section>`

### `setGroundCleanSwitch`

- **Target DP**: `dpGroundClean` (`88`)
- **Transport**: `sendPublicCmd` (wrapped through `dpCommon` / DP 101)
- **Value / params**:
  - `<see module_940.js section>`

### `requestMapAndPathData`

- **Target DP**: `dpRequest` (`16`)
- **Transport**: `sendPublicCmd` (wrapped through `dpCommon` / DP 101)
- **Value / params**:
  - `<see module_940.js section>`

### `setNotDisturbExpand`

- **Target DP**: `dpNotDisturbExpand` (`92`)
- **Transport**: `sendPublicCmd` (wrapped through `dpCommon` / DP 101)
- **Value / params**:
  - `<see module_940.js section>`

### `setDisturbLight`

- **Target DP**: `dpNotDisturbExpand` (`92`)
- **Transport**: `sendPublicCmd` (wrapped through `dpCommon` / DP 101)
- **Value / params**:
  - `<see module_940.js section>`

### `setDisturbVoice`

- **Target DP**: `dpNotDisturbExpand` (`92`)
- **Transport**: `sendPublicCmd` (wrapped through `dpCommon` / DP 101)
- **Value / params**:
  - `<see module_940.js section>`

### `setDisturbResumeClean`

- **Target DP**: `dpNotDisturbExpand` (`92`)
- **Transport**: `sendPublicCmd` (wrapped through `dpCommon` / DP 101)
- **Value / params**:
  - `<see module_940.js section>`

### `setDisturbDustEnable`

- **Target DP**: `dpNotDisturbExpand` (`92`)
- **Transport**: `sendPublicCmd` (wrapped through `dpCommon` / DP 101)
- **Value / params**:
  - `<see module_940.js section>`
- **Device support**:
  - Likely requires an auto-empty dock / dust collection hardware.

### `setAddCleanArea`

- **Target DP**: `dpAddCleanArea` (`95`)
- **Transport**: `sendPublicCmd` (wrapped through `dpCommon` / DP 101)
- **Value / params**:
  - `<base64_blob>`
- **Notes**:
  - Payload is a base64-encoded binary blob (built from a `Uint8Array`, then `fromByteArray(...)`).
  - Uses `.points` with `{x, y}` entries; coordinates are multiplied by 10 before packing into 2 bytes.
  - Uses `.oriModel` (seen fields: `.type`, `.name`).

### `setRestrictedArea`

- **Target DP**: `dpRestrictedArea` (`97`)
- **Transport**: `sendPublicCmd` (wrapped through `dpCommon` / DP 101)
- **Value / params**:
  - `<see module_940.js section>`

### `setSuspectedThreshold`

- **Target DP**: `dpSuspectedThreshold` (`99`)
- **Transport**: `sendPublicCmd` (wrapped through `dpCommon` / DP 101)
- **Value / params**:
  - `<see module_940.js section>`

### `jumpClean`

- **Target DP**: `dpJumpScan` (`101`)
- **Transport**: `sendPublicCmd` (wrapped through `dpCommon` / DP 101)
- **Value / params**:
  - `<see module_940.js section>`

### `sendUserPlan`

- **Target DP**: `dpUserPlan` (`207`)
- **Transport**: `sendCmdWithDp` (direct DP write)
- **Value / params**:
  - `<arg0>`

### `setCliffRestrictedArea`

- **Target DP**: `dpCliffRestrictedArea` (`102`)
- **Transport**: `sendPublicCmd` (wrapped through `dpCommon` / DP 101)
- **Value / params**:
  - `<see module_940.js section>`

### `getValleyPointChargingData`

- **Target DP**: `dpValleyPointChargingData` (`107`)
- **Transport**: `sendPublicCmd` (wrapped through `dpCommon` / DP 101)
- **Value / params**:
  - `<see module_940.js section>`
- **Device support**:
  - Only available if the device firmware supports valley/off-peak charging.

### `heartbeat`

- **Target DP**: `dpHeartbeat` (`110`)
- **Transport**: `sendPublicCmd` (wrapped through `dpCommon` / DP 101)
- **Value / params**:
  - `<see module_940.js section>`
