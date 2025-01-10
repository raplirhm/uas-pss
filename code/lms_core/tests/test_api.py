from django.test import TestCase
from django.contrib.auth.models import User
from lms_core.models import Course, CourseMember, CourseContent, Comment
from lms_core.api import apiv1
import json

class APITestCase(TestCase):

    base_url = '/api/v1/'

    def setUp(self):
        self.teacher = User.objects.create_user(username='teacher', password='password123')
        self.student = User.objects.create_user(username='student', password='password123')
        
        self.course = Course.objects.create(
            name="Django for Beginners",
            description="Learn Django from scratch.",
            price=100,
            teacher=self.teacher
        )

        login = self.client.post(self.base_url+'auth/sign-in', 
                                 data=json.dumps({'username': 'teacher', 'password': 'password123'}),
                                 content_type='application/json')
        self.token = login.json()['access']
        login = self.client.post(self.base_url+'auth/sign-in', 
                                 data=json.dumps({'username': 'student', 'password': 'password123'}),
                                 content_type='application/json')
        self.student_token = login.json()['access']

    def test_list_courses(self):
        response = self.client.get(f'{self.base_url}courses')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()['items']), 1)

    def test_create_course(self):
        response = self.client.post(self.base_url+'courses', data={
            'name': 'New Course',
            'description': 'New Course Description',
            'price': 150,
            'file': {'image': None}
        }, format='multipart', **{'HTTP_AUTHORIZATION': 'Bearer ' + str(self.token)}) 
        # print(response.request)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['name'], 'New Course')

    def test_update_course(self):
        response = self.client.post(f'{self.base_url}courses/{self.course.id}', data={
            'name': 'Updated Course',
            'description': 'Updated Description',
            'price': 200,
            'file': {'image': None}
        }, format='multipart', **{'HTTP_AUTHORIZATION': 'Bearer ' + str(self.token)}) 
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['name'], 'Updated Course')

    def test_enroll_course(self):
        response = self.client.post(f'{self.base_url}courses/{self.course.id}/enroll', 
                                    **{'HTTP_AUTHORIZATION': 'Bearer ' + str(self.student_token)}) 
        self.assertEqual(response.status_code, 200)
        self.assertTrue(CourseMember.objects.filter(course_id=self.course, user_id=self.student).exists())

    def test_create_content_comment(self):
        content = CourseContent.objects.create(course_id=self.course, 
                                               name="Content Title", 
                                               description="Content Description")
        self.client.post(f'{self.base_url}courses/{self.course.id}/enroll', 
                            **{'HTTP_AUTHORIZATION': 'Bearer ' + str(self.student_token)})
        response = self.client.post(f'{self.base_url}contents/{content.id}/comments', 
                                    data={'comment': 'This is a comment'}, 
                                    content_type='application/json',
                                    **{'HTTP_AUTHORIZATION': 'Bearer ' + str(self.student_token)})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['comment'], 'This is a comment')

    def test_delete_comment(self):
        content = CourseContent.objects.create(course_id=self.course, 
                                               name="Content Title", 
                                               description="Content Description")
        self.client.post(f'{self.base_url}courses/{self.course.id}/enroll', 
                            **{'HTTP_AUTHORIZATION': 'Bearer ' + str(self.student_token)})
        response = self.client.post(f'{self.base_url}contents/{content.id}/comments', 
                                    data={'comment': 'This is a comment'}, 
                                    content_type='application/json',
                                    **{'HTTP_AUTHORIZATION': 'Bearer ' + str(self.student_token)})
        comment_id = response.json()['id']
        response = self.client.delete(f'{self.base_url}comments/{comment_id}', 
                                    **{'HTTP_AUTHORIZATION': 'Bearer ' + str(self.student_token)})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Comment.objects.filter(id=comment_id).exists())
