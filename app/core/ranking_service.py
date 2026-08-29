class RankingService:
    @staticmethod
    def calculate_score(candidate: dict) -> dict:
        """Normaliza a média real das avaliações do api-core para uma nota de 0 a 1."""
        average_rating = float(candidate.get("average_rating", 0.0))
        review_count = int(candidate.get("review_count", 0))
        normalized_score = max(0.0, min(average_rating / 5.0, 1.0))

        if review_count == 0:
            reasons = ["Profissional ainda não possui avaliações"]
        elif normalized_score >= 0.8:
            reasons = [
                f"Excelente avaliação: {average_rating:.1f}/5 em {review_count} avaliação(ões)"
            ]
        else:
            reasons = [
                f"Avaliação média: {average_rating:.1f}/5 em {review_count} avaliação(ões)"
            ]

        candidate_result = candidate.copy()
        candidate_result["score"] = round(normalized_score, 2)
        candidate_result["reasons"] = reasons
        return candidate_result
