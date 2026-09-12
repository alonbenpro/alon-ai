"""Initial L02 provider governance, frozen SQL snapshot."""

from alembic import op

revision = "20260912_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        "\nCREATE TABLE gov_authorities (\n\taccount VARCHAR NOT NULL, \n\tcapability VARCHAR NOT NULL, \n\tenabled BOOLEAN DEFAULT 'true' NOT NULL, \n\tpolicy_id UUID, \n\twindow_start TIMESTAMP WITH TIME ZONE, \n\tquota_used INTEGER DEFAULT '0' NOT NULL, \n\tactive INTEGER DEFAULT '0' NOT NULL, \n\tfailures INTEGER DEFAULT '0' NOT NULL, \n\tfailure_start TIMESTAMP WITH TIME ZONE, \n\topen_until TIMESTAMP WITH TIME ZONE, \n\tprobe_id UUID, \n\tPRIMARY KEY (account, capability), \n\tUNIQUE (account, capability), \n\tCHECK (capability IN ('OPENAI_GENERATE','BRAVE_WEB_COVERAGE','BRAVE_LOCAL_DISCOVERY','BRAVE_COMPANY_DISCOVERY','FIRECRAWL_MAP','FIRECRAWL_PAGE_CAPTURE','FIRECRAWL_PDF_CAPTURE','FIRECRAWL_JS_RETRIEVAL','HUNTER_DOMAIN_SEARCH','HUNTER_EMAIL_FINDER','HUNTER_COMPANY_ENRICHMENT','HUNTER_PERSON_ENRICHMENT','HUNTER_EMAIL_VERIFICATION','GMAIL_READ','GMAIL_SEND','GOOGLE_CALENDAR_READ','GOOGLE_CALENDAR_WRITE')), \n\tCHECK (account ~ '^[A-Za-z0-9_-]{1,100}$'), \n\tCHECK (quota_used>=0 AND active>=0 AND failures>=0)\n)\n\n"
    )
    op.execute(
        "\nCREATE TABLE gov_evidence (\n\tid UUID NOT NULL, \n\tkind VARCHAR NOT NULL, \n\tmode VARCHAR NOT NULL, \n\tregistered_by UUID NOT NULL, \n\tregistered_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tcall_id UUID, \n\tPRIMARY KEY (id), \n\tCHECK (kind IN ('PRICE','FX','GRANT','GRANT_EVENT','CONTROL','RECONCILIATION','INVOICE','PROVIDER_RESULT')), \n\tCHECK (mode IN ('SYNTHETIC','TRUSTED_REFERENCE')), \n\tCHECK ((kind IN ('RECONCILIATION','INVOICE','PROVIDER_RESULT') AND call_id IS NOT NULL) OR (kind NOT IN ('RECONCILIATION','INVOICE','PROVIDER_RESULT') AND call_id IS NULL))\n)\n\n"
    )
    op.execute(
        "\nCREATE TABLE gov_experiments (\n\tid UUID NOT NULL, \n\tenabled BOOLEAN DEFAULT 'true' NOT NULL, \n\tPRIMARY KEY (id)\n)\n\n"
    )
    op.execute(
        "\nCREATE TABLE gov_fx (\n\tid UUID NOT NULL, \n\tcurrency VARCHAR(3) NOT NULL, \n\tquote_currency VARCHAR(3) NOT NULL, \n\trate NUMERIC NOT NULL, \n\teffective_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\texpires_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tevidence_id UUID NOT NULL, \n\trounding_version VARCHAR NOT NULL, \n\tPRIMARY KEY (id), \n\tCHECK (effective_at < expires_at), \n\tCHECK (rate > 0 AND rate < 1000000000000000000000000 AND scale(rate) <= 12), \n\tCHECK (currency ~ '^[A-Z]{3}$' AND quote_currency='ILS'), \n\tCHECK (currency <> 'ILS' OR rate=1), \n\tCONSTRAINT fk_gov_fx_evidence FOREIGN KEY(evidence_id) REFERENCES gov_evidence (id), \n\tCHECK (currency IN ('USD','ILS'))\n)\n\n"
    )
    op.execute(
        "\nCREATE TABLE gov_grants (\n\tid UUID NOT NULL, \n\tversion INTEGER NOT NULL, \n\taccount VARCHAR NOT NULL, \n\tcapability VARCHAR NOT NULL, \n\teffective_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\texpires_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tdata JSONB NOT NULL, \n\tevidence_id UUID NOT NULL, \n\tPRIMARY KEY (id, version), \n\tCHECK (effective_at < expires_at), \n\tCHECK (version > 0), \n\tFOREIGN KEY(account, capability) REFERENCES gov_authorities (account, capability), \n\tCHECK (data->>'grant_id'=id::text AND (data->>'version')::integer=version AND data->>'account_handle'=account AND data->>'capability'=capability AND (data->>'effective_at')::timestamptz=effective_at AND (data->>'expires_at')::timestamptz=expires_at), \n\tCONSTRAINT fk_gov_grants_evidence FOREIGN KEY(evidence_id) REFERENCES gov_evidence (id)\n)\n\n"
    )
    op.execute(
        "\nCREATE TABLE gov_policies (\n\tid UUID NOT NULL, \n\taccount VARCHAR NOT NULL, \n\tcapability VARCHAR NOT NULL, \n\tdata JSONB NOT NULL, \n\tevidence_id UUID NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(account, capability) REFERENCES gov_authorities (account, capability), \n\tUNIQUE (id, account, capability), \n\tCONSTRAINT fk_gov_policies_evidence FOREIGN KEY(evidence_id) REFERENCES gov_evidence (id)\n)\n\n"
    )
    op.execute(
        "\nCREATE TABLE gov_prices (\n\tid UUID NOT NULL, \n\tcapability VARCHAR NOT NULL, \n\tcomponent VARCHAR NOT NULL, \n\tcurrency VARCHAR(3) NOT NULL, \n\tunit_price NUMERIC NOT NULL, \n\tunit_quantity NUMERIC NOT NULL, \n\tcurrency_quantum NUMERIC NOT NULL, \n\teffective_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\texpires_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tevidence_id UUID NOT NULL, \n\trounding_version VARCHAR NOT NULL, \n\tmodel_identifier VARCHAR, \n\tPRIMARY KEY (id), \n\tCHECK (effective_at < expires_at), \n\tCHECK (unit_price >= 0 AND unit_price < 1000000000000000000000000 AND scale(unit_price) <= 12), \n\tCHECK (unit_quantity > 0 AND unit_quantity < 1000000000000000000000000 AND scale(unit_quantity) <= 12), \n\tCHECK (capability IN ('OPENAI_GENERATE','BRAVE_WEB_COVERAGE','BRAVE_LOCAL_DISCOVERY','BRAVE_COMPANY_DISCOVERY','FIRECRAWL_MAP','FIRECRAWL_PAGE_CAPTURE','FIRECRAWL_PDF_CAPTURE','FIRECRAWL_JS_RETRIEVAL','HUNTER_DOMAIN_SEARCH','HUNTER_EMAIL_FINDER','HUNTER_COMPANY_ENRICHMENT','HUNTER_PERSON_ENRICHMENT','HUNTER_EMAIL_VERIFICATION','GMAIL_READ','GMAIL_SEND','GOOGLE_CALENDAR_READ','GOOGLE_CALENDAR_WRITE')), \n\tCHECK (currency ~ '^[A-Z]{3}$'), \n\tCHECK (currency_quantum IN (1,.1,.01,.001,.0001)), \n\tCONSTRAINT fk_gov_prices_evidence FOREIGN KEY(evidence_id) REFERENCES gov_evidence (id), \n\tCHECK (currency IN ('USD','ILS') AND currency_quantum=.01), \n\tCHECK ((capability='OPENAI_GENERATE' AND model_identifier IS NOT NULL) OR (capability<>'OPENAI_GENERATE' AND model_identifier IS NULL))\n)\n\n"
    )
    op.execute(
        "\nCREATE TABLE gov_workflows (\n\tid UUID NOT NULL, \n\texperiment_id UUID NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(experiment_id) REFERENCES gov_experiments (id), \n\tUNIQUE (id, experiment_id)\n)\n\n"
    )
    op.execute(
        "\nCREATE TABLE gov_agents (\n\tid UUID NOT NULL, \n\tworkflow_id UUID NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(workflow_id) REFERENCES gov_workflows (id), \n\tUNIQUE (id, workflow_id)\n)\n\n"
    )
    op.execute(
        "\nCREATE TABLE gov_configs (\n\tid UUID NOT NULL, \n\tworkflow_id UUID NOT NULL, \n\tversion UUID NOT NULL, \n\taccount VARCHAR NOT NULL, \n\tcapability VARCHAR NOT NULL, \n\tfx_id UUID NOT NULL, \n\tdata JSONB NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(workflow_id) REFERENCES gov_workflows (id), \n\tFOREIGN KEY(fx_id) REFERENCES gov_fx (id), \n\tFOREIGN KEY(account, capability) REFERENCES gov_authorities (account, capability), \n\tUNIQUE (id, workflow_id, version), \n\tCHECK (data->>'id'=id::text AND data->>'workflow_id'=workflow_id::text AND data->>'version'=version::text AND data->>'fx_id'=fx_id::text AND data->'intended_use'->>'account_handle'=account AND data->'intended_use'->>'capability'=capability)\n)\n\n"
    )
    op.execute(
        "\nCREATE TABLE gov_grant_events (\n\tid UUID NOT NULL, \n\tgrant_id UUID NOT NULL, \n\tgrant_version INTEGER NOT NULL, \n\tdata JSONB NOT NULL, \n\tevidence_id UUID NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(grant_id, grant_version) REFERENCES gov_grants (id, version), \n\tCHECK (((data->>'event_id')::uuid=id AND (data->>'grant_id')::uuid=grant_id AND (data->>'grant_version')::integer=grant_version) IS TRUE), \n\tCONSTRAINT fk_gov_grant_events_evidence FOREIGN KEY(evidence_id) REFERENCES gov_evidence (id)\n)\n\n"
    )
    op.execute(
        "\nCREATE TABLE gov_config_prices (\n\tconfig_id UUID NOT NULL, \n\tprice_id UUID NOT NULL, \n\tmax_quantity NUMERIC NOT NULL, \n\tPRIMARY KEY (config_id, price_id), \n\tFOREIGN KEY(config_id) REFERENCES gov_configs (id), \n\tFOREIGN KEY(price_id) REFERENCES gov_prices (id), \n\tCHECK (max_quantity > 0 AND max_quantity < 1000000000000000000000000 AND scale(max_quantity) <= 12)\n)\n\n"
    )
    op.execute(
        "\nCREATE TABLE gov_operations (\n\tid UUID NOT NULL, \n\texperiment_id UUID NOT NULL, \n\tworkflow_id UUID NOT NULL, \n\tkind VARCHAR NOT NULL, \n\tagent_id UUID, \n\tservice VARCHAR, \n\tconfig_version UUID NOT NULL, \n\tgate_kind VARCHAR NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(workflow_id, experiment_id) REFERENCES gov_workflows (id, experiment_id), \n\tFOREIGN KEY(agent_id, workflow_id) REFERENCES gov_agents (id, workflow_id), \n\tUNIQUE (id, workflow_id, experiment_id, config_version), \n\tUNIQUE (id, workflow_id, experiment_id), \n\tCHECK (kind IN ('RESEARCH','DISCOVERY','ENRICHMENT','VERIFICATION','SYSTEM')), \n\tCHECK (gate_kind IN ('NONE','SUPPLY','CONTACT')), \n\tCHECK ((agent_id IS NOT NULL AND service IS NULL) OR (agent_id IS NULL AND service IN ('provider-executor','contact-resolution','campaign-supply','send-gateway','calendar-gateway'))), \n\tCHECK (agent_id IS NOT NULL OR service IS NOT NULL)\n)\n\n"
    )
    op.execute(
        "\nCREATE TABLE gov_budget_accounts (\n\tid UUID NOT NULL, \n\tscope VARCHAR NOT NULL, \n\texperiment_id UUID, \n\tworkflow_id UUID, \n\toperation_id UUID, \n\tprovider VARCHAR, \n\tcurrency VARCHAR(3) NOT NULL, \n\teffective_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\texpires_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\t\"limit\" NUMERIC NOT NULL, \n\treserved NUMERIC DEFAULT '0' NOT NULL, \n\taccrued NUMERIC DEFAULT '0' NOT NULL, \n\tfrozen BOOLEAN DEFAULT 'false' NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(experiment_id) REFERENCES gov_experiments (id), \n\tFOREIGN KEY(workflow_id, experiment_id) REFERENCES gov_workflows (id, experiment_id), \n\tFOREIGN KEY(operation_id, workflow_id, experiment_id) REFERENCES gov_operations (id, workflow_id, experiment_id), \n\tCHECK ((scope='GLOBAL' AND experiment_id IS NULL AND workflow_id IS NULL AND operation_id IS NULL AND provider IS NULL) OR (scope='PROVIDER' AND experiment_id IS NULL AND workflow_id IS NULL AND operation_id IS NULL AND provider IS NOT NULL) OR (scope='EXPERIMENT' AND experiment_id IS NOT NULL AND workflow_id IS NULL AND operation_id IS NULL AND provider IS NULL) OR (scope='EXPERIMENT_PROVIDER' AND experiment_id IS NOT NULL AND workflow_id IS NULL AND operation_id IS NULL AND provider IS NOT NULL) OR (scope='WORKFLOW' AND experiment_id IS NOT NULL AND workflow_id IS NOT NULL AND operation_id IS NULL AND provider IS NULL) OR (scope='OPERATION' AND experiment_id IS NOT NULL AND workflow_id IS NOT NULL AND operation_id IS NOT NULL AND provider IS NULL)), \n\tCHECK (currency ~ '^[A-Z]{3}$'), \n\tCHECK (provider IN ('OPENAI','BRAVE','FIRECRAWL','HUNTER','GMAIL','GOOGLE_CALENDAR')), \n\tCHECK (effective_at < expires_at), \n\tCHECK (\"limit\" >= 0 AND \"limit\" < 1000000000000000000000000 AND scale(\"limit\") <= 24), \n\tCHECK (reserved >= 0 AND reserved < 1000000000000000000000000 AND scale(reserved) <= 24), \n\tCHECK (accrued >= 0 AND accrued < 1000000000000000000000000 AND scale(accrued) <= 24), \n\tUNIQUE NULLS NOT DISTINCT (scope, experiment_id, workflow_id, operation_id, provider, currency, effective_at)\n)\n\n"
    )
    op.execute(
        "\nCREATE TABLE gov_calls (\n\tid UUID NOT NULL, \n\tidempotency_key UUID NOT NULL, \n\tlogical_operation_id UUID NOT NULL, \n\texperiment_id UUID NOT NULL, \n\tworkflow_id UUID NOT NULL, \n\toperation_id UUID NOT NULL, \n\tconfig_version UUID NOT NULL, \n\tconfig_id UUID NOT NULL, \n\tattribution JSONB NOT NULL, \n\trequest JSONB NOT NULL, \n\tgrant_id UUID NOT NULL, \n\tgrant_version INTEGER NOT NULL, \n\tcurrency VARCHAR(3) NOT NULL, \n\treserved NUMERIC NOT NULL, \n\treserved_ils NUMERIC NOT NULL, \n\taccrued NUMERIC DEFAULT '0' NOT NULL, \n\taccrued_ils NUMERIC DEFAULT '0' NOT NULL, \n\tstate VARCHAR NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tdispatch_at TIMESTAMP WITH TIME ZONE, \n\tlease_until TIMESTAMP WITH TIME ZONE, \n\ttoken UUID, \n\tfinished_at TIMESTAMP WITH TIME ZONE, \n\tpolicy_id UUID, \n\terror VARCHAR, \n\tresult_metadata JSONB, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(operation_id, workflow_id, experiment_id, config_version) REFERENCES gov_operations (id, workflow_id, experiment_id, config_version), \n\tFOREIGN KEY(config_id, workflow_id, config_version) REFERENCES gov_configs (id, workflow_id, version), \n\tFOREIGN KEY(grant_id, grant_version) REFERENCES gov_grants (id, version), \n\tCHECK (state IN ('RESERVED','DISPATCHED','RECONCILING','FINAL','RELEASED')), \n\tCHECK ((state IN ('RESERVED','RELEASED') AND token IS NULL AND dispatch_at IS NULL AND lease_until IS NULL) OR (state IN ('DISPATCHED','RECONCILING','FINAL') AND token IS NOT NULL AND dispatch_at IS NOT NULL AND lease_until IS NOT NULL)), \n\tCHECK (reserved >= 0 AND reserved < 1000000000000000000000000 AND scale(reserved) <= 24), \n\tCHECK (reserved_ils >= 0 AND reserved_ils < 1000000000000000000000000 AND scale(reserved_ils) <= 24), \n\tCHECK (accrued >= 0 AND accrued < 1000000000000000000000000 AND scale(accrued) <= 24), \n\tCHECK (accrued_ils >= 0 AND accrued_ils < 1000000000000000000000000 AND scale(accrued_ils) <= 24), \n\tUNIQUE (idempotency_key), \n\tUNIQUE (logical_operation_id), \n\tCONSTRAINT fk_gov_dispatch_policy FOREIGN KEY(policy_id) REFERENCES gov_policies (id), \n\tUNIQUE (id, grant_id, grant_version)\n)\n\n"
    )
    op.execute(
        "\nCREATE TABLE gov_allocations (\n\tcall_id UUID NOT NULL, \n\taccount_id UUID NOT NULL, \n\tamount NUMERIC NOT NULL, \n\tPRIMARY KEY (call_id, account_id), \n\tFOREIGN KEY(call_id) REFERENCES gov_calls (id), \n\tFOREIGN KEY(account_id) REFERENCES gov_budget_accounts (id), \n\tCHECK (amount >= 0 AND amount < 1000000000000000000000000 AND scale(amount) <= 24)\n)\n\n"
    )
    op.execute(
        "\nCREATE TABLE gov_audit (\n\tid UUID NOT NULL, \n\tcall_id UUID, \n\texperiment_id UUID, \n\tcorrelation_id UUID, \n\tkind VARCHAR NOT NULL, \n\treason VARCHAR, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(call_id) REFERENCES gov_calls (id)\n)\n\n"
    )
    op.execute(
        "\nCREATE TABLE gov_cash_entries (\n\tid UUID NOT NULL, \n\tcommand_key UUID NOT NULL, \n\tcall_id UUID NOT NULL, \n\tamount NUMERIC NOT NULL, \n\tamount_ils NUMERIC NOT NULL, \n\tevidence_id UUID NOT NULL, \n\tcorrects_id UUID, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(call_id) REFERENCES gov_calls (id), \n\tFOREIGN KEY(corrects_id) REFERENCES gov_cash_entries (id), \n\tCHECK (amount >= 0 AND amount < 1000000000000000000000000 AND scale(amount) <= 24), \n\tCHECK (amount_ils >= 0 AND amount_ils < 1000000000000000000000000 AND scale(amount_ils) <= 24), \n\tUNIQUE (corrects_id), \n\tUNIQUE (command_key), \n\tUNIQUE (id, call_id), \n\tCONSTRAINT fk_gov_cash_correction_call FOREIGN KEY(corrects_id, call_id) REFERENCES gov_cash_entries (id, call_id), \n\tCONSTRAINT fk_gov_cash_entries_evidence FOREIGN KEY(evidence_id) REFERENCES gov_evidence (id)\n)\n\n"
    )
    op.execute(
        "\nCREATE TABLE gov_retained (\n\tid UUID NOT NULL, \n\tcall_id UUID NOT NULL, \n\tgrant_id UUID NOT NULL, \n\tgrant_version INTEGER NOT NULL, \n\tfield VARCHAR NOT NULL, \n\tvalues JSONB NOT NULL, \n\texpires_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tretention_rule_id UUID NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(call_id) REFERENCES gov_calls (id), \n\tFOREIGN KEY(grant_id, grant_version) REFERENCES gov_grants (id, version), \n\tUNIQUE (call_id, field), \n\tCHECK (field IN ('URL','TITLE','TEXT','EMAIL','COMPANY','RANKING','MESSAGE','EVENT')), \n\tCONSTRAINT fk_gov_retained_call_grant FOREIGN KEY(call_id, grant_id, grant_version) REFERENCES gov_calls (id, grant_id, grant_version)\n)\n\n"
    )
    op.execute(
        "\nCREATE TABLE gov_settlements (\n\tid UUID NOT NULL, \n\tcall_id UUID NOT NULL, \n\tcommand_key UUID NOT NULL, \n\tkind VARCHAR NOT NULL, \n\tcost NUMERIC NOT NULL, \n\tcost_ils NUMERIC NOT NULL, \n\tprevious_cost NUMERIC NOT NULL, \n\tprevious_ils NUMERIC NOT NULL, \n\tevidence_id UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(call_id) REFERENCES gov_calls (id), \n\tUNIQUE (call_id, command_key), \n\tCHECK (kind IN ('FINAL','ADJUSTMENT','PROVEN_UNUSED')), \n\tCHECK (cost >= 0 AND cost < 1000000000000000000000000 AND scale(cost) <= 24), \n\tCHECK (cost_ils >= 0 AND cost_ils < 1000000000000000000000000 AND scale(cost_ils) <= 24), \n\tCHECK (previous_cost >= 0 AND previous_cost < 1000000000000000000000000 AND scale(previous_cost) <= 24), \n\tCHECK (previous_ils >= 0 AND previous_ils < 1000000000000000000000000 AND scale(previous_ils) <= 24), \n\tCONSTRAINT fk_gov_settlements_evidence FOREIGN KEY(evidence_id) REFERENCES gov_evidence (id)\n)\n\n"
    )
    op.execute(
        "\nCREATE TABLE gov_usage (\n\tid UUID NOT NULL, \n\tcall_id UUID NOT NULL, \n\tobservation_key UUID NOT NULL, \n\tcomponent VARCHAR NOT NULL, \n\tprice_id UUID NOT NULL, \n\tcurrency VARCHAR(3) NOT NULL, \n\tquantity NUMERIC, \n\tcost NUMERIC, \n\tknowledge VARCHAR NOT NULL, \n\tsupersedes_id UUID, \n\tobserved_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(call_id) REFERENCES gov_calls (id), \n\tFOREIGN KEY(price_id) REFERENCES gov_prices (id), \n\tFOREIGN KEY(supersedes_id, call_id, component) REFERENCES gov_usage (id, call_id, component), \n\tUNIQUE (id, call_id, component), \n\tUNIQUE (call_id, observation_key), \n\tUNIQUE (supersedes_id), \n\tCHECK (cost >= 0 AND cost < 1000000000000000000000000 AND scale(cost) <= 24), \n\tCHECK (quantity >= 0 AND quantity < 1000000000000000000000000 AND scale(quantity) <= 12), \n\tCHECK (knowledge IN ('ESTIMATE','FINAL','UNAVAILABLE')), \n\tCHECK ((knowledge='UNAVAILABLE' AND cost IS NULL) OR (knowledge IN ('ESTIMATE','FINAL') AND cost IS NOT NULL))\n)\n\n"
    )
    op.execute(
        "ALTER TABLE gov_authorities ADD CONSTRAINT fk_gov_current_policy FOREIGN KEY(policy_id, account, capability) REFERENCES gov_policies (id, account, capability)"
    )
    op.execute(
        "ALTER TABLE gov_evidence ADD CONSTRAINT fk_gov_evidence_call FOREIGN KEY(call_id) REFERENCES gov_calls (id)"
    )
    op.execute("CREATE INDEX ix_gov_evidence_call ON gov_evidence (call_id)")
    op.execute("CREATE INDEX ix_gov_fx_evidence ON gov_fx (evidence_id)")
    op.execute(
        "CREATE INDEX ix_gov_grants_current ON gov_grants (account, capability, effective_at, expires_at)"
    )
    op.execute("CREATE INDEX ix_gov_grants_evidence ON gov_grants (evidence_id)")
    op.execute("CREATE INDEX ix_gov_grants_fk_0 ON gov_grants (account, capability)")
    op.execute("CREATE INDEX ix_gov_policies_evidence ON gov_policies (evidence_id)")
    op.execute(
        "CREATE INDEX ix_gov_policies_fk_0 ON gov_policies (account, capability)"
    )
    op.execute("CREATE INDEX ix_gov_prices_evidence ON gov_prices (evidence_id)")
    op.execute("CREATE INDEX ix_gov_workflows_fk_0 ON gov_workflows (experiment_id)")
    op.execute("CREATE INDEX ix_gov_agents_fk_0 ON gov_agents (workflow_id)")
    op.execute("CREATE INDEX ix_gov_configs_fk_0 ON gov_configs (account, capability)")
    op.execute("CREATE INDEX ix_gov_configs_fk_1 ON gov_configs (fx_id)")
    op.execute("CREATE INDEX ix_gov_configs_fk_2 ON gov_configs (workflow_id)")
    op.execute(
        "CREATE INDEX ix_gov_grant_events_evidence ON gov_grant_events (evidence_id)"
    )
    op.execute(
        "CREATE INDEX ix_gov_grant_events_fk_0 ON gov_grant_events (grant_id, grant_version)"
    )
    op.execute(
        "CREATE INDEX ix_gov_config_prices_fk_0 ON gov_config_prices (config_id)"
    )
    op.execute("CREATE INDEX ix_gov_config_prices_fk_1 ON gov_config_prices (price_id)")
    op.execute(
        "CREATE INDEX ix_gov_operations_fk_0 ON gov_operations (agent_id, workflow_id)"
    )
    op.execute(
        "CREATE INDEX ix_gov_operations_fk_1 ON gov_operations (workflow_id, experiment_id)"
    )
    op.execute(
        "CREATE INDEX ix_gov_budget_accounts_fk_0 ON gov_budget_accounts (experiment_id)"
    )
    op.execute(
        "CREATE INDEX ix_gov_budget_accounts_fk_1 ON gov_budget_accounts (operation_id, workflow_id, experiment_id)"
    )
    op.execute(
        "CREATE INDEX ix_gov_budget_accounts_fk_2 ON gov_budget_accounts (workflow_id, experiment_id)"
    )
    op.execute(
        "CREATE INDEX ix_gov_budget_current ON gov_budget_accounts (scope, currency, effective_at)"
    )
    op.execute(
        "CREATE INDEX ix_gov_calls_fk_0 ON gov_calls (config_id, workflow_id, config_version)"
    )
    op.execute("CREATE INDEX ix_gov_calls_fk_1 ON gov_calls (grant_id, grant_version)")
    op.execute(
        "CREATE INDEX ix_gov_calls_fk_2 ON gov_calls (operation_id, workflow_id, experiment_id, config_version)"
    )
    op.execute("CREATE INDEX ix_gov_allocations_fk_0 ON gov_allocations (account_id)")
    op.execute("CREATE INDEX ix_gov_allocations_fk_1 ON gov_allocations (call_id)")
    op.execute("CREATE INDEX ix_gov_audit_fk_0 ON gov_audit (call_id)")
    op.execute(
        "CREATE INDEX ix_gov_cash_entries_evidence ON gov_cash_entries (evidence_id)"
    )
    op.execute("CREATE INDEX ix_gov_cash_entries_fk_0 ON gov_cash_entries (call_id)")
    op.execute(
        "CREATE INDEX ix_gov_cash_entries_fk_1 ON gov_cash_entries (corrects_id)"
    )
    op.execute("CREATE INDEX ix_gov_retained_expiry ON gov_retained (expires_at)")
    op.execute("CREATE INDEX ix_gov_retained_fk_0 ON gov_retained (call_id)")
    op.execute(
        "CREATE INDEX ix_gov_retained_fk_1 ON gov_retained (grant_id, grant_version)"
    )
    op.execute(
        "CREATE INDEX ix_gov_settlements_evidence ON gov_settlements (evidence_id)"
    )
    op.execute("CREATE INDEX ix_gov_settlements_fk_0 ON gov_settlements (call_id)")
    op.execute("CREATE INDEX ix_gov_usage_fk_0 ON gov_usage (call_id)")
    op.execute("CREATE INDEX ix_gov_usage_fk_1 ON gov_usage (price_id)")
    op.execute(
        "CREATE INDEX ix_gov_usage_fk_2 ON gov_usage (supersedes_id, call_id, component)"
    )
    op.execute(
        "CREATE FUNCTION gov_immutable() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'immutable governance fact' USING ERRCODE='23514'; END $$"
    )
    op.execute(
        "CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON gov_workflows FOR EACH ROW EXECUTE FUNCTION gov_immutable()"
    )
    op.execute(
        "CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON gov_agents FOR EACH ROW EXECUTE FUNCTION gov_immutable()"
    )
    op.execute(
        "CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON gov_operations FOR EACH ROW EXECUTE FUNCTION gov_immutable()"
    )
    op.execute(
        "CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON gov_policies FOR EACH ROW EXECUTE FUNCTION gov_immutable()"
    )
    op.execute(
        "CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON gov_grants FOR EACH ROW EXECUTE FUNCTION gov_immutable()"
    )
    op.execute(
        "CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON gov_grant_events FOR EACH ROW EXECUTE FUNCTION gov_immutable()"
    )
    op.execute(
        "CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON gov_prices FOR EACH ROW EXECUTE FUNCTION gov_immutable()"
    )
    op.execute(
        "CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON gov_fx FOR EACH ROW EXECUTE FUNCTION gov_immutable()"
    )
    op.execute(
        "CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON gov_configs FOR EACH ROW EXECUTE FUNCTION gov_immutable()"
    )
    op.execute(
        "CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON gov_config_prices FOR EACH ROW EXECUTE FUNCTION gov_immutable()"
    )
    op.execute(
        "CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON gov_allocations FOR EACH ROW EXECUTE FUNCTION gov_immutable()"
    )
    op.execute(
        "CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON gov_usage FOR EACH ROW EXECUTE FUNCTION gov_immutable()"
    )
    op.execute(
        "CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON gov_settlements FOR EACH ROW EXECUTE FUNCTION gov_immutable()"
    )
    op.execute(
        "CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON gov_cash_entries FOR EACH ROW EXECUTE FUNCTION gov_immutable()"
    )
    op.execute(
        "CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON gov_audit FOR EACH ROW EXECUTE FUNCTION gov_immutable()"
    )
    op.execute(
        "CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON gov_evidence FOR EACH ROW EXECUTE FUNCTION gov_immutable()"
    )
    op.execute(
        "\nCREATE FUNCTION gov_json_object(value jsonb, keys text[]) RETURNS boolean\nLANGUAGE sql IMMUTABLE AS $$\n SELECT COALESCE(jsonb_typeof(value)='object' AND value ?& keys\n   AND value-keys='{}'::jsonb AND value->>'schema_version'='1'\n   AND jsonb_typeof(value->'schema_version')='number',false)\n$$;\nCREATE FUNCTION gov_json_uuid(value jsonb) RETURNS boolean\nLANGUAGE sql IMMUTABLE AS $$\n SELECT COALESCE(jsonb_typeof(value)='string' AND value#>>'{}' ~\n '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',false)\n$$;\nCREATE FUNCTION gov_json_time(value jsonb) RETURNS boolean\nLANGUAGE plpgsql IMMUTABLE AS $$\nBEGIN\n RETURN COALESCE(jsonb_typeof(value)='string' AND value#>>'{}' ~\n   '^[0-9]{4}-[0-9]{2}-[0-9]{2}T.*(Z|[+-][0-9]{2}:[0-9]{2})$'\n   AND isfinite((value#>>'{}')::timestamptz),false);\nEXCEPTION WHEN OTHERS THEN RETURN false;\nEND $$;\nCREATE FUNCTION gov_json_quantity(value jsonb) RETURNS boolean\nLANGUAGE plpgsql IMMUTABLE AS $$\nBEGIN\n IF value='null'::jsonb THEN RETURN true; END IF;\n RETURN COALESCE(jsonb_typeof(value)='string' AND value#>>'{}' ~\n   '^[0-9]+(\\.[0-9]+)?([Ee][+-]?[0-9]+)?$'\n   AND (value#>>'{}')::numeric>=0 AND (value#>>'{}')::numeric<1e24\n   AND scale((value#>>'{}')::numeric)<=12,false);\nEXCEPTION WHEN OTHERS THEN RETURN false;\nEND $$;\nCREATE FUNCTION gov_validate_call_json(item gov_calls) RETURNS void\nLANGUAGE plpgsql AS $$\nDECLARE operation gov_operations; config gov_configs; a jsonb; r jsonb; m jsonb; u jsonb; actor jsonb;\nBEGIN\n SELECT * INTO operation FROM gov_operations WHERE id=item.operation_id;\n SELECT * INTO config FROM gov_configs WHERE id=item.config_id;\n a:=item.attribution; r:=item.request; m:=item.result_metadata;\n IF operation.agent_id IS NOT NULL THEN\n  actor:=jsonb_build_object('schema_version',1,'kind','agent','agent_run_id',operation.agent_id::text);\n ELSE\n  actor:=jsonb_build_object('schema_version',1,'kind','system','service',operation.service);\n END IF;\n IF NOT gov_json_object(a,ARRAY['schema_version','experiment_id','workflow_run_id','operation_run_id',\n   'operation_run_kind','actor','correlation_id','logical_operation_id','config_version','deadline'])\n   OR NOT (a->>'experiment_id'=item.experiment_id::text AND a->>'workflow_run_id'=item.workflow_id::text\n    AND a->>'operation_run_id'=item.operation_id::text AND a->>'config_version'=item.config_version::text\n    AND a->>'logical_operation_id'=item.logical_operation_id::text AND a->>'operation_run_kind'=operation.kind\n    AND a->'actor'=actor AND a->'actor'->>'schema_version'='1') IS TRUE\n   OR NOT gov_json_uuid(a->'correlation_id') OR NOT gov_json_time(a->'deadline') THEN\n  RAISE EXCEPTION 'invalid governance attribution' USING ERRCODE='23514';\n END IF;\n IF NOT gov_json_object(r,ARRAY['schema_version','config_ref','requested_count'])\n   OR NOT (r->>'config_ref'=item.config_id::text AND jsonb_typeof(r->'requested_count')='number'\n    AND r->>'requested_count' ~ '^[1-9][0-9]*$' AND (r->>'requested_count')::integer BETWEEN 1 AND 100\n    AND r->'requested_count'=config.data->'requested_count') IS TRUE THEN\n  RAISE EXCEPTION 'invalid governance request metadata' USING ERRCODE='23514';\n END IF;\n IF m IS NULL THEN RETURN; END IF;\n IF NOT gov_json_object(m,ARRAY['schema_version','capability','external_request_id','started_at','finished_at','status','error_code','usage'])\n   OR NOT (m->>'capability'=config.capability AND item.state IN ('DISPATCHED','RECONCILING','FINAL')\n    AND item.token IS NOT NULL AND item.finished_at IS NOT NULL\n    AND m->>'status' IN ('SUCCEEDED','REFUSED','FAILED')\n    AND ((m->>'status'='SUCCEEDED' AND m->'error_code'='null'::jsonb)\n     OR (m->>'status'<>'SUCCEEDED' AND m->>'error_code' IN ('DENIED','CAPABILITY_MISMATCH','TIMEOUT','UNAVAILABLE','MALFORMED_RESPONSE','REFUSED','WRITE_AUTHORITY_REQUIRED')))\n    AND (m->'external_request_id'='null'::jsonb OR (jsonb_typeof(m->'external_request_id')='string' AND m->>'external_request_id' ~ '^[A-Za-z0-9_-]{1,100}$'))\n    AND jsonb_typeof(m->'usage')='array') IS TRUE\n   OR NOT gov_json_time(m->'started_at') OR NOT gov_json_time(m->'finished_at') THEN\n  RAISE EXCEPTION 'invalid governance result metadata' USING ERRCODE='23514';\n END IF;\n IF (m->>'finished_at')::timestamptz < (m->>'started_at')::timestamptz THEN\n  RAISE EXCEPTION 'invalid governance result timing' USING ERRCODE='23514';\n END IF;\n FOR u IN SELECT value FROM jsonb_array_elements(m->'usage') LOOP\n  IF NOT gov_json_object(u,ARRAY['schema_version','component','quantity','currency','cost','knowledge','observation_key'])\n    OR NOT gov_json_uuid(u->'observation_key') OR NOT gov_json_quantity(u->'quantity') OR NOT gov_json_quantity(u->'cost')\n    OR NOT (u->>'currency'=item.currency AND u->>'knowledge' IN ('ESTIMATE','FINAL','UNAVAILABLE')\n      AND ((u->>'knowledge'='UNAVAILABLE' AND u->'cost'='null'::jsonb)\n       OR (u->>'knowledge'<>'UNAVAILABLE' AND u->'cost'<>'null'::jsonb))) IS TRUE THEN\n   RAISE EXCEPTION 'invalid governance usage metadata' USING ERRCODE='23514';\n  END IF;\n  IF NOT EXISTS(SELECT 1 FROM gov_usage existing WHERE existing.call_id=item.id\n    AND existing.observation_key::text=u->>'observation_key' AND existing.component=u->>'component'\n    AND existing.currency=u->>'currency' AND existing.knowledge=u->>'knowledge'\n    AND existing.quantity IS NOT DISTINCT FROM (u->>'quantity')::numeric\n    AND existing.cost IS NOT DISTINCT FROM (u->>'cost')::numeric) THEN\n   RAISE EXCEPTION 'governance usage metadata binding' USING ERRCODE='23514';\n  END IF;\n END LOOP;\nEND $$;\n"
    )
    op.execute(
        "CREATE FUNCTION gov_binding_guard() RETURNS trigger LANGUAGE plpgsql AS $$\nDECLARE cfg gov_configs; p gov_prices; g gov_grants; ca gov_calls; a gov_budget_accounts; f gov_fx;\nBEGIN\n IF TG_TABLE_NAME='gov_config_prices' THEN\n  SELECT * INTO cfg FROM gov_configs WHERE id=NEW.config_id;\n  SELECT * INTO p FROM gov_prices WHERE id=NEW.price_id;\n  SELECT * INTO f FROM gov_fx WHERE id=cfg.fx_id;\n  IF cfg.capability IS DISTINCT FROM p.capability OR p.currency IS DISTINCT FROM f.currency OR p.model_identifier IS DISTINCT FROM (cfg.data->>'model_identifier') THEN\n   RAISE EXCEPTION 'governance price binding' USING ERRCODE='23514';\n  END IF;\n ELSIF TG_TABLE_NAME='gov_calls' THEN\n  PERFORM gov_validate_call_json(NEW);\n  SELECT * INTO cfg FROM gov_configs WHERE id=NEW.config_id;\n  SELECT * INTO g FROM gov_grants WHERE id=NEW.grant_id AND version=NEW.grant_version;\n  SELECT * INTO f FROM gov_fx WHERE id=cfg.fx_id;\n  IF cfg.capability IS DISTINCT FROM g.capability OR cfg.account IS DISTINCT FROM g.account OR NEW.currency IS DISTINCT FROM f.currency THEN\n   RAISE EXCEPTION 'governance call binding' USING ERRCODE='23514';\n  END IF;\n  IF TG_OP='UPDATE' AND (to_jsonb(NEW)-ARRAY['state','accrued','accrued_ils','dispatch_at','lease_until','token','finished_at','policy_id','error','result_metadata']) IS DISTINCT FROM\n    (to_jsonb(OLD)-ARRAY['state','accrued','accrued_ils','dispatch_at','lease_until','token','finished_at','policy_id','error','result_metadata']) THEN\n   RAISE EXCEPTION 'immutable governance intent' USING ERRCODE='23514';\n  END IF;\n  IF TG_OP='UPDATE' AND NOT (NEW.state=OLD.state OR\n      (OLD.state='RESERVED' AND NEW.state IN ('DISPATCHED','RELEASED')) OR\n      (OLD.state='DISPATCHED' AND NEW.state IN ('RECONCILING','FINAL')) OR\n      (OLD.state='RECONCILING' AND NEW.state='FINAL')) THEN\n   RAISE EXCEPTION 'governance state transition' USING ERRCODE='23514';\n  END IF;\n ELSIF TG_TABLE_NAME='gov_usage' THEN\n  SELECT * INTO ca FROM gov_calls WHERE id=NEW.call_id;\n  SELECT * INTO p FROM gov_prices WHERE id=NEW.price_id;\n  IF p.component IS DISTINCT FROM NEW.component OR p.currency IS DISTINCT FROM NEW.currency OR NOT EXISTS\n     (SELECT 1 FROM gov_config_prices WHERE config_id=ca.config_id AND price_id=NEW.price_id) THEN\n   RAISE EXCEPTION 'governance usage binding' USING ERRCODE='23514';\n  END IF;\n ELSIF TG_TABLE_NAME='gov_allocations' THEN\n  SELECT * INTO ca FROM gov_calls WHERE id=NEW.call_id;\n  SELECT * INTO a FROM gov_budget_accounts WHERE id=NEW.account_id;\n  SELECT * INTO cfg FROM gov_configs WHERE id=ca.config_id;\n  IF (a.experiment_id IS NOT NULL AND a.experiment_id<>ca.experiment_id) OR\n     (a.workflow_id IS NOT NULL AND a.workflow_id<>ca.workflow_id) OR\n     (a.operation_id IS NOT NULL AND a.operation_id<>ca.operation_id) OR\n     (a.provider IS NOT NULL AND a.provider<>cfg.data->'intended_use'->>'provider') OR\n     a.currency NOT IN (ca.currency,'ILS') OR NEW.amount <> (CASE WHEN a.currency='ILS' THEN ca.reserved_ils ELSE ca.reserved END) THEN\n   RAISE EXCEPTION 'governance allocation binding' USING ERRCODE='23514';\n  END IF;\n END IF;\n RETURN NEW;\nEND $$;\n"
    )
    op.execute(
        "CREATE FUNCTION gov_proof_guard() RETURNS trigger LANGUAGE plpgsql AS $$\nDECLARE proof gov_evidence; required_kind text;\nBEGIN\n SELECT * INTO proof FROM gov_evidence WHERE id=NEW.evidence_id;\n required_kind := CASE TG_TABLE_NAME WHEN 'gov_prices' THEN 'PRICE' WHEN 'gov_fx' THEN 'FX' WHEN 'gov_grants' THEN 'GRANT'\n   WHEN 'gov_grant_events' THEN 'GRANT_EVENT' WHEN 'gov_policies' THEN 'CONTROL' WHEN 'gov_cash_entries' THEN 'INVOICE' ELSE 'RECONCILIATION' END;\n IF proof.id IS NULL OR NOT (proof.kind=required_kind OR (TG_TABLE_NAME='gov_settlements' AND proof.kind='PROVIDER_RESULT')) THEN\n  RAISE EXCEPTION 'governance proof kind' USING ERRCODE='23514';\n END IF;\n IF TG_TABLE_NAME IN ('gov_settlements','gov_cash_entries') THEN\n  IF proof.call_id IS DISTINCT FROM NEW.call_id THEN\n   RAISE EXCEPTION 'governance proof scope' USING ERRCODE='23514';\n  END IF;\n END IF;\n RETURN NEW;\nEND $$;\n"
    )
    op.execute(
        "CREATE TRIGGER proof_binding BEFORE INSERT ON gov_prices FOR EACH ROW EXECUTE FUNCTION gov_proof_guard()"
    )
    op.execute(
        "CREATE TRIGGER proof_binding BEFORE INSERT ON gov_fx FOR EACH ROW EXECUTE FUNCTION gov_proof_guard()"
    )
    op.execute(
        "CREATE TRIGGER proof_binding BEFORE INSERT ON gov_grants FOR EACH ROW EXECUTE FUNCTION gov_proof_guard()"
    )
    op.execute(
        "CREATE TRIGGER proof_binding BEFORE INSERT ON gov_grant_events FOR EACH ROW EXECUTE FUNCTION gov_proof_guard()"
    )
    op.execute(
        "CREATE TRIGGER proof_binding BEFORE INSERT ON gov_policies FOR EACH ROW EXECUTE FUNCTION gov_proof_guard()"
    )
    op.execute(
        "CREATE TRIGGER proof_binding BEFORE INSERT ON gov_settlements FOR EACH ROW EXECUTE FUNCTION gov_proof_guard()"
    )
    op.execute(
        "CREATE TRIGGER proof_binding BEFORE INSERT ON gov_cash_entries FOR EACH ROW EXECUTE FUNCTION gov_proof_guard()"
    )
    op.execute(
        "CREATE TRIGGER binding BEFORE INSERT OR UPDATE ON gov_config_prices FOR EACH ROW EXECUTE FUNCTION gov_binding_guard()"
    )
    op.execute(
        "CREATE TRIGGER binding BEFORE INSERT OR UPDATE ON gov_calls FOR EACH ROW EXECUTE FUNCTION gov_binding_guard()"
    )
    op.execute(
        "CREATE TRIGGER binding BEFORE INSERT OR UPDATE ON gov_usage FOR EACH ROW EXECUTE FUNCTION gov_binding_guard()"
    )
    op.execute(
        "CREATE TRIGGER binding BEFORE INSERT OR UPDATE ON gov_allocations FOR EACH ROW EXECUTE FUNCTION gov_binding_guard()"
    )


