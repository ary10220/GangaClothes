from pydantic import BaseModel, EmailStr, Field


class LoginIn(BaseModel):
    """CU-02: login con contexto de tenant.
    El tenant se identifica por su codigo + email + password.
    (Elegimos codigo de tenant en el formulario; justificacion en el README.)
    """
    codigo_tenant: str = Field(min_length=1, max_length=50)
    email: EmailStr
    password: str


class SuperLoginIn(BaseModel):
    """Login del superadministrador de plataforma. Sin tenant."""
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    kind: str
    """'tenant' o 'super'."""
    tenant_id: int | None = None
    tenant_codigo: str | None = None
    user_id: int
    nombre: str
    roles: list[str]


class MeOut(BaseModel):
    kind: str
    user_id: int
    nombre: str
    email: str
    roles: list[str]
    tenant_id: int | None = None
    tenant_codigo: str | None = None
    tenant_razon_social: str | None = None
