"""Verify the retained epoch-selection receipts (no build claimed).

Checks, independently of the producer:
- packet manifest lists exactly the files present, with matching hashes;
- repository inputs (images, trade fixture, IDL, evidence programs)
  hash to the recorded values;
- 8 cases x 3 images = 24 receipts, ordered, with contexts matching the report;
- every transaction verifies (all signatures valid, 1 signature field);
- every receipt's clock epoch matches the case, and the quote mint's
  before snapshot carries the case's older/newer epoch and bps pairs at
  the TLV offsets (epochs @242/@260, bps @258/@276, max @250/@268);
- every receipt succeeded, and the fee actually withheld (vault outflow
  minus user inflow) equals ceil(sent * selected_bps / 10000) capped at
  the maximum fee, with the selected bps matching the case expectation;
- all three images agree on the received amount in every case;
- the payer's lamport delta is exactly the 5000 fee.
"""
import base64
import gzip
import hashlib
import json
import struct
import sys
from pathlib import Path

from solders.transaction import Transaction

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from pump_amm_liquidity_differential import userquote as USERQUOTE_KEY  # noqa: E402
from pump_amm_liquidity_differential import vaultquote as VAULT_KEY  # noqa: E402

if not __debug__:
    raise SystemExit("Run without -O")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
MINT_KEY = "So11111111111111111111111111111111111111112"
IMAGES = ("original", "control", "candidate")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def amount_at(data_hex, offset):
    return struct.unpack_from("<Q", bytes.fromhex(data_hex), offset)[0]


def main():
    paths = list(HERE.rglob("*"))
    assert not any(p.is_symlink() for p in paths)
    manifest = json.loads((HERE / "MANIFEST.json").read_text())
    files = {p.relative_to(HERE).as_posix() for p in paths
             if p.is_file() and p.name != "MANIFEST.json"}
    assert files == set(manifest["files"]), sorted(files ^ set(manifest["files"]))
    for name, digest in manifest["files"].items():
        assert sha((HERE / name).read_bytes()) == digest, name
    for name, digest in manifest["repository_inputs"].items():
        path = ROOT / name
        assert path.is_file() and not path.is_symlink(), name
        assert sha(path.read_bytes()) == digest, name

    report = json.loads(gzip.decompress((HERE / "runtime/report.json.gz").read_bytes()))
    receipt_data = (HERE / "runtime/raw-transactions.jsonl.gz").read_bytes()
    receipts = [json.loads(line) for line in gzip.decompress(receipt_data).splitlines()]
    assert report["case_count"] == len(report["cases"]) == 8
    assert len(receipts) == 24
    assert report["transaction_receipts"] == {
        "path": "raw-transactions.jsonl.gz", "sha256": sha(receipt_data)}
    assert report["counts"] == {"vms": 24, "transactions": 24, "signature_fields": 24}
    assert report["mismatches"] == []
    assert report["image_sha256"] == {
        "original": sha((ROOT / "evidence/original/pump_amm/deployed.so").read_bytes()),
        "control": sha(gzip.decompress((ROOT / "research/amm-multi-hop-group-slice-recovery"
                                        "/artifacts/candidate.so.gz").read_bytes())),
        "candidate": sha(gzip.decompress((ROOT / "research/amm-transfer-fee-diagnostic-recovery"
                                          "/artifacts/candidate.so.gz").read_bytes())),
    }
    for name, digest in report["input_sha256"].items():
        assert sha((ROOT / name).read_bytes()) == digest, name

    for index, row in enumerate(report["cases"]):
        case = row["case"]
        assert case["lp_token_amount_in"] > 0
        received_set = set()
        for image_offset, image in enumerate(IMAGES):
            rec = receipts[index * 3 + image_offset]
            assert rec["sequence"] == rec["vm"] == index * 3 + image_offset
            assert rec["context"] == {"index": index, "image": image,
                                      "instruction": "withdraw",
                                      "label": case["label"]}
            assert rec["clock"]["epoch"] == case["clock_epoch"]
            assert rec["clock"]["slot"] == 100
            raw = base64.b64decode(rec["transaction_base64"], validate=True)
            tx = Transaction.from_bytes(raw)
            checks = tx.verify_with_results()
            assert checks and all(checks) and len(checks) == 1
            assert rec["all_signatures_verified"] and rec["signature_fields"] == 1
            assert sha(raw) == rec["transaction_sha256"]
            assert [str(s) for s in tx.signatures] == rec["signatures"]
            assert rec["loaded_programs"][next(
                k for k in rec["loaded_programs"] if k.startswith("pAMM"))]["sha256"] == \
                report["image_sha256"][image]
            mint = bytes.fromhex(rec["before"][MINT_KEY]["data_hex"])
            assert mint[166:168] == b"\x01\x00" and int.from_bytes(mint[168:170], "little") == 108
            assert struct.unpack_from("<Q", mint, 242)[0] == case["older"]["epoch"]
            assert struct.unpack_from("<H", mint, 258)[0] == case["older"]["bps"]
            assert struct.unpack_from("<Q", mint, 260)[0] == case["newer"]["epoch"]
            assert struct.unpack_from("<H", mint, 276)[0] == case["newer"]["bps"]
            assert struct.unpack_from("<Q", mint, 250)[0] == 2**64 - 1
            assert struct.unpack_from("<Q", mint, 268)[0] == 2**64 - 1
            assert rec["error"] is None
            value = row[image]
            assert value["error"] == rec["error"] and value["logs"] == rec["metadata"]["logs"]
            vault_key, user_key = str(VAULT_KEY), str(USERQUOTE_KEY)
            sent = amount_at(rec["before"][vault_key]["data_hex"], 64) - \
                amount_at(rec["after"][vault_key]["data_hex"], 64)
            received = amount_at(rec["after"][user_key]["data_hex"], 64) - \
                amount_at(rec["before"][user_key]["data_hex"], 64)
            fee = sent - received
            expect_fee = min((sent * case["expected_bps"] + 9999) // 10000, 2**64 - 1)
            assert fee == expect_fee, (case, image, sent, received, fee, expect_fee)
            assert rec["observed"] == {"quote_sent": sent, "quote_received": received,
                                       "fee": fee, "selected_bps": case["expected_bps"]}
            assert value["observed"] == rec["observed"]
            received_set.add(received)
            payer = str(tx.message.account_keys[0])
            assert rec["before"][payer]["lamports"] - rec["after"][payer]["lamports"] == \
                rec["payer_fee_lamports"] == 5000
        assert len(received_set) == 1, (case, "images must agree on the selected schedule")
    print("PASS: 8 cases, 24 signed receipts, "
          "epoch selection inclusive at newer.epoch, inverted pairs apply "
          "the future-dated older schedule, all images agree")


if __name__ == "__main__":
    main()
