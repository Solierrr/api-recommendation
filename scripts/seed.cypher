// Script de povoamento (seed) do grafo do Motor de Recomendação B2B.
// Uso: python scripts/seed.py (lê este arquivo e executa contra o Neo4j
// configurado em NEO4J_URI / NEO4J_USER / NEO4J_PASSWORD no .env)
//
// ATENÇÃO: a primeira instrução apaga TODOS os nós e relacionamentos do
// banco de dados configurado antes de recriar a massa de dados de teste.

// Limpar banco de dados
MATCH (n) DETACH DELETE n;

// Criar Entidades de Dominio
CREATE (emp:Empresa {id: "emp_1", nome: "TechCorp Brasil"});
CREATE (prj:Projeto {id: "prj_101", nome: "Migracao Cloud"});
CREATE (srv1:Servico {nome: "Desenvolvimento Python"});
CREATE (srv2:Servico {nome: "Arquitetura Cloud"});

CREATE (q1:Qualificacao {nome: "FastAPI"});
CREATE (q2:Qualificacao {nome: "Neo4j"});
CREATE (q3:Qualificacao {nome: "AWS"});

CREATE (p1:Profissional {id: "prof_1", nome: "Ana Silva"});
CREATE (p2:Profissional {id: "prof_2", nome: "Carlos Souza"});
CREATE (p3:Profissional {id: "prof_3", nome: "Mariana Costa"});

// Mapear Relacionamentos do Pipeline Operacional
MATCH (emp:Empresa {id: "emp_1"}), (prj:Projeto {id: "prj_101"})
CREATE (emp)-[:POSSUI_PROJETO]->(prj);

MATCH (prj:Projeto {id: "prj_101"}), (srv1:Servico {nome: "Desenvolvimento Python"})
CREATE (prj)-[:DEMANDA_SERVICO]->(srv1);

// Profissional 1 - Altamente Qualificado
MATCH (p1:Profissional {id: "prof_1"}), (srv1:Servico {nome: "Desenvolvimento Python"})
CREATE (p1)-[:OFERECE_SERVICO]->(srv1);

MATCH (p1:Profissional {id: "prof_1"}), (q1:Qualificacao {nome: "FastAPI"})
CREATE (p1)-[:POSSUI_QUALIFICACAO {nivel: 5}]->(q1);

MATCH (p1:Profissional {id: "prof_1"}), (q2:Qualificacao {nome: "Neo4j"})
CREATE (p1)-[:POSSUI_QUALIFICACAO {nivel: 4}]->(q2);

// Profissional 2 - Qualificacao Media
MATCH (p2:Profissional {id: "prof_2"}), (srv1:Servico {nome: "Desenvolvimento Python"})
CREATE (p2)-[:OFERECE_SERVICO]->(srv1);

MATCH (p2:Profissional {id: "prof_2"}), (q1:Qualificacao {nome: "FastAPI"})
CREATE (p2)-[:POSSUI_QUALIFICACAO {nivel: 3}]->(q1);

// Profissional 3 - Outro Servico
MATCH (p3:Profissional {id: "prof_3"}), (srv2:Servico {nome: "Arquitetura Cloud"})
CREATE (p3)-[:OFERECE_SERVICO]->(srv2);

MATCH (p3:Profissional {id: "prof_3"}), (q3:Qualificacao {nome: "AWS"})
CREATE (p3)-[:POSSUI_QUALIFICACAO {nivel: 5}]->(q3);
