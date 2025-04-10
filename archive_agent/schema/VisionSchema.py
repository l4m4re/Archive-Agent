#  Copyright © 2025 Dr.-Ing. Paul Wilhelm <paul@wilhelm.dev>
#  This file is part of Archive Agent. See LICENSE for details.

from pydantic import BaseModel


class VisionSchema(BaseModel):
    answer: str
    reject: bool
    rejection_reason: str

    class Config:
        extra = "forbid"  # Ensures additionalProperties: false
