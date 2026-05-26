from typing import Literal

from pydantic import BaseModel, ConfigDict


HighlightType = Literal[
    "conflict",
    "reversal",
    "face_slap",
    "villain_pressure",
    "identity_reveal",
    "revenge_counterattack",
    "sweet_moment",
    "confession",
    "rescue",
    "betrayal",
    "misunderstanding",
    "tearjerker",
    "cliffhanger",
    "comic_relief",
]

AudienceEmotion = Literal[
    "anger",
    "disgust",
    "shock",
    "satisfaction",
    "anticipation",
    "sympathy",
    "sadness",
    "anxiety",
    "sweetness",
    "delight",
    "amusement",
    "admiration",
    "curiosity",
    "relief",
]

InteractionIntent = Literal[
    "vent",
    "celebrate",
    "support",
    "comfort",
    "ship",
    "tease",
    "applaud",
    "predict",
    "question",
]

SentimentPolarity = Literal["positive", "negative", "mixed", "neutral"]


class HighlightTaxonomy(BaseModel):
    model_config = ConfigDict(frozen=True)

    taxonomy_version: str
    highlight_type_enum: list[str]
    audience_emotion_enum: list[str]
    interaction_intent_enum: list[str]

    def as_prompt_payload(self) -> dict:
        return self.model_dump(mode="json")


TAXONOMY = HighlightTaxonomy(
    taxonomy_version="highlight_taxonomy_v0.1",
    highlight_type_enum=[
        "conflict",
        "reversal",
        "face_slap",
        "villain_pressure",
        "identity_reveal",
        "revenge_counterattack",
        "sweet_moment",
        "confession",
        "rescue",
        "betrayal",
        "misunderstanding",
        "tearjerker",
        "cliffhanger",
        "comic_relief",
    ],
    audience_emotion_enum=[
        "anger",
        "disgust",
        "shock",
        "satisfaction",
        "anticipation",
        "sympathy",
        "sadness",
        "anxiety",
        "sweetness",
        "delight",
        "amusement",
        "admiration",
        "curiosity",
        "relief",
    ],
    interaction_intent_enum=[
        "vent",
        "celebrate",
        "support",
        "comfort",
        "ship",
        "tease",
        "applaud",
        "predict",
        "question",
    ],
)
