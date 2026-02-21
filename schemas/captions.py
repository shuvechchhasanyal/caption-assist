from pydantic import BaseModel, Field

class PlatformCaptions(BaseModel):
    linkedin_caption: str = Field(
        description="Professional, thoughtful LinkedIn-style caption"
    )
    instagram_caption: str = Field(
        description="Engaging, aesthetic Instagram-style caption with emojis and hashtags"
    )
    whatsapp_caption: str = Field(
        description="Short, casual WhatsApp status-style caption"
    )