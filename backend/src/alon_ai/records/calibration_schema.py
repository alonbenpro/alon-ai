"""Immutable offer-fit calibration and post-calibration requalification records."""

from sqlalchemy import (
    ARRAY,
    CheckConstraint,
    ForeignKeyConstraint,
    Index,
    String,
    Table,
    UniqueConstraint,
)

from alon_ai.accounting import schema as g


def table(name, *parts):
    return Table("record_calibration_" + name, g.metadata, *parts)


proposals = table(
    "proposals",
    g.col("id", g.U, primary_key=True),
    g.col("experiment_id", g.U),
    g.col("base_offer_acceptance_id", g.U),
    g.col("base_offer_id", g.U),
    g.col("base_profile_id", g.U),
    g.col("base_policy_id", g.U),
    g.col("mismatch_code", String(64)),
    g.col("proposed_change_codes", ARRAY(String(64))),
    g.col("evidence_hash", String(64)),
    g.col("proposed_by", g.U),
    g.col("proposed_at", g.T),
    ForeignKeyConstraint(
        ["base_offer_acceptance_id", "experiment_id"],
        ["record_offer_acceptances.id", "record_offer_acceptances.experiment_id"],
    ),
    ForeignKeyConstraint(
        ["base_offer_id", "experiment_id"],
        ["record_offer_packages.id", "record_offer_packages.experiment_id"],
    ),
    ForeignKeyConstraint(
        ["base_profile_id"], ["record_offer_qualification_profiles.id"]
    ),
    ForeignKeyConstraint(["base_policy_id"], ["record_initial_outreach_policies.id"]),
    UniqueConstraint("id", "experiment_id"),
    CheckConstraint("cardinality(proposed_change_codes)>0"),
)

proposal_evidence = table(
    "proposal_evidence",
    g.col("proposal_id", g.U, primary_key=True),
    g.col("decision_id", g.U, primary_key=True),
    g.col("candidate_id", g.U),
    g.col("dossier_id", g.U),
    g.col("matrix_id", g.U),
    g.col("finding_code", String(64)),
    ForeignKeyConstraint(["proposal_id"], ["record_calibration_proposals.id"]),
    ForeignKeyConstraint(["decision_id"], ["record_qualification_decisions.id"]),
    ForeignKeyConstraint(["dossier_id"], ["record_qualification_dossiers.id"]),
    ForeignKeyConstraint(["matrix_id"], ["record_qualification_matrices.id"]),
    UniqueConstraint("proposal_id", "candidate_id"),
)

decisions = table(
    "decisions",
    g.col("id", g.U, primary_key=True),
    g.col("experiment_id", g.U),
    g.col("proposal_id", g.U, unique=True),
    g.col("base_offer_acceptance_id", g.U),
    g.col("base_offer_id", g.U),
    g.col("base_profile_id", g.U),
    g.col("base_policy_id", g.U),
    g.col("evidence_hash", String(64)),
    g.col("outcome", String(24)),
    g.col("rule_version", String(64)),
    g.col("reason_code", String(64)),
    g.col("decided_by", g.U),
    g.col("decided_at", g.T),
    ForeignKeyConstraint(
        ["proposal_id", "experiment_id"],
        [
            "record_calibration_proposals.id",
            "record_calibration_proposals.experiment_id",
        ],
    ),
    ForeignKeyConstraint(
        ["base_offer_acceptance_id", "experiment_id"],
        ["record_offer_acceptances.id", "record_offer_acceptances.experiment_id"],
    ),
    UniqueConstraint("id", "experiment_id"),
    CheckConstraint(
        "outcome IN ('ACCEPT','REJECT','INSUFFICIENT_EVIDENCE') AND "
        "rule_version='qualification-calibration-v1'"
    ),
)

# An experiment is the existing preparation boundary: only one accepted calibration
# may be fulfilled before its first cohort is frozen.
Index(
    "uq_record_calibration_one_accepted_per_experiment",
    decisions.c.experiment_id,
    unique=True,
    postgresql_where=decisions.c.outcome == "ACCEPT",
)

