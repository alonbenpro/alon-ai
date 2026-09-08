#!/usr/bin/env python3
"""Read-only roadmap contract coverage; not a product database/privacy implementation."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
RULES = json.loads((HERE / "data-inventory-rules.v1.json").read_text())
TABLES = RULES["table_policies"] | RULES["operational_policies"]
PROFILES = RULES["profiles"]
AXES = {"purpose", "source", "sensitivity", "encryption", "redaction", "normal_writers",
        "retention_writer", "internal_readers", "query", "model", "telemetry",
        "retention", "duration_authority", "deletion_order", "backup_expiry",
        "hold", "hold_owner", "hold_review", "restore"}

def projection_schema_ref(schema_id: str) -> dict:
    schema = RULES["descendant_schemas"][schema_id]
    raw = json.dumps(schema, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    return {"schema_version": schema["schema_version"], "schema_hash": hashlib.sha256(raw).hexdigest()}

def descendant_policy(transform: dict, table: str, path: str, field_type: str,
                      schema_ref: dict | None) -> dict | None:
    """A container selector is not a prefix grant: only a closed, typed leaf can inherit."""
    if not re.fullmatch(r"[a-z][a-z0-9_]*(?:\[\])?(?:\.[a-z][a-z0-9_]*(?:\[\])?)*", path):
        return None
    deny = RULES["descendant_projection_rules"]["deny_path_component_regex"]
    if any(re.search(deny, part.removesuffix("[]")) for part in path.split(".")):
        return None
    for root, schema_id in transform.get("descendant_schemas", {}).get(table, {}).items():
        if root not in transform["selectors"].get(table, []):
            continue
        relative = path[len(root):] if path.startswith(root + "[]") else (
            path[len(root) + 1:] if path.startswith(root + ".") else None)
        if relative is None:
            continue
        schema = RULES["descendant_schemas"][schema_id]
        if schema.get("additional_properties") is not False or schema_ref != projection_schema_ref(schema_id):
            return None
        leaf = schema["leaves"].get(relative)
        if not leaf or leaf["type"] != field_type:
            return None
        safe = leaf.get("descendant_safe_policy")
        if safe not in RULES["descendant_projection_rules"]["descendant_safe_policies"]:
            return None
        if {"ACCEPTED_TERM_REDACTED": "OFFER_TERMS_V1",
            "CLOSED_CHECKPOINT_AGGREGATE": "CHECKPOINT_LEARNING_V1"}.get(safe) != transform["id"]:
            return None
        if safe == "CLOSED_CHECKPOINT_AGGREGATE" and field_type not in {"integer", "bigint", "numeric", "enum", "boolean"}:
            return None
        if safe == "ACCEPTED_TERM_REDACTED" and set(transform["consumers"]) & {"GlobalLearningEngine", "ExperimentEvaluationAgent"}:
            return None
        return {"root": root, "leaf": relative, "schema_ref": schema_ref, "policy": safe}
    return None

def resolve(table: str, path: str, field_type: str = "text", *, schema_ref: dict | None = None) -> dict:
    """Total first-match resolver; unknown table fails and opaque containers grant no access."""
    policy = TABLES[table]
    path = re.sub(r"\[(?:0|[1-9][0-9]*)\]", "[]", path)
    leaf = path.rsplit(".", 1)[-1].removesuffix("[]")
    selected = None
    for rule in RULES["field_rules"]:
        predicates = []
        if "leaf_regex" in rule:
            predicates.append(re.fullmatch(rule["leaf_regex"], leaf) is not None)
        if "type_in" in rule:
            predicates.append(field_type in rule["type_in"])
        if rule.get("match_all") or (predicates and all(predicates)):
            selected = rule
            break
    assert selected is not None
    profile = PROFILES[selected["profile"]]
    operational = table in RULES["operational_policies"]
    internal = list(policy["internal_readers"])
    raw = profile["raw_readers"]
    if isinstance(raw, list):
        internal = sorted(set(internal) & set(raw))
    elif raw == "TABLE_CREATE_WRITER_ONLY":
        internal = [policy["create_writer"]]
    else:
        # A service can have an internal lookup port and a separately restricted
        # output port. Query-output membership neither adds nor removes DB access.
        internal = sorted(set(internal))
    if operational:
        internal = [] if selected["profile"] == "FORBIDDEN" else ["OperatorSessionService"]
    forbidden = selected["profile"] in {"FORBIDDEN", "LOOKUP", "CREDENTIAL_METADATA", "ENCRYPTED_SECRET"}
    grants = []
    if not forbidden and not operational and field_type not in {"json", "jsonb", "array", "composite", "object"}:
        for transform in RULES["transforms"]:
            roots = transform.get("descendant_schemas", {}).get(table, {})
            child = descendant_policy(transform, table, path, field_type, schema_ref)
            scalar = (path in transform["selectors"].get(table, []) and path not in roots
                      and path not in transform.get("structured_selectors", {}).get(table, [])
                      and not transform.get("source_intersection_only"))
            if scalar or child:
                grants.append({"transform": transform["id"], "consumers": transform["consumers"],
                               "mode": "PROJECTED_OUTPUT_ONLY;RECURSIVE_SOURCE_GRANTS_REQUIRED",
                               "projection": transform["projection"], "descendant": child})
    writers = {"create": policy["create_writer"], "update": policy["normal_update_writer"],
               "immutable_update": "DENY"}
    for key in ("insert_writer_arms", "mutable_writer_arms"):
        if key in policy:
            writers[key] = policy[key]
    payload = policy.get("payload_retention_override", policy.get("payload_retention", "SENSITIVE_SHORT"))
    if selected["profile"] in {"CONTENT", "ENCRYPTED_CONTENT", "LOOKUP", "PER_LEAF_CONTAINER"}:
        retention = {"shortest_of": [policy["retention_class"], payload],
                     "clock": policy["scope_clock"], "field_rule": profile["retention"]}
    else:
        retention = {"class": policy["retention_class"], "clock": policy["scope_clock"],
                     "field_rule": profile["retention"]}
    shared = RULES["shared_field_axes"]
    return {
        "table": table, "path": path, "type": field_type, "profile": selected["profile"],
        "purpose": policy["purpose"], "source": shared["source"],
        "sensitivity": profile["sensitivity"], "encryption": profile["encryption"],
        "redaction": profile["redaction"], "normal_writers": writers,
        "retention_writer": "RetentionCommandService",
        "internal_readers": internal,
        "internal_lookup": policy.get("internal_lookup_contract") if path == "recipient_hash" else None,
        "query": {"principals": [] if operational or forbidden else policy["query_readers"],
                  "field_access": "DENY" if operational else profile["query"],
                  "raw_hash_serialization": "DENY" if selected["profile"] == "LOOKUP" else "NO_ADDITIONAL_GRANT",
                  "intersection": shared["query_access"]},
        "model": grants, "telemetry": "DENY_RAW;" + ("DENY" if operational else profile["telemetry"]),
        "retention": retention, "duration_authority": RULES["duration_authority"],
        "deletion_order": policy["deletion_policy"] + ";" + shared["deletion_order"],
        "backup_expiry": shared["backup_expiry"], "hold": shared["holds"],
        "hold_owner": shared["hold_owner"], "hold_review": shared["hold_review"],
        "restore": policy.get("restore", shared["restore"]),
    }

def intersect_wrapper_grants(table: str, root: str, source: dict) -> list[dict]:
    """After validating immutable snapshot dependency refs, wrappers only narrow grants."""
    grants = []
    for wrapper in RULES["transforms"]:
        if not wrapper.get("source_intersection_only") or root not in wrapper["selectors"].get(table, []):
            continue
        for grant in source["model"]:
            consumers = sorted(set(wrapper["consumers"]) & set(grant["consumers"]))
            if consumers:
                grants.append({**grant, "consumers": consumers, "wrapper_transform": wrapper["id"],
                               "source": {"table": source["table"], "path": source["path"]}})
    return grants

def declared_fields(sources: dict[str, str]) -> dict[str, dict[str, str]]:
    """Extract explicit SQL columns and conservative normative record-field tokens.
    Composite/shorthand tokens are coverage witnesses, not a substitute for pg_catalog
    plus strict nested-schema equality required by DB-06-T01.
    """
    fields = {table: {} for table in RULES["table_policies"]}
    for text in sources.values():
        for match in re.finditer(r"CREATE TABLE ([a-z_]+) \(\n(.*?)\n\);", text, re.S):
            table, block = match.groups()
            assert table in fields, table
            for line in block.splitlines():
                column = re.match(r"\s+([a-z][a-z0-9_]*)\s+([a-z][a-z0-9_]*)", line)
                if column:
                    field, kind = column.groups()
                    if "CHECK" in line and " IN (" in line:
                        kind = "enum"
                    fields[table][field] = kind
        for line in text.splitlines():
            if not line.startswith("|"):
                continue
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            head = re.match(r"([a-z_]+)(?: /|$)", cells[0].replace("`", ""))
            if not head or head.group(1) not in fields or len(cells) < 2:
                continue
            table = head.group(1)
            # Exact field cell plus immutable reference/constraint tokens; extra witnesses
            # are deliberately restrictive rather than silently skipping shorthand leaves.
            declaration = cells[1] if " / " in cells[0] else " ".join(cells[1:])
            for token in re.findall(r"\b[a-z][a-z0-9]*(?:_[a-z0-9]+)+\b", declaration):
                fields[table].setdefault(token, "text")
            for token in re.findall(r"(?:^|; |, )([a-z][a-z0-9_]*) (?:uuid|text|integer|bigint|boolean|numeric|jsonb|timestamptz)", declaration):
                fields[table].setdefault(token, "text")
        action = re.search(r"Add action_controls with (.*?)\n\n", text, re.S)
        if action:
            for token in re.findall(r"\b[a-z][a-z0-9]*(?:_[a-z0-9]+)+\b", action.group(1)):
                fields["action_controls"].setdefault(token, "text")
    # DB-02..05 common immutable-record macro applies to every normative shorthand row.
    for table, entries in fields.items():
        entries.setdefault("created_at", "timestamptz")
        assert len(entries) > 1, "No source field witnesses for " + table
    return fields

def main() -> None:
    manifest = (HERE / RULES["table_manifest"]).read_text()
    listed = dict(re.findall(r"^\| ([a-z_]+) \| (BUSINESS_ACTIVE|SAFETY_LONG|SENSITIVE_SHORT|EVALUATION_VERSIONED) \| RetentionCommandService \|$", manifest, re.M))
    assert set(listed) == set(RULES["table_policies"]), "Exact table manifest mismatch"
    sources = {}
    for name in RULES["source_schema_documents"]:
        raw = (HERE / name).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == RULES["source_contract_sha256"][name], "Source-schema drift: " + name
        sources[name] = raw.decode()
    declared = declared_fields(sources)
    all_rows = []
    for table, policy in TABLES.items():
        assert {"create_writer", "internal_readers", "query_readers", "purpose", "retention_class",
                "normal_update_writer", "scope_clock", "deletion_policy"} <= policy.keys(), table
        if table in listed:
            assert policy["retention_class"] == listed[table]
        assert policy["retention_class"] in RULES["retention"]
        assert not re.search(r"\b(TBD|TODO|each|named|generic|future)\b", json.dumps(policy)), table
        witnesses = declared.get(table, {"current_handle_digest": "text", "expires_at": "timestamptz",
                                        "nonce_ciphertext": "bytea", "state": "enum"})
        for path, kind in witnesses.items():
            result = resolve(table, path, kind)
            assert AXES <= result.keys(), (table, path, AXES - result.keys())
            assert result == resolve(table, path, kind), "Nondeterminism"
            assert result["normal_writers"]["create"]
            all_rows.append(result)
    descendant_count = 0
    for transform in RULES["transforms"]:
        for table, roots in transform.get("descendant_schemas", {}).items():
            for root, schema_id in roots.items():
                assert root in transform["selectors"][table]
                schema = RULES["descendant_schemas"][schema_id]
                assert schema["schema_version"] == schema_id and schema["additional_properties"] is False
                for leaf, definition in schema["leaves"].items():
                    path = root + ("" if leaf.startswith("[]") else ".") + leaf
                    row = resolve(table, path, definition["type"], schema_ref=projection_schema_ref(schema_id))
                    assert row["model"] and {g["transform"] for g in row["model"]} == {transform["id"]}, (table, path)
                    descendant_count += 1
    assert RULES["field_rules"][-1] == {"id": "RESTRICTED_CONTENT_FALLBACK", "match_all": True, "profile": "CONTENT"}
    for table in TABLES:
        row = resolve(table, "new_unclassified_payload")
        assert row["profile"] == "CONTENT" and not row["model"]
        assert "DENY" in row["query"]["field_access"]
        secret = resolve(table, "access_token")
        assert secret["profile"] == "FORBIDDEN" and not secret["internal_readers"] and not secret["model"]
        lookup = resolve(table, "recipient_hash")
        assert lookup["profile"] == "LOOKUP" and not lookup["model"] and lookup["query"]["field_access"] == "DENY"
        assert resolve(table, "state", "text")["profile"] == "CONTENT"
        assert resolve(table, "state", "enum")["profile"] == "STATE_TIME"
        assert resolve(table, "payload_ciphertext")["profile"] == "ENCRYPTED_CONTENT"
        assert resolve(table, "payload", "jsonb")["profile"] == "PER_LEAF_CONTAINER"
    try:
        resolve("unregistered_table", "id")
    except KeyError:
        pass
    else:
        raise AssertionError("Unknown table did not fail")
    global_agents = {"GlobalLearningEngine", "ExperimentEvaluationAgent"}
    for table, path in [("conversation_messages", "raw_body_ciphertext"), ("budget_assertions", "upper_minor"),
                        ("calendar_observations", "payload_ciphertext"), ("contact_identities", "value_ciphertext")]:
        assert not any(global_agents & set(g["consumers"]) for g in resolve(table, path)["model"])
    assert all(g["transform"] == "CHECKPOINT_LEARNING_V1" for g in resolve("checkpoint_evidence_members", "evidence_partition")["model"])
    assert not resolve("agent_io_snapshots", "snapshot_ciphertext")["model"]
    positive = [
        ("metric_snapshots", "values_json.booking_count", "integer", "checkpoint.metrics.model.v1", "CHECKPOINT_LEARNING_V1"),
        ("offer_packages", "scope.summary", "text", "offer.scope.model.v1", "OFFER_TERMS_V1"),
        ("offer_packages", "scope.deliverables[0].quantity", "integer", "offer.scope.model.v1", "OFFER_TERMS_V1"),
        ("offer_economics", "payment_terms.instalments[0].amount_minor", "bigint", "offer.payment_terms.model.v1", "OFFER_TERMS_V1"),
        ("offer_variants", "payment_schedule[1].due_after_days", "integer", "offer.payment_schedule.model.v1", "OFFER_TERMS_V1"),
    ]
    for table, path, kind, schema_id, expected in positive:
        ref = projection_schema_ref(schema_id)
        row = resolve(table, path, kind, schema_ref=ref)
        assert row["model"] and {g["transform"] for g in row["model"]} == {expected}, (table, path)
        assert all(g["descendant"]["schema_ref"] == ref for g in row["model"])
        assert not resolve(table, path, kind)["model"], "Missing schema ref must deny"
        assert not resolve(table, path, kind, schema_ref={**ref, "schema_hash": "0" * 64})["model"]
        assert not resolve(table, path, "jsonb", schema_ref=ref)["model"], "Container type must deny"
    for table, path, kind, schema_id in [
        ("metric_snapshots", "values_json.recipient_hash", "text", "checkpoint.metrics.model.v1"),
        ("metric_snapshots", "values_json.unknown_count", "integer", "checkpoint.metrics.model.v1"),
        ("metric_snapshots", "values_json.booking_count", "text", "checkpoint.metrics.model.v1"),
        ("offer_packages", "scope.private_calendar.description", "text", "offer.scope.model.v1"),
        ("offer_packages", "scope.unknown_field", "text", "offer.scope.model.v1"),
        ("offer_economics", "payment_terms.bank_account", "text", "offer.payment_terms.model.v1"),
        ("offer_variants", "payment_schedule[].recipient_email", "text", "offer.payment_schedule.model.v1"),
    ]:
        assert not resolve(table, path, kind, schema_ref=projection_schema_ref(schema_id))["model"], (table, path)
    for table, root in [("metric_snapshots", "values_json"), ("offer_packages", "scope"),
                        ("offer_economics", "payment_terms"), ("offer_variants", "payment_schedule")]:
        assert not resolve(table, root)["model"] and not resolve(table, root, "jsonb")["model"]
    metric = resolve("metric_snapshots", "values_json.booking_count", "integer",
                     schema_ref=projection_schema_ref("checkpoint.metrics.model.v1"))
    wrapped = intersect_wrapper_grants("agent_io_snapshots", "snapshot_ciphertext", metric)
    assert wrapped and all(g["transform"] == "CHECKPOINT_LEARNING_V1" for g in wrapped)
    assert not intersect_wrapper_grants("agent_io_snapshots", "snapshot_ciphertext",
                                       resolve("conversation_messages", "raw_body_ciphertext"))
    lookup = resolve("suppression_entries", "recipient_hash")
    assert "SuppressionQueryService" in lookup["internal_readers"]
    assert lookup["internal_lookup"]["mode"] == "UNCACHED_LOCKED_SAME_GATEWAY_UNIT_OF_WORK"
    assert lookup["query"]["principals"] == [] and lookup["query"]["field_access"] == "DENY"
    assert lookup["query"]["raw_hash_serialization"] == "DENY" and not lookup["model"]
    assert RULES["retention"]["OPERATIONAL_BACKUP_CHAINS"]["absolute_recoverability_max_days"] == 35
    assert RULES["retention"]["OPERATIONAL_BACKUP_CHAINS"]["hold_extension"] is False
    assert RULES["retention"]["SENSITIVE_SHORT"]["maximum"] == {"days": 30}
    for name, policy in RULES["external_policies"].items():
        assert {"writer", "readers", "purpose", "sensitivity", "model", "telemetry", "encryption",
                "retention", "hold", "restore"} <= policy.keys(), name
        # All external fields inherit shared deletion/source/backup/hold-owner axes too.
        assert RULES["shared_field_axes"]["backup_expiry"] and RULES["shared_field_axes"]["deletion_order"]
    for pattern in RULES["redaction_rules"]["patterns"]:
        re.compile(pattern["regex"])
    assert "MINIMUM_CELL_5" in RULES["redaction_rules"]["global_free_text"]
    assert "NO_ROUTINE_OPERATOR_APPROVAL" in RULES["redaction_rules"]["source_span_rule"]
    digest = hashlib.sha256(json.dumps(all_rows, sort_keys=True).encode()).hexdigest()
    print(f"PASS exact table coverage: {len(listed)} product + {len(RULES['operational_policies'])} operational; {len(RULES['external_policies'])} external classes")
    print(f"PASS deterministic privacy axes: {len(all_rows)} source field witnesses; resolved manifest sha256={digest}")
    print("PASS source hashes, ordered total rules, exact owners, unknown-schema/secret/lookup/global-PII denials, container/transform intersection, retention/backup/hold/restore rules")
    print(f"PASS descendant projections: {descendant_count} registered leaf bindings + 5 explicit probes; unknown/prohibited/type/hash/container negatives; wrappers only intersect source grants")
    print("PASS suppression lookup: internal uncached locked SuppressionQueryService access; HTTP/report hash serialization, model and telemetry denied")
    print("NOTE source witnesses are roadmap coverage; DB-06-T01/SEC-06-T01 require physical-column and nested-schema equality before collection")

if __name__ == "__main__":
    main()
