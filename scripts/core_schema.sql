CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TYPE supplier_status AS ENUM ('ACTIVE', 'SUSPENDED', 'DISABLED');

CREATE TYPE billing_cycle AS ENUM ('MONTHLY', 'QUARTELY', 'ANNUAL');

CREATE TYPE subscription_status AS ENUM ('PAID', 'DELINQUENT', 'SUSPENDED');

CREATE TYPE payment_method AS ENUM ('PIX', 'BOLETO', 'CREDIT_CARD', 'BANK_TRANSFER');

CREATE TYPE billing_status AS ENUM ('PENDING', 'PAID', 'CANCELED', 'REFUNDED');

CREATE TYPE model_status AS ENUM ('APPROVED', 'REJECTED', 'UNDER_REVIEW');

CREATE TYPE local_unit_type AS ENUM ('BUILDING', 'HOUSE', 'CONDOMINIUM');

CREATE TYPE proposal_status AS ENUM (
  'OPEN',
  'NEGOTIATING',
  'ACCEPTED',
  'REJECTED',
  'CANCELED'
);

CREATE TYPE affiliation_type AS ENUM ('INDEPENDENT', 'AFFILIATED', 'PARTNER');

CREATE TYPE project_status AS ENUM ('OPEN', 'IN_PROGRESS', 'COMPLETED', 'CANCELED');

CREATE TYPE service_status AS ENUM ('OPEN', 'IN_PROGRESS', 'COMPLETED', 'CANCELED');

CREATE TYPE audit_operation AS ENUM ('INSERT', 'UPDATE', 'DELETE');

CREATE TABLE IF NOT EXISTS "address" (
  "id" UUID NOT NULL DEFAULT gen_random_uuid (),
  "state" VARCHAR(2) NOT NULL,
  "city" TEXT NOT NULL,
  "neighborhood" TEXT,
  "zip_code" VARCHAR(8) NOT NULL,
  "street" TEXT NOT NULL,
  "number" VARCHAR(10),
  CONSTRAINT "pk_address" PRIMARY KEY ("id")
);

CREATE TABLE IF NOT EXISTS "business_contact" (
  "id" UUID NOT NULL DEFAULT gen_random_uuid (),
  "business_email" VARCHAR(100) NOT NULL,
  "phone" VARCHAR(20),
  "website" TEXT,
  CONSTRAINT "pk_business_contact" PRIMARY KEY ("id")
);

CREATE TABLE IF NOT EXISTS "users" (
  "id" UUID NOT NULL DEFAULT gen_random_uuid (),
  "auth_id" UUID NOT NULL,
  "created_at" TIMESTAMPTZ NOT NULL DEFAULT now (),
  CONSTRAINT "pk_users" PRIMARY KEY ("id"),
  CONSTRAINT "uq_users_auth_id" UNIQUE ("auth_id")
);

CREATE TABLE IF NOT EXISTS "role" (
  "id" UUID NOT NULL DEFAULT gen_random_uuid (),
  "name" VARCHAR(60) NOT NULL,
  "description" VARCHAR(120) NOT NULL,
  CONSTRAINT "pk_role" PRIMARY KEY ("id")
);

CREATE TABLE IF NOT EXISTS "permission" (
  "id" UUID NOT NULL DEFAULT gen_random_uuid (),
  "permission_name" VARCHAR(100),
  "mask" TEXT NOT NULL,
  CONSTRAINT "pk_permission" PRIMARY KEY ("id"),
  CONSTRAINT "uq_permission_name" UNIQUE ("permission_name")
);

CREATE TABLE IF NOT EXISTS "subscription_plan" (
  "id" UUID NOT NULL DEFAULT gen_random_uuid (),
  "name" TEXT NOT NULL,
  "amount" NUMERIC(12, 2) NOT NULL CHECK ("amount" >= 0),
  "billing_cycle" billing_cycle NOT NULL,
  CONSTRAINT "pk_subscription_plan" PRIMARY KEY ("id")
);

