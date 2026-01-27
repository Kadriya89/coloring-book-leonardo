"""Pydantic models for Leonardo AI API responses."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class GenerationStatus(str, Enum):
    """Status of a generation request."""

    PENDING = "PENDING"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"


class GenerationImage(BaseModel):
    """A single generated image."""

    id: str
    url: str
    nsfw: bool = False
    likeCount: int = 0
    motionMP4URL: str | None = None

    class Config:
        extra = "allow"


class Generation(BaseModel):
    """A generation request and its results."""

    id: str
    status: GenerationStatus
    createdAt: datetime | None = None
    prompt: str | None = None
    negativePrompt: str | None = None
    modelId: str | None = None
    width: int | None = None
    height: int | None = None
    seed: int | None = None
    generated_images: list[GenerationImage] = Field(default_factory=list)

    class Config:
        extra = "allow"


class GenerationRequest(BaseModel):
    """Request body for creating a generation."""

    prompt: str
    modelId: str | None = None
    width: int = 2550
    height: int = 3300
    num_images: int = 1
    seed: int | None = None
    negative_prompt: str | None = None
    guidance_scale: float | None = None
    public: bool = False
    alchemy: bool = False
    photoReal: bool = False
    presetStyle: str | None = None

    class Config:
        extra = "allow"


class PlatformModel(BaseModel):
    """A Leonardo platform model."""

    id: str
    name: str
    description: str | None = None
    nsfw: bool = False
    featured: bool = False
    generated_image: dict | None = None

    class Config:
        extra = "allow"


class UserInfo(BaseModel):
    """User account information."""

    id: str
    username: str | None = None
    tokenRenewalDate: str | None = None
    subscriptionTokens: int | None = None
    apiCredit: int | None = None

    class Config:
        extra = "allow"


class APIResponse(BaseModel):
    """Generic API response wrapper."""

    data: Any = None
    error: str | None = None

    class Config:
        extra = "allow"
