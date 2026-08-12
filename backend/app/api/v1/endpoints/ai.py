from fastapi import APIRouter, HTTPException

from app.core.deps import CurrentUser, DbDep
from app.core.permissions import Perm, role_has_permission
from app.schemas.misc import AIAskRequest, AIAskResponse
from app.services.ai import answer_question, founder_briefing

router = APIRouter()


@router.get("/briefing")
def briefing(db: DbDep, user: CurrentUser):
    text, actions = founder_briefing(db, user)
    return {"briefing": text, "recommended_actions": actions}


@router.post("/ask", response_model=AIAskResponse)
def ask(payload: AIAskRequest, db: DbDep, user: CurrentUser):
    if not role_has_permission(user.role_key, Perm.AI_USE):
        raise HTTPException(403, "Sunny AI is not available for this role")
    answer, citations = answer_question(db, user, payload.question)
    return AIAskResponse(answer=answer, citations=citations)