CREATE TABLE IF NOT EXISTS "model" (
  "id" UUID NOT NULL DEFAULT gen_random_uuid (),
  "brand" TEXT NOT NULL,
  "model_name" TEXT NOT NULL,
  "power_wp" NUMERIC(7, 2) NOT NULL CHECK ("power_wp" >= 0),
  "efficiency" NUMERIC(5, 2) NOT NULL CHECK ("efficiency" BETWEEN 0 AND 100),
  "dimension" NUMERIC(8, 3) NOT NULL CHECK ("dimension" >= 0),
  "weight" NUMERIC(6, 2) NOT NULL CHECK ("weight" >= 0),
  "status" model_status NOT NULL DEFAULT 'UNDER_REVIEW',
  "created_at" TIMESTAMPTZ NOT NULL DEFAULT now (),
  CONSTRAINT "pk_model" PRIMARY KEY ("id")
);

CREATE TABLE IF NOT EXISTS "profession" (
  "id" UUID NOT NULL DEFAULT gen_random_uuid (),
  "name" VARCHAR(100) NOT NULL,
  "description" TEXT,
  CONSTRAINT "pk_profession" PRIMARY KEY ("id"),
  CONSTRAINT "uq_profession_name" UNIQUE ("name")
);

CREATE TABLE IF NOT EXISTS "company" (
  "id" UUID NOT NULL DEFAULT gen_random_uuid (),
  "address_id" UUID NOT NULL,
  "business_contact_id" UUID NOT NULL,
  "cnpj" VARCHAR(20) NOT NULL,
  "trade_name" VARCHAR(120) NOT NULL,
  "legal_name" VARCHAR(120) NOT NULL,
  CONSTRAINT "pk_company" PRIMARY KEY ("id"),
  CONSTRAINT "uq_company_cnpj" UNIQUE ("cnpj")
);

CREATE TABLE IF NOT EXISTS "geolocation" (
  "id" UUID NOT NULL DEFAULT gen_random_uuid (),
  "address_id" UUID,
  "latitude" NUMERIC(10, 7),
  "longitude" NUMERIC(10, 7),
  CONSTRAINT "pk_geolocation" PRIMARY KEY ("id"),
  CONSTRAINT "uq_geolocation_address" UNIQUE ("address_id")
);

CREATE TABLE IF NOT EXISTS "professional" (
  "id" UUID NOT NULL DEFAULT gen_random_uuid (),
  "user_id" UUID NOT NULL,
  CONSTRAINT "pk_professional" PRIMARY KEY ("id"),
  CONSTRAINT "uq_professional_user" UNIQUE ("user_id")
);

CREATE TABLE IF NOT EXISTS "professional_review" (
  "id" UUID NOT NULL DEFAULT gen_random_uuid (),
  "professional_id" UUID NOT NULL,
  "reviewer_id" UUID NOT NULL,
  "rating" NUMERIC(2, 1) NOT NULL CHECK ("rating" BETWEEN 0 AND 5),
  "comment" TEXT,
  "active" BOOLEAN NOT NULL DEFAULT true,
  "created_at" TIMESTAMPTZ NOT NULL DEFAULT now (),
  CONSTRAINT "pk_professional_review" PRIMARY KEY ("id")
);

CREATE TABLE IF NOT EXISTS "supplier" (
  "id" UUID NOT NULL DEFAULT gen_random_uuid (),
  "company_id" UUID NOT NULL,
  "status" supplier_status NOT NULL DEFAULT 'ACTIVE',
  "business_type" VARCHAR(40),
  CONSTRAINT "pk_supplier" PRIMARY KEY ("id")
);

CREATE TABLE IF NOT EXISTS "product_review" (
  "id" UUID NOT NULL DEFAULT gen_random_uuid (),
  "model_id" UUID NOT NULL,
  "reviewer_id" UUID NOT NULL,
  "rating" NUMERIC(2, 1) NOT NULL CHECK ("rating" BETWEEN 0 AND 5),
  "comment" TEXT,
  "active" BOOLEAN NOT NULL DEFAULT true,
  "created_at" TIMESTAMPTZ NOT NULL DEFAULT now (),
  CONSTRAINT "pk_product_review" PRIMARY KEY ("id")
);

CREATE TABLE IF NOT EXISTS "client" (
  "id" UUID NOT NULL DEFAULT gen_random_uuid (),
  "company_id" UUID NOT NULL,
  "business_type" VARCHAR(40),
  CONSTRAINT "pk_client" PRIMARY KEY ("id")
);

