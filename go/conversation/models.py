from django.db import models
from go.base.models import Contact


class Conversation(models.Model):
    """A conversation with an audience"""
    user = models.ForeignKey('auth.User')
    subject = models.CharField('Conversation Name', max_length=255)
    message = models.TextField('Message')
    start_date = models.DateField()
    start_time = models.TimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    groups = models.ManyToManyField('base.ContactGroup')
    previewcontacts = models.ManyToManyField('base.Contact')

    def participants(self):
        return Contact.objects.filter(groups__in=self.groups.all())

    class Meta:
        ordering = ['-updated_at']
        get_latest_by = 'updated_at'

    def __unicode__(self):
        return self.subject
