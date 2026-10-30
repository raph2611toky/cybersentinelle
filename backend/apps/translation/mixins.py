"""Accept FR-only changes while preserving Django's bilingual invariants.

MG temporarily mirrors FR only inside drafts. The public publication path
rejects unfinished tasks; translators must be human-reviewed before release.
"""
from django.db import transaction
from rest_framework import serializers
from .services import create_jobs, job_summary
from copy import copy


class FrenchFirstMixin:
    translation_fields = ()
    translation_state = serializers.SerializerMethodField(read_only=True)

    def get_translation_state(self, obj):
        return job_summary(obj._meta.label,obj.pk)

    def to_internal_value(self, data):
        data=copy(data)
        changed=[]
        for prefix in self.translation_fields:
            fr=f'{prefix}_fr';mg=f'{prefix}_mg'
            if fr not in data:continue
            text=data[fr]
            if not isinstance(text,str):continue
            old=getattr(self.instance,fr,None) if self.instance else None
            if old!=text:
                # MG is only a temporary draft placeholder, NOT a translation.
                data[mg]=text
                changed.append(([fr],text))
            elif not self.instance and mg not in data:
                data[mg]=text
        if changed and hasattr(self.Meta.model,'statut_editorial'):
            data['statut_editorial']='BROUILLON'
            for field in ('valide_le','relecture_fr_le','relecture_mg_le'):
                data[field]=None
            for field in ('validateur_role','relecteur_fr_role','relecteur_mg_role'):
                data[field]=''
        self._translation_changes=changed
        return super().to_internal_value(data)

    def create(self,validated_data):
        with transaction.atomic():
            obj=super().create(validated_data)
            create_jobs(obj,getattr(self,'_translation_changes',[]))
            return obj

    def update(self,instance,validated_data):
        with transaction.atomic():
            obj=super().update(instance,validated_data)
            create_jobs(obj,getattr(self,'_translation_changes',[]))
            return obj


def french_only_fields(prefixes):
    # With the original ModelSerializer all MG columns are marked required.
    return {f'{key}_mg': {'required':False,'allow_blank':True} for key in prefixes}
