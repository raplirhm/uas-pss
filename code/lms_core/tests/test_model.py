# tests.py
from django.test import TestCase
from django.contrib.auth.models import User
from lms_core.models import Course, CourseMember, ROLE_OPTIONS

class CourseModelTest(TestCase):

    def setUp(self):
        # Menyiapkan data untuk pengujian
        self.user = User.objects.create_user(username='teacher1', password='password123')
        self.student = User.objects.create_user(username='student1', password='password123')
        self.course = Course.objects.create(
            name="Django for Beginners",
            description="Learn Django from scratch.",
            price=100,
            teacher=self.user
        )

    def test_course_creation(self):
        # Menguji apakah objek Course berhasil dibuat
        self.assertEqual(self.course.name, "Django for Beginners")
        self.assertEqual(self.course.description, "Learn Django from scratch.")
        self.assertEqual(self.course.price, 100)
        self.assertEqual(self.course.teacher, self.user)

    def test_course_str(self):
        # Menguji metode __str__
        self.assertEqual(str(self.course), "Django for Beginners")

    def test_is_member(self):
        # Menguji metode is_member
        # Sebelum menambahkan anggota, harusnya False
        self.assertFalse(self.course.is_member(self.student))

        # Menambahkan anggota ke kursus
        CourseMember.objects.create(course_id=self.course, user_id=self.student)

        # Setelah menambahkan anggota, harusnya True
        self.assertTrue(self.course.is_member(self.student))

class CourseMemberModelTest(TestCase):

    def setUp(self):
        # Menyiapkan data untuk pengujian
        self.user = User.objects.create_user(username='teacher1', password='password123')
        self.student = User.objects.create_user(username='student1', password='password123')
        self.course = Course.objects.create(
            name="Django for Beginners",
            description="Learn Django from scratch.",
            price=100,
            teacher=self.user
        )
        self.course_member = CourseMember.objects.create(
            course_id=self.course,
            user_id=self.student,
            roles='std'
        )

    def test_course_member_creation(self):
        # Menguji apakah objek CourseMember berhasil dibuat
        self.assertEqual(self.course_member.course_id, self.course)
        self.assertEqual(self.course_member.user_id, self.student)
        self.assertEqual(self.course_member.roles, 'std')

    def test_course_member_str(self):
        # Menguji metode __str__
        self.assertEqual(str(self.course_member), 
                         f"{self.course_member.id} {self.course_member.course_id} : {self.course_member.user_id}")

    def test_course_member_role_options(self):
        # Menguji pilihan peran
        self.assertIn(self.course_member.roles, dict(ROLE_OPTIONS).keys())