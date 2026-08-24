from fastapi import APIRouter, Depends, HTTPException, status
from neo4j import AsyncSession
from app.database import neo4j_service

router = APIRouter()

@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check(session: AsyncSession = Depends(neo4j_service.get_session)):
    try:
        # Envia um comando Cypher super leve só para testar a resposta
        result = await session.run("RETURN 1 AS status")
        record = await result.single()
        
        if record and record["status"] == 1:
            return {"status": "online", "database": "connected, AuraDB is UP!"}
            
        raise HTTPException(status_code=500, detail="Resposta inesperada do banco")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro de conexão: {str(e)}")
