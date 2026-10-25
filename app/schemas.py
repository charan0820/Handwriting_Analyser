from typing import Literal
from pydantic import BaseModel, Field, model_validator


class Settings(BaseModel):
    engine: Literal['trocr', 'crnn'] = 'trocr'
    detector: Literal['kraken', 'projection'] = 'kraken'
    paragraph_mode: Literal['lines', 'paragraphs'] = 'paragraphs'
    preprocessing: Literal['natural', 'enhanced'] = 'natural'
    deskew: bool = True
    rotation: Literal[0, 90, 180, 270] = 0
    corners: list[tuple[float, float]] | None = None
    beam_width: int = Field(default=3, ge=1, le=5)
    max_new_tokens: int = Field(default=128, ge=16, le=256)
    line_padding: int = Field(default=8, ge=0, le=40)
    review_threshold: float = Field(default=0.65, ge=0, le=1)

    @model_validator(mode='after')
    def valid_corners(self):
        if self.corners is not None:
            if len(self.corners) != 4 or any(not (0 <= x <= 1 and 0 <= y <= 1) for x, y in self.corners):
                raise ValueError('Use four normalized page corners, clockwise from top left.')
        return self


class Line(BaseModel):
    id: str
    polygon: list[tuple[float, float]] = Field(min_length=4, max_length=4096)
    baseline: list[tuple[float, float]] | None = None
    raw_text: str = ''
    text: str = Field(default='', max_length=20000)
    score: float | None = None
    warnings: list[str] = Field(default_factory=list)
    reviewed: bool = False
    paragraph_start: bool = False


class Document(BaseModel):
    schema_version: int = 1
    width: int
    height: int
    original_width: int
    original_height: int
    transform: list[list[float]]
    lines: list[Line] = Field(default_factory=list, max_length=5000)
    raw_text: str = ''
    full_text: str = ''
    warnings: list[str] = Field(default_factory=list)
    model: dict = Field(default_factory=dict)
    settings: Settings
    timings: dict = Field(default_factory=dict)


class Edit(BaseModel):
    revision: int = Field(ge=0)
    title: str = Field(min_length=1, max_length=160)
    lines: list[Line] = Field(max_length=5000)
    paragraph_mode: Literal['lines', 'paragraphs'] = 'paragraphs'
    reference: str | None = Field(default=None, max_length=100000)


class Rerun(BaseModel):
    line_ids: list[str] = Field(min_length=1, max_length=5000)
