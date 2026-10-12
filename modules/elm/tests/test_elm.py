from django.test import TestCase, Client
from django.urls import reverse
from modules.elm.models import ELMModel

class ELMTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse('elm-list')
        ELMModel.objects.create(name='Test Model', description='This is a test model.')

    def test_elm_list(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)
