#!/usr/bin/env python3
"""Build research/amm-boost-chains-20261029 receipts.

3rd run packet #34: boost_buy_and_burn chained into trades,
liquidity, sweeps, and collects.

The gap: 2nd #26 pinned boost_buy_and_burn in isolation (vault
drain, tf legs, gates) and 2nd #37/#40 touched boost partial
spend and virtual-reserve drift, but nobody chained a boost
INTO the fee pipes: after a boost burns base and tops up the
quote vault, do the following trade legs move, does the trade
bucket still sweep/collect cleanly, and does the boost window
itself survive trades, sweeps, and liquidity?

Sharp results (all three images agree on every step):
- The fixture pool cannot boost at all: vq + pf + cf == 0
  exactly (-125,882 + 2,488 + 123,394), so a fresh boost fails
  6065 PoolCannotBoost (boost.rs:245). A pool with vq patched
  to 10^9 boosts freely.
- A boost moves the next trade: boost-then-buy spends
  1,893,007 (vs 1,862,827 unboosted on the same vq=10^9 pool),
  vaults 1,884,313, buyback 8,694, bucket 129,003 (vs 128,914).
  Boost-then-sell receipts 184,622 (vault -185,491, buyback
  869); boost-then-buyx outs 52,822,650,212.
- Boost never touches pool fields, so the window survives
  everything: buy -> boost -> buy works (second buy spends
  1,893,064), boost -> boost -> buy works (spends 1,923,431),
  sweep -> boost -> collect works (sweep relabels cf into vq
  1:1, sum unchanged, boost still allowed).
- Liquidity drifts the window on a boostable pool: dep-1e9
  moves vq 10^9 -> 1,000,238,445 (floor), wd-1e9 moves it to
  999,761,554 (ceil); dep -> wd leaves vq at 999,999,999
  (drift -1) and the post-round-trip boost still burns the
  same 5,391,870,655,895.
- Under tf100 the boost curve uses the net: used 10^9 gross
  burns only 5,338,379,201,831 (vs 5,391,870,655,895 nofee),
  vault nets 990,000,000, withheld 10,000,000; the following
  tf buy spends 1,911,735 gross and its sweep/collect drain
  127,712 / 126,434 net.
- Drain needs a writable quote mint in the Token-2022 world:
  boost(10^12) with a read-only mint fails 6088
  QuoteMintNotWritable AFTER emitting both events (ghost
  events, full rollback); with a writable mint it succeeds,
  closes the boost vault ATA, and splits its lamports
  (10^12 to the pool quote vault via the native transfer,
  10^9 - fee to the payer).
- Boost amount 1 fails 6001 ZeroBaseAmount; amount 2 burns
  5,435. Min gate is exact: min == burned succeeds,
  min == burned+1 fails 6004 ExceededSlippage.
- Mayhem boost-then-buy spends the same 1,893,007 with
  buyback 0 (vault takes the full 1,893,007).

The builder asserts every expected value below per image before
writing. The packet's producer.py is this file.
"""
import base64
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
    base, f, lp, pool, poolraw, quote, supply, token, transferfee,
    userbase, userlp, userquote, vaultbase, vaultquote,
)
from pump_amm_trade_v2_differential import FEES, buyback, feeconfig, volume

ROOT = Path.home() / "workspace/pumpfun-sparse"
OUT = ROOT / "research/amm-boost-chains-20261029"
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
BB_OWNER = Pubkey.from_bytes(base64.b64decode(f['accounts']['buyback_fee_recipient']['data_base64'])[32:64])
BOOST, _ = Pubkey.find_program_address([b'boost_vault', bytes(pool)], PROGRAM)
POOLV2 = Pubkey.find_program_address([b'pool-v2', bytes(base)], PROGRAM)[0]
GVOL = Pubkey.find_program_address([b'global_volume_accumulator'], PROGRAM)[0]
GDISC = bytes(next(x for x in IDL['accounts'] if x['name'] == 'GlobalVolumeAccumulator')['discriminator'])
MX = 2**64 - 1
S_ASIS = 4194352106721
S_DEP9 = S_ASIS + 10**9
S_WD9 = S_ASIS - 10**9
RENT22 = 2157600


def ata22(owner):
    return Pubkey.find_program_address([bytes(owner), bytes(TOKEN22), bytes(quote)], ATA_PROG)[0]


def vault_of(creator):
    return Pubkey.find_program_address([b'creator_vault', bytes(creator)], PROGRAM)[0]


CREAT_VAULT = vault_of(CREATOR)
PROTOCOL = Pubkey.from_bytes(bytes(RAW[57:89]))
PROTO22 = ata22(PROTOCOL)
CREAT22 = ata22(CREAT_VAULT)
DEST22 = ata22(CREATOR)
BB22 = ata22(BB_OWNER)
BOOST_ATA22 = ata22(BOOST)

TRD_KEYS = [pool, PAYER_KEY, CONFIG_KEY, base, quote, userbase, userquote,
            vaultbase, vaultquote, TOKEN, TOKEN, Pubkey.default(), volume, feeconfig,
            buyback, EVENT, PROGRAM]
DEP_KEYS = [pool, CONFIG_KEY, PAYER_KEY, base, quote, lp, userbase, userquote,
            userlp, vaultbase, vaultquote, TOKEN, TOKEN22, EVENT, PROGRAM]
