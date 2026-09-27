"""Explicit one-operator provisioning use case for the local CLI."""

from alon_ai.config import get_settings
from alon_ai.db.engine import create_engine
from alon_ai.db.repositories.operator_provisioning import (
    OperatorProvisioningDenied,
    OperatorProvisioningRepository,
)


async def provision_operator(display_name: str) -> str:
    settings = get_settings()
    subject = settings.operator_auth_subject
    if (
        not subject
        or not settings.operator_password_hash
        or not settings.session_signing_key
        or not display_name.strip()
    ):
        raise OperatorProvisioningDenied(
            "Operator authentication configuration is incomplete"
        )
    engine = create_engine(settings)
    try:
        operator_id, created = await OperatorProvisioningRepository(engine).provision(
            subject, display_name.strip()
        )
    finally:
        await engine.dispose()
    if created:
        return f"Operator provisioned: {operator_id}"
    return f"Operator already provisioned: {operator_id}"
