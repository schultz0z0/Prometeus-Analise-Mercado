import json
import subprocess
from pathlib import Path


def test_portfolio_escapes_all_controlled_metadata():
    payload = '<img src=x onerror="window.__audit_xss=1">'
    source = Path("web/js/views/portfolio-view.js").resolve().as_uri()
    script = f"""import {{renderPortfolioView}} from {json.dumps(source)};
const p={json.dumps(payload)};
const course={{id:p,name:p,area:p,level:p,modality:p,ticket:100,price_period:'total',recommendation:p,viability_score:20,coverage_index:.5}};
console.log(renderPortfolioView({{getState:()=>({{portfolioTab:'diagnostics',courses:[course],historicalCourses:[]}})}}));"""
    result = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        capture_output=True,
        encoding="utf-8",
        check=True,
    )
    assert payload not in result.stdout
    assert "&lt;img" in result.stdout
    assert "/mês" not in result.stdout
