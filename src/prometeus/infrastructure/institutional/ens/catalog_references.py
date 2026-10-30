"""Referências acadêmicas oficiais conferidas em 28/10/2026.

Somente os campos enumerados são observados. Não há histórico comercial público
nessas referências, nem atribuição de autenticidade às grades simuladas da fixture.
"""

from typing import Any

EXTENSIONS_SOURCE = "https://acontece.ens.edu.br/primeiro-semestre-com-ampla-oferta-de-extensoes/"

OFFICIAL_ACADEMIC_REFERENCES: dict[str, dict[str, Any]] = {
    "ENS-MBA-SEG-01": {
        "name": "MBA Gestão Avançada de Seguros",
        "category": "MBA",
        "source_url": "https://acontece.ens.edu.br/mba-gestao-avancada-de-seguros-abre-inscricoes-para-nova-turma/",
        "synthetic_modules": [
            "Estratégia e gestão de seguros",
            "Gestão de resseguros e riscos",
            "Liderança e finanças de seguradoras",
            "Operações, sinistros e subscrição",
        ],
    },
    "ENS-MBA-RISC-06": {
        "name": "MBA Finanças e Seguros",
        "category": "MBA",
        "source_url": "https://prdapi.ens.edu.br/media/course/visual-content/Programa_MBA_Financas_e_Segurosv4.2novo_1.pdf",
        "synthetic_modules": [
            "Finanças e seguros",
            "Gestão de riscos corporativos",
            "Estratégia e investimentos",
            "Atuária e governança",
        ],
    },
    "ENS-MBA-FIN-09": {
        "name": "MBA Gestão Jurídica em Contratos de Seguro e Inovação",
        "category": "MBA",
        "source_url": "https://acontece.ens.edu.br/category/carreiras-em-foco/mba-e-pos-graduacao/",
        "synthetic_modules": [
            "Contratos de seguro",
            "Resseguros e responsabilidades",
            "Inovação e proteção de dados",
            "Gestão de riscos jurídicos",
        ],
    },
    "ENS-POS-COMP-12": {
        "name": "Pós-Graduação em Gestão Estratégica de Seguros",
        "category": "Pós-Graduação",
        "source_url": "https://acontece.ens.edu.br/pos-graduacao-capacita-para-gestao-estrategica-em-seguros/",
        "synthetic_modules": [
            "Gestão de seguros e resseguros",
            "Planejamento estratégico",
            "Gestão de pessoas e marketing",
            "Riscos e governança",
        ],
    },
    "ENS-EXT-SIN-03": {
        "name": "Regulação de Sinistros por Ramos de Seguros",
        "category": "Extensão",
        "source_url": "https://ens.edu.br/pos/regulacao-de-sinistros-por-ramos-de-seguros",
        "synthetic_modules": [
            "Regulação de sinistros",
            "Contratos e coberturas",
            "Liquidação por ramo",
            "Tecnologia e análise de casos",
        ],
    },
    "ENS-EXT-RES-14": {
        "name": "Gestão de Resseguro",
        "category": "Extensão",
        "source_url": "https://ens.edu.br/pos/gestao-de-resseguro",
        "synthetic_modules": [
            "Fundamentos de resseguros",
            "Contratos e negociação",
            "Gestão de riscos cedidos",
            "Sinistros e prestação de contas",
        ],
    },
    "ENS-EXT-FRA-18": {
        "name": "Seguros de Responsabilidade Civil e Linhas Financeiras",
        "category": "Extensão",
        "source_url": EXTENSIONS_SOURCE,
        "synthetic_modules": [
            "Responsabilidade civil",
            "Coberturas e exclusões",
            "Seguros de administradores",
            "Riscos profissionais e sinistros",
        ],
    },
    "ENS-EXT-RUR-20": {
        "name": "Logística, Riscos e Seguros",
        "category": "Extensão",
        "source_url": EXTENSIONS_SOURCE,
        "synthetic_modules": [
            "Gestão logística",
            "Riscos da cadeia de suprimentos",
            "Seguros de transporte",
            "Prevenção de perdas",
        ],
    },
    "ENS-EXT-MAR-21": {
        "name": "Contrato de Resseguro: Cláusulas e Estruturas",
        "category": "Extensão",
        "source_url": EXTENSIONS_SOURCE,
        "synthetic_modules": [
            "Estrutura dos contratos de resseguro",
            "Cláusulas e coberturas",
            "Gestão de riscos contratuais",
            "Sinistros e arbitragem",
        ],
    },
    "ENS-TEST-GRAD-31": {
        "name": "Graduação em Gestão de Seguros",
        "category": "Graduação Tecnológica",
        "source_url": "https://prdapi.ens.edu.br/media/course/visual-content/Programa_CST_Gestao_de_Seguros_2025.pdf",
        "synthetic_modules": [
            "Fundamentos de seguros",
            "Administração e gestão",
            "Operações e comercialização",
            "Análise de riscos",
        ],
    },
    "ENS-TEST-IMERSAO-32": {
        "name": "Risk Management and Innovation – Connecticut / New York",
        "category": "Imersão Internacional",
        "source_url": "https://acontece.ens.edu.br/ens-anuncia-treinamento-inedito-em-connecticut-nova-iorque/",
        "synthetic_modules": [
            "Gerenciamento de riscos",
            "Inovação em seguros",
            "Ecossistemas internacionais",
            "Visitas técnicas simuladas",
        ],
    },
    "ENS-TEST-CERT-33": {
        "name": "Seguro de RC Produtos e Operações Completadas",
        "category": "Certificação Avançada",
        "source_url": "https://acontece.ens.edu.br/curso-inedito-capacitara-profissionais-em-rc-produtos-e-operacoes-completadas/",
        "synthetic_modules": [
            "Responsabilidade civil de produtos",
            "Contratos e subscrição",
            "Gestão de sinistros",
            "Riscos complexos",
        ],
    },
}
