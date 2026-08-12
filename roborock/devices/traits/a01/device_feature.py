from __future__ import annotations

from roborock.roborock_message import RoborockZeoProtocol

# ── Per-series model ID frozensets ──────────────────────────────────────

_H1_SERIES: frozenset[str] = frozenset(
    {
        "roborock.wm.a63",  # H1
        "roborock.wm.a102",  # H1 Overseas
    }
)

_H1_LITE_SERIES: frozenset[str] = frozenset(
    {
        "roborock.wm.a90",  # H1 Lite
        "roborock.wm.a91",  # H1 Lite Overseas
        "roborock.wm.a237",  # H1 Lite Resupply
    }
)

_H1C_SERIES: frozenset[str] = frozenset(
    {
        "roborock.wm.a114",  # H1C
        "roborock.wm.a242",  # H1C Overseas
    }
)

_M1_SERIES: frozenset[str] = frozenset(
    {
        "roborock.wm.a92",  # M1
        "roborock.wm.a93",  # M1 Overseas
        "roborock.wm.a133",  # M1Lite
        "roborock.wm.a162",  # M1Lite Overseas
        "roborock.wm.a233",  # M1Lite Plus
        "roborock.wm.a234",  # M1 Plus
        "roborock.wm.a218",  # M1 Rev2
        "roborock.wm.a213",  # Medusa
        "roborock.wm.a276",  # M1Lite Plus Rev2
        "roborock.wm.a277",  # M1Lite Rev3
    }
)

_MUSE_SERIES: frozenset[str] = frozenset(
    {
        "roborock.wm.a142",  # Muse
        "roborock.wm.a215",  # Muse Overseas
        "roborock.wm.a211",  # Mitty
    }
)

_METIS_SERIES: frozenset[str] = frozenset(
    {
        "roborock.wm.a154",  # Metis
        "roborock.wm.a214",  # Metis Overseas
    }
)

_HYPERION_SERIES: frozenset[str] = frozenset(
    {
        "roborock.wm.a141",  # Hyperion
        "roborock.wm.a149",  # HyperionPro
        "roborock.wm.a207",  # Hyperion Plus
        "roborock.wm.a230",  # Hyperion Overseas
    }
)

_POSEIDON_SERIES: frozenset[str] = frozenset(
    {
        "roborock.wm.a180",  # Pro
        "roborock.wm.a181",
        "roborock.wm.a201",  # Pro+
        "roborock.wm.a255",  # Overseas
    }
)

_HERA_SERIES: frozenset[str] = frozenset(
    {
        "roborock.wm.a227",  # Hera
        "roborock.wm.a261",  # DE
        "roborock.wm.a268",  # KR
        "roborock.wm.a269",  # TW
        "roborock.wm.a273",  # NO
    }
)

_PANDORA_SERIES: frozenset[str] = frozenset(
    {
        "roborock.wm.a239",  # Pandora
        "roborock.wm.a262",  # DE
        "roborock.wm.a270",  # KR
        "roborock.wm.a271",  # TW
        "roborock.wm.a272",  # NO
    }
)

_HALIA_SERIES: frozenset[str] = frozenset(
    {
        "roborock.wm.a240",  # Halia
        "roborock.wm.a241",  # Halia Lite
    }
)

_APOLLO_SERIES: frozenset[str] = frozenset(
    {
        "roborock.cd.a188",  # Apollo Pro+
        "roborock.cd.a204",  # Apollo Pro
        "roborock.cd.a258",  # Apollo Pro Overseas
        "roborock.cd.a265",  # Apollo Pro+ Overseas
    }
)

# ── Device-type frozensets ──────────────────────────────────────────────

# All dryer models (cd.* prefix).
_DRYER_PRODUCT_IDS: frozenset[str] = _APOLLO_SERIES

