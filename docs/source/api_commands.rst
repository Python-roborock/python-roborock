Api commands
============
This page is still under construction. All of the following are the commands we have reverse engineered. It is not an exhaustive list of all the possible commands.

Commands can have multiple parameters that can change from one model to another.

app_charge
----------

Description: This tells your vacuum to go back to the dock and charge.

Parameters: None


app_get_dryer_setting
---------------------

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

Return example::

    {'status': 1, 'on': {'cliff_on': 1, 'cliff_off': 1, 'count': 10, 'dry_time': 7200}, 'off': {'cliff_on': 2, 'cliff_off': 1, 'count': 10}}

Source: Roborock S7 MaxV Ultra

app_get_init_status
-------------------

Description:

Parameters:


app_goto_target
---------------

Description:

Parameters:


app_pause
---------

Description: This pauses the vacuum's current task

Parameters: None


app_rc_end
----------

Description:

Parameters:


app_rc_move
-----------

Description:

Parameters:


app_rc_start
------------

Description:

Parameters:


app_rc_stop
-----------

Description:

Parameters:


app_segment_clean
-----------------

Description:

Parameters:


app_set_dryer_setting
---------------------

Description:

Parameters:


app_set_smart_cliff_forbidden
-----------------------------

Description:

Parameters:


app_spot
--------

Description:

Parameters:


app_start
---------

Description:

Parameters:


app_start_collect_dust
----------------------

Description:

Parameters:


app_start_wash
--------------

Description:

Parameters:


app_stat
--------

Description:

Parameters:


app_stop
--------

Description:

Parameters:


app_stop_wash
-------------

Description:

Parameters:


app_wakeup_robot
----------------

Description:

Parameters:


app_zoned_clean
---------------

Description:

Parameters:


camera_status
-------------

Get: get_camera_status

Description: Get camera status.

Parameters: None

Returns: 3457

Source: Roborock S7 MaxV Ultra


Set: set_camera_status

Description:

Parameters:


carpet_clean_mode
-----------------

Get: get_carpet_clean_mode

Description: Get carpet clean mode.

Parameters:

Returns:

    carpet_clean_mode: Enumeration for carpet clean mode.

Return example::

    {'carpet_clean_mode': 3}

Source: Roborock S7 MaxV Ultra


Set: set_carpet_clean_mode

Description:

Parameters:


carpet_mode
-----------

Get: get_carpet_mode

Description:

Parameters: None

Returns:

    enable:

    current_integral:

    current_high:

    current_low:

    stall_time:

Return example::

    {'enable': 1, 'current_integral': 450, 'current_high': 500, 'current_low': 400, 'stall_time': 10}

======================  =========
Vacuum Model            Supported
======================  =========
Roborock S7 MaxV Ultra  Yes
======================  =========


Set: set_carpet_mode

Description:

Parameters:


child_lock_status
-----------------

Get: get_child_lock_status

Description: This gets the child lock status of the device. 0 is off, 1 is on.

Parameters: None


Set: set_child_lock_status

Description: This sets the child lock status of the device.

Parameters: None


collision_avoid_status
----------------------

Get: get_collision_avoid_status

Description:

Parameters: None

Returns:

    status:

Return example::

    {'status': 1}

Source: Roborock S7 MaxV Ultra


Set: set_collision_avoid_status

Description:

Parameters:


consumable
----------

Get: get_consumable

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



custom_mode
-----------

Get: get_custom_mode

Description:

Parameters:


Set: set_custom_mode

Description:

Parameters:


customize_clean_mode
--------------------

Get: get_customize_clean_mode

Description:

Parameters:


Set: set_customize_clean_mode

Description:

Parameters:


del_server_timer
----------------

Description:

Parameters:


dnd_timer
---------

Get: get_dnd_timer

Description: Gets the do not disturb timer

    start_hour: The hour you want dnd to start

    start_minute: The minute you want dnd to start

    end_hour: The hour you want dnd to be turned off

    end_minute: The minute you want dnd to be turned off

    enabled: If the switch is currently turned on in the app for DnD

Parameters: None


Set: set_dnd_timer

Description:

Parameters:


Close: close_dnd_timer

Description: This disables the dnd timer

Parameters: None


dnld_install_sound
------------------

Description:

Parameters:


dust_collection_mode
--------------------

Get: get_dust_collection_mode

Description:

Parameters: None

Returns:

    mode:

Return example::

    {'mode': 0}

Source: Roborock S7 MaxV Ultra


Set: set_dust_collection_mode

Description:

Parameters:


enable_log_upload
-----------------

Description:

Parameters:


end_edit_map
------------

Description:

Parameters:


find_me
-------

Description:

Parameters:


flow_led_status
---------------

Get: get_flow_led_status

Description:

Parameters:


Set: set_flow_led_status

Description:

Parameters:


get_clean_record
----------------

Description:

Parameters:


get_clean_record_map
--------------------

Description:

Parameters:


get_clean_sequence
------------------

Description:

Parameters:


get_clean_summary
-----------------

Description: Get a summary of cleaning history.

Parameters: None

Returns:

    clean_time:

    clean_area:

    clean_count:

    dust_collection_count:

    records:

Return example::

    {'clean_time': 568146, 'clean_area': 8816865000, 'clean_count': 178, 'dust_collection_count': 172, 'records': [1689740211, 1689555788, 1689259450, 1688999113, 1688852350, 1688693213, 1688692357, 1688614354, 1688613280, 1688606676, 1688325265, 1688174717, 1688149381, 1688092832, 1688001593, 1687921414, 1687890618, 1687743256, 1687655018, 1687631444]}

Source: Roborock S7 MaxV Ultra


get_current_sound
-----------------

Description:

Parameters:


get_device_ice
--------------

