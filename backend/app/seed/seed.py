"""Seed realistic Studio Sunny HQ demo data."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select

from app.core.security import hash_password
from app.db.base import utcnow
from app.db.session import SessionLocal, engine
from app.db.base import Base
from app import models  # noqa: F401
from app.models.activity import Activity
from app.models.chat import ChatChannel, ChatMessage
from app.models.client import Client
from app.models.department import Department
from app.models.document import EMPTY_DOC, Document
from app.models.employee import Employee
from app.models.file_asset import FileAsset
from app.models.invoice import Invoice
from app.models.lead import Lead
from app.models.notification import Notification
from app.models.project import Project, ProjectMember, ProjectMilestone
from app.models.task import Task
from app.core.schema import ensure_schema
from app.core.tenant import STUDIO_SUNNY_ORG_ID
from app.models.organization import Organization, default_org
from app.models.user import User

DEMO_PASSWORD = "SunnyHQ2026!"
TODAY = date.today()


def get_or_create_dept(db, name: str, slug: str, description: str) -> Department:
    existing = db.scalar(select(Department).where(Department.slug == slug))
    if existing:
        return existing
    d = Department(name=name, slug=slug, description=description, org_id=STUDIO_SUNNY_ORG_ID)
    db.add(d)
    db.flush()
    return d


def create_person(
    db,
    *,
    email: str,
    first: str,
    last: str,
    role: str,
    title: str,
    dept: Department | None,
    location: str,
    salary: int,
    skills: list[str],
    availability: str = "available",
    joining: date | None = None,
    superadmin: bool = False,
) -> tuple[User, Employee]:
    existing = db.scalar(select(User).where(User.email == email))
    if existing:
        return existing, existing.employee
    user = User(
        email=email,
        hashed_password=hash_password(DEMO_PASSWORD),
        first_name=first,
        last_name=last,
        display_name=f"{first} {last}".strip() if last else first,
        role_key=role,
        is_active=True,
        is_superadmin=superadmin,
        email_verified=True,
        phone="+91 90000 00000",
        org_id=STUDIO_SUNNY_ORG_ID,
    )
    if first == "Sunny":
        user.display_name = "Sunny"
        user.phone = "+91 98480 11221"
    db.add(user)
    db.flush()
    emp = Employee(
        user_id=user.id,
        org_id=STUDIO_SUNNY_ORG_ID,
        department_id=dept.id if dept else None,
        job_title=title,
        employment_type="full_time",
        location=location,
        joining_date=joining or date(2023, 4, 1),
        salary=Decimal(salary),
        salary_currency="INR",
        weekly_capacity_hours=40,
        availability=availability,
        skills=skills,
        leave_balance_days=16,
    )
    db.add(emp)
    db.flush()
    return user, emp


def ensure_docs(db) -> None:
    if db.scalar(select(Document.id).limit(1)):
        return
    sunny = db.scalar(select(User).where(User.email == "sunny@studiosunny.com"))
    if not sunny:
        return
    muttonly = db.scalar(select(Project).where(Project.slug == "muttonly-commerce"))
    company = Document(
        title="Studio Sunny operating notes",
        slug="studio-sunny-operating-notes",
        kind="handbook",
        status="published",
        summary="How we run delivery, communication, and quality at HQ.",
        content={
            "type": "doc",
            "content": [
                {
                    "type": "heading",
                    "attrs": {"level": 2},
                    "content": [{"type": "text", "text": "Principles"}],
                },
                {
                    "type": "bulletList",
                    "content": [
                        {
                            "type": "listItem",
                            "content": [
                                {
                                    "type": "paragraph",
                                    "content": [{"type": "text", "text": "Ship small, ship often."}],
                                }
                            ],
                        },
                        {
                            "type": "listItem",
                            "content": [
                                {
                                    "type": "paragraph",
                                    "content": [{"type": "text", "text": "Write decisions where the work lives."}],
                                }
                            ],
                        },
                        {
                            "type": "listItem",
                            "content": [
                                {
                                    "type": "paragraph",
                                    "content": [{"type": "text", "text": "Client trust beats internal convenience."}],
                                }
                            ],
                        },
                    ],
                },
                {
                    "type": "heading",
                    "attrs": {"level": 2},
                    "content": [{"type": "text", "text": "Daily rhythm"}],
                },
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "type": "text",
                            "text": "Use My Desk for personal focus. Keep #general for company signal, project rooms for delivery.",
                        }
                    ],
                },
            ],
        },
        plain_text="Principles Ship small, ship often. Write decisions where the work lives. Client trust beats internal convenience. Daily rhythm Use My Desk for personal focus.",
        created_by_id=sunny.id,
        updated_by_id=sunny.id,
        org_id=STUDIO_SUNNY_ORG_ID,
    )
    brief = Document(
        title="Muttonly launch brief",
        slug="muttonly-launch-brief",
        kind="brief",
        status="published",
        summary="Launch checklist and open risks for Muttonly.",
        project_id=muttonly.id if muttonly else None,
        content={
            "type": "doc",
            "content": [
                {
                    "type": "heading",
                    "attrs": {"level": 2},
                    "content": [{"type": "text", "text": "Goal"}],
                },
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "type": "text",
                            "text": "Stable mobile checkout, WhatsApp order alerts, and admin visibility before go-live.",
                        }
                    ],
                },
                {
                    "type": "heading",
                    "attrs": {"level": 2},
                    "content": [{"type": "text", "text": "Open risks"}],
                },
                {
                    "type": "orderedList",
                    "content": [
                        {
                            "type": "listItem",
                            "content": [
                                {
                                    "type": "paragraph",
                                    "content": [{"type": "text", "text": "Mobile checkout edge cases on low-end Androids."}],
                                }
                            ],
                        },
                        {
                            "type": "listItem",
                            "content": [
                                {
                                    "type": "paragraph",
                                    "content": [{"type": "text", "text": "WhatsApp alert latency under peak load."}],
                                }
                            ],
                        },
                    ],
                },
            ],
        },
        plain_text="Goal Stable mobile checkout. Open risks Mobile checkout edge cases. WhatsApp alert latency.",
        created_by_id=sunny.id,
        updated_by_id=sunny.id,
        org_id=STUDIO_SUNNY_ORG_ID,
    )
    blank = Document(
        title="Meeting notes template",
        slug="meeting-notes-template",
        kind="template",
        status="draft",
        summary="Reusable agenda + decisions template.",
        content=EMPTY_DOC,
        plain_text="",
        created_by_id=sunny.id,
        updated_by_id=sunny.id,
        org_id=STUDIO_SUNNY_ORG_ID,
    )
    db.add_all([company, brief, blank])
    db.commit()


def ensure_files(db) -> None:
    if db.scalar(select(FileAsset.id).limit(1)):
        return
    sunny = db.scalar(select(User).where(User.email == "sunny@studiosunny.com"))
    if not sunny:
        return
    from app.services import storage as store

    muttonly = db.scalar(select(Project).where(Project.slug == "muttonly-commerce"))
    content = (
        "Studio Sunny HQ — sample asset\n"
        "Replace this with contracts, brand packs, and delivery deliverables.\n"
    ).encode("utf-8")
    key = store.build_storage_key(STUDIO_SUNNY_ORG_ID, "hq-readme.txt")
    store.write_bytes(key, content)
    db.add(
        FileAsset(
            name="HQ readme",
            original_name="hq-readme.txt",
            storage_key=key,
            mime_type="text/plain",
            size_bytes=len(content),
            kind="asset",
            notes="Starter file so the cabinet isn’t empty.",
            project_id=muttonly.id if muttonly else None,
            uploaded_by_id=sunny.id,
            org_id=STUDIO_SUNNY_ORG_ID,
        )
    )
    db.commit()


def ensure_chat(db) -> None:
    from app.models.chat import ChatChannelMember
    from app.models.project import Project, ProjectMember

    sunny = db.scalar(select(User).where(User.email == "sunny@studiosunny.com"))
    for slug, name, topic in (
        ("general", "General", "Company-wide"),
        ("engineering", "Engineering", "Build and ship"),
        ("muttonly", "Muttonly", "Client delivery room"),
    ):
        if not db.scalar(select(ChatChannel).where(ChatChannel.slug == slug)):
            db.add(ChatChannel(slug=slug, name=name, topic=topic, kind="channel", org_id=STUDIO_SUNNY_ORG_ID))
    db.flush()

    def _ensure_member(channel: ChatChannel, user_id) -> None:
        if not db.scalar(
            select(ChatChannelMember.id).where(
                ChatChannelMember.channel_id == channel.id,
                ChatChannelMember.user_id == user_id,
            )
        ):
            db.add(
                ChatChannelMember(
                    channel_id=channel.id,
                    user_id=user_id,
                    org_id=STUDIO_SUNNY_ORG_ID,
                )
            )

    general = db.scalar(select(ChatChannel).where(ChatChannel.slug == "general"))
    engineering = db.scalar(select(ChatChannel).where(ChatChannel.slug == "engineering"))
    muttonly_ch = db.scalar(select(ChatChannel).where(ChatChannel.slug == "muttonly"))

    active_users = db.scalars(select(User).where(User.deleted_at.is_(None), User.is_active.is_(True))).all()
    if general:
        for u in active_users:
            _ensure_member(general, u.id)
    if engineering:
        eng_roles = {"founder", "project_manager", "developer", "designer", "automation_engineer", "operations_manager"}
        for u in active_users:
            if u.role_key in eng_roles:
                _ensure_member(engineering, u.id)
    if muttonly_ch:
        project = db.scalar(select(Project).where(Project.slug == "muttonly-commerce"))
        if project:
            member_ids = set(
                db.scalars(select(ProjectMember.user_id).where(ProjectMember.project_id == project.id)).all()
            )
            if project.project_manager_id:
                member_ids.add(project.project_manager_id)
            for uid in member_ids:
                _ensure_member(muttonly_ch, uid)

    if sunny and general and not db.scalar(select(ChatMessage.id).where(ChatMessage.channel_id == general.id)):
        db.add(
            ChatMessage(
                channel_id=general.id,
                author_id=sunny.id,
                body="Morning — HQ chat is live. Keep it short and useful.",
                org_id=STUDIO_SUNNY_ORG_ID,
            )
        )
    db.commit()


def ensure_org(db) -> Organization:
    org = db.scalar(select(Organization).where(Organization.slug == "studio-sunny"))
    if org:
        return org
    org = db.get(Organization, STUDIO_SUNNY_ORG_ID)
    if org:
        return org
    org = default_org()
    db.add(org)
    db.flush()
    return org


def run() -> None:
    Base.metadata.create_all(bind=engine)
    ensure_schema(engine)
    db = SessionLocal()
    try:
        ensure_org(db)
        if db.scalar(select(User).where(User.email == "sunny@studiosunny.com")):
            ensure_chat(db)
            ensure_docs(db)
            ensure_files(db)
            print("Seed already applied. Demo login: sunny@studiosunny.com / SunnyHQ2026!")
            return

        founder_dept = get_or_create_dept(db, "Founder", "founder", "Leadership")
        ops = get_or_create_dept(db, "Operations", "operations", "Delivery and client operations")
        eng = get_or_create_dept(db, "Engineering", "engineering", "Product and custom software")
        design = get_or_create_dept(db, "Design", "design", "Brand, product, and UX")
        auto = get_or_create_dept(db, "Automation", "automation", "AI, WhatsApp, and workflow systems")
        sales = get_or_create_dept(db, "Sales", "sales", "New business and partnerships")
        marketing = get_or_create_dept(db, "Marketing", "marketing", "SEO and growth")
        finance = get_or_create_dept(db, "Finance", "finance", "Invoicing and commercial control")

        sunny, _ = create_person(
            db,
            email="sunny@studiosunny.com",
            first="Sunny",
            last="",
            role="founder",
            title="Founder",
            dept=founder_dept,
            location="Hyderabad",
            salary=0,
            skills=["Leadership", "Product", "Sales"],
            joining=date(2022, 1, 10),
            superadmin=True,
        )
        arjun, _ = create_person(
            db,
            email="arjun@studiosunny.com",
            first="Arjun",
            last="Mehta",
            role="project_manager",
            title="Project Manager",
            dept=ops,
            location="Hyderabad",
            salary=95000,
            skills=["Delivery", "Client comms", "Scoping"],
            joining=date(2023, 6, 12),
        )
        rahul, _ = create_person(
            db,
            email="rahul@studiosunny.com",
            first="Rahul",
            last="Kumar",
            role="developer",
            title="Full Stack Developer",
            dept=eng,
            location="Hyderabad",
            salary=110000,
            skills=["Next.js", "Python", "PostgreSQL", "Stripe"],
            joining=date(2023, 8, 1),
            availability="busy",
        )
        priya, _ = create_person(
            db,
            email="priya@studiosunny.com",
            first="Priya",
            last="Sharma",
            role="designer",
            title="UI/UX Designer",
            dept=design,
            location="Bengaluru",
            salary=88000,
            skills=["Figma", "Design systems", "Brand"],
            joining=date(2024, 1, 15),
        )
        kiran, _ = create_person(
            db,
            email="kiran@studiosunny.com",
            first="Kiran",
            last="Reddy",
            role="automation_engineer",
            title="Automation Engineer",
            dept=auto,
            location="Hyderabad",
            salary=105000,
            skills=["n8n", "WhatsApp API", "OpenAI", "Zapier"],
            joining=date(2024, 3, 4),
        )

        muttonly = Client(
            business_name="Muttonly",
            slug="muttonly",
            primary_contact_name="Imran Shaik",
            phone="+91 98490 22110",
            whatsapp="+91 98490 22110",
            email="imran@muttonly.com",
            location="Hyderabad",
            website="https://muttonly.com",
            industry="Food & Q-commerce",
            lead_source="Inbound website",
            account_manager_id=sunny.id,
            status="active",
            lifetime_value=Decimal("420000"),
            notes="Premium meat delivery brand. Launching new checkout and admin ops console.",
            onboarding_step=8,
            onboarding_complete=True,
        )
        patel = Client(
            business_name="Patel Gems",
            slug="patel-gems",
            primary_contact_name="Nisha Patel",
            phone="+91 98250 11882",
            whatsapp="+91 98250 11882",
            email="nisha@patelgems.in",
            location="Surat",
            website="https://patelgems.in",
            industry="Jewellery",
            lead_source="Referral",
            account_manager_id=arjun.id,
            status="active",
            lifetime_value=Decimal("185000"),
            notes="Family jewellery house. Awaiting product photography and copy for catalogue.",
            onboarding_step=5,
            onboarding_complete=False,
        )
        agro = Client(
            business_name="M&M Agro Foods",
            slug="mm-agro-foods",
            primary_contact_name="Manoj Reddy",
            phone="+91 90001 33445",
            whatsapp="+91 90001 33445",
            email="manoj@mmagrofoods.com",
            location="Vijayawada",
            website="https://mmagrofoods.com",
            industry="Agri-processing",
            lead_source="Cold outreach",
            account_manager_id=sunny.id,
            status="active",
            lifetime_value=Decimal("96000"),
            notes="B2B agro exporter. Needs bilingual brochure site + enquiry automation.",
            onboarding_step=4,
            onboarding_complete=False,
        )
        db.add_all([muttonly, patel, agro])
        db.flush()

        p_muttonly = Project(
            name="Muttonly Commerce Platform",
            slug="muttonly-commerce",
            client_id=muttonly.id,
            project_manager_id=arjun.id,
            project_type="E-commerce",
            description="Storefront, checkout, and internal ops dashboard for Muttonly’s same-day meat delivery.",
            start_date=TODAY - timedelta(days=62),
            target_completion_date=TODAY + timedelta(days=2),
            budget=Decimal("320000"),
            status="testing",
            health="at_risk",
            priority="urgent",
            progress=78,
            tech_stack=["Next.js", "FastAPI", "PostgreSQL", "Razorpay", "AWS"],
            repository_url="https://github.com/studiosunny/muttonly",
            staging_url="https://staging.muttonly.com",
            production_url="https://muttonly.com",
            hours_spent=286,
            is_pinned=True,
        )
        p_patel = Project(
            name="Patel Gems Digital Catalogue",
            slug="patel-gems-catalogue",
            client_id=patel.id,
            project_manager_id=arjun.id,
            project_type="Website",
            description="Jewellery catalogue, appointment booking, and WhatsApp enquiry flow.",
            start_date=TODAY - timedelta(days=28),
            target_completion_date=TODAY + timedelta(days=24),
            budget=Decimal("145000"),
            status="design",
            health="needs_attention",
            priority="high",
            progress=34,
            tech_stack=["Next.js", "Sanity", "WhatsApp Cloud API"],
            staging_url="https://patel-gems.studio-sunny.dev",
            hours_spent=74,
            is_pinned=True,
        )
        p_agro = Project(
            name="M&M Agro Corporate Site",
            slug="mm-agro-site",
            client_id=agro.id,
            project_manager_id=arjun.id,
            project_type="Website",
            description="Bilingual corporate site with export enquiry forms and product specs.",
            start_date=TODAY - timedelta(days=18),
            target_completion_date=TODAY + timedelta(days=36),
            budget=Decimal("98000"),
            status="development",
            health="healthy",
            priority="medium",
            progress=41,
            tech_stack=["Next.js", "Tailwind", "Resend"],
            hours_spent=52,
        )
        db.add_all([p_muttonly, p_patel, p_agro])
        db.flush()

        memberships = [
            (p_muttonly, sunny, "founder"),
            (p_muttonly, arjun, "project_manager"),
            (p_muttonly, rahul, "developer"),
            (p_muttonly, priya, "designer"),
            (p_muttonly, kiran, "automation"),
            (p_patel, sunny, "founder"),
            (p_patel, arjun, "project_manager"),
            (p_patel, priya, "designer"),
            (p_patel, rahul, "developer"),
            (p_agro, arjun, "project_manager"),
            (p_agro, rahul, "developer"),
            (p_agro, kiran, "automation"),
        ]
        for project, person, role in memberships:
            db.add(ProjectMember(project_id=project.id, user_id=person.id, role_on_project=role))

        phases = [
            ("Discovery", "completed"),
            ("Planning", "completed"),
            ("Design", "completed"),
            ("Development", "completed"),
            ("Testing", "in_progress"),
            ("Client Review", "upcoming"),
            ("Deployment", "upcoming"),
            ("Launch", "upcoming"),
            ("Maintenance", "upcoming"),
        ]
        for i, (phase, st) in enumerate(phases):
            db.add(
                ProjectMilestone(
                    project_id=p_muttonly.id,
                    title=phase,
                    phase=phase.lower().replace(" ", "_"),
                    owner_id=arjun.id if i < 6 else rahul.id,
                    start_date=TODAY - timedelta(days=60 - i * 7),
                    due_date=TODAY - timedelta(days=53 - i * 7) if st != "upcoming" else TODAY + timedelta(days=i),
                    status=st,
                    sort_order=i,
                    deliverables=[f"{phase} sign-off"] if st == "completed" else [],
                )
            )

        db.add(
            ProjectMilestone(
                project_id=p_patel.id,
                title="Brand & information architecture",
                phase="design",
                owner_id=priya.id,
                due_date=TODAY + timedelta(days=6),
                status="in_progress",
                sort_order=0,
                deliverables=["Homepage", "Catalogue templates"],
            )
        )

        tasks = [
            Task(
                title="Finish Muttonly admin dashboard",
                description="Complete orders, inventory, and delivery-slot screens before launch QA.",
                project_id=p_muttonly.id,
                assignee_id=rahul.id,
                reviewer_id=arjun.id,
                created_by_id=arjun.id,
                priority="urgent",
                status="in_progress",
                due_date=TODAY,
                start_date=TODAY - timedelta(days=4),
                estimated_minutes=480,
                tags=["frontend", "launch"],
                checklist=[
                    {"id": "1", "label": "Orders table filters", "done": True},
                    {"id": "2", "label": "Inventory adjustments", "done": True},
                    {"id": "3", "label": "Delivery slots", "done": False},
                ],
            ),
            Task(
                title="Fix mobile checkout",
                description="Address payment retry and address-form overflow on iOS Safari.",
                project_id=p_muttonly.id,
                assignee_id=rahul.id,
                reviewer_id=arjun.id,
                created_by_id=arjun.id,
                priority="urgent",
                status="todo",
                due_date=TODAY,
                estimated_minutes=180,
                tags=["mobile", "checkout"],
            ),
            Task(
                title="Review Patel Gems client feedback",
                description="Nisha requested warmer jewellery photography treatment and larger type on PDP.",
                project_id=p_patel.id,
                assignee_id=priya.id,
                reviewer_id=arjun.id,
                created_by_id=arjun.id,
                priority="high",
                status="todo",
                due_date=TODAY,
                estimated_minutes=120,
                tags=["design", "feedback"],
            ),
            Task(
                title="Muttonly launch QA checklist",
                description="Run staging smoke tests across storefront, cart, Razorpay, and admin.",
                project_id=p_muttonly.id,
                assignee_id=arjun.id,
                created_by_id=sunny.id,
                priority="high",
                status="todo",
                due_date=TODAY + timedelta(days=1),
                tags=["qa", "launch"],
            ),
            Task(
                title="WhatsApp order alerts for Muttonly",
                description="Send ops channel a summary when a prepaid order is confirmed.",
                project_id=p_muttonly.id,
                assignee_id=kiran.id,
                reviewer_id=arjun.id,
                created_by_id=arjun.id,
                priority="high",
                status="in_progress",
                due_date=TODAY + timedelta(days=1),
                tags=["automation"],
            ),
            Task(
                title="Homepage redesign polish",
                description="Apply final type scale and product photography treatment.",
                project_id=p_patel.id,
                assignee_id=priya.id,
                created_by_id=arjun.id,
                priority="medium",
                status="review",
                due_date=TODAY + timedelta(days=2),
                tags=["design"],
            ),
            Task(
                title="Awaiting Patel Gems product copy",
                description="Blocked on client content for 42 SKUs.",
                project_id=p_patel.id,
                assignee_id=arjun.id,
                created_by_id=arjun.id,
                priority="high",
                status="blocked",
                due_date=TODAY + timedelta(days=3),
                tags=["content"],
            ),
            Task(
                title="Agro enquiry form → CRM",
                description="Pipe M&M Agro form submissions into HQ leads with source tagging.",
                project_id=p_agro.id,
                assignee_id=kiran.id,
                created_by_id=arjun.id,
                priority="medium",
                status="todo",
                due_date=TODAY + timedelta(days=5),
                tags=["automation"],
            ),
            Task(
                title="Build M&M product spec templates",
                description="Create reusable spec blocks for rice, spices, and oil seeds.",
                project_id=p_agro.id,
                assignee_id=rahul.id,
                created_by_id=arjun.id,
                priority="medium",
                status="in_progress",
                due_date=TODAY + timedelta(days=6),
                tags=["frontend"],
            ),
            Task(
                title="Razorpay webhook hardening",
                description="Idempotent payment events + failed-capture retry.",
                project_id=p_muttonly.id,
                assignee_id=rahul.id,
                created_by_id=sunny.id,
                priority="high",
                status="review",
                due_date=TODAY + timedelta(days=1),
                tags=["backend", "payments"],
            ),
        ]
        db.add_all(tasks)
        db.flush()

        invoices = [
            Invoice(
                number="SS-1021",
                client_id=muttonly.id,
                project_id=p_muttonly.id,
                amount=Decimal("160000"),
                tax=Decimal("28800"),
                currency="INR",
                due_date=TODAY - timedelta(days=20),
                issued_date=TODAY - timedelta(days=50),
                status="paid",
                payment_method="NEFT",
            ),
            Invoice(
                number="SS-1024",
                client_id=muttonly.id,
                project_id=p_muttonly.id,
                amount=Decimal("125000"),
                tax=Decimal("22500"),
                currency="INR",
                due_date=TODAY - timedelta(days=2),
                issued_date=TODAY - timedelta(days=18),
                status="paid",
                payment_method="Razorpay",
            ),
            Invoice(
                number="SS-1028",
                client_id=patel.id,
                project_id=p_patel.id,
                amount=Decimal("48000"),
                tax=Decimal("8640"),
                currency="INR",
                due_date=TODAY + timedelta(days=5),
                issued_date=TODAY - timedelta(days=10),
                status="sent",
            ),
            Invoice(
                number="SS-1030",
                client_id=agro.id,
                project_id=p_agro.id,
                amount=Decimal("32000"),
                tax=Decimal("5760"),
                currency="INR",
                due_date=TODAY - timedelta(days=4),
                issued_date=TODAY - timedelta(days=19),
                status="overdue",
            ),
        ]
        db.add_all(invoices)

        leads = [
            Lead(
                business_name="Coastal Dental Studio",
                contact_name="Dr. Ananya Rao",
                phone="+91 98850 22119",
                email="hello@coastaldental.in",
                industry="Healthcare",
                location="Visakhapatnam",
                requested_service="Website",
                estimated_value=Decimal("85000"),
                source="Website form",
                stage="new_lead",
                assigned_to_id=sunny.id,
                probability=20,
                notes="Wants appointment booking + Google reviews integration.",
            ),
            Lead(
                business_name="Nivaara Interiors",
                contact_name="Sneha Iyer",
                phone="+91 98190 33440",
                email="sneha@nivaara.co",
                industry="Interior design",
                location="Mumbai",
                requested_service="Custom Software",
                estimated_value=Decimal("240000"),
                source="Referral",
                stage="discovery_call",
                assigned_to_id=sunny.id,
                probability=45,
            ),
            Lead(
                business_name="GreenCart Wholesale",
                contact_name="Vikram Singh",
                email="vikram@greencart.in",
                industry="FMCG",
                location="Pune",
                requested_service="E-commerce",
                estimated_value=Decimal("310000"),
                source="LinkedIn",
                stage="proposal_sent",
                assigned_to_id=arjun.id,
                probability=60,
            ),
            Lead(
                business_name="Lumen Labs",
                contact_name="Ayesha Khan",
                email="ayesha@lumenlabs.ai",
                industry="SaaS",
                location="Bengaluru",
                requested_service="AI Automation",
                estimated_value=Decimal("180000"),
                source="Inbound website",
                stage="qualified",
                assigned_to_id=sunny.id,
                probability=50,
            ),
            Lead(
                business_name="Oak & Ember Cafe",
                contact_name="Rohit Das",
                industry="Hospitality",
                location="Hyderabad",
                requested_service="WhatsApp Automation",
                estimated_value=Decimal("42000"),
                source="Walk-in intro",
                stage="contacted",
                assigned_to_id=sunny.id,
                probability=25,
            ),
            Lead(
                business_name="Sutra Legal",
                contact_name="Meera Joshi",
                industry="Legal",
                location="Delhi",
                requested_service="Website",
                estimated_value=Decimal("95000"),
                source="Referral",
                stage="negotiation",
                assigned_to_id=sunny.id,
                probability=70,
            ),
            Lead(
                business_name="Aarogya Diagnostics",
                contact_name="Dr. Farhan Ali",
                industry="Healthcare",
                location="Hyderabad",
                requested_service="Custom Software",
                estimated_value=Decimal("400000"),
                source="Conference",
                stage="new_lead",
                assigned_to_id=arjun.id,
                probability=15,
            ),
            Lead(
                business_name="Kite School Online",
                contact_name="Neel Kapoor",
                industry="Edtech",
                location="Remote",
                requested_service="Mobile App",
                estimated_value=Decimal("275000"),
                source="Website form",
                stage="new_lead",
                assigned_to_id=sunny.id,
                probability=20,
            ),
            Lead(
                business_name="Harbor Freight Brokers",
                contact_name="Joseph Mathew",
                industry="Logistics",
                location="Kochi",
                requested_service="Digital Transformation",
                estimated_value=Decimal("150000"),
                source="Cold outreach",
                stage="lost",
                assigned_to_id=sunny.id,
                probability=0,
                notes="Chose an in-house team.",
            ),
        ]
        db.add_all(leads)

        activities = [
            Activity(
                actor_id=rahul.id,
                verb="completed",
                entity_type="task",
                project_id=p_muttonly.id,
                client_id=muttonly.id,
                summary="Rahul completed API integration",
                meta={},
            ),
            Activity(
                actor_id=priya.id,
                verb="uploaded",
                entity_type="file",
                project_id=p_patel.id,
                client_id=patel.id,
                summary="Priya uploaded homepage redesign",
                meta={},
            ),
            Activity(
                actor_id=arjun.id,
                verb="approved",
                entity_type="milestone",
                project_id=p_muttonly.id,
                client_id=muttonly.id,
                summary="Muttonly approved checkout flow",
                meta={},
            ),
            Activity(
                actor_id=sunny.id,
                verb="created",
                entity_type="lead",
                summary="New lead created from website",
                meta={"lead": "Coastal Dental Studio"},
            ),
            Activity(
                actor_id=None,
                verb="paid",
                entity_type="invoice",
                project_id=p_muttonly.id,
                client_id=muttonly.id,
                summary="Invoice #SS-1024 paid",
                meta={},
            ),
            Activity(
                actor_id=kiran.id,
                verb="updated",
                entity_type="task",
                project_id=p_muttonly.id,
                summary="Kiran started WhatsApp order alerts",
                meta={},
            ),
            Activity(
                actor_id=arjun.id,
                verb="created",
                entity_type="task",
                project_id=p_patel.id,
                summary="Arjun flagged Patel Gems content blocker",
                meta={},
            ),
        ]
        db.add_all(activities)

        notifications = [
            Notification(
                user_id=sunny.id,
                type="project_status",
                title="Muttonly is 2 days from launch",
                body="Testing is in progress. Mobile checkout still open.",
                href=f"/projects/{p_muttonly.id}",
                priority="high",
            ),
            Notification(
                user_id=sunny.id,
                type="invoice_overdue",
                title="Invoice SS-1030 is overdue",
                body="M&M Agro Foods · ₹32,000",
                href="/finance",
                priority="high",
            ),
            Notification(
                user_id=sunny.id,
                type="lead",
                title="New website lead",
                body="Coastal Dental Studio requested a website + booking flow.",
                href="/leads",
            ),
            Notification(
                user_id=rahul.id,
                type="task_assigned",
                title="Urgent: Finish Muttonly admin dashboard",
                body="Due today · assigned by Arjun",
                href="/desk",
                priority="high",
            ),
            Notification(
                user_id=priya.id,
                type="task_assigned",
                title="Review Patel Gems client feedback",
                body="Due today",
                href="/desk",
            ),
            Notification(
                user_id=arjun.id,
                type="client_request",
                title="Patel Gems awaiting content",
                body="Catalogue copy still outstanding for 42 SKUs.",
                href=f"/projects/{p_patel.id}",
                priority="high",
            ),
            Notification(
                user_id=kiran.id,
                type="task_assigned",
                title="WhatsApp order alerts for Muttonly",
                body="Due tomorrow",
                href="/desk",
            ),
        ]
        db.add_all(notifications)

        ensure_chat(db)
        ensure_docs(db)
        ensure_files(db)
        print("Seeded Studio Sunny HQ.")
        print("Demo accounts (password: SunnyHQ2026!):")
        print("  sunny@studiosunny.com          Founder")
        print("  arjun@studiosunny.com          Project Manager")
        print("  rahul@studiosunny.com          Developer")
        print("  priya@studiosunny.com          Designer")
        print("  kiran@studiosunny.com          Automation Engineer")
    finally:
        db.close()


if __name__ == "__main__":
    run()
