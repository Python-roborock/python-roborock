from __future__ import annotations

from roborock.data.zeo.zeo_code_mappings import ZeoFeatureBits
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

# Series that support UV light (DP 228).
_UV_LIGHT_SERIES: frozenset[str] = (
    _H1_LITE_SERIES  # a90, a91, a237
    | _M1_SERIES  # a92, a93, a133, a162, a233, a234, a218, a213, a276, a277
    | _MUSE_SERIES  # a142, a215, a211
    | _METIS_SERIES  # a154, a214
    | _HYPERION_SERIES  # a141, a149, a207, a230
    | _POSEIDON_SERIES  # a180, a181, a201, a255
    | _APOLLO_SERIES  # cd.a188, cd.a204, cd.a258, cd.a265
    | _HALIA_SERIES  # a240, a241
    | _HERA_SERIES  # a227, a261, a268, a269, a273
    | _PANDORA_SERIES  # a239, a262, a270, a271, a272
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

    # ── Smart-hosting DPs (always queried when FEATURE_BITS is supported) ──
    if supports_feature_bits(model):
        base.extend(
            [
                RoborockZeoProtocol.SMART_HOSTING,  # 235
                RoborockZeoProtocol.SMART_HOSTING_TIME,  # 236
                RoborockZeoProtocol.SMART_HOSTING_WAITED_TIME,  # 238
            ]
        )

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


# ── Feature-gated DP mapping (matches Bundle's loadFeatureDps()) ─────────
#
# Each entry maps a ZeoFeatureBits flag to the DPs that should only be
# queried when that feature bit is set in DP 237 (FEATURE_BITS).

_FEATURE_DP_MAP: dict[ZeoFeatureBits, list[RoborockZeoProtocol]] = {
    ZeoFeatureBits.silent_mode: [
        RoborockZeoProtocol.SILENT_MODE_ON,  # 240
        RoborockZeoProtocol.SILENT_MODE_START_TIME,  # 241
        RoborockZeoProtocol.SILENT_MODE_END_TIME,  # 242
    ],
    ZeoFeatureBits.dry_care: [
        RoborockZeoProtocol.DRY_CARE_MODE,  # 244
    ],
    ZeoFeatureBits.expand_softener: [
        RoborockZeoProtocol.SOFTENER_EXPANSION_TYPE,  # 245
    ],
    ZeoFeatureBits.wool_detergent: [
        RoborockZeoProtocol.SOFTENER_EXPANSION_TYPE,  # 245
    ],
    ZeoFeatureBits.smile_light: [
        RoborockZeoProtocol.SMILE_LIGHT_STATUS,  # 247
    ],
    ZeoFeatureBits.concentrated_detergent: [
        RoborockZeoProtocol.DETERGENT_EXPANSION_TYPE,  # 248
    ],
    ZeoFeatureBits.voice_assistant: [
        RoborockZeoProtocol.VOICE_SWITCH,  # 10301
        RoborockZeoProtocol.VOICE_VOLUME,  # 10009
        RoborockZeoProtocol.VOICE_RECORD_INFO,  # 10302
        RoborockZeoProtocol.VOICE_RECORD,  # 10303
        RoborockZeoProtocol.SND_STATE,  # 10004
    ],
    ZeoFeatureBits.fluff_clean_notification: [
        RoborockZeoProtocol.IS_NEED_FLUFF_CLEAN,  # 250
    ],
    ZeoFeatureBits.power_button_indicator_light: [
        RoborockZeoProtocol.POWER_LIGHT,  # 251
    ],
    ZeoFeatureBits.dirt_detection: [
        RoborockZeoProtocol.DIRT_DETECTION_SWITCH,  # 215
        RoborockZeoProtocol.DIRT_DETECTION_STATUS,  # 216
    ],
    ZeoFeatureBits.steam_care: [
        RoborockZeoProtocol.STEAM_VOLUME,  # 257
        RoborockZeoProtocol.STEAM_CARE_TIME,  # 261
    ],
    ZeoFeatureBits.wash_dry_linkage: [
        RoborockZeoProtocol.WASH_DRY_LINKED,  # 255
        RoborockZeoProtocol.DEVICE_BOUND,  # 262
        RoborockZeoProtocol.CLOTH_PUT_IN,  # 263
        RoborockZeoProtocol.CLOTH_READY_TO_DRY_COUNT_DOWN,  # 264
        RoborockZeoProtocol.START_DRYER_ERROR,  # 265
    ],
    ZeoFeatureBits.save_panel_program_params: [
        RoborockZeoProtocol.WIFI_LINKAGE_RESET,  # 266
    ],
}


def build_feature_dp_list(feature_bits: int) -> list[RoborockZeoProtocol]:
    """Return the DPs gated behind feature bits enabled in *feature_bits*."""
    dps: list[RoborockZeoProtocol] = []
    for feature, feature_dps in _FEATURE_DP_MAP.items():
        if feature_bits & (1 << feature.value):
            dps.extend(feature_dps)
    # De-duplicate while preserving order (expand_softener and wool_detergent
    # both map to SOFTENER_EXPANSION_TYPE).
    seen: set[RoborockZeoProtocol] = set()
    unique_dps: list[RoborockZeoProtocol] = []
    for dp in dps:
        if dp not in seen:
            seen.add(dp)
            unique_dps.append(dp)
    return unique_dps


def supports_uv_light(model: str | None) -> bool:
    """Return True if *model* supports UV light (DP 228)."""
    if model is None:
        return False
    return model in _UV_LIGHT_SERIES
