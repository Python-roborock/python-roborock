# CHANGELOG

<!-- version list -->

## v4.2.0 (2025-12-30)

### Chores

- Add end to end tests for Q10 devices
  ([#721](https://github.com/Python-roborock/python-roborock/pull/721),
  [`8d76119`](https://github.com/Python-roborock/python-roborock/commit/8d761194bc1daaa82564fc49e3ef63f85a209dba))

- Remove unused timeout field ([#721](https://github.com/Python-roborock/python-roborock/pull/721),
  [`8d76119`](https://github.com/Python-roborock/python-roborock/commit/8d761194bc1daaa82564fc49e3ef63f85a209dba))

### Features

- Recognize Q10 devices and add a command trait
  ([#721](https://github.com/Python-roborock/python-roborock/pull/721),
  [`8d76119`](https://github.com/Python-roborock/python-roborock/commit/8d761194bc1daaa82564fc49e3ef63f85a209dba))


## v4.1.1 (2025-12-29)

### Bug Fixes

- Fix CLI to no longer depend on old API
  ([#717](https://github.com/Python-roborock/python-roborock/pull/717),
  [`a4fde4a`](https://github.com/Python-roborock/python-roborock/commit/a4fde4a1756dee6d631a1eab24e0a57bf68af6e6))

### Chores

- Fix cli lint errors ([#717](https://github.com/Python-roborock/python-roborock/pull/717),
  [`a4fde4a`](https://github.com/Python-roborock/python-roborock/commit/a4fde4a1756dee6d631a1eab24e0a57bf68af6e6))


## v4.1.0 (2025-12-29)

### Bug Fixes

- Return self for classmethods of roborockmodeenum
  ([#720](https://github.com/Python-roborock/python-roborock/pull/720),
  [`0cc41e8`](https://github.com/Python-roborock/python-roborock/commit/0cc41e8127740b5f763d7dd2735e7427e4ae9afe))

### Features

- Expose prefer-cache to create_device_manager caller
  ([#719](https://github.com/Python-roborock/python-roborock/pull/719),
  [`1d098d6`](https://github.com/Python-roborock/python-roborock/commit/1d098d6775d86a8ffd425d42bf2a6f8cd8bcc9a7))


## v4.0.2 (2025-12-29)

### Bug Fixes

- Add b01 q10 protocol encoding/decoding and tests
  ([#718](https://github.com/Python-roborock/python-roborock/pull/718),
  [`656f715`](https://github.com/Python-roborock/python-roborock/commit/656f715807c7605e9b0ce674c12b4fd0ad4a549f))

- Support unknown q10 DPS enum codes
  ([#718](https://github.com/Python-roborock/python-roborock/pull/718),
  [`656f715`](https://github.com/Python-roborock/python-roborock/commit/656f715807c7605e9b0ce674c12b4fd0ad4a549f))


## v4.0.1 (2025-12-29)

### Bug Fixes

- Fix wind and water mappings for Q7
  ([#716](https://github.com/Python-roborock/python-roborock/pull/716),
  [`421a9c4`](https://github.com/Python-roborock/python-roborock/commit/421a9c4970e8dc8e30552025ad37326d318476fe))

- Fix wind and water mappings for Q7 (#715)
  ([#716](https://github.com/Python-roborock/python-roborock/pull/716),
  [`421a9c4`](https://github.com/Python-roborock/python-roborock/commit/421a9c4970e8dc8e30552025ad37326d318476fe))

- Improve device startup connection reliability for L01 devices
  ([#708](https://github.com/Python-roborock/python-roborock/pull/708),
  [`9cf83a4`](https://github.com/Python-roborock/python-roborock/commit/9cf83a4a762e03e70ed59fb5b1c1982ff52b43b2))

- Update device startup connection behavior
  ([#708](https://github.com/Python-roborock/python-roborock/pull/708),
  [`9cf83a4`](https://github.com/Python-roborock/python-roborock/commit/9cf83a4a762e03e70ed59fb5b1c1982ff52b43b2))

### Chores

- Update tests/e2e/test_device_manager.py
  ([#708](https://github.com/Python-roborock/python-roborock/pull/708),
  [`9cf83a4`](https://github.com/Python-roborock/python-roborock/commit/9cf83a4a762e03e70ed59fb5b1c1982ff52b43b2))


## v4.0.0 (2025-12-29)

### Bug Fixes

- Allow startup with unsupported devices
  ([#707](https://github.com/Python-roborock/python-roborock/pull/707),
  [`7e40857`](https://github.com/Python-roborock/python-roborock/commit/7e40857d0e723f73e4501e7be6068ffa12ebd086))

- Properly shutdown the context in the CLI
  ([#710](https://github.com/Python-roborock/python-roborock/pull/710),
  [`bf31b9b`](https://github.com/Python-roborock/python-roborock/commit/bf31b9b5e7bc22b04e15791cbbcca47e08bcef34))

### Chores

- Add an end to end device manager test
  ([#705](https://github.com/Python-roborock/python-roborock/pull/705),
  [`5e5b9d3`](https://github.com/Python-roborock/python-roborock/commit/5e5b9d38a542a34b486edd21a0fc27fbea9221ef))

- Add end to end tests of the device cache
  ([#705](https://github.com/Python-roborock/python-roborock/pull/705),
  [`5e5b9d3`](https://github.com/Python-roborock/python-roborock/commit/5e5b9d38a542a34b486edd21a0fc27fbea9221ef))

- Add explicit Q7 request message handling code
  ([#712](https://github.com/Python-roborock/python-roborock/pull/712),
  [`a0aee33`](https://github.com/Python-roborock/python-roborock/commit/a0aee338539a060b31b156d607afa9d476e31f95))

- Apply suggestions from code review
  ([#707](https://github.com/Python-roborock/python-roborock/pull/707),
  [`7e40857`](https://github.com/Python-roborock/python-roborock/commit/7e40857d0e723f73e4501e7be6068ffa12ebd086))

- Fix exception catching ([#710](https://github.com/Python-roborock/python-roborock/pull/710),
  [`bf31b9b`](https://github.com/Python-roborock/python-roborock/commit/bf31b9b5e7bc22b04e15791cbbcca47e08bcef34))

- Fix formatting in tests. ([#714](https://github.com/Python-roborock/python-roborock/pull/714),
  [`e00ce88`](https://github.com/Python-roborock/python-roborock/commit/e00ce886ba8012189c88e3f3a01b8f5d8cb4124e))

- Fix lint errors in code mappings test
  ([#711](https://github.com/Python-roborock/python-roborock/pull/711),
  [`4725574`](https://github.com/Python-roborock/python-roborock/commit/4725574cb8f14c13e5b66e5051da83d6f2670456))

- Fix lint errors in q7 protocol tests
  ([#712](https://github.com/Python-roborock/python-roborock/pull/712),
  [`a0aee33`](https://github.com/Python-roborock/python-roborock/commit/a0aee338539a060b31b156d607afa9d476e31f95))

- Fix lint formatting ([#707](https://github.com/Python-roborock/python-roborock/pull/707),
  [`7e40857`](https://github.com/Python-roborock/python-roborock/commit/7e40857d0e723f73e4501e7be6068ffa12ebd086))

- Fix protocol test paths ([#712](https://github.com/Python-roborock/python-roborock/pull/712),
  [`a0aee33`](https://github.com/Python-roborock/python-roborock/commit/a0aee338539a060b31b156d607afa9d476e31f95))

- Improve error handling for session loop
  ([#710](https://github.com/Python-roborock/python-roborock/pull/710),
  [`bf31b9b`](https://github.com/Python-roborock/python-roborock/commit/bf31b9b5e7bc22b04e15791cbbcca47e08bcef34))

- Split up test_containers.py into data subdirectories
  ([#714](https://github.com/Python-roborock/python-roborock/pull/714),
  [`e00ce88`](https://github.com/Python-roborock/python-roborock/commit/e00ce886ba8012189c88e3f3a01b8f5d8cb4124e))

- Update diagnostics counters ([#707](https://github.com/Python-roborock/python-roborock/pull/707),
  [`7e40857`](https://github.com/Python-roborock/python-roborock/commit/7e40857d0e723f73e4501e7be6068ffa12ebd086))

- Update error building tests ([#712](https://github.com/Python-roborock/python-roborock/pull/712),
  [`a0aee33`](https://github.com/Python-roborock/python-roborock/commit/a0aee338539a060b31b156d607afa9d476e31f95))

### Features

- Allow RoborockModeEnum parsing by either enum name, value name, or code
  ([#711](https://github.com/Python-roborock/python-roborock/pull/711),
  [`4725574`](https://github.com/Python-roborock/python-roborock/commit/4725574cb8f14c13e5b66e5051da83d6f2670456))

- Allow RoborockModeEnum parsing by either enum name, value name, or code.
  ([#711](https://github.com/Python-roborock/python-roborock/pull/711),
  [`4725574`](https://github.com/Python-roborock/python-roborock/commit/4725574cb8f14c13e5b66e5051da83d6f2670456))

- **api**: Remove original Cloud and Local APIs
  ([#713](https://github.com/Python-roborock/python-roborock/pull/713),
  [`557810f`](https://github.com/Python-roborock/python-roborock/commit/557810f2d7ad4f56c94d6a981223f90bafdd0b5a))

### Breaking Changes

- **api**: Removes older cloud and local APIs.


## v3.21.1 (2025-12-24)

### Bug Fixes

- Fix typing for send() for q7 ([#706](https://github.com/Python-roborock/python-roborock/pull/706),
  [`1d32f2e`](https://github.com/Python-roborock/python-roborock/commit/1d32f2ef438f34286bb0ed1714d0e7479851a8a8))


## v3.21.0 (2025-12-23)

### Bug Fixes

- Add a hook for handling background rate limit errors
  ([#695](https://github.com/Python-roborock/python-roborock/pull/695),
  [`e38bc9f`](https://github.com/Python-roborock/python-roborock/commit/e38bc9f10bad27b9622d1f6216339426e00d239d))

### Chores

- Add protocol snapshot tests for the mqtt and local e2e tests
  ([#697](https://github.com/Python-roborock/python-roborock/pull/697),
  [`6293a67`](https://github.com/Python-roborock/python-roborock/commit/6293a676e508cb42acf17852c37bf6f69547636a))

- Add protocol snapshot tests for the mqtt and local e2e tests.
  ([#697](https://github.com/Python-roborock/python-roborock/pull/697),
  [`6293a67`](https://github.com/Python-roborock/python-roborock/commit/6293a676e508cb42acf17852c37bf6f69547636a))

- Address co-pilot review feedback
  ([#699](https://github.com/Python-roborock/python-roborock/pull/699),
  [`c317f8e`](https://github.com/Python-roborock/python-roborock/commit/c317f8e4e6d4deda755b511f0c382db7fd68b911))

- Fix lint ([#697](https://github.com/Python-roborock/python-roborock/pull/697),
  [`6293a67`](https://github.com/Python-roborock/python-roborock/commit/6293a676e508cb42acf17852c37bf6f69547636a))

- Fix lint errors ([#704](https://github.com/Python-roborock/python-roborock/pull/704),
  [`b9a241c`](https://github.com/Python-roborock/python-roborock/commit/b9a241c9274a9a204ac5e7c3854e239f64c819c0))

- Fix lint errors ([#697](https://github.com/Python-roborock/python-roborock/pull/697),
  [`6293a67`](https://github.com/Python-roborock/python-roborock/commit/6293a676e508cb42acf17852c37bf6f69547636a))

- Fix lint errors ([#695](https://github.com/Python-roborock/python-roborock/pull/695),
  [`e38bc9f`](https://github.com/Python-roborock/python-roborock/commit/e38bc9f10bad27b9622d1f6216339426e00d239d))

- Fix lint errors ([#699](https://github.com/Python-roborock/python-roborock/pull/699),
  [`c317f8e`](https://github.com/Python-roborock/python-roborock/commit/c317f8e4e6d4deda755b511f0c382db7fd68b911))

- Fix merge conflicts ([#697](https://github.com/Python-roborock/python-roborock/pull/697),
  [`6293a67`](https://github.com/Python-roborock/python-roborock/commit/6293a676e508cb42acf17852c37bf6f69547636a))

- Organize test fixtures ([#699](https://github.com/Python-roborock/python-roborock/pull/699),
  [`c317f8e`](https://github.com/Python-roborock/python-roborock/commit/c317f8e4e6d4deda755b511f0c382db7fd68b911))

- Remove duplicate captured request log
  ([#699](https://github.com/Python-roborock/python-roborock/pull/699),
  [`c317f8e`](https://github.com/Python-roborock/python-roborock/commit/c317f8e4e6d4deda755b511f0c382db7fd68b911))

- Remove duplicate params ([#697](https://github.com/Python-roborock/python-roborock/pull/697),
  [`6293a67`](https://github.com/Python-roborock/python-roborock/commit/6293a676e508cb42acf17852c37bf6f69547636a))

- Remove unnecessary whitespace
  ([#697](https://github.com/Python-roborock/python-roborock/pull/697),
  [`6293a67`](https://github.com/Python-roborock/python-roborock/commit/6293a676e508cb42acf17852c37bf6f69547636a))

- Resolving merge conflict ([#697](https://github.com/Python-roborock/python-roborock/pull/697),
  [`6293a67`](https://github.com/Python-roborock/python-roborock/commit/6293a676e508cb42acf17852c37bf6f69547636a))

- Small tweaks to test fixtures
  ([#704](https://github.com/Python-roborock/python-roborock/pull/704),
  [`b9a241c`](https://github.com/Python-roborock/python-roborock/commit/b9a241c9274a9a204ac5e7c3854e239f64c819c0))

- Update device test snapshots ([#704](https://github.com/Python-roborock/python-roborock/pull/704),
  [`b9a241c`](https://github.com/Python-roborock/python-roborock/commit/b9a241c9274a9a204ac5e7c3854e239f64c819c0))

- Update test fixtures ([#704](https://github.com/Python-roborock/python-roborock/pull/704),
  [`b9a241c`](https://github.com/Python-roborock/python-roborock/commit/b9a241c9274a9a204ac5e7c3854e239f64c819c0))

- **deps-dev**: Bump pre-commit from 4.5.0 to 4.5.1
  ([#701](https://github.com/Python-roborock/python-roborock/pull/701),
  [`8cd51cc`](https://github.com/Python-roborock/python-roborock/commit/8cd51cce07a244813f26b169f6f97b457c6a629f))

- **deps-dev**: Bump ruff from 0.14.9 to 0.14.10
  ([#700](https://github.com/Python-roborock/python-roborock/pull/700),
  [`942d3a1`](https://github.com/Python-roborock/python-roborock/commit/942d3a1acc335726405decc3a7fc7b7b2fd6e698))

### Features

- Revert whitespace change. ([#704](https://github.com/Python-roborock/python-roborock/pull/704),
  [`b9a241c`](https://github.com/Python-roborock/python-roborock/commit/b9a241c9274a9a204ac5e7c3854e239f64c819c0))

- Small tweaks to test fixtures
  ([#704](https://github.com/Python-roborock/python-roborock/pull/704),
  [`b9a241c`](https://github.com/Python-roborock/python-roborock/commit/b9a241c9274a9a204ac5e7c3854e239f64c819c0))


## v3.20.1 (2025-12-22)

### Bug Fixes

- Improve debug logs redaction ([#698](https://github.com/Python-roborock/python-roborock/pull/698),
  [`067794c`](https://github.com/Python-roborock/python-roborock/commit/067794c0b24847520b423fdaacda679aab550cbd))

### Chores

- Address co-pilot readability comments
  ([#698](https://github.com/Python-roborock/python-roborock/pull/698),
  [`067794c`](https://github.com/Python-roborock/python-roborock/commit/067794c0b24847520b423fdaacda679aab550cbd))


## v3.20.0 (2025-12-22)

### Bug Fixes

- Catch broad exception ([#690](https://github.com/Python-roborock/python-roborock/pull/690),
  [`f9f8e43`](https://github.com/Python-roborock/python-roborock/commit/f9f8e43ca97f1136191db92174e937fc1906822d))

- Lower log level for mqtt channel publish exceptions
  ([#696](https://github.com/Python-roborock/python-roborock/pull/696),
  [`642004a`](https://github.com/Python-roborock/python-roborock/commit/642004a3d7f439f7d614aa439e6705377c626a11))

- Reduce log level of decode errors
  ([#691](https://github.com/Python-roborock/python-roborock/pull/691),
  [`98d89f0`](https://github.com/Python-roborock/python-roborock/commit/98d89f027c57195869b65123c8396a20e7a7d648))

- Try to fix fan setting ([#690](https://github.com/Python-roborock/python-roborock/pull/690),
  [`f9f8e43`](https://github.com/Python-roborock/python-roborock/commit/f9f8e43ca97f1136191db92174e937fc1906822d))

### Chores

- Add self.send ([#690](https://github.com/Python-roborock/python-roborock/pull/690),
  [`f9f8e43`](https://github.com/Python-roborock/python-roborock/commit/f9f8e43ca97f1136191db92174e937fc1906822d))

- Add testing ([#690](https://github.com/Python-roborock/python-roborock/pull/690),
  [`f9f8e43`](https://github.com/Python-roborock/python-roborock/commit/f9f8e43ca97f1136191db92174e937fc1906822d))

- Address PR comments ([#690](https://github.com/Python-roborock/python-roborock/pull/690),
  [`f9f8e43`](https://github.com/Python-roborock/python-roborock/commit/f9f8e43ca97f1136191db92174e937fc1906822d))

- Change typing ([#690](https://github.com/Python-roborock/python-roborock/pull/690),
  [`f9f8e43`](https://github.com/Python-roborock/python-roborock/commit/f9f8e43ca97f1136191db92174e937fc1906822d))

- Fix tests ([#691](https://github.com/Python-roborock/python-roborock/pull/691),
  [`98d89f0`](https://github.com/Python-roborock/python-roborock/commit/98d89f027c57195869b65123c8396a20e7a7d648))

- More debug logs and error handling
  ([#690](https://github.com/Python-roborock/python-roborock/pull/690),
  [`f9f8e43`](https://github.com/Python-roborock/python-roborock/commit/f9f8e43ca97f1136191db92174e937fc1906822d))

- Move send and add docs ([#690](https://github.com/Python-roborock/python-roborock/pull/690),
  [`f9f8e43`](https://github.com/Python-roborock/python-roborock/commit/f9f8e43ca97f1136191db92174e937fc1906822d))

- Update tests ([#691](https://github.com/Python-roborock/python-roborock/pull/691),
  [`98d89f0`](https://github.com/Python-roborock/python-roborock/commit/98d89f027c57195869b65123c8396a20e7a7d648))

### Features

- Add some basic setters for q7
  ([#690](https://github.com/Python-roborock/python-roborock/pull/690),
  [`f9f8e43`](https://github.com/Python-roborock/python-roborock/commit/f9f8e43ca97f1136191db92174e937fc1906822d))

- Add some more actions ([#690](https://github.com/Python-roborock/python-roborock/pull/690),
  [`f9f8e43`](https://github.com/Python-roborock/python-roborock/commit/f9f8e43ca97f1136191db92174e937fc1906822d))


## v3.19.1 (2025-12-20)

### Bug Fixes

- Revert A01 padding ([#694](https://github.com/Python-roborock/python-roborock/pull/694),
  [`ac622cc`](https://github.com/Python-roborock/python-roborock/commit/ac622cc07b497b03981fadd97c039555c31a0bae))

### Chores

- Update snapshot ([#694](https://github.com/Python-roborock/python-roborock/pull/694),
  [`ac622cc`](https://github.com/Python-roborock/python-roborock/commit/ac622cc07b497b03981fadd97c039555c31a0bae))


## v3.19.0 (2025-12-17)

### Bug Fixes

- Handle AppInitStatus with omitted new_feature_info_str
  ([#688](https://github.com/Python-roborock/python-roborock/pull/688),
  [`aaeee22`](https://github.com/Python-roborock/python-roborock/commit/aaeee224bc2a715f04ef05b20ef75eb0d2aaa0b9))

### Chores

- Add additional test coverage for default string value
  ([#688](https://github.com/Python-roborock/python-roborock/pull/688),
  [`aaeee22`](https://github.com/Python-roborock/python-roborock/commit/aaeee224bc2a715f04ef05b20ef75eb0d2aaa0b9))

- Add snapshot tests for device payloads
  ([#676](https://github.com/Python-roborock/python-roborock/pull/676),
  [`cd7ef7c`](https://github.com/Python-roborock/python-roborock/commit/cd7ef7c96a16568efd14e29013cbbfded8fe7d86))

- Add socket based tests for the new APIs
  ([#677](https://github.com/Python-roborock/python-roborock/pull/677),
  [`7d113db`](https://github.com/Python-roborock/python-roborock/commit/7d113db6ea75b4864b7edb1657535ad4dc2b9f8f))

- Apply co-pilot suggestion for dataclass initialization
  ([#673](https://github.com/Python-roborock/python-roborock/pull/673),
  [`33c174b`](https://github.com/Python-roborock/python-roborock/commit/33c174b0685c4dc00df6a81437e9b9995934eb61))

- Clean up tests from previous pr
  ([#687](https://github.com/Python-roborock/python-roborock/pull/687),
  [`211429b`](https://github.com/Python-roborock/python-roborock/commit/211429bdcf188bf248d1f28f123c6297016b458b))

- Fix lint errors ([#676](https://github.com/Python-roborock/python-roborock/pull/676),
  [`cd7ef7c`](https://github.com/Python-roborock/python-roborock/commit/cd7ef7c96a16568efd14e29013cbbfded8fe7d86))

- Fix lint errors in test_device_manager.py
  ([#673](https://github.com/Python-roborock/python-roborock/pull/673),
  [`33c174b`](https://github.com/Python-roborock/python-roborock/commit/33c174b0685c4dc00df6a81437e9b9995934eb61))

- Fix local session ([#677](https://github.com/Python-roborock/python-roborock/pull/677),
  [`7d113db`](https://github.com/Python-roborock/python-roborock/commit/7d113db6ea75b4864b7edb1657535ad4dc2b9f8f))

- Remove duplicate test ([#673](https://github.com/Python-roborock/python-roborock/pull/673),
  [`33c174b`](https://github.com/Python-roborock/python-roborock/commit/33c174b0685c4dc00df6a81437e9b9995934eb61))

- Remove unnecessary whitespace
  ([#676](https://github.com/Python-roborock/python-roborock/pull/676),
  [`cd7ef7c`](https://github.com/Python-roborock/python-roborock/commit/cd7ef7c96a16568efd14e29013cbbfded8fe7d86))

- Update default value for new feature string to empty string
  ([#688](https://github.com/Python-roborock/python-roborock/pull/688),
  [`aaeee22`](https://github.com/Python-roborock/python-roborock/commit/aaeee224bc2a715f04ef05b20ef75eb0d2aaa0b9))

- Update roborock/diagnostics.py
  ([#673](https://github.com/Python-roborock/python-roborock/pull/673),
  [`33c174b`](https://github.com/Python-roborock/python-roborock/commit/33c174b0685c4dc00df6a81437e9b9995934eb61))

- Update tests/conftest.py ([#676](https://github.com/Python-roborock/python-roborock/pull/676),
  [`cd7ef7c`](https://github.com/Python-roborock/python-roborock/commit/cd7ef7c96a16568efd14e29013cbbfded8fe7d86))

### Features

- Add diagnostics library for tracking stats/counters
  ([#673](https://github.com/Python-roborock/python-roborock/pull/673),
  [`33c174b`](https://github.com/Python-roborock/python-roborock/commit/33c174b0685c4dc00df6a81437e9b9995934eb61))


## v3.18.0 (2025-12-17)

### Bug Fixes

- Use value instead of name to get lower cased
  ([#686](https://github.com/Python-roborock/python-roborock/pull/686),
  [`728e53a`](https://github.com/Python-roborock/python-roborock/commit/728e53a44949c9044fc64e53725fe0103b43b4a8))

### Chores

- Fix pydoc string ([#674](https://github.com/Python-roborock/python-roborock/pull/674),
  [`c576d5f`](https://github.com/Python-roborock/python-roborock/commit/c576d5ff1e1247c20a1b1c0f4895b8870f929734))

- Fix typo in README.md ([#685](https://github.com/Python-roborock/python-roborock/pull/685),
  [`d01287a`](https://github.com/Python-roborock/python-roborock/commit/d01287a3a9883ee9698fbe6ad9bd95e4e8779b5e))

- Improve library user documentation
  ([#685](https://github.com/Python-roborock/python-roborock/pull/685),
  [`d01287a`](https://github.com/Python-roborock/python-roborock/commit/d01287a3a9883ee9698fbe6ad9bd95e4e8779b5e))

- Remove unnecessary assert in test
  ([#674](https://github.com/Python-roborock/python-roborock/pull/674),
  [`c576d5f`](https://github.com/Python-roborock/python-roborock/commit/c576d5ff1e1247c20a1b1c0f4895b8870f929734))

- Style cleanup re-raising a bare exception
  ([#674](https://github.com/Python-roborock/python-roborock/pull/674),
  [`c576d5f`](https://github.com/Python-roborock/python-roborock/commit/c576d5ff1e1247c20a1b1c0f4895b8870f929734))

- Update roborock/data/code_mappings.py
  ([#686](https://github.com/Python-roborock/python-roborock/pull/686),
  [`728e53a`](https://github.com/Python-roborock/python-roborock/commit/728e53a44949c9044fc64e53725fe0103b43b4a8))

- **deps-dev**: Bump pytest from 8.4.2 to 9.0.2
  ([#681](https://github.com/Python-roborock/python-roborock/pull/681),
  [`5520a56`](https://github.com/Python-roborock/python-roborock/commit/5520a562f1913e11dea6a007b4b2accb3d30d222))

### Features

- Allow device manager to perform rediscovery of devices
  ([#674](https://github.com/Python-roborock/python-roborock/pull/674),
  [`c576d5f`](https://github.com/Python-roborock/python-roborock/commit/c576d5ff1e1247c20a1b1c0f4895b8870f929734))

- Improvements to B01 for HA integration
  ([#686](https://github.com/Python-roborock/python-roborock/pull/686),
  [`728e53a`](https://github.com/Python-roborock/python-roborock/commit/728e53a44949c9044fc64e53725fe0103b43b4a8))


## v3.17.0 (2025-12-15)

### Chores

- **deps**: Bump python-semantic-release/publish-action
  ([#679](https://github.com/Python-roborock/python-roborock/pull/679),
  [`3cf1a9a`](https://github.com/Python-roborock/python-roborock/commit/3cf1a9af0d65482c65a14b2d266ff3b134dcb6f8))

- **deps**: Bump python-semantic-release/python-semantic-release
  ([#680](https://github.com/Python-roborock/python-roborock/pull/680),
  [`2afa86c`](https://github.com/Python-roborock/python-roborock/commit/2afa86cdf234ef5626dbf9f2f778d0a3b23ac5a7))

- **deps-dev**: Bump mypy from 1.19.0 to 1.19.1
  ([#683](https://github.com/Python-roborock/python-roborock/pull/683),
  [`bfb2c63`](https://github.com/Python-roborock/python-roborock/commit/bfb2c63e85d96c2c663686e05c598d0e724685a9))

- **deps-dev**: Bump ruff from 0.14.6 to 0.14.9
  ([#682](https://github.com/Python-roborock/python-roborock/pull/682),
  [`cfd51e4`](https://github.com/Python-roborock/python-roborock/commit/cfd51e4a75eecb66f60ac137ece36b2fa7583ea9))

### Features

- Improvements to B01 for HA integration
  ([#678](https://github.com/Python-roborock/python-roborock/pull/678),
  [`97fb0b7`](https://github.com/Python-roborock/python-roborock/commit/97fb0b75ff4aa164d81340d276991537e0c9662e))


## v3.16.1 (2025-12-14)

### Bug Fixes

- Share a HealthManager instance across all mqtt channels
  ([#672](https://github.com/Python-roborock/python-roborock/pull/672),
  [`4ad95dd`](https://github.com/Python-roborock/python-roborock/commit/4ad95ddee4d4d4cd64c7908f150c71d81f45e705))


## v3.16.0 (2025-12-14)

### Bug Fixes

- Fix bugs in the subscription idle timeout
  ([#665](https://github.com/Python-roborock/python-roborock/pull/665),
  [`85b7bee`](https://github.com/Python-roborock/python-roborock/commit/85b7beeb810cfb3d501658cd44f06b2c0052ca33))

- Harden the device connection logic used in startup
  ([#666](https://github.com/Python-roborock/python-roborock/pull/666),
  [`19703f4`](https://github.com/Python-roborock/python-roborock/commit/19703f42fe692a38f8f8639b1136a7585eae76fc))

- Harden the initial startup logic
  ([#666](https://github.com/Python-roborock/python-roborock/pull/666),
  [`19703f4`](https://github.com/Python-roborock/python-roborock/commit/19703f42fe692a38f8f8639b1136a7585eae76fc))

### Chores

- Apply suggestions from code review
  ([#675](https://github.com/Python-roborock/python-roborock/pull/675),
  [`ab2de5b`](https://github.com/Python-roborock/python-roborock/commit/ab2de5bda7b8e1ff1ad46c7f2bf3b39dc9af4ace))

- Clarify comments and docstrings
  ([#666](https://github.com/Python-roborock/python-roborock/pull/666),
  [`19703f4`](https://github.com/Python-roborock/python-roborock/commit/19703f42fe692a38f8f8639b1136a7585eae76fc))

- Fix logging ([#666](https://github.com/Python-roborock/python-roborock/pull/666),
  [`19703f4`](https://github.com/Python-roborock/python-roborock/commit/19703f42fe692a38f8f8639b1136a7585eae76fc))

- Reduce whitespace changes ([#666](https://github.com/Python-roborock/python-roborock/pull/666),
  [`19703f4`](https://github.com/Python-roborock/python-roborock/commit/19703f42fe692a38f8f8639b1136a7585eae76fc))

- Revert whitespace change ([#666](https://github.com/Python-roborock/python-roborock/pull/666),
  [`19703f4`](https://github.com/Python-roborock/python-roborock/commit/19703f42fe692a38f8f8639b1136a7585eae76fc))

### Features

- Add basic schedule getting ([#675](https://github.com/Python-roborock/python-roborock/pull/675),
  [`ab2de5b`](https://github.com/Python-roborock/python-roborock/commit/ab2de5bda7b8e1ff1ad46c7f2bf3b39dc9af4ace))


## v3.15.0 (2025-12-14)

### Chores

- Address some comments ([#662](https://github.com/Python-roborock/python-roborock/pull/662),
  [`b3664bc`](https://github.com/Python-roborock/python-roborock/commit/b3664bcc0764d1dfbde2af9588dc0821c3ca1317))

- Apply suggestions from code review
  ([#662](https://github.com/Python-roborock/python-roborock/pull/662),
  [`b3664bc`](https://github.com/Python-roborock/python-roborock/commit/b3664bcc0764d1dfbde2af9588dc0821c3ca1317))

- Fix test naming ([#662](https://github.com/Python-roborock/python-roborock/pull/662),
  [`b3664bc`](https://github.com/Python-roborock/python-roborock/commit/b3664bcc0764d1dfbde2af9588dc0821c3ca1317))

- Small tweaks ([#662](https://github.com/Python-roborock/python-roborock/pull/662),
  [`b3664bc`](https://github.com/Python-roborock/python-roborock/commit/b3664bcc0764d1dfbde2af9588dc0821c3ca1317))

- Update roborock/devices/b01_channel.py
  ([#662](https://github.com/Python-roborock/python-roborock/pull/662),
  [`b3664bc`](https://github.com/Python-roborock/python-roborock/commit/b3664bcc0764d1dfbde2af9588dc0821c3ca1317))

- Update snapshot ([#662](https://github.com/Python-roborock/python-roborock/pull/662),
  [`b3664bc`](https://github.com/Python-roborock/python-roborock/commit/b3664bcc0764d1dfbde2af9588dc0821c3ca1317))

### Features

- Add b01 Q7 basic getter support
  ([#662](https://github.com/Python-roborock/python-roborock/pull/662),
  [`b3664bc`](https://github.com/Python-roborock/python-roborock/commit/b3664bcc0764d1dfbde2af9588dc0821c3ca1317))

- Add b01 Q7 support ([#662](https://github.com/Python-roborock/python-roborock/pull/662),
  [`b3664bc`](https://github.com/Python-roborock/python-roborock/commit/b3664bcc0764d1dfbde2af9588dc0821c3ca1317))


## v3.14.3 (2025-12-14)

### Bug Fixes

- Allow firmware version as an optional field
  ([#670](https://github.com/Python-roborock/python-roborock/pull/670),
  [`0f70bf9`](https://github.com/Python-roborock/python-roborock/commit/0f70bf9dd2010c2c72b3b9543d891a1071dc22c4))

### Chores

- Add test for example offline device
  ([#670](https://github.com/Python-roborock/python-roborock/pull/670),
  [`0f70bf9`](https://github.com/Python-roborock/python-roborock/commit/0f70bf9dd2010c2c72b3b9543d891a1071dc22c4))


## v3.14.2 (2025-12-14)

### Bug Fixes

- Additional device logging improvements
  ([#668](https://github.com/Python-roborock/python-roborock/pull/668),
  [`a86db71`](https://github.com/Python-roborock/python-roborock/commit/a86db717a07d24b0e6ab471ee814b0853b523918))

- Improve device logging ([#668](https://github.com/Python-roborock/python-roborock/pull/668),
  [`a86db71`](https://github.com/Python-roborock/python-roborock/commit/a86db717a07d24b0e6ab471ee814b0853b523918))

### Chores

- Further readability improvements to device logging
  ([#668](https://github.com/Python-roborock/python-roborock/pull/668),
  [`a86db71`](https://github.com/Python-roborock/python-roborock/commit/a86db717a07d24b0e6ab471ee814b0853b523918))

- Improve device logging container summary string
  ([#668](https://github.com/Python-roborock/python-roborock/pull/668),
  [`a86db71`](https://github.com/Python-roborock/python-roborock/commit/a86db717a07d24b0e6ab471ee814b0853b523918))


## v3.14.1 (2025-12-14)

### Bug Fixes

- Fix diagnostic data redaction to use camelized keys
  ([#669](https://github.com/Python-roborock/python-roborock/pull/669),
  [`6a20e27`](https://github.com/Python-roborock/python-roborock/commit/6a20e27506d01fbb30683c2d74d26ab073aa3036))

### Chores

- Remove redundant/broken part of the readme
  ([#667](https://github.com/Python-roborock/python-roborock/pull/667),
  [`b629a61`](https://github.com/Python-roborock/python-roborock/commit/b629a61f28f3bb64914a9bc461ce9f7a27a30c35))

- **deps**: Bump pdoc from 15.0.4 to 16.0.0
  ([#652](https://github.com/Python-roborock/python-roborock/pull/652),
  [`5f4c14e`](https://github.com/Python-roborock/python-roborock/commit/5f4c14ead4eda21cd6954e3898d79a6eaa983f62))


## v3.14.0 (2025-12-14)

### Bug Fixes

- Add device logger ([#663](https://github.com/Python-roborock/python-roborock/pull/663),
  [`06d051c`](https://github.com/Python-roborock/python-roborock/commit/06d051c7b8203e23970d52d65abec88a2757227f))

- Update roborock/devices/device.py
  ([#664](https://github.com/Python-roborock/python-roborock/pull/664),
  [`494c5b4`](https://github.com/Python-roborock/python-roborock/commit/494c5b4f2b447f12f5ef90167cad16e08a8230ac))

### Chores

- Add details about test structure
  ([#633](https://github.com/Python-roborock/python-roborock/pull/633),
  [`109d05b`](https://github.com/Python-roborock/python-roborock/commit/109d05ba86275f2cdd65c5cda12fc423cbfb5850))

- Add more tests for already connected devices
  ([#664](https://github.com/Python-roborock/python-roborock/pull/664),
  [`494c5b4`](https://github.com/Python-roborock/python-roborock/commit/494c5b4f2b447f12f5ef90167cad16e08a8230ac))

- Apply suggestions from code review
  ([#663](https://github.com/Python-roborock/python-roborock/pull/663),
  [`06d051c`](https://github.com/Python-roborock/python-roborock/commit/06d051c7b8203e23970d52d65abec88a2757227f))

- Document combined mqtt channels
  ([#633](https://github.com/Python-roborock/python-roborock/pull/633),
  [`109d05b`](https://github.com/Python-roborock/python-roborock/commit/109d05ba86275f2cdd65c5cda12fc423cbfb5850))

- Fix lint errors ([#664](https://github.com/Python-roborock/python-roborock/pull/664),
  [`494c5b4`](https://github.com/Python-roborock/python-roborock/commit/494c5b4f2b447f12f5ef90167cad16e08a8230ac))

- Fix lint errors ([#633](https://github.com/Python-roborock/python-roborock/pull/633),
  [`109d05b`](https://github.com/Python-roborock/python-roborock/commit/109d05ba86275f2cdd65c5cda12fc423cbfb5850))

- Fix lint errors in readme ([#633](https://github.com/Python-roborock/python-roborock/pull/633),
  [`109d05b`](https://github.com/Python-roborock/python-roborock/commit/109d05ba86275f2cdd65c5cda12fc423cbfb5850))

- Fix typo ([#633](https://github.com/Python-roborock/python-roborock/pull/633),
  [`109d05b`](https://github.com/Python-roborock/python-roborock/commit/109d05ba86275f2cdd65c5cda12fc423cbfb5850))

- Update device traits by protocol
  ([#633](https://github.com/Python-roborock/python-roborock/pull/633),
  [`109d05b`](https://github.com/Python-roborock/python-roborock/commit/109d05ba86275f2cdd65c5cda12fc423cbfb5850))

- Update devices documentation with design details
  ([#633](https://github.com/Python-roborock/python-roborock/pull/633),
  [`109d05b`](https://github.com/Python-roborock/python-roborock/commit/109d05ba86275f2cdd65c5cda12fc423cbfb5850))

- Use the existing device logger
  ([#663](https://github.com/Python-roborock/python-roborock/pull/663),
  [`06d051c`](https://github.com/Python-roborock/python-roborock/commit/06d051c7b8203e23970d52d65abec88a2757227f))

### Features

- Add ability to listen for ready devices
  ([#664](https://github.com/Python-roborock/python-roborock/pull/664),
  [`494c5b4`](https://github.com/Python-roborock/python-roborock/commit/494c5b4f2b447f12f5ef90167cad16e08a8230ac))


## v3.13.1 (2025-12-12)

### Bug Fixes

- Clean up some naming ([#635](https://github.com/Python-roborock/python-roborock/pull/635),
  [`9a1a360`](https://github.com/Python-roborock/python-roborock/commit/9a1a3600fb3eff612088e9203a04f795678e9da7))

- Update roborock/devices/traits/b01/__init__.py
  ([#635](https://github.com/Python-roborock/python-roborock/pull/635),
  [`9a1a360`](https://github.com/Python-roborock/python-roborock/commit/9a1a3600fb3eff612088e9203a04f795678e9da7))

- Use strip not split ([#635](https://github.com/Python-roborock/python-roborock/pull/635),
  [`9a1a360`](https://github.com/Python-roborock/python-roborock/commit/9a1a3600fb3eff612088e9203a04f795678e9da7))

### Chores

- Refactor to separate b01 q7 and q10 logic
  ([#635](https://github.com/Python-roborock/python-roborock/pull/635),
  [`9a1a360`](https://github.com/Python-roborock/python-roborock/commit/9a1a3600fb3eff612088e9203a04f795678e9da7))

- Refactor to seperate b01 ss and sc logic
  ([#635](https://github.com/Python-roborock/python-roborock/pull/635),
  [`9a1a360`](https://github.com/Python-roborock/python-roborock/commit/9a1a3600fb3eff612088e9203a04f795678e9da7))

- Share duplicated code ([#635](https://github.com/Python-roborock/python-roborock/pull/635),
  [`9a1a360`](https://github.com/Python-roborock/python-roborock/commit/9a1a3600fb3eff612088e9203a04f795678e9da7))

- Update roborock/devices/device_manager.py
  ([#635](https://github.com/Python-roborock/python-roborock/pull/635),
  [`9a1a360`](https://github.com/Python-roborock/python-roborock/commit/9a1a3600fb3eff612088e9203a04f795678e9da7))

- Update roborock/devices/traits/b01/q7/__init__.py
  ([#635](https://github.com/Python-roborock/python-roborock/pull/635),
  [`9a1a360`](https://github.com/Python-roborock/python-roborock/commit/9a1a3600fb3eff612088e9203a04f795678e9da7))


## v3.13.0 (2025-12-12)

### Bug Fixes

- Update device cache handling in cli
  ([#660](https://github.com/Python-roborock/python-roborock/pull/660),
  [`405a4fb`](https://github.com/Python-roborock/python-roborock/commit/405a4fba281b09269c0a065f79dedfd9dc9b5a8b))

- Update device cache handling in cli.
  ([#660](https://github.com/Python-roborock/python-roborock/pull/660),
  [`405a4fb`](https://github.com/Python-roborock/python-roborock/commit/405a4fba281b09269c0a065f79dedfd9dc9b5a8b))

### Features

- Add additional fields to HomeDataDevice class
  ([#660](https://github.com/Python-roborock/python-roborock/pull/660),
  [`405a4fb`](https://github.com/Python-roborock/python-roborock/commit/405a4fba281b09269c0a065f79dedfd9dc9b5a8b))


## v3.12.2 (2025-12-10)

### Bug Fixes

- Filter tests to be warnings only
  ([#656](https://github.com/Python-roborock/python-roborock/pull/656),
  [`e725eab`](https://github.com/Python-roborock/python-roborock/commit/e725eabab7c498569c5e17be9a7b435c917745f1))

- Handle random length bytes before version bytes
  ([#656](https://github.com/Python-roborock/python-roborock/pull/656),
  [`e725eab`](https://github.com/Python-roborock/python-roborock/commit/e725eabab7c498569c5e17be9a7b435c917745f1))

### Chores

- Add debug to help us determine if buffer is source of problem
  ([#656](https://github.com/Python-roborock/python-roborock/pull/656),
  [`e725eab`](https://github.com/Python-roborock/python-roborock/commit/e725eabab7c498569c5e17be9a7b435c917745f1))

- Apply suggestions from code review
  ([#656](https://github.com/Python-roborock/python-roborock/pull/656),
  [`e725eab`](https://github.com/Python-roborock/python-roborock/commit/e725eabab7c498569c5e17be9a7b435c917745f1))

- Only log if remaining ([#656](https://github.com/Python-roborock/python-roborock/pull/656),
  [`e725eab`](https://github.com/Python-roborock/python-roborock/commit/e725eabab7c498569c5e17be9a7b435c917745f1))

- Update roborock/protocol.py ([#656](https://github.com/Python-roborock/python-roborock/pull/656),
  [`e725eab`](https://github.com/Python-roborock/python-roborock/commit/e725eabab7c498569c5e17be9a7b435c917745f1))


## v3.12.1 (2025-12-10)

### Bug Fixes

- Redact additional keys from diagnostic data
  ([#659](https://github.com/Python-roborock/python-roborock/pull/659),
  [`0330755`](https://github.com/Python-roborock/python-roborock/commit/033075559fb63f696073e235d36f4a906c324881))

### Chores

- Update comments on redaction ([#659](https://github.com/Python-roborock/python-roborock/pull/659),
  [`0330755`](https://github.com/Python-roborock/python-roborock/commit/033075559fb63f696073e235d36f4a906c324881))


## v3.12.0 (2025-12-10)

### Bug Fixes

- Align V4 code login with app ([#657](https://github.com/Python-roborock/python-roborock/pull/657),
  [`2328d45`](https://github.com/Python-roborock/python-roborock/commit/2328d4596c6bda35686944880b601c35b390ac9c))

### Chores

- **deps**: Bump mypy from 1.18.2 to 1.19.0
  ([#654](https://github.com/Python-roborock/python-roborock/pull/654),
  [`2799a19`](https://github.com/Python-roborock/python-roborock/commit/2799a19263a511a2d141a97cdb6e9814961a4b0f))

- **deps**: Bump syrupy from 4.9.1 to 5.0.0
  ([#655](https://github.com/Python-roborock/python-roborock/pull/655),
  [`cc2d00f`](https://github.com/Python-roborock/python-roborock/commit/cc2d00fdd21968c0cfe8da8704644dc2c7ff8091))

### Features

- Log when we see a new key we have never seen before for easier reverse engineering
  ([#658](https://github.com/Python-roborock/python-roborock/pull/658),
  [`81dde05`](https://github.com/Python-roborock/python-roborock/commit/81dde05eac61e7dc6e0fdb9eb0b7e0ffc97cf9d8))


## v3.11.1 (2025-12-10)

### Bug Fixes

- Throw MQTT authentication errors as authentication related exceptions
  ([#634](https://github.com/Python-roborock/python-roborock/pull/634),
  [`4ad9bcd`](https://github.com/Python-roborock/python-roborock/commit/4ad9bcdc1eddc3a0698056fce19f33d0ea0a119b))

- Update the exception handling behavior to account for ambiguity
  ([#634](https://github.com/Python-roborock/python-roborock/pull/634),
  [`4ad9bcd`](https://github.com/Python-roborock/python-roborock/commit/4ad9bcdc1eddc3a0698056fce19f33d0ea0a119b))


## v3.11.0 (2025-12-10)

### Features

- Add mappings for cleaning fluid states
  ([#636](https://github.com/Python-roborock/python-roborock/pull/636),
  [`32c717e`](https://github.com/Python-roborock/python-roborock/commit/32c717ebdcc963af691398d176b7175c59d7616c))


## v3.10.10 (2025-12-08)

### Bug Fixes

- Fix exception when sending dyad/zeo requests
  ([#651](https://github.com/Python-roborock/python-roborock/pull/651),
  [`a1014a6`](https://github.com/Python-roborock/python-roborock/commit/a1014a60320c45d82c80c2c47f2cb7cc6f242252))

### Chores

- Fix lint ([#651](https://github.com/Python-roborock/python-roborock/pull/651),
  [`a1014a6`](https://github.com/Python-roborock/python-roborock/commit/a1014a60320c45d82c80c2c47f2cb7cc6f242252))

- Fix tests to be focused on value encoder
  ([#651](https://github.com/Python-roborock/python-roborock/pull/651),
  [`a1014a6`](https://github.com/Python-roborock/python-roborock/commit/a1014a60320c45d82c80c2c47f2cb7cc6f242252))


## v3.10.9 (2025-12-07)

### Bug Fixes

- Convert a01 values ([#647](https://github.com/Python-roborock/python-roborock/pull/647),
  [`f875e7a`](https://github.com/Python-roborock/python-roborock/commit/f875e7a65f5f422da97d0f2881956ec077c8a7df))

- Update tests and conversion logic
  ([#647](https://github.com/Python-roborock/python-roborock/pull/647),
  [`f875e7a`](https://github.com/Python-roborock/python-roborock/commit/f875e7a65f5f422da97d0f2881956ec077c8a7df))

### Chores

- Small changes to comments ([#647](https://github.com/Python-roborock/python-roborock/pull/647),
  [`f875e7a`](https://github.com/Python-roborock/python-roborock/commit/f875e7a65f5f422da97d0f2881956ec077c8a7df))


## v3.10.8 (2025-12-07)

### Bug Fixes

- Encode a01 values as json strings
  ([#645](https://github.com/Python-roborock/python-roborock/pull/645),
  [`7301a2a`](https://github.com/Python-roborock/python-roborock/commit/7301a2a7145b3ffa862b5ae83f2961b1b28b2867))

- Update where the string conversion happens
  ([#645](https://github.com/Python-roborock/python-roborock/pull/645),
  [`7301a2a`](https://github.com/Python-roborock/python-roborock/commit/7301a2a7145b3ffa862b5ae83f2961b1b28b2867))

### Chores

- Remove unnecessary imports ([#645](https://github.com/Python-roborock/python-roborock/pull/645),
  [`7301a2a`](https://github.com/Python-roborock/python-roborock/commit/7301a2a7145b3ffa862b5ae83f2961b1b28b2867))

- Update tests to capture bug fix
  ([#645](https://github.com/Python-roborock/python-roborock/pull/645),
  [`7301a2a`](https://github.com/Python-roborock/python-roborock/commit/7301a2a7145b3ffa862b5ae83f2961b1b28b2867))


## v3.10.7 (2025-12-07)

### Bug Fixes

- Add test coverage for a01 traits
  ([#649](https://github.com/Python-roborock/python-roborock/pull/649),
  [`89874cb`](https://github.com/Python-roborock/python-roborock/commit/89874cb5de97362c29d31f50916b2355e1d3f90f))

### Chores

- Add codecov support ([#646](https://github.com/Python-roborock/python-roborock/pull/646),
  [`3928280`](https://github.com/Python-roborock/python-roborock/commit/39282809217ec6d4b6e0c4f4f7729fbfd48ecadb))

- Add more test coverage for a01 API and fix `False` value handling
  ([#648](https://github.com/Python-roborock/python-roborock/pull/648),
  [`4bd9b18`](https://github.com/Python-roborock/python-roborock/commit/4bd9b18fddf4df6e05c185ff23d8be2d8fa90763))

- Fix lint errors in tests ([#648](https://github.com/Python-roborock/python-roborock/pull/648),
  [`4bd9b18`](https://github.com/Python-roborock/python-roborock/commit/4bd9b18fddf4df6e05c185ff23d8be2d8fa90763))

- Use raw return values ([#649](https://github.com/Python-roborock/python-roborock/pull/649),
  [`89874cb`](https://github.com/Python-roborock/python-roborock/commit/89874cb5de97362c29d31f50916b2355e1d3f90f))


## v3.10.6 (2025-12-07)

### Bug Fixes

- Handle base64 serializing wrong
  ([#643](https://github.com/Python-roborock/python-roborock/pull/643),
  [`d933ec8`](https://github.com/Python-roborock/python-roborock/commit/d933ec82f470fec47339f938065ab70a635112fd))


## v3.10.5 (2025-12-07)

### Bug Fixes

- Consider RPC channel health based on MQTT session
  ([#642](https://github.com/Python-roborock/python-roborock/pull/642),
  [`b1738fe`](https://github.com/Python-roborock/python-roborock/commit/b1738fec4edde302c5f0fb478146faaa3d864ee8))


## v3.10.4 (2025-12-07)

### Bug Fixes

- Lower log level for internal protocol connection details
  ([#637](https://github.com/Python-roborock/python-roborock/pull/637),
  [`6945c6a`](https://github.com/Python-roborock/python-roborock/commit/6945c6ad25f39930cdea23d2f7004824f681a6e7))

- Revert CLIENT_KEEPALIVE back to 60
  ([#641](https://github.com/Python-roborock/python-roborock/pull/641),
  [`632b88b`](https://github.com/Python-roborock/python-roborock/commit/632b88b22e2ac722c5c4849b7b217fa4a88f757c))

### Chores

- Fix lint erors ([#637](https://github.com/Python-roborock/python-roborock/pull/637),
  [`6945c6a`](https://github.com/Python-roborock/python-roborock/commit/6945c6ad25f39930cdea23d2f7004824f681a6e7))

- Remove tests for logging ([#637](https://github.com/Python-roborock/python-roborock/pull/637),
  [`6945c6a`](https://github.com/Python-roborock/python-roborock/commit/6945c6ad25f39930cdea23d2f7004824f681a6e7))


## v3.10.3 (2025-12-06)

### Bug Fixes

- Ensure immediate local connection is attempted
  ([#640](https://github.com/Python-roborock/python-roborock/pull/640),
  [`3c918ae`](https://github.com/Python-roborock/python-roborock/commit/3c918aec33483b93ae9d632cc4ada286b6761b70))

- Fix mqtt rate limiting and broken local connections
  ([#638](https://github.com/Python-roborock/python-roborock/pull/638),
  [`4249769`](https://github.com/Python-roborock/python-roborock/commit/42497696e92dad79147e404be96e73b9e408bd0b))

### Chores

- Add back test case and add test ids
  ([#638](https://github.com/Python-roborock/python-roborock/pull/638),
  [`4249769`](https://github.com/Python-roborock/python-roborock/commit/42497696e92dad79147e404be96e73b9e408bd0b))

- Fix lint errors ([#640](https://github.com/Python-roborock/python-roborock/pull/640),
  [`3c918ae`](https://github.com/Python-roborock/python-roborock/commit/3c918aec33483b93ae9d632cc4ada286b6761b70))

- Fix lint errors ([#638](https://github.com/Python-roborock/python-roborock/pull/638),
  [`4249769`](https://github.com/Python-roborock/python-roborock/commit/42497696e92dad79147e404be96e73b9e408bd0b))

- Update roborock/devices/v1_channel.py
  ([#638](https://github.com/Python-roborock/python-roborock/pull/638),
  [`4249769`](https://github.com/Python-roborock/python-roborock/commit/42497696e92dad79147e404be96e73b9e408bd0b))


## v3.10.2 (2025-12-05)

### Bug Fixes

- Keep MQTT topic subscriptions alive with an idle timeout
  ([#632](https://github.com/Python-roborock/python-roborock/pull/632),
  [`d0d2e42`](https://github.com/Python-roborock/python-roborock/commit/d0d2e425e3005f3f83f4a57079fcef4736171b7a))

### Chores

- Add tests that reproduce key parsing bugs
  ([#631](https://github.com/Python-roborock/python-roborock/pull/631),
  [`87e14a2`](https://github.com/Python-roborock/python-roborock/commit/87e14a265a6c6bbe18fbe63f360ca57ca63db9c3))

- Fix lint errors ([#631](https://github.com/Python-roborock/python-roborock/pull/631),
  [`87e14a2`](https://github.com/Python-roborock/python-roborock/commit/87e14a265a6c6bbe18fbe63f360ca57ca63db9c3))


## v3.10.1 (2025-12-05)

### Bug Fixes

- Add fallback ([#630](https://github.com/Python-roborock/python-roborock/pull/630),
  [`e4fa8c6`](https://github.com/Python-roborock/python-roborock/commit/e4fa8c60bb29978b06704ce22dc4a2cda0e28875))

- Ensure keys are correct type when serializing from data
  ([#630](https://github.com/Python-roborock/python-roborock/pull/630),
  [`e4fa8c6`](https://github.com/Python-roborock/python-roborock/commit/e4fa8c60bb29978b06704ce22dc4a2cda0e28875))

- Ensure keys are valid type when serializing from data
  ([#630](https://github.com/Python-roborock/python-roborock/pull/630),
  [`e4fa8c6`](https://github.com/Python-roborock/python-roborock/commit/e4fa8c60bb29978b06704ce22dc4a2cda0e28875))


## v3.10.0 (2025-12-04)

### Bug Fixes

- Catch UnicodeDecodeError when parsing messages
  ([#629](https://github.com/Python-roborock/python-roborock/pull/629),
  [`e8c3b75`](https://github.com/Python-roborock/python-roborock/commit/e8c3b75a9d3efb8ff79a6d4e8544549a5abe766a))

- Reset keep_alive_task to None
  ([#627](https://github.com/Python-roborock/python-roborock/pull/627),
  [`a802f66`](https://github.com/Python-roborock/python-roborock/commit/a802f66fec913be82a25ae45d96555c2d328964b))

### Chores

- Copilot test ([#627](https://github.com/Python-roborock/python-roborock/pull/627),
  [`a802f66`](https://github.com/Python-roborock/python-roborock/commit/a802f66fec913be82a25ae45d96555c2d328964b))

### Features

- Add comprehensive test coverage for keep-alive functionality
  ([#627](https://github.com/Python-roborock/python-roborock/pull/627),
  [`a802f66`](https://github.com/Python-roborock/python-roborock/commit/a802f66fec913be82a25ae45d96555c2d328964b))

- Add pinging to local client ([#627](https://github.com/Python-roborock/python-roborock/pull/627),
  [`a802f66`](https://github.com/Python-roborock/python-roborock/commit/a802f66fec913be82a25ae45d96555c2d328964b))

### Refactoring

- Address code review feedback on keep-alive tests
  ([#627](https://github.com/Python-roborock/python-roborock/pull/627),
  [`a802f66`](https://github.com/Python-roborock/python-roborock/commit/a802f66fec913be82a25ae45d96555c2d328964b))


## v3.9.3 (2025-12-03)

### Bug Fixes

- Use correct index for clean records
  ([#620](https://github.com/Python-roborock/python-roborock/pull/620),
  [`f129603`](https://github.com/Python-roborock/python-roborock/commit/f1296032e7b8c8c1348882d58e9da5ecc8287eee))


## v3.9.2 (2025-12-03)

### Bug Fixes

- Add device info getters and setters
  ([#614](https://github.com/Python-roborock/python-roborock/pull/614),
  [`ee02a71`](https://github.com/Python-roborock/python-roborock/commit/ee02a71a8d99848256f2bb69533e9d1827f52585))

- Fix issues with the cache clobbering information for each device
  ([#614](https://github.com/Python-roborock/python-roborock/pull/614),
  [`ee02a71`](https://github.com/Python-roborock/python-roborock/commit/ee02a71a8d99848256f2bb69533e9d1827f52585))

- Update DeviceCache interface ([#614](https://github.com/Python-roborock/python-roborock/pull/614),
  [`ee02a71`](https://github.com/Python-roborock/python-roborock/commit/ee02a71a8d99848256f2bb69533e9d1827f52585))

### Chores

- Fix test snapshots ([#614](https://github.com/Python-roborock/python-roborock/pull/614),
  [`ee02a71`](https://github.com/Python-roborock/python-roborock/commit/ee02a71a8d99848256f2bb69533e9d1827f52585))

- Remove unnecessary imports ([#614](https://github.com/Python-roborock/python-roborock/pull/614),
  [`ee02a71`](https://github.com/Python-roborock/python-roborock/commit/ee02a71a8d99848256f2bb69533e9d1827f52585))


## v3.9.1 (2025-12-03)

### Bug Fixes

- Fix DeviceFeatures so that it can be serialized and deserialized properly.
  ([#615](https://github.com/Python-roborock/python-roborock/pull/615),
  [`88b2055`](https://github.com/Python-roborock/python-roborock/commit/88b2055a7aea50d8b45bfb07c3a937b6d8d267d0))


## v3.9.0 (2025-12-03)

### Bug Fixes

- Set default arugments to store/load value functions
  ([#613](https://github.com/Python-roborock/python-roborock/pull/613),
  [`ce3d88d`](https://github.com/Python-roborock/python-roborock/commit/ce3d88dd52e78adccf7f705d4076cc963bbe9724))

### Chores

- Remove unncessary logging ([#613](https://github.com/Python-roborock/python-roborock/pull/613),
  [`ce3d88d`](https://github.com/Python-roborock/python-roborock/commit/ce3d88dd52e78adccf7f705d4076cc963bbe9724))

- Remove unnecessary snapshot files
  ([#613](https://github.com/Python-roborock/python-roborock/pull/613),
  [`ce3d88d`](https://github.com/Python-roborock/python-roborock/commit/ce3d88dd52e78adccf7f705d4076cc963bbe9724))

- Remove unused import ([#613](https://github.com/Python-roborock/python-roborock/pull/613),
  [`ce3d88d`](https://github.com/Python-roborock/python-roborock/commit/ce3d88dd52e78adccf7f705d4076cc963bbe9724))

### Features

- Make CacheData serializable ([#613](https://github.com/Python-roborock/python-roborock/pull/613),
  [`ce3d88d`](https://github.com/Python-roborock/python-roborock/commit/ce3d88dd52e78adccf7f705d4076cc963bbe9724))


## v3.8.5 (2025-11-29)

### Bug Fixes

- Remove python 3.11 incompatibility
  ([#609](https://github.com/Python-roborock/python-roborock/pull/609),
  [`f3487e8`](https://github.com/Python-roborock/python-roborock/commit/f3487e8ec478e000d1330745dff178125796bfb5))

### Chores

- Fix v1 channel typing and improve readability
  ([#609](https://github.com/Python-roborock/python-roborock/pull/609),
  [`f3487e8`](https://github.com/Python-roborock/python-roborock/commit/f3487e8ec478e000d1330745dff178125796bfb5))

- Improve doc string readability and grammar
  ([#609](https://github.com/Python-roborock/python-roborock/pull/609),
  [`f3487e8`](https://github.com/Python-roborock/python-roborock/commit/f3487e8ec478e000d1330745dff178125796bfb5))

- Refactor v1 rpc channels ([#609](https://github.com/Python-roborock/python-roborock/pull/609),
  [`f3487e8`](https://github.com/Python-roborock/python-roborock/commit/f3487e8ec478e000d1330745dff178125796bfb5))

- Remove unnecessary docstrings
  ([#609](https://github.com/Python-roborock/python-roborock/pull/609),
  [`f3487e8`](https://github.com/Python-roborock/python-roborock/commit/f3487e8ec478e000d1330745dff178125796bfb5))

- Remove unnecessary pydoc on private members
  ([#609](https://github.com/Python-roborock/python-roborock/pull/609),
  [`f3487e8`](https://github.com/Python-roborock/python-roborock/commit/f3487e8ec478e000d1330745dff178125796bfb5))

- Remove unnecessary pydoc to make the code more compact
  ([#609](https://github.com/Python-roborock/python-roborock/pull/609),
  [`f3487e8`](https://github.com/Python-roborock/python-roborock/commit/f3487e8ec478e000d1330745dff178125796bfb5))


## v3.8.4 (2025-11-29)

### Bug Fixes

- Encode map content bytes as base64
  ([#608](https://github.com/Python-roborock/python-roborock/pull/608),
  [`27c61f9`](https://github.com/Python-roborock/python-roborock/commit/27c61f9b7958edb5b4ca374e60898eb966163802))

- Fallback to the cached network information on failure
  ([#606](https://github.com/Python-roborock/python-roborock/pull/606),
  [`80d7d5a`](https://github.com/Python-roborock/python-roborock/commit/80d7d5af72629e83fbc7f2bf418ccecd793dbd58))

- Fallback to the cached network information when failing to lookup network info
  ([#606](https://github.com/Python-roborock/python-roborock/pull/606),
  [`80d7d5a`](https://github.com/Python-roborock/python-roborock/commit/80d7d5af72629e83fbc7f2bf418ccecd793dbd58))

- Improve partial update code ([#608](https://github.com/Python-roborock/python-roborock/pull/608),
  [`27c61f9`](https://github.com/Python-roborock/python-roborock/commit/27c61f9b7958edb5b4ca374e60898eb966163802))

### Chores

- Update roborock/devices/v1_channel.py
  ([#606](https://github.com/Python-roborock/python-roborock/pull/606),
  [`80d7d5a`](https://github.com/Python-roborock/python-roborock/commit/80d7d5af72629e83fbc7f2bf418ccecd793dbd58))


## v3.8.3 (2025-11-29)

### Bug Fixes

- Add a health manager for restarting unhealthy mqtt connections
  ([#605](https://github.com/Python-roborock/python-roborock/pull/605),
  [`879a641`](https://github.com/Python-roborock/python-roborock/commit/879a6412aafe8e7d0ba7a16e867ff3028873fd02))

- Add ability to restart the mqtt session
  ([#605](https://github.com/Python-roborock/python-roborock/pull/605),
  [`879a641`](https://github.com/Python-roborock/python-roborock/commit/879a6412aafe8e7d0ba7a16e867ff3028873fd02))

- Reset start_future each loop ([#605](https://github.com/Python-roborock/python-roborock/pull/605),
  [`879a641`](https://github.com/Python-roborock/python-roborock/commit/879a6412aafe8e7d0ba7a16e867ff3028873fd02))

### Chores

- Always use utc for now ([#605](https://github.com/Python-roborock/python-roborock/pull/605),
  [`879a641`](https://github.com/Python-roborock/python-roborock/commit/879a6412aafe8e7d0ba7a16e867ff3028873fd02))

- Cancel the connection and reconnect tasks
  ([#605](https://github.com/Python-roborock/python-roborock/pull/605),
  [`879a641`](https://github.com/Python-roborock/python-roborock/commit/879a6412aafe8e7d0ba7a16e867ff3028873fd02))

- Fix async tests ([#605](https://github.com/Python-roborock/python-roborock/pull/605),
  [`879a641`](https://github.com/Python-roborock/python-roborock/commit/879a6412aafe8e7d0ba7a16e867ff3028873fd02))


## v3.8.2 (2025-11-28)

### Bug Fixes

- Fix device feature discovery ([#603](https://github.com/Python-roborock/python-roborock/pull/603),
  [`d048001`](https://github.com/Python-roborock/python-roborock/commit/d0480015550edbe3e978902e141563e9c537fad1))

### Chores

- Revert requires_feature ([#603](https://github.com/Python-roborock/python-roborock/pull/603),
  [`d048001`](https://github.com/Python-roborock/python-roborock/commit/d0480015550edbe3e978902e141563e9c537fad1))


## v3.8.1 (2025-11-26)

### Bug Fixes

- Attempt to fix l01 ([#593](https://github.com/Python-roborock/python-roborock/pull/593),
  [`87e60d9`](https://github.com/Python-roborock/python-roborock/commit/87e60d9a9cb99ef9ddf99b1691baa2573db4221d))

- Decoding l01 ([#593](https://github.com/Python-roborock/python-roborock/pull/593),
  [`87e60d9`](https://github.com/Python-roborock/python-roborock/commit/87e60d9a9cb99ef9ddf99b1691baa2573db4221d))

- Ensure traits to always reflect the the status of commands
  ([#592](https://github.com/Python-roborock/python-roborock/pull/592),
  [`3d0ad74`](https://github.com/Python-roborock/python-roborock/commit/3d0ad74954948ebf0ea5c1a144aff3f9d111b1f7))

- Fix L01 encoding and decoding
  ([#593](https://github.com/Python-roborock/python-roborock/pull/593),
  [`87e60d9`](https://github.com/Python-roborock/python-roborock/commit/87e60d9a9cb99ef9ddf99b1691baa2573db4221d))

- Temp cache of protocol version until restart
  ([#593](https://github.com/Python-roborock/python-roborock/pull/593),
  [`87e60d9`](https://github.com/Python-roborock/python-roborock/commit/87e60d9a9cb99ef9ddf99b1691baa2573db4221d))

- Update bad asserts found by co-pilot
  ([#592](https://github.com/Python-roborock/python-roborock/pull/592),
  [`3d0ad74`](https://github.com/Python-roborock/python-roborock/commit/3d0ad74954948ebf0ea5c1a144aff3f9d111b1f7))

- Update the messages callback to not mutate the protocol once created.
  ([#593](https://github.com/Python-roborock/python-roborock/pull/593),
  [`87e60d9`](https://github.com/Python-roborock/python-roborock/commit/87e60d9a9cb99ef9ddf99b1691baa2573db4221d))

### Chores

- Add comments everywhere on implicit refreshes
  ([#592](https://github.com/Python-roborock/python-roborock/pull/592),
  [`3d0ad74`](https://github.com/Python-roborock/python-roborock/commit/3d0ad74954948ebf0ea5c1a144aff3f9d111b1f7))

- Fix lint errors ([#593](https://github.com/Python-roborock/python-roborock/pull/593),
  [`87e60d9`](https://github.com/Python-roborock/python-roborock/commit/87e60d9a9cb99ef9ddf99b1691baa2573db4221d))

- Fix typos ([#592](https://github.com/Python-roborock/python-roborock/pull/592),
  [`3d0ad74`](https://github.com/Python-roborock/python-roborock/commit/3d0ad74954948ebf0ea5c1a144aff3f9d111b1f7))

- Remove unnecessary whitespace
  ([#592](https://github.com/Python-roborock/python-roborock/pull/592),
  [`3d0ad74`](https://github.com/Python-roborock/python-roborock/commit/3d0ad74954948ebf0ea5c1a144aff3f9d111b1f7))

- Update roborock/devices/traits/v1/common.py
  ([#592](https://github.com/Python-roborock/python-roborock/pull/592),
  [`3d0ad74`](https://github.com/Python-roborock/python-roborock/commit/3d0ad74954948ebf0ea5c1a144aff3f9d111b1f7))

- Update working for the CommandTrait
  ([#592](https://github.com/Python-roborock/python-roborock/pull/592),
  [`3d0ad74`](https://github.com/Python-roborock/python-roborock/commit/3d0ad74954948ebf0ea5c1a144aff3f9d111b1f7))

- **deps**: Bump actions/checkout from 5 to 6
  ([#598](https://github.com/Python-roborock/python-roborock/pull/598),
  [`a9e91ae`](https://github.com/Python-roborock/python-roborock/commit/a9e91aedaed142f433d52c8b21b3fda3a1f62450))

- **deps**: Bump click from 8.3.0 to 8.3.1
  ([#594](https://github.com/Python-roborock/python-roborock/pull/594),
  [`4b5d6bb`](https://github.com/Python-roborock/python-roborock/commit/4b5d6bb0044deef158484b712f75ef3ab76f1cef))

- **deps**: Bump pre-commit from 4.4.0 to 4.5.0
  ([#602](https://github.com/Python-roborock/python-roborock/pull/602),
  [`50b70a4`](https://github.com/Python-roborock/python-roborock/commit/50b70a454dd80c1b41df855496c72818ecf30cea))

- **deps**: Bump pytest-asyncio from 1.2.0 to 1.3.0
  ([#596](https://github.com/Python-roborock/python-roborock/pull/596),
  [`ee85762`](https://github.com/Python-roborock/python-roborock/commit/ee85762ebe34663c25c3c05509a265f2d624b3ab))

- **deps**: Bump python-semantic-release/publish-action
  ([#599](https://github.com/Python-roborock/python-roborock/pull/599),
  [`bcfe314`](https://github.com/Python-roborock/python-roborock/commit/bcfe3141fde31b1930c54ac1ce8f0a3aef9adea7))

- **deps**: Bump python-semantic-release/python-semantic-release
  ([#600](https://github.com/Python-roborock/python-roborock/pull/600),
  [`f8061ff`](https://github.com/Python-roborock/python-roborock/commit/f8061ffcf416bd2618ac5b6f4b056650599bcbe8))

- **deps**: Bump ruff from 0.14.4 to 0.14.5
  ([#595](https://github.com/Python-roborock/python-roborock/pull/595),
  [`e561838`](https://github.com/Python-roborock/python-roborock/commit/e561838449be48abebf6ea94ff944222eea4d0ec))

- **deps**: Bump ruff from 0.14.5 to 0.14.6
  ([#601](https://github.com/Python-roborock/python-roborock/pull/601),
  [`c16c529`](https://github.com/Python-roborock/python-roborock/commit/c16c529881d84f370f99a7c5b31255a24a74da3a))


## v3.8.0 (2025-11-15)

### Bug Fixes

- Update roborock/devices/device.py
  ([#588](https://github.com/Python-roborock/python-roborock/pull/588),
  [`3994110`](https://github.com/Python-roborock/python-roborock/commit/39941103fe5247a9764d38db5ee0915dd39e043d))

### Chores

- Fix lint ([#589](https://github.com/Python-roborock/python-roborock/pull/589),
  [`fa69bf2`](https://github.com/Python-roborock/python-roborock/commit/fa69bf2d9d090bf8bc6cf89ead6ab122d5dbcd00))

- Fix lint errors ([#588](https://github.com/Python-roborock/python-roborock/pull/588),
  [`3994110`](https://github.com/Python-roborock/python-roborock/commit/39941103fe5247a9764d38db5ee0915dd39e043d))

- Update comments to clarify close call
  ([#588](https://github.com/Python-roborock/python-roborock/pull/588),
  [`3994110`](https://github.com/Python-roborock/python-roborock/commit/39941103fe5247a9764d38db5ee0915dd39e043d))

- Update documentation to point to the newer device APIs
  ([#589](https://github.com/Python-roborock/python-roborock/pull/589),
  [`fa69bf2`](https://github.com/Python-roborock/python-roborock/commit/fa69bf2d9d090bf8bc6cf89ead6ab122d5dbcd00))

- Update pydoc and formatting ([#588](https://github.com/Python-roborock/python-roborock/pull/588),
  [`3994110`](https://github.com/Python-roborock/python-roborock/commit/39941103fe5247a9764d38db5ee0915dd39e043d))

- Update README.md ([#589](https://github.com/Python-roborock/python-roborock/pull/589),
  [`fa69bf2`](https://github.com/Python-roborock/python-roborock/commit/fa69bf2d9d090bf8bc6cf89ead6ab122d5dbcd00))

- Update roborock/devices/device.py
  ([#588](https://github.com/Python-roborock/python-roborock/pull/588),
  [`3994110`](https://github.com/Python-roborock/python-roborock/commit/39941103fe5247a9764d38db5ee0915dd39e043d))

- Update roborock/devices/traits/b01/__init__.py
  ([#589](https://github.com/Python-roborock/python-roborock/pull/589),
  [`fa69bf2`](https://github.com/Python-roborock/python-roborock/commit/fa69bf2d9d090bf8bc6cf89ead6ab122d5dbcd00))

- Update roborock/devices/traits/v1/__init__.py
  ([#589](https://github.com/Python-roborock/python-roborock/pull/589),
  [`fa69bf2`](https://github.com/Python-roborock/python-roborock/commit/fa69bf2d9d090bf8bc6cf89ead6ab122d5dbcd00))

- Update typing ([#588](https://github.com/Python-roborock/python-roborock/pull/588),
  [`3994110`](https://github.com/Python-roborock/python-roborock/commit/39941103fe5247a9764d38db5ee0915dd39e043d))

### Features

- Add examples that show how to use the cache and implement a file cache
  ([#589](https://github.com/Python-roborock/python-roborock/pull/589),
  [`fa69bf2`](https://github.com/Python-roborock/python-roborock/commit/fa69bf2d9d090bf8bc6cf89ead6ab122d5dbcd00))

- Connect to devices asynchronously
  ([#588](https://github.com/Python-roborock/python-roborock/pull/588),
  [`3994110`](https://github.com/Python-roborock/python-roborock/commit/39941103fe5247a9764d38db5ee0915dd39e043d))


## v3.7.4 (2025-11-15)

### Bug Fixes

- Update trait `refresh` method to return `None`
  ([#586](https://github.com/Python-roborock/python-roborock/pull/586),
  [`86ec1a7`](https://github.com/Python-roborock/python-roborock/commit/86ec1a7377159ed9bdceb339804b61c73532f441))

### Chores

- Fix lint errors ([#586](https://github.com/Python-roborock/python-roborock/pull/586),
  [`86ec1a7`](https://github.com/Python-roborock/python-roborock/commit/86ec1a7377159ed9bdceb339804b61c73532f441))

- Remove unnecessary whitespace
  ([#586](https://github.com/Python-roborock/python-roborock/pull/586),
  [`86ec1a7`](https://github.com/Python-roborock/python-roborock/commit/86ec1a7377159ed9bdceb339804b61c73532f441))

- Revert accidental CleanSummary changes
  ([#586](https://github.com/Python-roborock/python-roborock/pull/586),
  [`86ec1a7`](https://github.com/Python-roborock/python-roborock/commit/86ec1a7377159ed9bdceb339804b61c73532f441))

- Revert unnecessary change to Clean Summary Trait
  ([#586](https://github.com/Python-roborock/python-roborock/pull/586),
  [`86ec1a7`](https://github.com/Python-roborock/python-roborock/commit/86ec1a7377159ed9bdceb339804b61c73532f441))


## v3.7.3 (2025-11-14)

### Bug Fixes

- Switches commands were incorrect
  ([#591](https://github.com/Python-roborock/python-roborock/pull/591),
  [`40aa6b6`](https://github.com/Python-roborock/python-roborock/commit/40aa6b67a6e43e273d6e4512ccdc8df11dd4dc8a))

### Chores

- Add device info for roborock.vacuum.s5e
  ([#587](https://github.com/Python-roborock/python-roborock/pull/587),
  [`20afa92`](https://github.com/Python-roborock/python-roborock/commit/20afa925e298f9fb36fc3e1ac79bf8cba90fcdf5))

- **deps**: Bump ruff from 0.14.1 to 0.14.4
  ([#585](https://github.com/Python-roborock/python-roborock/pull/585),
  [`324c816`](https://github.com/Python-roborock/python-roborock/commit/324c8165bacfdd7abbc1561c3f4f5768cd9c331c))


## v3.7.2 (2025-11-11)

### Bug Fixes

- Improve Home trait discovery process.
  ([#580](https://github.com/Python-roborock/python-roborock/pull/580),
  [`44680e3`](https://github.com/Python-roborock/python-roborock/commit/44680e367991b6eafef0267f6b4209a09929973a))

### Chores

- Refactor test by removing redundant assertion
  ([#580](https://github.com/Python-roborock/python-roborock/pull/580),
  [`44680e3`](https://github.com/Python-roborock/python-roborock/commit/44680e367991b6eafef0267f6b4209a09929973a))

- Update tests/devices/traits/v1/test_home.py
  ([#580](https://github.com/Python-roborock/python-roborock/pull/580),
  [`44680e3`](https://github.com/Python-roborock/python-roborock/commit/44680e367991b6eafef0267f6b4209a09929973a))

- **deps**: Bump aiohttp from 3.13.0 to 3.13.2
  ([#583](https://github.com/Python-roborock/python-roborock/pull/583),
  [`c7bacad`](https://github.com/Python-roborock/python-roborock/commit/c7bacad32ede1290fbaea261538e1b90476d61c6))

- **deps**: Bump pre-commit from 4.3.0 to 4.4.0
  ([#584](https://github.com/Python-roborock/python-roborock/pull/584),
  [`3adc76b`](https://github.com/Python-roborock/python-roborock/commit/3adc76bdd21c16fcb25d9d3dee9c5857eccea960))

- **deps**: Bump python-semantic-release/publish-action
  ([#582](https://github.com/Python-roborock/python-roborock/pull/582),
  [`c76bf06`](https://github.com/Python-roborock/python-roborock/commit/c76bf069191bf221a848c4dfa34104e8b93b81b8))


## v3.7.1 (2025-11-05)

### Bug Fixes

- Fix typing issues in new device traits
  ([#577](https://github.com/Python-roborock/python-roborock/pull/577),
  [`3266ae6`](https://github.com/Python-roborock/python-roborock/commit/3266ae6aa9d799c398542c95463d63a8cb77dd4e))


## v3.7.0 (2025-10-27)

### Chores

- Change imports for typing ([#574](https://github.com/Python-roborock/python-roborock/pull/574),
  [`05c8e94`](https://github.com/Python-roborock/python-roborock/commit/05c8e9458e44a6ca61977cc0d26c2776bb1fcae5))

- Update tests/devices/traits/v1/fixtures.py
  ([#574](https://github.com/Python-roborock/python-roborock/pull/574),
  [`05c8e94`](https://github.com/Python-roborock/python-roborock/commit/05c8e9458e44a6ca61977cc0d26c2776bb1fcae5))

### Features

- Add a trait for working with routines
  ([#574](https://github.com/Python-roborock/python-roborock/pull/574),
  [`05c8e94`](https://github.com/Python-roborock/python-roborock/commit/05c8e9458e44a6ca61977cc0d26c2776bb1fcae5))


## v3.6.0 (2025-10-27)

### Chores

- Add test coverage for failing to parse bytes
  ([#572](https://github.com/Python-roborock/python-roborock/pull/572),
  [`e524d31`](https://github.com/Python-roborock/python-roborock/commit/e524d31fa63cc6c97c10bf890dbde91e7e5d3840))

- Update tests/devices/traits/v1/test_home.py
  ([#572](https://github.com/Python-roborock/python-roborock/pull/572),
  [`e524d31`](https://github.com/Python-roborock/python-roborock/commit/e524d31fa63cc6c97c10bf890dbde91e7e5d3840))

### Features

- Add map content to the Home trait
  ([#572](https://github.com/Python-roborock/python-roborock/pull/572),
  [`e524d31`](https://github.com/Python-roborock/python-roborock/commit/e524d31fa63cc6c97c10bf890dbde91e7e5d3840))


## v3.5.0 (2025-10-27)

### Chores

- Disable body-max-line-length ([#573](https://github.com/Python-roborock/python-roborock/pull/573),
  [`6a5db1d`](https://github.com/Python-roborock/python-roborock/commit/6a5db1d9aac274bbfa46624250def64ada2b507b))

- Go back to old web API name ([#570](https://github.com/Python-roborock/python-roborock/pull/570),
  [`4e7e776`](https://github.com/Python-roborock/python-roborock/commit/4e7e776fed4cae17636659b9e3365ac26347e86b))

### Features

- Simplify device manager creation
  ([#570](https://github.com/Python-roborock/python-roborock/pull/570),
  [`4e7e776`](https://github.com/Python-roborock/python-roborock/commit/4e7e776fed4cae17636659b9e3365ac26347e86b))


## v3.4.0 (2025-10-26)

### Bug Fixes

- Only validate connection when sending commands
  ([#571](https://github.com/Python-roborock/python-roborock/pull/571),
  [`efa48e9`](https://github.com/Python-roborock/python-roborock/commit/efa48e96a1554b7a7358f9f22873b847d93d663d))

### Features

- Rename home_cache to home_map_info
  ([#569](https://github.com/Python-roborock/python-roborock/pull/569),
  [`9aff1cf`](https://github.com/Python-roborock/python-roborock/commit/9aff1cf01aa8e1a56d594cd2be20400cbf1eb324))


## v3.3.3 (2025-10-25)

### Bug Fixes

- FIx bug in clean record parsing
  ([#567](https://github.com/Python-roborock/python-roborock/pull/567),
  [`8196bcc`](https://github.com/Python-roborock/python-roborock/commit/8196bccdf5239ef540291bf55fa2bd270a4544ed))


## v3.3.2 (2025-10-25)

### Bug Fixes

- Ensure that result is not none
  ([#565](https://github.com/Python-roborock/python-roborock/pull/565),
  [`c0a84eb`](https://github.com/Python-roborock/python-roborock/commit/c0a84eb434ea1b8e15adea7adeba28b7fb1853f6))

- Set to empty dict ([#565](https://github.com/Python-roborock/python-roborock/pull/565),
  [`c0a84eb`](https://github.com/Python-roborock/python-roborock/commit/c0a84eb434ea1b8e15adea7adeba28b7fb1853f6))

### Chores

- Fix typing for InMemoryCache ([#566](https://github.com/Python-roborock/python-roborock/pull/566),
  [`904494d`](https://github.com/Python-roborock/python-roborock/commit/904494da3dcf899d9a4d5d4ab589d543dcea1fe2))

- Go back to the other way ([#565](https://github.com/Python-roborock/python-roborock/pull/565),
  [`c0a84eb`](https://github.com/Python-roborock/python-roborock/commit/c0a84eb434ea1b8e15adea7adeba28b7fb1853f6))

- Update roborock/protocols/v1_protocol.py
  ([#565](https://github.com/Python-roborock/python-roborock/pull/565),
  [`c0a84eb`](https://github.com/Python-roborock/python-roborock/commit/c0a84eb434ea1b8e15adea7adeba28b7fb1853f6))


## v3.3.1 (2025-10-25)

### Bug Fixes

- Truncate debug strings for MapContent
  ([#564](https://github.com/Python-roborock/python-roborock/pull/564),
  [`5a377de`](https://github.com/Python-roborock/python-roborock/commit/5a377ded245f6948f86775287eb7d70c12ec7740))

### Chores

- Apply github co-pilot recommendation
  ([#564](https://github.com/Python-roborock/python-roborock/pull/564),
  [`5a377de`](https://github.com/Python-roborock/python-roborock/commit/5a377ded245f6948f86775287eb7d70c12ec7740))


## v3.3.0 (2025-10-25)

### Bug Fixes

- Lower local timeout ([#559](https://github.com/Python-roborock/python-roborock/pull/559),
  [`8514461`](https://github.com/Python-roborock/python-roborock/commit/8514461a0d5e69b7c1fc1466ac5f19cb8bd5cbd5))

- Remove unneeded params setting
  ([#559](https://github.com/Python-roborock/python-roborock/pull/559),
  [`8514461`](https://github.com/Python-roborock/python-roborock/commit/8514461a0d5e69b7c1fc1466ac5f19cb8bd5cbd5))

### Chores

- Add some tests and adress comments
  ([#559](https://github.com/Python-roborock/python-roborock/pull/559),
  [`8514461`](https://github.com/Python-roborock/python-roborock/commit/8514461a0d5e69b7c1fc1466ac5f19cb8bd5cbd5))

- Fix comments ([#559](https://github.com/Python-roborock/python-roborock/pull/559),
  [`8514461`](https://github.com/Python-roborock/python-roborock/commit/8514461a0d5e69b7c1fc1466ac5f19cb8bd5cbd5))

- Handle failed hello ([#559](https://github.com/Python-roborock/python-roborock/pull/559),
  [`8514461`](https://github.com/Python-roborock/python-roborock/commit/8514461a0d5e69b7c1fc1466ac5f19cb8bd5cbd5))

- Remove unneeded code ([#559](https://github.com/Python-roborock/python-roborock/pull/559),
  [`8514461`](https://github.com/Python-roborock/python-roborock/commit/8514461a0d5e69b7c1fc1466ac5f19cb8bd5cbd5))

- Switch to more specific exception
  ([#559](https://github.com/Python-roborock/python-roborock/pull/559),
  [`8514461`](https://github.com/Python-roborock/python-roborock/commit/8514461a0d5e69b7c1fc1466ac5f19cb8bd5cbd5))

- Update roborock/devices/local_channel.py
  ([#559](https://github.com/Python-roborock/python-roborock/pull/559),
  [`8514461`](https://github.com/Python-roborock/python-roborock/commit/8514461a0d5e69b7c1fc1466ac5f19cb8bd5cbd5))

### Features

- Add l01 to the new device format
  ([#559](https://github.com/Python-roborock/python-roborock/pull/559),
  [`8514461`](https://github.com/Python-roborock/python-roborock/commit/8514461a0d5e69b7c1fc1466ac5f19cb8bd5cbd5))


## v3.2.0 (2025-10-25)

### Bug Fixes

- Update redacted values to remove sensitive values
  ([#560](https://github.com/Python-roborock/python-roborock/pull/560),
  [`0fc7200`](https://github.com/Python-roborock/python-roborock/commit/0fc720034f9da988fe0ba981128b7d66c4998e60))

- Update shapshots ([#560](https://github.com/Python-roborock/python-roborock/pull/560),
  [`0fc7200`](https://github.com/Python-roborock/python-roborock/commit/0fc720034f9da988fe0ba981128b7d66c4998e60))

### Chores

- Cleanup lint ([#560](https://github.com/Python-roborock/python-roborock/pull/560),
  [`0fc7200`](https://github.com/Python-roborock/python-roborock/commit/0fc720034f9da988fe0ba981128b7d66c4998e60))

- Only emit traits that have any values set
  ([#560](https://github.com/Python-roborock/python-roborock/pull/560),
  [`0fc7200`](https://github.com/Python-roborock/python-roborock/commit/0fc720034f9da988fe0ba981128b7d66c4998e60))

- Revert mqtt channel changes ([#560](https://github.com/Python-roborock/python-roborock/pull/560),
  [`0fc7200`](https://github.com/Python-roborock/python-roborock/commit/0fc720034f9da988fe0ba981128b7d66c4998e60))

### Features

- Add diagnostic information to the device
  ([#560](https://github.com/Python-roborock/python-roborock/pull/560),
  [`0fc7200`](https://github.com/Python-roborock/python-roborock/commit/0fc720034f9da988fe0ba981128b7d66c4998e60))


## v3.1.2 (2025-10-25)

### Bug Fixes

- Move semantic release build command
  ([`8ed178d`](https://github.com/Python-roborock/python-roborock/commit/8ed178d9f75245bde3ffcebbf8ef18e171ba563d))


## v3.1.1 (2025-10-25)

### Bug Fixes

- Explicitly pip install uv in release
  ([`4409ee9`](https://github.com/Python-roborock/python-roborock/commit/4409ee90694e9b3389342692f30fbf3706f2f00c))

### Chores

- Add pre commit step for commitlint
  ([#563](https://github.com/Python-roborock/python-roborock/pull/563),
  [`14c811f`](https://github.com/Python-roborock/python-roborock/commit/14c811f30f0bb1f574be59e759aecab5ca61cd65))


## v3.1.0 (2025-10-25)

### Bug Fixes

- Fix enum names to include `none` states
  ([#561](https://github.com/Python-roborock/python-roborock/pull/561),
  [`82f6dc2`](https://github.com/Python-roborock/python-roborock/commit/82f6dc29d55fd4f8565312af3cf60abf8abba56c))

### Chores

- Add a temp main branch for testing
  ([#562](https://github.com/Python-roborock/python-roborock/pull/562),
  [`7592255`](https://github.com/Python-roborock/python-roborock/commit/75922550bad8f5fc4ece1f2f4a6be74ebb3849c2))

- Build system to make sure it doesn't break
  ([#562](https://github.com/Python-roborock/python-roborock/pull/562),
  [`7592255`](https://github.com/Python-roborock/python-roborock/commit/75922550bad8f5fc4ece1f2f4a6be74ebb3849c2))

- Fix branches ([#562](https://github.com/Python-roborock/python-roborock/pull/562),
  [`7592255`](https://github.com/Python-roborock/python-roborock/commit/75922550bad8f5fc4ece1f2f4a6be74ebb3849c2))

- Fix changelog ([#552](https://github.com/Python-roborock/python-roborock/pull/552),
  [`e2073ed`](https://github.com/Python-roborock/python-roborock/commit/e2073edc655c1a91caae5f05e1377aebfad2938e))

- Fix test release ([#562](https://github.com/Python-roborock/python-roborock/pull/562),
  [`7592255`](https://github.com/Python-roborock/python-roborock/commit/75922550bad8f5fc4ece1f2f4a6be74ebb3849c2))

- Get uv release to work properly
  ([#562](https://github.com/Python-roborock/python-roborock/pull/562),
  [`7592255`](https://github.com/Python-roborock/python-roborock/commit/75922550bad8f5fc4ece1f2f4a6be74ebb3849c2))

- Switch dependabot from pip to uv
  ([#554](https://github.com/Python-roborock/python-roborock/pull/554),
  [`9377e9a`](https://github.com/Python-roborock/python-roborock/commit/9377e9ac305f45339b022b5ef8f0c16b58732300))

- Try running a test release on every PR
  ([#562](https://github.com/Python-roborock/python-roborock/pull/562),
  [`7592255`](https://github.com/Python-roborock/python-roborock/commit/75922550bad8f5fc4ece1f2f4a6be74ebb3849c2))

- Update snapshot ([#555](https://github.com/Python-roborock/python-roborock/pull/555),
  [`b45ad3c`](https://github.com/Python-roborock/python-roborock/commit/b45ad3c487b21639a1f2ba148fe69836b11024c4))

- Update spelling from co-pilot suggestion
  ([#555](https://github.com/Python-roborock/python-roborock/pull/555),
  [`b45ad3c`](https://github.com/Python-roborock/python-roborock/commit/b45ad3c487b21639a1f2ba148fe69836b11024c4))

- Update test assertion for network info
  ([#558](https://github.com/Python-roborock/python-roborock/pull/558),
  [`b34abde`](https://github.com/Python-roborock/python-roborock/commit/b34abde2e3401c463e7fb821bae1cf20a325ec6d))

- **deps**: Bump ruff from 0.14.0 to 0.14.1
  ([#553](https://github.com/Python-roborock/python-roborock/pull/553),
  [`df438f7`](https://github.com/Python-roborock/python-roborock/commit/df438f7a293fb0c1f1b3cfaf3691eafaa8a3fd8b))

### Features

- Add a trait for reading NetworkInfo from the device
  ([#558](https://github.com/Python-roborock/python-roborock/pull/558),
  [`b34abde`](https://github.com/Python-roborock/python-roborock/commit/b34abde2e3401c463e7fb821bae1cf20a325ec6d))

- Combine the clean record trait with the clean summary
  ([#555](https://github.com/Python-roborock/python-roborock/pull/555),
  [`b45ad3c`](https://github.com/Python-roborock/python-roborock/commit/b45ad3c487b21639a1f2ba148fe69836b11024c4))


## v3.0.0 (2025-10-20)

### Features

- Add data subpackage ([#551](https://github.com/Python-roborock/python-roborock/pull/551),
  [`c4d3b86`](https://github.com/Python-roborock/python-roborock/commit/c4d3b86e9862847c0dd47add13e70542141ab214))


## v2.61.0 (2025-10-19)

### Bug Fixes

- Remove DockSummary and make dust collection mode optional based on dock type
  ([#550](https://github.com/Python-roborock/python-roborock/pull/550),
  [`03d0f37`](https://github.com/Python-roborock/python-roborock/commit/03d0f37cfca41ed5943e81b6ac30e061d4f4bd3f))

### Chores

- Fix semantic release using poetry
  ([#549](https://github.com/Python-roborock/python-roborock/pull/549),
  [`4bf5396`](https://github.com/Python-roborock/python-roborock/commit/4bf5396ac270e864ed433d96baf1c6c5d613106b))

### Features

- Add clean record and dock related traits
  ([#550](https://github.com/Python-roborock/python-roborock/pull/550),
  [`03d0f37`](https://github.com/Python-roborock/python-roborock/commit/03d0f37cfca41ed5943e81b6ac30e061d4f4bd3f))

- Add dock summary and clean record traits
  ([#550](https://github.com/Python-roborock/python-roborock/pull/550),
  [`03d0f37`](https://github.com/Python-roborock/python-roborock/commit/03d0f37cfca41ed5943e81b6ac30e061d4f4bd3f))


## v2.60.1 (2025-10-19)

### Bug Fixes

- Add a common base type for all switches
  ([#548](https://github.com/Python-roborock/python-roborock/pull/548),
  [`767e118`](https://github.com/Python-roborock/python-roborock/commit/767e118ed193cd16cecb61989614b50dab432aab))

### Chores

- Fix lint ([#544](https://github.com/Python-roborock/python-roborock/pull/544),
  [`fe463c3`](https://github.com/Python-roborock/python-roborock/commit/fe463c36d6862864d03b8040475d57e917c310ce))

- Update pydoc for V1 subscribe
  ([#544](https://github.com/Python-roborock/python-roborock/pull/544),
  [`fe463c3`](https://github.com/Python-roborock/python-roborock/commit/fe463c36d6862864d03b8040475d57e917c310ce))


## v2.60.0 (2025-10-18)

### Chores

- Match pyproject version
  ([`80f9149`](https://github.com/Python-roborock/python-roborock/commit/80f91498359e81c97d4e0666a9d85d52ee6f315a))

### Features

- Add a device property to determine local connection status
  ([#547](https://github.com/Python-roborock/python-roborock/pull/547),
  [`962ffe2`](https://github.com/Python-roborock/python-roborock/commit/962ffe2b94da26a6879f1006cb585dcaac36c798))


## v2.59.0 (2025-10-18)

### Chores

- Match version and do chore so it doesn't bump
  ([#546](https://github.com/Python-roborock/python-roborock/pull/546),
  [`140de50`](https://github.com/Python-roborock/python-roborock/commit/140de50bda73901ee43b864603cd42802de1570d))

- Match version and do chore so it doesn't bump hopefully
  ([#546](https://github.com/Python-roborock/python-roborock/pull/546),
  [`140de50`](https://github.com/Python-roborock/python-roborock/commit/140de50bda73901ee43b864603cd42802de1570d))

- Switch to the non-depreciated action
  ([#546](https://github.com/Python-roborock/python-roborock/pull/546),
  [`140de50`](https://github.com/Python-roborock/python-roborock/commit/140de50bda73901ee43b864603cd42802de1570d))

### Features

- Update command trait to allow string commands
  ([#543](https://github.com/Python-roborock/python-roborock/pull/543),
  [`1fdddaf`](https://github.com/Python-roborock/python-roborock/commit/1fdddafc8b0ad490beff3f08c5118e826ab8169f))


## v2.58.1 (2025-10-18)

### Bug Fixes

- Re-align version for semantic release
  ([#545](https://github.com/Python-roborock/python-roborock/pull/545),
  [`b724a5b`](https://github.com/Python-roborock/python-roborock/commit/b724a5bec52ce7fe723710f28f9f63c3b9fa6673))

### Chores

- Re-align version ([#545](https://github.com/Python-roborock/python-roborock/pull/545),
  [`b724a5b`](https://github.com/Python-roborock/python-roborock/commit/b724a5bec52ce7fe723710f28f9f63c3b9fa6673))

- Use github_token for release ([#545](https://github.com/Python-roborock/python-roborock/pull/545),
  [`b724a5b`](https://github.com/Python-roborock/python-roborock/commit/b724a5bec52ce7fe723710f28f9f63c3b9fa6673))


## v2.58.0 (2025-10-18)

### Bug Fixes

- Add everything else back ([#542](https://github.com/Python-roborock/python-roborock/pull/542),
  [`84c4c48`](https://github.com/Python-roborock/python-roborock/commit/84c4c48fe1c6268db8ceb6dbe8f1ed3318ed78aa))

- Correctly run pdocs on github action
  ([#542](https://github.com/Python-roborock/python-roborock/pull/542),
  [`84c4c48`](https://github.com/Python-roborock/python-roborock/commit/84c4c48fe1c6268db8ceb6dbe8f1ed3318ed78aa))

### Features

- Create a home data API client from an existing RoborockApiClient
  ([#541](https://github.com/Python-roborock/python-roborock/pull/541),
  [`e7f8e43`](https://github.com/Python-roborock/python-roborock/commit/e7f8e432cb063765f89223332b5994b0ddb639bc))


## v2.57.1 (2025-10-18)

### Bug Fixes

- Bug and add test ([#537](https://github.com/Python-roborock/python-roborock/pull/537),
  [`6a3d28c`](https://github.com/Python-roborock/python-roborock/commit/6a3d28c24f7444fc5e3cc73392509aca0d5ddd6e))

- Fallback to old version of login
  ([#537](https://github.com/Python-roborock/python-roborock/pull/537),
  [`6a3d28c`](https://github.com/Python-roborock/python-roborock/commit/6a3d28c24f7444fc5e3cc73392509aca0d5ddd6e))

### Chores

- **deps-dev**: Bump ruff from 0.13.2 to 0.14.0
  ([#530](https://github.com/Python-roborock/python-roborock/pull/530),
  [`538504d`](https://github.com/Python-roborock/python-roborock/commit/538504dbe66e5edb82a2bb7bfb78272752e0802f))


## v2.57.0 (2025-10-18)

### Chores

- Fix lint ([#540](https://github.com/Python-roborock/python-roborock/pull/540),
  [`24a0660`](https://github.com/Python-roborock/python-roborock/commit/24a06600633b16a0228876184125e3c5ffe16d02))

- Fix lint errors ([#539](https://github.com/Python-roborock/python-roborock/pull/539),
  [`fbf1434`](https://github.com/Python-roborock/python-roborock/commit/fbf1434be05103401b2f53c77737a5bfcc719102))

- Fix syntax and lint errors ([#539](https://github.com/Python-roborock/python-roborock/pull/539),
  [`fbf1434`](https://github.com/Python-roborock/python-roborock/commit/fbf1434be05103401b2f53c77737a5bfcc719102))

- Fix tests ([#539](https://github.com/Python-roborock/python-roborock/pull/539),
  [`fbf1434`](https://github.com/Python-roborock/python-roborock/commit/fbf1434be05103401b2f53c77737a5bfcc719102))

### Features

- Add a trait for sending commands
  ([#539](https://github.com/Python-roborock/python-roborock/pull/539),
  [`fbf1434`](https://github.com/Python-roborock/python-roborock/commit/fbf1434be05103401b2f53c77737a5bfcc719102))

- Expose device and product information on the new Device API
  ([#540](https://github.com/Python-roborock/python-roborock/pull/540),
  [`24a0660`](https://github.com/Python-roborock/python-roborock/commit/24a06600633b16a0228876184125e3c5ffe16d02))

- Update cli to use new command interface
  ([#539](https://github.com/Python-roborock/python-roborock/pull/539),
  [`fbf1434`](https://github.com/Python-roborock/python-roborock/commit/fbf1434be05103401b2f53c77737a5bfcc719102))


## v2.56.0 (2025-10-17)

### Bug Fixes

- Revert changes to dnd ([#538](https://github.com/Python-roborock/python-roborock/pull/538),
  [`aaf3636`](https://github.com/Python-roborock/python-roborock/commit/aaf3636553d68c31e89a763fb6da77d83842b6b8))

### Chores

- Add comment about firmware updates
  ([#538](https://github.com/Python-roborock/python-roborock/pull/538),
  [`aaf3636`](https://github.com/Python-roborock/python-roborock/commit/aaf3636553d68c31e89a763fb6da77d83842b6b8))

- Add python 3.14 for tests ([#524](https://github.com/Python-roborock/python-roborock/pull/524),
  [`a6f889d`](https://github.com/Python-roborock/python-roborock/commit/a6f889db0229d5821b04e70514ad5e7f8d5a25df))

- Explicitly install pdoc ([#531](https://github.com/Python-roborock/python-roborock/pull/531),
  [`5e4c913`](https://github.com/Python-roborock/python-roborock/commit/5e4c9138838eace5c010aa736c61565930520172))

- Fix lint errors ([#538](https://github.com/Python-roborock/python-roborock/pull/538),
  [`aaf3636`](https://github.com/Python-roborock/python-roborock/commit/aaf3636553d68c31e89a763fb6da77d83842b6b8))

- Fix typing on refresh ([#538](https://github.com/Python-roborock/python-roborock/pull/538),
  [`aaf3636`](https://github.com/Python-roborock/python-roborock/commit/aaf3636553d68c31e89a763fb6da77d83842b6b8))

- Just install pdoc ([#535](https://github.com/Python-roborock/python-roborock/pull/535),
  [`ef974cd`](https://github.com/Python-roborock/python-roborock/commit/ef974cd8fe5039aab55adea6d84375236c6a7072))

- Make roborock future test async
  ([#524](https://github.com/Python-roborock/python-roborock/pull/524),
  [`a6f889d`](https://github.com/Python-roborock/python-roborock/commit/a6f889db0229d5821b04e70514ad5e7f8d5a25df))

- Remove extra checkout ([#531](https://github.com/Python-roborock/python-roborock/pull/531),
  [`5e4c913`](https://github.com/Python-roborock/python-roborock/commit/5e4c9138838eace5c010aa736c61565930520172))

- Remove use of decorator and replace with class attribute
  ([#538](https://github.com/Python-roborock/python-roborock/pull/538),
  [`aaf3636`](https://github.com/Python-roborock/python-roborock/commit/aaf3636553d68c31e89a763fb6da77d83842b6b8))

- Switch pages to use uv ([#531](https://github.com/Python-roborock/python-roborock/pull/531),
  [`5e4c913`](https://github.com/Python-roborock/python-roborock/commit/5e4c9138838eace5c010aa736c61565930520172))

### Features

- Add various optional features with support for checking device features
  ([#538](https://github.com/Python-roborock/python-roborock/pull/538),
  [`aaf3636`](https://github.com/Python-roborock/python-roborock/commit/aaf3636553d68c31e89a763fb6da77d83842b6b8))


## v2.55.0 (2025-10-16)

### Bug Fixes

- Don't perform discovery when the device is cleaning
  ([#526](https://github.com/Python-roborock/python-roborock/pull/526),
  [`8ae82d1`](https://github.com/Python-roborock/python-roborock/commit/8ae82d1437ab60a09b828b399c69d56ced759b03))

- Require both country code and country
  ([#533](https://github.com/Python-roborock/python-roborock/pull/533),
  [`f827cbc`](https://github.com/Python-roborock/python-roborock/commit/f827cbccbb5b2204d614a95bf9ae82687c611325))

### Chores

- Add common routine for updating the cache
  ([#526](https://github.com/Python-roborock/python-roborock/pull/526),
  [`8ae82d1`](https://github.com/Python-roborock/python-roborock/commit/8ae82d1437ab60a09b828b399c69d56ced759b03))

- Fix lint error found by ruff on type comparison
  ([#528](https://github.com/Python-roborock/python-roborock/pull/528),
  [`5a4a03b`](https://github.com/Python-roborock/python-roborock/commit/5a4a03b05db97d7ce02f16b17de61f88daa1ee3d))

- Fix lint errors ([#528](https://github.com/Python-roborock/python-roborock/pull/528),
  [`5a4a03b`](https://github.com/Python-roborock/python-roborock/commit/5a4a03b05db97d7ce02f16b17de61f88daa1ee3d))

- Hook up the trait to the device and CLI
  ([#526](https://github.com/Python-roborock/python-roborock/pull/526),
  [`8ae82d1`](https://github.com/Python-roborock/python-roborock/commit/8ae82d1437ab60a09b828b399c69d56ced759b03))

- Migrate to uv ([#525](https://github.com/Python-roborock/python-roborock/pull/525),
  [`ec78beb`](https://github.com/Python-roborock/python-roborock/commit/ec78beb57a088d75ac9400c15cc15994f9978852))

- Replace async-timeout with asyncio.timeout
  ([#527](https://github.com/Python-roborock/python-roborock/pull/527),
  [`f376027`](https://github.com/Python-roborock/python-roborock/commit/f376027f5933e163441cf1815b820056731a3632))

- Upgrade ruff and apply ruff-format to all files
  ([#528](https://github.com/Python-roborock/python-roborock/pull/528),
  [`5a4a03b`](https://github.com/Python-roborock/python-roborock/commit/5a4a03b05db97d7ce02f16b17de61f88daa1ee3d))

### Features

- Add a Home trait that for caching information about maps and rooms
  ([#526](https://github.com/Python-roborock/python-roborock/pull/526),
  [`8ae82d1`](https://github.com/Python-roborock/python-roborock/commit/8ae82d1437ab60a09b828b399c69d56ced759b03))

- Add a trait for device features
  ([#534](https://github.com/Python-roborock/python-roborock/pull/534),
  [`8539fe4`](https://github.com/Python-roborock/python-roborock/commit/8539fe4b0ab72c388a55300a4724ca42bde83e38))


## v2.54.0 (2025-10-10)

### Features

- Add some extra status attributes
  ([#514](https://github.com/Python-roborock/python-roborock/pull/514),
  [`660e929`](https://github.com/Python-roborock/python-roborock/commit/660e9290659b27fb32a9e6dd1b82f6c608b1949e))

- Add support for detecting issues with the dock holders
  ([#514](https://github.com/Python-roborock/python-roborock/pull/514),
  [`660e929`](https://github.com/Python-roborock/python-roborock/commit/660e9290659b27fb32a9e6dd1b82f6c608b1949e))

- Get the latest clean info ([#522](https://github.com/Python-roborock/python-roborock/pull/522),
  [`3ac8f2d`](https://github.com/Python-roborock/python-roborock/commit/3ac8f2dd5490788dbe7f5ee74a1449eff42f802b))


## v2.53.1 (2025-10-06)

### Bug Fixes

- Cli on windows ([#520](https://github.com/Python-roborock/python-roborock/pull/520),
  [`4127db8`](https://github.com/Python-roborock/python-roborock/commit/4127db857e38db57ee5c84a27e7a6b64fdf40cbf))


## v2.53.0 (2025-10-05)

### Chores

- Fix formatting ([#517](https://github.com/Python-roborock/python-roborock/pull/517),
  [`e49b3ea`](https://github.com/Python-roborock/python-roborock/commit/e49b3ea1c2cc29a6c41562c3e937659ed9c0816a))

- Fix lint and typing errors ([#517](https://github.com/Python-roborock/python-roborock/pull/517),
  [`e49b3ea`](https://github.com/Python-roborock/python-roborock/commit/e49b3ea1c2cc29a6c41562c3e937659ed9c0816a))

- Fix lint error ([#517](https://github.com/Python-roborock/python-roborock/pull/517),
  [`e49b3ea`](https://github.com/Python-roborock/python-roborock/commit/e49b3ea1c2cc29a6c41562c3e937659ed9c0816a))

- Fix test wording ([#517](https://github.com/Python-roborock/python-roborock/pull/517),
  [`e49b3ea`](https://github.com/Python-roborock/python-roborock/commit/e49b3ea1c2cc29a6c41562c3e937659ed9c0816a))

- Refactor to reuse the same payload functions
  ([#517](https://github.com/Python-roborock/python-roborock/pull/517),
  [`e49b3ea`](https://github.com/Python-roborock/python-roborock/commit/e49b3ea1c2cc29a6c41562c3e937659ed9c0816a))

- Remove duplicate code ([#517](https://github.com/Python-roborock/python-roborock/pull/517),
  [`e49b3ea`](https://github.com/Python-roborock/python-roborock/commit/e49b3ea1c2cc29a6c41562c3e937659ed9c0816a))

### Features

- Add a v1 device trait for map contents
  ([#517](https://github.com/Python-roborock/python-roborock/pull/517),
  [`e49b3ea`](https://github.com/Python-roborock/python-roborock/commit/e49b3ea1c2cc29a6c41562c3e937659ed9c0816a))


## v2.52.0 (2025-10-05)

### Bug Fixes

- Fix room mapping parsing bug and add addtiional format samples
  ([#516](https://github.com/Python-roborock/python-roborock/pull/516),
  [`a68fbf1`](https://github.com/Python-roborock/python-roborock/commit/a68fbf197a0abd9aaa0418eec21949e65b53b88c))

- Update test ([#516](https://github.com/Python-roborock/python-roborock/pull/516),
  [`a68fbf1`](https://github.com/Python-roborock/python-roborock/commit/a68fbf197a0abd9aaa0418eec21949e65b53b88c))

### Chores

- Abort bad merges ([#516](https://github.com/Python-roborock/python-roborock/pull/516),
  [`a68fbf1`](https://github.com/Python-roborock/python-roborock/commit/a68fbf197a0abd9aaa0418eec21949e65b53b88c))

- Add additional example room mapping
  ([#516](https://github.com/Python-roborock/python-roborock/pull/516),
  [`a68fbf1`](https://github.com/Python-roborock/python-roborock/commit/a68fbf197a0abd9aaa0418eec21949e65b53b88c))

- Adjust test case ([#519](https://github.com/Python-roborock/python-roborock/pull/519),
  [`df6c674`](https://github.com/Python-roborock/python-roborock/commit/df6c6740431d75f06868979aed5e07bfa8887ed6))

- Fix lint errors ([#516](https://github.com/Python-roborock/python-roborock/pull/516),
  [`a68fbf1`](https://github.com/Python-roborock/python-roborock/commit/a68fbf197a0abd9aaa0418eec21949e65b53b88c))

- Fix test warning ([#519](https://github.com/Python-roborock/python-roborock/pull/519),
  [`df6c674`](https://github.com/Python-roborock/python-roborock/commit/df6c6740431d75f06868979aed5e07bfa8887ed6))

- Fix typing ([#516](https://github.com/Python-roborock/python-roborock/pull/516),
  [`a68fbf1`](https://github.com/Python-roborock/python-roborock/commit/a68fbf197a0abd9aaa0418eec21949e65b53b88c))

- Switch the rooms trait back to the local API
  ([#516](https://github.com/Python-roborock/python-roborock/pull/516),
  [`a68fbf1`](https://github.com/Python-roborock/python-roborock/commit/a68fbf197a0abd9aaa0418eec21949e65b53b88c))

### Features

- Add v1 rooms support to the device traits API
  ([#516](https://github.com/Python-roborock/python-roborock/pull/516),
  [`a68fbf1`](https://github.com/Python-roborock/python-roborock/commit/a68fbf197a0abd9aaa0418eec21949e65b53b88c))


## v2.51.0 (2025-10-05)

### Chores

- Add a class comment about availability
  ([#502](https://github.com/Python-roborock/python-roborock/pull/502),
  [`6bc3458`](https://github.com/Python-roborock/python-roborock/commit/6bc3458f49fc1072798ce8bfbcdea0d512e19bfd))

- Remove whitespace ([#502](https://github.com/Python-roborock/python-roborock/pull/502),
  [`6bc3458`](https://github.com/Python-roborock/python-roborock/commit/6bc3458f49fc1072798ce8bfbcdea0d512e19bfd))

### Features

- Add support for getting and reseting consumables
  ([#502](https://github.com/Python-roborock/python-roborock/pull/502),
  [`6bc3458`](https://github.com/Python-roborock/python-roborock/commit/6bc3458f49fc1072798ce8bfbcdea0d512e19bfd))


## v2.50.4 (2025-10-05)

### Bug Fixes

- Return in finally ([#518](https://github.com/Python-roborock/python-roborock/pull/518),
  [`9d400d5`](https://github.com/Python-roborock/python-roborock/commit/9d400d5a20a09395f93c0370718c4589d8155814))

### Chores

- **deps**: Bump actions/upload-pages-artifact from 3 to 4
  ([#505](https://github.com/Python-roborock/python-roborock/pull/505),
  [`e505791`](https://github.com/Python-roborock/python-roborock/commit/e5057919c9d0d90c85f29df35a628a209508121c))

- **deps**: Bump click from 8.2.1 to 8.3.0
  ([#495](https://github.com/Python-roborock/python-roborock/pull/495),
  [`9e12170`](https://github.com/Python-roborock/python-roborock/commit/9e121704267dea8c8bbac0e799dcfa8462bc7de7))

- **deps-dev**: Bump mypy from 1.18.1 to 1.18.2
  ([#496](https://github.com/Python-roborock/python-roborock/pull/496),
  [`31cbf41`](https://github.com/Python-roborock/python-roborock/commit/31cbf41caf1485dcebe5c6590d634e36392c6b3b))

- **deps-dev**: Bump ruff from 0.13.0 to 0.13.2
  ([#509](https://github.com/Python-roborock/python-roborock/pull/509),
  [`3ba07ad`](https://github.com/Python-roborock/python-roborock/commit/3ba07ad572aa28735828c78dd339308e3cb0340d))


## v2.50.3 (2025-10-03)

### Bug Fixes

- Update containers that __post_init__ to use properties
  ([#503](https://github.com/Python-roborock/python-roborock/pull/503),
  [`f87f55c`](https://github.com/Python-roborock/python-roborock/commit/f87f55ce2d62f90dd945a283def927b9fca70dab))

### Chores

- Fix lint errors ([#503](https://github.com/Python-roborock/python-roborock/pull/503),
  [`f87f55c`](https://github.com/Python-roborock/python-roborock/commit/f87f55ce2d62f90dd945a283def927b9fca70dab))

- Fix typo ([#503](https://github.com/Python-roborock/python-roborock/pull/503),
  [`f87f55c`](https://github.com/Python-roborock/python-roborock/commit/f87f55ce2d62f90dd945a283def927b9fca70dab))

- Include atributes in repr computation
  ([#503](https://github.com/Python-roborock/python-roborock/pull/503),
  [`f87f55c`](https://github.com/Python-roborock/python-roborock/commit/f87f55ce2d62f90dd945a283def927b9fca70dab))

- Update to get all properties at runtime
  ([#503](https://github.com/Python-roborock/python-roborock/pull/503),
  [`f87f55c`](https://github.com/Python-roborock/python-roborock/commit/f87f55ce2d62f90dd945a283def927b9fca70dab))


## v2.50.2 (2025-10-03)

### Bug Fixes

- Cycle through iot urls ([#490](https://github.com/Python-roborock/python-roborock/pull/490),
  [`2cee9dd`](https://github.com/Python-roborock/python-roborock/commit/2cee9ddcfb2c608967499405992c6e42f6124855))

### Chores

- Add tests ([#490](https://github.com/Python-roborock/python-roborock/pull/490),
  [`2cee9dd`](https://github.com/Python-roborock/python-roborock/commit/2cee9ddcfb2c608967499405992c6e42f6124855))

- Convert to store all iot login info together
  ([#490](https://github.com/Python-roborock/python-roborock/pull/490),
  [`2cee9dd`](https://github.com/Python-roborock/python-roborock/commit/2cee9ddcfb2c608967499405992c6e42f6124855))

- Remove gemini ([#512](https://github.com/Python-roborock/python-roborock/pull/512),
  [`632f0f4`](https://github.com/Python-roborock/python-roborock/commit/632f0f4031fe38c621a50e4bf6a7d2097f560aa9))


## v2.50.1 (2025-10-03)

### Bug Fixes

- Use correct replace times ([#513](https://github.com/Python-roborock/python-roborock/pull/513),
  [`a6ac92c`](https://github.com/Python-roborock/python-roborock/commit/a6ac92c5443833fe19a1d184495171904e04cbe2))


## v2.50.0 (2025-10-03)

### Bug Fixes

- Add a decorator to mark traits as mqtt only
  ([#499](https://github.com/Python-roborock/python-roborock/pull/499),
  [`87d9aa6`](https://github.com/Python-roborock/python-roborock/commit/87d9aa61676e11fd0ca56f5fc6c998fbff48645b))

### Chores

- Add additional test coverage ([#499](https://github.com/Python-roborock/python-roborock/pull/499),
  [`87d9aa6`](https://github.com/Python-roborock/python-roborock/commit/87d9aa61676e11fd0ca56f5fc6c998fbff48645b))

- Add comment describing the decorator check
  ([#499](https://github.com/Python-roborock/python-roborock/pull/499),
  [`87d9aa6`](https://github.com/Python-roborock/python-roborock/commit/87d9aa61676e11fd0ca56f5fc6c998fbff48645b))

- Fix lint errors ([#499](https://github.com/Python-roborock/python-roborock/pull/499),
  [`87d9aa6`](https://github.com/Python-roborock/python-roborock/commit/87d9aa61676e11fd0ca56f5fc6c998fbff48645b))

### Features

- Add v1 api support for the list of maps
  ([#499](https://github.com/Python-roborock/python-roborock/pull/499),
  [`87d9aa6`](https://github.com/Python-roborock/python-roborock/commit/87d9aa61676e11fd0ca56f5fc6c998fbff48645b))


## v2.49.1 (2025-09-29)

### Bug Fixes

- Broken current map logic ([#497](https://github.com/Python-roborock/python-roborock/pull/497),
  [`d7d0a3b`](https://github.com/Python-roborock/python-roborock/commit/d7d0a3b5f4066aab54be5736e01eb2b437c920de))

- The map id ([#497](https://github.com/Python-roborock/python-roborock/pull/497),
  [`d7d0a3b`](https://github.com/Python-roborock/python-roborock/commit/d7d0a3b5f4066aab54be5736e01eb2b437c920de))

### Chores

- Add no_map constant ([#497](https://github.com/Python-roborock/python-roborock/pull/497),
  [`d7d0a3b`](https://github.com/Python-roborock/python-roborock/commit/d7d0a3b5f4066aab54be5736e01eb2b437c920de))

- Add test ([#497](https://github.com/Python-roborock/python-roborock/pull/497),
  [`d7d0a3b`](https://github.com/Python-roborock/python-roborock/commit/d7d0a3b5f4066aab54be5736e01eb2b437c920de))

- Try `poetry run pdoc` to fix CI
  ([#504](https://github.com/Python-roborock/python-roborock/pull/504),
  [`da5d80f`](https://github.com/Python-roborock/python-roborock/commit/da5d80fb5c9e425317c3ade3065b2158af0a830f))


## v2.49.0 (2025-09-29)

### Bug Fixes

- Remove functon ([#448](https://github.com/Python-roborock/python-roborock/pull/448),
  [`27fb9fc`](https://github.com/Python-roborock/python-roborock/commit/27fb9fc00c9c16235a983db0df4cc0d2cfb5f7b3))

- Tchange name of cleanmodesold
  ([#448](https://github.com/Python-roborock/python-roborock/pull/448),
  [`27fb9fc`](https://github.com/Python-roborock/python-roborock/commit/27fb9fc00c9c16235a983db0df4cc0d2cfb5f7b3))

### Chores

- Cap product feature map ([#448](https://github.com/Python-roborock/python-roborock/pull/448),
  [`27fb9fc`](https://github.com/Python-roborock/python-roborock/commit/27fb9fc00c9c16235a983db0df4cc0d2cfb5f7b3))

- Fix lint ([#500](https://github.com/Python-roborock/python-roborock/pull/500),
  [`d5bb862`](https://github.com/Python-roborock/python-roborock/commit/d5bb8625ba6eb46a13b79df78a02f7e5e25cfd9f))

- Remove more complicated changes
  ([#448](https://github.com/Python-roborock/python-roborock/pull/448),
  [`27fb9fc`](https://github.com/Python-roborock/python-roborock/commit/27fb9fc00c9c16235a983db0df4cc0d2cfb5f7b3))

### Features

- Add dynamic clean modes ([#448](https://github.com/Python-roborock/python-roborock/pull/448),
  [`27fb9fc`](https://github.com/Python-roborock/python-roborock/commit/27fb9fc00c9c16235a983db0df4cc0d2cfb5f7b3))

- Add module for parsing map content
  ([#500](https://github.com/Python-roborock/python-roborock/pull/500),
  [`d5bb862`](https://github.com/Python-roborock/python-roborock/commit/d5bb8625ba6eb46a13b79df78a02f7e5e25cfd9f))

- Improve dynamic clean ([#448](https://github.com/Python-roborock/python-roborock/pull/448),
  [`27fb9fc`](https://github.com/Python-roborock/python-roborock/commit/27fb9fc00c9c16235a983db0df4cc0d2cfb5f7b3))

- Improve dynamic clean modes ([#448](https://github.com/Python-roborock/python-roborock/pull/448),
  [`27fb9fc`](https://github.com/Python-roborock/python-roborock/commit/27fb9fc00c9c16235a983db0df4cc0d2cfb5f7b3))


## v2.48.0 (2025-09-29)

### Chores

- Add gemini default ci actions
  ([#493](https://github.com/Python-roborock/python-roborock/pull/493),
  [`20e3c3d`](https://github.com/Python-roborock/python-roborock/commit/20e3c3da8100dd5e7b4a0b6418b41bb40a2efc36))

- Add imports for public APIs ([#501](https://github.com/Python-roborock/python-roborock/pull/501),
  [`21c83c0`](https://github.com/Python-roborock/python-roborock/commit/21c83c06116ef0c36dc7069cb2a3b822406de866))

### Features

- Add pdoc for leveraging python docstrings for documentation
  ([#501](https://github.com/Python-roborock/python-roborock/pull/501),
  [`21c83c0`](https://github.com/Python-roborock/python-roborock/commit/21c83c06116ef0c36dc7069cb2a3b822406de866))


## v2.47.1 (2025-09-22)

### Bug Fixes

- Improve new v1 apis to use mqtt lazily and work entirely locally
  ([#491](https://github.com/Python-roborock/python-roborock/pull/491),
  [`d0212e5`](https://github.com/Python-roborock/python-roborock/commit/d0212e58b032de2cce7c99691bdcec49ac8dfce2))

### Chores

- Extract caching logic to one place
  ([#491](https://github.com/Python-roborock/python-roborock/pull/491),
  [`d0212e5`](https://github.com/Python-roborock/python-roborock/commit/d0212e58b032de2cce7c99691bdcec49ac8dfce2))

- Remove unnecessary logging ([#491](https://github.com/Python-roborock/python-roborock/pull/491),
  [`d0212e5`](https://github.com/Python-roborock/python-roborock/commit/d0212e58b032de2cce7c99691bdcec49ac8dfce2))

- Remove whitespace ([#491](https://github.com/Python-roborock/python-roborock/pull/491),
  [`d0212e5`](https://github.com/Python-roborock/python-roborock/commit/d0212e58b032de2cce7c99691bdcec49ac8dfce2))

- Update comments ([#491](https://github.com/Python-roborock/python-roborock/pull/491),
  [`d0212e5`](https://github.com/Python-roborock/python-roborock/commit/d0212e58b032de2cce7c99691bdcec49ac8dfce2))


## v2.47.0 (2025-09-21)

### Bug Fixes

- Add version to ping ([#487](https://github.com/Python-roborock/python-roborock/pull/487),
  [`bff0e9c`](https://github.com/Python-roborock/python-roborock/commit/bff0e9c96b32d7a5c28e56488a7a92c57b098a46))

- Bug fixes for 1.0 ([#487](https://github.com/Python-roborock/python-roborock/pull/487),
  [`bff0e9c`](https://github.com/Python-roborock/python-roborock/commit/bff0e9c96b32d7a5c28e56488a7a92c57b098a46))

- Make sure we are connected on message send
  ([#487](https://github.com/Python-roborock/python-roborock/pull/487),
  [`bff0e9c`](https://github.com/Python-roborock/python-roborock/commit/bff0e9c96b32d7a5c28e56488a7a92c57b098a46))

- Potentially fix ping? ([#487](https://github.com/Python-roborock/python-roborock/pull/487),
  [`bff0e9c`](https://github.com/Python-roborock/python-roborock/commit/bff0e9c96b32d7a5c28e56488a7a92c57b098a46))

- Remove excluding ping from id check
  ([#487](https://github.com/Python-roborock/python-roborock/pull/487),
  [`bff0e9c`](https://github.com/Python-roborock/python-roborock/commit/bff0e9c96b32d7a5c28e56488a7a92c57b098a46))

- Some misc bug changes ([#487](https://github.com/Python-roborock/python-roborock/pull/487),
  [`bff0e9c`](https://github.com/Python-roborock/python-roborock/commit/bff0e9c96b32d7a5c28e56488a7a92c57b098a46))

- Some small changes ([#487](https://github.com/Python-roborock/python-roborock/pull/487),
  [`bff0e9c`](https://github.com/Python-roborock/python-roborock/commit/bff0e9c96b32d7a5c28e56488a7a92c57b098a46))

### Chores

- Add comment about rpc channel hacks and separate property files
  ([#489](https://github.com/Python-roborock/python-roborock/pull/489),
  [`362ec1d`](https://github.com/Python-roborock/python-roborock/commit/362ec1d3360e56cc4b98151b9c001bcdad64ffd2))

- Fix return types in CleanSummaryTrait
  ([#489](https://github.com/Python-roborock/python-roborock/pull/489),
  [`362ec1d`](https://github.com/Python-roborock/python-roborock/commit/362ec1d3360e56cc4b98151b9c001bcdad64ffd2))

- Init try based on Homey logic
  ([#487](https://github.com/Python-roborock/python-roborock/pull/487),
  [`bff0e9c`](https://github.com/Python-roborock/python-roborock/commit/bff0e9c96b32d7a5c28e56488a7a92c57b098a46))

- Only allow a single trait ([#489](https://github.com/Python-roborock/python-roborock/pull/489),
  [`362ec1d`](https://github.com/Python-roborock/python-roborock/commit/362ec1d3360e56cc4b98151b9c001bcdad64ffd2))

- Overhaul new device trait interfaces
  ([#489](https://github.com/Python-roborock/python-roborock/pull/489),
  [`362ec1d`](https://github.com/Python-roborock/python-roborock/commit/362ec1d3360e56cc4b98151b9c001bcdad64ffd2))

- Remove debug ([#487](https://github.com/Python-roborock/python-roborock/pull/487),
  [`bff0e9c`](https://github.com/Python-roborock/python-roborock/commit/bff0e9c96b32d7a5c28e56488a7a92c57b098a46))

- Remove unnecessarily local variables
  ([#489](https://github.com/Python-roborock/python-roborock/pull/489),
  [`362ec1d`](https://github.com/Python-roborock/python-roborock/commit/362ec1d3360e56cc4b98151b9c001bcdad64ffd2))

- Rename b01 properties to match v1
  ([#489](https://github.com/Python-roborock/python-roborock/pull/489),
  [`362ec1d`](https://github.com/Python-roborock/python-roborock/commit/362ec1d3360e56cc4b98151b9c001bcdad64ffd2))

- Set sign_key to private ([#488](https://github.com/Python-roborock/python-roborock/pull/488),
  [`ed46bce`](https://github.com/Python-roborock/python-roborock/commit/ed46bce0db7201c0416cdf6076b3403f5b1fad5e))

- Some potential clean up ([#487](https://github.com/Python-roborock/python-roborock/pull/487),
  [`bff0e9c`](https://github.com/Python-roborock/python-roborock/commit/bff0e9c96b32d7a5c28e56488a7a92c57b098a46))

### Features

- Implement L01 protocol ([#487](https://github.com/Python-roborock/python-roborock/pull/487),
  [`bff0e9c`](https://github.com/Python-roborock/python-roborock/commit/bff0e9c96b32d7a5c28e56488a7a92c57b098a46))

- Update CLI with new properties
  ([#489](https://github.com/Python-roborock/python-roborock/pull/489),
  [`362ec1d`](https://github.com/Python-roborock/python-roborock/commit/362ec1d3360e56cc4b98151b9c001bcdad64ffd2))


## v2.46.0 (2025-09-21)

### Bug Fixes

- Address some comments ([#460](https://github.com/Python-roborock/python-roborock/pull/460),
  [`599da6c`](https://github.com/Python-roborock/python-roborock/commit/599da6c044ba897b5005a2e1536ddc53af84cd4d))

- Handle auth expiring ([#460](https://github.com/Python-roborock/python-roborock/pull/460),
  [`599da6c`](https://github.com/Python-roborock/python-roborock/commit/599da6c044ba897b5005a2e1536ddc53af84cd4d))

- Mqtt error handling ([#460](https://github.com/Python-roborock/python-roborock/pull/460),
  [`599da6c`](https://github.com/Python-roborock/python-roborock/commit/599da6c044ba897b5005a2e1536ddc53af84cd4d))

- Str some other rcs ([#460](https://github.com/Python-roborock/python-roborock/pull/460),
  [`599da6c`](https://github.com/Python-roborock/python-roborock/commit/599da6c044ba897b5005a2e1536ddc53af84cd4d))

### Chores

- Add else back ([#460](https://github.com/Python-roborock/python-roborock/pull/460),
  [`599da6c`](https://github.com/Python-roborock/python-roborock/commit/599da6c044ba897b5005a2e1536ddc53af84cd4d))

- Clean up ([#460](https://github.com/Python-roborock/python-roborock/pull/460),
  [`599da6c`](https://github.com/Python-roborock/python-roborock/commit/599da6c044ba897b5005a2e1536ddc53af84cd4d))

- Inverse boolean logic to match variable naming
  ([#460](https://github.com/Python-roborock/python-roborock/pull/460),
  [`599da6c`](https://github.com/Python-roborock/python-roborock/commit/599da6c044ba897b5005a2e1536ddc53af84cd4d))

- Remove extra exception ([#460](https://github.com/Python-roborock/python-roborock/pull/460),
  [`599da6c`](https://github.com/Python-roborock/python-roborock/commit/599da6c044ba897b5005a2e1536ddc53af84cd4d))

### Features

- Add seperate validate connection for the cloud api and bump keepalive
  ([#460](https://github.com/Python-roborock/python-roborock/pull/460),
  [`599da6c`](https://github.com/Python-roborock/python-roborock/commit/599da6c044ba897b5005a2e1536ddc53af84cd4d))


## v2.45.0 (2025-09-21)

### Chores

- Add tests ([#486](https://github.com/Python-roborock/python-roborock/pull/486),
  [`1eebd29`](https://github.com/Python-roborock/python-roborock/commit/1eebd29231534d187699dfaaa7d6f5721a31b5c8))

- **deps**: Bump python-semantic-release/python-semantic-release
  ([#479](https://github.com/Python-roborock/python-roborock/pull/479),
  [`68f52ab`](https://github.com/Python-roborock/python-roborock/commit/68f52ab40f782766a73df7640df2b0a92f7d360f))

- **deps-dev**: Bump mypy from 1.17.1 to 1.18.1
  ([#478](https://github.com/Python-roborock/python-roborock/pull/478),
  [`efe460b`](https://github.com/Python-roborock/python-roborock/commit/efe460b2f8150fa34e33129854f6c2abb7ae1c4c))

- **deps-dev**: Bump pytest from 8.4.1 to 8.4.2
  ([#466](https://github.com/Python-roborock/python-roborock/pull/466),
  [`efa2922`](https://github.com/Python-roborock/python-roborock/commit/efa2922cb76e9716ff2ed0bd9edd92fbbcac36ce))

### Features

- Add v4 for code login ([#486](https://github.com/Python-roborock/python-roborock/pull/486),
  [`1eebd29`](https://github.com/Python-roborock/python-roborock/commit/1eebd29231534d187699dfaaa7d6f5721a31b5c8))


## v2.44.1 (2025-09-18)

### Bug Fixes

- Pass through additional fields to the home data fetcher
  ([#484](https://github.com/Python-roborock/python-roborock/pull/484),
  [`6fd180a`](https://github.com/Python-roborock/python-roborock/commit/6fd180a3277fe7d92f44e6af6575edeb6a682a45))

### Chores

- Add test coverage of end to end trait parsin from raw responses
  ([#482](https://github.com/Python-roborock/python-roborock/pull/482),
  [`0fac328`](https://github.com/Python-roborock/python-roborock/commit/0fac32824bb7edc71171a6ad6e44c61a298a9d11))

- Add test coverage of end to end trait parsing from raw responses
  ([#482](https://github.com/Python-roborock/python-roborock/pull/482),
  [`0fac328`](https://github.com/Python-roborock/python-roborock/commit/0fac32824bb7edc71171a6ad6e44c61a298a9d11))

- Fix lint errors ([#482](https://github.com/Python-roborock/python-roborock/pull/482),
  [`0fac328`](https://github.com/Python-roborock/python-roborock/commit/0fac32824bb7edc71171a6ad6e44c61a298a9d11))


## v2.44.0 (2025-09-15)

### Chores

- Fix imports ([#477](https://github.com/Python-roborock/python-roborock/pull/477),
  [`a391c17`](https://github.com/Python-roborock/python-roborock/commit/a391c1765e4b62004a290e1f63d46f7e722d4c49))

- Remove duplicate api_error from bad merge
  ([#477](https://github.com/Python-roborock/python-roborock/pull/477),
  [`a391c17`](https://github.com/Python-roborock/python-roborock/commit/a391c1765e4b62004a290e1f63d46f7e722d4c49))

- **deps-dev**: Bump pytest-asyncio from 1.1.0 to 1.2.0
  ([#480](https://github.com/Python-roborock/python-roborock/pull/480),
  [`772a829`](https://github.com/Python-roborock/python-roborock/commit/772a829f115138f9e99e26d3fb6950b743b1e8fe))

- **deps-dev**: Bump ruff from 0.12.9 to 0.13.0
  ([#481](https://github.com/Python-roborock/python-roborock/pull/481),
  [`c56252e`](https://github.com/Python-roborock/python-roborock/commit/c56252eb3882b4a1b4b3bc517206e34f5dcd4657))

### Features

- Add a sound volume trait ([#477](https://github.com/Python-roborock/python-roborock/pull/477),
  [`a391c17`](https://github.com/Python-roborock/python-roborock/commit/a391c1765e4b62004a290e1f63d46f7e722d4c49))

- Add volume trait ([#477](https://github.com/Python-roborock/python-roborock/pull/477),
  [`a391c17`](https://github.com/Python-roborock/python-roborock/commit/a391c1765e4b62004a290e1f63d46f7e722d4c49))


## v2.43.0 (2025-09-15)

### Features

- Add a clean summary trait ([#476](https://github.com/Python-roborock/python-roborock/pull/476),
  [`1585e1c`](https://github.com/Python-roborock/python-roborock/commit/1585e1ccd8cda8008a701e4289f4b2e3febb84f5))


## v2.42.0 (2025-09-14)

### Chores

- **deps**: Bump actions/setup-python from 5 to 6
  ([#465](https://github.com/Python-roborock/python-roborock/pull/465),
  [`7333643`](https://github.com/Python-roborock/python-roborock/commit/7333643417b57890a6fd18bc63929c2c48f45dbe))

- **deps**: Bump pypa/gh-action-pypi-publish from 1.12.4 to 1.13.0
  ([#463](https://github.com/Python-roborock/python-roborock/pull/463),
  [`ff44b2d`](https://github.com/Python-roborock/python-roborock/commit/ff44b2d1a2d5f70ed7b1ac10abe8295f39376180))

### Features

- Add ability to encrypt and decrypt L01
  ([#468](https://github.com/Python-roborock/python-roborock/pull/468),
  [`50aef42`](https://github.com/Python-roborock/python-roborock/commit/50aef42fa130f696fe367b3696547865bc7a690a))

- Add session to CLI ([#473](https://github.com/Python-roborock/python-roborock/pull/473),
  [`d58072e`](https://github.com/Python-roborock/python-roborock/commit/d58072eb12be15d5e1fcbd171e5434897497544c))


## v2.41.1 (2025-09-14)

### Bug Fixes

- Fix a bug with local / mqtt fallback
  ([#475](https://github.com/Python-roborock/python-roborock/pull/475),
  [`9f97a2b`](https://github.com/Python-roborock/python-roborock/commit/9f97a2bcf5189f515e9cd07629b65be7762c19ff))


## v2.41.0 (2025-09-14)

### Bug Fixes

- Fix bug parsing MultiMapsListMapInfo
  ([#474](https://github.com/Python-roborock/python-roborock/pull/474),
  [`d79ea3b`](https://github.com/Python-roborock/python-roborock/commit/d79ea3b76d9e1fedbb5fecd7edd21fcf07b29b80))

### Chores

- Revert changes to rpc channel
  ([#471](https://github.com/Python-roborock/python-roborock/pull/471),
  [`cce1c1b`](https://github.com/Python-roborock/python-roborock/commit/cce1c1b0a5db4a02be949a310ccd4356126bc229))

- Simplify command sending ([#471](https://github.com/Python-roborock/python-roborock/pull/471),
  [`cce1c1b`](https://github.com/Python-roborock/python-roborock/commit/cce1c1b0a5db4a02be949a310ccd4356126bc229))

### Features

- Add a DnD trait and fix bugs in the rpc channels
  ([#471](https://github.com/Python-roborock/python-roborock/pull/471),
  [`cce1c1b`](https://github.com/Python-roborock/python-roborock/commit/cce1c1b0a5db4a02be949a310ccd4356126bc229))


## v2.40.1 (2025-09-13)

### Bug Fixes

- Bug where the map requested from the app confuses our system
  ([#469](https://github.com/Python-roborock/python-roborock/pull/469),
  [`4ddfce0`](https://github.com/Python-roborock/python-roborock/commit/4ddfce0e0abcc21b97285aa7a5e585d5076c4f30))


## v2.40.0 (2025-09-07)

### Bug Fixes

- Missing code ([#462](https://github.com/Python-roborock/python-roborock/pull/462),
  [`99dd479`](https://github.com/Python-roborock/python-roborock/commit/99dd479029758186d5ad6efcc7420c18b1690dde))

- Wrong package ([#462](https://github.com/Python-roborock/python-roborock/pull/462),
  [`99dd479`](https://github.com/Python-roborock/python-roborock/commit/99dd479029758186d5ad6efcc7420c18b1690dde))

### Features

- Add l01 discovery ([#462](https://github.com/Python-roborock/python-roborock/pull/462),
  [`99dd479`](https://github.com/Python-roborock/python-roborock/commit/99dd479029758186d5ad6efcc7420c18b1690dde))


## v2.39.2 (2025-09-07)

### Bug Fixes

- Remove __del__ ([#459](https://github.com/Python-roborock/python-roborock/pull/459),
  [`62f19ca`](https://github.com/Python-roborock/python-roborock/commit/62f19ca37ee84a817e1e5444619b1bd1031d6626))

### Chores

- Move broadcast_protocol to its own file
  ([#459](https://github.com/Python-roborock/python-roborock/pull/459),
  [`62f19ca`](https://github.com/Python-roborock/python-roborock/commit/62f19ca37ee84a817e1e5444619b1bd1031d6626))

- Move broadcast_protocol to t's own file
  ([#459](https://github.com/Python-roborock/python-roborock/pull/459),
  [`62f19ca`](https://github.com/Python-roborock/python-roborock/commit/62f19ca37ee84a817e1e5444619b1bd1031d6626))


## v2.39.1 (2025-09-07)

### Bug Fixes

- Add missing finish reason ([#461](https://github.com/Python-roborock/python-roborock/pull/461),
  [`4d9ba70`](https://github.com/Python-roborock/python-roborock/commit/4d9ba70a9b18d56abd8583ae4f8c6ca33b833e2c))

### Chores

- Add snapshot tests for parsing device wire formats
  ([#457](https://github.com/Python-roborock/python-roborock/pull/457),
  [`d966b84`](https://github.com/Python-roborock/python-roborock/commit/d966b845d5c73ab6a15128e65785ee1306c8986b))

- Sort imports ([#457](https://github.com/Python-roborock/python-roborock/pull/457),
  [`d966b84`](https://github.com/Python-roborock/python-roborock/commit/d966b845d5c73ab6a15128e65785ee1306c8986b))


## v2.39.0 (2025-08-24)

### Bug Fixes

- Add more containers information
  ([#449](https://github.com/Python-roborock/python-roborock/pull/449),
  [`5ef1cd8`](https://github.com/Python-roborock/python-roborock/commit/5ef1cd833ea027b1dcd02b66694b37e404a63dc1))

- Get RoborockBase working for other files
  ([#449](https://github.com/Python-roborock/python-roborock/pull/449),
  [`5ef1cd8`](https://github.com/Python-roborock/python-roborock/commit/5ef1cd833ea027b1dcd02b66694b37e404a63dc1))

- Make code dynamic ([#449](https://github.com/Python-roborock/python-roborock/pull/449),
  [`5ef1cd8`](https://github.com/Python-roborock/python-roborock/commit/5ef1cd833ea027b1dcd02b66694b37e404a63dc1))

- Version check ([#449](https://github.com/Python-roborock/python-roborock/pull/449),
  [`5ef1cd8`](https://github.com/Python-roborock/python-roborock/commit/5ef1cd833ea027b1dcd02b66694b37e404a63dc1))

### Chores

- Fix style and comments ([#456](https://github.com/Python-roborock/python-roborock/pull/456),
  [`57d82e2`](https://github.com/Python-roborock/python-roborock/commit/57d82e2485fcf1cf63bd651427dd56b17f8cb694))

- Move imports ([#449](https://github.com/Python-roborock/python-roborock/pull/449),
  [`5ef1cd8`](https://github.com/Python-roborock/python-roborock/commit/5ef1cd833ea027b1dcd02b66694b37e404a63dc1))

- Remove registry ([#449](https://github.com/Python-roborock/python-roborock/pull/449),
  [`5ef1cd8`](https://github.com/Python-roborock/python-roborock/commit/5ef1cd833ea027b1dcd02b66694b37e404a63dc1))

- Unify callback handling recipes across mqtt and local channels
  ([#456](https://github.com/Python-roborock/python-roborock/pull/456),
  [`57d82e2`](https://github.com/Python-roborock/python-roborock/commit/57d82e2485fcf1cf63bd651427dd56b17f8cb694))

### Features

- Improve B01 support ([#449](https://github.com/Python-roborock/python-roborock/pull/449),
  [`5ef1cd8`](https://github.com/Python-roborock/python-roborock/commit/5ef1cd833ea027b1dcd02b66694b37e404a63dc1))


## v2.38.0 (2025-08-21)

### Bug Fixes

- Change to store info in a yaml file
  ([#428](https://github.com/Python-roborock/python-roborock/pull/428),
  [`41d5433`](https://github.com/Python-roborock/python-roborock/commit/41d543362c8163d565feffd2fd48425480159087))

### Chores

- Fix lint errors from merge ([#428](https://github.com/Python-roborock/python-roborock/pull/428),
  [`41d5433`](https://github.com/Python-roborock/python-roborock/commit/41d543362c8163d565feffd2fd48425480159087))

- Update doc ([#428](https://github.com/Python-roborock/python-roborock/pull/428),
  [`41d5433`](https://github.com/Python-roborock/python-roborock/commit/41d543362c8163d565feffd2fd48425480159087))

- **deps**: Bump actions/checkout from 4 to 5
  ([#454](https://github.com/Python-roborock/python-roborock/pull/454),
  [`2020f33`](https://github.com/Python-roborock/python-roborock/commit/2020f3386a8d69f94a01d433220b3081b661c86e))

- **deps-dev**: Bump ruff from 0.12.8 to 0.12.9
  ([#455](https://github.com/Python-roborock/python-roborock/pull/455),
  [`aec476c`](https://github.com/Python-roborock/python-roborock/commit/aec476c1c9b09e04f788a9825ed0ec590a205c30))

### Features

- Add the ability to update supported_features via cli
  ([#428](https://github.com/Python-roborock/python-roborock/pull/428),
  [`41d5433`](https://github.com/Python-roborock/python-roborock/commit/41d543362c8163d565feffd2fd48425480159087))


## v2.37.0 (2025-08-19)

### Bug Fixes

- Remove query_values response ([#453](https://github.com/Python-roborock/python-roborock/pull/453),
  [`0004721`](https://github.com/Python-roborock/python-roborock/commit/0004721d5264a13261d8485dd487de512d7c310e))

- Update mqtt channel to correctly handle multiple subscribers
  ([#453](https://github.com/Python-roborock/python-roborock/pull/453),
  [`0004721`](https://github.com/Python-roborock/python-roborock/commit/0004721d5264a13261d8485dd487de512d7c310e))

### Chores

- Remove dependencies on `get_request_id` in RequestMessage
  ([#452](https://github.com/Python-roborock/python-roborock/pull/452),
  [`f4dcea5`](https://github.com/Python-roborock/python-roborock/commit/f4dcea542477b1208591c2d316048d86080c48af))

- Remove pending rpcs object ([#453](https://github.com/Python-roborock/python-roborock/pull/453),
  [`0004721`](https://github.com/Python-roborock/python-roborock/commit/0004721d5264a13261d8485dd487de512d7c310e))

- Remove unnecessary whitespace
  ([#453](https://github.com/Python-roborock/python-roborock/pull/453),
  [`0004721`](https://github.com/Python-roborock/python-roborock/commit/0004721d5264a13261d8485dd487de512d7c310e))

- Update logging and comments ([#453](https://github.com/Python-roborock/python-roborock/pull/453),
  [`0004721`](https://github.com/Python-roborock/python-roborock/commit/0004721d5264a13261d8485dd487de512d7c310e))

- **deps**: Bump aiohttp from 3.12.13 to 3.12.15
  ([#446](https://github.com/Python-roborock/python-roborock/pull/446),
  [`b6bcb2a`](https://github.com/Python-roborock/python-roborock/commit/b6bcb2ab2cdebb07b540a573299520675257a1c9))

- **deps**: Bump pyrate-limiter from 3.7.0 to 3.9.0
  ([#445](https://github.com/Python-roborock/python-roborock/pull/445),
  [`8ac85da`](https://github.com/Python-roborock/python-roborock/commit/8ac85da5ecdbda5ef374b0cc492e505041cf8f4e))

- **deps-dev**: Bump freezegun from 1.5.4 to 1.5.5
  ([#444](https://github.com/Python-roborock/python-roborock/pull/444),
  [`e62168a`](https://github.com/Python-roborock/python-roborock/commit/e62168af067501fae2f853fb5924f787470fdd69))

- **deps-dev**: Bump mypy from 1.15.0 to 1.17.1
  ([#443](https://github.com/Python-roborock/python-roborock/pull/443),
  [`241b166`](https://github.com/Python-roborock/python-roborock/commit/241b1661063083b2685c420a8d931325106b341d))

### Features

- Fix a01 and b01 response handling in new api
  ([#453](https://github.com/Python-roborock/python-roborock/pull/453),
  [`0004721`](https://github.com/Python-roborock/python-roborock/commit/0004721d5264a13261d8485dd487de512d7c310e))


## v2.36.0 (2025-08-18)

### Chores

- Extract common module for manaing pending RPCs
  ([#451](https://github.com/Python-roborock/python-roborock/pull/451),
  [`d8ce60f`](https://github.com/Python-roborock/python-roborock/commit/d8ce60fe985f152c9f3485cbc12f8c04aaf041b1))

- Extract map parser into a separate function to share with new api
  ([#440](https://github.com/Python-roborock/python-roborock/pull/440),
  [`2a800c2`](https://github.com/Python-roborock/python-roborock/commit/2a800c2943bf0bb6389349798d26dab65411ae40))

- Remove docstrings ([#450](https://github.com/Python-roborock/python-roborock/pull/450),
  [`1addf95`](https://github.com/Python-roborock/python-roborock/commit/1addf95d5502dde8900bb4bceca418eaad179733))

- **deps-dev**: Bump pre-commit from 4.2.0 to 4.3.0
  ([#442](https://github.com/Python-roborock/python-roborock/pull/442),
  [`d59d6e3`](https://github.com/Python-roborock/python-roborock/commit/d59d6e331b4a03082d8f494117b28e04766e0e7b))

- **deps-dev**: Bump ruff from 0.12.0 to 0.12.8
  ([#441](https://github.com/Python-roborock/python-roborock/pull/441),
  [`e58bd95`](https://github.com/Python-roborock/python-roborock/commit/e58bd95d631bf0d85a66686fd0fab82528958458))

### Features

- Add container and function for app_init_status
  ([#450](https://github.com/Python-roborock/python-roborock/pull/450),
  [`1addf95`](https://github.com/Python-roborock/python-roborock/commit/1addf95d5502dde8900bb4bceca418eaad179733))


## v2.35.0 (2025-08-11)

### Chores

- Avoid re-parsing RoborockMessages and replace with passing explicit arguments
  ([#439](https://github.com/Python-roborock/python-roborock/pull/439),
  [`251b3f9`](https://github.com/Python-roborock/python-roborock/commit/251b3f9fbc245a606279dd4a00603efbf93daa26))

### Features

- Add dynamic clean modes ([#437](https://github.com/Python-roborock/python-roborock/pull/437),
  [`af17544`](https://github.com/Python-roborock/python-roborock/commit/af175440a3e754dc198f9026a4bcfd24b891f5ee))


## v2.34.2 (2025-08-11)

### Bug Fixes

- Merge the local api with the local v1 api
  ([#438](https://github.com/Python-roborock/python-roborock/pull/438),
  [`450e35e`](https://github.com/Python-roborock/python-roborock/commit/450e35e23ca591dcf75b916dd3be3daeb4a09e84))


## v2.34.1 (2025-08-10)

### Bug Fixes

- Fix "retry" error handling ([#436](https://github.com/Python-roborock/python-roborock/pull/436),
  [`eb6da93`](https://github.com/Python-roborock/python-roborock/commit/eb6da93478f89625ca71a381d5a104653d8888f4))


## v2.34.0 (2025-08-10)

### Chores

- Fix lint whitespace ([#435](https://github.com/Python-roborock/python-roborock/pull/435),
  [`a385a14`](https://github.com/Python-roborock/python-roborock/commit/a385a14816e835ad0d53de1afcd58036877a47ed))

- Fix merge with cache data rename
  ([#418](https://github.com/Python-roborock/python-roborock/pull/418),
  [`98ea911`](https://github.com/Python-roborock/python-roborock/commit/98ea911a313c71b65508b7c934b21c8379b3846e))

- Speed up mqtt session shutdown by avoiding a sleep
  ([#435](https://github.com/Python-roborock/python-roborock/pull/435),
  [`a385a14`](https://github.com/Python-roborock/python-roborock/commit/a385a14816e835ad0d53de1afcd58036877a47ed))

### Features

- Add some basic B01 support ([#429](https://github.com/Python-roborock/python-roborock/pull/429),
  [`72274e9`](https://github.com/Python-roborock/python-roborock/commit/72274e9aa23ed31327cd44200fd8c2f0bd26daff))

- Get_home_data_v3 for new devices
  ([#418](https://github.com/Python-roborock/python-roborock/pull/418),
  [`98ea911`](https://github.com/Python-roborock/python-roborock/commit/98ea911a313c71b65508b7c934b21c8379b3846e))

- Update cli.py and device_manager.py to use get_home_data_v3
  ([#418](https://github.com/Python-roborock/python-roborock/pull/418),
  [`98ea911`](https://github.com/Python-roborock/python-roborock/commit/98ea911a313c71b65508b7c934b21c8379b3846e))

- Use get_home_data_v3 for tests
  ([#418](https://github.com/Python-roborock/python-roborock/pull/418),
  [`98ea911`](https://github.com/Python-roborock/python-roborock/commit/98ea911a313c71b65508b7c934b21c8379b3846e))


## v2.33.0 (2025-08-10)

### Bug Fixes

- Adjust cache implementation defaults
  ([#432](https://github.com/Python-roborock/python-roborock/pull/432),
  [`f076a51`](https://github.com/Python-roborock/python-roborock/commit/f076a516b4569aa00ff767f19eab66eddba0b0b9))

### Chores

- Add back generator exception handling
  ([#434](https://github.com/Python-roborock/python-roborock/pull/434),
  [`c0f28da`](https://github.com/Python-roborock/python-roborock/commit/c0f28da1e5fbc707c5092baf179c8daa2d97db75))

- Fix lint errors ([#434](https://github.com/Python-roborock/python-roborock/pull/434),
  [`c0f28da`](https://github.com/Python-roborock/python-roborock/commit/c0f28da1e5fbc707c5092baf179c8daa2d97db75))

- Fix lint errors ([#432](https://github.com/Python-roborock/python-roborock/pull/432),
  [`f076a51`](https://github.com/Python-roborock/python-roborock/commit/f076a516b4569aa00ff767f19eab66eddba0b0b9))

- Update pytest-asyncio and fix clean shutdown
  ([#434](https://github.com/Python-roborock/python-roborock/pull/434),
  [`c0f28da`](https://github.com/Python-roborock/python-roborock/commit/c0f28da1e5fbc707c5092baf179c8daa2d97db75))

### Features

- Add an explicit module for caching
  ([#432](https://github.com/Python-roborock/python-roborock/pull/432),
  [`f076a51`](https://github.com/Python-roborock/python-roborock/commit/f076a516b4569aa00ff767f19eab66eddba0b0b9))

- Add explicit cache module ([#432](https://github.com/Python-roborock/python-roborock/pull/432),
  [`f076a51`](https://github.com/Python-roborock/python-roborock/commit/f076a516b4569aa00ff767f19eab66eddba0b0b9))

- Update the cli cache to also store network info
  ([#432](https://github.com/Python-roborock/python-roborock/pull/432),
  [`f076a51`](https://github.com/Python-roborock/python-roborock/commit/f076a516b4569aa00ff767f19eab66eddba0b0b9))


## v2.32.0 (2025-08-10)

### Bug Fixes

- Add test where current_map is none
  ([#433](https://github.com/Python-roborock/python-roborock/pull/433),
  [`0e28988`](https://github.com/Python-roborock/python-roborock/commit/0e289881e88632c1093827cf4f7d6b9076405c0b))

### Chores

- **deps**: Bump pycryptodome from 3.22.0 to 3.23.0
  ([#403](https://github.com/Python-roborock/python-roborock/pull/403),
  [`011631c`](https://github.com/Python-roborock/python-roborock/commit/011631ccdd5313bc5de9d72066fd7b255c8368e8))

- **deps**: Bump pycryptodomex from 3.22.0 to 3.23.0
  ([#404](https://github.com/Python-roborock/python-roborock/pull/404),
  [`c87d40b`](https://github.com/Python-roborock/python-roborock/commit/c87d40b446e5ab091465f2911e0470a9042f43cc))

- **deps**: Bump python-semantic-release/python-semantic-release
  ([#421](https://github.com/Python-roborock/python-roborock/pull/421),
  [`381acf6`](https://github.com/Python-roborock/python-roborock/commit/381acf64b9c5208950c555a92797c4c0cc0eb5ed))

- **deps-dev**: Bump freezegun from 1.5.1 to 1.5.4
  ([#423](https://github.com/Python-roborock/python-roborock/pull/423),
  [`1d3fe5c`](https://github.com/Python-roborock/python-roborock/commit/1d3fe5c7ca6ea215b3051759068b8a7843f87f4d))

- **deps-dev**: Bump pytest from 8.3.5 to 8.4.1
  ([#405](https://github.com/Python-roborock/python-roborock/pull/405),
  [`65e961b`](https://github.com/Python-roborock/python-roborock/commit/65e961b62bc6e248c966565da2470ae482aeafbd))

### Features

- Add property for accessing the current map from the status object
  ([#433](https://github.com/Python-roborock/python-roborock/pull/433),
  [`0e28988`](https://github.com/Python-roborock/python-roborock/commit/0e289881e88632c1093827cf4f7d6b9076405c0b))


## v2.31.0 (2025-08-10)

### Chores

- Fix lint errors ([#427](https://github.com/Python-roborock/python-roborock/pull/427),
  [`b4e3693`](https://github.com/Python-roborock/python-roborock/commit/b4e3693caad062ffaa20dd907a53eb5b15e5bd96))

### Features

- Update the cli cache to also store network info
  ([#427](https://github.com/Python-roborock/python-roborock/pull/427),
  [`b4e3693`](https://github.com/Python-roborock/python-roborock/commit/b4e3693caad062ffaa20dd907a53eb5b15e5bd96))


## v2.30.0 (2025-08-10)

### Chores

- Remove command info ([#430](https://github.com/Python-roborock/python-roborock/pull/430),
  [`04a83e8`](https://github.com/Python-roborock/python-roborock/commit/04a83e8485e297f329750e41fe663fe90819152e))

### Features

- Add a new type for supported features
  ([#431](https://github.com/Python-roborock/python-roborock/pull/431),
  [`b23c358`](https://github.com/Python-roborock/python-roborock/commit/b23c358b2cbc9642a8be908fa0864592f64df0fc))


## v2.29.1 (2025-08-09)

### Bug Fixes

- Add test coverage for extra keys
  ([#426](https://github.com/Python-roborock/python-roborock/pull/426),
  [`97dfd16`](https://github.com/Python-roborock/python-roborock/commit/97dfd1647ac16900875f1e77aadfbd7921a9fadc))

### Chores

- Cleanup whitespace ([#426](https://github.com/Python-roborock/python-roborock/pull/426),
  [`97dfd16`](https://github.com/Python-roborock/python-roborock/commit/97dfd1647ac16900875f1e77aadfbd7921a9fadc))

- Fix typing ([#426](https://github.com/Python-roborock/python-roborock/pull/426),
  [`97dfd16`](https://github.com/Python-roborock/python-roborock/commit/97dfd1647ac16900875f1e77aadfbd7921a9fadc))

- Remove container ([#426](https://github.com/Python-roborock/python-roborock/pull/426),
  [`97dfd16`](https://github.com/Python-roborock/python-roborock/commit/97dfd1647ac16900875f1e77aadfbd7921a9fadc))

- Remove unnecessary container ([#426](https://github.com/Python-roborock/python-roborock/pull/426),
  [`97dfd16`](https://github.com/Python-roborock/python-roborock/commit/97dfd1647ac16900875f1e77aadfbd7921a9fadc))

- Update container parsing using native typing and dataclass
  ([#426](https://github.com/Python-roborock/python-roborock/pull/426),
  [`97dfd16`](https://github.com/Python-roborock/python-roborock/commit/97dfd1647ac16900875f1e77aadfbd7921a9fadc))

- Update unknown key test to use simple object
  ([#426](https://github.com/Python-roborock/python-roborock/pull/426),
  [`97dfd16`](https://github.com/Python-roborock/python-roborock/commit/97dfd1647ac16900875f1e77aadfbd7921a9fadc))


## v2.29.0 (2025-08-09)

### Bug Fixes

- Add safety check for trait creation
  ([#425](https://github.com/Python-roborock/python-roborock/pull/425),
  [`f7d1a55`](https://github.com/Python-roborock/python-roborock/commit/f7d1a553677fd988c24891648410c144565c658b))

- Update mqtt payload encoding signature
  ([#425](https://github.com/Python-roborock/python-roborock/pull/425),
  [`f7d1a55`](https://github.com/Python-roborock/python-roborock/commit/f7d1a553677fd988c24891648410c144565c658b))

### Chores

- Address code review feedback ([#425](https://github.com/Python-roborock/python-roborock/pull/425),
  [`f7d1a55`](https://github.com/Python-roborock/python-roborock/commit/f7d1a553677fd988c24891648410c144565c658b))

- Revert encode_mqtt_payload typing change
  ([#425](https://github.com/Python-roborock/python-roborock/pull/425),
  [`f7d1a55`](https://github.com/Python-roborock/python-roborock/commit/f7d1a553677fd988c24891648410c144565c658b))

- Update roborock/devices/v1_channel.py
  ([#425](https://github.com/Python-roborock/python-roborock/pull/425),
  [`f7d1a55`](https://github.com/Python-roborock/python-roborock/commit/f7d1a553677fd988c24891648410c144565c658b))

### Features

- Support both a01 and v1 device types with traits
  ([#425](https://github.com/Python-roborock/python-roborock/pull/425),
  [`f7d1a55`](https://github.com/Python-roborock/python-roborock/commit/f7d1a553677fd988c24891648410c144565c658b))

- Update cli with v1 status trait
  ([#425](https://github.com/Python-roborock/python-roborock/pull/425),
  [`f7d1a55`](https://github.com/Python-roborock/python-roborock/commit/f7d1a553677fd988c24891648410c144565c658b))


## v2.28.0 (2025-08-09)

### Chores

- Add timeout to queue request to diagnose
  ([#420](https://github.com/Python-roborock/python-roborock/pull/420),
  [`717654a`](https://github.com/Python-roborock/python-roborock/commit/717654a648a86c1323048fb6cfdb022aef3097ec))

- Attempt to reduce a01 test flakiness by fixing shutdown to reduce number of active threads
  ([#420](https://github.com/Python-roborock/python-roborock/pull/420),
  [`717654a`](https://github.com/Python-roborock/python-roborock/commit/717654a648a86c1323048fb6cfdb022aef3097ec))

- Fix a01 client ([#420](https://github.com/Python-roborock/python-roborock/pull/420),
  [`717654a`](https://github.com/Python-roborock/python-roborock/commit/717654a648a86c1323048fb6cfdb022aef3097ec))

- Fix lint errors ([#420](https://github.com/Python-roborock/python-roborock/pull/420),
  [`717654a`](https://github.com/Python-roborock/python-roborock/commit/717654a648a86c1323048fb6cfdb022aef3097ec))

- Move device_features to seperate file and add some tests and rework device_features
  ([#365](https://github.com/Python-roborock/python-roborock/pull/365),
  [`c6ba0d6`](https://github.com/Python-roborock/python-roborock/commit/c6ba0d669f259744176821927c8606172c5c345d))

- Refactor some of the internal channel details used by the device.
  ([#424](https://github.com/Python-roborock/python-roborock/pull/424),
  [`cbd6df2`](https://github.com/Python-roborock/python-roborock/commit/cbd6df23da93681b72d47a68c1d64dcb25b27db5))

- Remove unnecessary command ([#424](https://github.com/Python-roborock/python-roborock/pull/424),
  [`cbd6df2`](https://github.com/Python-roborock/python-roborock/commit/cbd6df23da93681b72d47a68c1d64dcb25b27db5))

- Rename rpc channels to have v1 in the name
  ([#424](https://github.com/Python-roborock/python-roborock/pull/424),
  [`cbd6df2`](https://github.com/Python-roborock/python-roborock/commit/cbd6df23da93681b72d47a68c1d64dcb25b27db5))

- Separate V1 API connection logic from encoding logic
  ([#424](https://github.com/Python-roborock/python-roborock/pull/424),
  [`cbd6df2`](https://github.com/Python-roborock/python-roborock/commit/cbd6df23da93681b72d47a68c1d64dcb25b27db5))

- Update to the version from the other PR
  ([#365](https://github.com/Python-roborock/python-roborock/pull/365),
  [`c6ba0d6`](https://github.com/Python-roborock/python-roborock/commit/c6ba0d669f259744176821927c8606172c5c345d))

### Features

- Add device_features to automatically determine what is supported
  ([#365](https://github.com/Python-roborock/python-roborock/pull/365),
  [`c6ba0d6`](https://github.com/Python-roborock/python-roborock/commit/c6ba0d669f259744176821927c8606172c5c345d))


## v2.27.0 (2025-08-03)

### Bug Fixes

- Simplify local connection handling
  ([#416](https://github.com/Python-roborock/python-roborock/pull/416),
  [`c1bdac0`](https://github.com/Python-roborock/python-roborock/commit/c1bdac0ac56a9b86c33fb89c84c9eae92c9ed682))

- Update error message and add pydoc for exception handling on subscribe
  ([#416](https://github.com/Python-roborock/python-roborock/pull/416),
  [`c1bdac0`](https://github.com/Python-roborock/python-roborock/commit/c1bdac0ac56a9b86c33fb89c84c9eae92c9ed682))

- Update pydoc for sending a raw command
  ([#416](https://github.com/Python-roborock/python-roborock/pull/416),
  [`c1bdac0`](https://github.com/Python-roborock/python-roborock/commit/c1bdac0ac56a9b86c33fb89c84c9eae92c9ed682))

### Chores

- Remove whitespace ([#416](https://github.com/Python-roborock/python-roborock/pull/416),
  [`c1bdac0`](https://github.com/Python-roborock/python-roborock/commit/c1bdac0ac56a9b86c33fb89c84c9eae92c9ed682))

- **deps**: Bump click from 8.1.8 to 8.2.1
  ([#416](https://github.com/Python-roborock/python-roborock/pull/416),
  [`c1bdac0`](https://github.com/Python-roborock/python-roborock/commit/c1bdac0ac56a9b86c33fb89c84c9eae92c9ed682))

### Features

- Add a v1 protocol channel bridging across MQTT/Local channels
  ([#416](https://github.com/Python-roborock/python-roborock/pull/416),
  [`c1bdac0`](https://github.com/Python-roborock/python-roborock/commit/c1bdac0ac56a9b86c33fb89c84c9eae92c9ed682))

- Add a v1 protocol channel that can send messages across MQTT or Local connections, preferring
  local ([#416](https://github.com/Python-roborock/python-roborock/pull/416),
  [`c1bdac0`](https://github.com/Python-roborock/python-roborock/commit/c1bdac0ac56a9b86c33fb89c84c9eae92c9ed682))

- Fix tests referencing RoborockStateCode
  ([#416](https://github.com/Python-roborock/python-roborock/pull/416),
  [`c1bdac0`](https://github.com/Python-roborock/python-roborock/commit/c1bdac0ac56a9b86c33fb89c84c9eae92c9ed682))

- Fix tests reverted by co-pilot
  ([#416](https://github.com/Python-roborock/python-roborock/pull/416),
  [`c1bdac0`](https://github.com/Python-roborock/python-roborock/commit/c1bdac0ac56a9b86c33fb89c84c9eae92c9ed682))


## v2.26.0 (2025-08-03)

### Chores

- Move a01 encoding and decoding to a separate module
  ([#417](https://github.com/Python-roborock/python-roborock/pull/417),
  [`5a2dac0`](https://github.com/Python-roborock/python-roborock/commit/5a2dac0ae39d05fd71efa753fc860009d0a07428))

- Remove logging code ([#417](https://github.com/Python-roborock/python-roborock/pull/417),
  [`5a2dac0`](https://github.com/Python-roborock/python-roborock/commit/5a2dac0ae39d05fd71efa753fc860009d0a07428))

- Remove stale comment in roborock_client_a01.py
  ([#417](https://github.com/Python-roborock/python-roborock/pull/417),
  [`5a2dac0`](https://github.com/Python-roborock/python-roborock/commit/5a2dac0ae39d05fd71efa753fc860009d0a07428))

- Revert some logging changes ([#417](https://github.com/Python-roborock/python-roborock/pull/417),
  [`5a2dac0`](https://github.com/Python-roborock/python-roborock/commit/5a2dac0ae39d05fd71efa753fc860009d0a07428))

### Features

- Add Saros 10 code mappings ([#419](https://github.com/Python-roborock/python-roborock/pull/419),
  [`54a7e53`](https://github.com/Python-roborock/python-roborock/commit/54a7e53da7a482cd293243dd752bbe3ce77cbda3))


## v2.25.1 (2025-07-27)

### Bug Fixes

- Add saros 10r modes ([#415](https://github.com/Python-roborock/python-roborock/pull/415),
  [`7ebcde9`](https://github.com/Python-roborock/python-roborock/commit/7ebcde942587ab3de81783b4b6006080cd715466))

### Chores

- **deps**: Bump click from 8.1.8 to 8.2.1
  ([#401](https://github.com/Python-roborock/python-roborock/pull/401),
  [`36f5f2b`](https://github.com/Python-roborock/python-roborock/commit/36f5f2b76aee7d21da63e3f222cffa01d7e303b8))

- **deps**: Bump python-semantic-release/python-semantic-release
  ([#400](https://github.com/Python-roborock/python-roborock/pull/400),
  [`fd17a30`](https://github.com/Python-roborock/python-roborock/commit/fd17a307a74ab10550ac129590542528a8bac3ca))


## v2.25.0 (2025-07-15)

### Chores

- Change return type of caplog ([#411](https://github.com/Python-roborock/python-roborock/pull/411),
  [`f1dd1fe`](https://github.com/Python-roborock/python-roborock/commit/f1dd1fec36629cffb01e1a44ce96e36566bb4246))

- Create module for v1 request encoding
  ([#413](https://github.com/Python-roborock/python-roborock/pull/413),
  [`7507423`](https://github.com/Python-roborock/python-roborock/commit/7507423478c0a35375cc51fbffa043f015d73755))

- Delete tests/devices/test_v1_protocol.py
  ([#413](https://github.com/Python-roborock/python-roborock/pull/413),
  [`7507423`](https://github.com/Python-roborock/python-roborock/commit/7507423478c0a35375cc51fbffa043f015d73755))

- Enable verbose logging in CI ([#411](https://github.com/Python-roborock/python-roborock/pull/411),
  [`f1dd1fe`](https://github.com/Python-roborock/python-roborock/commit/f1dd1fec36629cffb01e1a44ce96e36566bb4246))

- Fix CI logging ([#411](https://github.com/Python-roborock/python-roborock/pull/411),
  [`f1dd1fe`](https://github.com/Python-roborock/python-roborock/commit/f1dd1fec36629cffb01e1a44ce96e36566bb4246))

- Fix lint ([#411](https://github.com/Python-roborock/python-roborock/pull/411),
  [`f1dd1fe`](https://github.com/Python-roborock/python-roborock/commit/f1dd1fec36629cffb01e1a44ce96e36566bb4246))

- Fix lint in test ([#412](https://github.com/Python-roborock/python-roborock/pull/412),
  [`ec780c9`](https://github.com/Python-roborock/python-roborock/commit/ec780c94c2de89fc565b24dc02fbaa3a5b531422))

- Fix warning in tests/devices/test_device_manager.py
  ([#412](https://github.com/Python-roborock/python-roborock/pull/412),
  [`ec780c9`](https://github.com/Python-roborock/python-roborock/commit/ec780c94c2de89fc565b24dc02fbaa3a5b531422))

- Remove incorrect caplog package
  ([#411](https://github.com/Python-roborock/python-roborock/pull/411),
  [`f1dd1fe`](https://github.com/Python-roborock/python-roborock/commit/f1dd1fec36629cffb01e1a44ce96e36566bb4246))

- Remove tests that timeout on CI
  ([#411](https://github.com/Python-roborock/python-roborock/pull/411),
  [`f1dd1fe`](https://github.com/Python-roborock/python-roborock/commit/f1dd1fec36629cffb01e1a44ce96e36566bb4246))

- Update log format to include timining information and thread names
  ([#411](https://github.com/Python-roborock/python-roborock/pull/411),
  [`f1dd1fe`](https://github.com/Python-roborock/python-roborock/commit/f1dd1fec36629cffb01e1a44ce96e36566bb4246))

### Features

- Simplify local payload encoding by rejecting any cloud commands sent locally
  ([#413](https://github.com/Python-roborock/python-roborock/pull/413),
  [`7507423`](https://github.com/Python-roborock/python-roborock/commit/7507423478c0a35375cc51fbffa043f015d73755))


## v2.24.0 (2025-07-05)

### Features

- Add a local channel, similar to the MQTT channel
  ([#410](https://github.com/Python-roborock/python-roborock/pull/410),
  [`1fb135b`](https://github.com/Python-roborock/python-roborock/commit/1fb135b763b8abe88d799fc609bdfc07077dee0a))

- Add debug lines ([#409](https://github.com/Python-roborock/python-roborock/pull/409),
  [`509ff6a`](https://github.com/Python-roborock/python-roborock/commit/509ff6aa223b4e49de1fe4fd70c8e2a2afbcb501))

- Add support for sending/recieving messages
  ([#409](https://github.com/Python-roborock/python-roborock/pull/409),
  [`509ff6a`](https://github.com/Python-roborock/python-roborock/commit/509ff6aa223b4e49de1fe4fd70c8e2a2afbcb501))

- Add test coverage for device manager close
  ([#409](https://github.com/Python-roborock/python-roborock/pull/409),
  [`509ff6a`](https://github.com/Python-roborock/python-roborock/commit/509ff6aa223b4e49de1fe4fd70c8e2a2afbcb501))

- Add test coverage to device modules
  ([#409](https://github.com/Python-roborock/python-roborock/pull/409),
  [`509ff6a`](https://github.com/Python-roborock/python-roborock/commit/509ff6aa223b4e49de1fe4fd70c8e2a2afbcb501))

- Apply suggestions from code review
  ([#409](https://github.com/Python-roborock/python-roborock/pull/409),
  [`509ff6a`](https://github.com/Python-roborock/python-roborock/commit/509ff6aa223b4e49de1fe4fd70c8e2a2afbcb501))

- Gather tasks ([#409](https://github.com/Python-roborock/python-roborock/pull/409),
  [`509ff6a`](https://github.com/Python-roborock/python-roborock/commit/509ff6aa223b4e49de1fe4fd70c8e2a2afbcb501))

- Log a warning when transport is already closed
  ([#410](https://github.com/Python-roborock/python-roborock/pull/410),
  [`1fb135b`](https://github.com/Python-roborock/python-roborock/commit/1fb135b763b8abe88d799fc609bdfc07077dee0a))

- Simplify rpc handling and tests
  ([#409](https://github.com/Python-roborock/python-roborock/pull/409),
  [`509ff6a`](https://github.com/Python-roborock/python-roborock/commit/509ff6aa223b4e49de1fe4fd70c8e2a2afbcb501))

- Update device manager and device to establish an MQTT subscription
  ([#409](https://github.com/Python-roborock/python-roborock/pull/409),
  [`509ff6a`](https://github.com/Python-roborock/python-roborock/commit/509ff6aa223b4e49de1fe4fd70c8e2a2afbcb501))

- Update roborock/devices/mqtt_channel.py
  ([#409](https://github.com/Python-roborock/python-roborock/pull/409),
  [`509ff6a`](https://github.com/Python-roborock/python-roborock/commit/509ff6aa223b4e49de1fe4fd70c8e2a2afbcb501))


## v2.23.0 (2025-07-01)

### Features

- Implement set_value method for a01 device protocols
  ([#408](https://github.com/Python-roborock/python-roborock/pull/408),
  [`011b253`](https://github.com/Python-roborock/python-roborock/commit/011b2538fc6c0876f2b40465f9a6474bd03d21c6))


## v2.22.0 (2025-07-01)

### Chores

- Increase test timeout to 30 seconds
  ([#407](https://github.com/Python-roborock/python-roborock/pull/407),
  [`e59c0b5`](https://github.com/Python-roborock/python-roborock/commit/e59c0b5948a83081a4a248fa2108fed81aa6f036))

### Features

- Add a CLI for exercising the asyncio MQTT session
  ([#396](https://github.com/Python-roborock/python-roborock/pull/396),
  [`54547d8`](https://github.com/Python-roborock/python-roborock/commit/54547d87bef080fe3ce03672509ba179bf7feafb))

- Fix lint error ([#396](https://github.com/Python-roborock/python-roborock/pull/396),
  [`54547d8`](https://github.com/Python-roborock/python-roborock/commit/54547d87bef080fe3ce03672509ba179bf7feafb))

- Remove unused import ([#396](https://github.com/Python-roborock/python-roborock/pull/396),
  [`54547d8`](https://github.com/Python-roborock/python-roborock/commit/54547d87bef080fe3ce03672509ba179bf7feafb))

- Share mqtt url parsing code with original client
  ([#396](https://github.com/Python-roborock/python-roborock/pull/396),
  [`54547d8`](https://github.com/Python-roborock/python-roborock/commit/54547d87bef080fe3ce03672509ba179bf7feafb))

- Update bytes dump ([#396](https://github.com/Python-roborock/python-roborock/pull/396),
  [`54547d8`](https://github.com/Python-roborock/python-roborock/commit/54547d87bef080fe3ce03672509ba179bf7feafb))


## v2.21.0 (2025-07-01)

### Chores

- Minor refactoring creating functions for transforming bytes
  ([#397](https://github.com/Python-roborock/python-roborock/pull/397),
  [`b19dbaa`](https://github.com/Python-roborock/python-roborock/commit/b19dbaac894a9fec8953e782cfb51433f19b2b90))

- Refactor authorization header
  ([#398](https://github.com/Python-roborock/python-roborock/pull/398),
  [`9e0ddf8`](https://github.com/Python-roborock/python-roborock/commit/9e0ddf89dfb18774b757ad07270de0be3af14561))

- **deps**: Bump vacuum-map-parser-roborock from 0.1.2 to 0.1.4
  ([#373](https://github.com/Python-roborock/python-roborock/pull/373),
  [`05966aa`](https://github.com/Python-roborock/python-roborock/commit/05966aa474227bbb1d58192d68b44f3003f97e86))

### Features

- Add a DeviceManager to perform discovery
  ([#399](https://github.com/Python-roborock/python-roborock/pull/399),
  [`e04a215`](https://github.com/Python-roborock/python-roborock/commit/e04a215bcadce6e582d92dce81f58e902391ec57))

- Fix lint error ([#399](https://github.com/Python-roborock/python-roborock/pull/399),
  [`e04a215`](https://github.com/Python-roborock/python-roborock/commit/e04a215bcadce6e582d92dce81f58e902391ec57))

- Update CLI to allow logging in with a code
  ([#395](https://github.com/Python-roborock/python-roborock/pull/395),
  [`e1a9e69`](https://github.com/Python-roborock/python-roborock/commit/e1a9e695362677d82abf1693bb8790537e38d2d1))

- Update review feedback ([#399](https://github.com/Python-roborock/python-roborock/pull/399),
  [`e04a215`](https://github.com/Python-roborock/python-roborock/commit/e04a215bcadce6e582d92dce81f58e902391ec57))

- Update tests with additional feedback
  ([#399](https://github.com/Python-roborock/python-roborock/pull/399),
  [`e04a215`](https://github.com/Python-roborock/python-roborock/commit/e04a215bcadce6e582d92dce81f58e902391ec57))


## v2.20.0 (2025-06-30)

### Bug Fixes

- Correct keepalive log message
  ([#385](https://github.com/Python-roborock/python-roborock/pull/385),
  [`8d4902b`](https://github.com/Python-roborock/python-roborock/commit/8d4902b408cba89daad7eb46d85ef7bdb4b8c8c7))

- Correct typos in log messages
  ([#385](https://github.com/Python-roborock/python-roborock/pull/385),
  [`8d4902b`](https://github.com/Python-roborock/python-roborock/commit/8d4902b408cba89daad7eb46d85ef7bdb4b8c8c7))

### Chores

- **deps**: Bump aiohttp from 3.11.16 to 3.12.13
  ([#390](https://github.com/Python-roborock/python-roborock/pull/390),
  [`e10b464`](https://github.com/Python-roborock/python-roborock/commit/e10b464b895fcbb8340fcf11ea7b5f2a2f33b676))

- **deps**: Bump python-semantic-release/python-semantic-release
  ([#391](https://github.com/Python-roborock/python-roborock/pull/391),
  [`6536700`](https://github.com/Python-roborock/python-roborock/commit/653670031bb366ed0e08d3daadb63d511795929c))

- **deps-dev**: Bump pre-commit from 4.1.0 to 4.2.0
  ([#358](https://github.com/Python-roborock/python-roborock/pull/358),
  [`9653abc`](https://github.com/Python-roborock/python-roborock/commit/9653abc2451d8b2d2f8c68232777d1419a194efb))

- **deps-dev**: Bump pytest-timeout from 2.3.1 to 2.4.0
  ([#379](https://github.com/Python-roborock/python-roborock/pull/379),
  [`150de05`](https://github.com/Python-roborock/python-roborock/commit/150de05390ce7e31862a202e99017932da3529a5))

- **deps-dev**: Bump ruff from 0.11.4 to 0.12.0
  ([#394](https://github.com/Python-roborock/python-roborock/pull/394),
  [`6ce7af8`](https://github.com/Python-roborock/python-roborock/commit/6ce7af82c847f7cdfa7107bae3505088437a9e66))

### Features

- Add Qrevo MaxV code mappings ([#385](https://github.com/Python-roborock/python-roborock/pull/385),
  [`8d4902b`](https://github.com/Python-roborock/python-roborock/commit/8d4902b408cba89daad7eb46d85ef7bdb4b8c8c7))

- Add support for roborock qrevo maxv code mappings
  ([#385](https://github.com/Python-roborock/python-roborock/pull/385),
  [`8d4902b`](https://github.com/Python-roborock/python-roborock/commit/8d4902b408cba89daad7eb46d85ef7bdb4b8c8c7))


## v2.19.0 (2025-05-13)

### Bug Fixes

- Add Saros 10 dock type code ([#362](https://github.com/Python-roborock/python-roborock/pull/362),
  [`240bf59`](https://github.com/Python-roborock/python-roborock/commit/240bf59df1873e85e05356496e5be01f1a000199))

### Chores

- **deps**: Bump aiomqtt from 2.3.2 to 2.4.0
  ([#375](https://github.com/Python-roborock/python-roborock/pull/375),
  [`b243a25`](https://github.com/Python-roborock/python-roborock/commit/b243a25569c2cb6b54e6c0e1eed6dadecb9ad84c))

Bumps [aiomqtt](https://github.com/empicano/aiomqtt) from 2.3.2 to 2.4.0. - [Release
  notes](https://github.com/empicano/aiomqtt/releases) -
  [Changelog](https://github.com/empicano/aiomqtt/blob/main/CHANGELOG.md) -
  [Commits](https://github.com/empicano/aiomqtt/compare/v2.3.2...v2.4.0)

--- updated-dependencies: - dependency-name: aiomqtt dependency-version: 2.4.0

dependency-type: direct:production

update-type: version-update:semver-minor ...

Signed-off-by: dependabot[bot] <support@github.com>

Co-authored-by: dependabot[bot] <49699333+dependabot[bot]@users.noreply.github.com>

### Features

- Add some logging for the web api
  ([#377](https://github.com/Python-roborock/python-roborock/pull/377),
  [`74c1b5f`](https://github.com/Python-roborock/python-roborock/commit/74c1b5f6e88ce410f95676de802bd04d304963b1))


## v2.18.2 (2025-05-04)

### Bug Fixes

- Add session to home_data_v3 ([#372](https://github.com/Python-roborock/python-roborock/pull/372),
  [`77061fe`](https://github.com/Python-roborock/python-roborock/commit/77061fe1545a3d2f9e874a3f7e4a94eedfd17706))


## v2.18.1 (2025-05-04)

### Bug Fixes

- Get home_data_v3 working ([#371](https://github.com/Python-roborock/python-roborock/pull/371),
  [`f9e6c54`](https://github.com/Python-roborock/python-roborock/commit/f9e6c546e68a71a321dafabd5d502abef3e89b31))


## v2.18.0 (2025-04-06)

### Features

- Rate limits for login and home data
  ([#361](https://github.com/Python-roborock/python-roborock/pull/361),
  [`93ef8ad`](https://github.com/Python-roborock/python-roborock/commit/93ef8addfd2faa6264606c9d710c46772cd52150))

* feat: rate limits for login and home data

* fix: comments

* fix: testing and comments


## v2.17.0 (2025-04-05)

### Features

- Add support for g20s ultra ([#359](https://github.com/Python-roborock/python-roborock/pull/359),
  [`593c368`](https://github.com/Python-roborock/python-roborock/commit/593c3687064779ee6790e17f40411cd8129b756e))


## v2.16.1 (2025-03-22)

### Bug Fixes

- Close the session if we created it
  ([#356](https://github.com/Python-roborock/python-roborock/pull/356),
  [`96cc718`](https://github.com/Python-roborock/python-roborock/commit/96cc718dbd4106fa344172e2dbf0c3779344ba04))


## v2.16.0 (2025-03-22)

### Features

- Allow forcing of updating cache variables
  ([#355](https://github.com/Python-roborock/python-roborock/pull/355),
  [`eae7803`](https://github.com/Python-roborock/python-roborock/commit/eae7803db8973870c396ce45341e5d38cbfaf321))


## v2.15.0 (2025-03-18)

### Chores

- Fix documentation links ([#348](https://github.com/Python-roborock/python-roborock/pull/348),
  [`404a47c`](https://github.com/Python-roborock/python-roborock/commit/404a47c8c51891ed90093869e567d56386cdc4a2))

### Features

- Allow passing in clientsession
  ([#354](https://github.com/Python-roborock/python-roborock/pull/354),
  [`1d31cf6`](https://github.com/Python-roborock/python-roborock/commit/1d31cf619ef38dfdd2891cd42c0acf4550b88c29))

* feat: allow passing in clientsession

* fix: test


## v2.14.0 (2025-03-16)

### Features

- Add load_multi_map function ([#349](https://github.com/Python-roborock/python-roborock/pull/349),
  [`23bae12`](https://github.com/Python-roborock/python-roborock/commit/23bae1225389b6ec88bad868b8c6d4a28f458e61))


## v2.13.0 (2025-03-16)

### Features

- Add home_data_v3 ([#347](https://github.com/Python-roborock/python-roborock/pull/347),
  [`1325fda`](https://github.com/Python-roborock/python-roborock/commit/1325fdaef0f9d920ab499a0550da51cdb8efc0c4))

* feat: add home_data_v3

* fix: address comments


## v2.12.2 (2025-03-11)

### Bug Fixes

- Bad dock summary logic ([#345](https://github.com/Python-roborock/python-roborock/pull/345),
  [`eda1e98`](https://github.com/Python-roborock/python-roborock/commit/eda1e98e5ea177e2eb2390d877b383780f938fd8))

### Chores

- **deps-dev**: Bump pytest from 8.3.4 to 8.3.5
  ([#342](https://github.com/Python-roborock/python-roborock/pull/342),
  [`53635ed`](https://github.com/Python-roborock/python-roborock/commit/53635eda2a2415fc5744f9ebdf8e80fb2df96ef0))

Bumps [pytest](https://github.com/pytest-dev/pytest) from 8.3.4 to 8.3.5. - [Release
  notes](https://github.com/pytest-dev/pytest/releases) -
  [Changelog](https://github.com/pytest-dev/pytest/blob/main/CHANGELOG.rst) -
  [Commits](https://github.com/pytest-dev/pytest/compare/8.3.4...8.3.5)

--- updated-dependencies: - dependency-name: pytest dependency-type: direct:development

update-type: version-update:semver-patch ...

Signed-off-by: dependabot[bot] <support@github.com>

Co-authored-by: dependabot[bot] <49699333+dependabot[bot]@users.noreply.github.com>

- **deps-dev**: Bump ruff from 0.9.9 to 0.9.10
  ([#344](https://github.com/Python-roborock/python-roborock/pull/344),
  [`94b281d`](https://github.com/Python-roborock/python-roborock/commit/94b281daf5906ec572fa679869eb78fab030db59))

Bumps [ruff](https://github.com/astral-sh/ruff) from 0.9.9 to 0.9.10. - [Release
  notes](https://github.com/astral-sh/ruff/releases) -
  [Changelog](https://github.com/astral-sh/ruff/blob/main/CHANGELOG.md) -
  [Commits](https://github.com/astral-sh/ruff/compare/0.9.9...0.9.10)

--- updated-dependencies: - dependency-name: ruff dependency-type: direct:development

update-type: version-update:semver-patch ...

Signed-off-by: dependabot[bot] <support@github.com>

Co-authored-by: dependabot[bot] <49699333+dependabot[bot]@users.noreply.github.com>


## v2.12.1 (2025-03-04)

### Bug Fixes

- Add error for web calls and saros dock
  ([#343](https://github.com/Python-roborock/python-roborock/pull/343),
  [`49fb137`](https://github.com/Python-roborock/python-roborock/commit/49fb1372aead96ad5b03222699ab150bf83b31f9))

### Chores

- **deps**: Bump aiohttp from 3.11.11 to 3.11.12
  ([#328](https://github.com/Python-roborock/python-roborock/pull/328),
  [`f2d0c39`](https://github.com/Python-roborock/python-roborock/commit/f2d0c39353aff0d2f63ba5402cbfd1fd5c9f70c3))

--- updated-dependencies: - dependency-name: aiohttp dependency-type: direct:production

update-type: version-update:semver-patch ...

Signed-off-by: dependabot[bot] <support@github.com>

Co-authored-by: dependabot[bot] <49699333+dependabot[bot]@users.noreply.github.com>

- **deps**: Bump aiohttp from 3.11.12 to 3.11.13
  ([#340](https://github.com/Python-roborock/python-roborock/pull/340),
  [`7c6bb54`](https://github.com/Python-roborock/python-roborock/commit/7c6bb544fe14b0512eb4cc73f3d92f19fc56f4f7))

--- updated-dependencies: - dependency-name: aiohttp dependency-type: direct:production

update-type: version-update:semver-patch ...

Signed-off-by: dependabot[bot] <support@github.com>

Co-authored-by: dependabot[bot] <49699333+dependabot[bot]@users.noreply.github.com>

- **deps**: Bump python-semantic-release/python-semantic-release
  ([#338](https://github.com/Python-roborock/python-roborock/pull/338),
  [`15f7705`](https://github.com/Python-roborock/python-roborock/commit/15f77056b8f2c4dcd2772812c6c2f9647f808bcd))

Bumps
  [python-semantic-release/python-semantic-release](https://github.com/python-semantic-release/python-semantic-release)
  from 9.17.0 to 9.21.0. - [Release
  notes](https://github.com/python-semantic-release/python-semantic-release/releases) -
  [Changelog](https://github.com/python-semantic-release/python-semantic-release/blob/master/CHANGELOG.rst)
  -
  [Commits](https://github.com/python-semantic-release/python-semantic-release/compare/v9.17.0...v9.21.0)

--- updated-dependencies: - dependency-name: python-semantic-release/python-semantic-release
  dependency-type: direct:production

update-type: version-update:semver-minor ...

Signed-off-by: dependabot[bot] <support@github.com>

Co-authored-by: dependabot[bot] <49699333+dependabot[bot]@users.noreply.github.com>

- **deps-dev**: Bump mypy from 1.14.1 to 1.15.0
  ([#329](https://github.com/Python-roborock/python-roborock/pull/329),
  [`2105cdf`](https://github.com/Python-roborock/python-roborock/commit/2105cdf2a29a1ad1c1c9117e3dff4c4548466d4f))

Bumps [mypy](https://github.com/python/mypy) from 1.14.1 to 1.15.0. -
  [Changelog](https://github.com/python/mypy/blob/master/CHANGELOG.md) -
  [Commits](https://github.com/python/mypy/compare/v1.14.1...v1.15.0)

--- updated-dependencies: - dependency-name: mypy dependency-type: direct:development

update-type: version-update:semver-minor ...

Signed-off-by: dependabot[bot] <support@github.com>

Co-authored-by: dependabot[bot] <49699333+dependabot[bot]@users.noreply.github.com>

- **deps-dev**: Bump ruff from 0.9.4 to 0.9.9
  ([#341](https://github.com/Python-roborock/python-roborock/pull/341),
  [`4e80f7a`](https://github.com/Python-roborock/python-roborock/commit/4e80f7a86764240729982de3336173231fac6a08))

Bumps [ruff](https://github.com/astral-sh/ruff) from 0.9.4 to 0.9.9. - [Release
  notes](https://github.com/astral-sh/ruff/releases) -
  [Changelog](https://github.com/astral-sh/ruff/blob/main/CHANGELOG.md) -
  [Commits](https://github.com/astral-sh/ruff/compare/0.9.4...0.9.9)

--- updated-dependencies: - dependency-name: ruff dependency-type: direct:development

update-type: version-update:semver-patch ...

Signed-off-by: dependabot[bot] <support@github.com>

Co-authored-by: dependabot[bot] <49699333+dependabot[bot]@users.noreply.github.com>


## v2.12.0 (2025-02-21)

### Features

- Add cli status ([#333](https://github.com/Python-roborock/python-roborock/pull/333),
  [`64e77d7`](https://github.com/Python-roborock/python-roborock/commit/64e77d7150babcc78ce3698fe98594891dcb7bd4))


## v2.11.3 (2025-02-19)

### Bug Fixes

- Q revo curv mappings ([#332](https://github.com/Python-roborock/python-roborock/pull/332),
  [`83d010a`](https://github.com/Python-roborock/python-roborock/commit/83d010acbc100f06ae322adde1eedcfd0f78efc8))


## v2.11.2 (2025-02-13)

### Bug Fixes

- Add some extra data protocol checking
  ([#331](https://github.com/Python-roborock/python-roborock/pull/331),
  [`4af1490`](https://github.com/Python-roborock/python-roborock/commit/4af1490ea4db0dbeb5d5666019d9433af4f3d273))


## v2.11.1 (2025-02-03)

### Bug Fixes

- Typing of scene api call ([#324](https://github.com/Python-roborock/python-roborock/pull/324),
  [`61e27ae`](https://github.com/Python-roborock/python-roborock/commit/61e27aedfbb363913f80ace3932fa4adf61f9792))


## v2.11.0 (2025-02-03)

### Chores

- **deps**: Bump pypa/gh-action-pypi-publish from 1.12.3 to 1.12.4
  ([#311](https://github.com/Python-roborock/python-roborock/pull/311),
  [`cb40279`](https://github.com/Python-roborock/python-roborock/commit/cb4027994e4ee0b72f25d9f51f46f8b3f9522bc5))

- **deps**: Bump python-semantic-release/python-semantic-release
  ([#312](https://github.com/Python-roborock/python-roborock/pull/312),
  [`7827af5`](https://github.com/Python-roborock/python-roborock/commit/7827af5ef7e6fb2dedd6eef0cb8c0c8439d2a8ef))

- **deps**: Bump python-semantic-release/upload-to-gh-release
  ([#290](https://github.com/Python-roborock/python-roborock/pull/290),
  [`87038e3`](https://github.com/Python-roborock/python-roborock/commit/87038e3a556a359d552775195d7640b6cdbeb1fe))

- **deps**: Bump wagoid/commitlint-github-action from 6.2.0 to 6.2.1
  ([#296](https://github.com/Python-roborock/python-roborock/pull/296),
  [`037e28c`](https://github.com/Python-roborock/python-roborock/commit/037e28c38df282dac09bd4ff9596dc0b3a09c78f))

- **deps-dev**: Bump codespell from 2.3.0 to 2.4.1
  ([#321](https://github.com/Python-roborock/python-roborock/pull/321),
  [`c36d46f`](https://github.com/Python-roborock/python-roborock/commit/c36d46f90780db50f2c5c2e947ada78b6ee4967c))

- **deps-dev**: Bump pytest-asyncio from 0.25.2 to 0.25.3
  ([#322](https://github.com/Python-roborock/python-roborock/pull/322),
  [`9e40fe7`](https://github.com/Python-roborock/python-roborock/commit/9e40fe780224903c8e81c4d210ab61212582948d))

- **deps-dev**: Bump ruff from 0.9.2 to 0.9.4
  ([#323](https://github.com/Python-roborock/python-roborock/pull/323),
  [`25d15a7`](https://github.com/Python-roborock/python-roborock/commit/25d15a78d1f5ffb069159aa652c2ef3f88d3eb03))

### Features

- Add scenes/routines support ([#317](https://github.com/Python-roborock/python-roborock/pull/317),
  [`090d912`](https://github.com/Python-roborock/python-roborock/commit/090d912872712e16b24597826a0b85d22b37acb3))

* add scenes support

---------

Co-authored-by: Luke Lashley <conway220@gmail.com>


## v2.10.1 (2025-02-03)

### Bug Fixes

- Delete in cli ([#320](https://github.com/Python-roborock/python-roborock/pull/320),
  [`6704f55`](https://github.com/Python-roborock/python-roborock/commit/6704f55915005d771d698e58dcbac5ec46a385e5))


## v2.10.0 (2025-01-31)

### Features

- Add commands to add a new device
  ([#307](https://github.com/Python-roborock/python-roborock/pull/307),
  [`430c248`](https://github.com/Python-roborock/python-roborock/commit/430c24806fa06a5cec6c7fb3945a9b9cbfbc2f7a))

* feat: add commands to add a new device

* chore: mr comments


## v2.9.8 (2025-01-30)

### Bug Fixes

- Ignore ping id during id check
  ([#316](https://github.com/Python-roborock/python-roborock/pull/316),
  [`b3d74b4`](https://github.com/Python-roborock/python-roborock/commit/b3d74b4bc9fa581da0485cf68a46c23f53fdbf50))


## v2.9.7 (2025-01-28)

### Bug Fixes

- Never create a new asyncio loop
  ([#310](https://github.com/Python-roborock/python-roborock/pull/310),
  [`ed7db1f`](https://github.com/Python-roborock/python-roborock/commit/ed7db1f09f379f509a38a61a445fb2c41b384f25))


## v2.9.6 (2025-01-26)

### Bug Fixes

- Remove the __del__ warning for disconnected clients
  ([#308](https://github.com/Python-roborock/python-roborock/pull/308),
  [`235752b`](https://github.com/Python-roborock/python-roborock/commit/235752bd77e4617323366b56439bf8981b071430))

### Refactoring

- Breaking change to remove sync APIs
  ([#306](https://github.com/Python-roborock/python-roborock/pull/306),
  [`3c30d93`](https://github.com/Python-roborock/python-roborock/commit/3c30d933f680cc567b10ad6566b02289eade5b3f))

* refactor: breaking change to remove sync APIs

* chore: downgrade log to a debug message


## v2.9.5 (2025-01-21)

### Bug Fixes

- Fix queue timeout variable and set default in tests of 10 seconds
  ([#302](https://github.com/Python-roborock/python-roborock/pull/302),
  [`9c75e3a`](https://github.com/Python-roborock/python-roborock/commit/9c75e3a67fc8f411c5496b5864a9a0e90a573c8a))

* test: set queue timeout of 10

* test: cleanup lint errors

* fix: set queue_timeout in the client leaf base classes

* chore: fix test fixture after merging

- Log an explicit message when intentionally resetting the connection
  ([#304](https://github.com/Python-roborock/python-roborock/pull/304),
  [`a20d2ac`](https://github.com/Python-roborock/python-roborock/commit/a20d2ac46c7553c7b7c7dffbbc86ee0da370418d))


## v2.9.4 (2025-01-21)

### Bug Fixes

- Bump paho-mqtt from 1.6.1 to 2.1.0
  ([#288](https://github.com/Python-roborock/python-roborock/pull/288),
  [`777b736`](https://github.com/Python-roborock/python-roborock/commit/777b736440a3633c089bf09ab9d7240e54e0fb0e))

Bumps [paho-mqtt](https://github.com/eclipse/paho.mqtt.python) from 1.6.1 to 2.1.0. - [Release
  notes](https://github.com/eclipse/paho.mqtt.python/releases) -
  [Changelog](https://github.com/eclipse-paho/paho.mqtt.python/blob/master/ChangeLog.txt) -
  [Commits](https://github.com/eclipse/paho.mqtt.python/compare/v1.6.1...v2.1.0)

--- updated-dependencies: - dependency-name: paho-mqtt dependency-type: direct:production

update-type: version-update:semver-major ...

Signed-off-by: dependabot[bot] <support@github.com>

Co-authored-by: dependabot[bot] <49699333+dependabot[bot]@users.noreply.github.com>

- Set unique sequence numbers on outgoing messages
  ([#300](https://github.com/Python-roborock/python-roborock/pull/300),
  [`14f03c7`](https://github.com/Python-roborock/python-roborock/commit/14f03c7df1c574ab87ea056227bb95f9150f4832))

### Chores

- Fix flaky tests by cleaning up threads
  ([#303](https://github.com/Python-roborock/python-roborock/pull/303),
  [`6e29e74`](https://github.com/Python-roborock/python-roborock/commit/6e29e7440f61ddde9a67b25c87864ed0cbf1a097))

* chore: set log level to debug to aid in tracking down flaky tests

* test: update log format to include timestamps and dates

test: update logmessage with package name

chore: fix tests to use valid zeo codes

* test: fix zeo test assertion

* test: add logging when updating future

* test: make the client read socket always available for reading to avoid getting blocked

* test: revert socket changes

* test: set function loop scope

* test: add pytest-timeout with a 20 second hard timeout

* test: explicitly disconnect threads

* test: fix formatting

* test: fix lint errors

* fix: stop the mqtt loop on disconnect

* fix: release the mqtt thread on release

* test: revert log changes

* chore: cleanup/revert changes

* chore: revert mqtt client check

* fix: always stop the event loop when disconnecting


## v2.9.3 (2025-01-21)

### Bug Fixes

- Remove methods no longer available in paho-mqtt
  ([#298](https://github.com/Python-roborock/python-roborock/pull/298),
  [`685edc8`](https://github.com/Python-roborock/python-roborock/commit/685edc825fbf2062d61c3294ea82c4566442dd64))

### Chores

- Remove test that creates abstract base class
  ([#299](https://github.com/Python-roborock/python-roborock/pull/299),
  [`a55b804`](https://github.com/Python-roborock/python-roborock/commit/a55b804fddff318d704cc04e6c4190514e3e3375))

- **deps-dev**: Bump aioresponses from 0.7.7 to 0.7.8
  ([#295](https://github.com/Python-roborock/python-roborock/pull/295),
  [`ab7ffb3`](https://github.com/Python-roborock/python-roborock/commit/ab7ffb36190090e6d5b39150da4ebe2f2e22fbd4))

Bumps [aioresponses](https://github.com/pnuckowski/aioresponses) from 0.7.7 to 0.7.8. - [Release
  notes](https://github.com/pnuckowski/aioresponses/releases) -
  [Commits](https://github.com/pnuckowski/aioresponses/compare/0.7.7...0.7.8)

--- updated-dependencies: - dependency-name: aioresponses dependency-type: direct:development

update-type: version-update:semver-patch ...

Signed-off-by: dependabot[bot] <support@github.com>

Co-authored-by: dependabot[bot] <49699333+dependabot[bot]@users.noreply.github.com>


## v2.9.2 (2025-01-19)

### Bug Fixes

- Update local API protocol broken during refactoring and add additional tests for API calls
  ([#293](https://github.com/Python-roborock/python-roborock/pull/293),
  [`ea8e55a`](https://github.com/Python-roborock/python-roborock/commit/ea8e55a0b9c54e7c7d6235ad0e73f7b75ec4de7b))

* test: add an additional local API test and fix bug in test fixture

* test: fix formatting

* fix: Update local API

### Chores

- Remove dacite and update readme
  ([#294](https://github.com/Python-roborock/python-roborock/pull/294),
  [`699a2c5`](https://github.com/Python-roborock/python-roborock/commit/699a2c5ed5362ee4004d2888037baf929869e98c))

- Update CI to run on one platform, but multiple python versions
  ([#292](https://github.com/Python-roborock/python-roborock/pull/292),
  [`16ab4ff`](https://github.com/Python-roborock/python-roborock/commit/16ab4ff433d25df9daa4bf102569c39bbd686420))


## v2.9.1 (2025-01-13)

### Bug Fixes

- Bump commitlint and allow caps
  ([#283](https://github.com/Python-roborock/python-roborock/pull/283),
  [`6211a81`](https://github.com/Python-roborock/python-roborock/commit/6211a8163d130c41594daf65e36be2d87788a5c6))

* fix: bump commitlint and allow caps

* fix: error

### Chores

- Add end-to-end tests for the MQTT client
  ([#278](https://github.com/Python-roborock/python-roborock/pull/278),
  [`0872691`](https://github.com/Python-roborock/python-roborock/commit/0872691c9eeb6e564a1ee47b8ba2bec73eb81a63))

* test: add end-to-end tests for the MQTT client

* test: extract connected client to a fixture

style: fix formatting of tests

refactor: extract variables for mock data used in mqtt tests

style: fix lint errors in tests

- Add local api test coverage ([#284](https://github.com/Python-roborock/python-roborock/pull/284),
  [`c8dcd34`](https://github.com/Python-roborock/python-roborock/commit/c8dcd34c8197b9d47ec3c96567313d658e0f36b3))

- Allow type checking in roborock/cloud_api.py
  ([#280](https://github.com/Python-roborock/python-roborock/pull/280),
  [`9100bbf`](https://github.com/Python-roborock/python-roborock/commit/9100bbff1390a706a74dc0ec15c1bb1d7dc83d9f))

- Inheritance fixes and simplifications
  ([#282](https://github.com/Python-roborock/python-roborock/pull/282),
  [`1013cb5`](https://github.com/Python-roborock/python-roborock/commit/1013cb5f35ec6feb71e58a437395b0cdaa593937))

- Remove level of inheritance in mqtt client
  ([#286](https://github.com/Python-roborock/python-roborock/pull/286),
  [`5add0da`](https://github.com/Python-roborock/python-roborock/commit/5add0dac8d1e1e86b184ebad709034ea2a2686a3))

- Remove one level of local client inheritence
  ([#285](https://github.com/Python-roborock/python-roborock/pull/285),
  [`1f5a9ec`](https://github.com/Python-roborock/python-roborock/commit/1f5a9ecd907c0314cc156a59156b03151e9c26a8))

- Use asyncio mode in tests ([#272](https://github.com/Python-roborock/python-roborock/pull/272),
  [`8f779c3`](https://github.com/Python-roborock/python-roborock/commit/8f779c39b21ab429335fc5d179fe3bacc0b5d274))

- **deps**: Bump pre-commit/action from 3.0.0 to 3.0.1
  ([#276](https://github.com/Python-roborock/python-roborock/pull/276),
  [`3f61bcc`](https://github.com/Python-roborock/python-roborock/commit/3f61bccde418c9e9e04ef059ca8a6a2dfcba8312))

- **deps**: Bump pypa/gh-action-pypi-publish from 1.12.2 to 1.12.3
  ([#291](https://github.com/Python-roborock/python-roborock/pull/291),
  [`be52b3d`](https://github.com/Python-roborock/python-roborock/commit/be52b3d48dc7edeb164a006db10b7efe91a18b71))

- **deps-dev**: Bump pre-commit from 3.8.0 to 4.0.1
  ([#287](https://github.com/Python-roborock/python-roborock/pull/287),
  [`f2f0c4c`](https://github.com/Python-roborock/python-roborock/commit/f2f0c4c8fa9f8fe85fd208daf28e5f7dfe02aba3))

- **deps-dev**: Bump pytest-asyncio from 0.25.1 to 0.25.2
  ([#275](https://github.com/Python-roborock/python-roborock/pull/275),
  [`b0611f0`](https://github.com/Python-roborock/python-roborock/commit/b0611f0eb72b0078c10a5c03ae8415d21cc19c03))

- **deps-dev**: Bump ruff from 0.8.6 to 0.9.1
  ([#277](https://github.com/Python-roborock/python-roborock/pull/277),
  [`eb8bbe3`](https://github.com/Python-roborock/python-roborock/commit/eb8bbe317b8d4f98e9c72151d6f9ca105e3c0db0))

### Refactoring

- Simplify future usage within the api clients
  ([#263](https://github.com/Python-roborock/python-roborock/pull/263),
  [`39a8661`](https://github.com/Python-roborock/python-roborock/commit/39a8661d4c5ade657cfc655a3ac78a66628bb755))


## v2.9.0 (2025-01-09)

### Chores

- Add example ([#269](https://github.com/Python-roborock/python-roborock/pull/269),
  [`d7a3af2`](https://github.com/Python-roborock/python-roborock/commit/d7a3af29c91bf2066f88a941789c0dc725eb7431))

- Add some testing and mocks for the web api
  ([#270](https://github.com/Python-roborock/python-roborock/pull/270),
  [`2356c16`](https://github.com/Python-roborock/python-roborock/commit/2356c16cd08cdf7210f605f9c890eb1c5631a792))

### Features

- Add dust collection mode name for typing ease
  ([#271](https://github.com/Python-roborock/python-roborock/pull/271),
  [`c85232a`](https://github.com/Python-roborock/python-roborock/commit/c85232a00b997dbc84a4b9b99b18ae1c714b7df7))

- Add product v4 and downloading code
  ([#267](https://github.com/Python-roborock/python-roborock/pull/267),
  [`b669117`](https://github.com/Python-roborock/python-roborock/commit/b6691174607a66959f4d9046dffb4cd4e782695d))

* feat: add product v4 and downloading code

* fix: remove got message

- Add support for qrevo curv ([#253](https://github.com/Python-roborock/python-roborock/pull/253),
  [`e42729a`](https://github.com/Python-roborock/python-roborock/commit/e42729aa5aedd2c77f68230825d6ce832a146f33))

* add support for qrevo curv

* add dock support

* revert unnecessary changes

* fix: lint

---------

Co-authored-by: Luke Lashley <conway220@gmail.com>


## v2.8.5 (2025-01-06)

### Bug Fixes

- Add additional log messages to track down concurrency errors
  ([#266](https://github.com/Python-roborock/python-roborock/pull/266),
  [`d750234`](https://github.com/Python-roborock/python-roborock/commit/d75023482e58689009c4df96cfc69b6080f5ada9))

- Update log message to include existing request id
  ([#264](https://github.com/Python-roborock/python-roborock/pull/264),
  [`ac8d23a`](https://github.com/Python-roborock/python-roborock/commit/ac8d23aa59342d9ae9f7c5d7c857de353e288ffa))

* fix: Update log message to include existing request id

* fix: Add protocol to log message

### Chores

- Always use time.monotonic ([#265](https://github.com/Python-roborock/python-roborock/pull/265),
  [`e14802c`](https://github.com/Python-roborock/python-roborock/commit/e14802cadde404d548cdff0c6b5906740a7e8c00))


## v2.8.4 (2024-12-20)

### Bug Fixes

- Update mop intensity, fan speed, and dock mappings for the QRevo Master
  ([#260](https://github.com/Python-roborock/python-roborock/pull/260),
  [`77f6d6f`](https://github.com/Python-roborock/python-roborock/commit/77f6d6fc917831f1966d2138bc7355292fa1e5e2))

* fix: update mop intensity, fan speed, and dock mappings for QRevo Master

* Fix sorting of imports

* Rerun precommit


## v2.8.3 (2024-12-19)

### Bug Fixes

- Add support for QRevo Master mop mode
  ([#259](https://github.com/Python-roborock/python-roborock/pull/259),
  [`db11c0f`](https://github.com/Python-roborock/python-roborock/commit/db11c0f8ca7c08d2f795f77f7a652db4bfaa91ae))


## v2.8.2 (2024-12-19)

### Bug Fixes

- Add a mop mode to QRevoMaster
  ([#258](https://github.com/Python-roborock/python-roborock/pull/258),
  [`bf0feb7`](https://github.com/Python-roborock/python-roborock/commit/bf0feb7ee8bc9933232e8235e6efa92a451ee19e))


## v2.8.1 (2024-12-18)

### Bug Fixes

- Add config github actions ([#247](https://github.com/Python-roborock/python-roborock/pull/247),
  [`35f888c`](https://github.com/Python-roborock/python-roborock/commit/35f888c653ad3d41ca40d27a5ea7041df47b6bbe))

* fix: add config github actions

* fix: remove placeholders

- Add gh_token to checkout ([#245](https://github.com/Python-roborock/python-roborock/pull/245),
  [`ab9fcfe`](https://github.com/Python-roborock/python-roborock/commit/ab9fcfe4526314b09c8fd382527c5b9d9b011315))

- Bad indentation ([#248](https://github.com/Python-roborock/python-roborock/pull/248),
  [`190f66e`](https://github.com/Python-roborock/python-roborock/commit/190f66e53fca6938b927fd587ebcdb249c908505))

- Bump semantic release ([#236](https://github.com/Python-roborock/python-roborock/pull/236),
  [`cf067d4`](https://github.com/Python-roborock/python-roborock/commit/cf067d4e4fa4680e766719dc22295afb2a526323))

* fix: bump semantic release

* fix: bump versioning and add environment

* fix: move if check

* fix: some other version bumps

- Change to deploy_key ([#254](https://github.com/Python-roborock/python-roborock/pull/254),
  [`de0a0c7`](https://github.com/Python-roborock/python-roborock/commit/de0a0c73f1f9b415f67412170a754d6685f0c969))

- Change to persist credentials
  ([#246](https://github.com/Python-roborock/python-roborock/pull/246),
  [`5b4b769`](https://github.com/Python-roborock/python-roborock/commit/5b4b7694743d96ca7acb57ed28271220791f9802))

- Container issue from api change and ci update
  ([#257](https://github.com/Python-roborock/python-roborock/pull/257),
  [`b1e645d`](https://github.com/Python-roborock/python-roborock/commit/b1e645d6acb8de776f5361e2a5a2be59c730237b))

- Give ci more permissions ([#240](https://github.com/Python-roborock/python-roborock/pull/240),
  [`641a40c`](https://github.com/Python-roborock/python-roborock/commit/641a40c12f38f3dcdca36aa61f17663440f0ba8e))

- Hopefully finalize semantic release
  ([#244](https://github.com/Python-roborock/python-roborock/pull/244),
  [`481f01d`](https://github.com/Python-roborock/python-roborock/commit/481f01dc039f27037e269a7234c97006dae91969))

- Move github token to env for semantic release
  ([#241](https://github.com/Python-roborock/python-roborock/pull/241),
  [`c61d8de`](https://github.com/Python-roborock/python-roborock/commit/c61d8de1bbf0705d0d7a2699822e6bfef49c3db4))

- Repair semantic release ([#251](https://github.com/Python-roborock/python-roborock/pull/251),
  [`431bc20`](https://github.com/Python-roborock/python-roborock/commit/431bc2033340267340f4740cef14ec0e4c5e7331))

- Semantic release versioning tag
  ([#237](https://github.com/Python-roborock/python-roborock/pull/237),
  [`fcc58ee`](https://github.com/Python-roborock/python-roborock/commit/fcc58ee6de75a61642e73c63cf614d8953318c29))

- Semantic release versioning tag
  ([#238](https://github.com/Python-roborock/python-roborock/pull/238),
  [`33a1e72`](https://github.com/Python-roborock/python-roborock/commit/33a1e72d97881aac867119eddca39c4366a549e3))

* fix: semantic release versioning tag

* fix: set version back

- Set python version in ci ([#239](https://github.com/Python-roborock/python-roborock/pull/239),
  [`dcad510`](https://github.com/Python-roborock/python-roborock/commit/dcad510ec232380f5bed7646c4455f656b7ca6ae))

- Specify x-access-token ([#249](https://github.com/Python-roborock/python-roborock/pull/249),
  [`e9f319b`](https://github.com/Python-roborock/python-roborock/commit/e9f319b0ee22cd90e9437d20f279a24228ee62c1))

- Update_gh_token ([#242](https://github.com/Python-roborock/python-roborock/pull/242),
  [`8a9866c`](https://github.com/Python-roborock/python-roborock/commit/8a9866cce2f6d868ab5f87b13a6b0151034d7a22))

- Update_gh_token ([#243](https://github.com/Python-roborock/python-roborock/pull/243),
  [`e100ab3`](https://github.com/Python-roborock/python-roborock/commit/e100ab3e8557ed97a5917cadb40968bbf7686b76))

### Chores

- Update README.md
  ([`5a982b7`](https://github.com/Python-roborock/python-roborock/commit/5a982b723528e67c6d8d664dd8b3eee64436a0c8))


## v2.8.0 (2024-11-12)

### Chores

- Call to super in docs ([#235](https://github.com/Python-roborock/python-roborock/pull/235),
  [`df331ea`](https://github.com/Python-roborock/python-roborock/commit/df331ea0165d05b093f170fb9107918aaaac03e6))

### Features

- Add some new roborock codes and add custom command
  ([#234](https://github.com/Python-roborock/python-roborock/pull/234),
  [`c8507ef`](https://github.com/Python-roborock/python-roborock/commit/c8507eff9cdc24654034fbe4fd63ac89b6de6f99))

* fix: add some new roborock codes and add custom command

* fix: lint


## v2.7.2 (2024-11-08)

### Bug Fixes

- Add some new roborock codes ([#233](https://github.com/Python-roborock/python-roborock/pull/233),
  [`59546dd`](https://github.com/Python-roborock/python-roborock/commit/59546dd68f7b40ad368d58fd502680ff9c03c81b))


## v2.7.1 (2024-10-28)

### Bug Fixes

- Check that clean area is not a str
  ([#230](https://github.com/Python-roborock/python-roborock/pull/230),
  [`e66a91e`](https://github.com/Python-roborock/python-roborock/commit/e66a91edaf6fedf5d4b2ab9117b7759295add492))

### Chores

- Add some async improvements ([#229](https://github.com/Python-roborock/python-roborock/pull/229),
  [`e987c17`](https://github.com/Python-roborock/python-roborock/commit/e987c17ee65982c7179f4d94a84e1863aa4830da))

* chore: add some async improvements

* chore: improve get_rand_int


## v2.7.0 (2024-10-28)

### Features

- Remove dacite ([#227](https://github.com/Python-roborock/python-roborock/pull/227),
  [`86878a7`](https://github.com/Python-roborock/python-roborock/commit/86878a71d82c2cc707daa16dec109fc07360e3f6))


## v2.6.1 (2024-10-22)

### Bug Fixes

- Add a warning for wrong type of clean area and add new dock
  ([#224](https://github.com/Python-roborock/python-roborock/pull/224),
  [`c334eb2`](https://github.com/Python-roborock/python-roborock/commit/c334eb2193091dccd23db0d3ee4863e838733e30))


## v2.6.0 (2024-06-29)

### Features

- Add q revo pro/p10 pro support
  ([#220](https://github.com/Python-roborock/python-roborock/pull/220),
  [`5e6a2d6`](https://github.com/Python-roborock/python-roborock/commit/5e6a2d6a7171da146efb3e59ddb3215c2a573507))


## v2.5.0 (2024-06-25)

### Features

- Add some typing ([#219](https://github.com/Python-roborock/python-roborock/pull/219),
  [`35d0900`](https://github.com/Python-roborock/python-roborock/commit/35d09000b8d144cbaf935069952ea135950d0e78))


## v2.4.0 (2024-06-25)

### Features

- Add some missing codes and make warnings only message once
  ([#218](https://github.com/Python-roborock/python-roborock/pull/218),
  [`12361b5`](https://github.com/Python-roborock/python-roborock/commit/12361b58e7a4d368281c4ffd9ac3d8e9d8155e62))


## v2.3.0 (2024-06-07)

### Features

- Add warning in web requests if it fails to decode
  ([#215](https://github.com/Python-roborock/python-roborock/pull/215),
  [`6ae69e9`](https://github.com/Python-roborock/python-roborock/commit/6ae69e9bcba6a98736f2f480114922186f6ca458))


## v2.2.3 (2024-06-04)

### Bug Fixes

- S8 maxv has a wash and fill dock
  ([#213](https://github.com/Python-roborock/python-roborock/pull/213),
  [`018fd05`](https://github.com/Python-roborock/python-roborock/commit/018fd052360dffd238919e336943809720457c4e))

### Chores

- Add load multi map parameter to docs(#209)
  ([`2cee5d7`](https://github.com/Python-roborock/python-roborock/commit/2cee5d7e065473232caacf1531c38e83506f0c5b))

- Update documentation for reset_consumable
  ([#207](https://github.com/Python-roborock/python-roborock/pull/207),
  [`4071538`](https://github.com/Python-roborock/python-roborock/commit/40715387f5eac6788d198ffefad0c1d25b7c7138))

Document parameter for API function reset_consumable


## v2.2.2 (2024-05-16)

### Bug Fixes

- Handle weird clean record response
  ([#206](https://github.com/Python-roborock/python-roborock/pull/206),
  [`07ce71a`](https://github.com/Python-roborock/python-roborock/commit/07ce71a2cd8085136952bd7639f6f4a2e273faf9))


## v2.2.1 (2024-05-11)

### Bug Fixes

- Add missing value "high = 203" to RoborockMopIntensityS8MaxVUltra
  ([#205](https://github.com/Python-roborock/python-roborock/pull/205),
  [`886b0e6`](https://github.com/Python-roborock/python-roborock/commit/886b0e6a8a4b98ff74964d59f4c8c0fbbf569688))


## v2.2.0 (2024-05-09)

### Features

- Improve some typing ([#204](https://github.com/Python-roborock/python-roborock/pull/204),
  [`7752db9`](https://github.com/Python-roborock/python-roborock/commit/7752db9066fa49bb93a6268a491e2a0baa608cfc))


## v2.1.1 (2024-05-08)

### Bug Fixes

- Set roommapping when it is only one room
  ([#203](https://github.com/Python-roborock/python-roborock/pull/203),
  [`26af66b`](https://github.com/Python-roborock/python-roborock/commit/26af66bd5d8dbfa4c94a9add317ccc9ca9161510))

* fix: set roommapping when it is only one room

* fix: add len check


## v2.1.0 (2024-05-08)

### Features

- Add s8_maxv_ultra info ([#202](https://github.com/Python-roborock/python-roborock/pull/202),
  [`aaaf0f0`](https://github.com/Python-roborock/python-roborock/commit/aaaf0f0c381924524a079f600de14db1cd61ed45))


## v2.0.0 (2024-04-11)

### Features

- Add zeo support and fix some a01 weirdness
  ([#200](https://github.com/Python-roborock/python-roborock/pull/200),
  [`e825ff5`](https://github.com/Python-roborock/python-roborock/commit/e825ff5811516b4034e9b41769e5912c99cf0166))

* major: add A01

* chore: add init

* chore: fix commitlint?

* chore: fix commitlint

* chore: change refactor to be major tag

* refactor: add A01

* feat: add a01

BREAKING CHANGE: You must now specify what version api you want to use with clients.

* feat: add initial zeo support

* fix: fix A01 support

* fix: allow messages to fail

* fix: lint

* feat: add more zeo things

### Breaking Changes

- You must now specify what version api you want to use with clients.


## v1.0.0 (2024-04-09)

### Chores

- Move more things around in version 1 api
  ([#198](https://github.com/Python-roborock/python-roborock/pull/198),
  [`30d2577`](https://github.com/Python-roborock/python-roborock/commit/30d257756f35b9fc71d64d0479b872661b9176a6))

* chore: move more things around in version 1 api

* fix: tests

### Refactoring

- Add A01 ([#199](https://github.com/Python-roborock/python-roborock/pull/199),
  [`16b9e3e`](https://github.com/Python-roborock/python-roborock/commit/16b9e3e8261db3ec38d6bc24661ecf40c6bb0870))

* major: add A01

* chore: add init

* chore: fix commitlint?

* chore: fix commitlint

* chore: change refactor to be major tag

* refactor: add A01

* feat: add a01

BREAKING CHANGE: You must now specify what version api you want to use with clients.

### Breaking Changes

- You must now specify what version api you want to use with clients.


## v0.41.0 (2024-03-06)

### Features

- Add v1 api ([#194](https://github.com/Python-roborock/python-roborock/pull/194),
  [`9fb124e`](https://github.com/Python-roborock/python-roborock/commit/9fb124ecdd0a979ff8f2c742eb4dd625b7e9292f))

* feat: add v1 api

* fix: change some imports

* fix: bug and versioning

* chore: move location of v1

* fix: random exception


## v0.40.0 (2024-03-03)

### Features

- Add nonce to diagnostic data ([#195](https://github.com/Python-roborock/python-roborock/pull/195),
  [`ceafcb6`](https://github.com/Python-roborock/python-roborock/commit/ceafcb6e30c60f6f6ad3833ab73861c18413b806))


## v0.39.2 (2024-02-26)

### Bug Fixes

- Bump construct and add wm category
  ([#192](https://github.com/Python-roborock/python-roborock/pull/192),
  [`2f18b35`](https://github.com/Python-roborock/python-roborock/commit/2f18b35755776844e266c893b126a830622afd43))


## v0.39.1 (2024-01-24)

### Bug Fixes

- Remove problematic code ([#189](https://github.com/Python-roborock/python-roborock/pull/189),
  [`a9e12ca`](https://github.com/Python-roborock/python-roborock/commit/a9e12ca122b467d74e9cd29dc031802cf0f551bc))


## v0.39.0 (2024-01-03)

### Chores

- Added code from decompiled react and refactoring web api
  ([#176](https://github.com/Python-roborock/python-roborock/pull/176),
  [`dab105c`](https://github.com/Python-roborock/python-roborock/commit/dab105c58d11f7789b5f11dd962dd916d5436ced))

* chore: added code from decompiled react and refactoring web api

* fix: patches

* fix: patch

* chore: add info from new_feature_info

- Update api_commands.rst app_goto_target
  ([#163](https://github.com/Python-roborock/python-roborock/pull/163),
  [`9c83c77`](https://github.com/Python-roborock/python-roborock/commit/9c83c77c732943b2cb9481442afddc3b1ba241c3))

### Features

- Add async_release ([#179](https://github.com/Python-roborock/python-roborock/pull/179),
  [`ae58627`](https://github.com/Python-roborock/python-roborock/commit/ae58627bda324c29090b7c4ab78776288a30a64d))


## v0.38.0 (2023-12-11)

### Features

- Add information from product api
  ([#158](https://github.com/Python-roborock/python-roborock/pull/158),
  [`22720ae`](https://github.com/Python-roborock/python-roborock/commit/22720aee79e582328ae642e61d57dc2e3a92ec1c))

* fix: add information from product api

* feat: add dyad protocol


## v0.37.0 (2023-12-10)

### Features

- House keeping, version bumping, doc fixes, doc improvements, v2 home data api
  ([#157](https://github.com/Python-roborock/python-roborock/pull/157),
  [`f3ca9b4`](https://github.com/Python-roborock/python-roborock/commit/f3ca9b45d3de3a15c57e134421d3abc11095bc22))

* feat: version bumping, docs improvements, mypy fixes, doc fixes

* fix: ci steps

* feat: convert to v2 of the api

* chore: linting, include docs, poetry lock

* fix: tests

* fix: add ability to remove listener


## v0.36.2 (2023-11-22)

### Bug Fixes

- Typing and error checking ([#149](https://github.com/Python-roborock/python-roborock/pull/149),
  [`d94aa48`](https://github.com/Python-roborock/python-roborock/commit/d94aa48c1e594f7f6cd1cff16da66169368fb86c))

* fix: typing and error checking

* chore: lint

* fix: merge weirdness


## v0.36.1 (2023-11-08)

### Bug Fixes

- Typing for map ([#141](https://github.com/Python-roborock/python-roborock/pull/141),
  [`64121ee`](https://github.com/Python-roborock/python-roborock/commit/64121eee14e4f0ca24db664b0664aaac5c7332af))


## v0.36.0 (2023-11-07)

### Features

- Update listeners ([#140](https://github.com/Python-roborock/python-roborock/pull/140),
  [`5498596`](https://github.com/Python-roborock/python-roborock/commit/549859669941e71c8d7ee09a0d4eea9564b4a12f))

* fix: change some typing

* fix: include poetry lock

* fix: linting

* fix: add typing

* fix: bugs

* fix: none typing

* fix: weird merge things

* fix: rework listeners and cache a bit more

* chore: linting

* chore: typo

* chore: self listener model

* fix: override missing for data protocol


## v0.35.4 (2023-11-03)

### Bug Fixes

- Mypy complaints ([#137](https://github.com/Python-roborock/python-roborock/pull/137),
  [`752e320`](https://github.com/Python-roborock/python-roborock/commit/752e320644449a83a724590628c4011b9d8bacb2))

* fix: change some typing

* fix: include poetry lock

* fix: linting

* fix: add typing

* fix: bugs

* fix: none typing

* Update api.py


## v0.35.3 (2023-10-29)

### Bug Fixes

- Typing and versioning ([#134](https://github.com/Python-roborock/python-roborock/pull/134),
  [`e1dc545`](https://github.com/Python-roborock/python-roborock/commit/e1dc545f20f2a163240eb72d831025cb2ff3ec7c))

* fix: change some typing

* fix: include poetry lock

* fix: linting

### Chores

- **deps**: Bump snok/install-poetry from 1.3.3 to 1.3.4
  ([#106](https://github.com/Python-roborock/python-roborock/pull/106),
  [`1fc0265`](https://github.com/Python-roborock/python-roborock/commit/1fc02658e9d5934c5b5a2e173d7bcba8d8c55c2f))

Bumps [snok/install-poetry](https://github.com/snok/install-poetry) from 1.3.3 to 1.3.4. - [Release
  notes](https://github.com/snok/install-poetry/releases) -
  [Commits](https://github.com/snok/install-poetry/compare/v1.3.3...v1.3.4)

--- updated-dependencies: - dependency-name: snok/install-poetry dependency-type: direct:production

update-type: version-update:semver-patch ...

Signed-off-by: dependabot[bot] <support@github.com>

Co-authored-by: dependabot[bot] <49699333+dependabot[bot]@users.noreply.github.com>


## v0.35.2 (2023-10-29)

### Bug Fixes

- Error catch and typing ([#133](https://github.com/Python-roborock/python-roborock/pull/133),
  [`171c302`](https://github.com/Python-roborock/python-roborock/commit/171c30265664b0161db75695d2d30d8b45bbf5b3))

### Chores

- Add some initial documentation ([#94](https://github.com/Python-roborock/python-roborock/pull/94),
  [`316fc0d`](https://github.com/Python-roborock/python-roborock/commit/316fc0d95f83948da25df0515622913173117ee0))


## v0.35.1 (2023-10-28)

### Bug Fixes

- Add s5 max mop code 207 ([#132](https://github.com/Python-roborock/python-roborock/pull/132),
  [`adc7ae0`](https://github.com/Python-roborock/python-roborock/commit/adc7ae0bbb75eb5be452efb62ca93de6a5211eef))


## v0.35.0 (2023-10-18)

### Features

- **code_mappings**: Add error n53 cleaning tank full or blocked
  ([#130](https://github.com/Python-roborock/python-roborock/pull/130),
  [`ebd57a0`](https://github.com/Python-roborock/python-roborock/commit/ebd57a0b559c0dee605e30eaead58b8433347a84))

Co-authored-by: jalcaras <jalcaras@free-mobile.fr>


## v0.34.6 (2023-10-02)

### Bug Fixes

- Add missing 207 code ([#127](https://github.com/Python-roborock/python-roborock/pull/127),
  [`87431a1`](https://github.com/Python-roborock/python-roborock/commit/87431a1f155059a51b1b3e2c8867fe18cc476e16))


## v0.34.5 (2023-09-29)

### Bug Fixes

- Remove alexapy ([#126](https://github.com/Python-roborock/python-roborock/pull/126),
  [`38ff4eb`](https://github.com/Python-roborock/python-roborock/commit/38ff4eb90a1805ad599f61322d7c3547f465868b))


## v0.34.4 (2023-09-28)

### Bug Fixes

- Parsing potential list of clean record
  ([#125](https://github.com/Python-roborock/python-roborock/pull/125),
  [`df7a920`](https://github.com/Python-roborock/python-roborock/commit/df7a920a94a632d9653637e0111b3a955db49356))


## v0.34.3 (2023-09-24)

### Bug Fixes

- Add custom code for p10 ([#123](https://github.com/Python-roborock/python-roborock/pull/123),
  [`8b57d50`](https://github.com/Python-roborock/python-roborock/commit/8b57d50b0c898ca7d3df7cbdfe3682fd03cf649e))


## v0.34.2 (2023-09-21)

### Bug Fixes

- Make cache not global ([#122](https://github.com/Python-roborock/python-roborock/pull/122),
  [`e119201`](https://github.com/Python-roborock/python-roborock/commit/e119201f1c700d98e3322653440097c91ef4e14c))

* feat: add datetime parsing in cleanrecord

* chore: lint

* fix: timezone for non-3.11

* feat: add is_available for ha and here in future

* fix: add timeout as a variable and set a longer default timeout for cloud

* fix: is_available true by default

* fix: status type as class variable

* fix: don't update status when it was none before listener

* fix: reduce info logs

* fix: don't cache device cache

* fix: double keepalive

* fix: don't continue calling unsupported functions

* fix: revert keepalive for now


## v0.34.1 (2023-09-19)

### Bug Fixes

- Status reworking ([#121](https://github.com/Python-roborock/python-roborock/pull/121),
  [`8f4b7d3`](https://github.com/Python-roborock/python-roborock/commit/8f4b7d376d5a475798782496ea52ac9674cb9ae7))

* fix: is_available true by default

* fix: status type as class variable

* fix: don't update status when it was none before listener

* fix: reduce info logs


## v0.34.0 (2023-09-12)

### Chores

- Add pyupgrade to ruff ([#118](https://github.com/Python-roborock/python-roborock/pull/118),
  [`360b240`](https://github.com/Python-roborock/python-roborock/commit/360b240ab89862f8003ece11833e50846b279259))

* chore: add pyupgrade to ruff

* chore: make ruff and isort play nice

### Features

- Add datetime parsing in cleanrecord
  ([#119](https://github.com/Python-roborock/python-roborock/pull/119),
  [`5e67fa6`](https://github.com/Python-roborock/python-roborock/commit/5e67fa648478e573239c2f1dfc4b58c01cae1797))

* feat: add datetime parsing in cleanrecord

* fix: timezone for non-3.11

* feat: add is_available for ha and here in future

* fix: add timeout as a variable and set a longer default timeout for cloud


## v0.33.2 (2023-09-06)

### Bug Fixes

- Add missing s5 codes ([#116](https://github.com/Python-roborock/python-roborock/pull/116),
  [`4d56021`](https://github.com/Python-roborock/python-roborock/commit/4d560216354fab4ab8b1d452dd6b29008b20d50a))

* fix: add missing codes for s5 max

* chore: lint


## v0.33.1 (2023-09-06)

### Bug Fixes

- Unknow values on HA component
  ([#117](https://github.com/Python-roborock/python-roborock/pull/117),
  [`1323618`](https://github.com/Python-roborock/python-roborock/commit/1323618c6c58bb6dcef5c7f5f2ca12e32969ba0f))

* feat add Q REVO support (RoborockFanSpeedP10 + RoborockMopModeP10)

* feat add Q REVO support (model ROBOROCK_P10/roborock.vacuum.a75)

* feat add Q REVO support (P10Status)

* feat add Q REVO support (status data)

* fix(P10Status): Change RoborockMopModeP10 by RoborockMopModeS8ProUltra

* fix(RoborockMopModeP10): Remove

* fix: change ordering of imports

* fix: change q_revo->p10 to be consistent with entire code

* fix: for HA component(items: dock_mop_wash_mode_interval, dock_washing_mode) stuck at "unknow"
  value when using P10

---------

Co-authored-by: jalcaras <jalcaras@free-mobile.Fr>

Co-authored-by: jalcaras <jalcaras@reseau.free.fr>

Co-authored-by: Luke <conway220@gmail.com>


## v0.33.0 (2023-09-04)

### Features

- Add q revo/p10 support ([#114](https://github.com/Python-roborock/python-roborock/pull/114),
  [`b2237d9`](https://github.com/Python-roborock/python-roborock/commit/b2237d97384d819cbcc62902bbcbb2c7dbe0072e))

* feat add Q REVO support (RoborockFanSpeedP10 + RoborockMopModeP10)

* feat add Q REVO support (model ROBOROCK_P10/roborock.vacuum.a75)

* feat add Q REVO support (P10Status)

* feat add Q REVO support (status data)

* fix(P10Status): Change RoborockMopModeP10 by RoborockMopModeS8ProUltra

* fix(RoborockMopModeP10): Remove

* fix: change ordering of imports

---------

Co-authored-by: jalcaras <jalcaras@free-mobile.Fr>

Co-authored-by: jalcaras <jalcaras@reseau.free.fr>

Co-authored-by: Luke <conway220@gmail.com>


## v0.32.4 (2023-08-30)

### Bug Fixes

- Refactor cache and call get_status after changing mop mode
  ([#105](https://github.com/Python-roborock/python-roborock/pull/105),
  [`8bf70f4`](https://github.com/Python-roborock/python-roborock/commit/8bf70f4f8b3cabe846bffdc3dd3300f9f621ae97))

### Chores

- **deps**: Bump wagoid/commitlint-github-action from 5.4.1 to 5.4.3
  ([#96](https://github.com/Python-roborock/python-roborock/pull/96),
  [`2da7b38`](https://github.com/Python-roborock/python-roborock/commit/2da7b3865bb1693b7ce655bf0d44090753aa5a52))


## v0.32.3 (2023-08-05)

### Bug Fixes

- Resolve unawaited task errors on connect/disconnect
  ([#103](https://github.com/Python-roborock/python-roborock/pull/103),
  [`1ad03be`](https://github.com/Python-roborock/python-roborock/commit/1ad03befa84f9b729a0cc7553b794fe5344a22ce))

* fix: resolve unawaited task errors on connect/disconnect

* chore: make lint happy


## v0.32.2 (2023-08-04)

### Bug Fixes

- Waiting queue
  ([`ff5376b`](https://github.com/Python-roborock/python-roborock/commit/ff5376be3a4ff4eb90e33118db89214ef699dc6f))


## v0.32.1 (2023-08-04)

### Bug Fixes

- Remove coroutine warning
  ([`da83078`](https://github.com/Python-roborock/python-roborock/commit/da83078f7ef8f333fa46b75603ce8a88bb97914d))


## v0.32.0 (2023-08-03)

### Chores

- Lint
  ([`d158dcc`](https://github.com/Python-roborock/python-roborock/commit/d158dcc2c44d2d529e762d95815dc854b5ed674e))

### Features

- Adding device_id to listeners and fixing race condition on connection, disconnection and messages
  ([`2bee8a1`](https://github.com/Python-roborock/python-roborock/commit/2bee8a11ad30cd4a3c186a4c0a619838adc83a53))


## v0.31.1 (2023-08-02)

### Bug Fixes

- Add error code for invalid credentials
  ([#101](https://github.com/Python-roborock/python-roborock/pull/101),
  [`703f48b`](https://github.com/Python-roborock/python-roborock/commit/703f48b66cfd32d20e74eaa959a66cd736ca38c8))


## v0.31.0 (2023-07-31)

### Features

- Add device name to logs ([#100](https://github.com/Python-roborock/python-roborock/pull/100),
  [`7690d56`](https://github.com/Python-roborock/python-roborock/commit/7690d5644181abb5fb7681d6c1764e2f8750c4b5))


## v0.30.3 (2023-07-31)

### Bug Fixes

- Adding no dustbin to docker errors
  ([`0e28628`](https://github.com/Python-roborock/python-roborock/commit/0e286280edda21a3b95c656d5bc358cd4229d075))


## v0.30.2 (2023-07-21)

### Bug Fixes

- Possible solution for future invalid state
  ([`8ac4e72`](https://github.com/Python-roborock/python-roborock/commit/8ac4e72372f26105423213bb85d4c33d7951af4d))


## v0.30.1 (2023-07-18)

### Bug Fixes

- Add missing s8 pro mop code and q revo dock
  ([#92](https://github.com/Python-roborock/python-roborock/pull/92),
  [`5d75c3b`](https://github.com/Python-roborock/python-roborock/commit/5d75c3b794db231e07f8b6693f2a96b132f737ce))

### Chores

- **deps**: Bump relekang/python-semantic-release from 7.34.6 to 8.0.0
  ([#89](https://github.com/Python-roborock/python-roborock/pull/89),
  [`9677018`](https://github.com/Python-roborock/python-roborock/commit/96770184e953598e6232dbed4e6d39466f7d7465))


## v0.30.0 (2023-07-10)

### Bug Fixes

- Add missing dock for s7 max ultra
  ([#88](https://github.com/Python-roborock/python-roborock/pull/88),
  [`10aff22`](https://github.com/Python-roborock/python-roborock/commit/10aff22bc1e6d17b1b6c2587ebefcfd1d9fb7be7))

- Listeners getting protocol data before it exists.
  ([#87](https://github.com/Python-roborock/python-roborock/pull/87),
  [`3d68ea4`](https://github.com/Python-roborock/python-roborock/commit/3d68ea4326da827f17a32b2b5645f1e1e43f3eca))

* fix: listeners getting protocol data before it exists

* fix: optimize code

### Features

- Created strong foundation for docs
  ([#86](https://github.com/Python-roborock/python-roborock/pull/86),
  [`ef88edd`](https://github.com/Python-roborock/python-roborock/commit/ef88eddb8b582f5ad958d8135964e39ba6a05c91))


## v0.29.2 (2023-06-28)

### Bug Fixes

- Downgrade construct ([#84](https://github.com/Python-roborock/python-roborock/pull/84),
  [`920f59f`](https://github.com/Python-roborock/python-roborock/commit/920f59f1fad2790084ee001225bbaff2e21b3f91))


## v0.29.1 (2023-06-27)

### Bug Fixes

- Adding scene commands
  ([`fddbe50`](https://github.com/Python-roborock/python-roborock/commit/fddbe508f177dc6bc336223007018f501709c995))


## v0.29.0 (2023-06-26)

### Features

- Adding server timer and retry command compatibility
  ([`1a1565b`](https://github.com/Python-roborock/python-roborock/commit/1a1565b1f2eb57fa373c9298dd2501a13914bb0a))


## v0.28.0 (2023-06-26)

### Features

- Adding status and consumable listeners
  ([#83](https://github.com/Python-roborock/python-roborock/pull/83),
  [`ebdbc90`](https://github.com/Python-roborock/python-roborock/commit/ebdbc907f1f1a2a91ad10953ca6e70b91b9664dd))

* feat: adding status and consumable listeners

* fix: api tests

* chore: linting


## v0.27.2 (2023-06-22)

### Bug Fixes

- Cache concurrency
  ([`7dd3aa4`](https://github.com/Python-roborock/python-roborock/commit/7dd3aa4933248ede6230a82e6d14e30e8009e27c))


## v0.27.1 (2023-06-22)

### Bug Fixes

- Improving cache and refactoring
  ([`e88854d`](https://github.com/Python-roborock/python-roborock/commit/e88854d3c6c9109e9fbb4e8ecd3d0ee4ad5d53ff))


## v0.27.0 (2023-06-22)

### Features

- Improving cache and refactoring
  ([#82](https://github.com/Python-roborock/python-roborock/pull/82),
  [`e6d48af`](https://github.com/Python-roborock/python-roborock/commit/e6d48af4e1c83fe79104d368918613ac0b332cbb))


## v0.26.2 (2023-06-21)

### Bug Fixes

- #81 - cli raising exception for diagnostic data
  ([`690b316`](https://github.com/Python-roborock/python-roborock/commit/690b316de35c970454a45418682c82d752b81201))


## v0.26.1 (2023-06-20)

### Bug Fixes

- Changelog ([#80](https://github.com/Python-roborock/python-roborock/pull/80),
  [`5c4928b`](https://github.com/Python-roborock/python-roborock/commit/5c4928b2d414b9decc1a454348e38d29aeb505fa))


## v0.26.0 (2023-06-20)

### Chores

- Update pyproject ([#79](https://github.com/Python-roborock/python-roborock/pull/79),
  [`cad97da`](https://github.com/Python-roborock/python-roborock/commit/cad97da7924288524993b32f2d2cd7d71abccee6))

- **deps**: Bump relekang/python-semantic-release from 7.34.4 to 7.34.6
  ([#78](https://github.com/Python-roborock/python-roborock/pull/78),
  [`cebc9d2`](https://github.com/Python-roborock/python-roborock/commit/cebc9d28aa5222e78670bab5e19e162774a9a73f))

### Features

- Adding command cache ([#77](https://github.com/Python-roborock/python-roborock/pull/77),
  [`505f5e4`](https://github.com/Python-roborock/python-roborock/commit/505f5e45a56e98c248a38236ae3f02908583de12))

* feat: adding command cache

* chore: typo

* fix: dependencies

* feat: adding cache evict time


## v0.25.2 (2023-06-17)

### Bug Fixes

- Downgrading construct version
  ([`d5148ce`](https://github.com/Python-roborock/python-roborock/commit/d5148ce8fc553f73819a9f03c7688d53100bdcd9))

- Moving back to python 3.10 due to python-semantic-release incompatibility
  ([`8ab9352`](https://github.com/Python-roborock/python-roborock/commit/8ab9352adb2cb82c24057bef3107b28d3a157087))

- Removing python 10 tests
  ([`46e258b`](https://github.com/Python-roborock/python-roborock/commit/46e258bc495123c8e8325a731e353f3bc5ce3e0c))


## v0.25.1 (2023-06-16)

### Bug Fixes

- Python-semantic-release python version
  ([`845da45`](https://github.com/Python-roborock/python-roborock/commit/845da456a0d59765d08962fee007b63c8d0c50eb))


## v0.25.0 (2023-06-16)

### Bug Fixes

- Remove dnd timer and valley electricity from props
  ([#75](https://github.com/Python-roborock/python-roborock/pull/75),
  [`2035af5`](https://github.com/Python-roborock/python-roborock/commit/2035af5d524605fcbd0b87e20f256c1c61ca9c68))

* fix: remove dnd timer and valley electricity from props

* fix: linting

* fix: clear out old keep alive before adding new one

* chore: remove keep_alive_task

* fix: add storing of dnd and valley in api

- Remove python 10 from tests
  ([`31fc34c`](https://github.com/Python-roborock/python-roborock/commit/31fc34c22ad9e5f06b588e6b283412902bd2959d))

- Semantic release ([#76](https://github.com/Python-roborock/python-roborock/pull/76),
  [`224a566`](https://github.com/Python-roborock/python-roborock/commit/224a5662d2dbdf47d5141554733a9b4aeaf8d4f2))

* fix: remove dnd timer and valley electricity from props

* fix: linting

* fix: clear out old keep alive before adding new one

* chore: remove keep_alive_task

* fix: add storing of dnd and valley in api

* 0.24.2

Automatically generated by python-semantic-release

* fix: add dirty tank latch error

### Chores

- Add dependabot ([#70](https://github.com/Python-roborock/python-roborock/pull/70),
  [`cff6871`](https://github.com/Python-roborock/python-roborock/commit/cff6871012370bc8c1aaeefbea32f08c3a8d21f6))

* add dependabot

* chore: update dependabot ignore

- Manually releasing 0.24.1
  ([`0ab69b3`](https://github.com/Python-roborock/python-roborock/commit/0ab69b3cdfb1697fdd7edb9a644f296f1dfa10a2))

- Updating ci.yml
  ([`d4c2714`](https://github.com/Python-roborock/python-roborock/commit/d4c2714a5800c38333d292f1bef0c17a38326e40))

- **deps**: Bump wagoid/commitlint-github-action from 5.3.0 to 5.4.1
  ([#71](https://github.com/Python-roborock/python-roborock/pull/71),
  [`951dd5c`](https://github.com/Python-roborock/python-roborock/commit/951dd5c13030e0bc15256d414ed8e11235ff192b))

Bumps [wagoid/commitlint-github-action](https://github.com/wagoid/commitlint-github-action) from
  5.3.0 to 5.4.1. -
  [Changelog](https://github.com/wagoid/commitlint-github-action/blob/master/CHANGELOG.md) -
  [Commits](https://github.com/wagoid/commitlint-github-action/compare/v5.3.0...v5.4.1)

--- updated-dependencies: - dependency-name: wagoid/commitlint-github-action dependency-type:
  direct:production

update-type: version-update:semver-minor ...

Signed-off-by: dependabot[bot] <support@github.com>

Co-authored-by: dependabot[bot] <49699333+dependabot[bot]@users.noreply.github.com>

- **deps**: Update pycryptodome requirement
  ([#73](https://github.com/Python-roborock/python-roborock/pull/73),
  [`52dd451`](https://github.com/Python-roborock/python-roborock/commit/52dd451b57e7d292c6f8f01f1777f7a5cb88918b))

Updates the requirements on [pycryptodome](https://github.com/Legrandin/pycryptodome) to permit the
  latest version. - [Release notes](https://github.com/Legrandin/pycryptodome/releases) -
  [Changelog](https://github.com/Legrandin/pycryptodome/blob/master/Changelog.rst) -
  [Commits](https://github.com/Legrandin/pycryptodome/compare/v3.17.0...v3.18.0)

--- updated-dependencies: - dependency-name: pycryptodome dependency-type: direct:production ...

Signed-off-by: dependabot[bot] <support@github.com>

Co-authored-by: dependabot[bot] <49699333+dependabot[bot]@users.noreply.github.com>

### Features

- Bump python version
  ([`aae48b1`](https://github.com/Python-roborock/python-roborock/commit/aae48b1395698136ca90b7fe7386a1b6ea8aaa9c))


## v0.24.1 (2023-06-14)

### Bug Fixes

- Device_prop update
  ([`b6d1ccc`](https://github.com/Python-roborock/python-roborock/commit/b6d1ccc913cff1a7e25745867435146e9f748df7))

- Python-semantic-release
  ([`80e9c24`](https://github.com/Python-roborock/python-roborock/commit/80e9c24a39f3147b0fbc0a5437631777ab52b027))

### Chores

- Manually releasing 0.24.0
  ([`0a08c97`](https://github.com/Python-roborock/python-roborock/commit/0a08c972dae32a8d5670fd049b8220a4af1d3307))


## v0.24.0 (2023-06-14)

### Features

- Adding valley_electricity_timer to props
  ([`0844067`](https://github.com/Python-roborock/python-roborock/commit/08440670a7fb098f5f3954e2ad09f9a32e64a54e))


## v0.23.6 (2023-06-08)

### Bug Fixes

- Add datetime_time back ([#68](https://github.com/Python-roborock/python-roborock/pull/68),
  [`a3461dd`](https://github.com/Python-roborock/python-roborock/commit/a3461dd0a08702add2625df8616ba20d239805ce))

### Chores

- Linting
  ([`90f905d`](https://github.com/Python-roborock/python-roborock/commit/90f905d331125c8536ab1db29444685fcf8bf196))


## v0.23.5 (2023-06-08)

### Bug Fixes

- Issue building roborock message
  ([`89e1f28`](https://github.com/Python-roborock/python-roborock/commit/89e1f28461baaf03029679aed5f91200bb7dac4e))


## v0.23.4 (2023-06-06)

### Bug Fixes

- Adding method parse_datetime_to_roborock_datetime
  ([`64c8159`](https://github.com/Python-roborock/python-roborock/commit/64c8159a9695374a4b0599a317418949bdd8f3fe))

### Chores

- Fix mypy
  ([`c0e7997`](https://github.com/Python-roborock/python-roborock/commit/c0e7997c61f9878436ae65aa8530b1c08b503ed9))


## v0.23.3 (2023-06-05)

### Bug Fixes

- Parse_time_to_datetime method
  ([`d0fc149`](https://github.com/Python-roborock/python-roborock/commit/d0fc1498e20217d28703455937f760ba45053c61))


## v0.23.2 (2023-06-05)

### Bug Fixes

- Parse_time_to_datetime method
  ([`bcbc211`](https://github.com/Python-roborock/python-roborock/commit/bcbc2117dd306c21495c1f3364aa3205b3c5cfce))


## v0.23.1 (2023-06-05)

### Bug Fixes

- Parse_time_to_datetime method
  ([`1c39216`](https://github.com/Python-roborock/python-roborock/commit/1c39216c0ee6a29d350d08adc5d662d8669f85cf))


## v0.23.0 (2023-06-05)

### Bug Fixes

- Merging timer entities
  ([`22ff7f4`](https://github.com/Python-roborock/python-roborock/commit/22ff7f451166bcfda360552e92d661d0520886ae))

### Chores

- Linting
  ([`9e2a3c5`](https://github.com/Python-roborock/python-roborock/commit/9e2a3c5f2908c3e69e14bda239112cc6d8bbca15))

### Features

- Add diagnostic data and extra containers
  ([#67](https://github.com/Python-roborock/python-roborock/pull/67),
  [`59ef6f4`](https://github.com/Python-roborock/python-roborock/commit/59ef6f4d5366859ba5d02ba66ec1aa2288564179))

* feat: add diagnostic data and extra containers

* fix: lint

* fix: dock summary as roborockbase

* fix: make deviceprop RoborockBase

* merge in changes


## v0.22.0 (2023-06-05)

### Features

- Adding type cast for send_command
  ([`4a0b709`](https://github.com/Python-roborock/python-roborock/commit/4a0b70997080012e3059150da2b12fb47f6ef43a))


## v0.21.1 (2023-06-05)

### Bug Fixes

- Cli json serializing ([#66](https://github.com/Python-roborock/python-roborock/pull/66),
  [`ab13b53`](https://github.com/Python-roborock/python-roborock/commit/ab13b53a15822067112edda285c6feddf389a8b8))


## v0.21.0 (2023-06-04)

### Features

- Add time datetime for valley ([#65](https://github.com/Python-roborock/python-roborock/pull/65),
  [`c965862`](https://github.com/Python-roborock/python-roborock/commit/c965862f5b8b1f4dfbc83738cdebc1e11122c387))


## v0.20.2 (2023-06-02)

### Bug Fixes

- S6maxvstatus and minor changes
  ([`01f84ae`](https://github.com/Python-roborock/python-roborock/commit/01f84ae741dd3c9fa3bc5932b718abebcc8e3f0f))


## v0.20.1 (2023-06-01)

### Bug Fixes

- S8 model name and adding api methods get_child_lock_status and get_sound_volume
  ([`a3b7cee`](https://github.com/Python-roborock/python-roborock/commit/a3b7cee63a70746ac3db5e5cee37c5b507b99478))


## v0.20.0 (2023-05-31)

### Features

- Adds code for duct blockage ([#64](https://github.com/Python-roborock/python-roborock/pull/64),
  [`84dd5fb`](https://github.com/Python-roborock/python-roborock/commit/84dd5fbdefebe4b33c6bae6879137847522b1bfb))


## v0.19.0 (2023-05-31)

### Features

- Moving clean area to api ([#63](https://github.com/Python-roborock/python-roborock/pull/63),
  [`7ade218`](https://github.com/Python-roborock/python-roborock/commit/7ade218e3efd44159c6ad40cd88933385bbd1496))


## v0.18.10 (2023-05-30)

### Bug Fixes

- Dict with enum instead of value
  ([`9653c50`](https://github.com/Python-roborock/python-roborock/commit/9653c50f31b03ce2d3d21e2042d5c194924f4aca))


## v0.18.9 (2023-05-28)

### Bug Fixes

- Mqtt reconnections
  ([`462d4e4`](https://github.com/Python-roborock/python-roborock/commit/462d4e4a30372c143c9198c7008808ca11800af5))

### Chores

- Linting
  ([`f850cd1`](https://github.com/Python-roborock/python-roborock/commit/f850cd1f7d10b774516e76f3dac1ba2fec254ad7))


## v0.18.8 (2023-05-28)

### Bug Fixes

- Improve device ping
  ([`56e4469`](https://github.com/Python-roborock/python-roborock/commit/56e4469c95ac9255604025df99f0d6ac1940dd19))


## v0.18.7 (2023-05-27)

### Bug Fixes

- Change e2 fan codes ([#62](https://github.com/Python-roborock/python-roborock/pull/62),
  [`7231f1e`](https://github.com/Python-roborock/python-roborock/commit/7231f1efc412f93bfb5719091337536bcb6185d6))

* fix: change e2 fan codes

* fix: linting

* fix: incorrect balanced code


## v0.18.6 (2023-05-19)

### Bug Fixes

- Consumables with time equals 0
  ([`ccab5f0`](https://github.com/Python-roborock/python-roborock/commit/ccab5f0724854ae27bbc51b9ee33f2a96ce709f1))


## v0.18.5 (2023-05-16)

### Bug Fixes

- Connection_lost
  ([`c2ba673`](https://github.com/Python-roborock/python-roborock/commit/c2ba673f2c198bc78e75e1cf6fc9844e385e85bb))


## v0.18.4 (2023-05-16)

### Bug Fixes

- Minor fixes
  ([`e4a291d`](https://github.com/Python-roborock/python-roborock/commit/e4a291dd2b011e5852c992dbb23068ef5dde0e52))


## v0.18.3 (2023-05-15)

### Bug Fixes

- Keep_alive_func
  ([`e4aeebc`](https://github.com/Python-roborock/python-roborock/commit/e4aeebc16317a5c9fe3ffcd3bff89be1f2070dbb))

### Chores

- Linting
  ([`dbffaab`](https://github.com/Python-roborock/python-roborock/commit/dbffaaba59214015a9b721347331b37ff38fb941))


## v0.18.2 (2023-05-15)

### Bug Fixes

- Adding hello command
  ([`dfa44ff`](https://github.com/Python-roborock/python-roborock/commit/dfa44ff56a794f30e7c93d0a9a270f2a02da7e65))

- Improving new protocols
  ([`08c6f95`](https://github.com/Python-roborock/python-roborock/commit/08c6f9530b202d17ef80047c2d60836f9f9b8422))


## v0.18.1 (2023-05-15)

### Bug Fixes

- Type checks
  ([`58b3322`](https://github.com/Python-roborock/python-roborock/commit/58b33225b50a221a5f3100055fe28461f5cff884))


## v0.18.0 (2023-05-15)

### Features

- Keep connection alive
  ([`691b04b`](https://github.com/Python-roborock/python-roborock/commit/691b04b0135a38cc6b150e284d96e217f18f7f46))


## v0.17.8 (2023-05-15)

### Bug Fixes

- Trying to fix connection leaks
  ([`a66482a`](https://github.com/Python-roborock/python-roborock/commit/a66482a22cba9a6e7cc449c3f35acc1f230cd211))


## v0.17.7 (2023-05-15)

### Bug Fixes

- Ignoring get_room_mapping for int list response
  ([`c71d3b5`](https://github.com/Python-roborock/python-roborock/commit/c71d3b549a8dd09d08d1d27cde6882298875269c))


## v0.17.6 (2023-05-13)

### Bug Fixes

- Using cache only a single time
  ([`1ebfb35`](https://github.com/Python-roborock/python-roborock/commit/1ebfb35b9fe9ec50d4abeb60c695d33a37818768))


## v0.17.5 (2023-05-12)

### Bug Fixes

- Adding log for local disconnection
  ([`3001798`](https://github.com/Python-roborock/python-roborock/commit/300179839ec6a25e4ab8172f2c11e8beb0ff17ce))


## v0.17.4 (2023-05-12)

### Bug Fixes

- Pycharm typing
  ([`12d7c0b`](https://github.com/Python-roborock/python-roborock/commit/12d7c0b71bdeae90e9abbc6a16de3e07ebaa82da))


## v0.17.3 (2023-05-12)

### Bug Fixes

- Trigger new release
  ([`270a65c`](https://github.com/Python-roborock/python-roborock/commit/270a65c24a847cdc58a630e6d6c8e296910de8ea))


## v0.17.2 (2023-05-11)

### Bug Fixes

- Adding fallback cache (to be tested)
  ([`0e214cd`](https://github.com/Python-roborock/python-roborock/commit/0e214cd0633e9b9baca3323cc505a4f787aa08fb))

- Fallback_cache func
  ([`8048d84`](https://github.com/Python-roborock/python-roborock/commit/8048d843f669b06960967918570201498e4ae051))

### Chores

- Linting
  ([`2263190`](https://github.com/Python-roborock/python-roborock/commit/226319078162796c186bcd0bef46b961153e0435))


## v0.17.1 (2023-05-11)

### Bug Fixes

- Improving logs
  ([`cdd0ea7`](https://github.com/Python-roborock/python-roborock/commit/cdd0ea75d4e336c8f918a79574fd7b642eaffeec))


## v0.17.0 (2023-05-11)

### Features

- Dynamic calculated prefixes
  ([`d57a0a7`](https://github.com/Python-roborock/python-roborock/commit/d57a0a7d31f851b6bf4381233a84187d19e5782f))


## v0.16.1 (2023-05-10)

### Bug Fixes

- Connection timeouts
  ([`36a7295`](https://github.com/Python-roborock/python-roborock/commit/36a7295ce878dd0649505dd4a5b5ad662f0655fd))


## v0.16.0 (2023-05-10)

### Chores

- Adding package_parser.py
  ([`c6cc29b`](https://github.com/Python-roborock/python-roborock/commit/c6cc29b86418c7ed62f30a5684f5a95a6a712834))

- Fix readthedocs ([#59](https://github.com/Python-roborock/python-roborock/pull/59),
  [`b747ad8`](https://github.com/Python-roborock/python-roborock/commit/b747ad89ec1180ceffc4130d1be1ce9dee203f98))

- Linting
  ([`3eaed1d`](https://github.com/Python-roborock/python-roborock/commit/3eaed1d48293f474e65914c17c93ea54b7c0a9a5))

### Features

- Adding pcap file parser to cli
  ([`798287a`](https://github.com/Python-roborock/python-roborock/commit/798287a5100a3e973524aae6dd9404c0af354c11))


## v0.15.0 (2023-05-09)

### Bug Fixes

- Add int for clean summary ([#57](https://github.com/Python-roborock/python-roborock/pull/57),
  [`4257aa7`](https://github.com/Python-roborock/python-roborock/commit/4257aa7888178703d1b38ed00c12ef932ca1e862))

### Features

- Add docs ([#58](https://github.com/Python-roborock/python-roborock/pull/58),
  [`959abe1`](https://github.com/Python-roborock/python-roborock/commit/959abe1f3b2be0bfb8705d1bc1f9cbe966577540))


## v0.14.1 (2023-05-09)

### Bug Fixes

- Add types for S8 ([#56](https://github.com/Python-roborock/python-roborock/pull/56),
  [`125b6e7`](https://github.com/Python-roborock/python-roborock/commit/125b6e728145fde39f49fa6b80168bb985f2cc43))

* fix: add types for S8

* fix: lint


## v0.14.0 (2023-05-08)

### Features

- Add more codes for status ([#55](https://github.com/Python-roborock/python-roborock/pull/55),
  [`cddd765`](https://github.com/Python-roborock/python-roborock/commit/cddd765aa15e31ae50db5a6b29ff6988050aa5cc))


## v0.13.4 (2023-05-05)

### Bug Fixes

- Command prefixes
  ([`65c5db8`](https://github.com/Python-roborock/python-roborock/commit/65c5db834baadc4c1a61704bd2279c48dd0f6074))


## v0.13.3 (2023-05-05)

### Bug Fixes

- Roborock enum
  ([`ae0b93e`](https://github.com/Python-roborock/python-roborock/commit/ae0b93ee0f0fc9c62c3f40b436ece209938e9e6c))

### Chores

- Linting
  ([`250d5fc`](https://github.com/Python-roborock/python-roborock/commit/250d5fcc0a320604ee25519764bd7ac1872dbd0b))

- Linting
  ([`fea34d6`](https://github.com/Python-roborock/python-roborock/commit/fea34d63400a94447834ab355d0a023b53e77d7d))


## v0.13.2 (2023-05-05)

### Bug Fixes

- Minor changes
  ([`522734a`](https://github.com/Python-roborock/python-roborock/commit/522734a4bdcf6555feede24e3e97c6a3a98fa760))


## v0.13.1 (2023-05-05)

### Bug Fixes

- Adding app_start_collect_dust prefix
  ([`3124d7e`](https://github.com/Python-roborock/python-roborock/commit/3124d7ea6277ec08d8e592448b2a4f8cb60fb7db))


## v0.13.0 (2023-05-05)

### Features

- Add s4_max ([#54](https://github.com/Python-roborock/python-roborock/pull/54),
  [`e7cfd15`](https://github.com/Python-roborock/python-roborock/commit/e7cfd153b3c41215fd1c85d4968a14d1862c91b5))


## v0.12.1 (2023-05-05)

### Bug Fixes

- Changed incorrect s8 pro ultra string
  ([`c6a37a9`](https://github.com/Python-roborock/python-roborock/commit/c6a37a97da9279af3a6a24dc0fd01770cdd9b3b1))

fixes #52


## v0.12.0 (2023-05-05)

### Features

- Extending device status by device model
  ([#51](https://github.com/Python-roborock/python-roborock/pull/51),
  [`8092b67`](https://github.com/Python-roborock/python-roborock/commit/8092b67b8c9a380cca5178217fde3a61746fcf75))

* feat: extending device status by device model

* chore: linting


## v0.11.0 (2023-05-04)

### Features

- Add error check for invalid user agreement
  ([#49](https://github.com/Python-roborock/python-roborock/pull/49),
  [`0374449`](https://github.com/Python-roborock/python-roborock/commit/0374449d7280c93ceb772b7fbe009c6d19d0c462))

* minor: add error check for invalid user agreement

* fix: lint

* feat: add no user agreement error

* fix: version issue

* fix: added account to str


## v0.10.3 (2023-05-04)

### Bug Fixes

- Port already in use
  ([`e5d71d8`](https://github.com/Python-roborock/python-roborock/commit/e5d71d88f5144c172482cd6ee71d9a5b01dbbe3f))


## v0.10.2 (2023-05-03)

### Bug Fixes

- Change devices fan speed enum to lower case
  ([`c559d40`](https://github.com/Python-roborock/python-roborock/commit/c559d40183e47ef8698651281ae8946a99cb897e))

- Test errors
  ([`6a46515`](https://github.com/Python-roborock/python-roborock/commit/6a465157bbf6fa15bc578a1c4b1dffa17a694a92))


## v0.10.1 (2023-05-03)

### Bug Fixes

- Allow discovering multiple devices
  ([`ada9e07`](https://github.com/Python-roborock/python-roborock/commit/ada9e0723728b1d7e3ccd6dc37cbbe06a3c6a2cc))

### Chores

- Using python construct for data parsing
  ([#48](https://github.com/Python-roborock/python-roborock/pull/48),
  [`71f7f22`](https://github.com/Python-roborock/python-roborock/commit/71f7f2207986cb22c2990ae6d67fd38c2d04b472))

* chore: using python construct for data parsing

* chore: linting

* fix: roborock message protocol

* fix: change local api constructor


## v0.10.0 (2023-05-03)

### Chores

- Linting
  ([`e3f2541`](https://github.com/Python-roborock/python-roborock/commit/e3f25419fcfe00f18e0cca9214c4d50cd5254c80))

### Features

- Add specific device functionality
  ([#46](https://github.com/Python-roborock/python-roborock/pull/46),
  [`32abce5`](https://github.com/Python-roborock/python-roborock/commit/32abce5d51d14aab9adef5b9560ceee534186b1a))

* feat: add support for old mop and vacuum codes

* fix: linting

* feat: using api for single device and adding new commands

* fix: using single device api

(cherry picked from commit e689e8d141acff998fd524ace923621fc0f91d0c)

* chore: linting

(cherry picked from commit 2ed367cba5e9b4199fdea935305fb47f85a8c1e7)

(cherry picked from commit 58b46835d609794210f8c49daddbc7d25cee011d)

* chore: init work

* feat: added more device specific

* fix: merge issues

* feat: finalize specific device work

* feat: finished specific device with current info

* fix: add fast for S8

* fix: add s8 dock

---------

Co-authored-by: humbertogontijo <humberto.gontijo@clevertech.biz>


## v0.9.0 (2023-05-01)

### Chores

- Linting
  ([`a6a55ac`](https://github.com/Python-roborock/python-roborock/commit/a6a55ac4d11d230a0599aeec3d5254895fbaa684))

### Features

- Single device api and discovery method
  ([`5fef26d`](https://github.com/Python-roborock/python-roborock/commit/5fef26d257433c12d38f6b19731018e54884a150))


## v0.8.3 (2023-04-28)

### Bug Fixes

- Add functionality for missing enum values
  ([#43](https://github.com/Python-roborock/python-roborock/pull/43),
  [`49d77f8`](https://github.com/Python-roborock/python-roborock/commit/49d77f8208a65cb0fb86ab7948138df0bf447e45))

* fix: add functionality for missing enum values

* fix: temp removed 207

* Revert "chore: linting"

This reverts commit 58b46835d609794210f8c49daddbc7d25cee011d.

This reverts commit 2ed367cba5e9b4199fdea935305fb47f85a8c1e7.

* Revert "fix: using single device api"

This reverts commit e689e8d141acff998fd524ace923621fc0f91d0c.

### Chores

- Linting
  ([`58b4683`](https://github.com/Python-roborock/python-roborock/commit/58b46835d609794210f8c49daddbc7d25cee011d))

- Linting
  ([`2ed367c`](https://github.com/Python-roborock/python-roborock/commit/2ed367cba5e9b4199fdea935305fb47f85a8c1e7))


## v0.8.2 (2023-04-27)

### Bug Fixes

- Using single device api
  ([`e689e8d`](https://github.com/Python-roborock/python-roborock/commit/e689e8d141acff998fd524ace923621fc0f91d0c))

### Chores

- Linting
  ([`2e8e307`](https://github.com/Python-roborock/python-roborock/commit/2e8e307e6d82e045856d2a4ae731feba25005fe4))


## v0.8.1 (2023-04-27)

### Bug Fixes

- Adding keepalive to local connection
  ([`8ff8d2f`](https://github.com/Python-roborock/python-roborock/commit/8ff8d2f13fd85df96b3b334456799244ac878fbe))


## v0.8.0 (2023-04-27)

### Features

- Added error check and deviceprop functionality for core
  ([#42](https://github.com/Python-roborock/python-roborock/pull/42),
  [`746eec9`](https://github.com/Python-roborock/python-roborock/commit/746eec99ae0b6115fea6277f51b546036f7b3f18))

* feat: added update to deviceprop

* feat: added time remaining to consumable

* feat: added more exception checking

* fix: linting

* feat: add consumable const


## v0.7.8 (2023-04-26)

### Bug Fixes

- Local api failing to send message
  ([`4cc38fe`](https://github.com/Python-roborock/python-roborock/commit/4cc38fe13df487296efda2a1e962c238e3d69168))

### Chores

- Linting
  ([`c378036`](https://github.com/Python-roborock/python-roborock/commit/c3780369a2ea237f7ed6f5114d68d55fff6b1386))


## v0.7.7 (2023-04-26)

### Bug Fixes

- Local api recover after command fail
  ([`cb11f14`](https://github.com/Python-roborock/python-roborock/commit/cb11f14d7b771b31c77dafe6435bcd52527c16a8))


## v0.7.6 (2023-04-26)

### Bug Fixes

- Reset_consumable command prefix
  ([`a1a8c06`](https://github.com/Python-roborock/python-roborock/commit/a1a8c06d369e33e4ebd42cf6f563b9727d0ce24e))

### Chores

- Linting
  ([`ac7e15a`](https://github.com/Python-roborock/python-roborock/commit/ac7e15a349aa7a6f438339109189d9d715dfa71d))

- Linting
  ([`4907044`](https://github.com/Python-roborock/python-roborock/commit/4907044e1933ab8afc30f2289df0ca1130cadb28))


## v0.7.5 (2023-04-25)

### Bug Fixes

- Adding missing prefixes
  ([`66b1833`](https://github.com/Python-roborock/python-roborock/commit/66b183385c96dd7ee395bff143f2d64ef8fb927a))

### Chores

- Linting
  ([`41af0e2`](https://github.com/Python-roborock/python-roborock/commit/41af0e2469cb2d9786ceab8fbcfdb4701714db69))

- Linting
  ([`6d6dff5`](https://github.com/Python-roborock/python-roborock/commit/6d6dff5a0131b9a6735023ce0ac47bc9a0622bc9))


## v0.7.4 (2023-04-25)

### Bug Fixes

- Get_room_mapping
  ([`459119b`](https://github.com/Python-roborock/python-roborock/commit/459119bee90513451bf10a1abeeccb75f3daa539))


## v0.7.3 (2023-04-25)

### Bug Fixes

- Added missing docks ([#40](https://github.com/Python-roborock/python-roborock/pull/40),
  [`65a6cc4`](https://github.com/Python-roborock/python-roborock/commit/65a6cc4fd19a30bc78f2c34b407d3d88e3aac2b1))


## v0.7.2 (2023-04-25)

### Bug Fixes

- Command prefixes
  ([`e792728`](https://github.com/Python-roborock/python-roborock/commit/e7927288cc3059a1eced1a65b31f84190718aaf2))


## v0.7.1 (2023-04-25)

### Bug Fixes

- Command prefixes
  ([`156ac51`](https://github.com/Python-roborock/python-roborock/commit/156ac5182d1a97c93ab16696099c8c099a19155d))


## v0.7.0 (2023-04-25)

### Features

- Add room mapping ([#41](https://github.com/Python-roborock/python-roborock/pull/41),
  [`aa3e6e4`](https://github.com/Python-roborock/python-roborock/commit/aa3e6e442fbbb679c4eca68840c4d19f9c659fde))

* feat: add room mapping

* fix: lint

* chore: move room mapping to super class client

* chore: linting

* Update roborock/api.py

Co-authored-by: Humberto Gontijo <humberto.gontijo@clevertech.biz>

---------


## v0.6.17 (2023-04-25)

### Bug Fixes

- Adding multi_maps_list to device props
  ([`7ac0485`](https://github.com/Python-roborock/python-roborock/commit/7ac0485c4a5bb43350c51331323c6773ff1c54fc))

- Removing non-needed classes
  ([`6ceedad`](https://github.com/Python-roborock/python-roborock/commit/6ceedadf09c20c743c994b07489887e344cd3061))


## v0.6.16 (2023-04-22)

### Bug Fixes

- Improving local integration
  ([`7657617`](https://github.com/Python-roborock/python-roborock/commit/7657617901d807908e5fd5c364700851b5108ab4))


## v0.6.15 (2023-04-21)

### Bug Fixes

- Get_clean_summary
  ([`ee81538`](https://github.com/Python-roborock/python-roborock/commit/ee815380a8b70efbac65627fdd69fdf0bb75420e))

### Chores

- Linting
  ([`0d3b000`](https://github.com/Python-roborock/python-roborock/commit/0d3b00093395a706ec202c5a55639ed9ece54281))

- Linting
  ([`124fa11`](https://github.com/Python-roborock/python-roborock/commit/124fa115b14430b2a9680d4b1da36f1b70ae85b5))


## v0.6.14 (2023-04-21)

### Bug Fixes

- Get_multi_map_list
  ([`cfaeb41`](https://github.com/Python-roborock/python-roborock/commit/cfaeb419e188510ade5bc1506214c9b3d2afeb18))

- Linting
  ([`fdb4484`](https://github.com/Python-roborock/python-roborock/commit/fdb44840741cd6872f7defea70e8f118a9803099))


## v0.6.13 (2023-04-20)

### Bug Fixes

- Check dock_type is not none ([#38](https://github.com/Python-roborock/python-roborock/pull/38),
  [`84c95e3`](https://github.com/Python-roborock/python-roborock/commit/84c95e3b3bebd940b9cc6cc06b73c1770605c765))


## v0.6.12 (2023-04-19)

### Bug Fixes

- Removed enum type check ([#37](https://github.com/Python-roborock/python-roborock/pull/37),
  [`585238e`](https://github.com/Python-roborock/python-roborock/commit/585238e505e685e14d867b19819815e7c3e19634))


## v0.6.11 (2023-04-18)

### Bug Fixes

- Lint
  ([`b0d8996`](https://github.com/Python-roborock/python-roborock/commit/b0d8996d46c2a52f87a8c01eb50fd6aa7bd98ed8))


## v0.6.10 (2023-04-18)

### Bug Fixes

- Lint
  ([`5ae44e2`](https://github.com/Python-roborock/python-roborock/commit/5ae44e247efca5e9b7958b887f6049f09ae2ced8))


## v0.6.9 (2023-04-18)

### Bug Fixes

- Lint
  ([`8499522`](https://github.com/Python-roborock/python-roborock/commit/8499522e5fb44abad20af1cfb7a677ca4e03639f))


## v0.6.8 (2023-04-18)

### Bug Fixes

- Lint
  ([`20bf54b`](https://github.com/Python-roborock/python-roborock/commit/20bf54b0a1834065584bdcb469a3123700c68f1d))


## v0.6.7 (2023-04-18)


## v0.6.6 (2023-04-17)

### Bug Fixes

- Using asyncio future instead of queue
  ([`1ea5430`](https://github.com/Python-roborock/python-roborock/commit/1ea5430197620dbd2dc87949e4326f24601f4ba8))


## v0.6.5 (2023-04-13)

### Bug Fixes

- Clean_summary for older devices
  ([`0a0c9e7`](https://github.com/Python-roborock/python-roborock/commit/0a0c9e7c965c183df971e11bd597319c68c8f646))

- Exclude changelog.md from pre-commit
  ([#36](https://github.com/Python-roborock/python-roborock/pull/36),
  [`b12c7a2`](https://github.com/Python-roborock/python-roborock/commit/b12c7a229dfdbe0af182d6a120548100b0ca4140))

### Chores

- Fix mypy errors ([#34](https://github.com/Python-roborock/python-roborock/pull/34),
  [`16bd2d1`](https://github.com/Python-roborock/python-roborock/commit/16bd2d1fab65760670252120fafa4b8e87e968be))

* chore: fix mypy errors

* fix: run mypy through pre-commit

* fix: spacing for ci

* fix: tests changes

* fix: cli exclusion

* fix: add typing for roborockenum

* fix: ignore warnings with mqtt.client

* fix: more mypy changes

* fix: limit cli mypy

* fix: ignore type for containers

* fix: add pre-commit information to dev poetry dependencies

- New styling ([#35](https://github.com/Python-roborock/python-roborock/pull/35),
  [`55e6426`](https://github.com/Python-roborock/python-roborock/commit/55e6426129ec70f41a019fd9408b227fb8a03b5a))


## v0.6.4 (2023-04-11)

### Bug Fixes

- Disconnect on timeout so next command can work
  ([`5ad397b`](https://github.com/Python-roborock/python-roborock/commit/5ad397b3bbb4bc600888baba6c0cc15be9d17ef7))


## v0.6.3 (2023-04-11)

### Bug Fixes

- Semantic_release
  ([`63b249d`](https://github.com/Python-roborock/python-roborock/commit/63b249d65d3fc40b048320e6596aedc40f588bf9))


## v0.6.2 (2023-04-11)

### Bug Fixes

- Error code nogo_zone_detected
  ([`722e4b5`](https://github.com/Python-roborock/python-roborock/commit/722e4b5cfd0c4891adc506e9fe99740860027670))


## v0.6.1 (2023-04-10)

### Bug Fixes

- Lowercase true
  ([`774c3cc`](https://github.com/Python-roborock/python-roborock/commit/774c3cc9765ee76a3a553ca6911751124ae7164c))

- Semantic release not updating changelong
  ([`eaf6e90`](https://github.com/Python-roborock/python-roborock/commit/eaf6e90264b6ab69549da0e5bc3d17c4c0a2c07c))

- Trigger release
  ([`f1ce0ed`](https://github.com/Python-roborock/python-roborock/commit/f1ce0ed55a254bccd8567b48974ff74dd9ec8b25))

- Trigger release
  ([`9a4462c`](https://github.com/Python-roborock/python-roborock/commit/9a4462c800762393cc047085156acbe119cd0fe4))

- Trigger release
  ([`b7a664b`](https://github.com/Python-roborock/python-roborock/commit/b7a664b15b7c5180d816de325537693f47c24860))

- Trigger release
  ([`9256849`](https://github.com/Python-roborock/python-roborock/commit/9256849252f019f4fea2f59384bc0ea7c57adb5c))

### Chores

- Update gh token
  ([`f13690d`](https://github.com/Python-roborock/python-roborock/commit/f13690de8c4b5eb3d72809dff66a0caf275476dc))


## v0.6.0 (2023-04-08)

### Bug Fixes

- Changed prefixes for debugged commands
  ([`0db6b6d`](https://github.com/Python-roborock/python-roborock/commit/0db6b6dc3b7ef1b7721b8a9536affdd08380d916))

### Features

- Add more commands and prefixes
  ([`fe85dea`](https://github.com/Python-roborock/python-roborock/commit/fe85deaa1acc053c9c18f2b313ff5b812ba0e2c3))


## v0.5.9 (2023-04-07)

### Bug Fixes

- Assume device prop attr can be none
  ([`573db33`](https://github.com/Python-roborock/python-roborock/commit/573db337664be1f768254e384e3eef6c957955ba))

- Change to dataclass
  ([`111d762`](https://github.com/Python-roborock/python-roborock/commit/111d7627aa5999fc82cde650326857e51c4dc4a2))


## v0.5.8 (2023-04-07)

### Bug Fixes

- Changed prefix for set_custom_mode
  ([`d187eb4`](https://github.com/Python-roborock/python-roborock/commit/d187eb467e6c5c969fcaa48dcc7881d75784663d))


## v0.5.7 (2023-04-07)


## v0.5.6 (2023-04-06)

### Bug Fixes

- Create function for creating roborock code
  ([`2cf00fe`](https://github.com/Python-roborock/python-roborock/commit/2cf00fe607c7b5b544ea9671dabf87454cdb2322))

- Roborockbase.as_dict
  ([`bf52b44`](https://github.com/Python-roborock/python-roborock/commit/bf52b44b01e93000268c9fa274a3449ac3f82e36))


## v0.5.5 (2023-04-06)

### Bug Fixes

- Fix cloud_api
  ([`6159412`](https://github.com/Python-roborock/python-roborock/commit/6159412b577efa3544add18982d6a9859ad8225d))


## v0.5.4 (2023-04-06)

### Bug Fixes

- Minor fixes
  ([`7579ad5`](https://github.com/Python-roborock/python-roborock/commit/7579ad5266f46102b90be0a7676e5c116f5daefa))


## v0.5.3 (2023-04-06)

### Bug Fixes

- Roborock enum
  ([`df1262e`](https://github.com/Python-roborock/python-roborock/commit/df1262ef41b2b1cb4fd866cda1527b82723d38cd))


## v0.5.2 (2023-04-06)

### Bug Fixes

- Changing code mappings
  ([`493ed4b`](https://github.com/Python-roborock/python-roborock/commit/493ed4b9a1fb8f62918ecc4899b9ce716801b4be))

- Code mappings
  ([`115dad2`](https://github.com/Python-roborock/python-roborock/commit/115dad22c0280edf1853de43ae86ff1169707f5b))

- Roborockdeviceinfo
  ([`1ced9e9`](https://github.com/Python-roborock/python-roborock/commit/1ced9e95a6d2effb359008c2c5ef340db3243d6e))

- Using dataclass for containers
  ([`ad25a44`](https://github.com/Python-roborock/python-roborock/commit/ad25a443fb697f90b10a9c42c93bccbf4204c383))


## v0.5.1 (2023-04-05)


## v0.5.0 (2023-04-05)

### Bug Fixes

- Change device info class to dataclass
  ([`158766f`](https://github.com/Python-roborock/python-roborock/commit/158766fcb70b92aba87e8b7fe2255528fa72f123))

### Features

- Add networking function
  ([`19746aa`](https://github.com/Python-roborock/python-roborock/commit/19746aa7739da295c4e7c7316596af9f8ff6b0a0))


## v0.4.16 (2023-04-05)

### Bug Fixes

- Mapping prefix for all known commands
  ([`ad3afc0`](https://github.com/Python-roborock/python-roborock/commit/ad3afc04dfec31a20a4a2635b4c6b52cf236ce17))


## v0.4.15 (2023-04-04)

### Bug Fixes

- Test_get_washing_mode
  ([`17e72c3`](https://github.com/Python-roborock/python-roborock/commit/17e72c34c6ac133025450eab68f4be7025ab138b))

- **local_api**: Receiving multiple messages
  ([`e3c419c`](https://github.com/Python-roborock/python-roborock/commit/e3c419c98f64bc3adada4cc78ce4de366b5267cb))


## v0.4.14 (2023-04-03)

### Bug Fixes

- Adding is_valid function to RoborockBase
  ([`7575aee`](https://github.com/Python-roborock/python-roborock/commit/7575aeea3b1ca4cfe4a1fb0cb3cea29e964f52b7))


## v0.4.13 (2023-04-03)

### Bug Fixes

- Adiing broken pipe exception log
  ([`7e73eb2`](https://github.com/Python-roborock/python-roborock/commit/7e73eb2ac7b93f6d0d7331515cf9db5da2c92dc5))


## v0.4.12 (2023-04-03)

### Bug Fixes

- Add containers for dock information
  ([`77dc414`](https://github.com/Python-roborock/python-roborock/commit/77dc4146b16906807d8a5fbc5025c4a8344c62f0))

### Chores

- Add changelog
  ([`cc3f378`](https://github.com/Python-roborock/python-roborock/commit/cc3f378d9427c95a66ecdd5c1277a7415e322850))

- Pypi cleanup
  ([`1878e8e`](https://github.com/Python-roborock/python-roborock/commit/1878e8e42692a2f56679fbdd667da29dfcf759e3))


## v0.4.11 (2023-04-01)

### Bug Fixes

- Changing RoborockDeviceInfo to serializable
  ([`6dd8ff8`](https://github.com/Python-roborock/python-roborock/commit/6dd8ff8e622d5021e20caf19d36812e34e6c435f))


## v0.4.10 (2023-04-01)

### Bug Fixes

- Using entire object for roborock device info
  ([`599d461`](https://github.com/Python-roborock/python-roborock/commit/599d461af69c7d6b220973c5d905decc5657ce0f))


## v0.4.9 (2023-04-01)

### Bug Fixes

- Cloud_api.py
  ([`39fd964`](https://github.com/Python-roborock/python-roborock/commit/39fd964a9ccd0a33310747d6f7d764db1b7c3c23))


## v0.4.8 (2023-04-01)

### Bug Fixes

- Refactor roborock device info
  ([`291a6b2`](https://github.com/Python-roborock/python-roborock/commit/291a6b295943d6635116e79f7f56c97a553a7c62))


## v0.4.7 (2023-04-01)

### Bug Fixes

- Local_api should receive ip for each device
  ([`b2f2f15`](https://github.com/Python-roborock/python-roborock/commit/b2f2f1566a27505ebf456aef360b76d001a1351c))


## v0.4.6 (2023-04-01)

### Bug Fixes

- Adding local_api disconnection
  ([`a010304`](https://github.com/Python-roborock/python-roborock/commit/a01030480353b8d6524c71e463455802082f4066))

- Move add_status_listener from cloud_api to base_api
  ([`dcad915`](https://github.com/Python-roborock/python-roborock/commit/dcad91545ba18e163ba4ceca887065817b0a4e0c))


## v0.4.5 (2023-04-01)

### Bug Fixes

- Close socket on broken pipe
  ([`bf8c8d5`](https://github.com/Python-roborock/python-roborock/commit/bf8c8d52b390b27b442a3b7dd046f8ece483bc2e))

### Chores

- Fix cloud_api.py
  ([`b954c9c`](https://github.com/Python-roborock/python-roborock/commit/b954c9c22977b8239b034e346292a23afe5acbfb))


## v0.4.4 (2023-04-01)

### Bug Fixes

- Removing local_api.py nonworking commands from api.py
  ([`12bf756`](https://github.com/Python-roborock/python-roborock/commit/12bf756d8d5193bd4cfd9b59d85f11ec3ad4f6e0))

### Chores

- Add new commands
  ([`e0869cf`](https://github.com/Python-roborock/python-roborock/commit/e0869cf83e87d4c35986acdddf25f650acbd92ee))

- Removing local_api.py nonworking commands from api.py
  ([`70c04a3`](https://github.com/Python-roborock/python-roborock/commit/70c04a32878cb98c1e009860f2b6d8ede83a6e47))


## v0.4.3 (2023-04-01)

### Bug Fixes

- Minor fixes
  ([`29bdb45`](https://github.com/Python-roborock/python-roborock/commit/29bdb4542e1c32b956ea8b739f9a610b92e27259))


## v0.4.2 (2023-04-01)

### Bug Fixes

- Refactoring api
  ([`aa66e1d`](https://github.com/Python-roborock/python-roborock/commit/aa66e1d31ed635690104f9b30b62421e8a2ba663))


## v0.4.1 (2023-03-31)

### Bug Fixes

- Code cleaning
  ([`d6e3b34`](https://github.com/Python-roborock/python-roborock/commit/d6e3b34bfa5e1803b5e5e494711e56b7d909f1ea))


## v0.4.0 (2023-03-31)

### Features

- Sppliting clients into local and cloud
  ([`8019313`](https://github.com/Python-roborock/python-roborock/commit/8019313ccb50233610b74d2626ae87e79f55204e))


## v0.3.1 (2023-03-30)

### Bug Fixes

- Minor fixes to offline integration
  ([`1b4926e`](https://github.com/Python-roborock/python-roborock/commit/1b4926e1d79401f21bee68e4676235426e253191))


## v0.3.0 (2023-03-30)

### Features

- Adding offline.py for others to test local api
  ([`22680bf`](https://github.com/Python-roborock/python-roborock/commit/22680bfd7929d77b12c27c270478c3253d0cfada))


## v0.2.3 (2023-03-29)

### Bug Fixes

- Bug with dock commands
  ([`2f2cfb6`](https://github.com/Python-roborock/python-roborock/commit/2f2cfb6b702b6a6f9500e3b272761962ed15ed09))


## v0.2.2 (2023-03-28)

### Bug Fixes

- Change semantic_release from tag_only to tag
  ([`cad8973`](https://github.com/Python-roborock/python-roborock/commit/cad897381515530ba221b2f92a75ebb3fde876bd))


## v0.2.1 (2023-03-28)

### Bug Fixes

- Repository variable for python-semantic-release
  ([`b9e21a3`](https://github.com/Python-roborock/python-roborock/commit/b9e21a3d2f5db0a426b96031e154a2a001bc3242))


## v0.2.0 (2023-03-28)

### Bug Fixes

- Add version source
  ([`c46e503`](https://github.com/Python-roborock/python-roborock/commit/c46e503b91159468e7cf4afb9549c720c1d3dee0))

- Change github token from user defined secret to default secret
  ([`5886535`](https://github.com/Python-roborock/python-roborock/commit/58865350d583ffa1c4e00a2c22c12b8cf60d3c5f))

- Change to timeout from wait_for
  ([`eaa4dee`](https://github.com/Python-roborock/python-roborock/commit/eaa4dee1dca696a5817205cd4387b92ce93df0bf))

wait_for creates a task, async_timeout does the same work and avoids the task creation

- Removed unneeded line
  ([`f2b4c89`](https://github.com/Python-roborock/python-roborock/commit/f2b4c89500ac169e9dc021de6e250474f6f75b15))

- Rename github_token to gh_token
  ([`012cd9d`](https://github.com/Python-roborock/python-roborock/commit/012cd9d0ec065d78063472dc66e60e9545547e24))

- Version source from pyproject.toml
  ([`20d3c59`](https://github.com/Python-roborock/python-roborock/commit/20d3c59bab6fee2093b892cdc062f929a2b83304))

### Chores

- Add typing to user_data property
  ([`16f1d5d`](https://github.com/Python-roborock/python-roborock/commit/16f1d5dc10123987ee480bc4696a9a80a5bbe376))

- Added some typing
  ([`3a72b58`](https://github.com/Python-roborock/python-roborock/commit/3a72b58273d80f0a5d8d8da473e2b0e16aeea722))

- Added typing for containers
  ([`be20ae1`](https://github.com/Python-roborock/python-roborock/commit/be20ae1fb8c3055b54de083b542cee86874ba9f7))

- Bump pycryptodome to 3.17
  ([`1931073`](https://github.com/Python-roborock/python-roborock/commit/193107361f81706e2a67b9558b9e0ad56607166b))

- Bump version
  ([`33ab4d1`](https://github.com/Python-roborock/python-roborock/commit/33ab4d1523aa21dc692685cd109f878888ee4d78))

- Fix tests with new code mapping
  ([`4dac8f5`](https://github.com/Python-roborock/python-roborock/commit/4dac8f5ced0dbe0c948a8e8ca335d05f39b27634))

- Moved code mappings to api
  ([`81bf2e2`](https://github.com/Python-roborock/python-roborock/commit/81bf2e24342dd0b5c1fee3d0c32c38cf4791f7d0))

### Features

- Add dock error mapping
  ([`4694c66`](https://github.com/Python-roborock/python-roborock/commit/4694c661edaa09a2f637a4ad2191a3b587613ffb))

- Added semantic release
  ([`2bb2279`](https://github.com/Python-roborock/python-roborock/commit/2bb2279187609a7a7cf4c1a854ede54e8a671860))

- Adding more options to commands
  ([`9b20345`](https://github.com/Python-roborock/python-roborock/commit/9b203456c3bd5e075e2945be24e1aa65620af12f))
