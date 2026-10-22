# Exemplos de contratos

Os exemplos são conceituais; o OpenAPI definitivo será gerado na Fase 07.

## Criar análise

```json
{
  "institution_id": "ens",
  "proposal": {
    "title": "Inteligência Artificial Aplicada a Seguros",
    "modality": "postgraduate",
    "audience": ["gestores de seguradoras", "corretores"],
    "objectives": ["aplicar IA a processos e produtos de seguros"],
    "syllabus": [
      {"title": "Fundamentos", "workload_hours": 20}
    ],
    "delivery_format": "online",
    "target_regions": ["BR"]
  },
  "callback_url": "https://chatbot.example.com/hooks/course-analysis",
  "previous_analysis_id": null
}
```

`previous_analysis_id` é opcional e cria uma reanálise vinculada (RF-010) sem alterar a análise anterior.

Resposta:

```json
{
  "analysis_id": "anl_01J...",
  "status": "QUEUED",
  "created_at": "2026-10-09T18:00:00Z"
}
```

## Resultado resumido

```json
{
  "analysis_id": "anl_01J...",
  "status": "COMPLETED",
  "recommendation": "APPROVED_WITH_ADJUSTMENTS",
  "scoring_profile_id": "default-v1",
  "score": {
    "viability": 72.4,
    "confidence": 0.81,
    "coverage": 0.90,
    "experimental": true
  },
  "pillars": [],
  "claims": [
    {
      "claim_id": "clm_01J...",
      "text": "O interesse de busca cresceu no período analisado.",
      "evidence_ids": ["evd_01J..."],
      "support": "suggestive"
    }
  ],
  "limitations": [],
  "recommendations": [],
  "versions": {
    "workflow": "1.0.0",
    "jev_model": "pinned-at-release",
    "dossier_prompt": "dossier-v1"
  }
}
```

## Erro

```json
{
  "type": "https://docs.example.com/problems/insufficient-evidence",
  "title": "Evidências insuficientes",
  "status": 409,
  "detail": "Uma fonte obrigatória não produziu dados válidos.",
  "correlation_id": "cor_01J...",
  "analysis_id": "anl_01J..."
}
```
