from neo4j import AsyncSession

VERSION = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
OLD_VERSION = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"

UNIT = "00000000-0000-4000-8000-000000000131"
PROFESSION = "00000000-0000-4000-8000-000000000181"
OTHER_PROFESSION = "00000000-0000-4000-8000-000000000182"
TECHNICIAN = "00000000-0000-4000-8000-000000000171"
OLD_TECHNICIAN = "00000000-0000-4000-8000-000000000179"
INACTIVE_TECHNICIAN = "00000000-0000-4000-8000-000000000178"
SUPPLIER = "00000000-0000-4000-8000-0000000000d1"
FAR_SUPPLIER = "00000000-0000-4000-8000-0000000000d3"
SUSPENDED_SUPPLIER = "00000000-0000-4000-8000-0000000000d2"
OFFER = "00000000-0000-4000-8000-000000000101"
FAR_OFFER = "00000000-0000-4000-8000-000000000105"
SUSPENDED_OFFER = "00000000-0000-4000-8000-000000000103"
REJECTED_OFFER = "00000000-0000-4000-8000-000000000102"

SEED = """
MATCH (n) DETACH DELETE n
"""

BUILD = """
CREATE (:SyncState {source: 'api-core', active_version: $version, activated_at: datetime(),
                    previous_version: $old_version})

CREATE (unit:LocalUnit {source: 'api-core', sync_version: $version, id: $unit,
                        geolocation_count: 1, latitude: 0.0, longitude: 0.0})

CREATE (good:SolarModel {source: 'api-core', sync_version: $version, id: '00000000-0000-4000-8000-0000000000f1', status: 'APPROVED',
                         brand: 'Canadian', model: 'CS7N', power_wp: 550.0, efficiency: 21.5,
                         dimension: 2.53, weight: 28.0})
CREATE (rejected:SolarModel {source: 'api-core', sync_version: $version, id: '00000000-0000-4000-8000-0000000000f2',
                             status: 'REJECTED', brand: 'Velha', model: 'X1', power_wp: 400.0,
                             efficiency: 18.0, dimension: 1.7, weight: 22.0})

CREATE (near:Supplier {source: 'api-core', sync_version: $version, id: $supplier, status: 'ACTIVE',
                       subscription_active: true, trade_name: 'Solar Forte', business_type: 'DISTRIBUTOR',
                       company_id: '00000000-0000-4000-8000-0000000000c1',
                       geolocation_count: 1, latitude: 0.0, longitude: 1.0})
CREATE (far:Supplier {source: 'api-core', sync_version: $version, id: $far_supplier, status: 'ACTIVE',
                      subscription_active: true, trade_name: 'Sol Distante', business_type: 'RETAILER',
                      company_id: '00000000-0000-4000-8000-0000000000c3',
                      geolocation_count: 1, latitude: 0.0, longitude: 5.0})
CREATE (suspended:Supplier {source: 'api-core', sync_version: $version, id: $suspended_supplier,
                            status: 'SUSPENDED', subscription_active: true, trade_name: 'Painel Parado',
                            business_type: 'DISTRIBUTOR',
                            company_id: '00000000-0000-4000-8000-0000000000c2',
                            geolocation_count: 0})

CREATE (o1:SolarOffer {source: 'api-core', sync_version: $version, id: $offer, unit_price_cents: 75055,
                       effective_availability: 15, accepted_proposal_quantity: 3})
CREATE (o2:SolarOffer {source: 'api-core', sync_version: $version, id: $far_offer, unit_price_cents: 60000,
                       effective_availability: 4, accepted_proposal_quantity: 9})
CREATE (o3:SolarOffer {source: 'api-core', sync_version: $version, id: $rejected_offer,
                       unit_price_cents: 10000, effective_availability: 5, accepted_proposal_quantity: 99})
CREATE (o4:SolarOffer {source: 'api-core', sync_version: $version, id: $suspended_offer,
                       unit_price_cents: 20000, effective_availability: 5, accepted_proposal_quantity: 99})
CREATE (o1)-[:OF_MODEL {source: 'api-core', sync_version: $version}]->(good)
CREATE (o2)-[:OF_MODEL {source: 'api-core', sync_version: $version}]->(good)
CREATE (o3)-[:OF_MODEL {source: 'api-core', sync_version: $version}]->(rejected)
CREATE (o4)-[:OF_MODEL {source: 'api-core', sync_version: $version}]->(good)
CREATE (o1)-[:FROM_SUPPLIER {source: 'api-core', sync_version: $version}]->(near)
CREATE (o2)-[:FROM_SUPPLIER {source: 'api-core', sync_version: $version}]->(far)
CREATE (o3)-[:FROM_SUPPLIER {source: 'api-core', sync_version: $version}]->(near)
CREATE (o4)-[:FROM_SUPPLIER {source: 'api-core', sync_version: $version}]->(suspended)

CREATE (engineer:Profession {source: 'api-core', sync_version: $version, id: $profession,
                             name: 'Engenheiro Eletricista'})
CREATE (installer:Profession {source: 'api-core', sync_version: $version, id: $other_profession,
                              name: 'Instalador'})
CREATE (tech:Technician {source: 'api-core', sync_version: $version, id: $technician,
                         name: 'Profissional 00000171', user_active: true,
                         average_rating_global: 4.5, review_count_global: 1,
                         completed_service_count_global: 1, assigned_service_count_global: 2,
                         canceled_service_count_global: 0})
CREATE (inactive:Technician {source: 'api-core', sync_version: $version, id: $inactive_technician,
                             name: 'Profissional 00000178', user_active: false,
                             average_rating_global: 5.0, review_count_global: 50,
                             completed_service_count_global: 50, assigned_service_count_global: 50,
                             canceled_service_count_global: 0})
CREATE (tech)-[:REGISTERED_AS {source: 'api-core', sync_version: $version, valid_certification_count: 1,
                               certification_names: ['NR-10']}]->(engineer)
CREATE (tech)-[:REGISTERED_AS {source: 'api-core', sync_version: $version, valid_certification_count: 2,
                               certification_names: ['NR-10', 'NR-35']}]->(installer)
CREATE (inactive)-[:REGISTERED_AS {source: 'api-core', sync_version: $version,
                                   valid_certification_count: 0, certification_names: []}]->(engineer)

CREATE (old:Technician {source: 'api-core', sync_version: $old_version, id: $old_technician,
                        name: 'Profissional antigo', user_active: true, average_rating_global: 5.0,
                        review_count_global: 99, completed_service_count_global: 99,
                        assigned_service_count_global: 99, canceled_service_count_global: 0})
CREATE (old_profession:Profession {source: 'api-core', sync_version: $old_version, id: $profession,
                                   name: 'Engenheiro Eletricista'})
CREATE (old)-[:REGISTERED_AS {source: 'api-core', sync_version: $old_version,
                              valid_certification_count: 9, certification_names: ['X']}]->(old_profession)
"""


async def seed_graph(session: AsyncSession) -> None:
    await (await session.run(SEED)).consume()
    result = await session.run(
        BUILD,
        version=VERSION,
        old_version=OLD_VERSION,
        unit=UNIT,
        profession=PROFESSION,
        other_profession=OTHER_PROFESSION,
        technician=TECHNICIAN,
        old_technician=OLD_TECHNICIAN,
        inactive_technician=INACTIVE_TECHNICIAN,
        supplier=SUPPLIER,
        far_supplier=FAR_SUPPLIER,
        suspended_supplier=SUSPENDED_SUPPLIER,
        offer=OFFER,
        far_offer=FAR_OFFER,
        rejected_offer=REJECTED_OFFER,
        suspended_offer=SUSPENDED_OFFER,
    )
    await result.consume()


async def clear_graph(session: AsyncSession) -> None:
    await (await session.run(SEED)).consume()
