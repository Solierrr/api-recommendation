MATCH (offer:SolarOffer {
    source: $source,
    sync_version: $sync_version
})-[:OF_MODEL]->(model:SolarModel {
    source: $source,
    sync_version: $sync_version
})
MATCH (offer)-[:FROM_SUPPLIER]->(supplier:Supplier {
    source: $source,
    sync_version: $sync_version
})
WHERE model.status = 'APPROVED'
  AND model.power_wp > 0
  AND model.efficiency >= 0
  AND model.efficiency <= 100
  AND model.dimension > 0
  AND model.weight > 0
  AND supplier.status = 'ACTIVE'
  AND supplier.subscription_active = true
  AND offer.unit_price_cents > 0
  AND offer.effective_availability > 0
  AND (offer.expiration_at IS NULL OR offer.expiration_at > datetime())
RETURN
    model.id AS model_id,
    offer.id AS offer_id,
    supplier.id AS supplier_id,
    supplier.trade_name AS supplier_trade_name,
    model.brand AS brand,
    model.model AS model,
    model.power_wp AS power_wp,
    model.efficiency AS efficiency,
    model.dimension AS dimension,
    model.weight AS weight,
    offer.unit_price_cents AS unit_price_cents,
    offer.effective_availability AS effective_availability,
    offer.accepted_proposal_quantity AS accepted_proposal_quantity,
    supplier.geolocation_count AS supplier_geolocation_count,
    supplier.latitude AS supplier_latitude,
    supplier.longitude AS supplier_longitude
ORDER BY offer.id
LIMIT $fetch_limit
