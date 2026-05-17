from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..dependencies import get_current_workspace
from ..models import EmailTopicRule, Keyword, Workspace
from ..schemas import EmailTopicRuleCreate, EmailTopicRuleOut, EmailTopicRuleUpdate

router = APIRouter(prefix="/api/email-topic-rules", tags=["email-topic-rules"])


def rule_out(rule: EmailTopicRule) -> EmailTopicRuleOut:
    return EmailTopicRuleOut(
        id=rule.id,
        workspace_id=rule.workspace_id,
        name=rule.name,
        rule_type=rule.rule_type,
        keyword_ids=rule.keyword_ids,
        exclude_keyword_ids=rule.exclude_keyword_ids,
        enabled=rule.enabled,
        recipients=rule.recipients,
        created_at=rule.created_at,
        updated_at=rule.updated_at,
    )


async def validate_keyword_ids(
    db: AsyncSession,
    workspace_id: int,
    keyword_ids: list[int],
    exclude_keyword_ids: list[int],
) -> None:
    ids = set(keyword_ids or []) | set(exclude_keyword_ids or [])
    if not ids:
        return
    result = await db.execute(
        select(Keyword.id).where(Keyword.workspace_id == workspace_id, Keyword.id.in_(ids))
    )
    found = {row[0] for row in result.all()}
    missing = sorted(ids - found)
    if missing:
        raise HTTPException(400, f"关键词不属于当前工作区或不存在: {missing}")


@router.get("", response_model=list[EmailTopicRuleOut])
async def list_rules(
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace),
):
    result = await db.execute(
        select(EmailTopicRule)
        .where(EmailTopicRule.workspace_id == workspace.id)
        .order_by(EmailTopicRule.created_at.desc(), EmailTopicRule.id.desc())
    )
    return [rule_out(rule) for rule in result.scalars().all()]


@router.post("", response_model=EmailTopicRuleOut)
async def create_rule(
    payload: EmailTopicRuleCreate,
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace),
):
    await validate_keyword_ids(db, workspace.id, payload.keyword_ids, payload.exclude_keyword_ids)
    rule = EmailTopicRule(
        workspace_id=workspace.id,
        name=payload.name.strip(),
        rule_type=payload.rule_type,
        enabled=payload.enabled,
        recipients=payload.recipients,
    )
    rule.set_keyword_ids(payload.keyword_ids)
    rule.set_exclude_keyword_ids(payload.exclude_keyword_ids)
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return rule_out(rule)


@router.put("/{rule_id}", response_model=EmailTopicRuleOut)
async def update_rule(
    rule_id: int,
    payload: EmailTopicRuleUpdate,
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace),
):
    rule = await db.get(EmailTopicRule, rule_id)
    if not rule or rule.workspace_id != workspace.id:
        raise HTTPException(404, "Email topic rule not found")

    data = payload.model_dump(exclude_unset=True)
    keyword_ids = data.get("keyword_ids", rule.keyword_ids)
    exclude_keyword_ids = data.get("exclude_keyword_ids", rule.exclude_keyword_ids)
    await validate_keyword_ids(db, workspace.id, keyword_ids, exclude_keyword_ids)

    if "name" in data and data["name"] is not None:
        rule.name = data["name"].strip()
    for field in ("rule_type", "enabled", "recipients"):
        if field in data:
            setattr(rule, field, data[field])
    if "keyword_ids" in data:
        rule.set_keyword_ids(data["keyword_ids"] or [])
    if "exclude_keyword_ids" in data:
        rule.set_exclude_keyword_ids(data["exclude_keyword_ids"] or [])

    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return rule_out(rule)


@router.delete("/{rule_id}")
async def delete_rule(
    rule_id: int,
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace),
):
    rule = await db.get(EmailTopicRule, rule_id)
    if not rule or rule.workspace_id != workspace.id:
        raise HTTPException(404, "Email topic rule not found")
    await db.delete(rule)
    await db.commit()
    return {"success": True}
