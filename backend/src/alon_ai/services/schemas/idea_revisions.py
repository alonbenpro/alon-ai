"""Version-bound operator instructions for a new governed research run."""

from uuid import UUID

from pydantic import Field, field_validator

from alon_ai.services.schemas.agent_runs import RunRef, StrictRunDTO


class IdeaRevisionRequest(StrictRunDTO):
    command_key: UUID
    run_id: UUID
    instructions: str = Field(min_length=1, max_length=4000)

    @field_validator("instructions")
    @classmethod
    def meaningful_instructions(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("revision instructions are blank")
        return value


class IdeaRevisionResult(RunRef):
    command_key: UUID
    revised_run_id: UUID
