# Repository Engineering Guidelines: python-roborock

## Overview & Scope
`python-roborock` is an asynchronous (`asyncio`) device integration library supporting multi-protocol Roborock vacuum and home appliances (V1 JSON-RPC over AES, B01 Tuya DPS for Q7/Q10, and A01 Tuya DPS for Dyad/Zeo). While Home Assistant Core is a primary downstream consumer, `python-roborock` is an independent client library whose public abstractions must remain general-purpose and consumer-agnostic.

This document serves as the authoritative, single source of truth for engineering conventions, architectural standards, and automated code reviews across all contributors and coding agents.

---

## Environment & Tooling Standards
- **Target**: Python 3.11+, Hatchling build backend, `uv` package manager.
- **Linters & Formatters**: Ruff (line length 120), Mypy (`check_untyped_defs = true`), Codespell.
- **Testing**: pytest (`pytest-asyncio`).

### Key Developer Commands
```bash
# Environment setup
uv venv && uv sync

# Run tests
uv run pytest
uv run pytest tests/devices/traits/v1/test_status.py
uv run pytest tests/protocols/test_v1_protocol.py

# Lint and typecheck
uv run pre-commit run --all-files
# or directly:
uv run ruff check roborock tests
uv run mypy roborock tests
```

---

## Core Architectural Hierarchy & Review Priorities
Evaluate every change against the repository's three core layers in strict priority order:

1. **Priority 1: Public Trait APIs & Consumer Contracts** (Highest Priority)
   - Clean, stable user-facing abstractions decoupled from wire protocol details, Tuya DPS keys, encryption keys, or transport sockets.
   - Strongly typed with concrete models subclassing `RoborockBase`; never expose raw protocol dictionaries or `Any` on public boundaries.

2. **Priority 2: Data Lifecycle & State Management**
   - Simple, linear data flow. Keep side effects visible: helper functions MUST be pure transformations that compute and return values rather than mutating object state as a side effect.
   - Exhaustive lifecycle teardown: all listeners, background tasks, and channels cleanly unhooked in `RoborockDevice.close()`.
   - Concurrency: 1:1 request/response matching across async push channels uses `asyncio.Future` correlated by protocol request/sequence ID (`request_id` for V1 RPC, `msg_id` for B01/Tuya).
   - Transform data in render pipelines; never mutate cached telemetry state or raw packets for presentation effects.

3. **Priority 3: Wire Protocol Parsers, Codecs & Cryptography**
   - Encapsulate cryptography (AES, MD5), protocol framing, and raw sockets to `roborock.protocols` and `roborock.devices.transport` / `roborock.devices.rpc`.
   - Keep protocol families (V1 JSON-RPC, B01 Tuya DPS, A01 Tuya DPS) strictly isolated; never conflate schemas across families.
   - Enforce enum fallback resilience (`RoborockEnum` with lowercase `unknown = -1` or `RoborockModeEnum.from_code_optional()`); never crash on unexpected firmware codes.

---

## Detailed Engineering Conventions

### 1. Typing & Data Models
- **Subclass `RoborockBase`**: Define structured domain and wire data models as `@dataclass` subclassing `RoborockBase` (`from_dict`, `as_dict`). Avoid `TypedDict` or loose dicts. (Binary protocol packets, transport message envelopes, and map layers are exempt).
- **Enum Fallback Resilience**: All enums representing device status, firmware modes, error codes, and wire protocol integer codes MUST inherit from `RoborockEnum` (defining a lowercase `unknown = -1` or `0` member) or `RoborockModeEnum` (using `from_code_optional()`). Internal enums not decoding unknown firmware codes remain standard `Enum`/`StrEnum`.
- **Strongly Type What You Know; Contain `Any` to the Wire**: Public trait APIs, method signatures, properties, and domain models MUST declare concrete types. `Any` is accepted only where the underlying wire protocol is dynamic or polymorphic (Tuya DPS maps, low-level RPC dispatch, serialization helpers, evolving cloud schemas).
- **Avoid Forward References & `TYPE_CHECKING`**: Avoid stringified forward references (`"ClassName"`) and `if typing.TYPE_CHECKING:` guards wherever possible. They typically indicate circular dependencies or coupling that should be refactored by extracting shared models.
- **Explicit Parameters**: Do not mark arguments or dataclass fields as `Optional[...]` or default them to `None` if they are always required by the protocol or caller.
- **Trust Type Annotations**: Prohibit defensive runtime `isinstance` checks on statically typed parameters in business and trait logic. (Dynamic wire payload unpacking and type narrowing in `from_dict` or RPC deserializers is legitimate and expected).

