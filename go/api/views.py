import json

from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import requests


import logging
logger = logging.getLogger(__name__)


@login_required
@csrf_exempt
@require_http_methods(['GET', 'POST'])
def go_api_proxy(request):
    url = settings.GO_API_URL
    auth = ('session_id', request.COOKIES['sessionid'])

    # FIXME: This hackery shouldn't be necessary:
    req_data = json.loads(request.body)
    # XXX: Extract the 'id' from the request to put in the response.
    #      Is this necessary? If so, the API worker should handle it.
    req_id = req_data['id']
    # XXX: Strip leading slashes off the method name.
    #      The JS and the API worker need to agree on this.
    req_data['method'] = req_data['method'].lstrip('/')
    data = json.dumps(req_data)

    logger.debug('Request data: %s %s %r' % (url, auth, data))
    request_method = {
        'GET': requests.get,
        'POST': requests.post,
    }[request.method]

    r = request_method(url, auth=auth, data=data)

    # FIXME: Once we don't need to juggle the 'id' field we can just return the
    #        raw response data.
    resp_data = r.json
    resp_data['id'] = req_id
    out = json.dumps(resp_data)

    logger.debug('Response data: %r' % (out,))

    return HttpResponse(out, status=r.status_code)
