from app.core.ranking_service import RankingService
from app.core.weights import WEIGHT_QUALIFICATION


def test_calculate_score_high_qualification_adds_excellence_reason():
    candidate = {"avg_qualification_score": 5.0}

    result = RankingService.calculate_score(candidate)

    assert result["score"] == round(1.0 * WEIGHT_QUALIFICATION, 2)
    assert len(result["reasons"]) == 1
    assert "Excelência técnica" in result["reasons"][0]


def test_calculate_score_minimum_qualification_adds_minimum_reason():
    candidate = {"avg_qualification_score": 2.0}

    result = RankingService.calculate_score(candidate)

    norm = 2.0 / 5.0
    assert result["score"] == round(norm * WEIGHT_QUALIFICATION, 2)
    assert "nível técnico mínimo" in result["reasons"][0]


def test_calculate_score_zero_qualification_has_no_reasons():
    candidate = {"avg_qualification_score": 0.0}

    result = RankingService.calculate_score(candidate)

    assert result["score"] == 0.0
    assert result["reasons"] == []


def test_calculate_score_missing_qualification_key_defaults_to_zero():
    candidate = {}

    result = RankingService.calculate_score(candidate)

    assert result["score"] == 0.0
    assert result["reasons"] == []


def test_calculate_score_caps_normalized_score_at_one():
    # Uma nota acima da escala esperada (1-5) não deve gerar score > peso máximo.
    candidate = {"avg_qualification_score": 10.0}

    result = RankingService.calculate_score(candidate)

    assert result["score"] == round(1.0 * WEIGHT_QUALIFICATION, 2)


def test_calculate_score_does_not_mutate_input_candidate():
    candidate = {"avg_qualification_score": 3.0}

    RankingService.calculate_score(candidate)

    assert "score" not in candidate
    assert "reasons" not in candidate


def test_calculate_score_preserves_other_candidate_fields():
    candidate = {
        "candidate_id": "prof_1",
        "name": "Ana Silva",
        "avg_qualification_score": 4.0,
    }

    result = RankingService.calculate_score(candidate)

    assert result["candidate_id"] == "prof_1"
    assert result["name"] == "Ana Silva"
