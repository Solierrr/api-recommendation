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
proven AS (
    SELECT
        supplier.id::text AS supplier_id,
        company.id::text AS company_id,
        company.trade_name,
        supplier.business_type,
        COUNT(offer.id)::integer AS offer_count,
        COALESCE(SUM(accepted_usage.accepted_proposal_quantity), 0)::integer AS accepted_proposal_quantity
    FROM supplier
    JOIN company
      ON company.id = supplier.company_id
    JOIN active_subscriptions
      ON active_subscriptions.supplier_id = supplier.id
     AND active_subscriptions.subscription_active IS TRUE
    JOIN offer
      ON offer.supplier_id = supplier.id
    JOIN model
      ON model.id = offer.model_id
    JOIN stock
      ON stock.supplier_id = offer.supplier_id
     AND stock.model_id = offer.model_id
    LEFT JOIN accepted_usage
      ON accepted_usage.offer_id = offer.id
    WHERE supplier.status = 'ACTIVE'
      AND model.status = 'APPROVED'
      AND model.power_wp > 0
      AND model.efficiency >= 0
      AND model.efficiency <= 100
      AND model.width > 0
      AND model.length > 0
      AND model.weight > 0
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
    GROUP BY supplier.id, company.id, company.trade_name, supplier.business_type
    ORDER BY accepted_proposal_quantity DESC, offer_count DESC, supplier.id
    LIMIT $1
)
SELECT *
FROM proven
ORDER BY random()
LIMIT $2