fulfillments = table(
    "fulfillments",
    g.col("id", g.U, primary_key=True),
    g.col("experiment_id", g.U),
    g.col("calibration_decision_id", g.U, unique=True),
    g.col("base_offer_acceptance_id", g.U),
    g.col("offer_acceptance_id", g.U),
    g.col("offer_id", g.U),
    g.col("profile_id", g.U),
    g.col("policy_id", g.U),
    g.col("fulfilled_by", g.U),
    g.col("fulfilled_at", g.T),
    ForeignKeyConstraint(
        ["calibration_decision_id", "experiment_id"],
        [
            "record_calibration_decisions.id",
            "record_calibration_decisions.experiment_id",
        ],
    ),
    ForeignKeyConstraint(
        ["base_offer_acceptance_id", "experiment_id"],
        ["record_offer_acceptances.id", "record_offer_acceptances.experiment_id"],
    ),
    ForeignKeyConstraint(
        ["offer_acceptance_id", "experiment_id"],
        ["record_offer_acceptances.id", "record_offer_acceptances.experiment_id"],
    ),
    ForeignKeyConstraint(
        ["offer_id", "experiment_id"],
        ["record_offer_packages.id", "record_offer_packages.experiment_id"],
    ),
    ForeignKeyConstraint(["profile_id"], ["record_offer_qualification_profiles.id"]),
    ForeignKeyConstraint(["policy_id"], ["record_initial_outreach_policies.id"]),
    UniqueConstraint("id", "experiment_id"),
    UniqueConstraint("offer_acceptance_id"),
)

# The accepted decision freezes its affected set. Fulfillment only supplies the
# independently accepted replacement offer and turns this immutable set into
# requalification obligations.
accepted_affected = table(
    "accepted_affected",
    g.col("calibration_decision_id", g.U, primary_key=True),
    g.col("candidate_id", g.U, primary_key=True),
    g.col("previous_decision_id", g.U),
    g.col("previous_dossier_id", g.U),
    g.col("previous_matrix_id", g.U),
    ForeignKeyConstraint(
        ["calibration_decision_id"], ["record_calibration_decisions.id"]
    ),
    ForeignKeyConstraint(
        ["previous_decision_id"], ["record_qualification_decisions.id"]
    ),
    ForeignKeyConstraint(["previous_dossier_id"], ["record_qualification_dossiers.id"]),
    ForeignKeyConstraint(["previous_matrix_id"], ["record_qualification_matrices.id"]),
)

obligations = table(
    "obligations",
    g.col("id", g.U, primary_key=True),
    g.col("experiment_id", g.U),
    g.col("fulfillment_id", g.U),
    g.col("candidate_id", g.U),
    g.col("previous_decision_id", g.U),
    g.col("previous_dossier_id", g.U),
    g.col("previous_matrix_id", g.U),
    g.col("required_offer_acceptance_id", g.U),
    g.col("created_at", g.T),
    ForeignKeyConstraint(
        ["fulfillment_id", "experiment_id"],
        [
            "record_calibration_fulfillments.id",
            "record_calibration_fulfillments.experiment_id",
        ],
    ),
    ForeignKeyConstraint(
        ["previous_decision_id"], ["record_qualification_decisions.id"]
    ),
    ForeignKeyConstraint(["previous_dossier_id"], ["record_qualification_dossiers.id"]),
    ForeignKeyConstraint(["previous_matrix_id"], ["record_qualification_matrices.id"]),
    ForeignKeyConstraint(
        ["required_offer_acceptance_id", "experiment_id"],
        ["record_offer_acceptances.id", "record_offer_acceptances.experiment_id"],
    ),
    UniqueConstraint("id", "experiment_id"),
    UniqueConstraint("fulfillment_id", "candidate_id"),
)

completions = table(
    "completions",
    g.col("obligation_id", g.U, primary_key=True),
    g.col("decision_id", g.U, unique=True),
    g.col("completed_at", g.T),
    ForeignKeyConstraint(["obligation_id"], ["record_calibration_obligations.id"]),
    ForeignKeyConstraint(["decision_id"], ["record_qualification_decisions.id"]),
)

TABLES = (
    proposals,
    proposal_evidence,
    decisions,
    fulfillments,
    accepted_affected,
    obligations,
    completions,
)
IMMUTABLE_TABLES = tuple(table.name for table in TABLES)

