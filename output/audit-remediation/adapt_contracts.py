from pathlib import Path

for name in ['tests/contract/mcp/test_mcp_tools.py','tests/e2e/test_chatbot_flow.py']:
    p=Path(name); s=p.read_text(encoding='utf-8')
    s=s.replace('PrometeusMCPServer(session_factory)', 'PrometeusMCPServer(session_factory, publisher=lambda *_: None)')
    s=s.replace('"course_name": "MBA em', '"idempotency_key": "test-mcp-create",\n                "course_name": "MBA em')
    s=s.replace('== "2024-11-05"','== "2025-11-25"')
    p.write_text(s,encoding='utf-8')
for name in ['tests/operational/test_kill_switch.py','tests/operational/test_shadow_mode.py']:
    p=Path(name); s=p.read_text(encoding='utf-8')
    s=s.replace('from prometeus.entrypoints.rest.app import app','from prometeus.domain.configuration import AppSettings\nfrom prometeus.entrypoints.rest.app import app')
    s=s.replace('instance = MockSettings.return_value', 'instance = AppSettings()\n        MockSettings.return_value = instance')
    s=s.replace('db_session=shadow_session,\n        shadow_mode=True,','db_session=shadow_session,\n        secret="isolated-test-secret",\n        shadow_mode=True,')
    p.write_text(s,encoding='utf-8')
p=Path('tests/operational/test_operational_failures.py');s=p.read_text(encoding='utf-8');s=s.replace('WebhookDispatcher(', 'WebhookDispatcher(secret="isolated-test-secret", ');p.write_text(s,encoding='utf-8')
p=Path('tests/unit/domain/test_tenant_ecosystem_config.py');s=p.read_text(encoding='utf-8');s=s.replace('session = AsyncMock()', 'session = AsyncMock()\n    session.begin_nested = MagicMock()\n    session.add = MagicMock()');p.write_text(s,encoding='utf-8')
