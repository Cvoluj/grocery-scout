from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from libs.pb_client import runtime

bearer = HTTPBearer()


def verify_token(credentials: HTTPAuthorizationCredentials = Security(bearer)):
    if credentials.credentials != runtime.get("LLM_SERVICE_API_KEY"):
        raise HTTPException(status_code=401, detail="Invalid token")
    return credentials.credentials
