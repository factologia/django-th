#!/usr/bin/env python
# coding: utf-8
from __future__ import unicode_literals
from multiprocessing import Pool, TimeoutError
# django
from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils.log import getLogger
from django.db.models import Q
# trigger happy
from django_th.models import TriggerService
from django_th.read import Read

# create logger
logger = getLogger('django_th.trigger_happy')


class Command(BaseCommand):

    help = 'Trigger all the services '\
        'and put them in cache'

    def handle(self, *args, **options):
        """
            get all the triggers that need to be handled
        """
        from django.db import connection
        connection.close()
        failed_tries = settings.DJANGO_TH.get('failed_tries', 10)
        trigger = TriggerService.objects.filter(
            Q(provider_failed__gte=failed_tries) |
            Q(consumer_failed__gte=failed_tries),
            status=True,
            user__is_active=True,
            provider__name__status=True,
            consumer__name__status=True,
        ).select_related('consumer__name', 'provider__name')
        try:
            with Pool(processes=settings.DJANGO_TH.get('processes')) as pool:
                r = Read()
                result = pool.map_async(r.reading, trigger)
                result.get(timeout=60)
        except TimeoutError as e:
            logger.warning(e)
