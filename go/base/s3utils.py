""" Utilities for dealing with uploading to S3. """

import StringIO

import boto

from django.conf import settings


class BucketConfig(object):
    """ Helper for accessing Django GO_S3_BUCKET settings. """

    def __init__(self, config_name):
        self.config_name = config_name

    def __getattr__(self, name):
        bucket_config = settings.GO_S3_BUCKETS.get(self.config_name, {})
        defaults = settings.GO_S3_BUCKETS.get('defaults', {})
        if name in bucket_config:
            return bucket_config[name]
        if name in defaults:
            return defaults[name]
        raise AttributeError(
            "BucketConfig %r has no attribute %r" % (self.config_name, name))


class Bucket(object):
    """ An S3 bucket.

    :param str config_name:
        The name of the bucket config.

    Bucket configuration is defined via Django settings as follows:

    ::

       GO_S3_BUCKETS = {
           'defaults': {
               'aws_access_key_id': 'MY-ACCESS-KEY-ID',
               'aws_secret_access_key': 'SECRET',
           },
           'billing.archive': {
               's3_bucket_name': 'go.vumi.org.billing.archive',
           },
       }

    """

    def __init__(self, config_name):
        self.config = BucketConfig(config_name)

    def get_s3_bucket(self):
        """ Return an S3 bucket object. """
        conn = boto.connect_s3(
            self.config.aws_access_key_id, self.config.aws_secret_access_key)
        return conn.get_bucket(self.config.s3_bucket_name)

    def upload(self, key_name, chunks, headers=None):
        """ Upload chunks of data to S3. """
        bucket = self.get_s3_bucket()
        mp = bucket.initiate_multipart_upload(key_name, headers=headers)
        try:
            for i, chunk in enumerate(chunks):
                fp = StringIO.StringIO(chunk)
                mp.upload_part_from_file(fp, part_num=i + 1)
        except:
            mp.cancel_upload()
            raise
        else:
            mp.complete_upload()