CREATE TABLE IF NOT EXISTS "company_role" (
  "id" UUID NOT NULL DEFAULT gen_random_uuid (),
  "company_id" UUID NOT NULL,
  "role_id" UUID NOT NULL,
  CONSTRAINT "pk_company_role" PRIMARY KEY ("id"),
  CONSTRAINT "uq_company_role_company_role" UNIQUE ("company_id", "role_id")
);

CREATE TABLE IF NOT EXISTS "user_company" (
  "id" UUID NOT NULL DEFAULT gen_random_uuid (),
  "company_id" UUID NOT NULL,
  "user_id" UUID NOT NULL,
  "role_id" UUID NOT NULL,
  CONSTRAINT "pk_user_company" PRIMARY KEY ("id"),
  CONSTRAINT "uq_user_company_user_company" UNIQUE ("user_id", "company_id")
);

CREATE TABLE IF NOT EXISTS "role_permission" (
  "id" UUID NOT NULL DEFAULT gen_random_uuid (),
  "role_id" UUID NOT NULL,
  "permission_id" UUID NOT NULL,
  CONSTRAINT "pk_role_permission" PRIMARY KEY ("id"),
  CONSTRAINT "uq_role_permission" UNIQUE ("role_id", "permission_id")
);

CREATE TABLE IF NOT EXISTS "subscription" (
  "id" UUID NOT NULL DEFAULT gen_random_uuid (),
  "supplier_id" UUID NOT NULL,
  "plan_id" UUID NOT NULL,
  "status" subscription_status NOT NULL DEFAULT 'PAID',
  "auto_renewal" BOOLEAN NOT NULL DEFAULT true,
  "start_date" TIMESTAMPTZ NOT NULL,
  "end_date" TIMESTAMPTZ,
  "created_at" TIMESTAMPTZ NOT NULL DEFAULT now (),
  CONSTRAINT "pk_subscription" PRIMARY KEY ("id"),
  CONSTRAINT "ck_subscription_dates" CHECK (
    "end_date" IS NULL
    OR "end_date" >= "start_date"
  )
);

CREATE TABLE IF NOT EXISTS "stock" (
  "id" UUID NOT NULL DEFAULT gen_random_uuid (),
  "supplier_id" UUID NOT NULL,
  "model_id" UUID NOT NULL,
  "quantity" INTEGER NOT NULL CHECK ("quantity" >= 0),
  CONSTRAINT "pk_stock" PRIMARY KEY ("id"),
  CONSTRAINT "uq_stock_supplier_model" UNIQUE ("supplier_id", "model_id")
);

CREATE TABLE IF NOT EXISTS "offer" (
  "id" UUID NOT NULL DEFAULT gen_random_uuid (),
  "supplier_id" UUID NOT NULL,
  "model_id" UUID NOT NULL,
  "unit_price" NUMERIC(12, 2) NOT NULL CHECK ("unit_price" >= 0),
  "availability" INTEGER NOT NULL CHECK ("availability" >= 0),
  "expiration_date" DATE,
  "created_at" TIMESTAMPTZ NOT NULL DEFAULT now (),
  CONSTRAINT "pk_offer" PRIMARY KEY ("id")
);

CREATE TABLE IF NOT EXISTS "local_unit" (
  "id" UUID NOT NULL DEFAULT gen_random_uuid (),
  "address_id" UUID NOT NULL,
  "client_id" UUID NOT NULL,
  "complement" TEXT,
  "unit_type" local_unit_type NOT NULL,
  CONSTRAINT "pk_local_unit" PRIMARY KEY ("id")
);

CREATE TABLE IF NOT EXISTS "professional_affiliation" (
  "id" UUID NOT NULL DEFAULT gen_random_uuid (),
  "company_id" UUID NOT NULL,
  "professional_id" UUID NOT NULL,
  "affiliation_type" affiliation_type NOT NULL,
  CONSTRAINT "pk_professional_affiliation" PRIMARY KEY ("id"),
  CONSTRAINT "uq_professional_affiliation_company_professional" UNIQUE ("company_id", "professional_id")
);