# Application commands perform freshness and ownership checks under the
# experiment lock. These guards retain the non-forgeable, exact-reference part
# of that contract for direct SQL as well.
GUARD_SQL = r"""
CREATE FUNCTION record_calibration_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF TG_OP<>'INSERT' THEN RAISE EXCEPTION 'immutable calibration record'; END IF;
 RETURN NEW;
END $$;
CREATE FUNCTION record_calibration_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE proposal record_calibration_proposals; decision record_calibration_decisions;
 acceptance record_offer_acceptances; fulfillment record_calibration_fulfillments;
 obligation record_calibration_obligations;
 qualification record_qualification_decisions; package record_offer_packages;
BEGIN
 IF TG_TABLE_NAME='record_calibration_proposals' THEN
  PERFORM 1 FROM gov_experiments WHERE id=NEW.experiment_id FOR UPDATE;
  SELECT * INTO acceptance FROM record_offer_acceptances WHERE id=NEW.base_offer_acceptance_id;
  IF acceptance.id IS NULL OR ROW(acceptance.experiment_id,acceptance.offer_id,acceptance.profile_id,acceptance.policy_id)
     IS DISTINCT FROM ROW(NEW.experiment_id,NEW.base_offer_id,NEW.base_profile_id,NEW.base_policy_id)
     OR NEW.base_offer_acceptance_id IS DISTINCT FROM
       (SELECT id FROM record_offer_acceptances WHERE experiment_id=NEW.experiment_id ORDER BY accepted_at DESC,id DESC LIMIT 1)
  THEN RAISE EXCEPTION 'exact calibration base required'; END IF;
 ELSIF TG_TABLE_NAME='record_calibration_proposal_evidence' THEN
  SELECT * INTO proposal FROM record_calibration_proposals WHERE id=NEW.proposal_id;
  SELECT * INTO qualification FROM record_qualification_decisions WHERE id=NEW.decision_id;
  IF proposal.id IS NULL OR qualification.id IS NULL
     OR ROW(qualification.candidate_id,qualification.dossier_id,qualification.matrix_id,qualification.experiment_id,qualification.offer_acceptance_id)
        IS DISTINCT FROM ROW(NEW.candidate_id,NEW.dossier_id,NEW.matrix_id,proposal.experiment_id,proposal.base_offer_acceptance_id)
     OR NEW.finding_code<>proposal.mismatch_code
     OR NOT (NEW.finding_code,qualification.outcome) IN (
       ('TECHNICAL_MISMATCH','REJECTED_TECHNICAL_MISMATCH'),
       ('ECONOMIC_MISMATCH','REJECTED_ECONOMIC_MISMATCH'),
       ('BUYER_MISMATCH','REJECTED_BUYER_MISMATCH'))
     OR NOT NEW.finding_code=ANY(qualification.finding_codes)
  THEN RAISE EXCEPTION 'exact calibration evidence required'; END IF;
 ELSIF TG_TABLE_NAME='record_calibration_decisions' THEN
  PERFORM 1 FROM gov_experiments WHERE id=NEW.experiment_id FOR UPDATE;
  SELECT * INTO proposal FROM record_calibration_proposals WHERE id=NEW.proposal_id;
  IF proposal.id IS NULL
     OR ROW(NEW.experiment_id,NEW.base_offer_acceptance_id,NEW.base_offer_id,NEW.base_profile_id,NEW.base_policy_id,NEW.evidence_hash)
        IS DISTINCT FROM ROW(proposal.experiment_id,proposal.base_offer_acceptance_id,proposal.base_offer_id,proposal.base_profile_id,proposal.base_policy_id,proposal.evidence_hash)
     OR NOT EXISTS(SELECT 1 FROM record_calibration_proposal_evidence e WHERE e.proposal_id=NEW.proposal_id GROUP BY e.proposal_id HAVING count(*)>=2 AND count(DISTINCT e.candidate_id)>=2)
     OR (NEW.outcome='ACCEPT' AND (EXISTS(SELECT 1 FROM record_qualification_cohorts WHERE experiment_id=NEW.experiment_id)
       OR EXISTS(SELECT 1 FROM record_calibration_decisions WHERE experiment_id=NEW.experiment_id AND outcome='ACCEPT')))
  THEN RAISE EXCEPTION 'invalid calibration decision'; END IF;
 ELSIF TG_TABLE_NAME='record_calibration_accepted_affected' THEN
  SELECT * INTO decision FROM record_calibration_decisions WHERE id=NEW.calibration_decision_id;
  SELECT * INTO qualification FROM record_qualification_decisions WHERE id=NEW.previous_decision_id;
  IF decision.id IS NULL OR qualification.id IS NULL OR decision.outcome<>'ACCEPT'
     OR ROW(qualification.candidate_id,qualification.dossier_id,qualification.matrix_id,qualification.experiment_id,qualification.offer_acceptance_id)
        IS DISTINCT FROM ROW(NEW.candidate_id,NEW.previous_dossier_id,NEW.previous_matrix_id,decision.experiment_id,decision.base_offer_acceptance_id)
     OR EXISTS(SELECT 1 FROM record_qualification_decisions later JOIN record_qualification_dossiers later_dossier ON later_dossier.id=later.dossier_id
       JOIN record_qualification_dossiers current_dossier ON current_dossier.id=qualification.dossier_id
       WHERE later.candidate_id=qualification.candidate_id AND later.offer_acceptance_id=decision.base_offer_acceptance_id
       AND later_dossier.version>current_dossier.version)
  THEN RAISE EXCEPTION 'invalid accepted calibration set'; END IF;
 ELSIF TG_TABLE_NAME='record_calibration_fulfillments' THEN
  PERFORM 1 FROM gov_experiments WHERE id=NEW.experiment_id FOR UPDATE;
  SELECT * INTO decision FROM record_calibration_decisions WHERE id=NEW.calibration_decision_id;
  SELECT * INTO acceptance FROM record_offer_acceptances WHERE id=NEW.offer_acceptance_id;
  SELECT * INTO package FROM record_offer_packages WHERE id=acceptance.offer_id;
  IF decision.id IS NULL OR decision.outcome<>'ACCEPT' OR acceptance.id IS NULL OR package.id IS NULL
     OR ROW(NEW.experiment_id,NEW.base_offer_acceptance_id) IS DISTINCT FROM ROW(decision.experiment_id,decision.base_offer_acceptance_id)
     OR ROW(NEW.experiment_id,NEW.offer_id,NEW.profile_id,NEW.policy_id) IS DISTINCT FROM ROW(acceptance.experiment_id,acceptance.offer_id,acceptance.profile_id,acceptance.policy_id)
     OR package.calibration_decision_id IS DISTINCT FROM decision.id OR acceptance.id=decision.base_offer_acceptance_id
     OR acceptance.accepted_at<decision.decided_at
     OR acceptance.id IS DISTINCT FROM (SELECT id FROM record_offer_acceptances WHERE experiment_id=NEW.experiment_id ORDER BY accepted_at DESC,id DESC LIMIT 1)
     OR EXISTS(SELECT 1 FROM record_qualification_cohorts WHERE experiment_id=NEW.experiment_id)
  THEN RAISE EXCEPTION 'invalid calibration fulfillment'; END IF;
 ELSIF TG_TABLE_NAME='record_calibration_obligations' THEN
  SELECT * INTO fulfillment FROM record_calibration_fulfillments WHERE id=NEW.fulfillment_id;
  SELECT * INTO qualification FROM record_qualification_decisions WHERE id=NEW.previous_decision_id;
  IF fulfillment.id IS NULL OR qualification.id IS NULL
     OR ROW(NEW.experiment_id,NEW.required_offer_acceptance_id,NEW.candidate_id,NEW.previous_dossier_id,NEW.previous_matrix_id)
        IS DISTINCT FROM ROW(fulfillment.experiment_id,fulfillment.offer_acceptance_id,qualification.candidate_id,qualification.dossier_id,qualification.matrix_id)
     OR qualification.offer_acceptance_id<>fulfillment.base_offer_acceptance_id
 THEN RAISE EXCEPTION 'invalid requalification obligation'; END IF;
 ELSIF TG_TABLE_NAME='record_calibration_completions' THEN
  SELECT * INTO obligation FROM record_calibration_obligations WHERE id=NEW.obligation_id;
  SELECT * INTO fulfillment FROM record_calibration_fulfillments WHERE id=obligation.fulfillment_id;
  SELECT * INTO qualification FROM record_qualification_decisions WHERE id=NEW.decision_id;
  IF fulfillment.id IS NULL OR qualification.id IS NULL OR qualification.outcome NOT IN ('QUALIFIED_CONTACTABLE','PILOT_FIT_CONTACTABLE')
     OR ROW(qualification.candidate_id,qualification.experiment_id,qualification.offer_acceptance_id)
        IS DISTINCT FROM ROW(obligation.candidate_id,fulfillment.experiment_id,obligation.required_offer_acceptance_id)
     OR qualification.decided_at<fulfillment.fulfilled_at
  THEN RAISE EXCEPTION 'invalid requalification completion'; END IF;
 END IF;
 RETURN NEW;
END $$;
"""
