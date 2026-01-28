from pydantic import BaseModel
from typing import Optional, Any

class SockResponse(BaseModel):
    success: bool
    statusCode: int
    message: Optional[str] = None
    error: Optional[str] = None
    data: Optional[Any] = None