#  Copyright © 2025 Dr.-Ing. Paul Wilhelm <paul@wilhelm.dev>
#  This file is part of Archive Agent. See LICENSE for details.

from typing import List
from pydantic import BaseModel


class QuerySchema(BaseModel):
    question_rephrased: str
    answer_list: List[str]
    answer_conclusion: str
    chunk_ref_list: List[str]
    follow_up_list: List[str]
    reject: bool

    class Config:
        extra = "forbid"  # Ensures additionalProperties: false