CREATE TABLE IF NOT EXISTS "professional_registration" (
  "id" UUID NOT NULL DEFAULT gen_random_uuid (),
  "professional_id" UUID NOT NULL,
  "profession_id" UUID NOT NULL,
  "council" VARCHAR(60) NOT NULL,
  "number" VARCHAR(30) NOT NULL,
  "expiration_date" DATE NOT NULL,
  CONSTRAINT "pk_professional_registration" PRIMARY KEY ("id"),
  CONSTRAINT "uq_professional_registration_council_number" UNIQUE ("council", "number")
);

CREATE TABLE IF NOT EXISTS "certification" (
  "id" UUID NOT NULL DEFAULT gen_random_uuid (),
  "professional_id" UUID NOT NULL,
  "type" VARCHAR(255) NOT NULL,
  "information" TEXT NOT NULL,
  "image" TEXT,
  CONSTRAINT "pk_certification" PRIMARY KEY ("id")
);

CREATE TABLE IF NOT EXISTS "unit_report" (
  "id" UUID NOT NULL DEFAULT gen_random_uuid (),
  "local_unit_id" UUID NOT NULL,
  "specifications" TEXT,
  "local_photos" JSONB,
  "report_date" TIMESTAMPTZ NOT NULL DEFAULT now (),
  CONSTRAINT "pk_unit_report" PRIMARY KEY ("id")
);

CREATE TABLE IF NOT EXISTS "proposal" (
  "id" UUID NOT NULL DEFAULT gen_random_uuid (),
  "client_id" UUID NOT NULL,
  "status" proposal_status NOT NULL DEFAULT 'OPEN',
  "notes" TEXT,
  "total_amount" NUMERIC(12, 2) CHECK ("total_amount" >= 0),
  "created_at" TIMESTAMPTZ NOT NULL DEFAULT now (),
  "updated_at" TIMESTAMPTZ,
  CONSTRAINT "pk_proposal" PRIMARY KEY ("id")
);

CREATE TABLE IF NOT EXISTS "technical_project" (
  "id" UUID NOT NULL DEFAULT gen_random_uuid (),
  "client_id" UUID NOT NULL,
  "local_unit_id" UUID NOT NULL,
  "status" project_status NOT NULL DEFAULT 'OPEN',
  "start_date" TIMESTAMPTZ NOT NULL DEFAULT now (),
  "end_date" TIMESTAMPTZ,
  CONSTRAINT "pk_technical_project" PRIMARY KEY ("id"),
  CONSTRAINT "ck_technical_project_dates" CHECK (
    "end_date" IS NULL
    OR "end_date" >= "start_date"
  )
);

CREATE TABLE IF NOT EXISTS "billing" (
  "id" UUID NOT NULL DEFAULT gen_random_uuid (),
  "subscription_id" UUID NOT NULL,
  "amount" NUMERIC(12, 2) NOT NULL CHECK ("amount" >= 0),
  "payment_method" payment_method NOT NULL,
  "status" billing_status NOT NULL DEFAULT 'PENDING',
  "payment_date" TIMESTAMPTZ,
  "created_at" TIMESTAMPTZ NOT NULL DEFAULT now (),
  "due_date" DATE NOT NULL,
  CONSTRAINT "pk_billing" PRIMARY KEY ("id")
);

CREATE TABLE IF NOT EXISTS "proposal_item" (
  "id" UUID NOT NULL DEFAULT gen_random_uuid (),
  "proposal_id" UUID NOT NULL,
  "offer_id" UUID NOT NULL,
  "quantity" INTEGER NOT NULL CHECK ("quantity" >= 0),
  "negotiated_price" NUMERIC(12, 2) CHECK ("negotiated_price" >= 0),
  "discount" NUMERIC(5, 2) CHECK (
    "discount" >= 0
    AND "discount" <= 100
  ),
  CONSTRAINT "pk_proposal_item" PRIMARY KEY ("id")
);

CREATE TABLE IF NOT EXISTS "technical_service" (
  "id" UUID NOT NULL DEFAULT gen_random_uuid (),
  "technical_project_id" UUID NOT NULL,
  "purpose" TEXT NOT NULL,
  "status" service_status NOT NULL DEFAULT 'OPEN',
  "created_at" TIMESTAMPTZ NOT NULL DEFAULT now (),
  "end_date" TIMESTAMPTZ,
  CONSTRAINT "pk_technical_service" PRIMARY KEY ("id")
);