BST_KEYS = [pool, PAYER_KEY, CONFIG_KEY, base, quote, vaultbase, vaultquote,
            BOOST, BOOST_ATA22, TOKEN, TOKEN, EVENT, PROGRAM]
SWC_KEYS = [PAYER_KEY, CONFIG_KEY, pool, quote, TOKEN22, vaultquote, CREAT_VAULT, CREAT22,
            Pubkey.default(), ATA_PROG, EVENT, PROGRAM]
COL_KEYS = [quote, TOKEN22, CREATOR, CREAT_VAULT, CREAT22, DEST22, EVENT, PROGRAM]
WATCH = [PAYER_KEY, pool, base, quote, lp, userbase, userquote, userlp,
         vaultbase, vaultquote, buyback, volume, feeconfig, CONFIG_KEY,
         PROTO22, CREAT22, DEST22, BB22, BOOST, BOOST_ATA22, CREAT_VAULT]
ROLE_KEY = {"userbase": userbase, "userquote": userquote, "userlp": userlp,
            "vaultbase": vaultbase, "vaultquote": vaultquote, "buyback": buyback,
            "protoata": PROTO22, "creatorata": CREAT22, "dest": DEST22, "bbata": BB22,
            "boostata": BOOST_ATA22}
SWP_DISC = "82a42461e48287a5"
COL_DISC = "e8f5c2eeeada3a59"
BUY_DISC = "67f4521f2cf57777"
SELL_DISC = "3e2f370aa503dc2a"
DEP_DISC = "78f83d531f8e6b90"
WD_DISC = "1609851aa02c47c0"
BST_DISC = "3f451c16305cc2b9"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def t22acct(owner, amount, withheld=0):
    data = bytearray(165)
    data[0:32] = bytes(quote)
    data[32:64] = bytes(owner)
    struct.pack_into("<Q", data, 64, amount)
    data[108] = 1
    return bytes(data) + bytes([2]) + struct.pack("<HH", 7, 0) + struct.pack("<HHQ", 2, 8, withheld)


