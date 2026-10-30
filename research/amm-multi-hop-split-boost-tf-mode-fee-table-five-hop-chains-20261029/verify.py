#!/usr/bin/env python3
"""Independent re-verification for amm-multi-hop-split-boost-tf-mode-fee-table-five-hop-chains-20261029.

Checks, from the packet files alone (plus the three program images
when present at their workspace paths):
- MANIFEST.json lists every packet file (except itself) with a matching
  sha256 and byte count.
- runtime/report.json.gz: 62 cases, 294 receipts, 30 parts
  (29x10 + 4), part sha256/byte counts match the part files.
- Every receipt transaction parses (solders) and all signatures verify
  (cpatch steps carry an empty transaction by design -- a harness field
  reset, never an instruction -- and are asserted as such instead, and
  the following step's before snapshot must equal the cpatch after
  snapshot).
- Every receipt's recorded before/after snapshots reproduce the
  report's per-image expected values: fee-payer and outsider lamport
  deltas, the token-leg deltas, the Token-2022 withheld deltas, the
  native-mint token-account lamport deltas, the three fixture pool
  states (virtual_quote_reserves i128, protocol_fees, creator_fees,
  lp_supply) plus the pool coin_creator bytes after every step, the
  GlobalConfig state (including boost authority 907..939 and the
  boost_enabled / disable flags), the user volume accumulator state,
  the global volume accumulator state (start/end/sec/mint/
  total_token_supply/sol_volumes), the account lengths (pool / config
  / UVA / GVA / fee-table / extend target) after every step, and the
  decoded event fields (multi-hop 508/449-byte hop events, boost
  512-byte BuyEvent + 208-byte boost event, sweep 185-byte fields,
  collect 120-byte fields).
- Failure steps roll back every watched account's data, and only
  transaction signers may change lamports on a failed step.
- Control and candidate observed surfaces are identical in every
  case. Original diverges from the rebuilds in exactly 26 cases,
  all of them mode-gate cases (listed in expected_divergent below);
  every other case agrees on all three images.
- Headline pins (see README): the #119 mode-gate split is
  tier-invariant -- non-terminal cashback flags diverge (original
  succeeds, rebuild 6079) under tier-0, tier-1 and exotic tables
  alike, terminal cashback fails 6079 on all images, mayhem fails
  6080 on all images, and both-flagged hops split 6080 (original)
  vs 6079 (rebuild) except at the terminal hop, where both fail
  6079; ghost ladders scale with hop position in both directions;
  global cashback/mayhem flags do not gate the multi-hop leg;
  boosts under mode+tiers are mode-blind (only a failed buy moves
  the next burn); the exotic tail accrual lands in P5's creator
  bucket exactly when the buy itself succeeds, so the mode gate,
  not the fee table, decides where the accrual lands.

"""
import base64
import gzip
import hashlib
import json
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PAYER = "DXyM8yAHqpMzDtvwz5DXoEUQmPxjJPMKCASCPhLMKpEx"
OUTSIDER = "5jotNjSnm9ZJRefVfqHato9FC4d9t6CHb2xS1726MTyY"
POOL = "GseMAnNDvntR5uFePZ51yZBXzNSn7GdFPkfHwfr6d77J"
POOL2 = "Fpyw25Qi4beJtjo22e1iLZ8PeGkKXFBkF2WbdSuxsaZa"
P3 = "3tvv2kFkoHENFctvg9VKJi2z6pagcMPoHMFP3m9FfruF"
CONFIG = "ADyA8hdefvWN2dbGGWFotbzWxrAvLW83WG6QCVXvJKqw"
FEECONFIG = "5PHirr8joyTMp9JMm6nW7hNDVyEYdkzDqazxPD7RaTjx"
VOLUME = "8NyBnxo9mS5MsqY4qoKmrt7MS89d7MNV6rh5fu2YsQPT"
GVOL = "C2aFPdENg4A2HQsmrd5rTw5TaYBX5Ku887cWjbFKtZpw"
EXTKEY = "B8qLUArXhjYyvaX8RovpeJmRcpZC2XyzpCyRk1is4yP3"
QUOTE = "So11111111111111111111111111111111111111112"
BB22 = "8imwZyx4D4zdUQ67TvftjjyGattafMNWMLs6HV8WNn1Y"
WDEST = "43HYZhSLzJVSwUAccwX2dmWmKBxhHDxjA1LQKJkzTg7w"
U3 = "6swiTCWtSwqi8sm9wzNwKA9NEpJWbXjLcVz654u7zz4W"
P4 = "5gZTf2A6UPeYZCq1mkdiYquMQqmjNcz9pknbABkWif9c"
P5 = "5TdRYVo7We7hYSXDS3ryvUvouL7hoaMLTGMRqMrzBhcE"
U5 = "79cu2QNvp92chEmBhBgcUfERDT9KHnUcr8eiJb5WzKML"
# Token-role keys are recovered from the receipts themselves: the
# builder's TOKEN_ROLES deltas are recomputed from snapshots, and
# the headline asserts below use only pool / config / UVA / GVA /
# payer / outsider keys plus decoded events, so no full role table
# is needed here.