# Overseas models (supports remote control via DP 232).
_OVERSEAS_PRODUCT_IDS: frozenset[str] = frozenset(
    {
        "roborock.wm.a102",  # H1 Overseas
        "roborock.wm.a91",  # H1 Lite Overseas
        "roborock.wm.a93",  # M1 Overseas
        "roborock.wm.a162",  # M1Lite Overseas
        "roborock.wm.a215",  # Muse Overseas
        "roborock.wm.a214",  # Metis Overseas
        "roborock.wm.a230",  # Hyperion Overseas
        "roborock.wm.a242",  # H1C Overseas
        "roborock.wm.a255",  # Poseidon Overseas
        "roborock.cd.a258",  # Apollo Pro Overseas
        "roborock.cd.a265",  # Apollo Pro+ Overseas
        "roborock.wm.a261",  # Hera DE
        "roborock.wm.a262",  # Pandora DE
    }
)

# Devices known to lack FEATURE_BITS (DP 237).
_UNSUPPORTED_FEATURE_BITS: frozenset[str] = frozenset(
    {
        "roborock.wm.a63",  # H1
        "roborock.wm.a90",  # H1 Lite
    }
)

# ── Force-load DP lists ─────────────────────────────────────────────────

_FORCE_LOAD_BASE_WASHER: list[RoborockZeoProtocol] = [
    RoborockZeoProtocol.START,  # 200
    RoborockZeoProtocol.PAUSE,  # 201
    RoborockZeoProtocol.SHUTDOWN,  # 202
    RoborockZeoProtocol.STATE,  # 203
    RoborockZeoProtocol.MODE,  # 204
    RoborockZeoProtocol.PROGRAM,  # 205
    RoborockZeoProtocol.CHILD_LOCK,  # 206
    RoborockZeoProtocol.TEMP,  # 207
    RoborockZeoProtocol.RINSE_TIMES,  # 208
    RoborockZeoProtocol.SPIN_LEVEL,  # 209
    RoborockZeoProtocol.DRYING_MODE,  # 210
    RoborockZeoProtocol.DETERGENT_SET,  # 211
    RoborockZeoProtocol.DETERGENT_TYPE,  # 213
    RoborockZeoProtocol.COUNTDOWN,  # 217
    RoborockZeoProtocol.WASHING_LEFT,  # 218
    RoborockZeoProtocol.DOORLOCK_STATE,  # 219
    RoborockZeoProtocol.ERROR,  # 220
    RoborockZeoProtocol.CUSTOM_PARAM_SAVE,  # 221
    RoborockZeoProtocol.CUSTOM_PARAM_GET,  # 222
    RoborockZeoProtocol.SOUND_SET,  # 223
    RoborockZeoProtocol.TIMES_AFTER_CLEAN,  # 224
    RoborockZeoProtocol.DETERGENT_EMPTY,  # 226
    RoborockZeoProtocol.FEATURE_BITS,  # 237
    RoborockZeoProtocol.PRODUCT_INFO,  # 10005
    RoborockZeoProtocol.WASHING_LOG,  # 10008
    RoborockZeoProtocol.OTA_NFO,  # 10007
    RoborockZeoProtocol.F_C,  # 10001
]

_FORCE_LOAD_BASE_DRYER: list[RoborockZeoProtocol] = [
    RoborockZeoProtocol.START,  # 200
    RoborockZeoProtocol.PAUSE,  # 201
    RoborockZeoProtocol.SHUTDOWN,  # 202
    RoborockZeoProtocol.STATE,  # 203
    RoborockZeoProtocol.MODE,  # 204
    RoborockZeoProtocol.PROGRAM,  # 205
    RoborockZeoProtocol.CHILD_LOCK,  # 206
    RoborockZeoProtocol.DRYING_MODE,  # 210
    RoborockZeoProtocol.COUNTDOWN,  # 217
    RoborockZeoProtocol.WASHING_LEFT,  # 218
    RoborockZeoProtocol.DOORLOCK_STATE,  # 219
    RoborockZeoProtocol.ERROR,  # 220
    RoborockZeoProtocol.CUSTOM_PARAM_GET,  # 222
    RoborockZeoProtocol.SOUND_SET,  # 223
    RoborockZeoProtocol.DRYING_METHOD,  # 256
    RoborockZeoProtocol.STEAM_VOLUME,  # 257
    RoborockZeoProtocol.FEATURE_BITS,  # 237
    RoborockZeoProtocol.PRODUCT_INFO,  # 10005
    RoborockZeoProtocol.WASHING_LOG,  # 10008
    RoborockZeoProtocol.OTA_NFO,  # 10007
    RoborockZeoProtocol.F_C,  # 10001
]