CREATE TABLE IF NOT EXISTS "proposal_unit" (
  "id" UUID NOT NULL DEFAULT gen_random_uuid (),
  "proposal_item_id" UUID NOT NULL,
  "local_unit_id" UUID NOT NULL,
  "quantity" INTEGER NOT NULL CHECK ("quantity" >= 0),
  "note" TEXT,
  CONSTRAINT "pk_proposal_unit" PRIMARY KEY ("id")
);

CREATE TABLE IF NOT EXISTS "service_executor" (
  "id" UUID NOT NULL DEFAULT gen_random_uuid (),
  "service_id" UUID NOT NULL,
  "professional_affiliation_id" UUID NOT NULL,
  "role_function" TEXT NOT NULL,
  CONSTRAINT "pk_service_executor" PRIMARY KEY ("id"),
  CONSTRAINT "uq_service_executor_service_affiliation" UNIQUE ("service_id", "professional_affiliation_id")
);

CREATE TABLE IF NOT EXISTS "service_contract" (
  "id" UUID NOT NULL DEFAULT gen_random_uuid (),
  "service_id" UUID NOT NULL,
  "warranty" TEXT,
  "delivery_deadline" DATE,
  "insurance" BOOLEAN NOT NULL DEFAULT false,
  "utility_approval" BOOLEAN NOT NULL DEFAULT false,
  CONSTRAINT "pk_service_contract" PRIMARY KEY ("id"),
  CONSTRAINT "uq_service_contract_service" UNIQUE ("service_id")
);

CREATE TABLE IF NOT EXISTS "audit_log" (
  "id" UUID NOT NULL DEFAULT gen_random_uuid (),
  "user_id" UUID,
  "record_id" UUID NOT NULL,
  "table_name" VARCHAR(100) NOT NULL,
  "operation" audit_operation NOT NULL,
  "event_timestamp" TIMESTAMPTZ NOT NULL DEFAULT now (),
  "ip_address" VARCHAR(45),
  "user_agent" TEXT,
  "previous_data" JSONB,
  "new_data" JSONB,
  CONSTRAINT "pk_audit_log" PRIMARY KEY ("id")
);

ALTER TABLE "company" ADD CONSTRAINT "fk_company_address" FOREIGN KEY ("address_id") REFERENCES "address" ("id") ON UPDATE CASCADE ON DELETE RESTRICT;

ALTER TABLE "company" ADD CONSTRAINT "fk_company_business_contact" FOREIGN KEY ("business_contact_id") REFERENCES "business_contact" ("id") ON UPDATE CASCADE ON DELETE RESTRICT;

ALTER TABLE "geolocation" ADD CONSTRAINT "fk_geolocation_address" FOREIGN KEY ("address_id") REFERENCES "address" ("id") ON UPDATE CASCADE ON DELETE SET NULL;

ALTER TABLE "professional" ADD CONSTRAINT "fk_professional_user" FOREIGN KEY ("user_id") REFERENCES "users" ("id") ON UPDATE CASCADE ON DELETE CASCADE;

ALTER TABLE "professional_review" ADD CONSTRAINT "fk_professional_review_professional" FOREIGN KEY ("professional_id") REFERENCES "professional" ("id") ON UPDATE CASCADE ON DELETE CASCADE;

ALTER TABLE "professional_review" ADD CONSTRAINT "fk_professional_review_reviewer" FOREIGN KEY ("reviewer_id") REFERENCES "users" ("id") ON UPDATE CASCADE ON DELETE RESTRICT;

ALTER TABLE "product_review" ADD CONSTRAINT "fk_product_review_model" FOREIGN KEY ("model_id") REFERENCES "model" ("id") ON UPDATE CASCADE ON DELETE CASCADE;

ALTER TABLE "product_review" ADD CONSTRAINT "fk_product_review_reviewer" FOREIGN KEY ("reviewer_id") REFERENCES "users" ("id") ON UPDATE CASCADE ON DELETE RESTRICT;