BST_DISC = "3f451c16305cc2b9"
MHBUY_DISC = "67f4521f2cf57777"
MHSELL_DISC = "3e2f370aa503dc2a"
SWP_DISC = "82a42461e48287a5"
COL_DISC = "e8f5c2eeeada3a59"


def check(cond, msg):
    if not cond:
        raise AssertionError(msg)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def u64(raw, off):
    return struct.unpack_from("<Q", raw, off)[0]


def tok_amount(entry):
    if entry is None:
        return None
    raw = bytes.fromhex(entry["data_hex"])
    return struct.unpack_from("<Q", raw, 64)[0] if len(raw) >= 72 else None


def tok_delta(rec, key):
    b, a = rec["before"].get(str(key)), rec["after"].get(str(key))
    return (tok_amount(a) or 0) - (tok_amount(b) or 0)


def wh_of(entry):
    if entry is None:
        return None
    raw = bytes.fromhex(entry["data_hex"])
    if len(raw) == 178:
        return struct.unpack_from("<Q", raw, 170)[0]
    if len(raw) == 182:
        return struct.unpack_from("<Q", raw, 174)[0]
    return None


def wh_delta(rec, key):
    b, a = rec["before"].get(str(key)), rec["after"].get(str(key))
    return (wh_of(a) or 0) - (wh_of(b) or 0)


def lam_delta(rec, key):
    b, a = rec["before"].get(str(key)), rec["after"].get(str(key))
    return (a["lamports"] if a else 0) - (b["lamports"] if b else 0)


def pool_state(entry):
    if entry is None:
        return None
    d = bytes.fromhex(entry["data_hex"])
    if len(d) < 287:
        return {"len": len(d)}
    return [int.from_bytes(d[245:261], "little", signed=True),
            struct.unpack_from("<Q", d, 271)[0],
            struct.unpack_from("<Q", d, 279)[0],
            struct.unpack_from("<Q", d, 203)[0]]


def cfg_fields(entry):
    if entry is None:
        return None
    raw = bytes.fromhex(entry["data_hex"])
    if len(raw) < 949:
        return {"len": len(raw)}
    return {"disable": raw[56], "lp": u64(raw, 40), "proto": u64(raw, 48),
            "recipients": [raw[57 + i * 32:57 + (i + 1) * 32].hex() for i in range(8)],
            "creator_fee": u64(raw, 313), "fee_auth": raw[321:353].hex(),
            "bps": u64(raw, 899),
            "bb_recipients": [raw[643 + i * 32:643 + (i + 1) * 32].hex() for i in range(8)],
            "mayhem": raw[417], "cashback": raw[642],
            "boost_auth": raw[907:939].hex(), "boost_enabled": raw[939]}


def uva_fields(entry):
    if entry is None:
        return None
    raw = bytes.fromhex(entry["data_hex"])
    if len(raw) < 90:
        return {"len": len(raw)}
    needs, unc, cla, vol, last, hasc, earn, cbcl = struct.unpack_from('<BQQQqBQQ', raw, 40)
    return {"needs": needs, "unclaimed": unc, "claimed": cla, "volume": vol,
            "last": last, "has": hasc, "earned": earn, "cb_claimed": cbcl}