def downgrade():
    op.execute("DROP FUNCTION gov_validate_call_json(gov_calls)")
    op.execute("DROP FUNCTION gov_json_quantity(jsonb)")
    op.execute("DROP FUNCTION gov_json_time(jsonb)")
    op.execute("DROP FUNCTION gov_json_uuid(jsonb)")
    op.execute("DROP FUNCTION gov_json_object(jsonb,text[])")
    op.execute("ALTER TABLE gov_authorities DROP CONSTRAINT fk_gov_current_policy")
    op.execute("ALTER TABLE gov_evidence DROP CONSTRAINT fk_gov_evidence_call")
    op.execute("DROP TABLE gov_usage")
    op.execute("DROP TABLE gov_settlements")
    op.execute("DROP TABLE gov_retained")
    op.execute("DROP TABLE gov_cash_entries")
    op.execute("DROP TABLE gov_audit")
    op.execute("DROP TABLE gov_allocations")
    op.execute("DROP TABLE gov_calls")
    op.execute("DROP TABLE gov_budget_accounts")
    op.execute("DROP TABLE gov_operations")
    op.execute("DROP TABLE gov_config_prices")
    op.execute("DROP TABLE gov_grant_events")
    op.execute("DROP TABLE gov_configs")
    op.execute("DROP TABLE gov_agents")
    op.execute("DROP TABLE gov_workflows")
    op.execute("DROP TABLE gov_prices")
    op.execute("DROP TABLE gov_policies")
    op.execute("DROP TABLE gov_grants")
    op.execute("DROP TABLE gov_fx")
    op.execute("DROP TABLE gov_experiments")
    op.execute("DROP TABLE gov_evidence")
    op.execute("DROP TABLE gov_authorities")
    op.execute("DROP FUNCTION gov_proof_guard()")
    op.execute("DROP FUNCTION gov_binding_guard()")
    op.execute("DROP FUNCTION gov_immutable()")
