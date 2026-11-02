#!/usr/bin/env python3
"""Offline, fail-closed classifier. Standard library only; no Windows dependency.

This is an evidence consistency checker, not tamper-proof attestation. A CSV alone
never establishes completeness: target presents are reconciled with frames.csv.
"""
from __future__ import annotations
import argparse
import bisect
import csv
import hashlib
import json
import re
import sys
from collections import Counter
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any

PM_SHA256 = "b2a706bc6ad475749e3b7e3409263aa1e6906d45bdcf993f6dbc0f660188f1af"
PM_VERSION = "2.6.0"
LEGACY = {"Hardware: Legacy Flip", "Hardware: Legacy Copy to front buffer"}
NONLEGACY = {"Hardware: Independent Flip", "Hardware Composed: Independent Flip",
             "Composed: Flip", "Composed: Copy with GPU GDI", "Composed: Copy with CPU GDI",
             "Composed: Composition Atlas"}
REQUIRED_PM = {"Application", "ProcessID", "SwapChainAddress", "PresentRuntime", "PresentMode",
               "CPUStartQPC", "DisplayedTime"}
# PresentMon 2.6.0 --v2_metrics writes CPUBusy; older/reference exports use MsCPUBusy.
PM_BUSY_COLUMNS = ("MsCPUBusy", "CPUBusy")
REQUIRED_FRAMES = {"FrameIndex", "BeforeQPC", "AfterQPC", "HResult", "Fullscreen", "Focus"}
EVIDENCE_FILES = ("app.jsonl", "frames.csv", "presentmon.csv", "presentmon.stdout.txt", "presentmon.stderr.txt")
KNOWN_EVENTS = {"START", "DISPLAY_SELECTED", "MODE_READY", "REQUEST_FULLSCREEN", "SET_FULLSCREEN_RESULT",
                "STATE", "CAPTURE_MARK_START", "CAPTURE_MARK_END", "MARK_REJECTED", "LOST_FOCUS", "DISPLAY_CHANGED",
                "RESIZED", "CAPTURE_INVALIDATED", "DXGI_LOST", "PRESENT_ERROR", "CAPTURE_INCOMPLETE", "NO_CAPTURE_MARKS",
                "LEAVE_FULLSCREEN_RESULT", "APP_ERROR", "ENVIRONMENT_REFUSED", "START_REFUSED", "END"}

class EvidenceError(Exception):
    def __init__(self, reason: str, detail: str = "", verdict: str = "UNVERIFIED") -> None:
        super().__init__(detail or reason)
        self.reason, self.detail, self.verdict = reason, detail or reason, verdict

def require(condition: bool, reason: str, detail: str = "", verdict: str = "UNVERIFIED") -> None:
    if not condition:
        raise EvidenceError(reason, detail, verdict)

def unique_json(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    obj: dict[str, Any] = {}
    for key, value in pairs:
        if key in obj:
            raise EvidenceError("UNVERIFIED_DUPLICATE_JSON_KEY", key)
        obj[key] = value
    return obj

def read_json(path: Path) -> dict[str, Any]:
    require(path.stat().st_size <= 2_000_000, "UNVERIFIED_OVERSIZE_JSON")
    value = json.loads(path.read_text(encoding="utf-8-sig"), object_pairs_hook=unique_json)
    require(isinstance(value, dict), "UNVERIFIED_JSON_OBJECT_REQUIRED")
    return value

def integer(value: Any, name: str, low: int = 0, high: int = (1 << 63)-1) -> int:
    require(type(value) is int or (isinstance(value, str) and re.fullmatch(r"[0-9]+", value) is not None),
            "UNVERIFIED_INTEGER", name)
    n = int(value)
    require(low <= n <= high, "UNVERIFIED_INTEGER_RANGE", name)
    return n

def decimal(value: str, name: str, maximum: Decimal = Decimal("60000")) -> Decimal:
    try:
        n = Decimal(value)
    except InvalidOperation as exc:
        raise EvidenceError("UNVERIFIED_NUMBER", name) from exc
    require(n.is_finite() and 0 <= n <= maximum, "UNVERIFIED_NUMBER", name)
    return n

def rows(path: Path, required: set[str]) -> list[dict[str, str]]:
    require(0 < path.stat().st_size < 128_000_000, "UNVERIFIED_CSV_SIZE", path.name)
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, strict=True)
        fields = reader.fieldnames or []
        require(len(fields) == len(set(fields)), "UNVERIFIED_DUPLICATE_HEADER", path.name)
        missing = required - set(fields)
        reason = "UNVERIFIED_TIME_AXIS" if "CPUStartQPC" in missing else "UNVERIFIED_SCHEMA"
        require(not missing, reason, f"{path.name}: missing {sorted(missing)}")
        out = []
        for i, row in enumerate(reader, 2):
            require(None not in row and all(v is not None for v in row.values()), "UNVERIFIED_CSV_ROW", f"{path.name}:{i}")
            require(i < 200_000, "UNVERIFIED_TOO_MANY_ROWS")
            out.append(row)
        require(bool(out), "UNVERIFIED_EMPTY_CSV", path.name)
        return out

