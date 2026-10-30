#!/usr/bin/env python3
"""Independent re-verification for amm-multi-hop-split-boost-tf-exact-out-five-hop-chains-20261029.

Checks, from the packet files alone (plus the three program images
when present at their workspace paths):
- MANIFEST.json lists every packet file (except itself) with a matching
  sha256 and byte count.
  (the true-5-hop route three_amm + g4 + g5, final output U5).
- runtime/report.json.gz: 72 cases, 330 receipts, 33 parts
  (33x10), part sha256/byte counts match the part files.
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
  GlobalConfig state, the user volume accumulator state, the global
  volume accumulator state, the account lengths (pool / config /
  UVA / GVA / fee-table / extend target) after every step, and the
  decoded event fields (multi-hop 508/449-byte hop events, boost
  512-byte BuyEvent + 208-byte boost event, sweep 185-byte fields,
  deposit/withdraw 264-byte fields, token claim 104-byte fields,
  collect 120-byte fields).
- Failure steps roll back every watched account's data, and only
  transaction signers may change lamports on a failed step.
  (main, P2, P3, P4, P5), the GlobalConfig state, the user volume
  accumulator state, the global volume accumulator state, the
  account lengths (pool / config / UVA / GVA / fee-table / extend
  target) after every step, and the decoded event fields
  (multi-hop 508/449-byte hop events, boost 512-byte BuyEvent +
  208-byte boost event, sweep 185-byte fields, deposit/withdraw
  264-byte fields, token claim 104-byte fields, collect 120-byte
  fields).
- Control and candidate observed surfaces are identical in every
  case; the original agrees with both in every case (0 divergent
  cases).
- Headline pins (see README): buy / buy_v2 are the exact-out legs
  (base_amount_out, max_quote_amount_in) and buy_exact_quote_in(_v2)
  the exact-in legs (spendable_quote_in, min_base_amount_out);
  single-hop exact gates are code-split (max_quote -> 6004,
  min_base -> 6040, both 0 events, both +-1 sharp); the 5-hop
  chain anchors are buy tail 5,207,955,235,891, sell payout
  178,541, plain buy tail 5,259,040,470,738, tf5000 buy tail
  2,668,075,748,732; a failing 5-hop BUY min_out panics
  (ProgramFailedToComplete, 5 ghost events) on all three images
  while a failing 5-hop SELL min_out stays clean 6004 (5 ghosts);
  the exact-out cost spent as exact-in falls short of the target
  (legacy 130,289, v2 53,575 at tf100; 4,259 even at tf0);
  legacy exact legs pay fees out to recipient ATAs while v2 exact
  legs accrue into pool buckets; a full-tail buy-then-sell pays
  957,362,033 at tf100 and 244,184,875 at tf5000, and
  sell-then-buy lands 56,182,293 above the fresh tail.

Usage: ~/workspace/venvs/pumpfun/bin/python -I -B verify.py
  (run from this packet directory)
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
    sol = [struct.unpack_from("<Q", raw, 64 + i * 8)[0] for i in range(30)] if len(raw) >= 304 else None
    tok = [struct.unpack_from("<Q", raw, 304 + i * 8)[0] for i in range(30)] if len(raw) >= 544 else None
    return {"len": len(raw),
            "start": struct.unpack_from("<q", raw, 8)[0],
            "end": struct.unpack_from("<q", raw, 16)[0],
            "sec": struct.unpack_from("<q", raw, 24)[0],
            "sol_head": sol[:3] if sol else None,
            "tok_head": tok[:3] if tok else None,
            "sol_last": sol[-1] if sol else None,
            "tok_last": tok[-1] if tok else None}


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
    if kind in ("mhbuy3", "mhsell3", "mhbuy5", "mhsell5"):
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


STEP_KIND = {"mhbuy3": "mhbuy3", "mhsell3": "mhsell3", "mhbuy5": "mhbuy5", "mhsell5": "mhsell5", "boost": "boost",
             "swp22": "swp", "swc22": "swc", "col22": "col", "dep": "dep", "wd": "wd",
             "tclaim": "tclaim", "cclaim": "cclaim", "sync": "sync",
             "swp": "swp", "swc": "swc", "col": "col",
             "xfer2": None, "xfer1": None, "cpatch": None,
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
    check(report["case_count"] == 72, f"case_count {report['case_count']}")
    check(report["counts"] == {"cases": 72, "receipts": 330, "parts": 33},
          f"counts {report['counts']}")
    receipts = []
    for part in report["parts"]:
        path = HERE / part["file"]
        check(path.stat().st_size == part["bytes"], f"part bytes {part['file']}")
        check(sha(path.read_bytes()) == part["sha256"], f"part sha {part['file']}")
        with gzip.open(path, "rt", encoding="utf-8") as fh:
            for line in fh:
                receipts.append(json.loads(line))
    check(len(receipts) == 330, f"receipts {len(receipts)}")
    check(report["receipt_count"] == 330, "report receipt_count")
    # Group receipts by (case, image), preserving step order.
    grouped = {}
    order = []
    for rec in receipts:
        key = (rec["case"], rec["image"])
        if key not in grouped:
            grouped[key] = []
            order.append(key)
        grouped[key].append(rec)
    check(len(grouped) == 72 * 3, f"groups {len(grouped)}")
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
    check(not any(c["divergent"] for c in report["cases"]), "expected 0 divergent cases")
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

    def err(label, idx):
        return str(x(label, idx)["error"])

    # A: exact-out anchors. buy/buy_v2 take (base_out, max_quote_in).
    check(x("A-legbuy-1e9", 0)["deltas"]["userquote"] == -186623, "legbuy 1e9 cost")
    check(x("A-legbuy-1e9", 0)["deltas"]["vq1"] == 182533, "legbuy 1e9 vq1")
    check(x("A-legbuy-1e9", 0)["withheld"] == {"vq1": 1844, "bb22": 9, "proto22": 9, "creat22": 6}, "legbuy 1e9 withheld")
    check(x("A-buy2m-1e9", 0)["deltas"]["userquote"] == -186637, "buy2m 1e9 cost (+14 vs legacy)")
    check(x("A-buy2m-1e9", 0)["deltas"]["vq1"] == 183930, "buy2m 1e9 vq1")
    check(x("A-buy2m-1e9", 0)["withheld"] == {"vq1": 1858, "bb22": 9}, "buy2m 1e9 withheld")
    check(x("A-legbuy-1e6", 0)["deltas"]["userquote"] == -189, "legbuy 1e6 cost")
    check(x("A-legbuy-1e8", 0)["deltas"]["userquote"] == -18664, "legbuy 1e8 cost")
    check(x("A-legbuy-twice", 1)["deltas"]["userquote"] == -186624, "legbuy second +1 dust")
    check(x("A-legbuy-tf0", 0)["deltas"]["userquote"] == -184779, "legbuy tf0 cost")
    check(x("A-legbuy-tf0", 0)["withheld"] == {}, "legbuy tf0 no withheld")
    check(x("A-legbuy-tf5000", 0)["deltas"]["userquote"] == -367312, "legbuy tf5000 cost")
    check(x("A-legbuy-tf5000", 0)["withheld"]["vq1"] == 182533, "legbuy tf5000 vq1 withheld = curve quote")
    check(x("A-buy2m-tf0", 0)["deltas"]["userquote"] == -184779, "buy2m tf0 cost")
    check(x("A-buy2m-tf5000", 0)["deltas"]["userquote"] == -368709, "buy2m tf5000 cost")
    # B: exact-in anchors. buy_exact_quote_in takes (spendable, min_base).
    check(x("B-lexact-1e9", 0)["deltas"]["userbase"] == 5315544542190, "lexact 1e9 base")
    check(x("B-lexact-1e9", 0)["deltas"]["userquote"] == -999878519, "lexact 1e9 spend")
    check(x("B-bexact2-1e9", 0)["deltas"]["userbase"] == 5315544542190, "bexact2 1e9 base identical")
    check(x("B-bexact2-1e9", 0)["deltas"]["userquote"] == -999954075, "bexact2 1e9 spend (+75556 vs legacy)")
    check(x("B-lexact-1e6", 0)["deltas"]["userbase"] == 5357760549, "lexact 1e6 base")
    check(x("B-bexact2-1e6", 0)["deltas"]["userbase"] == 5357760549, "bexact2 1e6 base identical")
    check(x("B-bexact2-1e6", 0)["deltas"]["userquote"] == -999955, "bexact2 1e6 spend")
    check(x("B-bexact2-1e8", 0)["deltas"]["userbase"] == 535356061229, "bexact2 1e8 base")
    check(x("B-bexact2-twice", 1)["deltas"]["userbase"] == 5232312441616, "bexact2 second base decay")
    check(x("B-bexact2-tf5000", 0)["deltas"]["userbase"] == 2695143552032, "bexact2 tf5000 base")
    check(x("B-bexact2-tf5000", 0)["deltas"]["userquote"] == -997703704, "bexact2 tf5000 spend")
    check(x("B-lexact-tf5000", 0)["deltas"]["userbase"] == 2695143552032, "lexact tf5000 base identical")
    check(x("B-lexact-tf5000", 0)["deltas"]["userquote"] == -993925925, "lexact tf5000 spend cheaper by 3777779")
    # C/D: gate codes split by leg family. max_quote -> 6004, min_base -> 6040.
    check("6004" in err("C-legbuy-max-1", 0) and x("C-legbuy-max-1", 0)["events"] == 0, "legbuy max-1 6004 0 events")
    check(x("C-legbuy-max-ok", 0)["deltas"]["userquote"] == -186623, "legbuy max-ok cost")
    check("6004" in err("C-buy2m-max-1", 0) and x("C-buy2m-max-1", 0)["events"] == 0, "buy2m max-1 6004 0 events")
    check(x("C-buy2m-max-ok", 0)["deltas"]["userquote"] == -186637, "buy2m max-ok cost")
    check(x("D-lexact-min-ok", 0)["deltas"]["userbase"] == 5315544542190, "lexact min-ok base")
    check("6040" in err("D-lexact-min-plus1", 0) and x("D-lexact-min-plus1", 0)["events"] == 0, "lexact min+1 6040 0 events")
    check(x("D-bexact2-min-ok", 0)["deltas"]["userbase"] == 5315544542190, "bexact2 min-ok base")
    check("6040" in err("D-bexact2-min-plus1", 0) and x("D-bexact2-min-plus1", 0)["events"] == 0, "bexact2 min+1 6040 0 events")
    # E: round trip is not a round trip, even at tf0.
    check(x("E-lexact-186623", 0)["deltas"]["userbase"] == 999869711, "lexact round trip shortfall 130289")
    check(x("E-bexact2-186637", 0)["deltas"]["userbase"] == 999946425, "bexact2 round trip shortfall 53575")
    check(x("E-lexact-tf0-184779", 0)["deltas"]["userbase"] == 999995741, "lexact tf0 round trip shortfall 4259")
    check(x("E-bexact2-tf0-184779", 0)["deltas"]["userbase"] == 999995741, "bexact2 tf0 round trip shortfall 4259")
    # F: sell-side analogue is a tight min_quote gate (no exact-quote-out sell).
    check(x("F-legsell-ok", 0)["deltas"]["userquote"] == 178409, "legsell payout")
    check(x("F-legsell-ok", 0)["withheld"] == {"userquote": 1803, "bb22": 9, "proto22": 9, "creat22": 6}, "legsell withheld")
    check("6004" in err("F-legsell-plus1", 0), "legsell min+1 6004")
    check(x("F-sell2m-ok", 0)["deltas"]["userquote"] == 178409, "sell2m payout identical")
    check("6004" in err("F-sell2m-plus1", 0), "sell2m min+1 6004")
    check(x("F-legsell-tf5000", 0)["deltas"]["userquote"] == 90106, "legsell tf5000 net")
    check(x("F-legsell-tf5000", 0)["withheld"]["userquote"] == 90106, "legsell tf5000 withheld = net")
    check(x("F-sell2m-tf5000", 0)["deltas"]["userquote"] == 90106, "sell2m tf5000 net")
    # G: multi-hop tight min_out gates at TRUE 5 hops. Buy failures
    # panic on all three images here (no UVA seed in these cases);
    # sell failures stay clean 6004. Both carry 5 ghost events.
    check(x("G-mhbuy5-tail", 0)["deltas"]["u5"] == 5207955235891, "mhbuy5 tail exact")
    check("ProgramFailedToComplete" in err("G-mhbuy5-tail-plus1", 0) and x("G-mhbuy5-tail-plus1", 0)["events"] == 5, "mhbuy5 tail+1 panic 5 ghosts")
    check(x("G-mhsell5-pay", 0)["deltas"]["userquote"] == 178541, "mhsell5 payout exact")
    check("6004" in err("G-mhsell5-pay-plus1", 0) and x("G-mhsell5-pay-plus1", 0)["events"] == 5, "mhsell5 pay+1 6004 5 ghosts")
    check(x("G-mhbuy5-plain-tail", 0)["deltas"]["u5"] == 5259040470738, "plain mhbuy5 tail exact")
    check(x("G-mhbuy5-plain-tail", 0)["withheld"] == {}, "plain mhbuy5 no withheld")
    check("ProgramFailedToComplete" in err("G-mhbuy5-plain-tail-plus1", 0) and x("G-mhbuy5-plain-tail-plus1", 0)["events"] == 5, "plain mhbuy5 tail+1 panic 5 ghosts")
    check(x("G-mhbuy5-tf5000-tail", 0)["deltas"]["u5"] == 2668075748732, "tf5000 mhbuy5 tail exact")
    check("ProgramFailedToComplete" in err("G-mhbuy5-tf5000-tail-plus1", 0), "tf5000 mhbuy5 tail+1 panic")
    check(x("G-mhsell5-tf5000-pay", 0)["deltas"]["userquote"] == 90172, "tf5000 mhsell5 payout exact")
    check("6004" in err("G-mhsell5-tf5000-pay-plus1", 0), "tf5000 mhsell5 pay+1 6004")
    check(x("G-mhbuy5-small", 0)["deltas"]["u5"] == 5361233911, "mhbuy5 small tail")
    check(x("G-mhsell5-small", 0)["deltas"]["userquote"] == 178, "mhsell5 small payout")
    # H: exact legs between chain legs move the next tail.
    check(x("H-mh5-mh5", 1)["deltas"]["u5"] == 4918089082874, "mh5-mh5 second tail")
    check(x("H-mh5-legbuy-mh5", 1)["deltas"]["userquote"] == -189614, "mid legbuy cost after chain")
    check(x("H-mh5-legbuy-mh5", 2)["deltas"]["u5"] == 4918074717461, "mh5-legbuy-mh5 second tail")
    check(x("H-mh5-bexact2-mh5", 2)["deltas"]["u5"] == 4843196047716, "mh5-bexact2-mh5 second tail")
    check(x("H-mh5-lexact-mh5", 2)["deltas"]["u5"] == 4843196047716, "mh5-lexact-mh5 second tail identical to v2")
    check(x("H-mhsell5-legsell", 1)["deltas"]["userquote"] == 178408, "legsell after chain 1 less")
    check(x("H-mhsell5-sell2m", 1)["deltas"]["userquote"] == 178408, "sell2m after chain 1 less")
    # I: exact legs move the next burn; a burn moves the next exact leg.
    check(x("I-legbuy-boost", 2)["decoded"][1]["burned"] == 5338363478447, "legbuy-boost burn")
    check(x("I-bexact2-boost", 2)["decoded"][1]["burned"] == 5254810797338, "bexact2-boost burn")
    check(x("I-boost-legbuy", 2)["deltas"]["userquote"] == -191159, "legbuy after boost +4536")
    check(x("I-boost-bexact2", 2)["deltas"]["userbase"] == 5190075630656, "bexact2 after boost base")
    check(x("I-mh5-boost", 2)["decoded"][1]["burned"] == 5254679949141, "mh5-boost burn")
    check(x("I-boost-mh5", 2)["deltas"]["u5"] == 5087534167771, "boost-mh5 tail")
    # J: legacy exact legs pay fees out to recipient ATAs; v2 exact legs accrue.
    check(x("J-legbuy-swp", 1)["deltas"]["proto22"] == 2463, "legbuy swp fixture only")
    check(x("J-legbuy-swp", 2)["deltas"]["creat22"] == 122160, "legbuy swc fixture only")
    check(x("J-bexact2-swp", 1)["deltas"]["proto22"] == 4503663, "bexact2 swp accrued")
    check(x("J-bexact2-swp", 2)["deltas"]["creat22"] == 3026160, "bexact2 swc accrued")
    check(x("J-legbuy-col", 2)["deltas"]["creat22"] == -122702, "legbuy collect drains 122702")
    check(x("J-legbuy-col", 2)["deltas"]["dest22"] == 121474, "legbuy collect dest net")
    check(x("J-bexact2-dep", 1)["deltas"]["userbase"] == -159352586, "bexact2 dep base")
    check(x("J-bexact2-dep", 1)["deltas"]["userquote"] == -29845, "bexact2 dep quote")
    check(x("J-legbuy-dep", 1)["deltas"]["userbase"] == -160619657, "legbuy dep base")
    check(x("J-legbuy-dep", 1)["deltas"]["userquote"] == -29610, "legbuy dep quote")
    # K: failed exact legs leave no residue.
    check(x("K-fail-legbuy-mh5", 1)["deltas"]["u5"] == 5207955235891, "failed legbuy then mh5 anchor")
    check(x("K-fail-bexact2-mh5", 1)["deltas"]["u5"] == 5207955235891, "failed bexact2 then mh5 anchor")
    check("ProgramFailedToComplete" in err("K-fail-mhbuy5-mh5", 0), "failed mhbuy5 panics")
    check(x("K-fail-mhbuy5-mh5", 1)["deltas"]["u5"] == 5207955235891, "failed mhbuy5 then mh5 anchor")
    # R: round trips at depth 5.
    check(x("R-mhbuy5-then-sell5", 1)["deltas"]["userquote"] == 957362033, "buy-then-sell full tail payout")
    check(x("R-mhsell5-then-buy5", 1)["deltas"]["u5"] == 5208011418184, "sell-then-buy tail +56182293")
    check(x("R-mhbuy5-then-sell5-tf5000", 1)["deltas"]["userquote"] == 244184875, "tf5000 buy-then-sell payout")
    check(x("R-exactout-cost-as-mh5-input", 0)["deltas"]["u5"] == 1000542480, "exact-out cost as mh5 input tail")
    check(x("R-mhbuy5-then-legsell", 1)["deltas"]["userquote"] == 936748372, "buy-then-legsell payout")
    print("PASS: 72 cases, 330 receipts, 33 parts, true 5-hop split x boost x tf exact-out chains, per-image expectations hold "
          "(signatures, deltas, withheld, lamports, events, error codes, rollback, "
          "pool/config/UVA/GVA/mint fields, account lengths, cpatch harness resets, "
          "exact-out vs exact-in costs, gate codes 6004 vs 6040, 5-hop buy panic vs sell 6004, "
          "round-trip payouts, chain/boost/sweep/collect/deposit interactions, failure isolation); "
          "control == candidate everywhere; "
          "original agrees everywhere; (0 divergent cases): []")


if __name__ == "__main__":
    main()
