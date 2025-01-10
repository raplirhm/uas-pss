from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from lms_core.models import Course, CourseContent, Comment
import json

class NegativeAPITestCase(TestCase):

    base_url = '/api/v1/'

    def setUp(self):
        # Membuat pengguna untuk pengujian
        self.teacher = User.objects.create_user(username='teacher', password='password123')
        self.student = User.objects.create_user(username='student', password='password123')
        self.student2 = User.objects.create_user(username='student2', password='password123')

        # Membuat kursus untuk pengujian
        self.course = Course.objects.create(
            name="Django for Beginners",
            description="Learn Django from scratch.",
            price=100,
            teacher=self.teacher
        )
        
        login = self.client.post(self.base_url+'auth/sign-in', 
                                 data=json.dumps({'username': 'student', 'password': 'password123'}),
                                 content_type='application/json')
        self.student_token = login.json()['access']
        login = self.client.post(self.base_url+'auth/sign-in', 
                                 data=json.dumps({'username': 'student2', 'password': 'password123'}),
                                 content_type='application/json')
        self.student2_token = login.json()['access']

    def test_create_course_without_login(self):
        # Menguji bahwa pengguna yang belum login tidak dapat membuat kursus
        response = self.client.post(self.base_url+'courses', data={
            'name': 'New Course',
            'description': 'New Course Description',
            'price': 150,
            'file': {'image': None}
        }, format='multipart') 
        self.assertEqual(response.status_code, 401)  # Unauthorized

    def test_update_course_as_non_teacher(self):
        # Menguji bahwa pengguna yang bukan pengajar tidak dapat memperbarui kursus
        response = self.client.post(f'{self.base_url}courses/{self.course.id}', data={
            'name': 'Updated Course',
            'description': 'Updated Description',
            'price': 200,
            'file': {'image': None}
        }, format='multipart', **{'HTTP_AUTHORIZATION': 'Bearer ' + str(self.student_token)}) 
        
        self.assertEqual(response.status_code, 401)  # Unauthorized

    def test_create_comment_as_non_member(self):
        # Menguji bahwa pengguna yang bukan anggota kursus tidak dapat memposting komentar
        content = CourseContent.objects.create(course_id=self.course, 
                                               name="Content Title", 
                                               description="Content Description")
        self.client.post(f'{self.base_url}courses/{self.course.id}/enroll', 
                            **{'HTTP_AUTHORIZATION': 'Bearer ' + str(self.student_token)})
        response = self.client.post(f'{self.base_url}contents/{content.id}/comments', 
                                    data={'comment': 'This is a comment'}, 
                                    content_type='application/json',
                                    **{'HTTP_AUTHORIZATION': 'Bearer ' + str(self.student2_token)})
        self.assertEqual(response.status_code, 401)  # Unauthorized
        self.assertIn("You are not authorized to create comment in this content", response.json().get("error"))