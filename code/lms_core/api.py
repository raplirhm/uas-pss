from ninja import NinjaAPI, UploadedFile, File, Form
from ninja.responses import Response
from lms_core.schema import CourseSchemaOut, CourseMemberOut, CourseSchemaIn
from lms_core.schema import CourseContentMini, CourseContentFull
from lms_core.schema import CourseCommentOut, CourseCommentIn
from lms_core.models import Course, CourseMember, CourseContent, Comment
from ninja_simple_jwt.auth.views.api import mobile_auth_router
from ninja_simple_jwt.auth.ninja_auth import HttpJwtAuth
from ninja.pagination import paginate, PageNumberPagination

from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password
from lms_core.schema import UserRegisterSchema

from .models import CompletionTracking


apiv1 = NinjaAPI()
apiv1.add_router("/auth/", mobile_auth_router)
apiAuth = HttpJwtAuth()

@apiv1.get("/hello")
def hello(request):
    return "Hello World"

# - paginate list_courses
@apiv1.get("/courses", response=list[CourseSchemaOut])
@paginate(PageNumberPagination, page_size=10)
def list_courses(request):
    courses = Course.objects.select_related('teacher').all()
    return courses

# - my courses
@apiv1.get("/mycourses", auth=apiAuth, response=list[CourseMemberOut])
def my_courses(request):
    user = User.objects.get(id=request.user.id)
    courses = CourseMember.objects.select_related('user_id', 'course_id').filter(user_id=user)
    return courses

# - create course
@apiv1.post("/courses", auth=apiAuth, response={201:CourseSchemaOut})
def create_course(request, data: Form[CourseSchemaIn], image: UploadedFile = File(None)):
    user = User.objects.get(id=request.user.id)
    course = Course(
        name=data.name,
        description=data.description,
        price=data.price,
        image=image,
        teacher=user
    )

    if image:
        course.image.save(image.name, image)

    course.save()
    return 201, course

# - update course
@apiv1.post("/courses/{course_id}", auth=apiAuth, response=CourseSchemaOut)
def update_course(request, course_id: int, data: Form[CourseSchemaIn], image: UploadedFile = File(None)):
    if request.user.id != Course.objects.get(id=course_id).teacher.id:
        message = {"error": "Anda tidak diijinkan update course ini"}
        return Response(message, status=401)
    
    course = Course.objects.get(id=course_id)
    course.name = data.name
    course.description = data.description
    course.price = data.price
    if image:
        course.image.save(image.name, image)
    course.save()
    return course

# - detail course
@apiv1.get("/courses/{course_id}", response=CourseSchemaOut)
def detail_course(request, course_id: int):
    course = Course.objects.select_related('teacher').get(id=course_id)
    return course

# - list content course
@apiv1.get("/courses/{course_id}/contents", response=list[CourseContentMini])
def list_content_course(request, course_id: int):
    contents = CourseContent.objects.filter(course_id=course_id)
    return contents

# - detail content course
@apiv1.get("/courses/{course_id}/contents/{content_id}", response=CourseContentFull)
def detail_content_course(request, course_id: int, content_id: int):
    content = CourseContent.objects.get(id=content_id)
    return content

# - enroll course
@apiv1.post("/courses/{course_id}/enroll", auth=apiAuth, response=CourseMemberOut)
def enroll_course(request, course_id: int):
    user = User.objects.get(id=request.user.id)
    course = Course.objects.get(id=course_id)
    course_member = CourseMember(course_id=course, user_id=user, roles="std")
    course_member.save()
    # print(course_member)
    return course_member

# - list content comment
@apiv1.get("/contents/{content_id}/comments", auth=apiAuth, response=list[CourseContentMini])
def list_content_comment(request, content_id: int):
    comments = CourseContent.objects.filter(course_id=content_id)
    return comments

# - create content comment
@apiv1.post("/contents/{content_id}/comments", auth=apiAuth, response={201: CourseCommentOut})
def create_content_comment(request, content_id: int, data: CourseCommentIn):
    user = User.objects.get(id=request.user.id)
    content = CourseContent.objects.get(id=content_id)

    if not content.course_id.is_member(user):
        message =  {"error": "You are not authorized to create comment in this content"}
        return Response(message, status=401)
    
    member = CourseMember.objects.get(course_id=content.course_id, user_id=user)
    
    comment = Comment(
        content_id=content,
        member_id=member,
        comment=data.comment
    )
    comment.save()
    return 201, comment

