from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class SizePriceEntry(BaseModel):
    model_config = ConfigDict(extra="allow")

    Name: str
    Price: Optional[float] = None


class ChoicePriceBySize(BaseModel):
    model_config = ConfigDict(extra="allow")

    sizeName: Optional[str] = None
    price: float


class ModifierChoice(BaseModel):
    model_config = ConfigDict(extra="allow")

    optionName: Optional[str] = None
    minRequired: Optional[int] = None
    maxAllowed: Optional[int] = None
    choiceName: str
    choicePrice: Optional[float] = None
    choicePriceBySize: List[ChoicePriceBySize] = Field(default_factory=list)


class ToppingEntry(BaseModel):
    model_config = ConfigDict(extra="allow")

    name: str
    group: Optional[str] = None
    price: Optional[float] = None
    priceHalf: Optional[float] = None


class ToppingsPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    default: List[str] = Field(default_factory=list)
    available: List[ToppingEntry] = Field(default_factory=list)


class ItemPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    s_no: Optional[str] = ""
    name: str
    price: Optional[float] = None
    options: List[ModifierChoice] = Field(default_factory=list)
    toppings: Optional[ToppingsPayload] = None
    ItemSizes: List[SizePriceEntry] = Field(default_factory=list)


class CategoryItemMinimalPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category_sizes: List[SizePriceEntry] = Field(default_factory=list)
    category_options: List[ModifierChoice] = Field(default_factory=list)
    category_toppings: Optional[ToppingsPayload] = None
    items: List[ItemPayload]
