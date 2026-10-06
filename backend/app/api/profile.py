from fastapi import APIRouter, HTTPException

from app.profile.evidence import gap_report, total_months_of_experience
from app.profile.validator import load_profile

router = APIRouter(prefix="/api/profile", tags=["profile"])


@router.get("")
def get_profile():
    try:
        profile = load_profile()
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="career_profile.json not found")
    except ValueError as exc:  # bad JSON or failed validation
        raise HTTPException(status_code=422, detail=f"career profile is invalid: {exc}")
    months = total_months_of_experience(profile)
    return {
        "profile": profile.model_dump(),
        "experience": {"months": months, "years": round(months / 12, 1)},
        "gaps": gap_report(profile),
    }