# - delete content comment
@apiv1.delete("/comments/{comment_id}", auth=apiAuth)
def delete_comment(request, comment_id: int):
    comment = Comment.objects.get(id=comment_id)
    if comment.member_id.user_id.id != request.user.id:
        return {"error": "You are not authorized to delete this comment"}
    comment.delete()
    return {"message": "Comment deleted"}   

# - register
@apiv1.post("/register", response={201: dict, 400: dict})
def register(request, data: UserRegisterSchema):
    if User.objects.filter(username=data.username).exists():
        return Response({"error": "Username already exists"}, status=400)
    if User.objects.filter(email=data.email).exists():
        return Response({"error": "Email already exists"}, status=400)

    user = User.objects.create(
        username=data.username,
        password=make_password(data.password),
        email=data.email,
        first_name=data.first_name,
        last_name=data.last_name
    )
    return 201, {"message": "User registered successfully"}

# - batch enroll students
@apiv1.post("/courses/{course_id}/batch-enroll", response={201: dict, 400: dict})
def batch_enroll_students(request, course_id: int, data: List[int]):
    user = User.objects.get(id=request.user.id)
    course = Course.objects.get(id=course_id)

    if not course.is_owner(user):
        return Response({"error": "You are not authorized to enroll students in this course"}, status=401)

    students = User.objects.filter(id__in=data)
    if not students.exists():
        return Response({"error": "No valid students found"}, status=400)

    for student in students:
        CourseMember.objects.create(course_id=course, user_id=student)

    return 201, {"message": "Students enrolled successfully"}

# - content comment moderation
@apiv1.put("/comments/{comment_id}/moderate", auth=apiAuth)
def moderate_comment(request, comment_id: int, data: dict):
    comment = Comment.objects.get(id=comment_id)
    course = comment.content.course

    if not course.is_owner(request.user):
        return {"error": "You are not authorized to moderate this comment"}

    comment.is_moderated = data.get("is_moderated", True)
    comment.save()
    return {"message": "Comment moderated successfully"}

# - user activity dashboard
@apiv1.get("/user/{user_id}/activity", auth=apiAuth)
def user_activity_dashboard(request, user_id: int):
    user = User.objects.get(id=user_id)

    courses_as_student = CourseMember.objects.filter(user_id=user).count()
    courses_created = Course.objects.filter(owner=user).count()
    comments_written = Comment.objects.filter(user=user).count()
    content_completed = ContentCompletion.objects.filter(user=user).count() if hasattr(ContentCompletion, 'objects') else 0

    return {
        "courses_as_student": courses_as_student,
        "courses_created": courses_created,
        "comments_written": comments_written,
        "content_completed": content_completed
    }

# - course analytics
@apiv1.get("/course/{course_id}/analytics", auth=apiAuth)
def course_analytics(request, course_id: int):
    course = Course.objects.get(id=course_id)

    if not course.is_owner(request.user):
        return {"error": "You are not authorized to view this course analytics"}

    member_count = CourseMember.objects.filter(course_id=course).count()
    content_count = Content.objects.filter(course_id=course).count()
    comment_count = Comment.objects.filter(content__course=course).count()
    feedback_count = Feedback.objects.filter(course_id=course).count() if hasattr(Feedback, 'objects') else 0

    return {
        "member_count": member_count,
        "content_count": content_count,
        "comment_count": comment_count,
        "feedback_count": feedback_count
    }

# - content scheduling
@apiv1.get("/course/{course_id}/contents", auth=apiAuth)
def list_course_contents(request, course_id: int):
    course = Course.objects.get(id=course_id)

    if not course.is_owner(request.user) and not course.is_member(request.user):
        return {"error": "You are not authorized to view this course contents"}

    now = datetime.now()
    contents = Content.objects.filter(course=course, release_time__lte=now)

    return {
        "contents": [
            {
                "id": content.id,
                "title": content.title,
                "description": content.description,
                "release_time": content.release_time
            }
            for content in contents
        ]
    }

