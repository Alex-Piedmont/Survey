from datetime import datetime

from pydantic import BaseModel, EmailStr


class DashboardStats(BaseModel):
    total_users: int
    total_instructors: int
    total_admins: int
    total_courses: int
    total_active_sessions: int
    total_submissions: int
    recent_courses: list["AdminCourseItem"]


class AdminCourseItem(BaseModel):
    id: str
    name: str
    term: str | None
    instructor_email: str
    section_count: int
    student_count: int

    model_config = {"from_attributes": True}


class AdminUserItem(BaseModel):
    email: EmailStr
    display_name: str | None = None
    is_admin: bool
    is_instructor: bool
    course_count: int
    created_at: datetime


class AdminUserDetail(BaseModel):
    email: EmailStr
    display_name: str | None = None
    is_admin: bool
    is_instructor: bool
    created_at: datetime
    enrollments: list[dict]


class AdminToggle(BaseModel):
    enabled: bool


class InstructorCreate(BaseModel):
    email: EmailStr


class InstructorCreateResponse(BaseModel):
    email: EmailStr
    display_name: str | None = None
    is_instructor: bool
    created: bool


class TAAssign(BaseModel):
    ta_email: EmailStr


class TAAssignResponse(BaseModel):
    instructor_email: str
    ta_email: str
    sections_enrolled: int


class TAItem(BaseModel):
    ta_email: str
    display_name: str | None = None
    created_at: datetime
    created_by: str


class InstructorItem(BaseModel):
    email: EmailStr
    display_name: str | None = None
    course_count: int
    ta_count: int