Description:

Parameters:


get_device_sdp
--------------

Description:

Parameters:


get_homesec_connect_status
--------------------------

Description:

Parameters:


get_map_v1
----------

Description:

Parameters:


get_mop_template_params_summary
-------------------------------

Description:

Parameters:


get_multi_map
-------------

Description:

Parameters:


get_multi_maps_list
-------------------

Description:

Parameters:


get_network_info
----------------

Description: Get the device's network information.

Parameters: None

Returns:

    ssid: SSID of the wirelness network the device is connected to.

    ip: IP address of the device.

    mac: MAC address of the device.

    bssid: BSSID of the device.

    rssi: RSSI of the device.

Return example::

    {'ssid': 'My WiFi Network', 'ip': '192.168.1.29', 'mac': 'a0:2b:47:3d:24:51', 'bssid': '18:3b:1a:23:41:3c', 'rssi': -32}

Source: Roborock S7 MaxV Ultra


get_prop
--------

Description:

Parameters:


get_room_mapping
----------------

Description:

Parameters:


get_scenes_valid_tids
---------------------

Description:

Parameters:


get_serial_number
-----------------

Description: Get serial number of the vacuum.

Parameters: None

Returns:

    serial_number: Serial number of the vacuum.

Return example::

    {'serial_number': 'B16EVD12345678'}

Source: Roborock S7 MaxV Ultra


get_sound_progress
------------------

Description:

Parameters:


get_turn_server
---------------

Description:

Parameters:


identify_furniture_status
-------------------------

Get: get_identify_furniture_status

Description:

Parameters:


Set: set_identify_furniture_status

Description:

Parameters:


identify_ground_material_status
-------------------------------

Get: get_identify_ground_material_status

Description:

Parameters:


Set: set_identify_ground_material_status

Description:

Parameters:


led_status
----------

Get: get_led_status

Description:

Parameters:


Set: set_led_status

Description:

Parameters:


load_multi_map
--------------

Description:

Parameters:


name_segment
------------

Description:

Parameters:


reset_consumable
----------------

Description:

Parameters:


resume_segment_clean
--------------------

Description:

Parameters:


resume_zoned_clean
------------------

Description:

Parameters:


retry_request
-------------

Description:

Parameters:


reunion_scenes
--------------

Description:

Parameters:


save_map
--------

Description:

Parameters:


send_ice_to_robot
-----------------

Description:

Parameters:


send_sdp_to_robot
-----------------

Description:

Parameters:


server_timer
------------

Get: get_server_timer

Description:

Parameters:


Set: set_server_timer

Description:

Parameters:


set_app_timezone
----------------

Description:

Parameters:


set_clean_motor_mode
--------------------

Description:

Parameters:


set_fds_endpoint
----------------

Description:

Parameters:


set_mop_mode
------------

Description:

Parameters:


set_scenes_segments
-------------------

Description:

Parameters:


set_scenes_zones
----------------

Description:

Parameters:


set_water_box_custom_mode
-------------------------

Description:

Parameters:


smart_wash_params
-----------------

Get: get_smart_wash_params

Description:

Parameters:


Set: set_smart_wash_params

Description:

Parameters:


sound_volume
------------

Get: get_sound_volume

Description:

Parameters:


Set: change_sound_volume

Description:

Parameters:


start_camera_preview
--------------------

Description:

Parameters:


start_edit_map
--------------

Description:

Parameters:


start_voice_chat
----------------

Description:

Parameters:


start_wash_then_charge
----------------------

Description:

Parameters:


status
------

Get: get_status

Description: Get status information of the device.

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

Return example::

    {'msg_ver': 2, 'msg_seq': 1965, 'state': 8, 'battery': 100, 'clean_time': 1976, 'clean_area': 33197500, 'error_code': 0, 'map_present': 1, 'in_cleaning': 0, 'in_returning': 0, 'in_fresh_state': 1, 'lab_status': 1, 'water_box_status': 1, 'back_type': -1, 'wash_phase': 0, 'wash_ready': 0, 'fan_power': 102, 'dnd_enabled': 0, 'map_status': 3, 'is_locating': 0, 'lock_status': 0, 'water_box_mode': 203, 'water_box_carriage_status': 1, 'mop_forbidden_enable': 1, 'camera_status': 3457, 'is_exploring': 0, 'home_sec_status': 0, 'home_sec_enable_password': 0, 'adbumper_status': [0, 0, 0], 'water_shortage_status': 0, 'dock_type': 3, 'dust_collection_status': 0, 'auto_dust_collection': 1, 'avoid_count': 141, 'mop_mode': 300, 'debug_mode': 0, 'collision_avoid_status': 1, 'switch_map_mode': 0, 'dock_error_status': 0, 'charge_status': 1, 'unsave_map_reason': 0, 'unsave_map_flag': 0}

Source: Roborock S7 MaxV Ultra


stop_camera_preview
-------------------

Description:

Parameters:


switch_water_mark
-----------------

Description:

Parameters:


test_sound_volume
-----------------

Description:

Parameters:


timezone
--------

Get: get_timezone

Description: Get the device's time zone.

Parameters: None

Returns: Time zone by the TZ identifier (e.g., America/Los_Angeles)


Set: set_timezone

Description:

Parameters:


upd_server_timer
----------------

Description:

Parameters:


valley_electricity_timer
------------------------

Get: get_valley_electricity_timer

Description:

Parameters:


Set: set_valley_electricity_timer

Description:

Parameters:


wash_towel_mode
---------------

Get: get_wash_towel_mode

Description:

Parameters: None

Returns:

    wash_mode:

Return example::

    {'wash_mode': 1}

Source: Roborock S7 MaxV Ultra


Set: set_wash_towel_mode

Description:

Parameters:
