"""Catalog facts from synthetic XML/SPED: no fiscal inference or global code merge."""
import json
import sqlite3
import tempfile
from pathlib import Path
import unittest
from xml.etree import ElementTree as ET
from src.persistence import AccountingStore
from src.reconciliation import SPED_PROFILE, CATALOG_PROFILE
from test_persistence import ISSUER, BUYER, NS, fake_xml
from test_reconciliation import fake_sped


def product_xml(number=1, code='PROD-FICTICIO', description='Produto inteiramente fictício', issuer=ISSUER):
    root=ET.fromstring(fake_xml(number=number))
    info=root.find(f'.//{{{NS}}}infNFe')
    detail=ET.SubElement(info,f'{{{NS}}}det',{'nItem':'1'})
    product=ET.SubElement(detail,f'{{{NS}}}prod')
    for key,value in {'cProd':code,'xProd':description,'NCM':'00000000','uCom':'UN','cEAN':'SEM GTIN'}.items():
        ET.SubElement(product,f'{{{NS}}}{key}').text=value
    return ET.tostring(root,encoding='utf-8')


def catalog_sped(*rows):
    original=fake_sped().splitlines()
    catalog=[b'|0001|0|']+[('|'+'|'.join(row)+'|').encode() for row in rows]+[b'|0990|'+str(len(rows)+2).encode()+b'|']
    return b'\n'.join(original[:1]+catalog+original[1:])+b'\n'


