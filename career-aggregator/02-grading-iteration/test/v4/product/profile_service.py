class ProfileService:
    def create_profile(self, user_id: int, title: str, description: str) -> dict:
        raise NotImplementedError("Profile service not implemented yet")

    def get_profile(self, profile_id: int) -> dict | None:
        raise NotImplementedError("Profile service not implemented yet")