def setup_vm(binary, setup):
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
    glob[907:939] = bytes(PAYER_KEY)
    glob[939] = 1
    vm.set_account(CONFIG_KEY, Account(CONFIG["lamports"], bytes(glob), PROGRAM))
    for n, row in f["accounts"].items():
        vm.set_account(Pubkey.from_string(row["address"]),
                       Account(row["lamports"], base64.b64decode(row["data_base64"]),
                               Pubkey.from_string(row["owner"])))
    pd = bytearray(poolraw)
    if setup.get("vq") is not None:
        pd[245:261] = setup["vq"].to_bytes(16, "little", signed=True)
    if setup.get("mayhem"):
        pd[243] = 1
    vm.set_account(pool, Account(f["accounts"]["pool"]["lamports"], bytes(pd), PROGRAM))
    mint = struct.pack("<I", 1) + bytes(pool) + struct.pack("<Q", supply) + bytes([9, 1]) + bytes(36)
    vm.set_account(lp, Account(10**9, mint, TOKEN22))
    vm.set_account(userbase, Account(10**9, token(base, PAYER_KEY, 10**15, False), TOKEN))
    vm.set_account(userquote, Account(10**15 + 2039280, token(quote, PAYER_KEY, 10**15, True), TOKEN))
    vm.set_account(userlp, Account(10**9, token(lp, PAYER_KEY, supply // 2, False), TOKEN22))
    vm.set_account(volume, Account(0, b"", Pubkey.default()))
    vm.set_account(GVOL, Account(10**9, GDISC + struct.pack('<qqq', 0, 0, 86400) + bytes(base) + bytes(480), PROGRAM))
    vm.set_account(BOOST, Account(10**9, b"", Pubkey.default()))
    vm.set_account(CREAT_VAULT, Account(10**9, b"", Pubkey.default()))
    vm.set_account(PROTO22, Account(RENT22, t22acct(PROTOCOL, 0), TOKEN22))
    vm.set_account(CREAT22, Account(RENT22, t22acct(CREAT_VAULT, 0), TOKEN22))
    vm.set_account(DEST22, Account(RENT22, t22acct(CREATOR, 0), TOKEN22))
    vm.set_account(BB22, Account(RENT22, t22acct(BB_OWNER, 0), TOKEN22))
    transferfee(quote, setup.get("bps", 0), MX)(h, [])
    # Boost vault ATA in the Token-2022 world: 178-byte account.
    a = vm.get_account(BOOST_ATA22)
    if a is None:
        # derive from the TOKEN boost ATA data pattern used by the boost harness
        raw = token(quote, BOOST, 10**12, True)
        d = bytes(raw[:165]) + bytes([2]) + struct.pack('<HHQ', 2, 8, 0)
        vm.set_account(BOOST_ATA22, Account(10**12 + 10**9, d, TOKEN22))
    else:
        d = bytes(a.data[:165]) + bytes([2]) + struct.pack('<HHQ', 2, 8, 0)
        vm.set_account(BOOST_ATA22, Account(10**12 + 10**9, d, TOKEN22))
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


def tok_withheld(entry):
    if entry is None:
        return None
    raw = bytes.fromhex(entry["data_hex"])
    if len(raw) >= 182:
        return struct.unpack_from("<Q", raw, 174)[0]
    if len(raw) >= 178:
        return struct.unpack_from("<Q", raw, 170)[0]
    return None


def tok_delta(rec, key):
    b = rec["before"][str(key)]
    a = rec["after"][str(key)]
    return (tok_amount(a) or 0) - (tok_amount(b) or 0)


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


def ev_list(logs):
    out = []
    for l in logs:
        if l.startswith("Program data: "):
            out.append(base64.b64decode(l.split("Program data: ", 1)[1].strip()))
    return out


def u64(raw, off):
    return struct.unpack_from("<Q", raw, off)[0]


def decode_event(kind, raw):
    if kind in ("dep", "wd"):
        return {"disc": raw[:8].hex(), "len": len(raw),
                "base": u64(raw, 72), "quote": u64(raw, 80)}
    if kind == "buy":
        return {"disc": raw[:8].hex(), "len": len(raw),
                "curve": u64(raw, 64), "lp_bps": u64(raw, 72),
                "lp_fee": u64(raw, 80), "proto_bps": u64(raw, 88),
                "proto_fee": u64(raw, 96), "qwlp": u64(raw, 104),
                "uin": u64(raw, 112)}
    if kind == "sell":
        return {"disc": raw[:8].hex(), "len": len(raw),
                "curve": u64(raw, 64), "lp_bps": u64(raw, 72),
                "lp_fee": u64(raw, 80), "proto_bps": u64(raw, 88),
                "proto_fee": u64(raw, 96), "quote": u64(raw, 104),
                "uout": u64(raw, 112)}
    if kind == "buyx":
        return {"disc": raw[:8].hex(), "len": len(raw),
                "out": u64(raw, 16), "quote_in": u64(raw, 64),
                "lp_bps": u64(raw, 72), "lp_fee": u64(raw, 80),
                "proto_bps": u64(raw, 88), "proto_fee": u64(raw, 96),
                "qwlp": u64(raw, 104), "uin": u64(raw, 112)}
    if kind == "swc":
        return {"disc": raw[:8].hex(), "len": len(raw),
                "timestamp": struct.unpack_from("<q", raw, 8)[0],
                "recipient": raw[112:144].hex(),
                "amount": u64(raw, 176), "bucket": raw[184]}
    if kind == "col":
        return {"disc": raw[:8].hex(), "len": len(raw),
                "timestamp": struct.unpack_from("<q", raw, 8)[0],
                "creator": raw[16:48].hex(), "fee": u64(raw, 48),
                "vault_ata": raw[56:88].hex(), "dest": raw[88:120].hex()}
    if kind == "boost":
        return {"disc": raw[:8].hex(), "len": len(raw),
                "requested": u64(raw, 144), "used": u64(raw, 152),
                "burned": u64(raw, 160),
                "vq": int.from_bytes(raw[168:184], "little", signed=True),
                "quote_after": u64(raw, 184), "base_after": u64(raw, 192),
                "remaining": u64(raw, 200)}
    return None


def check(cond, msg):
    if not cond:
        raise AssertionError(msg)


def disc(name):
    return bytes(next(x for x in IDL["instructions"] if x["name"] == name)["discriminator"])


def do_step(h, kind, args):
    if kind == "dep":
        name, keys, data = "deposit", DEP_KEYS, disc("deposit") + struct.pack("<QQQ", *args)
        metas_extra = {}
    elif kind == "wd":
        name, keys, data = "withdraw", DEP_KEYS, disc("withdraw") + struct.pack("<QQQ", *args)
        metas_extra = {}
    elif kind == "buy":
        name, keys, data = "buy_v2", TRD_KEYS, disc("buy_v2") + struct.pack("<QQ", args[0], MX)
        metas_extra = {}
    elif kind == "sell":
        name, keys, data = "sell_v2", TRD_KEYS, disc("sell_v2") + struct.pack("<QQ", args[0], 0)
        metas_extra = {}
    elif kind == "buyx":
        name, keys, data = "buy_exact_quote_in_v2", TRD_KEYS, disc("buy_exact_quote_in_v2") + struct.pack("<QQ", *args)
        metas_extra = {}
    elif kind in ("boost", "boostw"):
        name, keys, data = "boost_buy_and_burn", BST_KEYS, disc("boost_buy_and_burn") + struct.pack("<QQ", *args)
        metas_extra = {"writable_mint": kind == "boostw"}
    elif kind == "swc":
        name, keys, data = "sweep_creator_fee", SWC_KEYS, disc("sweep_creator_fee")
        metas_extra = {}
    elif kind == "col":
        name, keys, data = "collect_coin_creator_fee", COL_KEYS, disc("collect_coin_creator_fee")
        metas_extra = {}
    else:
        raise ValueError(kind)
    ix = next(x for x in IDL["instructions"] if x["name"] == name)
    metas = [AccountMeta(k, bool(a.get("signer")), bool(a.get("writable")))
             for k, a in zip(keys, ix["accounts"])]
    if kind in ("buy", "sell", "buyx"):
        metas[10] = AccountMeta(TOKEN22, False, False)
        metas[14] = AccountMeta(BB22, False, True)
    if kind in ("boost", "boostw"):
        metas[8] = AccountMeta(BOOST_ATA22, False, True)
        metas[10] = AccountMeta(TOKEN22, False, False)
        if metas_extra.get("writable_mint"):
            metas[4] = AccountMeta(quote, False, True)
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
      rollback=False, wh_after=None, lam_deltas=None, boost_event=None,
      ata_none=False):
    if lam_deltas is None:
        lam_deltas = {k: v for k, v in deltas.items()
                      if k not in ("userbase", "vaultbase", "userlp")}
    return {"dPAYER": dPAYER, "deltas": deltas, "pool_after": list(pool_after),
            "volume": volume, "event": event, "events": events, "error": error,
            "rollback": rollback, "wh_after": wh_after or {},
            "lam_deltas": lam_deltas, "boost_event": boost_event,
            "ata_none": ata_none}


def P(vq, pf, cf, sup=S_ASIS):
    return [vq, pf, cf, sup]


def SWP_EV(amount, bucket=1):
    return {"disc": SWP_DISC, "len": 185, "timestamp": 1234567890,
            "recipient": bytes(CREAT_VAULT).hex(), "amount": amount, "bucket": bucket}


def COL_EV(fee):
    return {"disc": COL_DISC, "len": 120, "timestamp": 1234567890,
            "creator": bytes(CREATOR).hex(), "fee": fee,
            "vault_ata": bytes(CREAT22).hex(), "dest": bytes(DEST22).hex()}


def BUY_EV(curve, lp_fee, proto_fee, qwlp, uin):
    return {"disc": BUY_DISC, "len": 500, "curve": curve, "lp_bps": 2,
            "lp_fee": lp_fee, "proto_bps": 93, "proto_fee": proto_fee,
            "qwlp": qwlp, "uin": uin}


def SELL_EV(curve, lp_fee, proto_fee, quote, uout):
    return {"disc": SELL_DISC, "len": 449, "curve": curve, "lp_bps": 2,
            "lp_fee": lp_fee, "proto_bps": 93, "proto_fee": proto_fee,
            "quote": quote, "uout": uout}


def BUYX_EV(out, lp_fee, proto_fee, qwlp, uin):
    return {"disc": BUY_DISC, "len": 515, "out": out, "quote_in": 10**7,
            "lp_bps": 2, "lp_fee": lp_fee, "proto_bps": 93, "proto_fee": proto_fee,
            "qwlp": qwlp, "uin": uin}


def BST_EV(used, burned, vq, quote_after, base_after, remaining, requested=None):
    return {"disc": BST_DISC, "len": 208,
            "requested": used if requested is None else requested, "used": used,
            "burned": burned, "vq": vq, "quote_after": quote_after,
            "base_after": base_after, "remaining": remaining}


def DEP_EV(base, quote):
    return {"disc": DEP_DISC, "len": 264, "base": base, "quote": quote}


def WD_EV(base, quote):
    return {"disc": WD_DISC, "len": 264, "base": base, "quote": quote}


def FAIL(pool_after, volume, code, events=0):
    return E(-5000, {}, pool_after, volume, events=events, error=code, rollback=True)


VOL_NONE = None
VOL_CREATED = {"lamports": 1844400, "len": 137, "user": bytes(PAYER_KEY).hex()}
P0 = P(10**9, 2488, 123394)
P_FRESH = P(-125882, 2488, 123394)
P_BUY = P(999985697, 11182, 129003)
P_SELL = P(999998569, 3358, 123955)
P_BUYX = P(999924444, 48414, 153024)
P_SWEPT_BUY = P(1000114700, 11182, 0)
P_SWEPT_SELL = P(1000122524, 3358, 0)
P_SWEPT_BUYX = P(1000077468, 48414, 0)
P_ANCHOR_BUY = P(999985924, 11044, 128914)
P_BUY2 = P(999971619, 19739, 134524)
P_BOOST2_BUY = P(999985466, 11322, 129094)
P_BOOST_BUY2 = P(999971392, 19877, 134613)
P_DEP = P(1000238445, 2488, 123394, S_DEP9)
P_DEP_BUY = P(1000224142, 11182, 129003, S_DEP9)
P_DEP_SWEPT = P(1000353145, 11182, 0, S_DEP9)
P_WD = P(999761554, 2488, 123394, S_WD9)
P_WD_SELL = P(999760123, 3358, 123955, S_WD9)
P_WD_SWEPT = P(999884078, 3358, 0, S_WD9)
P_DEPWD = P(999999999, 2488, 123394)
P_DEPWD_BUY = P(999985696, 11182, 129003)
P_SWEPT_SEED = P(1000123394, 2488, 0)
P_MAYHEM_BUY = P(999977003, 19876, 129003)
P_MAYHEM_SWEPT = P(1000106006, 19876, 0)

BST1 = BST_EV(10**9, 5391870655895, 10**9, 123946690720, 668304525256850, 999000000000)
BST2 = BST_EV(2 * 10**9, 10698119843084, 10**9, 124946690720, 662998276069661, 998000000000, requested=2 * 10**9)
BST_SMALL = BST_EV(2, 5435, 10**9, 122946690722, 673696395907310, 999999999998, requested=2)
BST_DRAIN = BST_EV(10**12, 599402446286043, 10**9, 1122946690720, 74293949626702, 0, requested=10**12)
BST_BUY2 = BST_EV(10**9, 5391711213454, 999985924, 123948544992, 668294684699291, 999000000000)
BST_BOOST2 = BST_EV(10**9, 5306249181882, 10**9, 124946690720, 662998276074968, 998000000000)
BST_DEP = BST_EV(10**9, 5391880941907, 1000238445, 123976003130, 668465134866062, 999000000000)
BST_WD = BST_EV(10**9, 5391860365016, 999761554, 123917378311, 668143915652506, 999000000000)
BST_DEPWD = BST_EV(10**9, 5391870655895, 999999999, 123946690721, 668304525256851, 999000000000)
BST_TF = BST_EV(10**9, 5338379201831, 10**9, 123936690720, 668358016710914, 999000000000)
BST_SWEPT = BST_EV(10**9, 5391870655895, 1000123394, 123946567326, 668304525256850, 999000000000)

# boost step helper: token deltas + lam defaults (vaultquote/boostata move lamports 1:1)
def B(dPAYER, deltas, pool_after, volume, boost_event, wh_after=None, lam_deltas=None):
    return E(dPAYER, deltas, pool_after, volume, events=2, boost_event=boost_event,
             wh_after=wh_after, lam_deltas=lam_deltas)


def BOOST_DELTA(burned, used):
    return {"vaultbase": -burned, "vaultquote": used, "boostata": -used}


CASES = [
    {"label": "a-boost-1e9", "setup": {"vq": 10**9, "bps": 0}, "steps": [
        ("boost", (10**9, 0), B(-5000, BOOST_DELTA(5391870655895, 10**9), P0, VOL_NONE, BST1)),
    ]},
    {"label": "a-boost-2e9", "setup": {"vq": 10**9, "bps": 0}, "steps": [
        ("boost", (2 * 10**9, 0), B(-5000, BOOST_DELTA(10698119843084, 2 * 10**9), P0, VOL_NONE, BST2)),
    ]},
    {"label": "a-boost-amount1", "setup": {"vq": 10**9, "bps": 0}, "steps": [
        ("boost", (1, 0), FAIL(P0, VOL_NONE, "6001")),
    ]},
    {"label": "a-boost-amount2", "setup": {"vq": 10**9, "bps": 0}, "steps": [
        ("boost", (2, 0), B(-5000, BOOST_DELTA(5435, 2), P0, VOL_NONE, BST_SMALL)),
    ]},
    {"label": "a-boost-drain-writable", "setup": {"vq": 10**9, "bps": 0}, "steps": [
        ("boostw", (10**12, 0), E(999995000, {"vaultbase": -599402446286043, "vaultquote": 10**12, "boostata": -10**12},
         P0, VOL_NONE, events=2, boost_event=BST_DRAIN, ata_none=True,
         lam_deltas={"vaultquote": 10**12, "boostata": -1001000000000})),
    ]},
    {"label": "a-boost-drain-nowrite-fail", "setup": {"vq": 10**9, "bps": 0}, "steps": [
        ("boost", (10**12, 0), FAIL(P0, VOL_NONE, "6088", events=2)),
    ]},
    {"label": "a-boost-min-exact", "setup": {"vq": 10**9, "bps": 0}, "steps": [
        ("boost", (10**9, 5391870655895), B(-5000, BOOST_DELTA(5391870655895, 10**9), P0, VOL_NONE, BST1)),
    ]},
    {"label": "a-boost-min-plus1", "setup": {"vq": 10**9, "bps": 0}, "steps": [
        ("boost", (10**9, 5391870655896), FAIL(P0, VOL_NONE, "6004")),
    ]},
    {"label": "b-boost-buy-swc-col", "setup": {"vq": 10**9, "bps": 0}, "steps": [
        ("boost", (10**9, 0), B(-5000, BOOST_DELTA(5391870655895, 10**9), P0, VOL_NONE, BST1)),
        ("buy", (10**10,), E(-1849400, {"userbase": 10**10, "userquote": -1893007,
         "vaultbase": -10**10, "vaultquote": 1884313, "bbata": 8694},
         P_BUY, VOL_CREATED, event=BUY_EV(1869636, 374, 17388, 1870010, 1893007))),
        ("swc", (), E(-5000, {"vaultquote": -129003, "creatorata": 129003},
         P_SWEPT_BUY, VOL_CREATED, event=SWP_EV(129003))),
        ("col", (), E(-5000, {"creatorata": -129003, "dest": 129003},
         P_SWEPT_BUY, VOL_CREATED, event=COL_EV(129003), lam_deltas={})),
    ]},
    {"label": "b-boost-sell-swc-col", "setup": {"vq": 10**9, "bps": 0}, "steps": [
        ("boost", (10**9, 0), B(-5000, BOOST_DELTA(5391870655895, 10**9), P0, VOL_NONE, BST1)),
        ("sell", (10**9,), E(-1849400, {"userbase": -10**9, "userquote": 184622,
         "vaultbase": 10**9, "vaultquote": -185491, "bbata": 869},
         P_SELL, VOL_CREATED, event=SELL_EV(186960, 38, 1739, 186922, 184622))),
        ("swc", (), E(-5000, {"vaultquote": -123955, "creatorata": 123955},
         P_SWEPT_SELL, VOL_CREATED, event=SWP_EV(123955))),
        ("col", (), E(-5000, {"creatorata": -123955, "dest": 123955},
         P_SWEPT_SELL, VOL_CREATED, event=COL_EV(123955), lam_deltas={})),
    ]},
    {"label": "b-boost-buyx-swc-col", "setup": {"vq": 10**9, "bps": 0}, "steps": [
        ("boost", (10**9, 0), B(-5000, BOOST_DELTA(5391870655895, 10**9), P0, VOL_NONE, BST1)),
        ("buyx", (10**7, 1), E(-1849400, {"userbase": 52822650212, "userquote": -10**7,
         "vaultbase": -52822650212, "vaultquote": 9954074, "bbata": 45926},
         P_BUYX, VOL_CREATED, event=BUYX_EV(52822650212, 1976, 91852, 9878518, 9876542))),
        ("swc", (), E(-5000, {"vaultquote": -153024, "creatorata": 153024},
         P_SWEPT_BUYX, VOL_CREATED, event=SWP_EV(153024))),
        ("col", (), E(-5000, {"creatorata": -153024, "dest": 153024},
         P_SWEPT_BUYX, VOL_CREATED, event=COL_EV(153024), lam_deltas={})),
    ]},
    {"label": "b-buy-boost-buy", "setup": {"vq": 10**9, "bps": 0}, "steps": [
        ("buy", (10**10,), E(-1849400, {"userbase": 10**10, "userquote": -1862827,
         "vaultbase": -10**10, "vaultquote": 1854272, "bbata": 8555},
         P_ANCHOR_BUY, VOL_CREATED, event=BUY_EV(1839828, 368, 17111, 1840196, 1862827))),
        ("boost", (10**9, 0), B(-5000, BOOST_DELTA(5391711213454, 10**9), P_ANCHOR_BUY, VOL_CREATED, BST_BUY2)),
        ("buy", (10**10,), E(-5000, {"userbase": 10**10, "userquote": -1893064,
         "vaultbase": -10**10, "vaultquote": 1884370, "bbata": 8694},
         P_BUY2, VOL_CREATED, event=BUY_EV(1869691, 374, 17389, 1870065, 1893064))),
    ]},
    {"label": "b-boost-boost-buy", "setup": {"vq": 10**9, "bps": 0}, "steps": [
        ("boost", (10**9, 0), B(-5000, BOOST_DELTA(5391870655895, 10**9), P0, VOL_NONE, BST1)),
        ("boost", (10**9, 0), B(-5000, BOOST_DELTA(5306249181882, 10**9), P0, VOL_NONE, BST_BOOST2)),
        ("buy", (10**10,), E(-1849400, {"userbase": 10**10, "userquote": -1923431,
         "vaultbase": -10**10, "vaultquote": 1914597, "bbata": 8834},
         P_BOOST2_BUY, VOL_CREATED, event=BUY_EV(1899683, 380, 17668, 1900063, 1923431))),
    ]},
    {"label": "b-boost-buy-buy", "setup": {"vq": 10**9, "bps": 0}, "steps": [
        ("boost", (10**9, 0), B(-5000, BOOST_DELTA(5391870655895, 10**9), P0, VOL_NONE, BST1)),
        ("buy", (10**10,), E(-1849400, {"userbase": 10**10, "userquote": -1893007,
         "vaultbase": -10**10, "vaultquote": 1884313, "bbata": 8694},
         P_BUY, VOL_CREATED, event=BUY_EV(1869636, 374, 17388, 1870010, 1893007))),
        ("buy", (10**10,), E(-5000, {"userbase": 10**10, "userquote": -1893065,
         "vaultbase": -10**10, "vaultquote": 1884371, "bbata": 8694},
         P_BOOST_BUY2, VOL_CREATED, event=BUY_EV(1869692, 374, 17389, 1870066, 1893065))),
    ]},
    {"label": "c-dep-boost-buy-swc-col", "setup": {"vq": 10**9, "bps": 0}, "steps": [
        ("dep", (10**9, 2**64 - 1, 2**64 - 1), E(-5000, {"userbase": -160619895224, "userquote": -29312410,
         "vaultbase": 160619895224, "vaultquote": 29312410, "userlp": 10**9},
         P_DEP, VOL_NONE, event=DEP_EV(160619895224, 29312410))),
        ("boost", (10**9, 0), B(-5000, BOOST_DELTA(5391880941907, 10**9), P_DEP, VOL_NONE, BST_DEP)),
        ("buy", (10**10,), E(-1849400, {"userbase": 10**10, "userquote": -1892999,
         "vaultbase": -10**10, "vaultquote": 1884305, "bbata": 8694},
         P_DEP_BUY, VOL_CREATED, event=BUY_EV(1869628, 374, 17388, 1870002, 1892999))),
        ("swc", (), E(-5000, {"vaultquote": -129003, "creatorata": 129003},
         P_DEP_SWEPT, VOL_CREATED, event=SWP_EV(129003))),
        ("col", (), E(-5000, {"creatorata": -129003, "dest": 129003},
         P_DEP_SWEPT, VOL_CREATED, event=COL_EV(129003), lam_deltas={})),
    ]},
    {"label": "c-wd-boost-sell-swc-col", "setup": {"vq": 10**9, "bps": 0}, "steps": [
        ("wd", (10**9, 0, 0), E(-5000, {"userbase": 160619895223, "userquote": 29312409,
         "vaultbase": -160619895223, "vaultquote": -29312409, "userlp": -10**9},
         P_WD, VOL_NONE, event=WD_EV(160619895223, 29312409))),
        ("boost", (10**9, 0), B(-5000, BOOST_DELTA(5391860365016, 10**9), P_WD, VOL_NONE, BST_WD)),
        ("sell", (10**9,), E(-1849400, {"userbase": -10**9, "userquote": 184623,
         "vaultbase": 10**9, "vaultquote": -185492, "bbata": 869},
         P_WD_SELL, VOL_CREATED, event=SELL_EV(186961, 38, 1739, 186923, 184623))),
        ("swc", (), E(-5000, {"vaultquote": -123955, "creatorata": 123955},
         P_WD_SWEPT, VOL_CREATED, event=SWP_EV(123955))),
        ("col", (), E(-5000, {"creatorata": -123955, "dest": 123955},
         P_WD_SWEPT, VOL_CREATED, event=COL_EV(123955), lam_deltas={})),
    ]},
    {"label": "c-dep-wd-boost-buy", "setup": {"vq": 10**9, "bps": 0}, "steps": [
        ("dep", (10**9, 2**64 - 1, 2**64 - 1), E(-5000, {"userbase": -160619895224, "userquote": -29312410,
         "vaultbase": 160619895224, "vaultquote": 29312410, "userlp": 10**9},
         P_DEP, VOL_NONE, event=DEP_EV(160619895224, 29312410))),
        ("wd", (10**9, 0, 0), E(-5000, {"userbase": 160619895223, "userquote": 29312409,
         "vaultbase": -160619895223, "vaultquote": -29312409, "userlp": -10**9},
         P_DEPWD, VOL_NONE, event=WD_EV(160619895223, 29312409))),
        ("boost", (10**9, 0), B(-5000, BOOST_DELTA(5391870655895, 10**9), P_DEPWD, VOL_NONE, BST_DEPWD)),
        ("buy", (10**10,), E(-1849400, {"userbase": 10**10, "userquote": -1893007,
         "vaultbase": -10**10, "vaultquote": 1884313, "bbata": 8694},
         P_DEPWD_BUY, VOL_CREATED, event=BUY_EV(1869636, 374, 17388, 1870010, 1893007))),
    ]},
    {"label": "d-boost-tf100", "setup": {"vq": 10**9, "bps": 100}, "steps": [
        ("boost", (10**9, 0), E(-5000, {"vaultbase": -5338379201831, "vaultquote": 990000000, "boostata": -10**9},
         P0, VOL_NONE, events=2, boost_event=BST_TF, wh_after={"vaultquote": 10000000},
         lam_deltas={"vaultquote": 10**9, "boostata": -10**9})),
    ]},
    {"label": "d-boost-tf100-buy-swc-col", "setup": {"vq": 10**9, "bps": 100}, "steps": [
        ("boost", (10**9, 0), E(-5000, {"vaultbase": -5338379201831, "vaultquote": 990000000, "boostata": -10**9},
         P0, VOL_NONE, events=2, boost_event=BST_TF, wh_after={"vaultquote": 10000000},
         lam_deltas={"vaultquote": 10**9, "boostata": -10**9})),
        ("buy", (10**10,), E(-1849400, {"userbase": 10**10, "userquote": -1911735,
         "vaultbase": -10**10, "vaultquote": 1884012, "bbata": 8605},
         P_BUY, VOL_CREATED, event=BUY_EV(1869336, 374, 17385, 1869710, 1892704),
         wh_after={"vaultquote": 10019031, "bbata": 87},
         lam_deltas={"userquote": -1911735, "vaultquote": 1903043, "bbata": 8692})),
        ("swc", (), E(-5000, {"vaultquote": -129003, "creatorata": 127712},
         P_SWEPT_BUY, VOL_CREATED, event=SWP_EV(129003), wh_after={"creatorata": 1291},
         lam_deltas={"vaultquote": -129003, "creatorata": 129003})),
        ("col", (), E(-5000, {"creatorata": -127712, "dest": 126434},
         P_SWEPT_BUY, VOL_CREATED, event=COL_EV(129003), lam_deltas={},
         wh_after={"creatorata": 1291, "dest": 1278})),
    ]},
    {"label": "d-boost-tf10000-fail", "setup": {"vq": 10**9, "bps": 10000}, "steps": [
        ("boost", (10**9, 0), FAIL(P0, VOL_NONE, "6002")),
    ]},
    {"label": "e-fresh-boost-fail", "setup": {"vq": None, "bps": 0}, "steps": [
        ("boost", (10**9, 0), FAIL(P_FRESH, VOL_NONE, "6065")),
    ]},
    {"label": "e-sweep-boost-collect", "setup": {"vq": 10**9, "bps": 0}, "steps": [
        ("swc", (), E(-5000, {"vaultquote": -123394, "creatorata": 123394},
         P_SWEPT_SEED, VOL_NONE, event=SWP_EV(123394))),
        ("boost", (10**9, 0), B(-5000, BOOST_DELTA(5391870655895, 10**9), P_SWEPT_SEED, VOL_NONE, BST_SWEPT)),
        ("col", (), E(-5000, {"creatorata": -123394, "dest": 123394},
         P_SWEPT_SEED, VOL_NONE, event=COL_EV(123394), lam_deltas={})),
    ]},
    {"label": "e-mayhem-boost-buy-swc-col", "setup": {"vq": 10**9, "bps": 0, "mayhem": True}, "steps": [
        ("boost", (10**9, 0), B(-5000, BOOST_DELTA(5391870655895, 10**9), P0, VOL_NONE, BST1)),
        ("buy", (10**10,), E(-1849400, {"userbase": 10**10, "userquote": -1893007,
         "vaultbase": -10**10, "vaultquote": 1893007},
         P_MAYHEM_BUY, VOL_CREATED, event=BUY_EV(1869636, 374, 17388, 1870010, 1893007))),
        ("swc", (), E(-5000, {"vaultquote": -129003, "creatorata": 129003},
         P_MAYHEM_SWEPT, VOL_CREATED, event=SWP_EV(129003))),
        ("col", (), E(-5000, {"creatorata": -129003, "dest": 129003},
         P_MAYHEM_SWEPT, VOL_CREATED, event=COL_EV(129003), lam_deltas={})),
    ]},
]

# Fix the tf buy pool: tf buy pool differs from nofee buy pool in pf only
# (pf 11181 vs 11182) -- set explicitly below.
for _c in CASES:
    if _c["label"] == "d-boost-tf100-buy-swc-col":
        _c["steps"][1][2]["pool_after"] = [999985698, 11181, 129003, S_ASIS]
        _c["steps"][2][2]["pool_after"] = [1000114701, 11181, 0, S_ASIS]
        _c["steps"][3][2]["pool_after"] = [1000114701, 11181, 0, S_ASIS]
        # tf sweep/collect events report the gross bucket, not the net
        _c["steps"][2][2]["event"] = SWP_EV(129003)
        _c["steps"][3][2]["event"] = {"disc": COL_DISC, "len": 120, "timestamp": 1234567890,
                                      "creator": bytes(CREATOR).hex(), "fee": 127712,
                                      "vault_ata": bytes(CREAT22).hex(), "dest": bytes(DEST22).hex()}


def run_case(case, image_name, binary):
    h = setup_vm(binary, case["setup"])
    out = []
    for kind, args, exp in case["steps"]:
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
        for role, want in exp["lam_deltas"].items():
            got_d = lam_delta(rec, ROLE_KEY[role])
            check(got_d == want, f"{tag}: lam_delta {role} {got_d} != {want}")
        for role, want in exp["wh_after"].items():
            got_e = rec["after"][str(ROLE_KEY[role])]
            got_w = tok_withheld(got_e)
            check(got_w == want, f"{tag}: wh_after {role} {got_w} != {want}")
        got_pool = pool_state(rec["after"][str(pool)])
        check(list(got_pool) == exp["pool_after"],
              f"{tag}: pool {got_pool} != {exp['pool_after']}")
        got_vol = vol_state(rec["after"][str(volume)])
        check(got_vol == exp["volume"], f"{tag}: volume {got_vol} != {exp['volume']}")
        if exp.get("rollback"):
            for k, b in rec["before"].items():
                if k == str(PAYER_KEY):
                    continue
                check(rec["after"][k] == b, f"{tag}: rollback violated for {k}")
        if exp.get("ata_none"):
            check(rec["after"][str(BOOST_ATA22)] is None, f"{tag}: boost ATA not closed")
        raws = ev_list(rec["logs"])
        if exp.get("boost_event") is not None:
            check(len(raws) == 2, f"{tag}: boost events {len(raws)} != 2")
            buy_raw, bst_raw = raws
            check(buy_raw[:8].hex() == BUY_DISC and len(buy_raw) == 512,
                  f"{tag}: boost BuyEvent {buy_raw[:8].hex()}/{len(buy_raw)}")
            got = decode_event("boost", bst_raw)
            for fkey, want in exp["boost_event"].items():
                check(got.get(fkey) == want, f"{tag}: boost event {fkey} {got.get(fkey)} != {want}")
        elif exp.get("event") is not None:
            check(len(raws) == 1, f"{tag}: event raws {len(raws)} != 1")
            got = decode_event(kind, raws[0])
            check(got is not None, f"{tag}: event decode failed")
            for fkey, want in exp["event"].items():
                check(got.get(fkey) == want, f"{tag}: event {fkey} {got.get(fkey)} != {want}")
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
        for image_name in ("original", "control", "candidate"):
            for rec in per_image[image_name]:
                receipts.append(rec)
        report_cases.append({"label": case["label"],
                             "setup": {k: (str(v) if not isinstance(v, list) else [str(x) for x in v]) for k, v in case["setup"].items()},
                             "steps": [e for _, _, e in case["steps"]],
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
    print("NEXT: write verify.py and README.md, then regenerate MANIFEST.json")


if __name__ == "__main__":
    main()
