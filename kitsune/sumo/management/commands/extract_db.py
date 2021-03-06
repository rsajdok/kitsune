import os
from optparse import make_option

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db.models.loading import get_model

from tower import strip_whitespace


HEADER = """\
#######################################################################
#
# Note: This file is a generated file--do not edit it directly!
# Instead make changes to the appropriate content in the database or
# write up a bug here:
#
#     https://bugzilla.mozilla.org/enter_bug.cgi?product=support.mozilla.org
#
# with the specific lines that are problematic and why.
#
# You can generate this file by running:
#
#     ./manage.py extract_db
#
#######################################################################
"""


class Command(BaseCommand):
    """
    Pulls strings from the database and puts them in a python file,
    wrapping each one in a gettext call.

    The models and attributes to pull are defined by DB_LOCALIZE:

    DB_LOCALIZE = {
        'some_app': {
            SomeModel': {
                'attrs': ['attr_name', 'another_attr'],
            }
        },
        'another_app': {
            AnotherModel': {
                'attrs': ['more_attrs'],
                'comments': ['Comment that will appear to localizers.'],
            }
        },
    }

    Database columns are expected to be CharFields or TextFields.
    """
    help = ('Pulls strings from the database and writes them to python file.')
    option_list = BaseCommand.option_list + (
        make_option('--output-file', '-o',
                    default=os.path.join(settings.ROOT, 'kitsune', 'sumo',
                                         'db_strings.py'),
                    dest='outputfile',
                    help='The file where extracted strings are written to.'
                         '(Default: %default)'),
        )

    def handle(self, *args, **options):
        try:
            apps = settings.DB_LOCALIZE
        except AttributeError:
            raise CommandError('DB_LOCALIZE setting is not defined!')

        strings = []
        for app, models in apps.items():
            for model, params in models.items():
                model_class = get_model(app, model)
                attrs = params['attrs']
                qs = model_class.objects.all().values_list(*attrs).distinct()
                for item in qs:
                    for i in range(len(attrs)):
                        msg = {
                            'id': strip_whitespace(item[i]),
                            'context': 'DB: %s.%s.%s' % (app, model, attrs[i]),
                            'comments': params.get('comments')}
                        strings.append(msg)

        py_file = os.path.expanduser(options.get('outputfile'))
        py_file = os.path.abspath(py_file)

        print 'Outputting db strings to: {filename}'.format(filename=py_file)
        with open(py_file, 'w+') as f:
            f.write(HEADER)
            f.write('from tower import ugettext as _\n\n')
            for s in strings:
                comments = s['comments']
                if comments:
                    for c in comments:
                        f.write(u'# {comment}\n'.format(comment=c).encode('utf8'))

                f.write(u'_("""{id}""", "{context}")\n'.format(id=s['id'], context=s['context'])
                        .encode('utf8'))
