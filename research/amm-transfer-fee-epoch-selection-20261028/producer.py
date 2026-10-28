#!/usr/bin/env python3
"""Build research/amm-transfer-fee-epoch-selection-20261028 receipts.

from_mint selects the schedule active at the current epoch with
`if epoch >= newer.epoch { newer } else { older }`. This packet pins
the rule at runtime: the boundary is inclusive (epoch == newer.epoch
already selects newer), and an inverted pair (older.epoch > newer.epoch)
applies the future-dated older schedule while the clock is before the
newer epoch. Each case burns supply//100 LP in a withdraw and reads the
fee actually withheld from the vault->user quote transfer, so the
selected schedule is observable in the after balances.
"""
import base64
import gzip
import hashlib
import json
import struct
import sys
from pathlib import Path
from types import SimpleNamespace

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
    CONFIG, CONFIG_KEY, EVENT, IDL, OUTSIDER, PAYER, PROGRAM, RAW, TOKEN, TOKEN22,
    base, f, lp, pool, poolraw, quote, supply, token, userbase,
    userlp, userquote, vaultbase, vaultquote,
)

ROOT = Path.home() / "workspace/pumpfun-sparse"
OUT = ROOT / "research/amm-transfer-fee-epoch-selection-20261028"
WS = Path.home() / "workspace/slop-verify"

IMAGES = {
    "original": ROOT / "evidence/original/pump_amm/deployed.so",
    "control": WS / "control.so",
    "candidate": WS / "candidate.so",
}
IMAGE_SHA = {
    "original": "6a7ad34596d83b4c435b32f458a56e718e9f82eb4ad38e4316616d15d24d8ff7",
    "control": "7a300434dced61413bde10788594b427d5649563e0223efcf09e6b214aff7ad3",
    "candidate": "d17a657baf5cc19736a924c41e75424604411ddbe9f6e72cddf41ab72a695007",
}

AMOUNT = supply // 100
MAXFEE = 2**64 - 1
CASES = [
    # (label, older_epoch, older_bps, newer_epoch, newer_bps, clock_epoch, expected_bps)
    ("epoch-0-before-newer", 0, 100, 10, 200, 0, 100),
    ("epoch-9-before-newer", 0, 100, 10, 200, 9, 100),
    ("epoch-10-at-newer", 0, 100, 10, 200, 10, 200),
    ("inverted-epoch-0", 100, 100, 50, 200, 0, 100),
    ("inverted-epoch-49", 100, 100, 50, 200, 49, 100),
    ("inverted-epoch-50", 100, 100, 50, 200, 50, 200),
    ("tie-epoch-10", 10, 100, 10, 200, 10, 200),
    ("tie-epoch-9", 10, 100, 10, 200, 9, 100),
]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def snap(vm, keys):
    out = {}
    for k in keys:
        a = vm.get_account(k)
        out[str(k)] = {"owner": str(a.owner), "lamports": a.lamports,
                       "executable": a.executable, "data_hex": a.data.hex()} if a else None
    return out


def amount_at(data, offset):
    return struct.unpack_from("<Q", bytes.fromhex(data), offset)[0]


def fee_epochs(old_epoch, old_bps, new_epoch, new_bps):
    def apply(h, m):
        mint = h.vm.get_account(quote)
        d = bytearray(mint.data[:82])
        d += bytes(83) + bytes([1])
        conf = bytes(72) + struct.pack("<QQH", old_epoch, MAXFEE, old_bps) + \
            struct.pack("<QQH", new_epoch, MAXFEE, new_bps)
        d += struct.pack("<HH", 1, len(conf)) + conf
        h.vm.set_account(quote, Account(mint.lamports, bytes(d), TOKEN22))
        for k in (userquote, vaultquote):
            a = h.vm.get_account(k)
            dd = bytearray(a.data[:165])
            dd += bytes([2]) + struct.pack("<HHQ", 2, 8, 0)
            h.vm.set_account(k, Account(a.lamports, bytes(dd), TOKEN22))
    return apply