# ── Public helpers ──────────────────────────────────────────────────────


def is_dryer(model: str | None) -> bool:
    """Return True if *model* belongs to a dryer (cd.*)."""
    if model is None:
        return False
    return model in _DRYER_PRODUCT_IDS


def has_softener_compartment(model: str | None) -> bool:
    """M1 / Muse / Metis and all dryers lack a softener compartment."""
    if model is None:
        return True  # conservative: assume yes
    if model in _DRYER_PRODUCT_IDS:
        return False
    if model in _M1_SERIES | _MUSE_SERIES | _METIS_SERIES:
        return False
    return True


def supports_feature_bits(model: str | None) -> bool:
    """Older entry-level devices (H1 a63, H1 Lite a90) lack DP 237."""
    if model is None:
        return True  # conservative: assume yes
    return model not in _UNSUPPORTED_FEATURE_BITS


def supports_remote_control(model: str | None) -> bool:
    """Remote control (DP 232) is supported on all overseas models."""
    if model is None:
        return False
    return model in _OVERSEAS_PRODUCT_IDS


def supports_soak(model: str | None) -> bool:
    """Soak (DP 233) is supported on M1 / Muse / Hyperion / Poseidon / Halia / Hera / Pandora."""
    if model is None:
        return False
    return model in (
        _M1_SERIES | _MUSE_SERIES | _HYPERION_SERIES | _POSEIDON_SERIES | _HALIA_SERIES | _HERA_SERIES | _PANDORA_SERIES
    )


def supports_smart_clean(model: str | None) -> bool:
    """Smart-clean (DP 239) is supported on M1 / Muse / Hyperion / Apollo / Halia / Hera."""
    if model is None:
        return False
    return model in (_M1_SERIES | _MUSE_SERIES | _HYPERION_SERIES | _APOLLO_SERIES | _HALIA_SERIES | _HERA_SERIES)


def build_force_load_dp_list(model: str | None) -> list[RoborockZeoProtocol]:
    """Return the complete DP list for ``_force_load()``."""
    if is_dryer(model):
        base = list(_FORCE_LOAD_BASE_DRYER)
    else:
        base = list(_FORCE_LOAD_BASE_WASHER)

    # ── Softener block (212, 214, 225, 227) ──
    if has_softener_compartment(model):
        base.extend(
            [
                RoborockZeoProtocol.SOFTENER_SET,  # 212
                RoborockZeoProtocol.SOFTENER_TYPE,  # 214
                RoborockZeoProtocol.DEFAULT_SETTING,  # 225
                RoborockZeoProtocol.SOFTENER_EMPTY,  # 227
            ]
        )

    # ── Feature-bits-gated DPs (queried immediately, not deferred) ──
    if supports_feature_bits(model):
        # These are always appended when FEATURE_BITS is supported.
        # The actual bitmask is checked later in loadFeatureDps() for
        # feature-gated sub-queries, but Bundle appends these upfront.
        pass  # DP 237 is already in the base list.

    # ── Soak ──
    if supports_soak(model):
        base.append(RoborockZeoProtocol.SOAK)  # 233

    # ── Smart Clean ──
    if supports_smart_clean(model):
        base.append(RoborockZeoProtocol.CUSTOM_PROGRAM_CLEANING_TIME)  # 239

    # ── Remote control (overseas-only) ──
    if supports_remote_control(model):
        base.append(RoborockZeoProtocol.APP_AUTHORIZATION)  # 232

    # ── Strip unsupported FEATURE_BITS ──
    if not supports_feature_bits(model):
        base = [dp for dp in base if dp != RoborockZeoProtocol.FEATURE_BITS]

    return base
