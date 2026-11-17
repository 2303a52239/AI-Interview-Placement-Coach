import json
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.performance import PreparationPlan
from app.schemas.performance import PerformanceSummary, PreparationPlanOut, PreparationItemOut
from app.utils.security import get_current_user
from app.services.performance_service import get_performance_summary
from app.services.prep_plan_service import generate_preparation_plan, build_weekly_schedule

router = APIRouter(tags=["Performance & Preparation"])


@router.get("/performance", response_model=PerformanceSummary)
def performance(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return get_performance_summary(db, current_user.id)


@router.get("/preparation-plan", response_model=PreparationPlanOut)
def get_prep_plan(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    plan = db.query(PreparationPlan).filter(PreparationPlan.user_id == current_user.id).first()
    if not plan:
        plan = generate_preparation_plan(db, current_user.id)
    return PreparationPlanOut(generated_at=plan.generated_at, items=[PreparationItemOut.model_validate(i) for i in plan.items], weekly_schedule=build_weekly_schedule(plan.items))


@router.post("/preparation-plan/regenerate", response_model=PreparationPlanOut)
def regenerate_prep_plan(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    plan = generate_preparation_plan(db, current_user.id)
    return PreparationPlanOut(generated_at=plan.generated_at, items=[PreparationItemOut.model_validate(i) for i in plan.items], weekly_schedule=build_weekly_schedule(plan.items))
