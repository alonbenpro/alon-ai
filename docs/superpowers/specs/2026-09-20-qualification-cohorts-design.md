# Qualification Matrices and Cohorts Design

Founder OS L03 remains the authority for this checkpoint. This design records the approved implementation boundary: add immutable qualification and cohort persistence without replacing the existing campaign-supply or organization-protection systems.

Each lead dossier binds one existing supply candidate and global organization binding to the exact accepted offer, qualification profile, outreach policy, admitted organization, and supported recipient source used for evaluation. Dossier evidence is immutable and distinguishes observed facts, hypotheses, contradictions, and unknowns. A qualification matrix binds the dossier and exact profile; it contains exactly one result for every criterion in that profile, and every result retains at least one dossier-evidence reference.

The qualification command verifies complete criterion coverage, current supported contact evidence, the current accepted offer version, current organization admission, and the absence of suppression, previous-contact, ambiguity, identity-conflict, or other-experiment reservation blocks. Hard gates must pass, an observed fatal disqualifier rejects, and missing or stale evidence fails closed with a stable reason code. Accepted decisions are mirrored into the existing supply qualification record so fixed-50 targeting, batch limits, feedback, and candidate lineage remain authoritative.

A cohort is a single experiment-level immutable record, with no stage registry. Freezing locks the experiment, revalidates exactly 50 accepted decisions against their exact offer/profile/candidate/organization/recipient/dossier lineage and current contact/protection state, creates organization reservations, cohort members, and one replay-protected command receipt in one database transaction. Any failed member rolls back the entire freeze.

This checkpoint does not implement discovery, provider execution, deep-research orchestration, outreach, conversations, handoffs, learning, or frontend behavior.
