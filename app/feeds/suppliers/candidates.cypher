MATCH (supplier:Supplier {
    source: $source,
    sync_version: $sync_version
})
WHERE supplier.status = 'ACTIVE'
  AND supplier.subscription_active = true
MATCH (offer:SolarOffer {
    source: $source,
    sync_version: $sync_version
})-[:FROM_SUPPLIER]->(supplier)
MATCH (offer)-[:OF_MODEL]->(model:SolarModel {
    source: $source,
    sync_version: $sync_version
})
WHERE model.status = 'APPROVED'
  AND offer.unit_price_cents > 0
  AND offer.effective_availability > 0
  AND (offer.expiration_at IS NULL OR offer.expiration_at > datetime())
WITH supplier,
     count(offer) AS offer_count,
     sum(offer.accepted_proposal_quantity) AS accepted_proposal_quantity
RETURN
    supplier.id AS supplier_id,
    supplier.company_id AS company_id,
    supplier.trade_name AS trade_name,
    supplier.business_type AS business_type,
    offer_count,
    coalesce(accepted_proposal_quantity, 0) AS accepted_proposal_quantity,
    supplier.geolocation_count AS supplier_geolocation_count,
    supplier.latitude AS supplier_latitude,
    supplier.longitude AS supplier_longitude
ORDER BY supplier.id
LIMIT $fetch_limit
