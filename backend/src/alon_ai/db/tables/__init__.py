"""Canonical metadata and registration of every existing SQL table."""

from alon_ai.db.tables import accounting as accounting
from alon_ai.db.tables import contact as contact
from alon_ai.db.tables import openai as openai
from alon_ai.db.tables import records as records
from alon_ai.db.tables import records_calibration as records_calibration
from alon_ai.db.tables import records_offer as records_offer
from alon_ai.db.tables import records_operator as records_operator
from alon_ai.db.tables import records_organization as records_organization
from alon_ai.db.tables import records_outreach as records_outreach
from alon_ai.db.tables import (
    records_qualification as records_qualification,
)
from alon_ai.db.tables import records_readiness as records_readiness
from alon_ai.db.tables import supply as supply
from alon_ai.db.tables.accounting import metadata

__all__ = ["metadata"]
