from app.core.ranking_service import RankingService


def test_calculate_score_high_rating_adds_excellence_reason():
    result = RankingService.calculate_score({"average_rating": 5.0, "review_count": 10})

    assert result["score"] == 1.0
    assert "Excelente avaliação" in result["reasons"][0]


def test_calculate_score_average_rating_is_normalized():
    result = RankingService.calculate_score({"average_rating": 2.0, "review_count": 3})

    assert result["score"] == 0.4
    assert "Avaliação média" in result["reasons"][0]


def test_calculate_score_without_reviews_explains_cold_start():
    result = RankingService.calculate_score({"average_rating": 0.0, "review_count": 0})

    assert result["score"] == 0.0
    assert result["reasons"] == ["Profissional ainda não possui avaliações"]


def test_calculate_score_missing_fields_defaults_to_zero():
    result = RankingService.calculate_score({})

    assert result["score"] == 0.0
    assert result["reasons"] == ["Profissional ainda não possui avaliações"]


def test_calculate_score_caps_normalized_score_at_one():
    result = RankingService.calculate_score({"average_rating": 10.0, "review_count": 1})

    assert result["score"] == 1.0


def test_calculate_score_does_not_mutate_input_candidate():
    candidate = {"average_rating": 3.0, "review_count": 2}

    RankingService.calculate_score(candidate)

    assert "score" not in candidate
    assert "reasons" not in candidate


def test_calculate_score_preserves_other_candidate_fields():
    candidate = {
        "candidate_id": "prof_1",
        "name": "Ana Silva",
        "average_rating": 4.0,
        "review_count": 5,
    }

    result = RankingService.calculate_score(candidate)

    assert result["candidate_id"] == "prof_1"
    assert result["name"] == "Ana Silva"
