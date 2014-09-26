
import cloudstorage as cs

BUCKET_NAME = 'data-delivery.appspot.com'
my_default_retry_params = cs.RetryParams(initial_delay=0.2, max_delay=5.0, backoff_factor=2, max_retry_period=15)
cs.set_default_retry_params(my_default_retry_params)


def get_bucket_path(filename):
    return '/' + BUCKET_NAME + '/' + filename


def create_file(filename, content, content_type='text/plain'):
    write_retry_params = cs.RetryParams(backoff_factor=1.1)
    filename = get_bucket_path(filename)
    cs_file = cs.open(filename, 'w', content_type=content_type, retry_params=write_retry_params)
    cs_file.write(content)
    cs_file.close()


def read_file(filename):
    filename = get_bucket_path(filename)
    cs_file = cs.open(filename)
    content = cs_file.read()
    cs_file.close()
    stat = cs.stat(filename)
    return (content, stat.content_type)


def check_file(filename):
    filename = get_bucket_path(filename)
    try:
        cs.stat(filename)
    except cs.NotFoundError:
        return False
    else:
        return True

# class MainPage(webapp2.RequestHandler):
#   """Main page for GCS demo application."""
#
#   def get(self):
#     # bucket_name = os.environ.get('cvm-funds.appspot.com',
#     # app_identity.get_default_cs_bucket_name())
#
#     self.response.headers['Content-Type'] = 'text/plain'
#     self.response.write('Demo GCS Application running from Version: '
#                         + os.environ['CURRENT_VERSION_ID'] + '\n')
#     self.response.write('Using bucket name: ' + bucket_name + '\n\n')
#
#     bucket = '/' + bucket_name
#     filename = bucket + '/demo-testfile'
#     self.tmp_filenames_to_clean_up = []
#
#     try:
#       self.create_file(filename)
#       self.response.write('\n\n')
#
#       self.read_file(filename)
#       self.response.write('\n\n')
#
#       self.stat_file(filename)
#       self.response.write('\n\n')
#
#       self.create_files_for_list_bucket(bucket)
#       self.response.write('\n\n')
#
#       self.list_bucket(bucket)
#       self.response.write('\n\n')
#
#       self.list_bucket_directory_mode(bucket)
#       self.response.write('\n\n')
#
#     except Exception, e:
#       logging.exception(e)
#       self.delete_files()
#       self.response.write('\n\nThere was an error running the demo! '
#                           'Please check the logs for more details.\n')
#
#     else:
#       self.delete_files()
#       self.response.write('\n\nThe demo ran successfully!\n')
#
#   def create_file(self, filename):
#     """Create a file.
#
#     The retry_params specified in the open call will override the default
#     retry params for this particular file handle.
#
#     Args:
#       filename: filename.
#     """
#     self.response.write('Creating file %s\n' % filename)
#
#     write_retry_params = cs.RetryParams(backoff_factor=1.1)
#     cs_file = cs.open(filename,
#                         'w',
#                         content_type='text/plain',
#                         options={'x-goog-meta-foo': 'foo',
#                                  'x-goog-meta-bar': 'bar'},
#                         retry_params=write_retry_params)
#     cs_file.write('abcde\n')
#     cs_file.write('f'*1024*4 + '\n')
#     cs_file.close()
#     self.tmp_filenames_to_clean_up.append(filename)
#
#   def read_file(self, filename):
#     self.response.write('Abbreviated file content (first line and last 1K):\n')
#
#     cs_file = cs.open(filename)
#     self.response.write(cs_file.readline())
#     cs_file.seek(-1024, os.SEEK_END)
#     self.response.write(cs_file.read())
#     cs_file.close()
#
#   def stat_file(self, filename):
#     self.response.write('File stat:\n')
#
#     stat = cs.stat(filename)
#     self.response.write(repr(stat))
#
#   def create_files_for_list_bucket(self, bucket):
#     self.response.write('Creating more files for listbucket...\n')
#     filenames = [bucket + n for n in ['/foo1', '/foo2', '/bar', '/bar/1',
#                                       '/bar/2', '/boo/']]
#     for f in filenames:
#       self.create_file(f)
#
#   def list_bucket(self, bucket):
#     """Create several files and paginate through them.
#
#     Production apps should set page_size to a practical value.
#
#     Args:
#       bucket: bucket.
#     """
#     self.response.write('Listbucket result:\n')
#
#     page_size = 1
#     stats = cs.listbucket(bucket + '/foo', max_keys=page_size)
#     while True:
#       count = 0
#       for stat in stats:
#         count += 1
#         self.response.write(repr(stat))
#         self.response.write('\n')
#
#       if count != page_size or count == 0:
#         break
#       stats = cs.listbucket(bucket + '/foo', max_keys=page_size,
#                              marker=stat.filename)
#
#   def list_bucket_directory_mode(self, bucket):
#     self.response.write('Listbucket directory mode result:\n')
#     for stat in cs.listbucket(bucket + '/b', delimiter='/'):
#       self.response.write('%r' % stat)
#       self.response.write('\n')
#       if stat.is_dir:
#         for subdir_file in cs.listbucket(stat.filename, delimiter='/'):
#           self.response.write('  %r' % subdir_file)
#           self.response.write('\n')
#
#   def delete_files(self):
#     self.response.write('Deleting files...\n')
#     for filename in self.tmp_filenames_to_clean_up:
#       self.response.write('Deleting file %s\n' % filename)
#       try:
#         cs.delete(filename)
#       except cs.NotFoundError:
#         pass
