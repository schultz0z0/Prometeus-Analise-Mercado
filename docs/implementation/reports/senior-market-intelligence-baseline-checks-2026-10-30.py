"""Verifica contagens da auditoria sem rede, inferência ou escrita em dados.

Executar da raiz: rtk proxy .venv/Scripts/python.exe
docs/implementation/reports/senior-market-intelligence-baseline-checks-2026-10-30.py
"""

import collections
import hashlib
import json
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
REPORTS = ROOT / "docs/implementation/reports"
STUDY = ROOT / "docs/Estudo_Prometeus_144_registros_73501c53_2026-10-29"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


baseline = read(REPORTS / "senior-market-intelligence-baseline-2026-10-29.json")
for name, expected in baseline["input_file_sha256"].items():
    assert hashlib.sha256((STUDY / name).read_bytes()).hexdigest() == expected, name
records = read(STUDY / "registros_para_estudo.json")
analysis = read(STUDY / "consultas_e_checkpoints.json")
originals = read(STUDY / "retornos_originais_e_higienizados.json")
assert len(records) == len(originals) == len({r["id"] for r in records}) == 144
assert collections.Counter(r["classification"] for r in records) == {
    "Indicador": 17, "Contexto": 73, "Excluído": 54
}
over_budget = 0
trends = []
missing_job_descriptions = []
for r in records:
    data = {k: v for k, v in r["sanitized_data"].items() if k != "_qualification"}
    projected = json.dumps({"title": r["title"], "url": r["source_url"], "data": data},
                           ensure_ascii=False)
    over_budget += len(projected) > 14000
    if r["source_name"] == "apify_google_trends":
        series = data["interestOverTime_timelineData"]
        assert len(series) == 262
        assert projected.find("interestOverTime_timelineData") > 14000
        assert all("REDACTED" in str(p.get("time")) for p in series)
        trends.append(sum(any(isinstance(v, (int, float)) and v > 0
                              for v in p.get("value", [])) for p in series))
    if r["source_name"] == "apify_linkedin_jobs" and data.get("descriptionText"):
        fact = r["fact_given_to_writer"]
        if fact and data["descriptionText"][:120] not in fact.get("summary", ""):
            missing_job_descriptions.append(r)
assert over_budget == 20
assert sorted(trends) == [2, 30, 30]
assert len(missing_job_descriptions) == 28
assert sum(r["classification"] == "Indicador" for r in missing_job_descriptions) == 16
assert sum(r["quality_score"] == 1 for r in records) == 144
assert collections.Counter(r["status"] for r in analysis["tool_runs"]) == {
    "SUCCEEDED": 15, "EMPTY": 3, "PARTIAL": 1
}
reported_cost = sum(Decimal(str(r["cost_usd"])) for r in analysis["tool_runs"])
assert reported_cost == Decimal("0.311142")

# Independent arithmetic over declared scenario premises, not a score recalculation.
weights = list(map(Decimal, [".20", ".20", ".20", ".15", ".15", ".10"]))
components = list(map(Decimal, [".9", ".44", ".506", ".51", ".675", ".5"]))
scenario = sum(w * c for w, c in zip(weights, components, strict=True))
assert scenario.quantize(Decimal(".0001"), rounding=ROUND_HALF_UP) == Decimal(".5970")
assert (scenario + Decimal(".1") * Decimal(".3")).quantize(
    Decimal(".0001"), rounding=ROUND_HALF_UP) == Decimal(".6270")
print("PASS: 10 file hashes, 144 records, classes, retention losses, tool counts/cost and scenario arithmetic.")
print("No model/Actor calls, source writes or published score changes.")