receipts_global = []
report_cases = []
for index, (label, oe, ob, ne, nb, clock_epoch, expected_bps) in enumerate(CASES):
    ix = next(x for x in IDL["instructions"] if x["name"] == "withdraw")
    metas = [AccountMeta(k, sign, w) for k, sign, w in [
        (pool, False, True), (CONFIG_KEY, False, False), (PAYER.pubkey(), True, False),
        (base, False, False), (quote, False, False), (lp, False, True),
        (userbase, False, True), (userquote, False, True), (userlp, False, True),
        (vaultbase, False, True), (vaultquote, False, True),
        (TOKEN, False, False), (TOKEN22, False, False),
        (EVENT, False, False), (PROGRAM, False, False)]]
    row = {"case": {"instruction": "withdraw", "label": label,
                    "older": {"epoch": oe, "bps": ob},
                    "newer": {"epoch": ne, "bps": nb},
                    "clock_epoch": clock_epoch, "expected_bps": expected_bps,
                    "lp_token_amount_in": AMOUNT}}
    received_set = set()
    for image_offset, image in enumerate(("original", "control", "candidate")):
        h = Harness(IMAGES[image])
        vm = h.vm
        vm.set_clock(Clock(100, 1234567890, clock_epoch, 0, 1234567890))
        for pid, path in ((TOKEN, "evidence/dependencies/spl_token/deployed.so"),
                          (TOKEN22, "evidence/dependencies/spl_token_2022/deployed.so")):
            vm.add_program_from_file(pid, str(ROOT / path))
        glob = bytearray(RAW)
        glob[56] = 0
        vm.set_account(CONFIG_KEY, Account(CONFIG["lamports"], bytes(glob), PROGRAM))
        for n in ["base_mint", "quote_mint", "pool_base_token_account", "pool_quote_token_account"]:
            rrow = f["accounts"][n]
            vm.set_account(Pubkey.from_string(f["keys"][n]),
                           Account(rrow["lamports"], base64.b64decode(rrow["data_base64"]),
                                   Pubkey.from_string(rrow["owner"])))
        data = bytearray(poolraw)
        data[245:261] = (0).to_bytes(16, "little", signed=True)
        data[271:287] = bytes(16)
        vm.set_account(pool, Account(f["accounts"]["pool"]["lamports"], bytes(data), PROGRAM))
        mint = struct.pack("<I", 1) + bytes(pool) + struct.pack("<Q", supply) + bytes([9, 1]) + bytes(36)
        vm.set_account(lp, Account(10**9, mint, TOKEN22))
        for k, m, own, amt, nat in ((userbase, base, TOKEN, 10**15, False),
                                    (userquote, quote, TOKEN, 10**15, True),
                                    (userlp, lp, TOKEN22, supply // 2, False)):
            vm.set_account(k, Account(amt + 2039280 if nat else 10**9,
                                      token(m, PAYER.pubkey(), amt, nat), own))
        fee_epochs(oe, ob, ne, nb)(SimpleNamespace(vm=vm), metas)
        args = bytes(ix["discriminator"]) + struct.pack("<QQQ", AMOUNT, 0, 0)
        before_keys = sorted({str(m.pubkey) for m in metas}, key=str)
        before = snap(vm, [Pubkey.from_string(k) for k in before_keys])
        tx = Transaction.new_signed_with_payer(
            [Instruction(PROGRAM, args, metas)], PAYER.pubkey(), [PAYER], vm.latest_blockhash())
        raw = bytes(tx)
        checks = tx.verify_with_results()
        assert checks and all(checks), "new transaction must verify"
        r = vm.send_transaction(tx)
        failed = isinstance(r, FailedTransactionMetadata)
        meta = r.meta() if failed else r
        after = snap(vm, [Pubkey.from_string(k) for k in before_keys])
        err = str(r.err()) if failed else None
        logs = meta.logs()
        assert not failed and err is None, (label, image, err, logs[-3:])
        vq, uq = str(vaultquote), str(userquote)
        sent = amount_at(before[vq]["data_hex"], 64) - amount_at(after[vq]["data_hex"], 64)
        received = amount_at(after[uq]["data_hex"], 64) - amount_at(before[uq]["data_hex"], 64)
        fee = sent - received
        expect_fee = min((sent * expected_bps + 9999) // 10000, MAXFEE)
        assert fee == expect_fee, (label, image, sent, received, fee, expect_fee)
        received_set.add(received)
        payer = str(PAYER.pubkey())
        payer_delta = before[payer]["lamports"] - after[payer]["lamports"]
        receipts_global.append({
            "sequence": len(receipts_global), "vm": len(receipts_global),
            "context": {"index": index, "image": image, "instruction": "withdraw",
                        "label": label},
            "transaction_base64": base64.b64encode(raw).decode(),
            "signatures": [str(s) for s in tx.signatures],
            "transaction_sha256": sha(raw),
            "all_signatures_verified": True, "signature_fields": 1,
            "before": before, "after": after,
            "metadata": {"signature": str(meta.signature()), "logs": logs,
                         "inner_instructions": str(meta.inner_instructions()),
                         "compute_units_consumed": str(meta.compute_units_consumed()),
                         "return_data": str(meta.return_data())},
            "clock": {"slot": 100, "epoch_start_timestamp": 1234567890, "epoch": clock_epoch,
                      "leader_schedule_epoch": 0, "unix_timestamp": 1234567890},
            "loaded_programs": {
                str(PROGRAM): {"path": "evidence/original/pump_amm/deployed.so",
                               "sha256": IMAGE_SHA[image]},
                str(TOKEN): {"path": "evidence/dependencies/spl_token/deployed.so",
                             "sha256": "8190d3f7ceb6cb7a7a8d8924bff89f9f611e15ce1f806f2b6237f3311a98f697"},
                str(TOKEN22): {"path": "evidence/dependencies/spl_token_2022/deployed.so",
                               "sha256": "15a2e615a42e20f31714bbaaee43002ae6f1cda2e8d7118243117ab3c1342e2d"}},
            "error": err, "rollback_except_payer_fee": False,
            "payer_fee_lamports": payer_delta,
            "observed": {"quote_sent": sent, "quote_received": received, "fee": fee,
                         "selected_bps": expected_bps},
        })
        row[image] = {"error": err, "logs": logs,
                      "accounts": {k: v for k, v in after.items()},
                      "observed": {"quote_sent": sent, "quote_received": received,
                                   "fee": fee, "selected_bps": expected_bps}}
        print(f"  {label} [{image}] sent={sent} received={received} fee={fee} bps={expected_bps}")
    assert len(received_set) == 1, (label, "images must agree on the selected schedule")
    report_cases.append(row)

(OUT / "runtime").mkdir(parents=True, exist_ok=True)
raw = b"\n".join(json.dumps(r).encode() for r in receipts_global) + b"\n"
(OUT / "runtime/raw-transactions.jsonl.gz").write_bytes(gzip.compress(raw, mtime=0))
report = {
    "scope": "Fresh normally signed original/control/candidate triples pinning the "
             "epoch schedule selection in from_mint (`if epoch >= "
             "newer.epoch { newer } else { older }`) at runtime. Each case "
             "burns supply//100 LP in a withdraw with older/newer fee "
             "schedules at distinct basis points, and reads the fee "
             "actually withheld from the vault->user quote transfer, so "
             "the selected schedule is observable in the after balances. "
             "The boundary is inclusive (epoch == newer.epoch already "
             "selects newer), and an inverted pair (older.epoch > "
             "newer.epoch) applies the future-dated older schedule while "
             "the clock is before the newer epoch. All three images select "
             "the same schedule in every case.",
    "fresh_vm_environment": "1",
    "image_sha256": IMAGE_SHA,
    "input_sha256": {
        "research/imported-lab/analysis/pump_fun/amm-v2-trade-fixture.json":
            sha((ROOT / "research/imported-lab/analysis/pump_fun/amm-v2-trade-fixture.json").read_bytes()),
        "research/imported-lab/analysis/pump_fun/config-snapshot.json":
            sha((ROOT / "research/imported-lab/analysis/pump_fun/config-snapshot.json").read_bytes()),
        "evidence/upstream/pump_amm.json":
            sha((ROOT / "evidence/upstream/pump_amm.json").read_bytes()),
        "evidence/dependencies/spl_token/deployed.so":
            sha((ROOT / "evidence/dependencies/spl_token/deployed.so").read_bytes()),
        "evidence/dependencies/spl_token_2022/deployed.so":
            sha((ROOT / "evidence/dependencies/spl_token_2022/deployed.so").read_bytes()),
    },
    "counts": {"vms": len(receipts_global), "transactions": len(receipts_global),
               "signature_fields": len(receipts_global)},
    "case_count": len(report_cases),
    "classifications": {"epoch-selection": 8},
    "mismatches": [],
    "cases": report_cases,
    "transaction_receipts": {"path": "raw-transactions.jsonl.gz",
                             "sha256": sha((OUT / "runtime/raw-transactions.jsonl.gz").read_bytes())},
}
(OUT / "runtime/report.json.gz").write_bytes(gzip.compress(
    json.dumps(report, indent=1).encode(), mtime=0))
print("cases:", len(report_cases), "receipts:", len(receipts_global))
print("wrote:", OUT / "runtime/report.json.gz")