def gva_fields(entry):
    if entry is None:
        return None
    raw = bytes.fromhex(entry["data_hex"])
    if len(raw) < 64:
        return {"len": len(raw)}
    sup = [struct.unpack_from("<Q", raw, 64 + i * 8)[0] for i in range(30)] if len(raw) >= 304 else None
    vol = [struct.unpack_from("<Q", raw, 304 + i * 8)[0] for i in range(30)] if len(raw) >= 544 else None
    return {"len": len(raw),
            "start": struct.unpack_from("<q", raw, 8)[0],
            "end": struct.unpack_from("<q", raw, 16)[0],
            "sec": struct.unpack_from("<q", raw, 24)[0],
            "mint": raw[32:64].hex(),
            "supply": sup, "vol": vol}


def mint_fields(entry):
    if entry is None:
        return None
    raw = bytes.fromhex(entry["data_hex"])
    if len(raw) < 278:
        return {"len": len(raw)}
    return {"oe": struct.unpack_from("<Q", raw, 242)[0],
            "omax": struct.unpack_from("<Q", raw, 250)[0],
            "ob": struct.unpack_from("<H", raw, 258)[0],
            "ne": struct.unpack_from("<Q", raw, 260)[0],
            "nmax": struct.unpack_from("<Q", raw, 268)[0],
            "nb": struct.unpack_from("<H", raw, 276)[0],
            "wh": u64(raw, 234) if len(raw) >= 242 else None}


def acct_len(entry):
    return None if entry is None else len(bytes.fromhex(entry["data_hex"]))


def ev_list(logs):
    out = []
    for l in logs:
        if l.startswith("Program data: "):
            out.append(base64.b64decode(l.split("Program data: ", 1)[1].strip()))
    return out


def decode_event(kind, raw):
    if kind in ("mhbuy3", "mhsell3", "mhbuy5", "mhsell5", "mhbuy4", "mhsell4", "mhbuy1", "mhsell1"):
        return {"disc": raw[:8].hex(), "len": len(raw)}
    if kind == "boost":
        if raw[:8].hex() != BST_DISC:
            return {"disc": raw[:8].hex(), "len": len(raw)}
        return {"disc": raw[:8].hex(), "len": len(raw),
                "requested": u64(raw, 144), "used": u64(raw, 152),
                "burned": u64(raw, 160),
                "vq": int.from_bytes(raw[168:184], "little", signed=True),
                "quote_after": u64(raw, 184), "base_after": u64(raw, 192),
                "remaining": u64(raw, 200)}
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
    if kind in ("dep", "wd"):
        return {"disc": raw[:8].hex(), "len": len(raw),
                "base": u64(raw, 72), "quote": u64(raw, 80)}
    if kind == "extend":
        return {"disc": raw[:8].hex(),
                "ts": struct.unpack_from("<q", raw, 8)[0],
                "account": raw[16:48].hex(), "user": raw[48:80].hex(),
                "old": u64(raw, 80), "new": u64(raw, 88), "len": len(raw)}
    if kind == "tclaim":
        return {"disc": raw[:8].hex(), "len": len(raw),
                "user": raw[8:40].hex(), "mint": raw[40:72].hex(),
                "amount": u64(raw, 72), "ts": struct.unpack_from("<q", raw, 80)[0],
                "total_claimed": u64(raw, 88), "current_sol_volume": u64(raw, 96)}
    if kind == "cclaim":
        return {"disc": raw[:8].hex(), "len": len(raw),
                "user": raw[8:40].hex(), "amount": u64(raw, 40),
                "ts": struct.unpack_from("<q", raw, 48)[0],
                "total_claimed": u64(raw, 56), "total_earned": u64(raw, 64)}
    if kind == "sync":
        return {"disc": raw[:8].hex(), "user": raw[8:40].hex(),
                "before": u64(raw, 40), "after": u64(raw, 48),
                "ts": struct.unpack_from("<q", raw, 56)[0], "len": len(raw)}
    if kind == "admin":
        return {"disc": raw[:8].hex(), "len": len(raw),
                "start": struct.unpack_from("<q", raw, 8)[0],
                "end": struct.unpack_from("<q", raw, 16)[0],
                "day": u64(raw, 24), "supply": u64(raw, 32),
                "mint": raw[40:72].hex(),
                "sec": struct.unpack_from("<q", raw, 72)[0],
                "timestamp": struct.unpack_from("<q", raw, 80)[0]}
    if kind in ("close", "close_other", "close_unsigned"):
        return {"disc": raw[:8].hex(), "user": raw[8:40].hex(),
                "ts": struct.unpack_from("<q", raw, 40)[0],
                "unc": u64(raw, 48), "claimed": u64(raw, 56),
                "vol": u64(raw, 64), "last": struct.unpack_from("<q", raw, 72)[0],
                "len": len(raw)}
    if kind == "init":
        return {"disc": raw[:8].hex(), "payer": raw[8:40].hex(),
                "user": raw[40:72].hex(),
                "ts": struct.unpack_from("<q", raw, 72)[0], "len": len(raw)}
    if kind == "buy2":
        return {"disc": raw[:8].hex(), "len": len(raw),
                "curve": u64(raw, 64), "lp_bps": u64(raw, 72),
                "lp_fee": u64(raw, 80), "proto_bps": u64(raw, 88),
                "proto_fee": u64(raw, 96), "qwlp": u64(raw, 104),
                "uin": u64(raw, 112)}
    if kind == "sell2":
        return {"disc": raw[:8].hex(), "len": len(raw),
                "curve": u64(raw, 64), "lp_bps": u64(raw, 72),
                "lp_fee": u64(raw, 80), "proto_bps": u64(raw, 88),
                "proto_fee": u64(raw, 96), "quote": u64(raw, 104),
                "uout": u64(raw, 112)}
    return None