ALTER TABLE "supplier" ADD CONSTRAINT "fk_supplier_company" FOREIGN KEY ("company_id") REFERENCES "company" ("id") ON UPDATE CASCADE ON DELETE CASCADE;

ALTER TABLE "client" ADD CONSTRAINT "fk_client_company" FOREIGN KEY ("company_id") REFERENCES "company" ("id") ON UPDATE CASCADE ON DELETE CASCADE;

ALTER TABLE "company_role" ADD CONSTRAINT "fk_company_role_company" FOREIGN KEY ("company_id") REFERENCES "company" ("id") ON UPDATE CASCADE ON DELETE CASCADE;

ALTER TABLE "company_role" ADD CONSTRAINT "fk_company_role_role" FOREIGN KEY ("role_id") REFERENCES "role" ("id") ON UPDATE CASCADE ON DELETE RESTRICT;

ALTER TABLE "user_company" ADD CONSTRAINT "fk_user_company_company" FOREIGN KEY ("company_id") REFERENCES "company" ("id") ON UPDATE CASCADE ON DELETE CASCADE;

ALTER TABLE "user_company" ADD CONSTRAINT "fk_user_company_user" FOREIGN KEY ("user_id") REFERENCES "users" ("id") ON UPDATE CASCADE ON DELETE CASCADE;

ALTER TABLE "user_company" ADD CONSTRAINT "fk_user_company_role" FOREIGN KEY ("role_id") REFERENCES "role" ("id") ON UPDATE CASCADE ON DELETE RESTRICT;

ALTER TABLE "role_permission" ADD CONSTRAINT "fk_role_permission_role" FOREIGN KEY ("role_id") REFERENCES "role" ("id") ON UPDATE CASCADE ON DELETE CASCADE;

ALTER TABLE "role_permission" ADD CONSTRAINT "fk_role_permission_permission" FOREIGN KEY ("permission_id") REFERENCES "permission" ("id") ON UPDATE CASCADE ON DELETE CASCADE;

ALTER TABLE "subscription" ADD CONSTRAINT "fk_subscription_supplier" FOREIGN KEY ("supplier_id") REFERENCES "supplier" ("id") ON UPDATE CASCADE ON DELETE CASCADE;

ALTER TABLE "subscription" ADD CONSTRAINT "fk_subscription_plan" FOREIGN KEY ("plan_id") REFERENCES "subscription_plan" ("id") ON UPDATE CASCADE ON DELETE RESTRICT;

ALTER TABLE "billing" ADD CONSTRAINT "fk_billing_subscription" FOREIGN KEY ("subscription_id") REFERENCES "subscription" ("id") ON UPDATE CASCADE ON DELETE CASCADE;

ALTER TABLE "stock" ADD CONSTRAINT "fk_stock_supplier" FOREIGN KEY ("supplier_id") REFERENCES "supplier" ("id") ON UPDATE CASCADE ON DELETE CASCADE;

ALTER TABLE "stock" ADD CONSTRAINT "fk_stock_model" FOREIGN KEY ("model_id") REFERENCES "model" ("id") ON UPDATE CASCADE ON DELETE RESTRICT;

ALTER TABLE "offer" ADD CONSTRAINT "fk_offer_supplier" FOREIGN KEY ("supplier_id") REFERENCES "supplier" ("id") ON UPDATE CASCADE ON DELETE CASCADE;

ALTER TABLE "offer" ADD CONSTRAINT "fk_offer_model" FOREIGN KEY ("model_id") REFERENCES "model" ("id") ON UPDATE CASCADE ON DELETE RESTRICT;

ALTER TABLE "local_unit" ADD CONSTRAINT "fk_local_unit_client" FOREIGN KEY ("client_id") REFERENCES "client" ("id") ON UPDATE CASCADE ON DELETE CASCADE;

ALTER TABLE "local_unit" ADD CONSTRAINT "fk_local_unit_address" FOREIGN KEY ("address_id") REFERENCES "address" ("id") ON UPDATE CASCADE ON DELETE RESTRICT;

ALTER TABLE "unit_report" ADD CONSTRAINT "fk_unit_report_local_unit" FOREIGN KEY ("local_unit_id") REFERENCES "local_unit" ("id") ON UPDATE CASCADE ON DELETE CASCADE;

