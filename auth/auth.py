from datetime import datetime
from typing import Annotated

import jwt
import pytz
import requests
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from config.settings import settings
from database.async_db import get_db
from models.cognine_models import Employee


async def get_openid_config() -> dict:
    if not settings.openid_config_url:
        raise HTTPException(status_code=500, detail="OIDC configuration URL not set")
    resp = requests.get(settings.openid_config_url, timeout=10)
    if resp.status_code != 200:
        raise HTTPException(status_code=500, detail="Failed to fetch OpenID config")
    return resp.json()


async def get_signing_key(kid: str, jwks: dict):
    keys = jwks.get("keys", [])
    for key in keys:
        if key.get("kid") == kid:
            return jwt.algorithms.RSAAlgorithm.from_jwk(key)
    return None


async def get_employee_by_email(db: AsyncSession, email: str):
    stmt = select(Employee).where(Employee.email == email)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def validate_token(token: str, db: Session) -> dict:
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication Token is missing!",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        openid_config = await get_openid_config()
        jwks_uri = openid_config.get("jwks_uri")
        if not jwks_uri:
            raise HTTPException(status_code=500, detail="JWKS URI missing in OIDC config")
        jwks = requests.get(jwks_uri, timeout=10).json()

        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")
        if not kid:
            raise HTTPException(status_code=401, detail="Invalid token: Missing Key ID (kid)")

        signing_key = await get_signing_key(kid, jwks)
        if not signing_key:
            raise HTTPException(status_code=401, detail="Invalid token: Key not found in JWKS")

        decoded_token = jwt.decode(
            token,
            signing_key,
            algorithms=["RS256"],
            audience=settings.valid_audience,
            issuer=settings.valid_issuer,
        )

        app_id = decoded_token.get("appid")
        tid = decoded_token.get("tid")

        if (settings.client_id and app_id != settings.client_id) or (
            settings.tenant_id and tid != settings.tenant_id
        ):
            raise HTTPException(status_code=401, detail="Invalid token: Unauthorized app or tenant")

        exp_time = datetime.fromtimestamp(decoded_token["exp"], pytz.timezone(settings.timezone))
        current_time_ist = datetime.now(pytz.timezone(settings.timezone))
        if current_time_ist > exp_time:
            raise HTTPException(status_code=401, detail="Authentication Token Has Expired!")

        unique_name = decoded_token.get("unique_name")
        if not unique_name:
            raise HTTPException(status_code=401, detail="Invalid Token: unique_name missing")

        current_user = await get_employee_by_email(db, unique_name)
        if current_user is None:
            raise HTTPException(status_code=401, detail="Invalid Token")

        return {
            "user_id": current_user.id,
            "email": current_user.email,
            "employee_name": current_user.employeename,
        }
    except jwt.ExpiredSignatureError as e:
        raise HTTPException(status_code=401, detail="Token has expired") from e
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Token validation failed: {str(e)}") from e
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Authentication error: {str(e)}") from e


async def token_required(
    authorization: Annotated[str | None, Header()] = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
) -> dict:
    token = authorization.split(" ", 1)[1].strip()
    current_user = await validate_token(token, db)
    return current_user
