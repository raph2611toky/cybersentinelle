from django.core.management.base import BaseCommand
from apps.translation.models import TranslationJob
from apps.translation.services import dispatch_jobs

class Command(BaseCommand):
    help='Renvoie à Celery les traductions persistées en attente (après indisponibilité de Redis).'

    def add_arguments(self,parser):
        parser.add_argument('--limit',type=int,default=100)

    def handle(self,*args,**options):
        ids=list(TranslationJob.objects.filter(state='PENDING').order_by('created_at')
                 .values_list('pk',flat=True)[:max(1,min(options['limit'],500))])
        dispatch_jobs(ids)
        self.stdout.write(f'{len(ids)} traductions soumises au broker (vérifier worker et états).')