ALTER TABLE "proposal" ADD CONSTRAINT "fk_proposal_client" FOREIGN KEY ("client_id") REFERENCES "client" ("id") ON UPDATE CASCADE ON DELETE CASCADE;

ALTER TABLE "proposal_item" ADD CONSTRAINT "fk_proposal_item_proposal" FOREIGN KEY ("proposal_id") REFERENCES "proposal" ("id") ON UPDATE CASCADE ON DELETE CASCADE;

ALTER TABLE "proposal_item" ADD CONSTRAINT "fk_proposal_item_offer" FOREIGN KEY ("offer_id") REFERENCES "offer" ("id") ON UPDATE CASCADE ON DELETE RESTRICT;

ALTER TABLE "proposal_unit" ADD CONSTRAINT "fk_proposal_unit_proposal_item" FOREIGN KEY ("proposal_item_id") REFERENCES "proposal_item" ("id") ON UPDATE CASCADE ON DELETE CASCADE;

ALTER TABLE "proposal_unit" ADD CONSTRAINT "fk_proposal_unit_local_unit" FOREIGN KEY ("local_unit_id") REFERENCES "local_unit" ("id") ON UPDATE CASCADE ON DELETE RESTRICT;

ALTER TABLE "professional_affiliation" ADD CONSTRAINT "fk_professional_affiliation_company" FOREIGN KEY ("company_id") REFERENCES "company" ("id") ON UPDATE CASCADE ON DELETE CASCADE;

ALTER TABLE "professional_affiliation" ADD CONSTRAINT "fk_professional_affiliation_professional" FOREIGN KEY ("professional_id") REFERENCES "professional" ("id") ON UPDATE CASCADE ON DELETE CASCADE;

ALTER TABLE "professional_registration" ADD CONSTRAINT "fk_professional_registration_professional" FOREIGN KEY ("professional_id") REFERENCES "professional" ("id") ON UPDATE CASCADE ON DELETE CASCADE;

ALTER TABLE "professional_registration" ADD CONSTRAINT "fk_professional_registration_profession" FOREIGN KEY ("profession_id") REFERENCES "profession" ("id") ON UPDATE CASCADE ON DELETE RESTRICT;

ALTER TABLE "certification" ADD CONSTRAINT "fk_certification_professional" FOREIGN KEY ("professional_id") REFERENCES "professional" ("id") ON UPDATE CASCADE ON DELETE CASCADE;

ALTER TABLE "technical_project" ADD CONSTRAINT "fk_technical_project_client" FOREIGN KEY ("client_id") REFERENCES "client" ("id") ON UPDATE CASCADE ON DELETE CASCADE;

ALTER TABLE "technical_project" ADD CONSTRAINT "fk_technical_project_local_unit" FOREIGN KEY ("local_unit_id") REFERENCES "local_unit" ("id") ON UPDATE CASCADE ON DELETE RESTRICT;

ALTER TABLE "technical_service" ADD CONSTRAINT "fk_technical_service_project" FOREIGN KEY ("technical_project_id") REFERENCES "technical_project" ("id") ON UPDATE CASCADE ON DELETE CASCADE;

ALTER TABLE "service_executor" ADD CONSTRAINT "fk_service_executor_service" FOREIGN KEY ("service_id") REFERENCES "technical_service" ("id") ON UPDATE CASCADE ON DELETE CASCADE;

ALTER TABLE "service_executor" ADD CONSTRAINT "fk_service_executor_affiliation" FOREIGN KEY ("professional_affiliation_id") REFERENCES "professional_affiliation" ("id") ON UPDATE CASCADE ON DELETE RESTRICT;

ALTER TABLE "service_contract" ADD CONSTRAINT "fk_service_contract_service" FOREIGN KEY ("service_id") REFERENCES "technical_service" ("id") ON UPDATE CASCADE ON DELETE CASCADE;

ALTER TABLE "audit_log" ADD CONSTRAINT "fk_audit_log_user" FOREIGN KEY ("user_id") REFERENCES "users" ("id") ON UPDATE CASCADE ON DELETE SET NULL;