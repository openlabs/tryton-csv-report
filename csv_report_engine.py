# -*- coding: utf-8 -*-
"""
    CSV Report Engine

    :copyright: (c) 2011 by Openlabs Technologies & Consulting (P) Ltd.
    :license: GPLv3, see LICENSE for more details.
"""
import csv
import base64
from datetime import date
from tempfile import NamedTemporaryFile

from trytond.wizard import Wizard
from trytond.model import fields, ModelView


class UnicodeDictWriter(csv.DictWriter):
    def __init__(self, csvfile, fieldnames, *args, **kwargs):
        """Allows to specify an additional keyword argument encoding which
        defaults to "utf-8"
        """
        self.encoding = kwargs.pop('encoding', 'utf-8')
        csv.DictWriter.__init__(self, csvfile, fieldnames, *args, **kwargs)

    def _dict_to_list(self, rowdict):
        rv = csv.DictWriter._dict_to_list(self, rowdict)
        return [(f.encode(self.encoding) if isinstance(f, basestring) else f)\
                    for f in rv]


class CSVReportEngine(ModelView):
    """CSV report Engine View
    """
    _name = 'csv.report.engine'
    _description = __doc__

    def get_date(self, end=False):
        """Return the first and last date of current month

        :param end: If True returns last day of month
        :type end: Boolean
        """
        date_obj = self.pool.get('ir.date')
        today = date_obj.today()
        if end:
            return today
        return date(today.year, today.month, 1)

    def _get_reports(self):
        """Builds a list of tuples for the selection field based on the reports
        that already exist.

        Registering the profile
        ~~~~~~~~~~~~~~~~~~~~~~~

        class CSVInventoryReport(Wizard):
            _name = "csv.report.engine"

            def report_inventory(self):
                "Inventory Status Report"
                return CSVInventoryReport
        """
        reports = []
        for attribute in dir(self):
            if attribute.startswith('report_'):
                reports.append((attribute, getattr(self, attribute).__doc__))
        return reports

    from_date = fields.Date('From Date')
    to_date = fields.Date('To Date')
    party = fields.Many2One('party.party', 'Party')
    report = fields.Selection('_get_reports', 'Report', required=True)

    def default_from_date(self):
        return self.get_date()

    def default_to_date(self):
        return self.get_date(end=True)

CSVReportEngine()


class CSVEngineWizardViewResponse(ModelView):
    """This wizard displays the response of csv report
    """
    _name = 'csv.report.wizard.response'
    _description = 'CSV Engine Response Wizard View'

    filename = fields.Char('Filename', readonly=True)
    file = fields.Binary('Report Data', readonly=True)

CSVEngineWizardViewResponse()


class CSVEngineWizard(Wizard):
    """A wizard with two states where the first state uses the view above
    and takes the data to generate the report
    """
    _name = "csv.report.wizard"
    _description = "CSV Report Engine"

    states = {
        'init': {
            'actions': [],
            'result': {
                'type': 'form',
                'object': 'csv.report.engine',
                'state': [
                    ('end', 'Cancel', 'tryton-cancel'),
                    ('do_generate_report', 'Generate Report',
                        'tryton-ok', True),
                ],
            },
        },
        'do_generate_report': {
            'actions': ['generate_report'],
            'result': {
                'type': 'form',
                'object': 'csv.report.wizard.response',
                'state': [
                    ('end', 'OK', 'tryton-ok'),
                ],
            },
        },
    }

    def generate_report(self, data):
        "Generate the report by calling corresponding method"
        csv_engine_obj = self.pool.get('csv.report.engine')
        buffer = NamedTemporaryFile(delete=False)
        getattr(csv_engine_obj, data['form']['report'])(data['form'], buffer)
        buffer.close()

        with open(buffer.name) as f:
            content = f.read()

        form = {}
        form['file'] = base64.b64encode(content)
        form['filename'] = '%s.csv' % (data['form']['report'])
        return form

CSVEngineWizard()
