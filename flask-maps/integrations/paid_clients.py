import os

class MunichReClient:
    def __init__(self):
        self.api_key = os.getenv("MUNICHRE_API_KEY", "")
        self.base_url = "https://api.munichre.com"
    def is_configured(self) -> bool:
        return bool(self.api_key)

class SwissReClient:
    def __init__(self):
        self.api_key = os.getenv("SWISSRE_API_KEY", "")
        self.base_url = "https://api.swissre.com"
    def is_configured(self) -> bool:
        return bool(self.api_key)

class PerilsClient:
    def __init__(self):
        self.api_key = os.getenv("PERILS_API_KEY", "")
        self.base_url = "https://api.perils.org"
    def is_configured(self) -> bool:
        return bool(self.api_key)

class OpenInsuranceClient:
    def __init__(self):
        self.client_id = os.getenv("OPEN_INSURANCE_CLIENT_ID", "")
        self.client_secret = os.getenv("OPEN_INSURANCE_CLIENT_SECRET", "")
        self.issuer = os.getenv("OPEN_INSURANCE_ISSUER", "")
        self.audience = os.getenv("OPEN_INSURANCE_AUDIENCE", "")
    def is_configured(self) -> bool:
        return all([self.client_id, self.client_secret, self.issuer, self.audience])
