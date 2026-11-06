import json
from pathlib import Path

import httpx

ART=Path(__file__).resolve().parent
ROOT=ART.parents[1]
key=(ROOT/'var/auth/admin.key').read_text(encoding='utf-8').strip()
proposal={
    'course_name':'Governança de Inteligência Artificial e Proteção de Dados no Mercado Segurador',
    'tenant_id':'ens',
    'proposal_data':{
        'validation_run':'homologacao-real-2026-11-04',
        'course_type':'Extensão',
        'level':'Extensão',
        'modality':'Online ao vivo',
        'workload_hours':24,
        'duration_months':2,
        'geography':'Brasil',
        'language':'pt-BR',
        'target_audience':'Profissionais de seguradoras, corretoras e insurtechs nas áreas de riscos, compliance, proteção de dados e inovação que avaliam o uso de IA generativa.',
        'learning_outcomes':[
            'Mapear riscos do uso de IA generativa em processos do setor de seguros.',
            'Elaborar critérios de governança, proteção de dados e supervisão humana.',
            'Construir um plano de avaliação e monitoramento de um caso de uso de IA.',
        ],
        'modules':[
            {'name':'IA generativa e aplicações no mercado segurador','workload_hours':4},
            {'name':'Riscos, vieses, limitações e avaliação de sistemas de IA','workload_hours':4},
            {'name':'Proteção de dados pessoais e segurança da informação','workload_hours':4},
            {'name':'Governança, compliance e supervisão humana','workload_hours':4},
            {'name':'Desenho e validação de casos de uso em seguros','workload_hours':4},
            {'name':'Oficina de plano de governança e monitoramento','workload_hours':4},
        ],
        'economics':{
            'total_price_brl':1800,
            'installments':3,
            'discount_rate_pct':10,
            'default_and_refund_rate_pct':3,
            'tax_rate_pct':10,
            'instruction_and_coordination_cost_brl':10000,
            'variable_cost_per_student_brl':100,
            'marketing_campaign_cost_brl':3000,
            'cac_per_enrolled_brl':0,
            'min_capacity':15,
            'max_capacity':30,
            'academic_duration_months':2,
            'financial_duration_months':3,
        },
        'proposed_price_brl':1800,
        'proposed_price_period':'total',
        'notes':'Caso controlado de homologação técnica. Premissas financeiras fornecidas exclusivamente para testar simulação; não constituem orçamento ENS aprovado. Histórico institucional permanece sintético. Não registrar aprovação humana nem lançamento comercial.',
    },
}
(ART/'canary-proposal.json').write_text(json.dumps(proposal,ensure_ascii=False,indent=2),encoding='utf-8')
headers={'Authorization':f'Bearer {key}','Idempotency-Key':'homologacao-20261104-real-01'}
with httpx.Client(base_url='http://127.0.0.1:8000',timeout=45,headers=headers) as client:
    first=client.post('/v1/analyses',json=proposal)
    first.raise_for_status()
    second=client.post('/v1/analyses',json=proposal)
    second.raise_for_status()
    assert first.json()['analysis_id']==second.json()['analysis_id']
    report={'analysis_id':first.json()['analysis_id'],'status':first.json()['status'],'idempotency_verified':True,'apify_budget_limit_usd':5.0}
    (ART/'canary.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))
