WITH active_subscriptions AS (
    SELECT
        supplier_id,
        BOOL_OR(
            status = 'PAID'
            AND (ends_at IS NULL OR ends_at > CURRENT_TIMESTAMP)
        ) AS subscription_active
    FROM subscription
    GROUP BY supplier_id
),
stock AS (
    SELECT supplier_id, model_id, SUM(quantity)::integer AS quantity
    FROM inventory
    GROUP BY supplier_id, model_id
),
accepted_usage AS (
    SELECT
        proposal_item.offer_id,
        COALESCE(SUM(proposal_item.quantity), 0)::integer AS accepted_proposal_quantity
    FROM proposal_item
    JOIN proposal
      ON proposal.id = proposal_item.proposal_id
    WHERE proposal.status = 'ACCEPTED'
    GROUP BY proposal_item.offer_id
),
best_value AS (
    SELECT
        offer.id::text AS offer_id,
        supplier.id::text AS supplier_id,
        company.trade_name AS supplier_trade_name,
        model.id::text AS model_id,
        brand.name AS brand,
        model.model_name AS model,
        model.power_wp::double precision AS power_wp,
        model.efficiency::double precision AS efficiency,
        (model.width * model.length)::double precision AS dimension,
        model.weight::double precision AS weight,
        ROUND(offer.unit_price * 100)::bigint AS unit_price_cents,
        LEAST(offer.availability, stock.quantity)::integer AS effective_availability,
        COALESCE(accepted_usage.accepted_proposal_quantity, 0) AS accepted_proposal_quantity,
        (offer.unit_price / model.power_wp)::double precision AS price_per_wp
    FROM offer
    JOIN model
      ON model.id = offer.model_id
    JOIN brand
      ON brand.id = model.brand_id
    JOIN supplier
      ON supplier.id = offer.supplier_id
    JOIN company
      ON company.id = supplier.company_id
    JOIN stock
      ON stock.supplier_id = offer.supplier_id
     AND stock.model_id = offer.model_id
    JOIN active_subscriptions
      ON active_subscriptions.supplier_id = supplier.id
     AND active_subscriptions.subscription_active IS TRUE
    LEFT JOIN accepted_usage
      ON accepted_usage.offer_id = offer.id
    WHERE model.status = 'APPROVED'
      AND model.power_wp > 0
      AND model.efficiency >= 0
      AND model.efficiency <= 100
      AND model.width > 0
      AND model.length > 0
      AND model.weight > 0
      AND supplier.status = 'ACTIVE'
      AND offer.unit_price > 0
      AND offer.availability > 0
      AND 'NaN'::numeric NOT IN (
          model.power_wp, model.efficiency, model.width, model.length, model.weight, offer.unit_price
      )
      AND stock.quantity > 0
      AND (
          offer.expires_at IS NULL
          OR offer.expires_at > CURRENT_TIMESTAMP
      )
    ORDER BY offer.unit_price / model.power_wp, model.efficiency DESC, offer.id
    LIMIT $1
)
SELECT *
FROM best_value
ORDER BY random()
LIMIT $2
