#!/usr/bin/env python3
"""Build research/amm-claim-token-incentives-tf-chains-20261029 receipts.

3rd run packet #21: claim_token_incentives under a Token-2022
transfer fee on the incentive mint, chained into sweep -> collect.

The gap: 2nd #48 proved no trade path ever writes
current_sol_volume (track_volume is event-only), 2nd #4 pinned
claim_token_incentives rewards from externally seeded volume, and
3rd #4/#10/#12 chained trades into sweep -> collect -- but nobody
chained a real trade INTO the token-incentive claim and then into
the fee pipes in one VM. The sharp questions: does a fresh trade's
volume accumulator feed the token claim at all, does a seeded
token claim change the fee buckets, does the claim's reward math
survive interleaved trades and sweeps, and do the cashback and
token-incentive claims share any field? All three images agree:
- A fresh v2/legacy trade creates a zeroed accumulator, so the
  token claim after it is a zero claim ("No tokens to claim", 0
  events, payer -5,000 only) that stamps last_update_timestamp
  0 -> 21 and leaves the fee buckets untouched; the following
  sweep/collect drain the full bucket.
- A seeded accumulator (unclaimed 111, claimed 222, volume
  333444, last 20) claims 3,334,551 = 111 + 333444*1000/100
  whether the claim runs before, between, or after the trade and
  the sweep/collect -- the token pipe and the fee pipes are fully
  independent, and a second claim is a zero claim (volume 0,
  unclaimed 0, last stays 21).
- Cashback and token claims touch disjoint fields: a cashback
  buy's earned 5,475 survives a token claim untouched, and a
  token claim's claimed/unclaimed survive a cashback claim; the
  two claims plus the collect conserve the non-cashback total
  128,869 exactly (5,475 + 123,394, or 548 + 123,394 on sells).
- Failure isolation: a token claim that fails (missing global
  accumulator -> 3012, short vault -> Token custom 1) rolls back
  fully and the following trade -> sweep -> collect still drains
  the full bucket; a missing user incentive ATA is created by
  init_if_needed (payer -2,044,280) and the claim lands.
"""
import base64
import copy
import gzip
import hashlib
import json
import struct
import sys
from pathlib import Path

import os
sys.path.insert(0, str(Path.home() / "workspace/pumpfun-sparse/scripts"))
os.chdir(Path.home() / "workspace/pumpfun-sparse")
from solders.account import Account
from solders.clock import Clock
from solders.instruction import AccountMeta, Instruction
from solders.pubkey import Pubkey
from solders.transaction import Transaction
from solders.transaction_metadata import FailedTransactionMetadata

from pump_amm_admin_differential import Harness
from pump_amm_liquidity_differential import (
    CONFIG, CONFIG_KEY, EVENT, IDL, PAYER, PROGRAM, RAW, TOKEN, TOKEN22,
    base, f, lp, pool, poolraw, quote, supply, token,
    userbase, userlp, userquote, vaultbase, vaultquote,
)
from pump_amm_trade_v2_differential import FEES, buyback, feeconfig, volume
from pump_amm_legacy_buy_differential import uvata

ROOT = Path.home() / "workspace/pumpfun-sparse"
OUT = ROOT / "research/amm-claim-token-incentives-tf-chains-20261029"
WS = Path.home() / "workspace/slop-verify"
IMAGES = {
    "original": ROOT / "evidence/original/pump_amm/deployed.so",
    "control": WS / "control.so",
    "candidate": WS / "candidate.so",
}
IMAGE_SHA = {k: hashlib.sha256(v.read_bytes()).hexdigest() for k, v in IMAGES.items()}

ATA_PROG = Pubkey.from_string('ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL')
PAYER_KEY = PAYER.pubkey()
CREATOR = Pubkey.from_bytes(bytes(poolraw[211:243]))
CREATOR_VAULT, _ = Pubkey.find_program_address([b'creator_vault', bytes(CREATOR)], PROGRAM)
CREATOR_ATA, _ = Pubkey.find_program_address([bytes(CREATOR_VAULT), bytes(TOKEN), bytes(quote)], ATA_PROG)
PROTOCOL = Pubkey.from_bytes(bytes(RAW[57:89]))
PROTOCOL_ATA, _ = Pubkey.find_program_address([bytes(PROTOCOL), bytes(TOKEN), bytes(quote)], ATA_PROG)
DEST = Pubkey.from_bytes(bytes([94]) * 32)
GVOL = Pubkey.find_program_address([b'global_volume_accumulator'], PROGRAM)[0]
GDISC = bytes(next(x for x in IDL['accounts'] if x['name'] == 'GlobalVolumeAccumulator')['discriminator'])
UVA_DISC = bytes(next(x for x in IDL['accounts'] if x['name'] == 'UserVolumeAccumulator')['discriminator'])
POOLV2 = Pubkey.find_program_address([b'pool-v2', bytes(base)], PROGRAM)[0]
BB_OWNER = Pubkey.from_bytes(base64.b64decode(f['accounts']['buyback_fee_recipient']['data_base64'])[32:64])
VQ0, PF0, CF0 = -125882, 2488, 123394
S_ASIS = 4194352106721

IMINT = Pubkey.from_bytes(bytes([226]) * 32)
GA_ATA, _ = Pubkey.find_program_address([bytes(GVOL), bytes(TOKEN22), bytes(IMINT)], ATA_PROG)
UA_ATA, _ = Pubkey.find_program_address([bytes(PAYER_KEY), bytes(TOKEN22), bytes(IMINT)], ATA_PROG)
GA_TOK, _ = Pubkey.find_program_address([bytes(GVOL), bytes(TOKEN), bytes(IMINT)], ATA_PROG)
UA_TOK, _ = Pubkey.find_program_address([bytes(PAYER_KEY), bytes(TOKEN), bytes(IMINT)], ATA_PROG)

SWP_KEYS_P = [PAYER_KEY, CONFIG_KEY, pool, quote, TOKEN, vaultquote, PROTOCOL, PROTOCOL_ATA,
              Pubkey.default(), ATA_PROG, EVENT, PROGRAM]
SWP_KEYS_C = [PAYER_KEY, CONFIG_KEY, pool, quote, TOKEN, vaultquote, CREATOR_VAULT, CREATOR_ATA,
              Pubkey.default(), ATA_PROG, EVENT, PROGRAM]
