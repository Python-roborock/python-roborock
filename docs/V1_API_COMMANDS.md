# Api commands

This page is still under construction. All of the following are the commands we have reverse engineered. It is not an exhaustive list of all the possible commands.

Commands do not immediately make it to this page. You can find more commands [here](https://github.com/Python-roborock/python-roborock/blob/main/roborock/roborock_typing.py#L18)

Commands can have multiple parameters that can change from one model to another.

* [app_charge](#app_charge)
* [app_get_dryer_setting](#app_get_dryer_setting)
* [app_get_init_status](#app_get_init_status)
* [app_pause](#app_pause)
* [app_rc_end](#app_rc_end)
* [app_rc_move](#app_rc_move)
* [app_rc_start](#app_rc_start)
* [app_rc_stop](#app_rc_stop)
* [app_segment_clean](#app_segment_clean)
* [app_set_dryer_setting](#app_set_dryer_setting)
* [app_start_collect_dust](#app_start_collect_dust)
* [app_start_wash](#app_start_wash)
* [app_start](#app_start)
* [app_stop_collect_dust](#app_stop_collect_dust)
* [app_stop_wash](#app_stop_wash)
* [app_stop](#app_stop)
* [change_sound_volume](#change_sound_volume)
* [close_dnd_timer](#close_dnd_timer)
* [del_server_timer](#del_server_timer)
* [dnld_install_sound](#dnld_install_sound)
* [get_clean_sequence](#get_clean_sequence)
* [get_consumable](#get_consumable)
* [get_custom_mode](#get_custom_mode)
* [get_customize_clean_mode](#get_customize_clean_mode)
* [get_dnd_timer](#get_dnd_timer)
* [get_dust_collection_mode](#get_dust_collection_mode)
* [get_clean_follow_ground_material_status](#get_clean_follow_ground_material_status)
* [get_identify_furniture_status](#get_identify_furniture_status)
* [get_identify_ground_material_status](#get_identify_ground_material_status)
* [get_led_status](#get_led_status)
* [get_map_v1](#get_map_v1)
* [get_multi_map](#get_multi_map)
* [get_multi_maps_list](#get_multi_maps_list)
* [get_network_info](#get_network_info)
* [get_prop](#get_prop)
* [get_room_mapping](#get_room_mapping)
* [get_scenes_valid_tids](#get_scenes_valid_tids)
* [get_serial_number](#get_serial_number)
* [get_smart_wash_params](#get_smart_wash_params)
* [get_sound_progress](#get_sound_progress)
* [get_status](#get_status)
* [get_timezone](#get_timezone)
* [get_turn_server](#get_turn_server)
* [get_valley_electricity_timer](#get_valley_electricity_timer)
* [get_wash_towel_mode](#get_wash_towel_mode)
* [load_multi_map](#load_multi_map)
* [name_segment](#name_segment)
* [reset_consumable](#reset_consumable)
* [resume_segment_clean](#resume_segment_clean)
* [resume_zoned_clean](#resume_zoned_clean)
* [retry_request](#retry_request)
* [reunion_scenes](#reunion_scenes)
* [save_map](#save_map)
* [send_ice_to_robot](#send_ice_to_robot)
* [send_sdp_to_robot](#send_sdp_to_robot)
* [set_server_timer](#set_server_timer)
* [set_clean_motor_mode](#set_clean_motor_mode)
* [set_customize_clean_mode](#set_customize_clean_mode)
* [set_dnd_timer](#set_dnd_timer)
* [set_dust_collection_mode](#set_dust_collection_mode)
* [set_fds_endpoint](#set_fds_endpoint)
* [set_identify_furniture_status](#set_identify_furniture_status)
* [set_identify_ground_material_status](#set_identify_ground_material_status)
* [set_led_status](#set_led_status)
* [set_mop_mode](#set_mop_mode)
* [set_scenes_segments](#set_scenes_segments)
* [set_scenes_zones](#set_scenes_zones)
* [set_segment_ground_material](#set_segment_ground_material)
* [set_smart_wash_params](#set_smart_wash_params)
* [set_timezone](#set_timezone)
* [set_valley_electricity_timer](#set_valley_electricity_timer)
* [set_wash_towel_mode](#set_wash_towel_mode)
* [set_water_box_custom_mode](#set_water_box_custom_mode)
* [start_camera_preview](#start_camera_preview)
* [start_edit_map](#start_edit_map)
* [start_voice_chat](#start_voice_chat)
* [start_wash_then_charge](#start_wash_then_charge)
* [stop_camera_preview](#stop_camera_preview)
* [stop_segment_clean](#stop_segment_clean)
* [test_sound_volume](#test_sound_volume)
* [upd_server_timer](#upd_server_timer)


## Robot status

### get_status

Description: Returns the current status of the vacuum

Parameters: None

Returns:

    msg_ver:

    msg_seq:

    state:

    battery: Battery level of your device.

    clean_time: Total clean time in hours.

    clean_area: Total clean area in meters.

    error_code:

    map_reset:

    in_cleaning:

    in_returning:

    in_fresh_state:

    lab_status:

    water_box_status:

    back_type:

    wash_phase:

    wash_ready:

    fan_power:

    dnd_enabled:

    map_status:

    is_locating:

    lock_status:

    water_box_mode:

    water_box_carriage_status:

    mop_forbidden_enable:

    camera_status:

    is_exploring:

    home_sec_status:

    home_sec_enable_password:

    adbumper_status:

    water_shortage_status:

    dock_type:

    dust_collection_status:

    auto_dust_collection:

    avoid_count:

    mop_mode:

    debug_mode:

    collision_avoid_status:

    switch_map_mode:

    dock_error_status:

    charge_status:

    unsave_map_reason:

    unsave_map_flag:

**Supported devices:**

* Roborock S7 MaxV Ultra: ✅
* Roborock S8 Pro Ultra: ✅

## App vacuum control

### app_start

Description:

Parameters:

### app_pause

Description: This pauses the vacuum's current task

Parameters: None

Returns ok or error

**Supported devices:**

* Roborock S8 Pro Ultra: ✅

### app_stop

Description:

Parameters:


### app_start_collect_dust

Description: This empties the bin while docked

Parameters: None

**Supported devices:**

* Roborock S8 Pro Ultra: ✅

### app_stop_collect_dust

Description: This stops the emptying of the dust bin while docked

Parameters: None

**Supported devices:**

* Roborock S8 Pro Ultra: ✅

### app_start_wash

Description: This washes the mop while docked

Parameters: None

**Supported devices:**

* Roborock S8 Pro Ultra: ✅


### app_stop_wash

Description: This stops washing the mop whiloe docked

Parameters: None

**Supported devices:**

* Roborock S8 Pro Ultra: ✅

### app_goto_target

Description: Got to target

Parameters:
    - X coordinate as integer (e.g.: 23450)
    - Y coordinate as integer (e.g.: 16450)

Returns ok or error

**Supported devices:**

* Roborock S8 Pro Ultra: ✅

### app_charge

Description: This tells your vacuum to go back to the dock and charge.

Parameters: None

Returns : ok or error

**Supported devices:**

* Roborock S7 MaxV Ultra: ✅
* Roborock S8 Pro Ultra: ✅


## App status

### app_get_init_status

Description: Returns details on the app being used to interact with Roborock servers ?? In this case  the app is backend supporting the HA integration ?

Parameters: None

Returns:

     local_info:

        name: Name of the app

        bom: Version of the app

        location: Location of the app

        language: Language of the app

        wifiplan: Wifi plan of the app

        timezone: Timezone of the app

        logserver: Log server of the app

        featureset: Featureset of the app

     feature_info: List of features

     new_feature_info: New feature info

Return example:
```json
    {'local_info': {'name': 'custom_A.03.0342_CE', 'bom': 'A.03.0342', 'location': 'de', 'language': 'en', 'wifiplan': '', 'timezone': 'Europe/Berlin', 'logserver': 'awsde0.fds.api.xiaomi.com', 'featureset': 3}, 'feature_info': [111, 112, 113, 114, 115, 116, 117, 118, 119, 120, 121, 122, 123, 124, 125], 'new_feature_info': 2247395306799103, 'new_feature_info_str': '00000008009EFFFE'}
```


**Supported devices:**

* Roborock S8 Pro Ultra: ✅

## App dryer settings

### app_get_dryer_setting

Description: Get dock dryer settings.

Parameters: None

Returns:

    status:

    on:

        cliff_on:

        cliff_off

        count:

        dry_time: Duration dryer remains on in seconds.

    off:

        cliff_on:

        cliff_off:

        count:

Return example:

```json
    {'status': 1, 'on': {'cliff_on': 1, 'cliff_off': 1, 'count': 10, 'dry_time': 7200}, 'off': {'cliff_on': 2, 'cliff_off': 1, 'count': 10}}
```

Source: Roborock S7 MaxV Ultra

**Supported devices:**

* Roborock S7 MaxV Ultra: ✅
* Roborock S8 Pro Ultra: ✅

### app_set_dryer_setting

Description: Set the time for the dryer to run

Parameters:  '{"status":1,"on":{"dry_time":14400}}'

dry_time is the time in seconds the dryer will run for

Returns ok or error


**Supported devices:**

* Roborock S8 Pro Ultra: ✅

## App remote control

### app_rc_start

Description: Starts remote control.

Parameters: None

Returns ok or error

**Supported devices:**

* Roborock S8 Pro Ultra: ✅


### app_rc_move

Description: Moves the robot in the direction specified

Parameters: To be documented

Returns ok or error

<!--
    Need to document the parameters - will need to explore the app to find out what they are
-->


### app_rc_stop

Description: Stops the remote control

Parameters: None

Returns ok or error

<!--
    Assume stop stops a move ?? Need to check
-->

### app_rc_end

Description: Ends the remote control task

Parameters:

Returns ok or error

**Supported devices:**

* Roborock S8 Pro Ultra: ✅



## App other

### app_set_smart_cliff_forbidden

Description:

Parameters:


### app_spot

Description:

Parameters:


### app_stat

Description: This returns the current status of the vacuum

Parameters: None

Returns: ok or error

**Supported devices:**

* Roborock S8 Pro Ultra: ✅

### app_wakeup_robot

Description:

Parameters:


### app_zoned_clean

Description: Starts a zone clean

Parameters:

<!--
    Us this the last known zone
-->

Returns: ok or error

**Supported devices:**

* Roborock S8 Pro Ultra: ✅

## Segments and Zones

### app_segment_clean

Description: This starts a segment clean and repeats it the number of times specified.

Parameters: An array of segments to clean. Each segment is an integer with the segment id and the number of times to clean it. For example, to clean segment 18 twice, the parameter would be

 `[{'segments': [18], 'repeat': 2}]`

<!-- Comment: The segment id can be obtained from the initial data returned on login -->

Command:
    `roborock -d command --device_id deviceIdRedacted --cmd app_segment_clean --params '[{"segments": [17,19], "repeat": 2}]'`

Returns ok or error

**Supported devices:**

* Roborock S8 Pro Ultra: ✅

### set_segment_ground_material

Description: Sets the groud material for the segment

Parameters: "{'data':[[22,3,0]]}"

Returns ok or error

### name_segment

Description:

Parameters: To be determined

<!--
    Need to work out parameter format
    Does this allow us to name a segment ?
-->


### resume_segment_clean

Description:

Parameters:

**Supported devices:**

* Roborock S8 Pro Ultra: ✅

### stop_segment_clean

Description:

Parameters:

**Supported devices:**

* Roborock S8 Pro Ultra: ✅

### set_scenes_zones

Description:

Parameters:

### set_scenes_segments

Description:

Parameters:


### get_scenes_valid_tids

Description: To be confirmed

Parameters: None

<!--
    Appears to be associated with rooms ??
-->

Returns:

```json
[{'tid': '1699679077347', 'map_flag': 0, 'segs': [{'sid': 24}, {'sid': 20}, {'sid': 22}, {'sid': 18}]}, {'tid': '1699679236553', 'map_flag': 0, 'segs': [{'sid': 24}, {'sid': 20}, {'sid': 22}]}, {'tid': '1699679386045', 'map_flag': 0, 'segs': [{'sid': 16}, {'sid': 19}, {'sid': 17}]}, {'tid': '1699679335823', 'map_flag': 0, 'segs': [{'sid': 19}, {'sid': 16}, {'sid': 17}]}]
```

**Supported devices:**

* Roborock S8 Pro Ultra: ✅

### resume_zoned_clean

Description:

Parameters:

### reunion_scenes

Description:

Parameters:

## Camera

### start_camera_preview

Description:

Parameters:

**Supported devices:**

* Roborock S8 Pro Ultra: ❌

### stop_camera_preview

Description:

Parameters:

**Supported devices:**

* Roborock S8 Pro Ultra: ❌

### get_camera_status

Description: Get camera status.

Parameters: None

Returns: 3457
         387 Roborock S8 Pro Ultra

Source: Roborock S7 MaxV Ultra


### set_camera_status

Description:

Parameters:



### start_voice_chat

Description:

Parameters:

**Supported devices:**

* Roborock S8 Pro Ultra: ❌


## Clean modes

### get_carpet_clean_mode

Description: Get carpet clean mode.

Parameters:

Returns:

    carpet_clean_mode: Enumeration for carpet clean mode.

Return example:

```json
    {'carpet_clean_mode': 3}
```

Source: Roborock S7 MaxV Ultra


### set_carpet_clean_mode

Description:

Parameters:

### get_carpet_mode

Description:

Parameters: None

Returns:

    enable:

    current_integral:

    current_high:

    current_low:

    stall_time:

Return example:

```json
    {'enable': 1, 'current_integral': 450, 'current_high': 500, 'current_low': 400, 'stall_time': 10}
```

**Supported devices:**

* Roborock S7 MaxV Ultra: ✅
* Roborock S8 Pro Ultra: ✅

### set_carpet_mode

Description:

Parameters:

### get_smart_wash_params

Description: Returns the smartwash parameters

Parameters: None

<!--
    Not clear what this does
-->

Returns:

        smart_wash: 0 is off, 1 is on

        wash_interval: The interval in seconds between washes

Example:

```json
{'smart_wash': 0, 'wash_interval': 1200}
```


**Supported devices:**

* Roborock S8 Pro Ultra: ✅

### set_smart_wash_params

Description: Sets the smartwash parameters

Parameters:

        smart_wash: 0 is off, 1 is on

        wash_interval: The interval in seconds between washes


`{'smart_wash': 0, 'wash_interval': 1200}`


**Supported devices:**

* Roborock S8 Pro Ultra: ✅

## Cleaning history

### get_clean_record

Description:

Parameters: To be determined


### get_clean_record_map

Description:

Parameters:


### get_clean_sequence

Description:

Parameters:


### get_clean_summary

Description: Get a summary of cleaning history.

Parameters: None

Returns:

    clean_time:

    clean_area:

    clean_count:

    dust_collection_count:

    records:

Return example:

```json
    {'clean_time': 568146, 'clean_area': 8816865000, 'clean_count': 178, 'dust_collection_count': 172, 'records': [1689740211, 1689555788, 1689259450, 1688999113, 1688852350, 1688693213, 1688692357, 1688614354, 1688613280, 1688606676, 1688325265, 1688174717, 1688149381, 1688092832, 1688001593, 1687921414, 1687890618, 1687743256, 1687655018, 1687631444]}
```

Source: Roborock S7 MaxV Ultra

**Supported devices:**

* Roborock S7 MaxV Ultra: ✅
* Roborock S8 Pro Ultra: ✅


### get_mop_template_params_summary

Description:

Parameters:

**Supported devices:**

* Roborock S8 Pro Ultra: ❌

## Child lock

### get_child_lock_status

Description: This gets the child lock status of the device. 0 is off, 1 is on.

Parameters: None

Returns:

    lock_status:

Return example:

```json
    {'lock_status': 0}
```

**Supported devices:**

* Roborock S8 Pro Ultra: ✅

### set_child_lock_status

Description: This sets the child lock status of the device.

Parameters: '{"lock_status" :0}'

Returns: ok

**Supported devices:**

* Roborock S8 Pro Ultra: ✅




## Consumables

### get_consumable

Description: This gets the status of all of the consumables for your device.

Parameters: None

Returns:

    main_brush_work_time: This is the amount of time the main brush has been used in seconds since it was last replaced

    side_brush_work_time:  This is the amount of time the side brush has been used in seconds since it was last replaced

    filter_work_time: This is the amount of time the air filter inside the vacuum has been used in seconds since it was last replaced

    filter_element_work_time:

    sensor_dirty_time: This is the amount of time since you have cleaned the sensors on the bottom of your vacuum.

    strainer_work_times:

    dust_collection_work_times:

    cleaning_brush_work_times:

Return examples:

```json
    {'main_brush_work_time': 14151, 'side_brush_work_time': 41638, 'filter_work_time': 14151, 'filter_element_work_time': 0, 'sensor_dirty_time': 41522, 'strainer_work_times': 44, 'dust_collection_work_times': 19, 'cleaning_brush_work_times': 44}
```


### reset_consumable

Description:

Parameters: List of consumables to reset. For example, to reset consumables 'strainer_work_times' and 'sensor_dirty_time' the parameter would be

 `['strainer_work_times', 'sensor_dirty_time']`

**Supported devices:**

* Roborock S7 MaxV Ultra: ✅
* Roborock S8 Pro Ultra: ✅


## Custom modes

### get_custom_mode

Description: It returns the current custom mode.

Parameters: None

Returns:

    integer value of the current custom mode

Return example:

```
    102
```

<!--
  Not clear what a custom mode is = will explore
-->

**Supported devices:**

* Roborock S7 MaxV Ultra: ✅
* Roborock S8 Pro Ultra: ✅

### set_custom_mode

Description: Set the fan speed (suction power). Used by `StatusTrait` on models that do not accept the fan speed in `set_clean_motor_mode`. See `set_clean_motor_mode` for the order the commands are sent in.

Parameters: Fan power code in a list, e.g. `[102]`. `105` (`VacuumModes.OFF`) turns the fan off for mop-only cleaning.

**Supported devices:**

* Roborock Saros 10R: ✅ (`[102]` from mop-only mode switches to vacuum and mop and resets route `301` to `300`)

### get_customize_clean_mode

Description:

Parameters:


### set_customize_clean_mode

Description:

Parameters:

## Furniture and ground material

### get_identify_furniture_status

Description:

Parameters:

<!--
    Does not return anything for S8 Pro Ultra when docked may require vacumm to be cleaning
-->

### set_identify_furniture_status

Description:

Parameters:

<!--
    Method not known for S8 Pro Ultra
-->


### get_identify_ground_material_status

Description:

Parameters:

<!--
    Does not return anything for S8 Pro Ultra when docked may require vacumm to be cleaning
-->


### set_identify_ground_material_status

Description:

Parameters:

<!--
    Method not known for S8 Pro Ultra
-->



## LEDs

### get_flow_led_status

Description:

Parameters:


### set_flow_led_status

Description:

Parameters:

### get_led_status

Description: Returns the LED status. If disabled the indicator light will turn off 1 minute after fully charged

Parameters:

Returns:

    led_status: 0 is off, 1 is on


**Supported devices:**

* Roborock S8 Pro Ultra: ✅

### set_led_status

Description:  Sets the LED status. If disabled the indicator light will turn off 1 minute after fully charged

Parameters: ????

<!--
    Need to work out parameter format
-->




## Maps

### get_multi_map

Description:

Parameters:

Comment: Response timed out for S8 Pro Ultra

<!--
    times out after 4 secs
-->

### get_multi_maps_list

Description: Returns a list of map information stored on the device.

Parameters: None required

Returns:

    max_multi_map:
    max_bak_map:
    multi_map_count:
    map_info:

            mapFlag:
            add_time:
            length:
            name:
            bak_maps:

                mapFlag:
                add_time:


Return example:

```json
    {'max_multi_map': 4, 'max_bak_map': 1, 'multi_map_count': 2, 'map_info': [{'mapFlag': 0, 'add_time': 1699919699, 'length': 4, 'name': 'Home', 'bak_maps': [{'mapFlag': 4, 'add_time': 1699823921}]}, {'mapFlag': 1, 'add_time': 1699828035, 'length': 13, 'name': 'Boys bathroom', 'bak_maps': [{'mapFlag': 5, 'add_time': 1699828035}]}]}
```

Source: S8 Pro Ultra

**Supported devices:**

* Roborock S8 Pro Ultra: ✅

### get_map_v1

Description: Returns the map

Parameters: Unknown

Comment: Returns a map in a format that is not yet understood by me

<!--
    Explore what parameters it may take
    Extend code to return byte stream ?
-->

### start_edit_map

Description:

Parameters:


### get_room_mapping

Description: Returns a list of rooms, ids as discovered by

Parameters: None

Returns:

    room_id

Return example:

```json
    [[16, '14731399', 12], [17, '2220009', 2], [18, '2219688', 12], [19, '2219685', 9], [20, '2219691', 12], [21, '2431758', 12], [22, '2219677', 13], [23, '2312548', 12], [24, '2219678', 14], [25, '2219686', 15], [26, '2219772', 12], [27, '14768755', 12]]
```

**Supported devices:**

* Roborock S7 MaxV Ultra: ✅
* Roborock S8 Pro Ultra: ✅

### load_multi_map

Description:

Parameters: number (the floor/map index)

<!--
    Need to work out parameter format
-->


### save_map

Description:

Parameters:

## Operating modes

### get_mop_mode

Description: Get mop mode.

Parameters: None

Returns: Enumeration for mop mode. 300

Example for S8 Pro Ultra:

    standard = 300
    deep = 301
    deep_plus = 303
    fast = 304
    custom = 302

**Supported devices:**

* Roborock S8 Pro Ultra: ✅

### set_mop_mode

Description: Set the mop route. Used by `StatusTrait` on models that do not accept `mop_mode` in `set_clean_motor_mode`. See `set_clean_motor_mode` for when it is sent.

Parameters: Mop route code in a list, e.g. `[300]`.

**Supported devices:**

* Roborock S8 Pro Ultra: ✅

### set_clean_motor_mode

Description: Set the fan speed, water mode and (on some models) mop route in one command. `StatusTrait.set_cleaning_mode`, `set_fan_speed`, `set_water_mode` and `set_mop_route` all apply a full set of codes (the settings they do not change keep their current values), and send the commands in the order the model needs (the lists were compared with the Roborock app):

| Model | Commands sent, in order |
| :--- | :--- |
| `is_shake_mop_set_supported` | `set_clean_motor_mode` with `fan_power`, `water_box_mode` and `mop_mode` (`mop_mode` only when a route is sent) |
| `is_set_clean_motor_mode_supported` (feature 118) | `set_clean_motor_mode` with `fan_power` and `water_box_mode`, then `set_mop_mode` when a route is sent |
| Devices without a mop (`is_support_water_mode` false) | `set_custom_mode` (fan) only, whatever the other flags say |
| Other models | `set_custom_mode` (fan), `set_water_box_custom_mode` (water), then `set_mop_mode` when a route is sent |

A mop route is sent only when the model supports both route setting (`is_clean_route_setting_supported`) and the shake module (`is_shake_mop_set_supported`), because only models with the shake module offer a route choice. Otherwise it is only sent to leave SmartPlan or custom mode: standard `300` is sent when the current route is `306` (SmartPlan) or `302` (custom) and the target mode is not the one that already owns that route (SmartPlan for `306`, custom for `302`), so the robot is not still reported in the mode it left. In every other case the route is not sent, so `set_fan_speed`, `set_water_mode` and `set_mop_route` never send `set_mop_mode` on models without the shake module. (The legacy `get_cleaning_mode_parameters` helper still adds `mop_mode` for every model with route setting.)

Parameters: List with a dictionary, e.g. `[{"fan_power": 102, "water_box_mode": 202}]`. `mop_mode` is added where the table says so.

`StatusTrait.supported_cleaning_settings` (helper `get_supported_settings`) lists the cleaning settings a model has at all, independent of the current cleaning mode, so a consumer can decide which settings to offer without combining feature flags. It is the set of settings that are adjustable in at least one regular cleaning mode: the fan speed always; the water mode when the model has a mop (`is_support_water_mode`); the mop route when the model has a mop and the shake module (`is_shake_mop_set_supported`) and either a mop-only mode (`is_pure_clean_mop_supported`) or the fast route outside mopping (`is_clean_route_fast_mode_supported` with route setting). The `fan_speed_options`/`water_mode_options`/`mop_route_options` lists and their `_mapping` dicts are empty for a setting the model does not have (the fan speed is never empty). The cleaning mode select has no entry in the set: it exists exactly when `cleaning_mode_options` is not empty, which is the case when `is_support_water_mode` is true. Whether a setting can be changed right now is still `is_fan_speed_adjustable`, `is_water_mode_adjustable` and `is_mop_route_adjustable`.

When the robot reports SmartPlan or custom codes (for example `106`/`204`/`302` or `110`/`209`/`306`) the adjustable, display and setter rules treat it as being in that mode, even if the model lacks the SmartPlan or custom support flags and `current_cleaning_mode` is therefore `None` (helper `get_reported_special_mode`). In that state the display options show only the SmartPlan or custom value, the settings are not adjustable and the setters raise `RoborockUnsupportedFeature`. `current_cleaning_mode` itself is unchanged.

`StatusTrait` setters: `set_fan_speed`, `set_water_mode` and `set_mop_route` only work when the matching `is_fan_speed_adjustable`, `is_water_mode_adjustable` or `is_mop_route_adjustable` is true, and only accept the values valid in the current cleaning mode, which are the same values that `fan_speed_display_options`, `water_mode_display_options` and `mop_route_display_options` list (`fan_speed_options`, `water_mode_options` and `mop_route_options` stay the model's full lists). SmartPlan, custom and unknown modes, and values that are not offered in the current mode, raise `RoborockUnsupportedFeature`; nothing is sent. They raise `RoborockException` when the status has not been loaded yet. Water slide codes `221`-`250` are accepted when the model supports water slide mode. After the commands succeed the local status fields are updated. Devices without a mop (`is_support_water_mode` false) have no water mode: `set_fan_speed` only needs the fan power loaded and sends only `set_custom_mode`.

The lists depend on the cleaning mode, following the mode tabs of the robot settings:

| Setting | Offered values |
|---|---|
| Fan speed | Not offered in mop-only mode (mop-only mode always sends fan code `105`). Max+ (`108`) only in vacuum-only mode with `is_max_plus_mode_supported`, never in vacuum and mop. On devices without mode tabs (`is_pure_clean_mop_supported` false) Max+ is offered in every mode with `is_none_pure_clean_mop_with_max_plus`. |
| Water mode | The model's list in every mode where it is offered, without `off` (`200`) when the device has a mop-only tab (`is_pure_clean_mop_supported`). Devices without a mop-only tab have one general tab: the water mode is adjustable in every regular mode, so a water-off state (classified as vacuum) can still turn the water on. |
| Mop route | Needs `is_shake_mop_set_supported`, and outside mop-only mode also `is_clean_route_fast_mode_supported` and `is_clean_route_setting_supported`. In vacuum and mop and in vacuum only only fast (`304`) and standard (`300`); in mop-only mode, and on devices without mode tabs, the model's full list. With `is_clean_efficiency_supported` the full list (which never contains deep, `301`) in every mode, with `is_none_pure_clean_mop_with_max_plus` fast and standard in every mode. |

Values left over from another tab (for example by an older client) are not sent on: `set_fan_speed`, `set_water_mode`, `set_mop_route` and `set_cleaning_mode` replace a fan speed that is not on the mode's list, such as Max+ (`108`) outside vacuum-only mode or the mop-only code `105` left over outside mop-only mode, with balanced (`102`), and a route that is not on the tab's route list with standard (`300`). The route is replaced even when it is not adjustable in the mode, but only when a route is sent at all (see above); the tab's list is the model's full list where the full list is offered and fast and standard otherwise. The robot rejects deep (`301`) in vacuum and mop with error `-10005`. A setting the device does not have (for example the mop route without route setting) always lists nothing, even in SmartPlan or custom mode; the same holds for the mop route without the shake module. In SmartPlan and custom mode only the SmartPlan or custom value is listed.

**Supported devices:**

* Roborock Saros 10R: ✅ (one command with `fan_power`, `water_box_mode` and `mop_mode`; tested in every cleaning mode, including SmartPlan `110`/`209`/`306` and custom `106`/`204`/`302`; deep route `301` returns `-10005` in vacuum and mop)

### get_dust_collection_mode

Description:

Parameters: None

Returns:

    mode:

Return example:

```json
    {'mode': 0}
```

Source: Roborock S7 MaxV Ultra

**Supported devices:**

* Roborock S7 MaxV Ultra: ✅
* Roborock S8 Pro Ultra: ✅


### set_dust_collection_mode

Description:

Parameters:

### get_wash_towel_mode

Description:

Parameters: None

Returns:

    wash_mode:

Return example:

```json
    {'wash_mode': 1}
```

Source: Roborock S7 MaxV Ultra


    unknown = -9999

    light = 0

    balanced = 1

    deep = 2


**Supported devices:**

* Roborock S7 MaxV Ultra: ✅
* Roborock S8 Pro Ultra: ✅


### set_wash_towel_mode

Description: Sets the wash wash_towel_mode

Parameters: {'wash_mode': 2}

Returns: ok or error

Source: S8 Pro Ultra

**Supported devices:**

* Roborock S7 MaxV Ultra: ✅
* Roborock S8 Pro Ultra: ✅

### get_collision_avoid_status

Description:

Parameters: None

Returns:

    status:

Return example:

```json
    {'status': 1}
```

**Supported devices:**

* Roborock S7 MaxV Ultra: ✅
* Roborock S8 Pro Ultra: ✅


### set_collision_avoid_status

Description: Update collision avoid status.

Parameters: '{"status" :1}'

Returns:

    ok

**Supported devices:**

* Roborock S7 MaxV Ultra: ✅
* Roborock S8 Pro Ultra: ✅


### start_wash_then_charge

Description:

Parameters:

<!--
    While this returns ok on the S8 Pro Ultra it does not appear to do anything
-->

### switch_water_mark

Description:

Parameters:

**Supported devices:**

* Roborock S8 Pro Ultra: ❌

<!--
    Not found for S8 Pro Ultra
-->

## System information

### get_network_info

Description: Get the device's network information.

Parameters: None

Returns:

    ssid: SSID of the wirelness network the device is connected to.

    ip: IP address of the device.

    mac: MAC address of the device.

    bssid: BSSID of the device.

    rssi: RSSI of the device.

Return example:

```json
    {'ssid': 'My WiFi Network', 'ip': '192.168.1.29', 'mac': 'a0:2b:47:3d:24:51', 'bssid': '18:3b:1a:23:41:3c', 'rssi': -32}
```

Source: Roborock S7 MaxV Ultra

**Supported devices:**

* Roborock S7 MaxV Ultra: ✅
* Roborock S8 Pro Ultra: ✅


### get_serial_number

Description: Get serial number of the vacuum.

Parameters: None

Returns:

    serial_number: Serial number of the vacuum.

Return example:

```json
    {'serial_number': 'B16EVD12345678'}
```

Source: Roborock S7 MaxV Ultra

**Supported devices:**

* Roborock S7 MaxV Ultra: ✅
* Roborock S8 Pro Ultra: ✅

### get_prop

Description: Generic get property command

Parameters: The property to get

Example:

    roborock -d command --device_id aHiddenDeviceId --cmd get_prop --params '["battery"]'



Comment : This example returns the same as get_status. Initial testing has shown that not all get commands are supported by this method


### get_turn_server

Description:

Parameters:

<!--
    Not found for S8 Pro Ultra
-->

**Supported devices:**

* Roborock S8 Pro Ultra: ❌


### enable_log_upload

Description:

Parameters:


### find_me

Description: This makes your vacuum speak so you can find it.

Parameters: None

### upd_server_timer

Description:

Parameters:

### get_homesec_connect_status

Description:

Parameters:

**Supported devices:**

* Roborock S8 Pro Ultra: ❌


### set_fds_endpoint

Description:

Parameters:

### send_ice_to_robot

Description:

Parameters:


### send_sdp_to_robot

Description:

Parameters:

### get_device_ice

<!--
    This doeas not appear to be supported on S8 Pro Ultra
-->

Description:

Parameters:

**Supported devices:**

* Roborock S8 Pro Ultra: ❌

### get_device_sdp

Description:

Parameters:

**Supported devices:**

* Roborock S8 Pro Ultra: ❌

### retry_request

Description:

Parameters:

## Timers

### del_server_timer

Description:

Parameters:


### dnd_timer

### get_dnd_timer

Description: Gets the do not disturb timer

    start_hour: The hour you want dnd to start

    start_minute: The minute you want dnd to start

    end_hour: The hour you want dnd to be turned off

    end_minute: The minute you want dnd to be turned off

    enabled: If the switch is currently turned on in the app for DnD

Parameters: None


### set_dnd_timer

Description:

Parameters:


### close_dnd_timer

Description: This disables the dnd timer

Parameters: None

### get_server_timer

Description:

Parameters:


### set_server_timer

Description:

Parameters:

### get_timezone

Description: Get the device's time zone.

Parameters: None

Returns: Time zone by the TZ identifier (e.g., America/Los_Angeles)

**Supported devices:**

* Roborock S7 MaxV Ultra: ✅
* Roborock S8 Pro Ultra: ✅


### set_timezone

Description: Sets the device's time zone

Parameters:




## Sound

### get_sound_volume

Description: Returns the volume of the sound played by the vacuum

Parameters: None

Returns:

    volume: The volume of the sound played by the vacuum

Example:

    72

**Supported devices:**

* Roborock S8 Pro Ultra: ✅

### change_sound_volume

Description: Sets the volume of the sound played by the vacuum

Parameters: volume

Returns: ok or error

`roborock -d command --device_id aHiddenDeviceId --cmd change_sound_volume --params 72`

**Supported devices:**

* Roborock S8 Pro Ultra: ✅

### test_sound_volume

Description: Plays a sound on the vacumm to identity volume

Parameters: None

**Supported devices:**

* Roborock S8 Pro Ultra: ✅


### get_sound_progress

Description:

Parameters:

Returns:

```json
{'sid_in_progress': 0, 'progress': 0, 'state': 0, 'error': 0}
```

<!--
    Is this where the vacumm is currently located ?
-->


### get_current_sound

<!--
    Is this an app setting ?
-->

Description:

Parameters:

Return example:

```json
    {'sid_in_use': 122, 'sid_version': 1, 'sid_in_progress': 0, 'location': 'de', 'bom': 'A.03.0342', 'language': 'en', 'msg_ver': 2}
```

**Supported devices:**

* Roborock S7 MaxV Ultra: ✅
* Roborock S8 Pro Ultra: ✅

### dnld_install_sound

Description:

Parameters:

## Off peak charging

### get_valley_electricity_timer

Description:  Get valley electricity timer.

Parameters: None

Returns:

    start_hour: The hour you want valley electricity to start

    start_minute: The minute you want valley electricity to start

    end_hour: The hour you want valley electricity to be turned off

    end_minute: The minute you want valley electricity to be turned off

    enabled: If the switch is currently turned on in the app for valley electricity


```json
{'start_hour': 0, 'start_minute': 0, 'end_hour': 0, 'end_minute': 0, 'enabled': 0}
```

**Supported devices:**

* Roborock S8 Pro Ultra: ✅

### set_valley_electricity_timer

Description: Sets the valley electricity timer

Parameters:

    start_hour: The hour you want valley electricity to start

    start_minute: The minute you want valley electricity to start

    end_hour: The hour you want valley electricity to be turned off

    end_minute: The minute you want valley electricity to be turned off

    enabled: If the switch is currently turned on in the app for valley electricity

Example:

```json
{'start_hour': 0, 'start_minute': 0, 'end_hour': 0, 'end_minute': 0, 'enabled': 0}
```


<!--
    This does not appear to have any effect on the S8 Pro Ultra - Params accepted however no affect ??
-->

**Supported devices:**

* Roborock S8 Pro Ultra: ❓




## Water box mode

### get_water_box_custom_mode

Description: Get the current water box / flow mode.

Parameters: None

Returns: Integer code representing the water box mode (e.g. `200`, `201`, `202`, `203`, `209`). See `set_water_box_custom_mode` below for the full mode enumeration.

**Supported devices:**

* Roborock S7 MaxV Ultra: ✅
* Roborock S8 Pro Ultra: ✅
* Roborock S8 MaxV Ultra: ✅


### get_clean_follow_ground_material_status

Description:

Parameters: None

**Supported devices:**

* Roborock S8 Pro Ultra: ✅

### set_water_box_custom_mode

Description: Set the water box / mopping water flow mode. Setting mode `200` turns off water dispensing completely (used for vacuum-only cleaning). To perform mop-only cleaning without vacuuming, pair water mode with turning off the vacuum fan (`set_custom_mode` to `105` / `VacuumModes.OFF`).

Parameters: Integer mode code inside a list or dictionary, e.g. `[200]` or `{'water_box_mode': 200}`. On models with water slide support the code can also be in the range `221`-`250`. Models that accept `water_box_mode` in `set_clean_motor_mode` use that command instead, see `set_clean_motor_mode`.

CLI Example:

```bash
roborock -d command --device_id <DeviceID> --cmd set_water_box_custom_mode --params '[200]'
```

**Standard Water Box Modes (`WaterModes`):**

| Code | Name | Description |
| :--- | :--- | :--- |
| `200` | Off | No water flow (used for vacuum only) |
| `201` | Low / Mild | Low water flow |
| `202` | Medium / Standard | Medium water flow |
| `203` | High / Intense | High water flow |
| `204` | Customized | Device-customized setting |
| `205` | Min | Minimum water flow |
| `206` | Max | Maximum water flow |
| `207` | Custom | Custom water flow rate |
| `208` | Extreme | Extreme water flow |
| `209` | Smart Mode | SmartPlan / AI automated mode |

*Note: Devices with water slide support use positions `221`–`250` (`PURE_WATER_FLOW_*`) for granular slider control.*

Returns: `ok` or error

**Supported devices:**

* Roborock S7 MaxV Ultra: ✅
* Roborock S8 Pro Ultra: ✅
* Roborock S8 MaxV Ultra: ✅