### 2. Protocol & Device Communications
- **Channel Trait Boundary**: Traits receive only an abstract communication channel (e.g., `Channel`, `RpcChannel`). Never pass device local keys, security tokens, IP addresses, or transport sockets into `Trait` instances.
- **Version Isolation**: Keep V1, B01, and A01 parser pipelines strictly isolated. Do not bleed Tuya DPS decoding logic into V1 or vice versa.

### 3. Trait Design & Client Integration
- **Compound Capability & Feature Gating**: Capability and trait availability MUST be gated by protocol version (`device.pv == "1.0"` or `DeviceVersion.V1`), appropriate category (`RoborockCategory.VACUUM`, `WET_DRY_VAC`, or `WASHING_MACHINE`), and device feature flags (`device.features`).
- **Linear State Flow**: Methods that parse responses or transform telemetry must return values to make state assignments explicit at the call site. Avoid multi-layered helper cascades.
- **Consumer Agnosticism**: Design traits around cohesive, general-purpose consumer concepts (`CleanHistoryTrait`, `DockTrait`, `ConsumableTrait`), not low-level firmware registers or raw Tuya DPS numbers.
- **Diagnostic Safety & Privacy**: Exclude sensitive user information (Wi-Fi SSIDs, passwords, cloud tokens, encryption keys) from device diagnostics and logs.

### 4. Error Handling & Exceptions
- **Hierarchy Rooting**: All custom exceptions MUST inherit from `roborock.exceptions.RoborockException`.
- **Specific Exception Narrowing**: Catch only specific, expected exception classes (`RoborockTimeout`, `RoborockConnectionException`, `json.JSONDecodeError`). Catching broad `Exception` is permitted only in teardown/cleanup handlers (e.g. `device.py`) to guarantee resources are unsubscribed before re-raising or logging.
- **Context-Rich Parsing Exceptions**: Wrap deserialization, decoding, and schema mapping errors into `RoborockParsingException` with rich context (`trait_name`, `command`, `payload`, `inner_error`).
- **Guard Clauses**: Flatten nested conditional branches with early exit guard clauses (`if not condition: return`).

### 5. Test Patterns & Fixtures
- **Test Mirroring & Colocation**: Place and maintain unit tests in the matching mirror path under `tests/` (e.g. `tests/devices/traits/v1/test_status.py` for `roborock/devices/traits/v1/status.py`; `tests/map/test_b01_q10_map_parser.py` for `roborock/map/b01_q10_map_parser.py`).
- **Avoid One-Off Test Files**: Do not create fragmented, single-bug test files (such as `tests/test_battery_low_voltage_fix.py`). Integrate test cases into the module's corresponding test suite.
- **Fixture Reuse & Parametrization**: Reuse shared fixtures (`fake_channel`, `message_builder`, `device_fixture`) in `tests/` and use table-driven `@pytest.mark.parametrize`.
- **Behavior-Driven Assertions**: Assert on public trait methods, return values, and emitted channel commands—never on private object attributes (`_state`).

### 6. PR Hygiene & Sizing
- **Scoping & Sizing**: Keep pull requests focused on a single logical change or subsystem where possible (e.g. parser module with tests in one PR, traits consuming it in a follow-up PR). Large PRs (>500–1,000 LOC) take longer to review and block releases.
- **CI Requirements**: PRs must pass automated CI (`.github/workflows/ci.yml`):
  - **Commitlint**: Commit messages and PR titles MUST follow Conventional Commits (`feat:`, `fix:`, `refactor:`, `chore:`, `docs:`).
  - **Pre-commit**: Ruff, Mypy (`check_untyped_defs = true`), and Codespell must pass (`uv run pre-commit run --all-files`).
  - **Pytest**: All unit tests must pass (`uv run pytest`).
- **Logical Placement**: Place domain constants and enums in the module where they are consumed or in `roborock.data.code_mappings`. Do not duplicate definitions across files.

---

## Available Agent Skills

Portable agent skills following the [Agent Skills specification](https://agentskills.io/specification) are located under `.agents/skills/`:

- **Code Review Skill** (`.agents/skills/review/SKILL.md`):
  A structured, interactive review workflow for evaluating pull requests and diffs against the repository's architectural hierarchy, typing rules, and testing standards. To invoke during interactive sessions, refer to [.agents/skills/review/SKILL.md](.agents/skills/review/SKILL.md).
