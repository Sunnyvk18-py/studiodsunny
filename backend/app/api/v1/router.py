from fastapi import APIRouter

from app.api.v1.endpoints import (
    activity,
    admin,
    ai,
    audit,
    auth,
    calendar,
    chat,
    clients,
    dashboard,
    debug,
    desk,
    docs,
    employees,
    files,
    invoices,
    leads,
    notifications,
    projects,
    reports,
    search,
    tasks,
)

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(desk.router, prefix="/desk", tags=["desk"])
api_router.include_router(clients.router, prefix="/clients", tags=["clients"])
api_router.include_router(projects.router, prefix="/projects", tags=["projects"])
api_router.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
api_router.include_router(calendar.router, prefix="/calendar", tags=["calendar"])
api_router.include_router(employees.router, prefix="/employees", tags=["employees"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
api_router.include_router(activity.router, prefix="/activity", tags=["activity"])
api_router.include_router(search.router, prefix="/search", tags=["search"])
api_router.include_router(ai.router, prefix="/ai", tags=["ai"])
api_router.include_router(leads.router, prefix="/leads", tags=["leads"])
api_router.include_router(invoices.router, prefix="/invoices", tags=["invoices"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(docs.router, prefix="/docs", tags=["docs"])
api_router.include_router(files.router, prefix="/files", tags=["files"])
api_router.include_router(audit.router, prefix="/audit", tags=["audit"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(debug.router, prefix="/debug", tags=["debug"])
