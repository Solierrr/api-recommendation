from app.core.weights import WEIGHT_QUALIFICATION


class RankingService:
    @staticmethod
    def calculate_score(candidate: dict) -> dict:
        """
        Recebe um candidato do grafo, calcula a pontuação ponderada e gera os motivos.
        """
        reasons = []
        
        # Normalização da nota de qualificação (assume escala de 1 a 5)
        raw_qual_score = candidate.get("avg_qualification_score", 0.0)
        norm_qual_score = min(raw_qual_score / 5.0, 1.0)
        
        if norm_qual_score >= 0.8:
            reasons.append(f"Excelência técnica no serviço com nota {raw_qual_score:.1f}/5.0")
        elif norm_qual_score > 0.0:
            reasons.append(f"Atende ao nível técnico mínimo requerido ({raw_qual_score:.1f}/5.0)")

        # Cálculo final com pesos configuráveis
        final_score = (norm_qual_score * WEIGHT_QUALIFICATION)
        
        # Adiciona metadados de recomendação ao dicionário do candidato
        candidate_result = candidate.copy()
        candidate_result["score"] = round(final_score, 2)
        candidate_result["reasons"] = reasons
        
        return candidate_result
