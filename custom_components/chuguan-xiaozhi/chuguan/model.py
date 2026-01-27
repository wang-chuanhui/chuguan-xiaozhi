from pydantic import BaseModel
from typing import Optional
''
# {"success":false,"statusCode":500,"message":"上报失败", "error": "update error"}
class SockResponse(BaseModel):
    success: bool
    statusCode: int
    message: Optional[str] = None
    error: Optional[str] = None