# Completion tracking
@apiv1.post("/course/{course_id}/content/{content_id}/complete", auth=apiAuth)
def mark_content_complete(request, course_id: int, content_id: int):
    course = Course.objects.get(id=course_id)
    content = Content.objects.get(id=content_id, course=course)

    if not course.is_member(request.user):
        return {"error": "You are not authorized to complete this content"}

    CompletionTracking.objects.get_or_create(student=request.user, content=content)
    return {"success": "Content marked as completed"}

# Show completion
@apiv1.get("/course/{course_id}/completions", auth=apiAuth)
def list_completions(request, course_id: int):
    course = Course.objects.get(id=course_id)

    if not course.is_member(request.user):
        return {"error": "You are not authorized to view completions for this course"}

    completions = CompletionTracking.objects.filter(student=request.user, content__course=course)
    return {
        "completions": [
            {
                "content_id": completion.content.id,
                "completed_at": completion.completed_at
            }
            for completion in completions
        ]
    }

# Delete completion
@apiv1.delete("/course/{course_id}/content/{content_id}/complete", auth=apiAuth)
def delete_completion(request, course_id: int, content_id: int):
    course = Course.objects.get(id=course_id)
    content = Content.objects.get(id=content_id, course=course)

    if not course.is_member(request.user):
        return {"error": "You are not authorized to delete this completion"}

    CompletionTracking.objects.filter(student=request.user, content=content).delete()
    return {"success": "Completion deleted"}

# Show Profile
@apiv1.get("/user/{user_id}/profile", auth=apiAuth)
def show_profile(request, user_id: int):
    user = User.objects.get(id=user_id)
    courses_joined = Course.objects.filter(members=user)
    courses_created = Course.objects.filter(creator=user)

    return {
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email,
        "phone": user.phone,
        "description": user.description,
        "profile_picture": user.profile_picture.url if user.profile_picture else None,
        "courses_joined": [
            {
                "id": course.id,
                "title": course.title,
                "description": course.description
            }
            for course in courses_joined
        ],
        "courses_created": [
            {
                "id": course.id,
                "title": course.title,
                "description": course.description
            }
            for course in courses_created
        ]
    }

# Edit Profile
@apiv1.put("/user/profile", auth=apiAuth)
def edit_profile(request):
    user = request.user
    data = request.json

    user.first_name = data.get("first_name", user.first_name)
    user.last_name = data.get("last_name", user.last_name)
    user.email = data.get("email", user.email)
    user.phone = data.get("phone", user.phone)
    user.description = data.get("description", user.description)
    
    if "profile_picture" in data:
        user.profile_picture = data["profile_picture"]

    user.save()

    return {"success": "Profile updated successfully"}

# Add Bookmark
@apiv1.post("/user/bookmark", auth=apiAuth)
def add_bookmark(request):
    user = request.user
    data = request.json
    course_content_id = data.get("course_content_id")

    if not course_content_id:
        return {"error": "Course content ID is required"}, 400

    course_content = CourseContent.objects.get(id=course_content_id)
    if not course_content:
        return {"error": "Course content not found"}, 404

    bookmark = Bookmark.objects.create(user=user, course_content=course_content)
    bookmark.save()

    return {"success": "Bookmark added successfully"}

# Show Bookmarks
@apiv1.get("/user/bookmarks", auth=apiAuth)
def show_bookmarks(request):
    user = request.user
    bookmarks = Bookmark.objects.filter(user=user)

    bookmarks_data = [
        {
            "id": bookmark.id,
            "course": {
                "id": bookmark.course_content.course.id,
                "title": bookmark.course_content.course.title,
            },
            "content": {
                "id": bookmark.course_content.id,
                "title": bookmark.course_content.title,
                "description": bookmark.course_content.description,
            }
        }
        for bookmark in bookmarks
    ]

    return {"bookmarks": bookmarks_data}

# Delete Bookmark
@apiv1.delete("/user/bookmark/{bookmark_id}", auth=apiAuth)
def delete_bookmark(request, bookmark_id):
    user = request.user
    try:
        bookmark = Bookmark.objects.get(id=bookmark_id, user=user)
        bookmark.delete()
        return {"success": "Bookmark deleted successfully"}
    except Bookmark.DoesNotExist:
        return {"error": "Bookmark not found"}, 404