STEP_KIND = {"mhbuy5": "mhbuy5", "mhsell5": "mhsell5", "boost": "boost",
             "swp22": "swp", "swc22": "swc", "col22": "col", "dep": "dep", "wd": "wd",
             "tclaim": "tclaim", "cclaim": "cclaim", "sync": "sync",
             "swp": "swp", "swc": "swc", "col": "col",
                "boost2": "boost", "boost2o": "boost", "boost3s": "boost", "boost3o": "boost",
                "boost4s": "boost", "boost5s": "boost",
                "boost2x": "boost", "boost3x": "boost", "boostx": "boost", "boosto": "boost",
                "boostauth": None, "initb": None,
             "xfer2": None, "xfer1": None, "cpatch": None,
             "admin": "admin", "close": "close", "close_other": "close", "close_unsigned": "close", "init": "init",
             "ww": None, "harvest": None, "wfm": None,
             "buy2m": "buy2", "sell2m": "sell2", "lexact": None, "bexact2": None}


def recompute(rec):
    sys.path.insert(0, str(HERE))
    import producer
    ROLE_KEY = producer.ROLE_KEY
    TOKEN_ROLES = producer.TOKEN_ROLES
    kind = rec["step"]
    raws = ev_list(rec["logs"])
    dk = STEP_KIND.get(kind)
    decoded = None
    if dk is not None:
        decoded = [decode_event(dk, raw) for raw in raws]
    if kind == "boost" and raws:
        decoded = [decode_event("boost", raw) for raw in raws]
    if kind == "cpatch":
        decoded = []
    after = rec["after"]
    # Token/withheld/lamport deltas use the producer's role table
    # (address constants only); all values are recomputed from the
    # receipt snapshots here.
    return {"step": kind, "error": rec["error"], "events": len(rec["events"]),
            "decoded": decoded,
            "dPAYER": lam_delta(rec, PAYER), "dOUT": lam_delta(rec, OUTSIDER),
            "pools": {name: pool_state(after[key]) for name, key in
                      (("main", POOL), ("pool2", POOL2), ("p3", P3), ("p4", P4), ("p5", P5))},
            "pool_creator": bytes.fromhex(after[POOL]["data_hex"])[211:243].hex() if after.get(POOL) else None,
            "cfg": cfg_fields(after.get(CONFIG)),
            "uva": uva_fields(after.get(VOLUME)),
            "gva": gva_fields(after.get(GVOL)),
            "mint": mint_fields(after.get(QUOTE)),
            "lens": {"pool": acct_len(after.get(POOL)), "cfg": acct_len(after.get(CONFIG)),
                     "uva": acct_len(after.get(VOLUME)), "gva": acct_len(after.get(GVOL)),
                     "fee": acct_len(after.get(FEECONFIG)), "extacc": acct_len(after.get(EXTKEY))},
            "site": rec["site"],
            "deltas": {role: tok_delta(rec, ROLE_KEY[role]) for role in TOKEN_ROLES if tok_delta(rec, ROLE_KEY[role]) != 0},
            "withheld": {role: wh_delta(rec, ROLE_KEY[role]) for role in TOKEN_ROLES if wh_delta(rec, ROLE_KEY[role]) != 0},
            "lam_deltas": {role: lam_delta(rec, ROLE_KEY[role]) for role in TOKEN_ROLES if lam_delta(rec, ROLE_KEY[role]) != 0}}


