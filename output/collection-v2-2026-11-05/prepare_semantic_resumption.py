from pathlib import Path
import shutil

p = Path(__file__).parent
shutil.copyfile(p/'canary2-progress.json', p/'semantic-blocked-progress.json')
s = (p/'resume_after_server_overload.py').read_text(encoding='utf-8')
s = s.replace('AnalysisStepModel.step_number == 9', 'AnalysisStepModel.step_number == 13')
s = s.replace("assert step and step.status == 'FAILED' and 'server_is_overloaded' in step.error_message", "assert step and step.status == 'FAILED' and any(i.get('code') == 'semantic_unavailable' for i in step.output_summary.get('verification',{}).get('issues',[]))")
s = s.replace('server-overload-', 'semantic-recovery-')
s = s.replace('Retomada operacional após sobrecarga transitória do fornecedor; chamada real LLM confirmada antes da retomada.', 'Retomada operacional após falha do verificador semântico; julgamento isolado real confirmado, falso positivo do denominador corrigido e regressões aprovadas.')
s = s.replace('collection-v2-overload-resumption.json', 'collection-v2-semantic-resumption.json')
(p/'resume_after_semantic_failure.py').write_text(s, encoding='utf-8')
print('Blocked diagnostic preserved; guarded resumption script prepared.')