def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024*1024), b""):
            h.update(block)
    return h.hexdigest()

def events(path: Path) -> list[dict[str, Any]]:
    require(path.stat().st_size < 16_000_000, "UNVERIFIED_LOG_SIZE")
    result = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        require(bool(line.strip()), "UNVERIFIED_BLANK_LOG_LINE")
        event = json.loads(line, object_pairs_hook=unique_json)
        require(isinstance(event, dict) and type(event.get("schema")) is int and event.get("schema") == 1, "UNVERIFIED_EVENT_SCHEMA")
        require(event.get("event") in KNOWN_EVENTS, "UNVERIFIED_UNKNOWN_EVENT")
        require(integer(event.get("seq"), "seq") == len(result), "UNVERIFIED_EVENT_SEQUENCE")
        q = integer(event.get("qpc"), "qpc", 1)
        require(not result or q >= result[-1]["qpc"], "UNVERIFIED_EVENT_ORDER")
        require(isinstance(event.get("utc"), str) and event["utc"].endswith("Z"), "UNVERIFIED_UTC")
        event["qpc"] = q
        result.append(event)
    require(bool(result), "UNVERIFIED_EMPTY_LOG")
    return result

def exactly_one(items: list[dict[str, Any]], name: str) -> dict[str, Any]:
    selected = [e for e in items if e["event"] == name]
    require(len(selected) == 1, "UNVERIFIED_EVENT_CARDINALITY", name)
    return selected[0]