def main():
    from solders.transaction import Transaction
    manifest = json.loads((HERE / "MANIFEST.json").read_text())
    listed = {f["path"]: f for f in manifest["files"]}
    actual = {}
    for p in sorted(HERE.rglob("*")):
        if p.is_file() and p.name != "MANIFEST.json" and ".git" not in p.parts:
            rel = str(p.relative_to(HERE))
            actual[rel] = {"sha256": sha(p.read_bytes()), "bytes": p.stat().st_size}
    check(set(listed) == set(actual),
          f"manifest file set mismatch: missing={set(actual) - set(listed)} extra={set(listed) - set(actual)}")
    for rel, f in listed.items():
        check(f["sha256"] == actual[rel]["sha256"] and f["bytes"] == actual[rel]["bytes"],
              f"manifest mismatch for {rel}")
    report = json.loads(gzip.open(HERE / "runtime" / "report.json.gz", "rt").read())
    check(report["case_count"] == 62, f"case_count {report['case_count']}")
    check(report["counts"] == {"cases": 62, "receipts": 294, "parts": 30},
          f"counts {report['counts']}")
    receipts = []
    for part in report["parts"]:
        path = HERE / part["file"]
        check(path.stat().st_size == part["bytes"], f"part bytes {part['file']}")
        check(sha(path.read_bytes()) == part["sha256"], f"part sha {part['file']}")
        with gzip.open(path, "rt", encoding="utf-8") as fh:
            for line in fh:
                receipts.append(json.loads(line))
    check(len(receipts) == 294, f"receipts {len(receipts)}")
    check(report["receipt_count"] == 294, "report receipt_count")
    # Group receipts by (case, image), preserving step order.
    grouped = {}
    order = []
    for rec in receipts:
        key = (rec["case"], rec["image"])
        if key not in grouped:
            grouped[key] = []
            order.append(key)
        grouped[key].append(rec)
    check(len(grouped) == 62 * 3, f"groups {len(grouped)}")
    for case in report["cases"]:
        for image in ("original", "control", "candidate"):
            recs = grouped[(case["label"], image)]
            check([r["step"] for r in recs] == case["steps"],
                  f"{case['label']}/{image}: steps {[r['step'] for r in recs]} != {case['steps']}")
            sums = case["summaries"][image]
            check(len(sums) == len(recs), f"{case['label']}/{image}: summary count")
            for rec, s in zip(recs, sums):
                got = recompute(rec)
                for field in ("step", "error", "events", "decoded", "dPAYER", "dOUT",
                              "deltas", "withheld", "lam_deltas",
                              "pools", "pool_creator", "cfg", "uva", "gva", "mint", "lens", "site"):
                    check(got[field] == s[field],
                          f"{case['label']}/{image}/{rec['step']}: {field} {got[field]} != {s[field]}")
                # Role-address tables come from the packet's own
                # producer (constants only); every delta above is
                # recomputed from the receipt snapshots here.
                if rec["step"] == "cpatch":
                    check(rec["transaction_base64"] == "", "cpatch must carry an empty transaction")
                    check(rec["error"] is None, "cpatch must succeed")
                else:
                    tx = Transaction.from_bytes(base64.b64decode(rec["transaction_base64"]))
                    check(tx.verify_with_results() and all(tx.verify_with_results()),
                          f"{case['label']}/{image}/{rec['step']}: bad signature")
                if rec["error"] is not None:
                    signers = set()
                    if rec["transaction_base64"]:
                        tx = Transaction.from_bytes(base64.b64decode(rec["transaction_base64"]))
                        for i, k in enumerate(tx.message.account_keys):
                            if tx.message.is_signer(i):
                                signers.add(str(k))
                    for k, b in rec["before"].items():
                        a = rec["after"][k]
                        if b is None or a is None:
                            check(b == a, f"{case['label']}/{image}/{rec['step']}: rollback absent mismatch {k}")
                            continue
                        check(a["data_hex"] == b["data_hex"],
                              f"{case['label']}/{image}/{rec['step']}: rollback data mismatch {k}")
                        if a["lamports"] != b["lamports"]:
                            check(k in signers,
                                  f"{case['label']}/{image}/{rec['step']}: non-signer lamport change {k}")
            # cpatch chain consistency
            for i, rec in enumerate(recs):
                if rec["step"] == "cpatch" and i + 1 < len(recs):
                    check(recs[i + 1]["before"] == rec["after"],
                          f"{case['label']}/{image}: cpatch does not carry into next step")
        # 3-image surface agreement (fee-payer lamports stripped per receipt)
        def surface(image):
            out = []
            for rec in grouped[(case["label"], image)]:
                def strip(snap):
                    d = dict(snap)
                    if rec["transaction_base64"]:
                        tx = Transaction.from_bytes(base64.b64decode(rec["transaction_base64"]))
                        fp = str(tx.message.account_keys[0])
                        if d.get(fp) is not None:
                            d[fp] = dict(d[fp])
                            d[fp]["lamports"] = 0
                    return d
                out.append({"step": rec["step"], "error": rec["error"],
                            "events": len(rec["events"]),
                            "before": strip(rec["before"]), "after": strip(rec["after"])})
            return out
        check(surface("control") == surface("candidate"),
              f"{case['label']}: control != candidate")
        if not case["divergent"]:
            check(surface("original") == surface("control"),
                  f"{case['label']}: original diverges but not marked divergent")
    expected_divergent = {
        "B-main-cb-buy",
        "B-p2-cb-buy",
        "B-p4-cb-buy",
        "B-main-both-buy",
        "B-p4-both-buy",
        "C-main-cb-tier1-buy",
        "C-p2-cb-tier1-buy",
        "C-p4-cb-tier1-buy",
        "C-main-both-tier1-buy",
        "D-main-cb-exo-buy",
        "D-p2-cb-exo-buy",
        "E-main-cb-tier1-buy-boost",
        "E-p2-cb-tier1-buy-boost",
        "E-main-cb-exo-buy-boost",
        "E-main-cb-tier1-buy-p5boost",
        "F-main-cb-clear-tier1-buy-boost",
        "F-main-cb-stable0-buy",
        "F-main-both-tier1-clear-buy",
        "F-tier1-flag-main-cb-buy",
        "G-main-cb-gcb-off-buy",
        "G-main-cb-gcb-off-tier1-buy",
        "H-main-cb-sell",
        "H-p2-cb-sell",
        "H-main-both-sell",
        "I-main-cb-tier1-tf5000-buy",
        "J-main-cb-exo-buy-swc-p5"}
    got_divergent = {c["label"] for c in report["cases"] if c["divergent"]}
    check(got_divergent == expected_divergent,
          f"divergent set mismatch: extra={got_divergent - expected_divergent} missing={expected_divergent - got_divergent}")
    # Image hashes when the images are present at workspace paths.
    ws = HERE.parent.parent.parent
    for name, path in (("original", ws / "evidence" / "original" / "pump_amm" / "deployed.so"),
                       ("control", ws / "slop-verify" / "control.so"),
                       ("candidate", ws / "slop-verify" / "candidate.so")):
        if path.exists():
            check(sha(path.read_bytes()) == report["input_sha256"][name], f"image hash {name}")

    # Headline pins.
    def get(label, image, idx):
        case = next(c for c in report["cases"] if c["label"] == label)
        return case["summaries"][image][idx]

    def x(label, idx):
        return get(label, "original", idx)

    def err(label, image, idx):
        return str(get(label, image, idx)["error"])

    def burn(label, idx):
        return x(label, idx)["decoded"][1]["burned"]

    def cburn(label, idx):
        return get(label, "control", idx)["decoded"][1]["burned"]

    # A: anchors (bps 100, spend 1e9).
    check(x("A-buy", 0)["deltas"]["u5"] == 5207955235891, "fresh 5-hop buy tail")
    check(x("A-sell", 0)["deltas"]["userquote"] == 178541, "fresh 5-hop sell payout")
    check(burn("A-buy-boost", 2) == 5254679949141, "buy then patched boost burn")
    check(burn("A-tier1-buy-boost", 2) == 5254134170969, "tier-1 buy then patched boost burn")
    # B: mode x tier-0 buys -- the #119 split, tier-independent.
    check(x("B-main-cb-buy", 0)["error"] is None and "6079" in err("B-main-cb-buy", "control", 0) and x("B-main-cb-buy", 0)["events"] == 5 and get("B-main-cb-buy", "control", 0)["events"] == 0, "non-terminal cashback buy: original succeeds, rebuild 6079 with 0 ghosts")
    check(x("B-p2-cb-buy", 0)["error"] is None and "6079" in err("B-p2-cb-buy", "control", 0) and get("B-p2-cb-buy", "control", 0)["events"] == 1, "P2 cashback buy: rebuild 6079 with 1 ghost")
    check(x("B-p4-cb-buy", 0)["error"] is None and "6079" in err("B-p4-cb-buy", "control", 0) and get("B-p4-cb-buy", "control", 0)["events"] == 3, "P4 cashback buy: rebuild 6079 with 3 ghosts")
    check("6079" in err("B-p5-cb-buy", "original", 0) and "6079" in err("B-p5-cb-buy", "control", 0) and x("B-p5-cb-buy", 0)["events"] == 4, "terminal cashback buy: both 6079 with 4 ghosts")
    check("6080" in err("B-main-mayhem-buy", "original", 0) and "6080" in err("B-main-mayhem-buy", "control", 0), "mayhem buy: both 6080")
    check("6080" in err("B-main-both-buy", "original", 0) and "6079" in err("B-main-both-buy", "control", 0), "both-flagged buy: original 6080 first, rebuild 6079 first")
    check("6079" in err("B-p5-both-buy", "original", 0) and "6079" in err("B-p5-both-buy", "control", 0) and x("B-p5-both-buy", 0)["events"] == 4, "terminal both buy: both 6079 with 4 ghosts (cashback wins at the terminal hop on both images)")
    # C/D: the same split under tier-1 and exotic tables.
    check(x("C-main-cb-tier1-buy", 0)["deltas"]["u5"] == 5252440110816 and "6079" in err("C-main-cb-tier1-buy", "control", 0), "tier-1 does not move the non-terminal cashback split")
    check("6079" in err("C-p5-cb-tier1-buy", "original", 0) and "6079" in err("C-p5-cb-tier1-buy", "control", 0), "terminal cashback under tier-1: both 6079")
    check(x("D-main-cb-exo-buy", 0)["deltas"]["u5"] == 4824041766089 and "6079" in err("D-main-cb-exo-buy", "control", 0), "exotic does not move the non-terminal cashback split")
    check("6079" in err("D-p5-cb-exo-buy", "original", 0) and "6079" in err("D-p5-cb-exo-buy", "control", 0), "terminal cashback under exotic: both 6079")
    # E: boost under mode+tiers is mode-blind; only the failed buy changes the burn.
    check(burn("E-main-cb-tier1-buy-boost", 2) == 5254134170969 and cburn("E-main-cb-tier1-buy-boost", 2) == 5338379201831, "original burns the tier-1 post-buy value, rebuild burns the fresh anchor after its failed buy")
    check(burn("E-p5-cb-tier1-buy-boost", 2) == 5338379201831 and cburn("E-p5-cb-tier1-buy-boost", 2) == 5338379201831, "terminal cashback failure leaves the anchor boost on both images")
    check(burn("E-main-cb-tier1-buy-p5boost", 2) == 989507744 and cburn("E-main-cb-tier1-buy-p5boost", 2) == 999997999, "original P5 hop boost after a tier-1 buy is the #165 value, rebuild burns fresh after its failed buy")
    # F: masking / unmasking mid-walk.
    check(burn("F-main-cb-clear-tier1-buy-boost", 4) == 5171867765352 and cburn("F-main-cb-clear-tier1-buy-boost", 4) == 5254134170969, "clearing the flag: original accrues twice, rebuild accrues once")
    check(x("F-tier1-flag-main-cb-buy", 2)["error"] is None and "6079" in err("F-tier1-flag-main-cb-buy", "control", 2), "flagging mid-walk gates the next buy on the rebuild only")
    check(x("F-main-cb-stable0-buy", 0)["deltas"]["u5"] == 5219868625118 and "6079" in err("F-main-cb-stable0-buy", "control", 0), "stable-count-0 tail under a non-terminal cashback flag: original tail, rebuild 6079")
    check("6079" in err("F-p5-cb-flat-buy", "original", 0) and "6079" in err("F-p5-cb-flat-buy", "control", 0), "flat edit under a terminal cashback flag: both 6079")
    # G: global flags do not gate the multi-hop leg.
    check(x("G-main-cb-gcb-off-buy", 0)["error"] is None and "6079" in err("G-main-cb-gcb-off-buy", "control", 0), "global cashback off changes nothing: original succeeds, rebuild 6079")
    check("6080" in err("G-main-mayhem-gmh-off-buy", "original", 0) and "6080" in err("G-main-mayhem-gmh-off-buy", "control", 0), "global mayhem off changes nothing: both 6080")
    check("6079" in err("G-p5-cb-gcb-off-buy", "original", 0) and "6079" in err("G-p5-cb-gcb-off-buy", "control", 0), "terminal cashback with global off: both 6079")
    # H: sell direction -- ghost ladder runs terminal-first.
    check(x("H-main-cb-sell", 0)["error"] is None and "6079" in err("H-main-cb-sell", "control", 0) and get("H-main-cb-sell", "control", 0)["events"] == 4, "main cashback sell: original succeeds, rebuild 6079 with 4 ghosts")
    check("6079" in err("H-p2-cb-sell", "control", 0) and get("H-p2-cb-sell", "control", 0)["events"] == 3, "P2 cashback sell: rebuild 6079 with 3 ghosts")
    check("6079" in err("H-p5-cb-sell", "original", 0) and "6079" in err("H-p5-cb-sell", "control", 0) and x("H-p5-cb-sell", 0)["events"] == 0, "terminal cashback sell: both 6079 with 0 ghosts (terminal hop executes first)")
    check("6080" in err("H-main-both-sell", "original", 0) and "6079" in err("H-main-both-sell", "control", 0) and get("H-main-both-sell", "control", 0)["events"] == 4, "both-flagged sell: original 6080 first, rebuild 6079 first, both 4 ghosts")
    # I: tf variants do not move the gates.
    check(x("I-main-cb-tier1-tf5000-buy", 0)["deltas"]["u5"] == 2691196006460 and "6079" in err("I-main-cb-tier1-tf5000-buy", "control", 0), "tf5000 tier-1 under a non-terminal cashback flag: original tail, rebuild 6079")
    check("6079" in err("I-p5-cb-tier1-tf0-buy", "original", 0) and "6079" in err("I-p5-cb-tier1-tf0-buy", "control", 0), "tf0 terminal cashback: both 6079")
    check("6080" in err("I-main-mayhem-exo-tf5000-buy", "original", 0) and "6080" in err("I-main-mayhem-exo-tf5000-buy", "control", 0), "tf5000 mayhem exotic: both 6080")
    # J: exotic tail accrual under mode flags -- the gate, not the table, decides where the accrual lands.
    check(x("J-exo-buy-swc-p5", 1)["decoded"][0]["amount"] == 376645119766, "unflagged exotic buy: P5 creator sweep pays the tail-hop accrual")
    check(x("J-p5-cb-exo-buy-swc-p5", 1)["decoded"][0]["amount"] == 123394, "terminal cashback failure: P5 sweep pays only the fixture (no accrual exists)")
    check(x("J-main-cb-exo-buy-swc-p5", 1)["decoded"][0]["amount"] == 376645119766 and get("J-main-cb-exo-buy-swc-p5", "control", 1)["decoded"][0]["amount"] == 123394, "non-terminal cashback: original accrues to P5 and sweeps it, rebuild sweeps only the fixture")
    print("PASS: 62 cases, 294 receipts, 30 parts, true 5-hop split x boost x tf mode x fee-table chains, per-image expectations hold (signatures, deltas, withheld, lamports, events, error codes, rollback, pool/config/UVA/GVA/mint fields, account lengths, cpatch harness resets, mode-gate split terminal-only vs every-hop 6079, mayhem 6080 both images, both-flagged priority 6080 vs 6079, ghost ladders buy and sell directions, tier-invariant gate pattern, global-flag blindness, boost mode-blindness under tiers, exotic tail accrual gated by the buy not the table, tf variants); control == candidate everywhere; original diverges in exactly 26 mode-gate cases (see expected_divergent)")
if __name__ == "__main__":
    main()
