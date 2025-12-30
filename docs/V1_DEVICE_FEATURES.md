# Roborock Device Features Documentation

This document provides comprehensive documentation for each `DeviceFeature` in the python-roborock library, explaining what each feature supports in the Roborock app and vacuum functionality.

## Table of Contents
- [Overview](#overview)
- [Feature Detection Systems](#feature-detection-systems)
- [Robot New Features (Lower 32 bits)](#robot-new-features-lower-32-bits)
- [Robot New Features (Upper 32 bits)](#robot-new-features-upper-32-bits)
- [New Feature String Mask Features](#new-feature-string-mask-features)
- [New Feature String Bit Features](#new-feature-string-bit-features)
- [Robot Features (Array-based)](#robot-features-array-based)
- [Model-Specific Features](#model-specific-features)
- [Product Features](#product-features)

---

## Overview

The Roborock ecosystem uses multiple feature flag systems to determine device capabilities:

1. **robotNewFeatures** - A 64-bit integer split into lower/upper 32 bits for bit-masked features
2. **new_feature_info_str** - A hexadecimal string where each bit/nibble represents a feature
3. **feature_info** (robotFeatures) - An array of integer feature IDs
4. **Model whitelists/blacklists** - Specific features tied to device models
5. **Product features** - Hardware capability flags (cameras, mop modules, etc.)

---

## Feature Detection Systems

### System 1: robotNewFeatures (Lower 32 bits)
Features checked via bitwise AND against the lower 32 bits of `new_feature_info`.

### System 2: robotNewFeatures (Upper 32 bits)
Features checked by shifting right 32 bits and checking individual bit positions.

### System 3: new_feature_info_str (Hex String)
A hexadecimal string where features are encoded as bits. The string is parsed from right to left.

### System 4: robotFeatures (Array)
An array of integer feature IDs. Feature is supported if ID is present in the array.

---

## Robot New Features (Lower 32 bits)

### is_show_clean_finish_reason_supported
**Bit Mask:** `1` (bit 0)
**Feature:** Show Clean Finish Reason
**Description:** Enables the app to display the reason why a cleaning session ended (e.g., completed, battery low, stuck, user canceled).
**Impact:** Provides better user feedback on cleaning outcomes.

---

### is_re_segment_supported
**Bit Mask:** `4` (bit 2)
**Feature:** Re-Segment Map
**Description:** Allows the vacuum to re-segment and re-divide rooms on the map after initial mapping.
**Impact:** Users can trigger automatic room re-detection if the initial segmentation was incorrect.

---

### is_video_monitor_supported
**Bit Mask:** `8` (bit 3)
**Feature:** Video Monitor
**Description:** Enables video monitoring capabilities through the vacuum's camera system.
**Impact:** Users can view live video feed from the vacuum's camera in the app.

---

### is_any_state_transit_goto_supported
**Bit Mask:** `16` (bit 4)
**Feature:** Any State Transit Goto
**Description:** Allows the vacuum to accept "go to" commands in any operational state, not just idle.
**Impact:** More flexible navigation commands during cleaning or other operations.

---

### is_fw_filter_obstacle_supported
**Bit Mask:** `32` (bit 5)
**Feature:** Firmware Filter Obstacle
**Description:** Firmware-level obstacle filtering to distinguish between real obstacles and false positives.
**Impact:** Reduces unnecessary obstacle avoidance for minor or temporary objects.

---

### is_video_setting_supported
**Bit Mask:** `64` (bit 6)
**Feature:** Video Settings
**Description:** Enables configuration options for camera video quality, resolution, and streaming settings.
**Impact:** Users can adjust video quality to balance bandwidth and clarity.

---

### is_ignore_unknown_map_object_supported
**Bit Mask:** `128` (bit 7)
**Feature:** Ignore Unknown Map Objects
**Description:** Allows the vacuum to ignore unrecognized map objects during navigation.
**Impact:** Prevents navigation issues from outdated or corrupted map data.

---

### is_set_child_supported
**Bit Mask:** `256` (bit 8)
**Feature:** Set Child Lock
**Description:** Enables child lock functionality to prevent unauthorized use of the vacuum.
**Impact:** Prevents children from starting or controlling the vacuum.

---

### is_carpet_supported
**Bit Mask:** `512` (bit 9)
**Feature:** Carpet Detection
**Description:** Enables carpet detection and special carpet cleaning modes (increased suction, mop lifting).
**Impact:** Automatic suction boost on carpets and prevents mopping on carpets.

---

### is_record_allowed
**Bit Mask:** `1024` (bit 10)
**Feature:** Video Recording Allowed
**Description:** Permits video recording from the vacuum's camera (privacy setting).
**Impact:** Users can record video clips from the camera feed.

---

### is_mop_path_supported
**Bit Mask:** `2048` (bit 11)
**Feature:** Mop Path Display
**Description:** Shows the mopping path separately from the vacuum path on the map.
**Impact:** Users can see exactly which areas were mopped vs. just vacuumed.

---

### is_multi_map_segment_timer_supported
**Bit Mask:** `4096` (bit 12)
**Feature:** Multi-Map Segment Timer
**Description:** Enables scheduled cleaning for specific rooms across multiple floor maps.
**Impact:** Create schedules that work across different floors/maps.

---

### is_current_map_restore_enabled
**Bit Mask:** `8192` (bit 13)
**Feature:** Current Map Restore
**Description:** Ability to restore and reload the current map if it becomes corrupted or lost.
**Impact:** Prevents need to remap after map corruption or vacuum reset.

---

### is_room_name_supported
**Bit Mask:** `16384` (bit 14)
**Feature:** Room Naming
**Description:** Allows users to assign custom names to rooms on the map.
**Impact:** More intuitive room selection (e.g., "Kitchen" instead of "Room 1").

---

### is_shake_mop_set_supported
**Bit Mask:** `262144` (bit 18)
**Feature:** Shake/Vibrating Mop Settings
**Description:** Configuration options for mop vibration/shaking intensity and frequency.
**Impact:** Users can adjust mopping aggressiveness for different floor types.

---

### is_map_beautify_internal_debug_supported
**Bit Mask:** `2097152` (bit 21)
**Feature:** Map Beautify Debug Mode
**Description:** Internal debugging mode for map rendering and beautification algorithms.
**Impact:** Developer/debug feature, not typically exposed to end users.

---

### is_new_data_for_clean_history
**Bit Mask:** `4194304` (bit 22)
**Feature:** Enhanced Clean History Data
**Description:** New data format for cleaning history with additional metrics and details.
**Impact:** More detailed cleaning history including area coverage, time per room, etc.

---

### is_new_data_for_clean_history_detail
**Bit Mask:** `8388608` (bit 23)
**Feature:** Enhanced Clean History Detail View
**Description:** Detailed view for individual cleaning sessions with comprehensive statistics.
**Impact:** Users can see granular details about each cleaning session.

---

### is_flow_led_setting_supported
**Bit Mask:** `16777216` (bit 24)
**Feature:** Flow LED Settings
**Description:** Configuration for LED light indicators on the vacuum.
**Impact:** Users can customize LED brightness or disable LEDs.

---

### is_dust_collection_setting_supported
**Bit Mask:** `33554432` (bit 25)
**Feature:** Dust Collection Settings
**Description:** Options for auto-empty dock dust collection frequency and duration.
**Impact:** Configure when and how aggressively the dock empties the dustbin.

---

### is_rpc_retry_supported
**Bit Mask:** `67108864` (bit 26)
**Feature:** RPC Retry Mechanism
**Description:** Automatic retry of failed remote procedure calls to the vacuum.
**Impact:** Improved command reliability over unreliable networks.

---

### is_avoid_collision_supported
**Bit Mask:** `134217728` (bit 27)
**Feature:** Collision Avoidance
**Description:** Advanced collision avoidance using sensors and camera.
**Impact:** Reduces bumping into furniture and obstacles.

---

### is_support_set_switch_map_mode
**Bit Mask:** `268435456` (bit 28)
**Feature:** Switch Map Mode
**Description:** Ability to switch between different mapping modes (2D/3D).
**Impact:** Users can toggle between different map visualization modes.

---

### is_map_carpet_add_support
**Bit Mask:** `1073741824` (bit 30)
**Feature:** Manual Carpet Area Addition
**Description:** Manually mark carpet areas on the map for special treatment.
**Impact:** Users can define carpet zones even if auto-detection fails.

---

### is_custom_water_box_distance_supported
**Bit Mask:** `2147483648` (bit 31)
**Feature:** Custom Water Box Distance
**Description:** Adjustable water tank capacity/distance settings.
**Impact:** Optimize water usage for different floor sizes.

---

## Robot New Features (Upper 32 bits)

### is_support_smart_scene
**Bit Position:** 1 (upper 32 bits)
**Feature:** Smart Scene
**Description:** Intelligent cleaning scenes that adapt to room type and detected objects.
**Impact:** Automatic cleaning parameter adjustment based on room identification.

---

### is_support_floor_edit
**Bit Position:** 3 (upper 32 bits)
**Feature:** Floor Map Editing
**Description:** Advanced map editing capabilities including floor type assignment.
**Impact:** Users can mark different floor types (hardwood, tile, carpet) for optimized cleaning.

---

### is_support_furniture
**Bit Position:** 4 (upper 32 bits)
**Feature:** Furniture Detection/Placement
**Description:** Detection and placement of furniture icons on the map.
**Impact:** Visual representation of furniture locations on the map.

---

### is_wash_then_charge_cmd_supported
**Bit Position:** 5 (upper 32 bits)
**Feature:** Wash Then Charge Command
**Description:** Command to wash the mop before returning to charging (for docks with mop washing).
**Impact:** Ensures mop is clean before drying/charging cycle.

---

### is_support_room_tag
**Bit Position:** 6 (upper 32 bits)
**Feature:** Room Tagging
**Description:** Ability to tag rooms with properties (e.g., high traffic, pet area).
**Impact:** Allows for room-specific cleaning strategies.

---

### is_support_quick_map_builder
**Bit Position:** 7 (upper 32 bits)
**Feature:** Quick Map Builder
**Description:** Rapid mapping mode that creates a basic map faster than full mapping.
**Impact:** Get a usable map quickly before running detailed mapping later.

---

### is_support_smart_global_clean_with_custom_mode
**Bit Position:** 8 (upper 32 bits)
**Feature:** Smart Global Clean with Custom Mode
**Description:** Apply custom cleaning modes during smart global cleaning.
**Impact:** Combine intelligent cleaning with user-defined preferences.

---

### is_careful_slow_mop_supported
**Bit Position:** 9 (upper 32 bits)
**Feature:** Careful/Slow Mopping Mode
**Description:** Extra slow and careful mopping for delicate floors.
**Impact:** Better cleaning for sensitive floor types that need gentle treatment.

---

### is_egg_mode_supported_from_new_features
**Bit Position:** 10 (upper 32 bits)
**Feature:** Egg Mode
**Description:** Special cleaning pattern that moves in egg-shaped paths.
**Impact:** Alternative cleaning pattern for thorough coverage.

---

### is_carpet_show_on_map
**Bit Position:** 12 (upper 32 bits)
**Feature:** Display Carpets on Map
**Description:** Visual indication of detected carpet areas on the map.
**Impact:** Users can see which areas the vacuum has identified as carpet.

---

### is_supported_valley_electricity
**Bit Position:** 13 (upper 32 bits)
**Feature:** Off-Peak Electricity Scheduling
**Description:** Schedule charging and intensive tasks during off-peak electricity hours.
**Impact:** Reduce electricity costs by charging during cheaper rate periods.

---

### is_unsave_map_reason_supported
**Bit Position:** 14 (upper 32 bits)
**Feature:** Unsaved Map Reason
**Description:** Displays reason why a map wasn't saved after a cleaning session.
**Impact:** Better understanding of why maps fail to save.

---

### is_supported_drying
**Bit Position:** 15 (upper 32 bits)
**Feature:** Mop Drying
**Description:** Active mop drying function in compatible docks.
**Impact:** Mop pads are actively dried to prevent odors and mildew.

---

### is_supported_download_test_voice
**Bit Position:** 16 (upper 32 bits)
**Feature:** Download Test Voice Packs
**Description:** Ability to download and test voice packs before installation.
**Impact:** Preview voice packs before committing to download.

---

### is_support_backup_map
**Bit Position:** 17 (upper 32 bits)
**Feature:** Map Backup
**Description:** Cloud backup of maps to prevent data loss.
**Impact:** Maps can be restored after device reset or replacement.

---

### is_support_custom_mode_in_cleaning
**Bit Position:** 18 (upper 32 bits)
**Feature:** Custom Mode During Cleaning
**Description:** Change custom cleaning modes while a cleaning session is in progress.
**Impact:** Adjust cleaning intensity on-the-fly without stopping.

---

### is_support_remote_control_in_call
**Bit Position:** 19 (upper 32 bits)
**Feature:** Remote Control During Video Call
**Description:** Manual remote control available during video call sessions.
**Impact:** Navigate the vacuum manually while viewing the camera feed.

---

## New Feature String Mask Features

These features are encoded in the last 8 characters of the `new_feature_info_str` hex string.

### is_support_set_volume_in_call
**Mask:** `1` (position 8)
**Feature:** Volume Control in Call
**Description:** Adjust audio volume during video call sessions.
**Impact:** Better audio experience during two-way communication.

---

### is_support_clean_estimate
**Mask:** `2` (position 8)
**Feature:** Clean Time Estimation
**Description:** Provides estimated cleaning time before starting a session.
**Impact:** Users know approximately how long cleaning will take.

---

### is_support_custom_dnd
**Mask:** `4` (position 8)
**Feature:** Custom Do Not Disturb
**Description:** Customizable DND schedules with fine-grained time control.
**Impact:** More flexible quiet hours configuration.

---

### is_carpet_deep_clean_supported
**Mask:** `8` (position 8)
**Feature:** Carpet Deep Clean Mode
**Description:** Extra-intense carpet cleaning with multiple passes.
**Impact:** Deeper cleaning for heavily soiled carpets.

---

### is_support_stuck_zone
**Mask:** `16` (position 8)
**Feature:** Stuck Zone Detection
**Description:** Automatically marks areas where the vacuum frequently gets stuck.
**Impact:** Can create automatic no-go zones for problematic areas.

---

### is_support_custom_door_sill
**Mask:** `32` (position 8)
**Feature:** Custom Door Sill Height
**Description:** Manually set door sill/threshold heights for better navigation.
**Impact:** Helps vacuum navigate over thresholds it might otherwise avoid.

---

### is_wifi_manage_supported
**Mask:** `128` (position 8)
**Feature:** WiFi Management
**Description:** Advanced WiFi settings including network switching and diagnostics.
**Impact:** Better control over network connectivity.

---

### is_clean_route_fast_mode_supported
**Mask:** `256` (position 8)
**Feature:** Fast Clean Route Mode
**Description:** Optimized routing for faster cleaning at slight coverage cost.
**Impact:** Quicker cleaning when thoroughness isn't critical.

---

### is_support_cliff_zone
**Mask:** `512` (position 8)
**Feature:** Cliff/Drop-off Zone Marking
**Description:** Mark areas with cliffs or drop-offs that sensors might miss.
**Impact:** Prevents falls in areas where cliff sensors may be unreliable.

---

### is_support_smart_door_sill
**Mask:** `1024` (position 8)
**Feature:** Smart Door Sill Detection
**Description:** Automatic detection and learning of door sill heights.
**Impact:** Vacuum learns which thresholds it can cross over time.

---

### is_support_floor_direction
**Mask:** `2048` (position 8)
**Feature:** Floor Direction/Grain
**Description:** Set floor grain direction for optimized mopping along wood grain.
**Impact:** Better mopping results on hardwood floors.

---

### is_back_charge_auto_wash_supported
**Mask:** `4096` (position 8)
**Feature:** Auto-Wash Before Charging
**Description:** Automatically wash mop when returning to charge.
**Impact:** Mop is always clean and ready for next session.

---

### is_support_incremental_map
**Mask:** `4194304` (position 8)
**Feature:** Incremental Mapping
**Description:** Continuously update and refine maps with each cleaning.
**Impact:** Maps improve over time with more cleaning sessions.

---

### is_offline_map_supported
**Mask:** `16384` (position 8)
**Feature:** Offline Map Access
**Description:** View and edit maps without internet connection.
**Impact:** Full functionality even when cloud services are unavailable.

---

### is_super_deep_wash_supported
**Mask:** `32768` (position 8)
**Feature:** Super Deep Mop Wash
**Description:** Extended and intensive mop washing cycle in dock.
**Impact:** Thoroughly clean heavily soiled mop pads.

---

### is_ces_2022_supported
**Mask:** `65536` (position 8)
**Feature:** CES 2022 Features
**Description:** Features demonstrated at CES 2022 trade show.
**Impact:** Early access or beta features from product announcements.

---

### is_dss_believable
**Mask:** `131072` (position 8)
**Feature:** DSS (Dirt Detect System) Believable
**Description:** Improved dirt detection system reliability.
**Impact:** More accurate dirty area detection and focused cleaning.

---

### is_main_brush_up_down_supported_from_str
**Mask:** `262144` (position 8)
**Feature:** Main Brush Lift
**Description:** Main brush can be raised/lowered automatically (for carpets/hard floors).
**Impact:** Optimized brush engagement for different floor types.

---

### is_goto_pure_clean_path_supported
**Mask:** `524288` (position 8)
**Feature:** Pure Clean Path Navigation
**Description:** Navigate to cleaning areas using pure/clean paths.
**Impact:** Avoids dirty areas when navigating to next cleaning zone.

---

### is_water_up_down_drain_supported
**Mask:** `1048576` (position 8)
**Feature:** Water Tank Auto Drain
**Description:** Automatic water tank drainage system.
**Impact:** Prevents stagnant water and simplifies maintenance.

---

### is_setting_carpet_first_supported
**Mask:** `8388608` (position 8)
**Feature:** Carpet-First Cleaning
**Description:** Option to clean all carpeted areas first before hard floors.
**Impact:** Vacuum-only areas completed before mopping begins.

---

### is_clean_route_deep_slow_plus_supported
**Mask:** `16777216` (position 8)
**Feature:** Deep Slow Plus Route
**Description:** Extra slow and thorough cleaning route for maximum coverage.
**Impact:** Most thorough cleaning at expense of time.

---

### is_dynamically_skip_clean_zone_supported
**Mask:** `33554432` (position 8)
**Feature:** Dynamic Zone Skipping
**Description:** Automatically skip certain zones based on conditions (e.g., doors closed).
**Impact:** More intelligent cleaning that adapts to real-time conditions.

---

### is_dynamically_add_clean_zones_supported
**Mask:** `67108864` (position 8)
**Feature:** Dynamic Zone Addition
**Description:** Automatically add new cleaning zones during a session.
**Impact:** Expand cleaning area on-the-fly when needed.

---

### is_left_water_drain_supported
**Mask:** `134217728` (position 8)
**Feature:** Residual Water Drainage
**Description:** Drain all remaining water from tank and system.
**Impact:** Completely empty water system for storage or travel.

---

### is_clean_count_setting_supported
**Mask:** `1073741824` (position 8)
**Feature:** Multi-Pass Clean Count
**Description:** Configure number of cleaning passes per area.
**Impact:** Set how many times vacuum should clean each area (1-3 passes).

---

### is_corner_clean_mode_supported
**Mask:** `2147483648` (position 8)
**Feature:** Corner Cleaning Mode
**Description:** Special mode for intensive corner and edge cleaning.
**Impact:** Better cleaning along walls and in corners.

---

## New Feature String Bit Features

These features are encoded as individual bits in the `new_feature_info_str` hex string.

### is_two_key_real_time_video_supported
**Bit Index:** 32
**Feature:** Two-Key Real-Time Video
**Description:** Real-time video requires two-step activation for privacy.
**Impact:** Additional privacy protection for camera access.

---

### is_two_key_rtv_in_charging_supported
**Bit Index:** 33
**Feature:** Two-Key RTV While Charging
**Description:** Two-step activation required for video while charging.
**Impact:** Privacy protection even when vacuum is docked.

---

### is_dirty_replenish_clean_supported
**Bit Index:** 34
**Feature:** Dirty Area Replenishment Clean
**Description:** Automatic return to re-clean areas detected as still dirty.
**Impact:** Ensures heavily soiled areas get adequate cleaning.

---

### is_auto_delivery_field_in_global_status_supported
**Bit Index:** 35
**Feature:** Auto-Delivery Status Field
**Description:** Status field for automatic detergent/cleaner delivery systems.
**Impact:** Monitor and control automatic cleaning solution dispensing.

---

### is_avoid_collision_mode_supported
**Bit Index:** 36
**Feature:** Collision Avoidance Mode
**Description:** Enhanced mode for avoiding collisions with obstacles.
**Impact:** Gentler navigation around furniture and objects.

---

### is_voice_control_supported
**Bit Index:** 37
**Feature:** Voice Control
**Description:** Voice command support (Alexa, Google Assistant, etc.).
**Impact:** Hands-free vacuum control via voice assistants.

---

### is_new_endpoint_supported
**Bit Index:** 38
**Feature:** New API Endpoint
**Description:** Support for new/updated API endpoints for app communication.
**Impact:** Access to latest features and improved communication protocol.

---

### is_pumping_water_supported
**Bit Index:** 39
**Feature:** Water Pumping System
**Description:** Active water pumping for precise water delivery control.
**Impact:** More consistent and controllable water flow for mopping.

---

### is_corner_mop_stretch_supported
**Bit Index:** 40
**Feature:** Corner Mop Stretch/Extension
**Description:** Mop pad extends or stretches to reach corners and edges.
**Impact:** Better mopping coverage in corners and along baseboards.

---

### is_hot_wash_towel_supported
**Bit Index:** 41
**Feature:** Hot Water Mop Washing
**Description:** Dock uses hot water to wash mop pads.
**Impact:** Better mop cleaning and sanitization.

---

### is_floor_dir_clean_any_time_supported
**Bit Index:** 42
**Feature:** Floor Direction Clean Anytime
**Description:** Apply floor direction settings at any time, not just during setup.
**Impact:** Adjust floor grain direction after initial mapping.

---

### is_pet_supplies_deep_clean_supported
**Bit Index:** 43
**Feature:** Pet Supplies Deep Clean
**Description:** Special deep cleaning mode for areas with pet supplies (bowls, toys, beds).
**Impact:** More thorough cleaning around pet areas.

---

### is_mop_shake_water_max_supported
**Bit Index:** 45
**Feature:** Maximum Mop Shake Water Mode
**Description:** Highest water flow setting for mop vibration mode.
**Impact:** Most aggressive mopping for stubborn stains.

---

### is_exact_custom_mode_supported
**Bit Index:** 47
**Feature:** Exact Custom Mode
**Description:** Precise custom mode configuration with fine-grained control.
**Impact:** More granular control over cleaning parameters.

---

### is_video_patrol_supported
**Bit Index:** 48
**Feature:** Video Patrol Mode
**Description:** Autonomous patrol mode with video recording for home monitoring.
**Impact:** Use vacuum as mobile security camera.

---

### is_carpet_custom_clean_supported
**Bit Index:** 49
**Feature:** Carpet Custom Clean
**Description:** Custom cleaning modes specifically for carpet areas.
**Impact:** Different cleaning strategies for different carpet types.

---

### is_pet_snapshot_supported
**Bit Index:** 50
**Feature:** Pet Snapshot
**Description:** Automatically capture photos of detected pets during cleaning.
**Impact:** Get photos of pets throughout the day.

---

### is_custom_clean_mode_count_supported
**Bit Index:** 51
**Feature:** Custom Clean Mode Count
**Description:** Support for multiple custom cleaning modes (more than default).
**Impact:** Create and save more than the standard 3 custom modes.

---

### is_new_ai_recognition_supported
**Bit Index:** 52
**Feature:** New AI Recognition
**Description:** Updated AI recognition algorithms for obstacles and objects.
**Impact:** Better object detection and classification.

---

### is_auto_collection_2_supported
**Bit Index:** 53
**Feature:** Auto-Empty 2.0
**Description:** Second generation auto-empty dock system.
**Impact:** Improved dustbin emptying with better suction and reliability.

---

### is_right_brush_stretch_supported
**Bit Index:** 54
**Feature:** Right Side Brush Extension
**Description:** Right side brush extends outward for better edge cleaning.
**Impact:** Better cleaning along walls and edges.

---

### is_smart_clean_mode_set_supported
**Bit Index:** 55
**Feature:** Smart Clean Mode Settings
**Description:** AI-powered automatic cleaning mode selection.
**Impact:** Vacuum automatically chooses optimal cleaning mode per room.

---

### is_dirty_object_detect_supported
**Bit Index:** 56
**Feature:** Dirty Object Detection
**Description:** Detect and focus on dirty objects/areas during cleaning.
**Impact:** More attention to visibly dirty spots.

---

### is_no_need_carpet_press_set_supported
**Bit Index:** 57
**Feature:** No Carpet Pressure Setting Needed
**Description:** Automatic carpet pressure adjustment without manual configuration.
**Impact:** Simplified setup with automatic carpet handling.

---

### is_voice_control_led_supported
**Bit Index:** 58
**Feature:** Voice Control LED Indicator
**Description:** LED indicator for voice control status.
**Impact:** Visual feedback when voice assistant is listening.

---

### is_water_leak_check_supported
**Bit Index:** 60
**Feature:** Water Leak Detection
**Description:** Sensors to detect water leaks from tank or mop system.
**Impact:** Alerts for water system issues before damage occurs.

---

### is_min_battery_15_to_clean_task_supported
**Bit Index:** 62
**Feature:** 15% Minimum Battery for Cleaning
**Description:** Requires at least 15% battery to start cleaning task.
**Impact:** Prevents starting cleaning with insufficient battery.

---

### is_gap_deep_clean_supported
**Bit Index:** 63
**Feature:** Gap Deep Cleaning
**Description:** Special mode for cleaning gaps and crevices.
**Impact:** Better cleaning in tight spaces between furniture.

---

### is_object_detect_check_supported
**Bit Index:** 64
**Feature:** Object Detection Check
**Description:** Verification system for object detection accuracy.
**Impact:** Improved reliability of obstacle avoidance.

---

### is_identify_room_supported
**Bit Index:** 66
**Feature:** Room Identification
**Description:** AI-based room type identification (bedroom, kitchen, etc.).
**Impact:** Automatic cleaning mode selection based on room type.

---

### is_matter_supported
**Bit Index:** 67
**Feature:** Matter Protocol Support
**Description:** Support for Matter smart home standard.
**Impact:** Integration with Matter-compatible smart home systems.

---

### is_workday_holiday_supported
**Bit Index:** 69
**Feature:** Workday/Holiday Scheduling
**Description:** Different schedules for workdays vs. holidays/weekends.
**Impact:** Flexible scheduling that adapts to your routine.

---

### is_clean_direct_status_supported
**Bit Index:** 70
**Feature:** Cleaning Direction Status
**Description:** Display current cleaning direction and path on map.
**Impact:** See which direction vacuum is moving in real-time.

---

### is_map_eraser_supported
**Bit Index:** 71
**Feature:** Map Eraser Tool
**Description:** Tool to erase portions of map for re-mapping.
**Impact:** Selectively re-map problem areas without full re-scan.

---

### is_optimize_battery_supported
**Bit Index:** 72
**Feature:** Battery Optimization
**Description:** Smart charging and battery management for longevity.
**Impact:** Extended battery lifespan through optimized charging.

---

### is_activate_video_charging_and_standby_supported
**Bit Index:** 73
**Feature:** Video in Charging/Standby
**Description:** Enable video camera when docked or in standby.
**Impact:** Use vacuum as stationary camera when not cleaning.

---

### is_carpet_long_haired_supported
**Bit Index:** 75
**Feature:** Long-Haired Carpet Mode
**Description:** Special mode for high-pile or shag carpets.
**Impact:** Better cleaning on thick, plush carpets.

---

### is_clean_history_time_line_supported
**Bit Index:** 76
**Feature:** Timeline Clean History
**Description:** Timeline view of cleaning history with visual map playback.
**Impact:** See cleaning progression over time with animated replay.

---

### is_max_zone_opened_supported
**Bit Index:** 77
**Feature:** Maximum Zone Expansion
**Description:** Support for larger number of zones than default.
**Impact:** Create more cleaning zones and no-go areas.

---

### is_exhibition_function_supported
**Bit Index:** 78
**Feature:** Exhibition/Demo Mode
**Description:** Special mode for retail display and demonstrations.
**Impact:** Retail demo functionality for stores.

---

### is_lds_lifting_supported
**Bit Index:** 79
**Feature:** LDS Sensor Lifting
**Description:** LDS (laser) sensor can retract/lower for low clearance areas.
**Impact:** Clean under low furniture that would block fixed LDS.

---

### is_auto_tear_down_mop_supported
**Bit Index:** 80
**Feature:** Auto Mop Removal
**Description:** Automatically detach mop when returning to dock.
**Impact:** Simplified mop maintenance and drying.

---

### is_small_side_mop_supported
**Bit Index:** 81
**Feature:** Small Side Mop
**Description:** Additional small mop on side for edge mopping.
**Impact:** Better mopping along baseboards and edges.

---

### is_support_side_brush_up_down_supported
**Bit Index:** 82
**Feature:** Side Brush Lift
**Description:** Side brush can lift up/down for carpet vs. hard floor.
**Impact:** Optimal brush position for different floor types.

---

### is_dry_interval_timer_supported
**Bit Index:** 83
**Feature:** Mop Drying Interval Timer
**Description:** Scheduled mop pad drying at set intervals.
**Impact:** Prevent mildew with regular drying cycles.

---

### is_uvc_sterilize_supported
**Bit Index:** 84
**Feature:** UVC Sterilization
**Description:** UVC light for sanitizing mop pads or dustbin.
**Impact:** Kills bacteria and germs on mop or in dust collection.

---

### is_midway_back_to_dock_supported
**Bit Index:** 85
**Feature:** Midway Return to Dock
**Description:** Return to dock during cleaning for mop wash or dust emptying.
**Impact:** Maintain clean mop and empty dustbin during long cleaning sessions.

---

### is_support_main_brush_up_down_supported
**Bit Index:** 86
**Feature:** Main Brush Lift (duplicate)
**Description:** Main brush height adjustment capability.
**Impact:** Same as is_main_brush_up_down_supported_from_str.

---

### is_egg_dance_mode_supported
**Bit Index:** 87
**Feature:** Egg Dance Cleaning Mode
**Description:** Egg-shaped cleaning dance pattern.
**Impact:** Alternative thorough cleaning pattern.

---

### is_mechanical_arm_mode_supported / is_tidyup_zones_supported
**Bit Index:** 89
**Feature:** Mechanical Arm / Tidy-Up Zones
**Description:** Robotic arm for object manipulation or designated tidy-up zones.
**Impact:** Can move small objects or perform tidy-up tasks in specific zones.

---

### is_clean_time_line_supported
**Bit Index:** 91
**Feature:** Clean Timeline View
**Description:** Visual timeline of cleaning sessions.
**Impact:** See cleaning history in chronological timeline format.

---

### is_clean_then_mop_mode_supported
**Bit Index:** 93
**Feature:** Vacuum-Then-Mop Mode
**Description:** Separate vacuum and mop passes (vacuum entire area first, then mop).
**Impact:** More thorough cleaning with dedicated vacuum and mop phases.

---

### is_type_identify_supported
**Bit Index:** 94
**Feature:** Object Type Identification
**Description:** Identify types of objects encountered (shoe, cable, pet waste, etc.).
**Impact:** Better obstacle handling based on object type.

---

### is_support_get_particular_status_supported
**Bit Index:** 96
**Feature:** Get Particular Status
**Description:** API support for querying specific status fields.
**Impact:** More efficient status updates with targeted queries.

---

### is_three_d_mapping_inner_test_supported
**Bit Index:** 97
**Feature:** 3D Mapping Internal Test
**Description:** Beta/test mode for 3D mapping features.
**Impact:** Early access to 3D mapping capabilities.

---

### is_sync_server_name_supported
**Bit Index:** 98
**Feature:** Sync Server Name
**Description:** Synchronize device name with cloud servers.
**Impact:** Consistent device naming across all platforms.

---

### is_should_show_arm_over_load_supported
**Bit Index:** 99
**Feature:** Arm Overload Warning
**Description:** Display warning when mechanical arm is overloaded.
**Impact:** Prevent damage to robotic arm from excessive weight.

---

### is_collect_dust_count_show_supported
**Bit Index:** 100
**Feature:** Dust Collection Count Display
**Description:** Show number of times dustbin has been auto-emptied.
**Impact:** Track dock usage and maintenance needs.

---

### is_support_api_app_stop_grasp_supported
**Bit Index:** 101
**Feature:** App Stop Grasp Command
**Description:** API command to stop robotic arm grasping action.
**Impact:** Emergency stop for arm operations.

---

### is_ctm_with_repeat_supported
**Bit Index:** 102
**Feature:** Custom Time Mode with Repeat
**Description:** Custom scheduled cleaning with repeat patterns.
**Impact:** More flexible scheduling options.

---

### is_side_brush_lift_carpet_supported
**Bit Index:** 104
**Feature:** Side Brush Lift on Carpet
**Description:** Automatically lift side brush when on carpet.
**Impact:** Prevents brush from scattering debris on carpet.

---

### is_detect_wire_carpet_supported
**Bit Index:** 105
**Feature:** Wire/Carpet Detection
**Description:** Detect wires or cables on carpet surfaces.
**Impact:** Avoid tangling in cables on carpeted areas.

---

### is_water_slide_mode_supported
**Bit Index:** 106
**Feature:** Water Slide Mode
**Description:** Gradual water flow adjustment during mopping.
**Impact:** Optimize water usage throughout cleaning session.

---

### is_soak_and_wash_supported
**Bit Index:** 107
**Feature:** Soak and Wash
**Description:** Pre-soak mop pads before washing in dock.
**Impact:** Better mop cleaning for dried or stubborn dirt.

---

### is_clean_efficiency_supported
**Bit Index:** 108
**Feature:** Clean Efficiency Mode
**Description:** Optimized cleaning for maximum efficiency vs. thoroughness balance.
**Impact:** Faster cleaning with acceptable thoroughness trade-off.

---

### is_back_wash_new_smart_supported
**Bit Index:** 109
**Feature:** Smart Back Wash
**Description:** Intelligent mop back-washing with dirt detection.
**Impact:** Wash mop more when it's dirtier, less when cleaner.

---

### is_dual_band_wi_fi_supported
**Bit Index:** 110
**Feature:** Dual-Band WiFi (2.4GHz + 5GHz)
**Description:** Support for both 2.4GHz and 5GHz WiFi networks.
**Impact:** Better WiFi connectivity options and performance.

---

### is_program_mode_supported
**Bit Index:** 111
**Feature:** Program Mode
**Description:** Programmable cleaning sequences and routines.
**Impact:** Create complex cleaning programs with multiple steps.

---

### is_clean_fluid_delivery_supported
**Bit Index:** 112
**Feature:** Cleaning Fluid Delivery
**Description:** Automatic delivery of cleaning solution/detergent.
**Impact:** Enhanced mopping with cleaning agents.

---

### is_carpet_long_haired_ex_supported
**Bit Index:** 113
**Feature:** Long-Haired Carpet Extended Mode
**Description:** Extended/enhanced mode for extra-thick carpets.
**Impact:** Even better performance on very thick pile carpets.

---

### is_over_sea_ctm_supported
**Bit Index:** 114
**Feature:** Overseas Custom Time Mode
**Description:** Custom scheduling for international/overseas regions.
**Impact:** Support for different time zones and regional calendars.

---

### is_full_duples_switch_supported
**Bit Index:** 115
**Feature:** Full Duplex Communication
**Description:** Two-way simultaneous audio communication during video calls.
**Impact:** Real-time conversation through vacuum's speaker/microphone.

---

### is_low_area_access_supported
**Bit Index:** 116
**Feature:** Low Area Access
**Description:** Special mode for accessing very low clearance areas.
**Impact:** Clean under furniture with minimal clearance.

---

### is_follow_low_obs_supported
**Bit Index:** 117
**Feature:** Follow Low Obstacles
**Description:** Navigate closely along low obstacles.
**Impact:** Clean more effectively around low furniture.

---

### is_two_gears_no_collision_supported
**Bit Index:** 118
**Feature:** Two-Gear No Collision Mode
**Description:** Two-level collision avoidance sensitivity.
**Impact:** Adjustable collision avoidance aggressiveness.

---

### is_carpet_shape_type_supported
**Bit Index:** 119
**Feature:** Carpet Shape Type Detection
**Description:** Detect and classify carpet shapes (rectangular, round, runner, etc.).
**Impact:** Better carpet handling based on shape and placement.

---

### is_sr_map_supported
**Bit Index:** 120
**Feature:** SR (Super Resolution) Map
**Description:** High-resolution map rendering and display.
**Impact:** More detailed and accurate map visualization.

---

## Robot Features (Array-based)

These features are checked by verifying if the feature ID exists in the `feature_info` array.

### is_led_status_switch_supported
**Feature ID:** 119
**Feature:** LED Status Switch
**Description:** Control and toggle LED indicators on/off.
**Impact:** Turn off LEDs for bedrooms or light-sensitive areas.

---

### is_multi_floor_supported
**Feature ID:** 120
**Feature:** Multi-Floor Mapping
**Description:** Save and manage maps for multiple floors/levels.
**Impact:** Use same vacuum on multiple floors with different maps.

---

### is_support_fetch_timer_summary
**Feature ID:** 122
**Feature:** Fetch Timer Summary
**Description:** Retrieve summary of all scheduled cleaning timers.
**Impact:** View all schedules at a glance.

---

### is_order_clean_supported
**Feature ID:** 123
**Feature:** Room Order Cleaning
**Description:** Clean rooms in specified order.
**Impact:** Control cleaning sequence (e.g., clean bedroom last).

---

### is_analysis_supported
**Feature ID:** 124
**Feature:** Cleaning Analysis
**Description:** Detailed analysis and statistics of cleaning performance.
**Impact:** Insights into cleaning effectiveness and coverage.

---

### is_remote_supported
**Feature ID:** 125
**Feature:** Remote Control
**Description:** Manual remote control mode via app.
**Impact:** Drive vacuum manually like an RC car.

---

### is_support_voice_control_debug
**Feature ID:** 130
**Feature:** Voice Control Debug Mode
**Description:** Debug mode for voice control features.
**Impact:** Troubleshoot voice command issues.

---

## Model-Specific Features

These features are enabled/disabled based on specific device model whitelists or blacklists.

### is_mop_forbidden_supported
**Model Whitelist:** TANOSV, TOPAZSV, TANOS, TANOSE, TANOSSLITE, TANOSS, TANOSSPLUS, TANOSSMAX, ULTRON, ULTRONLITE, PEARL, RUBYSLITE
**Feature:** Mop-Forbidden Zones
**Description:** Mark areas where mopping is forbidden (carpet protection).
**Impact:** Mop automatically lifts or avoids designated no-mop zones.

---

### is_soft_clean_mode_supported
**Model Whitelist:** TANOSV, TANOSE, TANOS
**Feature:** Soft Clean Mode
**Description:** Gentle cleaning mode for delicate floors.
**Impact:** Reduced suction and brush speed for sensitive surfaces.

---

### is_custom_mode_supported
**Model Blacklist:** TANOS (all except TANOS)
**Feature:** Custom Cleaning Mode
**Description:** User-defined custom cleaning modes.
**Impact:** Create personalized cleaning modes with specific parameters.

---

### is_support_custom_carpet
**Model Whitelist:** ULTRONLITE
**Feature:** Custom Carpet Settings
**Description:** Advanced carpet-specific customization options.
**Impact:** Fine-tune carpet cleaning behavior.

---

### is_show_general_obstacle_supported
**Model Whitelist:** TANOSSPLUS
**Feature:** Show General Obstacles
**Description:** Display generic obstacle markers on map.
**Impact:** See where obstacles were encountered during cleaning.

---

### is_show_obstacle_photo_supported
**Model Whitelist:** TANOSSPLUS, TANOSSMAX, ULTRON
**Feature:** Obstacle Photos
**Description:** Capture and display photos of detected obstacles.
**Impact:** Visual verification of what vacuum avoided.

---

### is_rubber_brush_carpet_supported
**Model Whitelist:** ULTRONLITE
**Feature:** Rubber Brush Carpet Mode
**Description:** Special mode for rubber brush on carpets.
**Impact:** Optimized rubber brush performance on carpets.

---

### is_carpet_pressure_use_origin_paras_supported
**Model Whitelist:** ULTRONLITE
**Feature:** Original Carpet Pressure Parameters
**Description:** Use original firmware carpet pressure settings.
**Impact:** Factory-calibrated carpet cleaning pressure.

---

### is_support_mop_back_pwm_set
**Model Whitelist:** PEARL
**Feature:** Mop Back PWM Settings
**Description:** PWM (Pulse Width Modulation) control for mop motor.
**Impact:** Fine-grained mop vibration control.

---

### is_collect_dust_mode_supported
**Model Blacklist:** PEARL (all except PEARL)
**Feature:** Dust Collection Mode
**Description:** Auto-empty dock dust collection.
**Impact:** Automatic dustbin emptying at dock.

---

## Product Features

These features are determined by hardware capabilities and product variant.

### is_support_water_mode
**Product Features:** MOP_ELECTRONIC_MODULE, MOP_SHAKE_MODULE, MOP_SPIN_MODULE
**Feature:** Water Mode Control
**Description:** Electronic control over water flow for mopping.
**Impact:** Adjustable water flow rates for different floor wetness.

---

### is_pure_clean_mop_supported
**Product Features:** CLEANMODE_PURECLEANMOP
**Feature:** Pure Clean Mop Mode
**Description:** Ultra-clean mopping mode for pristine floors.
**Impact:** Maximum mopping effectiveness for deep cleaning.

---

### is_new_remote_view_supported
**Product Features:** REMOTE_BACK
**Feature:** New Remote View Interface
**Description:** Updated UI for remote control view.
**Impact:** Improved user experience for manual control.

---

### is_max_plus_mode_supported
**Product Features:** CLEANMODE_MAXPLUS
**Feature:** Max+ Suction Mode
**Description:** Maximum suction power mode.
**Impact:** Highest cleaning power for heavily soiled areas.

---

### is_none_pure_clean_mop_with_max_plus
**Product Features:** CLEANMODE_NONE_PURECLEANMOP_WITH_MAXPLUS
**Feature:** Max+ Without Pure Clean Mop
**Description:** Max+ suction available but not pure clean mop mode.
**Impact:** High suction models without advanced mopping.

---

### is_clean_route_setting_supported
**Product Features:** MOP_SHAKE_MODULE, MOP_SPIN_MODULE
**Feature:** Clean Route Settings
**Description:** Configure cleaning route patterns.
**Impact:** Choose between different cleaning patterns (zigzag, edge-first, etc.).

---

### is_mop_shake_module_supported
**Product Features:** MOP_SHAKE_MODULE
**Feature:** Vibrating/Shaking Mop Module
**Description:** Hardware vibrating mop for better cleaning.
**Impact:** Enhanced mopping effectiveness through vibration.

---

### is_customized_clean_supported
**Product Features:** MOP_SHAKE_MODULE, MOP_SPIN_MODULE
**Feature:** Customized Clean Settings
**Description:** Advanced customization for mop-equipped models.
**Impact:** Detailed control over mopping parameters.

