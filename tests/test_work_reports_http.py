"""Accounting reports through the real loopback/token HTTP boundary."""
import unittest
import json
import test_accounting_http as helpers


class ReportsHTTPTests(unittest.TestCase):
    setUp = helpers.AccountingHTTPTests.setUp
    tearDown = helpers.AccountingHTTPTests.tearDown
    start_server = helpers.AccountingHTTPTests.start_server
    stop_server = helpers.AccountingHTTPTests.stop_server
    request = helpers.AccountingHTTPTests.request
    api = helpers.AccountingHTTPTests.api
    company = helpers.AccountingHTTPTests.company
    fixture = helpers.AccountingHTTPTests.fixture

    def test_report_http_integrity_scope_token_and_read_only_method(self):
        company, cycle, payload = self.fixture()
        plan = self.api(f'work-cycles?company_id={company}')[0]['plan_id']
        query = f'/api/accounting-report?company_id={company}&cycle_id={cycle}&plan_id={plan}'
        self.assertEqual(self.request(query, headers={'X-Local-Token':None})[0], 403)
        other = self.company()['id']
        self.assertEqual(self.request(query.replace(f'company_id={company}', f'company_id={other}'))[0], 400)
        scope = {'company_id':company, 'cycle_id':cycle}
        operation = self.api('work-operations', {**scope,'payload':payload,'reason':'Teste','request_key':'report-http'})
        transition = {'company_id':company,'operation_id':operation['operation_id'],'snapshot_hash':operation['snapshot_hash'],'reason':'Teste'}
        self.api('work-review', transition)
        self.api('work-post', transition)
        status, _, data = self.request(query + '&report=razao&account_code=1')
        self.assertEqual(status, 200, data)
        self.assertEqual(json.loads(data)['data']['totals']['debit'], '10.00')
        self.assertEqual(json.loads(data)['data']['rows'][0]['balance'], '10.00')
        self.assertEqual(self.request('/api/accounting-report','POST',{**scope,'plan_id':plan})[0], 404)
        self.assertEqual(self.request(query + '&cost_center=1')[0], 400)
        self.assertEqual(self.request(query + '&company_id=' + str(other))[0], 400)
        self.stop_server(); self.start_server()
        self.assertEqual(self.request(query + '&report=razao&account_code=1')[2], data)