COL_KEYS = [quote, TOKEN, CREATOR, CREATOR_VAULT, CREATOR_ATA, DEST, EVENT, PROGRAM]
CLAIM_KEYS = [PAYER_KEY, volume, quote, TOKEN, uvata, userquote, Pubkey.default(), EVENT, PROGRAM]
LEG_KEYS = [pool, PAYER_KEY, CONFIG_KEY, base, quote, userbase, userquote, vaultbase, vaultquote,
            PROTOCOL, PROTOCOL_ATA, TOKEN, TOKEN, Pubkey.default(), ATA_PROG, EVENT, PROGRAM,
            CREATOR_ATA, CREATOR_VAULT, feeconfig, FEES]
LEG_REM = [AccountMeta(POOLV2, False, False), AccountMeta(BB_OWNER, False, False),
           AccountMeta(buyback, False, True)]
LEG_CB_REM = [AccountMeta(uvata, False, True), AccountMeta(volume, False, True),
              AccountMeta(POOLV2, False, False), AccountMeta(BB_OWNER, False, False),
              AccountMeta(buyback, False, True)]
BUY_KEYS = [pool, PAYER_KEY, CONFIG_KEY, base, quote, userbase, userquote, vaultbase, vaultquote,
            PROTOCOL, PROTOCOL_ATA, TOKEN, TOKEN, Pubkey.default(), ATA_PROG, EVENT, PROGRAM,
            CREATOR_ATA, CREATOR_VAULT, GVOL, volume, feeconfig, FEES]
BUY_REM_STD = [AccountMeta(POOLV2, False, False), AccountMeta(BB_OWNER, False, False),
               AccountMeta(buyback, False, True)]
BUY_REM_CB = [AccountMeta(uvata, False, True), AccountMeta(POOLV2, False, False),
              AccountMeta(BB_OWNER, False, False), AccountMeta(buyback, False, True)]
V2_KEYS = [pool, PAYER_KEY, CONFIG_KEY, base, quote, userbase, userquote, vaultbase, vaultquote,
           TOKEN, TOKEN, Pubkey.default(), volume, feeconfig, buyback, EVENT, PROGRAM]
TCLAIM_KEYS = [PAYER_KEY, UA_ATA, GVOL, GA_ATA, volume, IMINT, TOKEN22,
               Pubkey.default(), ATA_PROG, EVENT, PROGRAM, PAYER_KEY]
TCLAIM_KEYS_2023 = [PAYER_KEY, UA_ATA, GVOL, GA_ATA, volume, IMINT, TOKEN,
               Pubkey.default(), ATA_PROG, EVENT, PROGRAM, PAYER_KEY]
TCLAIM_KEYS_3014 = [PAYER_KEY, UA_TOK, GVOL, GA_TOK, volume, IMINT, TOKEN22,
               Pubkey.default(), ATA_PROG, EVENT, PROGRAM, PAYER_KEY]
WATCH = [PAYER_KEY, pool, base, quote, lp, userbase, userquote, userlp,
         vaultbase, vaultquote, buyback, volume, feeconfig, CONFIG_KEY,
         PROTOCOL_ATA, CREATOR_ATA, DEST, uvata, GVOL, IMINT, GA_ATA, UA_ATA]
ROLE_KEY = {"userbase": userbase, "userquote": userquote, "userlp": userlp,
            "vaultbase": vaultbase, "vaultquote": vaultquote, "buyback": buyback,
            "protoata": PROTOCOL_ATA, "creatorata": CREATOR_ATA, "dest": DEST,
            "uvata": uvata, "gata": GA_ATA, "uata": UA_ATA}
SWP_DISC = "82a42461e48287a5"
SELL_DISC = "3e2f370aa503dc2a"
COL_DISC = "e8f5c2eeeada3a59"
CLAIM_DISC = hashlib.sha256(b"event:ClaimCashbackEvent").digest()[:8].hex()
TCLAIM_DISC = hashlib.sha256(b"event:ClaimTokenIncentivesEvent").digest()[:8].hex()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def tok_data(owner, amount):
    d = bytearray(165)
    d[:32] = bytes(IMINT)
    d[32:64] = bytes(owner)
    struct.pack_into('<Q', d, 64, amount)
    d[108] = 1
    return bytes(d)


def t22acct(mint, owner, amount, withheld=0):
    data = bytearray(165)
    data[0:32] = bytes(mint)
    data[32:64] = bytes(owner)
    struct.pack_into("<Q", data, 64, amount)
    data[108] = 1
    return bytes(data) + bytes([2]) + struct.pack("<HH", 7, 0) + struct.pack("<HHQ", 2, 8, withheld)


def tf_mint_data(base82, bps, maxfee=2**64 - 1):
    d = bytearray(base82)
    d += bytes(83) + bytes([1])
    conf = bytes(72) + struct.pack('<QQH', 0, maxfee, bps) * 2
    d += struct.pack('<HH', 1, len(conf)) + conf
    return bytes(d)


