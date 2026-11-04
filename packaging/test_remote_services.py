import sys
import unittest
from unittest.mock import patch
from remote_services import RemoteServices,validate_url,NoRedirect,protect

class RemoteServicesTests(unittest.TestCase):
    def test_rejects_plain_http_credentials_and_fragments(self):
        for url in ('http://localhost:8766','https://user:pass@example.test','https://example.test#secret','https://example.test?token=x','file:///tmp/test'):
            with self.assertRaises(ValueError):validate_url(url)
        self.assertEqual(validate_url('https://example.test/agent/'),'https://example.test/agent')
    def test_no_redirect_with_credential(self):
        with self.assertRaises(ValueError):NoRedirect().redirect_request(None,None,None,None,None,None)
    def test_commands_cannot_select_shell_or_other_path(self):
        client=RemoteServices('https://example.test/agent','synthetic')
        with patch.object(client,'request') as request:
            for ident,action in [('a'*64,'exec'),('../other','start')]:
                with self.assertRaises(ValueError):client.command(ident,action)
            request.assert_not_called()
    @unittest.skipUnless(sys.platform=='win32','DPAPI exige Windows')
    def test_dpapi_roundtrip(self):
        encrypted=protect('synthetic-agent-token')
        self.assertNotIn(b'synthetic-agent-token',encrypted)
        self.assertEqual(protect(encrypted,True),b'synthetic-agent-token')

if __name__=='__main__':unittest.main()
