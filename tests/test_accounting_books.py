"""Livros combinados com lotes documentais históricos e lançamentos manuais fictícios."""
import unittest
import test_accounting as helpers


class AccountingBookDocumentTests(unittest.TestCase):
    setUp = helpers.AccountingTests.setUp
    decision = helpers.AccountingTests.decision
    lines = helpers.AccountingTests.lines
    batch = helpers.AccountingTests.batch
    close = helpers.AccountingTests.close

    def test_combines_closed_sources_only_without_rewriting_documental_evidence(self):
        self.decision(); batch=self.close(self.batch())
        evidence=self.s.create_evidence_export(self.c,batch['id'],batch['snapshot_hash'],'Teste fictício')
        artifact=self.s.read_evidence_artifact(self.c,evidence['id'],'evidence.json')['content']
        accounts={row['code']:row['id'] for row in self.s.list_accounts(self.c,self.plan)}
        lines=[dict(date='2026-09-16',group='manual',side=side,amount='10.10',account_id=accounts[code],memo='Ajuste fictício')
               for side,code in (('D','1.1.1'),('C','2.1'))]
        journal=self.s.save_manual_journal(self.c,self.p,self.plan,lines,'Ref manual','Teste','manual-1')
        before=self.s.accounting_books(self.c,self.p,self.plan)
        self.assertEqual(len(before['diary']),2)
        for target in ('revisado','fechado'):
            self.s.transition_manual_journal(self.c,journal['journal_id'],journal['snapshot_hash'],'Teste',target)
        book=self.s.accounting_books(self.c,self.p,self.plan)
        self.assertEqual(len(book['diary']),4)
        self.assertEqual(book['totals'],{'debit':'110.40','credit':'110.40'})
        self.assertEqual([row['movement_balance'] for row in book['trial_balance_movements']],['110.40','-110.40'])
        documentary=[row for row in book['diary'] if row['source_kind']=='documental']
        self.assertEqual(documentary[0]['document_id'],self.doc)
        self.assertEqual(documentary[0]['observation_id'],self.obs)
        self.assertEqual([row['sequence'] for row in book['diary']],[1,2,3,4])
        self.assertEqual(self.s.read_evidence_artifact(self.c,evidence['id'],'evidence.json')['content'],artifact)

    def test_closed_documental_snapshot_survives_live_source_changes_and_scopes(self):
        self.decision();self.close(self.batch())
        original=self.s.accounting_books(self.c,self.p,self.plan)
        from test_persistence import fake_xml
        self.s.import_file(self.c,self.p,'outra-fonte-ficticia.xml',fake_xml(wrapper=False),'XML')
        self.assertEqual(self.s.accounting_books(self.c,self.p,self.plan),original)
        # Different reference contexts with the same processing month remain separate.
        other_period=self.s.create_period(self.c,'2026-07','2026-09')['id']
        self.assertEqual(self.s.accounting_books(self.c,other_period,self.plan)['diary'],[])
        with self.assertRaises(ValueError):self.s.accounting_books(self.c,self.p,self.plan+1)

    def test_corrupt_closed_documental_source_blocks_book_generation(self):
        self.decision();batch=self.close(self.batch())
        with self.s.db:self.s.db.execute("UPDATE accounting_batches SET snapshot_hash='invalido' WHERE id=?",(batch['id'],))
        with self.assertRaisesRegex(ValueError,'hash'):self.s.accounting_books(self.c,self.p,self.plan)


if __name__ == '__main__':unittest.main()