def setup_vm(binary, case):
    # mode: "std" | "cb-present"; uva_seed overrides the volume account;
    # gva False -> global accumulator missing; uata False -> user ATA missing.
    h = Harness(binary)
    vm = h.vm
    vm.set_clock(Clock(100, 1234567890, 0, 0, 1234567890))
    for pid, p in [(TOKEN, "evidence/dependencies/spl_token/deployed.so"),
                   (TOKEN22, "evidence/dependencies/spl_token_2022/deployed.so"),
                   (FEES, "evidence/original/pump_fees/deployed.so"),
                   (ATA_PROG, "evidence/dependencies/associated_token/deployed.so")]:
        vm.add_program_from_file(pid, ROOT / p)
    glob = bytearray(RAW)
    glob[56] = 0
    vm.set_account(CONFIG_KEY, Account(CONFIG["lamports"], bytes(glob), PROGRAM))
    for n, row in f["accounts"].items():
        vm.set_account(Pubkey.from_string(row["address"]),
                       Account(row["lamports"], base64.b64decode(row["data_base64"]),
                               Pubkey.from_string(row["owner"])))
    pd = bytearray(poolraw)
    if case["mode"] == "cb-present":
        pd[244] = 1
    vm.set_account(pool, Account(f["accounts"]["pool"]["lamports"], bytes(pd), PROGRAM))
    mint = struct.pack("<I", 1) + bytes(pool) + struct.pack("<Q", supply) + bytes([9, 1]) + bytes(36)
    vm.set_account(lp, Account(10**9, mint, TOKEN22))
    vm.set_account(userbase, Account(10**9, token(base, PAYER_KEY, 10**15, False), TOKEN))
    vm.set_account(userquote, Account(10**15 + 2039280, token(quote, PAYER_KEY, 10**15, True), TOKEN))
    vm.set_account(userlp, Account(10**9, token(lp, PAYER_KEY, supply // 2, False), TOKEN22))
    vm.set_account(PROTOCOL_ATA, Account(10**15 + 2039280, token(quote, PROTOCOL, 0, True), TOKEN))
    vm.set_account(CREATOR_ATA, Account(10**9, token(quote, CREATOR_VAULT, 0, True), TOKEN))
    vm.set_account(PROTOCOL, Account(10**9, b'', Pubkey.default()))
    vm.set_account(CREATOR_VAULT, Account(10**9, b'', Pubkey.default()))
    vm.set_account(POOLV2, Account(10**9, b'', Pubkey.default()))
    vm.set_account(BB_OWNER, Account(10**9, b'', Pubkey.default()))
    vm.set_account(DEST, Account(2039280, token(quote, CREATOR, 0, True), TOKEN))
    if case.get("gva", True):
        g = GDISC + struct.pack('<qqq', 20, 49, 1) + bytes(IMINT) \
            + struct.pack('<30Q', *([1000] * 30)) + struct.pack('<30Q', *([100] * 30))
        vm.set_account(GVOL, Account(10**9, g.ljust(600, b'\0'), PROGRAM))
    else:
        vm.set_account(GVOL, Account(0, b'', Pubkey.default()))
    bps = case.get("bps", 100)
    base82 = struct.pack('<I', 0) + bytes(32) + struct.pack('<Q', 10**12) + bytes([6, 1]) + bytes(36)
    vm.set_account(IMINT, Account(10**9, tf_mint_data(base82, bps, case.get("maxfee", 2**64 - 1)), TOKEN22))
    vm.set_account(GA_ATA, Account(10**9, t22acct(IMINT, GVOL, case.get("vault", 10**9)), TOKEN22))
    vm.set_account(UA_ATA, Account(10**9, t22acct(IMINT, PAYER_KEY, case.get("uata_amt", 17),
                                               case.get("uata_wh", 0)), TOKEN22))
    # TOKEN-program-derived ATA addresses, but owned by Token-2022:
    # the Anchor ATA check then fails on derivation (3014), not on the
    # token-program constraint (2023). This mirrors the probe exactly.
    vm.set_account(GA_TOK, Account(10**9, t22acct(IMINT, GVOL, case.get("vault", 10**9)), TOKEN22))
    vm.set_account(UA_TOK, Account(10**9, t22acct(IMINT, PAYER_KEY, 17), TOKEN22))
    if case["mode"] == "cb-present":
        vm.set_account(uvata, Account(2039280, token(quote, volume, 0, True), TOKEN))
    if case.get("uva_seed") is not None:
        raw = UVA_DISC + bytes(PAYER_KEY) + struct.pack('<BQQQqBQQ', *case["uva_seed"])
        vm.set_account(volume, Account(10**9, raw.ljust(137, b'\0'), PROGRAM))
    elif case["mode"] in ("cb-present", "uva-present"):
        vm.set_account(volume, Account(10**9, UVA_DISC + bytes(PAYER_KEY) + bytes(97), PROGRAM))
    else:
        vm.set_account(volume, Account(0, b"", Pubkey.default()))
    return h


def snap(vm):
    out = {}
    for k in WATCH:
        a = vm.get_account(k)
        out[str(k)] = None if a is None else {
            "lamports": a.lamports, "owner": str(a.owner),
            "data_hex": bytes(a.data).hex()}
    return out


def tok_amount(entry):
    if entry is None:
        return None
    raw = bytes.fromhex(entry["data_hex"])
    return struct.unpack_from("<Q", raw, 64)[0] if len(raw) >= 72 else None


def tok_delta(rec, key):
    b = rec["before"][str(key)]
    a = rec["after"][str(key)]
    return (tok_amount(a) or 0) - (tok_amount(b) or 0)


def tok_withheld(entry):
    if entry is None:
        return None
    raw = bytes.fromhex(entry["data_hex"])
    if len(raw) >= 182:
        return struct.unpack_from("<Q", raw, 174)[0]
    if len(raw) >= 178:
        return struct.unpack_from("<Q", raw, 170)[0]
    return None


def lam_delta(rec, key):
    b = rec["before"][str(key)]
    a = rec["after"][str(key)]
    return (a["lamports"] if a else 0) - (b["lamports"] if b else 0)


def pool_state(entry):
    d = bytes.fromhex(entry["data_hex"])
    return (int.from_bytes(d[245:261], "little", signed=True),
            struct.unpack_from("<Q", d, 271)[0],
            struct.unpack_from("<Q", d, 279)[0],
            struct.unpack_from("<Q", d, 203)[0])


def vol_state(entry):
    if entry is None:
        return None
    raw = bytes.fromhex(entry["data_hex"])
    return {"lamports": entry["lamports"], "len": len(raw),
            "user": raw[8:40].hex()}


def uva_fields(entry):
    if entry is None:
        return None
    raw = bytes.fromhex(entry["data_hex"])
    if len(raw) < 90:
        return {"len": len(raw)}
    needs, unc, cla, vol, last, hasc, earn, cbcl = struct.unpack_from('<BQQQqBQQ', raw, 40)
    return {"needs": needs, "unclaimed": unc, "claimed": cla, "volume": vol,
            "last": last, "has": hasc, "earned": earn, "cb_claimed": cbcl}


def ev_data(logs):
    lines = [l for l in logs if l.startswith("Program data: ")]
    if len(lines) != 1:
        return None
    return base64.b64decode(lines[0].split("Program data: ", 1)[1].strip())


def u64(raw, off):
    return struct.unpack_from("<Q", raw, off)[0]


def decode_event(kind, rec):
    raw = ev_data(rec["logs"])
    if raw is None:
        return None
    if kind in ("vbuy", "vsell", "vexact"):
        return {"disc": raw[:8].hex(), "len": len(raw),
                "out": u64(raw, 16), "max": u64(raw, 24),
                "curve": u64(raw, 64), "lp_bps": u64(raw, 72),
                "lp_fee": u64(raw, 80), "proto_bps": u64(raw, 88),
                "proto_fee": u64(raw, 96), "quote": u64(raw, 104),
                "uout": u64(raw, 112)}
    if kind == "tclaim":
        return {"disc": raw[:8].hex(), "len": len(raw),
                "user": raw[8:40].hex(), "mint": raw[40:72].hex(),
                "amount": u64(raw, 72), "ts": struct.unpack_from("<q", raw, 80)[0],
                "total_claimed": u64(raw, 88), "current_sol_volume": u64(raw, 96)}
    if kind in ("buy", "exact"):
        ev = {"disc": raw[:8].hex(), "len": len(raw),
              "out": u64(raw, 16), "max": u64(raw, 24),
              "curve": u64(raw, 64), "lp_bps": u64(raw, 72),
              "lp_fee": u64(raw, 80), "proto_bps": u64(raw, 88),
              "proto_fee": u64(raw, 96), "quote": u64(raw, 104),
              "uout": u64(raw, 112),
              "creator_bps": u64(raw, 344), "creator_fee": u64(raw, 352),
              "track": raw[360]}
        if len(raw) == 497:
            ev.update({"cb_bps": u64(raw, 408), "cb": u64(raw, 416),
                       "bb_bps": u64(raw, 424), "bb": u64(raw, 432)})
        else:
            ev.update({"cb_bps": u64(raw, 423), "cb": u64(raw, 431),
                       "bb_bps": u64(raw, 439), "bb": u64(raw, 447)})
        return ev
    if kind in ("lsell",):
        return {"disc": raw[:8].hex(), "len": len(raw),
                "curve": u64(raw, 64), "lp_fee": u64(raw, 80),
                "proto_fee": u64(raw, 96), "quote": u64(raw, 104),
                "uout": u64(raw, 112)}
    if kind in ("cbsell",):
        return {"disc": raw[:8].hex(), "len": len(raw),
                "curve": u64(raw, 64), "lp_fee": u64(raw, 80),
                "protocol_fee": u64(raw, 96), "quote": u64(raw, 104),
                "user_out": u64(raw, 112),
                "creator_bps": u64(raw, 344), "creator_fee": u64(raw, 352),
                "cashback_bps": u64(raw, 360), "cashback": u64(raw, 368),
                "buyback_fee": u64(raw, 384)}
    if kind in ("swp", "swc"):
        return {"disc": raw[:8].hex(), "len": len(raw),
                "timestamp": struct.unpack_from("<q", raw, 8)[0],
                "recipient": raw[112:144].hex(),
                "amount": u64(raw, 176), "bucket": raw[184]}
    if kind == "col":
        return {"disc": raw[:8].hex(), "len": len(raw),
                "timestamp": struct.unpack_from("<q", raw, 8)[0],
                "creator": raw[16:48].hex(), "fee": u64(raw, 48),
                "vault_ata": raw[56:88].hex(), "dest": raw[88:120].hex()}
    if kind == "claim":
        return {"disc": raw[:8].hex(), "len": len(raw),
                "user": raw[8:40].hex(), "amount": u64(raw, 40),
                "ts": struct.unpack_from("<q", raw, 48)[0],
                "total_claimed": u64(raw, 56), "total_earned": u64(raw, 64)}
    return None


def check(cond, msg):
    if not cond:
        raise AssertionError(msg)


def disc(name):
    return bytes(next(x for x in IDL["instructions"] if x["name"] == name)["discriminator"])


def do_step(h, kind, args):
    if kind == "swp":
        name, keys, data, rem = "sweep_protocol_fee", SWP_KEYS_P, disc("sweep_protocol_fee"), []
    elif kind == "swc":
        name, keys, data, rem = "sweep_creator_fee", SWP_KEYS_C, disc("sweep_creator_fee"), []
    elif kind == "col":
        name, keys, data, rem = "collect_coin_creator_fee", COL_KEYS, disc("collect_coin_creator_fee"), []
    elif kind == "claim":
        name, keys, data, rem = "claim_cashback", CLAIM_KEYS, disc("claim_cashback"), []
    elif kind == "tclaim":
        name, keys, data, rem = "claim_token_incentives", TCLAIM_KEYS, disc("claim_token_incentives"), []
    elif kind == "tclaim2023":
        name, keys, data, rem = "claim_token_incentives", TCLAIM_KEYS_2023, disc("claim_token_incentives"), []
    elif kind == "tclaim3014":
        name, keys, data, rem = "claim_token_incentives", TCLAIM_KEYS_3014, disc("claim_token_incentives"), []
    elif kind == "lsell":
        name, keys, data, rem = "sell", LEG_KEYS, disc("sell") + struct.pack("<QQ", args[0], args[1] if len(args) > 1 else 0), LEG_REM
    elif kind == "cbsell":
        name, keys, data, rem = "sell", LEG_KEYS, disc("sell") + struct.pack("<QQ", args[0], args[1] if len(args) > 1 else 0), LEG_CB_REM
    elif kind == "buy":
        name, keys, data, rem = "buy", BUY_KEYS, disc("buy") + struct.pack("<QQ", args[0], args[1]) + b"\0", BUY_REM_STD
    elif kind == "cbbuy":
        name, keys, data, rem = "buy", BUY_KEYS, disc("buy") + struct.pack("<QQ", args[0], args[1]) + b"\0", BUY_REM_CB
    elif kind == "vbuy":
        name, keys, data, rem = "buy_v2", V2_KEYS, disc("buy_v2") + struct.pack("<QQ", args[0], args[1]), []
    elif kind == "vsell":
        name, keys, data, rem = "sell_v2", V2_KEYS, disc("sell_v2") + struct.pack("<QQ", args[0], args[1]), []
    elif kind == "vexact":
        name, keys, data, rem = "buy_exact_quote_in_v2", V2_KEYS, disc("buy_exact_quote_in_v2") + struct.pack("<QQ", args[0], args[1]), []
    else:
        raise ValueError(kind)
    if kind in ("tclaim", "tclaim2023", "tclaim3014"):
        h.vm.set_clock(Clock(100, 0, 0, 0, 21))
    else:
        h.vm.set_clock(Clock(100, 1234567890, 0, 0, 1234567890))
    ix = next(x for x in IDL["instructions"] if x["name"] == name)
    metas = [AccountMeta(k, bool(a.get("signer")), bool(a.get("writable")))
             for k, a in zip(keys, ix["accounts"])] + list(rem)
    tx = Transaction.new_signed_with_payer(
        [Instruction(PROGRAM, data, metas)], PAYER_KEY, [PAYER], h.vm.latest_blockhash())
    assert tx.verify_with_results() and all(tx.verify_with_results())
    before = snap(h.vm)
    r = h.vm.send_transaction(tx)
    failed = isinstance(r, FailedTransactionMetadata)
    meta = r.meta() if failed else r
    logs = meta.logs()
    return {"transaction_base64": base64.b64encode(bytes(tx)).decode(),
            "error": str(r.err()) if failed else None, "logs": logs,
            "events": [l for l in logs if l.startswith("Program data: ")],
            "before": before, "after": snap(h.vm),
            "site": next((l for l in logs if "thrown in" in l or "caused by account" in l), None)}


def E(dPAYER, deltas, pool_after, volume, event=None, events=1, error=None,
      rollback=False, site_fragment=None, log_fragment=None, absent=None, lam_after=None,
      uva=None, withheld=None):
    return {"dPAYER": dPAYER, "deltas": deltas, "pool_after": list(pool_after),
            "volume": volume, "event": event, "events": events, "error": error,
            "rollback": rollback, "site_fragment": site_fragment,
            "log_fragment": log_fragment, "absent": absent or [],
            "lam_after": lam_after or {}, "uva": uva, "withheld": withheld or {}}


def P(vq, pf, cf, sup=S_ASIS):
    return [vq, pf, cf, sup]


POOL_ASIS = P(VQ0, PF0, CF0)
POOL_VBUY = P(-139844, 10975, 128869)
POOL_VBUY_SWC = P(-10975, 10975, 0)
POOL_VSELL = P(-139843, 10974, 128869)
POOL_VSELL_SWC = P(-10974, 10974, 0)
POOL_VEXACT = P(-201438, 48414, 153024)
POOL_VEXACT_SWC = P(-48414, 48414, 0)
POOL_SWC = P(-2488, PF0, 0)
VOL_FRESH = {"lamports": 1844400, "len": 137, "user": bytes(PAYER_KEY).hex()}
VOL_SEED = {"lamports": 10**9, "len": 137, "user": bytes(PAYER_KEY).hex()}
UVA_ZERO = {"needs": 0, "unclaimed": 0, "claimed": 0, "volume": 0,
            "last": 0, "has": 0, "earned": 0, "cb_claimed": 0}
UVA_ZERO_CLAIMED = dict(UVA_ZERO, last=21)
UVA_SEED = {"needs": 1, "unclaimed": 111, "claimed": 222, "volume": 333444,
            "last": 20, "has": 1, "earned": 555, "cb_claimed": 666}
UVA_SEED_CLAIMED = {"needs": 0, "unclaimed": 0, "claimed": 3334773, "volume": 0,
                    "last": 21, "has": 1, "earned": 555, "cb_claimed": 666}
UVA_SMALL = {"needs": 1, "unclaimed": 111, "claimed": 222, "volume": 0,
             "last": 20, "has": 1, "earned": 0, "cb_claimed": 0}
UVA_SMALL_CLAIMED = {"needs": 0, "unclaimed": 0, "claimed": 333, "volume": 0,
                     "last": 21, "has": 1, "earned": 0, "cb_claimed": 0}
UVA_CB = dict(UVA_ZERO)
UVA_CB_EARNED = dict(UVA_ZERO, earned=5475)
UVA_CB_EARNED_CLAIMED = dict(UVA_ZERO, earned=5475, cb_claimed=5475)
UVA_CB_EARNED_TSTAMP = dict(UVA_CB_EARNED, last=21)
UVA_CB_CLAIMED_TSTAMP = dict(UVA_CB_EARNED_CLAIMED, last=21)
UVA_CBSELL = dict(UVA_ZERO, earned=548)
UVA_CBSELL_TSTAMP = dict(UVA_CBSELL, last=21)
UVA_CBSELL_CLAIMED = dict(UVA_ZERO, earned=548, cb_claimed=548)
UVA_CBSELL_CLAIMED_TSTAMP = dict(UVA_CBSELL_CLAIMED, last=21)


def SWP_EV(amount, bucket, recipient):
    return {"disc": SWP_DISC, "len": 185, "timestamp": 1234567890,
            "recipient": bytes(recipient).hex(), "amount": amount, "bucket": bucket}


def COL_EV(fee):
    return {"disc": COL_DISC, "len": 120, "timestamp": 1234567890,
            "creator": bytes(CREATOR).hex(), "fee": fee,
            "vault_ata": bytes(CREATOR_ATA).hex(), "dest": bytes(DEST).hex()}


def VBUY_EV():
    return {"disc": "67f4521f2cf57777", "len": 500, "out": 10**10, "max": 10**12,
            "curve": 1824983, "lp_bps": 2, "lp_fee": 365, "proto_bps": 93,
            "proto_fee": 16973, "quote": 1825348, "uout": 1847796}


def VSELL_EV():
    return {"disc": SELL_DISC, "len": 449, "out": 10**10, "max": 1,
            "curve": 1824927, "lp_bps": 2, "lp_fee": 365, "proto_bps": 93,
            "proto_fee": 16972, "quote": 1824562, "uout": 1802115}


def VEXACT_EV():
    return {"disc": "67f4521f2cf57777", "len": 515, "out": 54115018303, "max": 10**7,
            "curve": 10**7, "lp_bps": 2, "lp_fee": 1976, "proto_bps": 93,
            "proto_fee": 91852, "quote": 9878518, "uout": 9876542}


def TCLAIM_EV(amount, claimed, vol):
    return {"disc": TCLAIM_DISC, "len": 104, "user": bytes(PAYER_KEY).hex(),
            "mint": bytes(IMINT).hex(), "amount": amount, "ts": 21,
            "total_claimed": claimed, "current_sol_volume": vol}


def CLAIM_EV(amount, claimed, earned):
    return {"disc": CLAIM_DISC, "len": 72, "user": bytes(PAYER_KEY).hex(),
            "amount": amount, "ts": 1234567890,
            "total_claimed": claimed, "total_earned": earned}


def BUY_EV(curve, lp_fee, proto_fee, qwlp, uqin, creator_bps, creator,
           cb_bps, cb, bb, maxv, length=497, out=10**10):
    return {"disc": "67f4521f2cf57777", "len": length, "out": out, "max": maxv,
            "curve": curve, "lp_bps": 2, "lp_fee": lp_fee,
            "proto_bps": 93, "proto_fee": proto_fee, "quote": qwlp,
            "uout": uqin, "creator_bps": creator_bps, "creator_fee": creator,
            "track": 0, "cb_bps": cb_bps, "cb": cb, "bb_bps": 5000, "bb": bb}


D_VBUY = {"userbase": 10**10, "userquote": -1847796,
          "vaultbase": -10**10, "vaultquote": 1839310, "buyback": 8486}
D_VSELL = {"userbase": -10**10, "userquote": 1802115,
           "vaultbase": 10**10, "vaultquote": -1810601, "buyback": 8486}
D_VEXACT = {"userbase": 54115018303, "userquote": -10000000,
            "vaultbase": -54115018303, "vaultquote": 9954074, "buyback": 45926}
D_LBUY = {"userbase": 10**10, "userquote": -1847796,
          "vaultbase": -10**10, "vaultquote": 1825348,
          "protoata": 8487, "creatorata": 5475, "buyback": 8486}
D_LSELL = {"userbase": -10**9, "userquote": 180212,
           "vaultbase": 10**9, "vaultquote": -182458,
           "protoata": 849, "creatorata": 548, "buyback": 849}
D_CBBUY = {"userbase": 10**10, "userquote": -1847796,
           "vaultbase": -10**10, "vaultquote": 1825348,
           "protoata": 8487, "creatorata": 0, "buyback": 8486, "uvata": 5475}
D_CBSELL = {"userbase": -10**9, "userquote": 180212,
            "vaultbase": 10**9, "vaultquote": -182458,
            "protoata": 849, "creatorata": 0, "buyback": 849, "uvata": 548}
EV_LBUY = BUY_EV(1824983, 365, 16973, 1825348, 1847796, 30, 5475, 0, 0, 8486, 10**12)
EV_CBBUY = BUY_EV(1824983, 365, 16973, 1825348, 1847796, 0, 0, 30, 5475, 8486, 10**12)
EV_LSELL = {"disc": SELL_DISC, "len": 449, "curve": 182495, "lp_fee": 37,
            "proto_fee": 1698, "quote": 182458, "uout": 180212}
EV_CBSELL = {"disc": SELL_DISC, "len": 449, "curve": 182495, "lp_fee": 37,
             "protocol_fee": 1698, "quote": 182458, "user_out": 180212,
             "creator_bps": 0, "creator_fee": 0, "cashback_bps": 30,
             "cashback": 548, "buyback_fee": 849}
SEED = (1, 111, 222, 333444, 20, 1, 555, 666)
SMALL = (1, 111, 222, 0, 20, 1, 0, 0)


def swc_after(pool_after, volume, uva, amount=128869):
    return E(-5000, {"creatorata": amount, "vaultquote": -amount}, pool_after, volume,
             event=SWP_EV(amount, 1, CREATOR_VAULT), uva=uva)


def col_after(fee, pool_after, volume, uva):
    return E(-5000, {"creatorata": -fee, "dest": fee}, pool_after, volume,
             event=COL_EV(fee), uva=uva)


def tclaim_zero(volume, uva):
    return E(-5000, {}, POOL_ASIS, volume, events=0, log_fragment="No tokens to claim",
             uva=uva)


def tclaim_seed(volume, uva):
    return E(-5000, {"gata": -3334551, "uata": 3334551}, POOL_ASIS, volume,
             event=TCLAIM_EV(3334551, 3334773, 0), uva=uva)


def tclaim_small(volume, uva, dpayer=-5000, lam_after=None):
    return E(dpayer, {"gata": -111, "uata": 111}, POOL_ASIS, volume,
             event=TCLAIM_EV(111, 333, 0), uva=uva, lam_after=lam_after or {})


UVA_CBSEED = {"needs": 1, "unclaimed": 111, "claimed": 222, "volume": 333444,
               "last": 20, "has": 1, "earned": 0, "cb_claimed": 0}
UVA_CBSEED_EARNED = dict(UVA_CBSEED, earned=5475)
UVA_CBSEED_TCLAIMED = {"needs": 0, "unclaimed": 0, "claimed": 3334773, "volume": 0,
                       "last": 21, "has": 1, "earned": 5475, "cb_claimed": 0}
UVA_CBSEED_DONE = dict(UVA_CBSEED_TCLAIMED, cb_claimed=5475)
UVA_NEEDS0 = {"needs": 0, "unclaimed": 111, "claimed": 222, "volume": 333444,
              "last": 20, "has": 1, "earned": 0, "cb_claimed": 0}
UVA_NEEDS0_CLAIMED = {"needs": 0, "unclaimed": 0, "claimed": 3334773, "volume": 0,
                      "last": 21, "has": 1, "earned": 0, "cb_claimed": 0}


def tclaim_tf(pool_after, uva, gata, uata, wh_uata, event, wh_gata=0):
    return E(-5000, {"gata": gata, "uata": uata}, pool_after, VOL_SEED,
             event=event, uva=uva, withheld={"gata": wh_gata, "uata": wh_uata})


CASES = [
    # Family A -- tf100 claim anchors
    {"label": "a-claim-tf100", "mode": "std", "uva_seed": SEED,
     "steps": [("tclaim", ())],
     "expect": [tclaim_tf(POOL_ASIS, UVA_SEED_CLAIMED, -3334551, 3301205, 33346,
                          TCLAIM_EV(3334551, 3334773, 0))]},
    {"label": "a-claim-tf100-second", "mode": "std", "uva_seed": SEED,
     "steps": [("tclaim", ()), ("tclaim", ())],
     "expect": [tclaim_tf(POOL_ASIS, UVA_SEED_CLAIMED, -3334551, 3301205, 33346,
                          TCLAIM_EV(3334551, 3334773, 0)),
                E(-5000, {}, POOL_ASIS, VOL_SEED, events=0,
                  log_fragment="No tokens to claim", uva=UVA_SEED_CLAIMED)]},
    {"label": "a-claim-tf100-prewh", "mode": "std", "uva_seed": SEED, "uata_wh": 500,
     "steps": [("tclaim", ())],
     "expect": [tclaim_tf(POOL_ASIS, UVA_SEED_CLAIMED, -3334551, 3301205, 33346,
                          TCLAIM_EV(3334551, 3334773, 0))]},
    # Family B -- heavier fees
    {"label": "b-claim-tf5000", "mode": "std", "uva_seed": SEED, "bps": 5000,
     "steps": [("tclaim", ())],
     "expect": [tclaim_tf(POOL_ASIS, UVA_SEED_CLAIMED, -3334551, 1667275, 1667276,
                          TCLAIM_EV(3334551, 3334773, 0))]},
    {"label": "b-claim-tf10000", "mode": "std", "uva_seed": SEED, "bps": 10000,
     "steps": [("tclaim", ())],
     "expect": [tclaim_tf(POOL_ASIS, UVA_SEED_CLAIMED, -3334551, 0, 3334551,
                          TCLAIM_EV(3334551, 3334773, 0))]},
    # Family C -- rounding, cap, gate
    {"label": "c-claim-small111-tf100", "mode": "std", "uva_seed": SMALL,
     "steps": [("tclaim", ())],
     "expect": [tclaim_tf(POOL_ASIS, UVA_SMALL_CLAIMED, -111, 109, 2,
                          TCLAIM_EV(111, 333, 0))]},
    {"label": "c-claim-maxfee1000-tf100", "mode": "std", "uva_seed": SEED, "maxfee": 1000,
     "steps": [("tclaim", ())],
     "expect": [tclaim_tf(POOL_ASIS, UVA_SEED_CLAIMED, -3334551, 3333551, 1000,
                          TCLAIM_EV(3334551, 3334773, 0))]},
    {"label": "c-claim-needs0-tf100", "mode": "std",
     "uva_seed": (0, 111, 222, 333444, 20, 1, 0, 0),
     "steps": [("tclaim", ())],
     "expect": [tclaim_tf(POOL_ASIS, UVA_NEEDS0_CLAIMED, -3334551, 3301205, 33346,
                          TCLAIM_EV(3334551, 3334773, 0))]},
    # Family D -- failure and program/ATA binding
    {"label": "d-claim-shortvault-tf100", "mode": "std", "uva_seed": SMALL, "vault": 5,
     "steps": [("tclaim", ())],
     "expect": [E(-5000, {}, POOL_ASIS, VOL_SEED, events=0,
                  error="InstructionErrorCustom(1)", rollback=True, uva=UVA_SMALL)]},
    {"label": "d-claim-tokenprog-2023", "mode": "std", "uva_seed": SEED,
     "steps": [("tclaim2023", ())],
     "expect": [E(-5000, {}, POOL_ASIS, VOL_SEED, events=0, error="2023",
                  rollback=True, site_fragment="user_ata", uva=UVA_SEED)]},
    {"label": "d-claim-splata-3014", "mode": "std", "uva_seed": SEED,
     "steps": [("tclaim3014", ())],
     "expect": [E(-5000, {}, POOL_ASIS, VOL_SEED, events=0, error="3014",
                  rollback=True, site_fragment="user_ata", uva=UVA_SEED)]},
    # Family E -- claim-tf chained into trade -> sweep -> collect
    {"label": "e-claim-tf100-v2buy-swc-col", "mode": "std", "uva_seed": SEED,
     "steps": [("tclaim", ()), ("vbuy", (10**10, 10**12)), ("swc", ()), ("col", ())],
     "expect": [tclaim_tf(POOL_ASIS, UVA_SEED_CLAIMED, -3334551, 3301205, 33346,
                          TCLAIM_EV(3334551, 3334773, 0)),
                E(-5000, D_VBUY, POOL_VBUY, VOL_SEED, event=VBUY_EV(), uva=UVA_SEED_CLAIMED),
                swc_after(POOL_VBUY_SWC, VOL_SEED, UVA_SEED_CLAIMED),
                col_after(128869, POOL_VBUY_SWC, VOL_SEED, UVA_SEED_CLAIMED)]},
    {"label": "e-v2buy-claim-tf100-swc-col", "mode": "std", "uva_seed": SEED,
     "steps": [("vbuy", (10**10, 10**12)), ("tclaim", ()), ("swc", ()), ("col", ())],
     "expect": [E(-5000, D_VBUY, POOL_VBUY, VOL_SEED, event=VBUY_EV(), uva=UVA_SEED),
                tclaim_tf(POOL_VBUY, UVA_SEED_CLAIMED, -3334551, 3301205, 33346,
                          TCLAIM_EV(3334551, 3334773, 0)),
                swc_after(POOL_VBUY_SWC, VOL_SEED, UVA_SEED_CLAIMED),
                col_after(128869, POOL_VBUY_SWC, VOL_SEED, UVA_SEED_CLAIMED)]},
    {"label": "e-v2buy-swc-col-claim-tf100", "mode": "std", "uva_seed": SEED,
     "steps": [("vbuy", (10**10, 10**12)), ("swc", ()), ("col", ()), ("tclaim", ())],
     "expect": [E(-5000, D_VBUY, POOL_VBUY, VOL_SEED, event=VBUY_EV(), uva=UVA_SEED),
                swc_after(POOL_VBUY_SWC, VOL_SEED, UVA_SEED),
                col_after(128869, POOL_VBUY_SWC, VOL_SEED, UVA_SEED),
                tclaim_tf(POOL_VBUY_SWC, UVA_SEED_CLAIMED, -3334551, 3301205, 33346,
                          TCLAIM_EV(3334551, 3334773, 0))]},
    {"label": "e-cbbuy-tclaim-tf100-cbclaim-swc-col", "mode": "cb-present",
     "uva_seed": (1, 111, 222, 333444, 20, 1, 0, 0),
     "steps": [("cbbuy", (10**10, 10**12)), ("tclaim", ()), ("claim", ()), ("swc", ()), ("col", ())],
     "expect": [E(-5000, D_CBBUY, POOL_ASIS, VOL_SEED, event=EV_CBBUY,
                  lam_after={"uvata": 2044755}, uva=UVA_CBSEED_EARNED),
                tclaim_tf(POOL_ASIS, UVA_CBSEED_TCLAIMED, -3334551, 3301205, 33346,
                          TCLAIM_EV(3334551, 3334773, 0)),
                E(-5000, {"uvata": -5475, "userquote": 5475}, POOL_ASIS, VOL_SEED,
                  event=CLAIM_EV(5475, 5475, 5475),
                  lam_after={"uvata": 2039280}, uva=UVA_CBSEED_DONE),
                swc_after(POOL_SWC, VOL_SEED, UVA_CBSEED_DONE, amount=123394),
                col_after(123394, POOL_SWC, VOL_SEED, UVA_CBSEED_DONE)]},
]


STEP_KIND = {"swp": "swp", "swc": "swc", "col": "col", "claim": "claim",
             "tclaim": "tclaim", "tclaim2023": "tclaim", "tclaim3014": "tclaim",
             "lsell": "lsell", "cbsell": "cbsell",
             "buy": "buy", "cbbuy": "buy", "vbuy": "vbuy", "vsell": "vsell",
             "vexact": "vexact"}


def run_case(case, image_name, binary):
    h = setup_vm(binary, case)
    out = []
    for (kind, args), exp in zip(case["steps"], case["expect"]):
        rec = do_step(h, kind, args)
        tag = f"{case['label']}/{image_name}/{kind}"
        if exp["error"] is None:
            check(rec["error"] is None, f"{tag}: unexpected error {rec['error']}")
        else:
            check(rec["error"] is not None and exp["error"] in rec["error"],
                  f"{tag}: expected error {exp['error']}, got {rec['error']}")
        check(len(rec["events"]) == exp["events"],
              f"{tag}: events {len(rec['events'])} != {exp['events']}")
        d_payer = lam_delta(rec, PAYER_KEY)
        check(d_payer == exp["dPAYER"], f"{tag}: dPAYER {d_payer} != {exp['dPAYER']}")
        for role, want in exp["deltas"].items():
            got_d = tok_delta(rec, ROLE_KEY[role])
            check(got_d == want, f"{tag}: delta {role} {got_d} != {want}")
        for role, want in exp["withheld"].items():
            b = tok_withheld(rec["before"][str(ROLE_KEY[role])])
            a = tok_withheld(rec["after"][str(ROLE_KEY[role])])
            got_w = (a or 0) - (b or 0)
            check(got_w == want, f"{tag}: withheld delta {role} {got_w} != {want}")
        for role, want in exp["lam_after"].items():
            got = rec["after"][str(ROLE_KEY[role])]
            check(got is not None and got["lamports"] == want,
                  f"{tag}: lam_after {role} {None if got is None else got['lamports']} != {want}")
        for role in exp["absent"]:
            check(rec["after"][str(ROLE_KEY[role])] is None,
                  f"{tag}: {role} should stay absent")
        got_pool = pool_state(rec["after"][str(pool)])
        check(list(got_pool) == exp["pool_after"], f"{tag}: pool {got_pool} != {exp['pool_after']}")
        got_vol = vol_state(rec["after"][str(volume)])
        check(got_vol == exp["volume"], f"{tag}: volume {got_vol} != {exp['volume']}")
        if exp.get("uva") is not None:
            got_uva = uva_fields(rec["after"][str(volume)])
            check(got_uva == exp["uva"], f"{tag}: uva {got_uva} != {exp['uva']}")
        elif "uva" in exp:
            check(rec["after"][str(volume)] is None, f"{tag}: volume should stay absent")
        check(rec["after"][str(GVOL)] == rec["before"][str(GVOL)],
              f"{tag}: global volume accumulator changed")
        if exp.get("rollback"):
            for k, b in rec["before"].items():
                if k == str(PAYER_KEY):
                    continue
                check(rec["after"][k] == b, f"{tag}: rollback violated for {k}")
        if exp.get("event") is not None:
            got = decode_event(STEP_KIND[kind], rec)
            check(got is not None, f"{tag}: event decode failed")
            for fkey, want in exp["event"].items():
                check(got.get(fkey) == want, f"{tag}: event {fkey} {got.get(fkey)} != {want}")
        if exp.get("site_fragment"):
            blob = "\n".join(rec["logs"])
            check(exp["site_fragment"] in blob,
                  f"{tag}: site fragment {exp['site_fragment']} not in logs")
        if exp.get("log_fragment"):
            blob = "\n".join(rec["logs"])
            check(exp["log_fragment"] in blob,
                  f"{tag}: log fragment {exp['log_fragment']} not in logs")
        rec["case"] = case["label"]
        rec["image"] = image_name
        rec["step"] = kind
        out.append(rec)
    return out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "runtime").mkdir(exist_ok=True)
    receipts = []
    report_cases = []
    for case in CASES:
        per_image = {}
        for image_name, binary in IMAGES.items():
            per_image[image_name] = run_case(case, image_name, binary)
        for rec in per_image["original"]:
            receipts.append(rec)

        def surface(recs):
            out = []
            for rec in recs:
                def strip(snap):
                    d = dict(snap)
                    if d.get(str(PAYER_KEY)) is not None:
                        d[str(PAYER_KEY)] = dict(d[str(PAYER_KEY)])
                        d[str(PAYER_KEY)]["lamports"] = 0
                    return d
                out.append({"step": rec["step"], "error": rec["error"],
                            "events": len(rec["events"]),
                            "before": strip(rec["before"]), "after": strip(rec["after"])})
            return out
        base = surface(per_image["original"])
        for image_name in ("control", "candidate"):
            check(surface(per_image[image_name]) == base,
                  f"{case['label']}: {image_name} observed surface differs from original")
            for rec in per_image[image_name]:
                receipts.append(rec)
        report_cases.append({"label": case["label"], "variant": case["mode"],
                             "steps": case["expect"],
                             "error_sites": {image_name: [r["site"] for r in per_image[image_name]] for image_name in IMAGES}})
        print(f"OK {case['label']} ({len(case['steps'])} steps x 3 images)")
    parts = []
    for i in range(0, len(receipts), 10):
        chunk = receipts[i:i + 10]
        name = f"raw-transactions-part{i // 10 + 1:02d}.jsonl.gz"
        path = OUT / "runtime" / name
        with gzip.open(path, "wt", encoding="utf-8") as fh:
            for rec in chunk:
                fh.write(json.dumps(rec) + "\n")
        parts.append({"file": f"runtime/{name}", "count": len(chunk),
                      "sha256": sha(path.read_bytes()), "bytes": path.stat().st_size})
    report = {"case_count": len(CASES), "receipt_count": len(receipts),
              "counts": {"cases": len(CASES), "receipts": len(receipts),
                         "parts": len(parts)},
              "mismatches": [],
              "input_sha256": {k: IMAGE_SHA[k] for k in IMAGES},
              "parts": parts, "cases": report_cases,
              "images": {k: IMAGE_SHA[k] for k in IMAGES}}
    with gzip.open(OUT / "runtime" / "report.json.gz", "wt", encoding="utf-8") as fh:
        fh.write(json.dumps(report, indent=2))
    print(f"cases={len(CASES)} receipts={len(receipts)} parts={len(parts)}")
    for p in parts:
        print(f"  {p['file']} {p['count']} receipts {p['bytes']} bytes")
    print("ROLE KEYS:")
    for role, key in ROLE_KEY.items():
        print(f"  {role} {key}")
    print(f"  pool {pool} payer {PAYER_KEY} volume {volume} gva {GVOL} mint {IMINT}")
    print("NEXT: write verify.py and README.md, then regenerate MANIFEST.json")


if __name__ == "__main__":
    main()
