

class Supa:
    def __init__(self, supabase_url: str, supabase_key: str) -> None:
        self.url = supabase_url
        self.key = supabase_key

        self.rest_url = f"{self.url}/rest/v1"
        self.realtime_url = f"{self.url}/realtime/v1".replace("http", "ws")
        self.auth_url = f"{self.url}/auth/v1"
        self.storage_url = f"{self.url}/storage/v1"