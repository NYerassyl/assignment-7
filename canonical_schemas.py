from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator


class Input(BaseModel):
    model_config = ConfigDict(extra='forbid')


class Register(Input):
    email: EmailStr = Field(max_length=254)
    nickname: str = Field(pattern=r'^[a-z]{3,24}$')
    password: str = Field(min_length=8, max_length=128)


class Login(Input):
    email: EmailStr = Field(max_length=254)
    password: str = Field(min_length=1, max_length=128)


class ProfilePatch(Input):
    displayName: str | None = Field(default=None, min_length=1, max_length=40)
    bio: str | None = Field(default=None, max_length=300)

    @model_validator(mode='after')
    def nonempty(self):
        if not self.model_fields_set or any(getattr(self, k) is None for k in self.model_fields_set):
            raise ValueError('Provide at least one non-null profile field.')
        return self
