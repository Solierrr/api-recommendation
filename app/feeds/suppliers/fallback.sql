WITH active_subscriptions AS (
    SELECT
        fk_supplier,
        BOOL_OR(
            status = 'PAID'
            AND (end_date IS NULL OR end_date > CURRENT_TIMESTAMP)
        ) AS subscription_active
    FROM subscription
    GROUP BY fk_supplier
),
stock AS (
    SELECT fk_supplier, fk_model, SUM(quantity)::integer AS quantity
    FROM inventory
    GROUP BY fk_supplier, fk_model
),
accepted_usage AS (
    SELECT
        proposal_item.fk_offer,
        COALESCE(SUM(proposal_item.quantity), 0)::integer AS accepted_proposal_quantity
    FROM proposal_item
    JOIN proposal
      ON proposal.id = proposal_item.fk_proposal
    WHERE proposal.status = 'ACCEPTED'
    GROUP BY proposal_item.fk_offer
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
      ON company.id = supplier.fk_company
    JOIN active_subscriptions
      ON active_subscriptions.fk_supplier = supplier.id
     AND active_subscriptions.subscription_active IS TRUE
    JOIN offer
      ON offer.fk_supplier = supplier.id
    JOIN model
      ON model.id = offer.fk_model
    JOIN stock
      ON stock.fk_supplier = offer.fk_supplier
     AND stock.fk_model = offer.fk_model
    LEFT JOIN accepted_usage
      ON accepted_usage.fk_offer = offer.id
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
          offer.expiration_date IS NULL
          OR offer.expiration_date > CURRENT_TIMESTAMP
      )
    GROUP BY supplier.id, company.id, company.trade_name, supplier.business_type
    ORDER BY accepted_proposal_quantity DESC, offer_count DESC, supplier.id
    LIMIT $1
)
SELECT *
FROM proven
ORDER BY random()
LIMIT $2
