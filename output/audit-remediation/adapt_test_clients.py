from pathlib import Path
import re

for path in Path('tests').rglob('test_*.py'):
    if path.name == 'test_access_control.py':
        continue
    source = path.read_text(encoding='utf-8')
    pattern = r'base_url=("http://(?:test|testserver)")'
    updated = re.sub(pattern, 'headers={"Authorization": "Bearer test-admin-key-12345678901234567890"}, ' + r'\g<0>', source)
    if source != updated:
        path.write_text(updated, encoding='utf-8')
        print(path)