def classify(run: Path) -> dict[str, Any]:
    report: dict[str, Any] = {
        "schema": 1, "verdict": "UNVERIFIED", "reason": "UNVERIFIED_NOT_EVALUATED", "detail": "",
        "dxgi_state": "NOT_EVALUATED", "presentation_proof": "UNVERIFIED",
        "recorder_result": "NOT_EVALUATED", "hardware_fse_validation": "NOT_EXECUTED",
        "live_verification": "NOT_LIVE_VERIFIED", "evidence_kind": "UNKNOWN",
        "scope": "Only the marked interval and its guard bands; no recorder API integration",
        "ci_build_status": "NOT_REPORTED", "warnings": [], "evidence_sha256": {}
    }
    try:
        session = read_json(run / "session.json")
        report["run_id"] = session.get("run_id")
        report["evidence_kind"] = session.get("evidence_kind", "UNKNOWN")
        require(type(session.get("schema")) is int and session.get("schema") == 1, "UNVERIFIED_SESSION_SCHEMA")
        if session.get("application_launch") == "BLOCKED_BY_APP_CONTROL":
            raise EvidenceError("BLOCKED_BY_APP_CONTROL", "No FSE result; application control prevented execution", "BLOCKED")
        require(session.get("application_launch") == "STARTED", "UNVERIFIED_LAUNCH")
        require(session.get("runner_error") is None, "UNVERIFIED_RUNNER_ERROR")
        require(session.get("evidence_kind") in {"REAL_WINDOWS_RUN", "SYNTHETIC_FIXTURE"}, "UNVERIFIED_EVIDENCE_KIND")
        require(session.get("physical_desktop_attested") is True, "UNVERIFIED_ENVIRONMENT",
                "Operator must attest a local physical display; automatic VM detection is insufficient")
        report["hardware_fse_validation"] = "NOT_VERIFIED" if session["evidence_kind"] == "REAL_WINDOWS_RUN" else "SYNTHETIC_NOT_HARDWARE"
        require(session.get("observer_sha256", "").lower() == PM_SHA256, "UNVERIFIED_OBSERVER_HASH")
        require(session.get("observer_version") == PM_VERSION, "UNVERIFIED_OBSERVER_VERSION")
        require(session.get("time_axis") == "qpc_ticks_v2", "UNVERIFIED_TIME_AXIS")
        require(type(session.get("observer_exit_code")) is int and session.get("observer_exit_code") == 0 and session.get("observer_timeout") is False,
                "UNVERIFIED_OBSERVER_EXIT")
        require(session.get("app_timeout") is False, "UNVERIFIED_APP_TIMEOUT")
        hashes = session.get("evidence_sha256", {})
        require(isinstance(hashes, dict), "UNVERIFIED_HASH_SCHEMA")
        for name in EVIDENCE_FILES:
            digest = sha(run / name)
            report["evidence_sha256"][name] = digest
            require(hashes.get(name) == digest, "UNVERIFIED_EVIDENCE_HASH", name)
        stderr = (run / "presentmon.stderr.txt").read_text(encoding="utf-8-sig")
        stdout = (run / "presentmon.stdout.txt").read_text(encoding="utf-8-sig")
        require(not stderr.strip(), "UNVERIFIED_OBSERVER_DIAGNOSTICS", "Inspect saved PresentMon stderr; no warnings ignored")
        require(not re.search(r"\b(error|warning)\b|\b[1-9][0-9]*\s+(?:events?|buffers?)\s+(?:were\s+)?lost\b", stdout, re.I),
                "UNVERIFIED_OBSERVER_DIAGNOSTICS", "PresentMon warning/error/loss output")
        ev = events(run / "app.jsonl")
        start, end = exactly_one(ev, "START"), exactly_one(ev, "END")
        require(ev[0] is start and ev[-1] is end, "UNVERIFIED_LOG_BOUNDARIES")
        require(start.get("run_id") == session.get("run_id"), "UNVERIFIED_RUN_ID")
        pid = integer(start.get("pid"), "PID", 1, (1 << 32)-1)
        require(pid == integer(session.get("target_pid"), "session PID", 1), "UNVERIFIED_IDENTITY")
        require(start.get("process_creation_filetime") == session.get("process_creation_filetime"), "UNVERIFIED_PROCESS_CREATION")
        integer(start.get("process_creation_filetime"), "FILETIME", 1, (1 << 64)-1)
        freq = integer(start.get("qpc_frequency"), "QPC frequency", 1)
        require(freq == integer(session.get("qpc_frequency"), "session QPC frequency", 1), "UNVERIFIED_TIME_AXIS")
        require(start.get("remote_session") is False and integer(start.get("session_id"), "session", 1) > 0, "UNVERIFIED_ENVIRONMENT")
        mode = start.get("mode")
        require(mode in {"legacy-exclusive", "borderless-control"} and mode == session.get("mode"), "UNVERIFIED_MODE")
        require(integer(session.get("observer_started_qpc"), "observer start", 1) < start["qpc"], "UNVERIFIED_LATE_OBSERVER")
        report.update(pid=pid, process_creation_filetime=start["process_creation_filetime"], qpc_frequency=freq, mode=mode)
        require(type(session.get("app_exit_code")) is int and type(end.get("exit_code")) is int and session.get("app_exit_code") == end.get("exit_code"), "UNVERIFIED_EXIT_MISMATCH")
        require(end.get("exit_code") == 0, "FAIL_APP_EXECUTION", "Application did not finish cleanly", "FAIL")
        ready = exactly_one(ev, "MODE_READY")
        begin, finish = exactly_one(ev, "CAPTURE_MARK_START"), exactly_one(ev, "CAPTURE_MARK_END")
        guard = max(1, freq // 4)  # 250 ms each side; never silently relax it.
        require(ready["qpc"] < begin["qpc"] - guard < finish["qpc"] + guard < end["qpc"], "UNVERIFIED_INTERVAL_BOUNDS")
        require(begin.get("kind") in {"AUTOMATIC_DIAGNOSTIC", "OPERATOR_MARKED"} and begin.get("kind") == finish.get("kind"), "UNVERIFIED_MARKERS")
        report["interval_kind"] = begin["kind"]
        report["capture_start_qpc"], report["capture_end_qpc"] = begin["qpc"], finish["qpc"]
        report["guard_ticks"] = guard
        if begin["kind"] == "AUTOMATIC_DIAGNOSTIC":
            report["warnings"].append("Automatic diagnostic interval does not establish that a recorder was running.")
        else:
            report["warnings"].append("Operator marks do not measure the external recorder's exact start/stop times.")
        desired = mode == "legacy-exclusive"
        states = [ready] + [e for e in ev if e["event"] == "STATE"]
        require(all(e.get("fullscreen") is desired and e.get("focus") is True and e.get("correct_output") is True for e in states),
                "FAIL_DXGI_STATE", "DXGI/focus/output mismatch", "FAIL")
        forbidden = {"LOST_FOCUS", "DISPLAY_CHANGED", "CAPTURE_INVALIDATED", "DXGI_LOST", "PRESENT_ERROR", "CAPTURE_INCOMPLETE", "APP_ERROR", "ENVIRONMENT_REFUSED"}
        require(not any(e["event"] in forbidden for e in ev), "FAIL_APP_STATE_CHANGE", "Invalidating app event", "FAIL")
        if desired:
            request = exactly_one(ev, "SET_FULLSCREEN_RESULT")
            require(request.get("hresult") == "0x0", "FAIL_DXGI_REQUEST", verdict="FAIL")
        else:
            require(not any(e["event"] == "REQUEST_FULLSCREEN" for e in ev), "FAIL_CONTROL_REQUESTED_FSE", verdict="FAIL")
        leave = exactly_one(ev, "LEAVE_FULLSCREEN_RESULT")
        require(leave.get("hresult") == "0x0", "FAIL_CLEANUP", verdict="FAIL")
        report["dxgi_state"] = "FULLSCREEN_REPORTED" if desired else "WINDOWED_REPORTED"
        rawframes = rows(run / "frames.csv", REQUIRED_FRAMES)
        frames: list[dict[str, Any]] = []
        for i, row in enumerate(rawframes):
            require(integer(row["FrameIndex"], "FrameIndex") == i, "UNVERIFIED_FRAME_SEQUENCE")
            b, a = integer(row["BeforeQPC"], "BeforeQPC", 1), integer(row["AfterQPC"], "AfterQPC", 1)
            require(start["qpc"] <= b <= a <= end["qpc"] and (not frames or b >= frames[-1]["after"]), "UNVERIFIED_FRAME_ORDER")
            require(row["HResult"] == "0x0" and row["Focus"] == "1" and row["Fullscreen"] == ("1" if desired else "0"), "FAIL_PRESENT_LEDGER", verdict="FAIL")
            frames.append({"before": b, "after": a, "index": i})
        left, right = begin["qpc"] - guard, finish["qpc"] + guard
        core_left, core_right = begin["qpc"] + guard, finish["qpc"] - guard
        expected = {f["index"] for f in frames if left <= f["before"] <= right}
        require(len(expected) >= 30, "UNVERIFIED_INSUFFICIENT_FRAMES")
        before_values = [f["before"] for f in frames]
        tolerance = max(1, freq // 4000)  # 0.25 ms rounding/mapping tolerance, not a scanout estimate.
        require(before_values[0] < left and before_values[-1] > right, "UNVERIFIED_GUARD_COVERAGE")
        csvrows = rows(run / "presentmon.csv", REQUIRED_PM)
        busy_column = next((name for name in PM_BUSY_COLUMNS if name in csvrows[0]), None)
        require(busy_column is not None, "UNVERIFIED_SCHEMA", "presentmon.csv: missing MsCPUBusy/CPUBusy")
        target = []
        for row in csvrows:
            rowpid = integer(row["ProcessID"], "ProcessID", 1, (1 << 32)-1)
            if rowpid != pid:
                continue
            require(row["Application"].lower().replace("\\", "/").split("/")[-1] == "fseprobe.exe", "UNVERIFIED_APPLICATION_NAME")
            q = integer(row["CPUStartQPC"], "CPUStartQPC", 1)
            busy = decimal(row[busy_column], busy_column)
            present_qpc = q + int((busy * freq / 1000).to_integral_value(rounding=ROUND_HALF_UP))
            require(re.fullmatch(r"(?:0x)?[0-9a-fA-F]+", row["SwapChainAddress"]) is not None, "UNVERIFIED_SWAPCHAIN")
            address = int(row["SwapChainAddress"], 16)
            require(0 < address < (1 << 64), "UNVERIFIED_SWAPCHAIN")
            # Rows before mode-ready or after END cannot be evidence for this app segment.
            if ready["qpc"] <= present_qpc <= end["qpc"]:
                target.append(dict(row, cpu_qpc=q, present_qpc=present_qpc, busy=busy, address=address))
        require(bool(target), "UNVERIFIED_NO_TARGET_FRAMES")
        addresses = {r["address"] for r in target}
        require(len(addresses) == 1, "UNVERIFIED_AMBIGUOUS_SWAPCHAIN")
        report["swapchain_address"] = hex(next(iter(addresses)))
        selected = [r for r in target if left-tolerance <= r["present_qpc"] <= right+tolerance]
        require(bool(selected), "UNVERIFIED_NO_INTERVAL_FRAMES")
        require(all(r["PresentRuntime"] == "DXGI" for r in selected), "UNVERIFIED_RUNTIME")
        require(all(r["busy"] <= 250 for r in selected), "UNVERIFIED_LONG_CPU_FRAME", "CPUStartQPC guard too small for observed CPU duration")
        modes = Counter(r["PresentMode"] for r in selected)
        report["observed_modes"] = dict(modes)
        require(all(m in LEGACY | NONLEGACY for m in modes), "UNVERIFIED_UNKNOWN_PRESENT_MODE")
        # Evaluate observed contradictions before attempting to prove coverage.
        if desired and any(m in NONLEGACY for m in modes):
            reason = "FAIL_PRESENT_MODE_CHANGED" if any(m in LEGACY for m in modes) else "FAIL_NOT_CLASSIC_EXCLUSIVE"
            raise EvidenceError(reason, "At least one observed non-legacy frame in the guarded capture interval", "FAIL")
        if not desired and any(m in LEGACY for m in modes):
            raise EvidenceError("FAIL_CONTROL_LEGACY_OBSERVED", "Windowed control unexpectedly used a legacy-ownership path", "FAIL")
        seen: set[int] = set()
        matched = []
        for row in selected:
            p = row["present_qpc"]
            pos = bisect.bisect_right(before_values, p)
            candidates = [j for j in range(max(0, pos-2), min(len(frames), pos+2))
                          if frames[j]["before"] - tolerance <= p <= frames[j]["after"] + tolerance]
            require(bool(candidates), "UNVERIFIED_TIME_RECONCILIATION", "CPUStartQPC + "+busy_column+" does not match any Present call")
            j = min(candidates, key=lambda v: abs(frames[v]["before"]-p))
            require(j not in seen, "UNVERIFIED_DUPLICATE_PRESENT", "Two CSV rows map to one app Present")
            seen.add(j)
            displayed = row["DisplayedTime"]
            require(displayed == "NA" or decimal(displayed, "DisplayedTime") >= 0, "UNVERIFIED_DISPLAY_METRIC")
            matched.append((j, row))
        require(expected <= seen, "UNVERIFIED_FRAME_GAP", f"{len(expected-seen)} guarded Present calls missing from CSV")
        # Extremely long stalls are not a sufficiently continuous presentation test.
        segment = sorted(frames[i]["before"] for i in expected)
        require(all(b-a <= freq//2 for a, b in zip(segment, segment[1:])), "UNVERIFIED_SPARSE_TIMELINE")
        core = [row for i, row in matched if core_left <= frames[i]["before"] <= core_right and row["DisplayedTime"] != "NA" and decimal(row["DisplayedTime"], "DisplayedTime") > 0]
        require(len(core) >= 30, "UNVERIFIED_INSUFFICIENT_DISPLAYED_FRAMES")
        require(max(r["present_qpc"] for r in core)-min(r["present_qpc"] for r in core) >= 2*freq, "UNVERIFIED_SHORT_INTERVAL")
        preflight = [r for r in target if ready["qpc"]+guard <= r["present_qpc"] < left]
        report["preflight"] = {"frames": len(preflight), "observed_modes": dict(Counter(r["PresentMode"] for r in preflight)),
                               "note": "Descriptive only; never substitutes for capture evidence"}
        report.update(guarded_presents=len(expected), matched_presents=len(seen), displayed_core_frames=len(core),
                      coverage="ONE_TO_ONE_PRESENT_LEDGER_RECONCILED")
        synthetic = session["evidence_kind"] == "SYNTHETIC_FIXTURE"
        report["verdict"] = "SYNTHETIC_PASS" if synthetic else "PASS"
        report["reason"] = "CLASSIC_EXCLUSIVE_OBSERVED" if desired else "NONEXCLUSIVE_CONTROL_OBSERVED"
        report["presentation_proof"] = ("SYNTHETIC_LEGACY_MATCH" if desired else "SYNTHETIC_CONTROL_MATCH") if synthetic else ("FSE_VERIFIED" if desired else "CONTROL_VERIFIED_NOT_FSE")
        if not synthetic:
            report["hardware_fse_validation"] = "VERIFIED_MARKED_INTERVAL" if desired else "CONTROL_ONLY"
        report["detail"] = "All observed guarded frames meet the selected mode contract and reconcile to application Presents."
        report["warnings"].append("This is not a security attestation; trust depends on accurate app/ETW data and the recorded environment.")
    except EvidenceError as exc:
        report.update(verdict=exc.verdict, reason=exc.reason, detail=exc.detail)
        if exc.verdict == "FAIL":
            report["presentation_proof"] = "NOT_VERIFIED"
    except (OSError, ValueError, TypeError, KeyError, AttributeError, OverflowError, RecursionError, csv.Error, InvalidOperation) as exc:
        report.update(verdict="UNVERIFIED", reason="UNVERIFIED_INPUT", detail=f"{type(exc).__name__}: {exc}")
    return report

def exit_code(report: dict[str, Any]) -> int:
    return {"PASS": 0, "SYNTHETIC_PASS": 0, "FAIL": 10, "UNVERIFIED": 11, "BLOCKED": 42}.get(report["verdict"], 11)

def write_report(report: dict[str, Any], directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "summary.json").write_text(json.dumps(report, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
    text = "\n".join(f"{k}: {report[k]}" for k in (
        "verdict", "reason", "detail", "dxgi_state", "presentation_proof", "recorder_result", "hardware_fse_validation", "evidence_kind", "scope"))
    text += "\n\nWarnings:\n" + "\n".join("- " + w for w in report["warnings"]) + "\n"
    (directory / "summary.txt").write_text(text, encoding="utf-8")

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True, type=Path)
    args = parser.parse_args()
    report = classify(args.run_dir)
    try:
        write_report(report, args.run_dir)
    except OSError as exc:
        print(f"Cannot write reports: {exc}", file=sys.stderr)
        return 11
    print(json.dumps(report, indent=2))
    return exit_code(report)

if __name__ == "__main__":
    raise SystemExit(main())
