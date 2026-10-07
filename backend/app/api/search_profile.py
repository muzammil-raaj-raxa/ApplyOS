from fastapi import APIRouter

from app.jobs.search_profile import SearchProfile, load_search_profile, save_search_profile

router = APIRouter(prefix="/api/search-profile", tags=["search-profile"])


@router.get("")
def get_search_profile():
    return load_search_profile().model_dump()


@router.put("")
def update_search_profile(profile: SearchProfile):
    save_search_profile(profile)
    return profile.model_dump()
