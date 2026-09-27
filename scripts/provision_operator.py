"""Bind the one configured private-login subject to the existing operator table."""

import argparse
import asyncio

from alon_ai.services.operator_provisioning import (
    OperatorProvisioningDenied,
    provision_operator,
)


async def provision(display_name: str) -> None:
    try:
        print(await provision_operator(display_name))
    except OperatorProvisioningDenied as error:
        raise SystemExit(str(error)) from None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--display-name", default="Alon")
    asyncio.run(provision(parser.parse_args().display_name))
