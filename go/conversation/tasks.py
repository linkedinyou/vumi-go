from StringIO import StringIO
from zipfile import ZipFile, ZIP_DEFLATED

from celery.task import task

from django.conf import settings
from django.core.mail import EmailMessage

from go.vumitools.api import VumiUserApi
from go.base.models import UserProfile
from go.base.utils import UnicodeDictWriter


# The field names to export
conversation_export_field_names = [
    'timestamp',
    'from_addr',
    'to_addr',
    'content',
    'message_id',
    'in_reply_to',
    'session_event',
    'transport_type',
    'direction',
    'network_handover_status',
    'network_handover_reason',
    'delivery_status',
    'endpoint',
]


def get_delivery_status(delivery_reports):
    if not delivery_reports:
        return 'Unknown'
    return delivery_reports[0]['delivery_status']


def get_network_status(acks_or_nacks):
    if not acks_or_nacks:
        return 'Unknown', ''
    event = acks_or_nacks[0]
    return event['event_type'], event.get('nack_reason', '')


def row_for_inbound_message(message):
    row = dict((field, unicode(message.payload[field]))
               for field in conversation_export_field_names
               if field in message)
    row['direction'] = 'inbound'
    row['endpoint'] = message.get_routing_endpoint()
    return row


def row_for_outbound_message(message, mdb):
    events = sorted(mdb.get_events_for_message(message['message_id']),
                    key=lambda event: event['timestamp'],
                    reverse=True)
    row = dict((field, unicode(message.payload[field]))
               for field in conversation_export_field_names
               if field in message)
    row['direction'] = 'outbound'
    delivery_reports = [event for event in events
                        if event['event_type'] == 'delivery_report']
    row['delivery_status'] = get_delivery_status(delivery_reports)
    network_events = [event for event in events
                      if event['event_type'] in ['ack', 'nack']]
    status, reason = get_network_status(network_events)
    row['network_handover_status'] = status
    row['network_handover_reason'] = reason
    row['endpoint'] = message.get_routing_endpoint()
    return row


def load_messages_in_chunks(conversation, direction='inbound',
                            include_sensitive=False, scrubber=None):
    """
    Load the conversation's messages one index page at a time, skipping and/or
    scrubbing messages depending on `include_sensitive` and `scrubber`.

    :param Conversation conv:
        The conversation.
    :param str direction:
        The direction, either ``'inbound'`` or ``'outbound'``.
    :param bool include_sensitive:
        If ``False`` then all messages marked as `sensitive` are skipped.
        Defaults to ``False``.
    :param callable scrubber:
        If provided, this is called for every message allowing it to be
        modified on the fly.
    """
    if direction == 'inbound':
        index_page = conversation.mdb.batch_inbound_keys_page(
            conversation.batch.key)
        get_msg = conversation.mdb.get_inbound_message
    elif direction == 'outbound':
        index_page = conversation.mdb.batch_outbound_keys_page(
            conversation.batch.key)
        get_msg = conversation.mdb.get_outbound_message
    else:
        raise ValueError('Invalid value (%s) received for `direction`. '
                         'Only `inbound` and `outbound` are allowed.' %
                         (direction,))

    while index_page is not None:
        messages = [get_msg(key) for key in index_page]
        yield conversation.filter_and_scrub_messages(
            messages, include_sensitive=include_sensitive, scrubber=scrubber)
        index_page = index_page.next_page()


def email_export(user_profile, conversation, io):
    zipio = StringIO()
    zf = ZipFile(zipio, "a", ZIP_DEFLATED)
    zf.writestr("messages-export.csv", io.getvalue())
    zf.close()

    email = EmailMessage(
        'Conversation message export: %s' % (conversation.name,),
        'Please find the messages of the conversation %s attached.\n' % (
            conversation.name),
        settings.DEFAULT_FROM_EMAIL, [user_profile.user.email])
    email.attach('messages-export.zip', zipio.getvalue(), 'application/zip')
    email.send()


@task(ignore_result=True)
def export_conversation_messages_unsorted(account_key, conversation_key):
    """
    Export the messages from a conversation as they come from the message
    store. Completely unsorted.

    :param str account_key:
        The account holder's account account_key
    :param str conversation_key:
        The key of the conversation we want to export the messages for.
    """
    user_api = VumiUserApi.from_config_sync(
        account_key, settings.VUMI_API_CONFIG)
    user_profile = UserProfile.objects.get(user_account=account_key)
    conversation = user_api.get_wrapped_conversation(conversation_key)

    io = StringIO()
    writer = UnicodeDictWriter(io, conversation_export_field_names)
    writer.writeheader()

    for messages in load_messages_in_chunks(conversation, 'inbound'):
        for message in messages:
            writer.writerow(row_for_inbound_message(message))

    for messages in load_messages_in_chunks(conversation, 'outbound'):
        for message in messages:
            mdb = user_api.api.mdb
            writer.writerow(row_for_outbound_message(message, mdb))

    email_export(user_profile, conversation, io)
