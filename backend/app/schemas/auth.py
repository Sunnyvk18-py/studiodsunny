from pydantic import BaseModel, EmailStr, Field

from app.schemas.common import UserBrief


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)


class TotpVerifyRequest(BaseModel):
    temp_token: str
    code: str = Field(min_length=6, max_length=8)


class TotpCodeRequest(BaseModel):
    code: str = Field(min_length=6, max_length=8)


class TotpDisableRequest(BaseModel):
    code: str = Field(min_length=6, max_length=8)
    current_password: str = Field(min_length=6)


class TokenUser(UserBrief):
    first_name: str
    last_name: str
    is_superadmin: bool
    permissions: list[str]
    employee_id: str | None = None
    org_id: str | None = None
    totp_enabled: bool = False


class MeResponse(BaseModel):
    user: TokenUser | None = None
    csrf_token: str | None = None
    needs_2fa: bool = False
    temp_token: str | None = None


class TotpSetupResponse(BaseModel):
    secret: str
    otpauth_url: str
    enabled: bool


class AuthProvidersResponse(BaseModel):
    google: bool
    totp_available: bool = True


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=6)
    new_password: str = Field(min_length=8)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8)


class AcceptInviteRequest(BaseModel):
    token: str
    password: str = Field(min_length=8)
    first_name: str | None = None
    last_name: str | None = None


class SessionOut(BaseModel):
    id: str
    created_at: str | None = None
    user_agent: str | None = None
    ip: str | None = None
    current: bool = False
