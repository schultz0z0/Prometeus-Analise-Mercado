from prometeus.application.pricing_reference import build_price_reference, extract_price_conditions


def offer(url, text, **extra):
    return {
        "id": url,
        "source_url": url,
        "title": "MBA em Gestão de Seguros",
        "sanitized_data": {"markdown": text, "_qualification": {"accepted": True}, **extra},
    }


def test_conditions_separate_installments_totals_and_registration_fee():
    conditions = extract_price_conditions(
        "Taxa de matrícula R$ 100,00. Curso em 20x de R$ 976,00. Valor à vista R$ 18.000,00."
    )
    assert any(c["total_brl"] == 19520 and c["installments"] == 20 for c in conditions)
    assert any(c["total_brl"] == 18000 for c in conditions)
    assert not any(c["total_brl"] == 100 for c in conditions)


def test_combines_one_price_per_course_with_internal_and_external_origin():
    audit = build_price_reference(
        course_title="MBA Gestão de Seguros",
        level="MBA Executivo",
        institution_name="ENS",
        internal_prices=[
            {
                "course_id": "h1",
                "name": "MBA Gestão de Seguros",
                "category": "MBA Executivo",
                "total_brl": 20000,
            }
        ],
        offers=[
            offer("https://college.example/mba", "Investimento total R$ 10.000,00"),
            offer(
                "https://college.example/mba?utm_source=google", "Investimento total R$ 10.000,00"
            ),
        ],
    )
    assert audit["mean_total_brl"] == 15000
    assert audit["internal_count"] == audit["external_count"] == 1
    assert len(audit["comparables"]) == 2


def test_excludes_own_institution_wrong_family_and_ambiguous_amounts():
    offers = [
        offer("https://ens.edu.br/mba", "Investimento total R$ 15.000,00"),
        offer("https://other.example/extension", "Investimento total R$ 100,00"),
        offer(
            "https://other.example/mba",
            "Matrícula R$ 50,00. Mensalidade R$ 500,00 sem número de parcelas.",
        ),
    ]
    offers[1]["title"] = "Extensão em Seguros"
    audit = build_price_reference(
        course_title="MBA Seguros",
        level="MBA Executivo",
        institution_name="Escola de Negócios e Seguros",
        internal_prices=[],
        offers=offers,
    )
    assert audit["mean_total_brl"] is None
    assert {x["reason_code"] for x in audit["excluded"]} >= {
        "own_institution",
        "category_mismatch",
        "total_not_observed",
    }


def test_unattributed_multiple_totals_remain_ambiguous_even_when_a_term_matches():
    audit = build_price_reference(
        course_title="MBA Seguros",
        level="MBA Executivo",
        institution_name="ENS",
        internal_prices=[],
        offers=[offer("https://other.example/mba", "12x de R$ 500,00 ou 20x de R$ 400,00")],
        installments=20,
    )
    assert audit["mean_total_brl"] is None
    assert audit["excluded"][0]["reason_code"] == "ambiguous_payment_condition"


def test_different_course_with_matching_term_cannot_supply_the_mba_price():
    audit = build_price_reference(
        course_title="MBA Gestão de Seguros",
        level="MBA Executivo",
        institution_name="ENS",
        internal_prices=[],
        installments=20,
        offers=[
            offer(
                "https://college.example/mba",
                "MBA Gestão de Seguros: 12x de R$ 1.000,00. Curso de Inglês: 20x de R$ 50,00.",
            )
        ],
    )
    assert audit["mean_total_brl"] is None


def test_single_explicit_installment_total_remains_eligible():
    audit = build_price_reference(
        course_title="MBA Seguros",
        level="MBA Executivo",
        institution_name="ENS",
        internal_prices=[],
        installments=20,
        offers=[offer("https://college.example/mba", "MBA Seguros: 20x de R$ 400,00")],
    )
    assert audit["mean_total_brl"] == 8000


def test_installment_registration_fee_is_not_the_course_price():
    audit = build_price_reference(
        course_title="MBA Seguros",
        level="MBA Executivo",
        institution_name="ENS",
        internal_prices=[],
        offers=[
            offer(
                "https://college.example/mba",
                "MBA em Gestão de Seguros. Taxa de matrícula em 2x de R$ 100,00. Mensalidade sob consulta.",
            )
        ],
    )
    assert audit["mean_total_brl"] is None


def test_registration_fee_does_not_hide_a_separately_identified_course_total():
    conditions = extract_price_conditions(
        "Taxa de matrícula em 2x de R$ 100,00. Curso em 20x de R$ 976,00."
    )
    assert [c["total_brl"] for c in conditions] == [19520]


def test_other_courses_footer_is_not_assigned_to_the_mba():
    audit = build_price_reference(
        course_title="MBA Gestão de Seguros",
        level="MBA Executivo",
        institution_name="ENS",
        internal_prices=[],
        offers=[
            offer(
                "https://college.example/mba",
                "MBA Gestão de Seguros: 20x de R$ 1.000,00. Outros cursos: Inglês 20x de R$ 50,00.",
            )
        ],
        installments=20,
    )
    assert audit["mean_total_brl"] == 20000


def test_multiple_totals_with_same_payment_term_are_not_silently_selected():
    audit = build_price_reference(
        course_title="MBA Seguros",
        level="MBA Executivo",
        institution_name="ENS",
        internal_prices=[],
        offers=[
            offer(
                "https://college.example/mba",
                "20x de R$ 1.000,00 ou 20x de R$ 50,00 com condições não identificadas.",
            )
        ],
        installments=20,
    )
    assert audit["mean_total_brl"] is None


def test_current_dated_offer_remains_eligible():
    audit = build_price_reference(
        course_title="MBA Seguros",
        level="MBA Executivo",
        institution_name="ENS",
        internal_prices=[],
        offers=[
            offer(
                "https://college.example/mba", "Investimento total R$ 20.000,00", date="2026-10-28"
            )
        ],
    )
    assert audit["mean_total_brl"] == 20000
