"""
Pydantic Schemas for the Web API

These models define the data structures for API requests and responses.
Using Pydantic ensures that the data conforms to a specific structure
and provides automatic validation and documentation.
"""

from typing import Optional

from pydantic import BaseModel


class Site(BaseModel):
    """
    Represents a single site record as returned by the API.
    """

    id: int
    domain: str
    name: str
    category: Optional[str] = None
    is_active: bool

    class Config:
        """
        Pydantic configuration.
        `from_attributes = True` allows the model to be created from ORM objects
        or other objects with attributes, not just dictionaries.
        """

        from_attributes = True
