import fnmatch
import urllib


class GerritReview(object):
    """ Encapsulation of a Gerrit review.

    :arg str message: (optional) Cover message.
    :arg dict labels: (optional) Review labels.
    :arg dict comments: (optional) Inline comments.

    """

    def __init__(self, message=None, labels=None, comments=None):
        self.message = message if message else ""
        if labels:
            if not isinstance(labels, dict):
                raise ValueError("labels must be a dict.")
            self.labels = labels
        else:
            self.labels = {}
        if comments:
            if not isinstance(comments, list):
                raise ValueError("comments must be a list.")
            self.comments = {}
            self.add_comments(comments)
        else:
            self.comments = {}

    def set_message(self, message):
        """ Set review cover message.

        :arg str message: Cover message.

        """
        self.message = message

    def add_labels(self, labels):
        """ Add labels.

        :arg dict labels: Labels to add, for example

        Usage::

            add_labels({'Verified': 1,
                        'Code-Review': -1})

        """
        self.labels.update(labels)

    def add_comments(self, comments):
        """ Add inline comments.

        :arg dict comments: Comments to add.

        Usage::

            add_comments([{'filename': 'Makefile',
                           'line': 10,
                           'message': 'inline message'}])

            add_comments([{'filename': 'Makefile',
                           'range': {'start_line': 0,
                                     'start_character': 1,
                                     'end_line': 0,
                                     'end_character': 5},
                           'message': 'inline message'}])

        """
        for comment in comments:
            if 'filename' and 'message' in list(comment.keys()):
                msg = {}
                if 'range' in list(comment.keys()):
                    msg = {"range": comment['range'],
                           "message": comment['message']}
                elif 'line' in list(comment.keys()):
                    msg = {"line": comment['line'],
                           "message": comment['message']}
                else:
                    continue
                file_comment = {comment['filename']: [msg]}
                if self.comments:
                    if comment['filename'] in list(self.comments.keys()):
                        self.comments[comment['filename']].append(msg)
                    else:
                        self.comments.update(file_comment)
                else:
                    self.comments.update(file_comment)

    def __str__(self):
        review_input = {}
        if self.message:
            review_input.update({'message': self.message})
        if self.labels:
            review_input.update({'labels': self.labels})
        if self.comments:
            review_input.update({'comments': self.comments})
        return json.dumps(review_input, sort_keys=True)


class GerritProject(object):
    def __init__(self, gerrit, **data):
        self.gerrit = gerrit
        self.data = data

    @property
    def name(self):
        return self.data['name']

    def get_content(self, branch, filepath):
        return self.gerrit.get('/projects/%s/branches/%s/files/%s/content' % (
            urllib.quote_plus(self.name), urllib.quote_plus(branch), urllib.quote_plus(filepath)))


class GerritChange(object):
    def __init__(self, gerrit, **data):
        self.gerrit = gerrit
        self.__dict__.update(data)

    @property
    def id(self):
        return str(self.__dict__['_number'])

    @property
    def change_id(self):
        return self.__dict__['change_id']

    @property
    def revision(self):
        return self.__dict__['current_revision']

    @property
    def files(self):
        return self.__dict__['revisions'][self.revision]['files']

    @property
    def status(self):
        return self.__dict__['status']

    def rebase(self):
        return self.gerrit.post('/changes/%s/rebase' % self.id)

    def abandon(self):
        return self.gerrit.post('/changes/%s/abandon' % self.id)

    def get_topic(self):
        return self.gerrit.get('/changes/%s/topic' % self.id)

    def set_topic(self, topic):
        return self.gerrit.put('/changes/%s/topic' % self.id, json={ 'topic': topic })

    def delete_topic(self):
        return self.gerrit.delete('/changes/%s/topic' % self.id)

    def submit(self):
        return self.gerrit.post('/changes/%s/submit' % self.id)

    def get_file_content(self, filename):
        return self.gerrit.get('/changes/%s/revisions/%s/files/%s/content' % (self.id, self.revision, filename))

    def get_files_changed(self, glob_filter='*'):
        files_changed_names = [urllib.parse.quote_plus(k) for k, v in self.files.items() if fnmatch.fnmatch(k, glob_filter)]
        return {f: self.get_file_content(f) for f in files_changed_names}

    def change_file_content_in_edit(self, filename, stream):
        return self.gerrit.put('/changes/%s/edit/%s' % (self.id, urllib.quote_plus(filename)), data=stream)

    def delete_file_in_edit(self, filename):
        return self.gerrit.delete('/changes/%s/edit/%s' % (self.id, urllib.quote_plus(filename)))

    def publish_edit(self):
        return self.gerrit.post('/changes/%s/edit:publish' % self.id)

    def delete_edit(self):
        return self.gerrit.delete('/changes/%s/edit' % self.id)

    def publish(self):
        return self.gerrit.post('/changes/%s/publish' % self.id)

    def add_reviewer(self, reviewer):
        return self.gerrit.post('/changes/%s/reviewers' % self.id, json={ 'reviewer': reviewer })

    def add_review(self, **kwargs):
        """
        Add a review to the current revision of this change
        :keyword tag
        :keyword message
        :keyword dict labels
        :keyword comments
        :return:
        """
        self.reload()
        return self.gerrit.post('/changes/%s/revisions/%s/review' % (self.id, self.revision), json=kwargs)

    def reload(self):
        self.__dict__.update(self.gerrit.get_change(change=self.id).__dict__)

    def __str__(self):
        return 'Change-Id %s' % self.change_id
