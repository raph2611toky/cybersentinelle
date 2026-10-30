"""Tests à lancer sur Kali: python -m pytest tests/test_translation_queue.py -q"""
from unittest.mock import patch
from django.test import TestCase
from rest_framework.exceptions import ValidationError
from apps.content_api.models import Tantara
from apps.content_api.serializers import TantaraEditorSerializer
from apps.translation.models import TranslationJob
from apps.translation.services import prime_graph,job_summary,ensure_ready


class TranslationQueueTests(TestCase):
    def story_payload(self):
        return {
            'slug':'exemple-22h47','numero':'98',
            'titre_fr':'Le message inconnu','sous_titre_fr':'Une menace','theme_fr':'Chantage numérique',
            'description_fr':'Histoire fictive de Miora.','avertissement_fr':'Contenu sensible fictif.',
            'duree':'5 min','decisions_attendues':2,'palette':'default','ordre':0,
        }

    def test_tantara_accepts_fr_only_and_creates_durable_jobs(self):
        serializer=TantaraEditorSerializer(data=self.story_payload())
        self.assertTrue(serializer.is_valid(),serializer.errors)
        obj=serializer.save()
        self.assertEqual(obj.titre_mg,obj.titre_fr)  # Brouillon temporaire, PAS traduction.
        self.assertEqual(TranslationJob.objects.filter(target_id=obj.pk).count(),5)
        self.assertEqual(job_summary('content_api.Tantara',obj.pk)['state'],'PENDING')
        with self.assertRaises(ValidationError):ensure_ready('content_api.Tantara',obj.pk)

    def test_same_fr_does_not_retranslate_and_changed_fr_resets_approval(self):
        original=TantaraEditorSerializer(data=self.story_payload())
        self.assertTrue(original.is_valid(),original.errors)
        story=original.save()
        serializer=TantaraEditorSerializer(story,data={'titre_fr':'Le message inconnu'},partial=True)
        self.assertTrue(serializer.is_valid(),serializer.errors)
        serializer.save()
        self.assertEqual(TranslationJob.objects.filter(target_id=story.pk).count(),5)
        new=TantaraEditorSerializer(story,data={'titre_fr':'Une nouvelle menace'},partial=True)
        self.assertTrue(new.is_valid(),new.errors)
        story=new.save()
        self.assertEqual(story.titre_mg,'Une nouvelle menace')
        self.assertEqual(story.statut_editorial,'BROUILLON')
        self.assertEqual(job_summary('content_api.Tantara',story.pk)['pending'],5)

    def test_duration_is_restricted(self):
        bad=self.story_payload();bad['duree']='5 minutes 20 sec'
        serializer=TantaraEditorSerializer(data=bad)
        self.assertFalse(serializer.is_valid())
        self.assertIn('duree',serializer.errors)

    def test_graph_new_fr_text_queues_field_and_keeps_old_translation(self):
        old={'nodes':[{'id':'start','data':{'title':{'fr':'Salut','mg':'Manao ahoana'},'text':{'fr':'Bienvenue','mg':'Tongasoa'},'options':[]}}],'edges':[]}
        new={'nodes':[{'id':'start','data':{'title':{'fr':'Salut','mg':''},'text':{'fr':'Texte modifié','mg':''},'options':[]}}],'edges':[]}
        jobs=prime_graph(new,old)
        self.assertEqual(new['nodes'][0]['data']['title']['mg'],'Manao ahoana')
        self.assertEqual(new['nodes'][0]['data']['text']['mg'],'Texte modifié')
        self.assertEqual(jobs,[(['nodes','start','text'],'Texte modifié')])
