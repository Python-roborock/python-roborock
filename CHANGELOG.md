# CHANGELOG


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