class CatalogTests(unittest.TestCase):
    def setUp(self):
        self.s=AccountingStore(':memory:');self.addCleanup(self.s.close)
        self.c=self.s.create_company('Empresa fictícia','1','1',ISSUER)['id']
        self.p=self.s.create_period(self.c,'2026-09','2026-09')['id']
        self.other=self.s.create_company('Outra fictícia','2','2')['id']

    def xml(self, content):
        return self.s.import_file(self.c,self.p,'ficticio.xml',content,'XML')

    def test_xml_products_preserve_first_representation_and_revision(self):
        first=self.xml(product_xml())
        again=self.xml(product_xml())
        self.assertTrue(again['duplicate'])
        self.xml(product_xml(number=2,description='Descrição divergente fictícia'))
        products=self.s.list_products(self.c)
        self.assertEqual(len(products),1)
        product=products[0]
        self.assertEqual(product['data']['description'],'Produto inteiramente fictício')
        self.assertTrue(product['pending'])
        self.assertEqual(len(product['observations']),2)
        self.assertEqual(product['observations'][-1]['file_id'],first['id'])
        observation=product['observations'][0]
        with self.assertRaises(ValueError):self.s.review_product(self.c,product['id'],product['version']-1,observation['id'],'Conferência fictícia')
        with self.assertRaises(ValueError):self.s.review_product(self.other,product['id'],product['version'],observation['id'],'Conferência fictícia')
        reviewed=self.s.review_product(self.c,product['id'],product['version'],observation['id'],'Conferência fictícia')
        self.assertFalse(reviewed['pending'])
        self.assertEqual(reviewed['data']['description'],'Descrição divergente fictícia')
        self.assertEqual(self.s.list_products(self.other),[])

    def test_equivalent_new_observation_invalidates_review_version_and_removed_sources(self):
        first=self.xml(product_xml())
        product=self.s.list_products(self.c)[0]
        self.xml(product_xml(number=2))
        with self.assertRaises(ValueError):self.s.review_product(self.c,product['id'],product['version'],product['observations'][0]['id'],'Conferência fictícia')
        current=self.s.list_products(self.c)[0]
        with self.s.db:self.s.db.execute("UPDATE files SET status='excluido' WHERE id=?",(first['id'],))
        self.assertFalse(self.s.list_products(self.c)[0]['pending'])
        with self.assertRaises(ValueError):self.s.review_product(self.c,current['id'],current['version'],product['observations'][0]['id'],'Origem removida')
        with self.s.db:self.s.db.execute("UPDATE files SET status='excluido'")
        self.assertTrue(self.s.list_products(self.c)[0]['pending'])

    def test_missing_code_never_fabricates_identity(self):
        self.xml(product_xml(code=''))
        self.assertEqual(self.s.list_products(self.c),[])
        row=self.s.db.execute('SELECT * FROM product_observations').fetchone()
        self.assertIsNone(row['product_id'])
        self.assertEqual(row['state'],'pendente')
        self.assertIn('Código ausente',json.loads(row['issues'])[0])

    def test_sped_catalog_participants_and_distinct_code_namespaces(self):
        self.xml(product_xml())
        participant=['0150','PART-FICTICIO','Participante fictício','1058',BUYER,'','IE-FICTICIA','3550308','','Rua fictícia','1','','Centro fictício']
        product=['0200','PROD-FICTICIO','Produto SPED fictício','SEM GTIN','','UN','00','00000000','','00','','0,00','']
        content=catalog_sped(participant,product)
        received=self.s.import_file(self.c,self.p,'ficticio.txt',content,'SPED')
        self.assertEqual(len(self.s.list_products(self.c)),1) # receipt alone creates no facts
        self.s.index_file(self.c,received['id'],SPED_PROFILE)
        self.assertEqual(len(self.s.list_products(self.c)),2)
        party=next(p for p in self.s.list_participants(self.c) if p['identifier_value']==BUYER)
        self.assertIn('participante',party['roles'])
        self.assertTrue(any('/0150' in o['source'] for o in party['observations']))
        observations=self.s.list_observations(self.c)
        source=next(o for o in observations if o['raw'].get('record')=='0200')
        self.assertTrue(source['locator'].startswith('linha:'))
        self.assertEqual(source['raw']['fields'],product)
        self.s.index_file(self.c,received['id'],SPED_PROFILE)
        self.assertEqual(len(self.s.list_products(self.c)),2)

    def test_sped_invalid_catalog_or_foreign_participant_does_not_create_identity(self):
        no_identity=['0150','EXTERIOR','Participante externo fictício','9999','','','','','','','','','']
        malformed=['0200','INCOMPLETO']
        self.s.import_file(self.c,self.p,'ficticio.txt',catalog_sped(no_identity,malformed),'SPED',sped_profile=SPED_PROFILE)
        self.assertEqual(self.s.list_products(self.c),[])
        self.assertFalse(any(p['name']=='Participante externo fictício' for p in self.s.list_participants(self.c)))
        self.assertTrue(any('somente preservado' in issue for o in self.s.list_observations(self.c) for issue in o['issues']))

    def test_separate_catalog_profile_reuses_saved_originals_without_rewriting_analysis(self):
        file=self.xml(product_xml())
        before=self.s.db.execute('SELECT * FROM file_indexings WHERE file_id=?',(file['id'],)).fetchone()
        with self.s.db:
            self.s.db.execute('DELETE FROM product_observations');self.s.db.execute('DELETE FROM products')
        result=self.s.index_file(self.c,file['id'],CATALOG_PROFILE)
        self.assertFalse(result['duplicate'])
        self.assertEqual(len(self.s.list_products(self.c)),1)
        self.assertTrue(self.s.index_file(self.c,file['id'],CATALOG_PROFILE)['duplicate'])
        after=self.s.db.execute('SELECT * FROM file_indexings WHERE id=?',(before['id'],)).fetchone()
        self.assertEqual(dict(before),dict(after))
        record=['0200','SPED-FICTICIO','Produto SPED fictício','SEM GTIN','','UN','00','00000000','','00','','0,00','']
        saved=self.s.import_file(self.c,self.p,'ficticio.txt',catalog_sped(record),'SPED')
        self.s.index_file(self.c,saved['id'],CATALOG_PROFILE)
        self.assertEqual(len(self.s.list_products(self.c)),2)
        self.assertEqual(len(self.s.list_documents(self.c)),1)

    def test_schema6_migration_is_additive_and_persists_originals(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'synthetic.sqlite3'
            with AccountingStore(path) as s:
                company=s.create_company('Fictícia','1','1',ISSUER)['id']
                period=s.create_period(company,'2026-09','2026-09')['id']
                file=s.import_file(company,period,'ficticio.xml',fake_xml(),'XML')
                with s.db:
                    s.db.execute('DROP TABLE product_observations');s.db.execute('DROP TABLE products')
                    s.db.execute('DROP TABLE import_items');s.db.execute('DROP TABLE import_batches')
                    s.db.execute('UPDATE schema_version SET version=6')
            with AccountingStore(path) as s:
                self.assertEqual(s.db.execute('SELECT version FROM schema_version').fetchone()[0],18)
                self.assertEqual(bytes(s._owned('files',company,file['id'])['original']),fake_xml())
                self.assertEqual(s.list_import_batches(company),[])
