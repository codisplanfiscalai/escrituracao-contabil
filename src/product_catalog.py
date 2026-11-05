"""Observed product identities. Supplier codes and SPED codes are never merged."""
import json
from .accounting_store import dump, identifier

PRODUCT_SCHEMA = """
CREATE TABLE IF NOT EXISTS products (
 id INTEGER PRIMARY KEY, company_id INTEGER NOT NULL REFERENCES companies(id),
 namespace TEXT NOT NULL, code TEXT NOT NULL, data TEXT NOT NULL, version INTEGER NOT NULL DEFAULT 1,
 UNIQUE(company_id,namespace,code));
CREATE TABLE IF NOT EXISTS product_observations (
 id INTEGER PRIMARY KEY, company_id INTEGER NOT NULL REFERENCES companies(id),
 product_id INTEGER REFERENCES products(id), file_id INTEGER NOT NULL REFERENCES files(id),
 locator TEXT NOT NULL, data TEXT NOT NULL, state TEXT NOT NULL, issues TEXT NOT NULL,
 UNIQUE(file_id,locator));
"""


class ProductCatalogMixin:
    def _observe_product(self, company_id, file_id, namespace, locator, data):
        if self.db.execute('SELECT 1 FROM product_observations WHERE file_id=? AND locator=?', (file_id, locator)).fetchone():
            return
        code = data.get('code', '').strip()
        product_id = None
        state = 'coincidente'
        issues = []
        if not code:
            state = 'pendente'
            issues.append('Código ausente na origem; nenhuma identidade de produto criada')
        else:
            row = self.db.execute('SELECT * FROM products WHERE company_id=? AND namespace=? AND code=?', (company_id, namespace, code)).fetchone()
            if row:
                product_id = row['id']
                if json.loads(row['data']) != data:
                    state = 'pendente'
                    issues.append('Cadastro divergente; representação anterior preservada para revisão')
                self.db.execute('UPDATE products SET version=version+1 WHERE id=?', (product_id,))
            else:
                product_id = self.db.execute('INSERT INTO products(company_id,namespace,code,data) VALUES(?,?,?,?)', (company_id, namespace, code, dump(data))).lastrowid
                self._audit(company_id, 'produto_observado', {'product_id': product_id, 'file_id': file_id, 'locator': locator})
        if not data.get('description'):
            state = 'pendente'
            issues.append('Descrição ausente na origem')
        self.db.execute('INSERT INTO product_observations(company_id,product_id,file_id,locator,data,state,issues) VALUES(?,?,?,?,?,?,?)',
                        (company_id, product_id, file_id, locator, dump(data), state, dump(issues)))

    def list_products(self, company_id):
        self._company(company_id)
        result = []
        for row in self.db.execute('SELECT * FROM products WHERE company_id=? ORDER BY id DESC', (company_id,)):
            item = dict(row)
            item['data'] = json.loads(item['data'])
            item['observations'] = [{**dict(o), 'data': json.loads(o['data']), 'issues': json.loads(o['issues'])} for o in self.db.execute(
                'SELECT o.*,f.status AS file_status FROM product_observations o JOIN files f ON f.id=o.file_id WHERE product_id=? ORDER BY o.id DESC', (row['id'],))]
            active = [o for o in item['observations'] if o['file_status'] != 'excluido']
            item['pending'] = not active or any(o['state'] == 'pendente' for o in active) or not any(o['data'] == item['data'] for o in active)
            result.append(item)
        return result

    def review_product(self, company_id, product_id, version, observation_id, reason):
        from .persistence import _text
        self._company(company_id)
        reason = _text(reason, 'motivo da revisão do produto', 2000)
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            product = self.db.execute('SELECT * FROM products WHERE company_id=? AND id=?', (company_id, identifier(product_id))).fetchone()
            observation = self.db.execute('SELECT o.* FROM product_observations o JOIN files f ON f.id=o.file_id WHERE o.company_id=? AND o.product_id=? AND o.id=? AND f.status!=?',
                                          (company_id, identifier(product_id), identifier(observation_id), 'excluido')).fetchone()
            if not product or type(version) is not int or product['version'] != version or not observation or not json.loads(observation['data']).get('description'):
                raise ValueError('Produto alterado, origem incompleta ou fora da empresa; recarregue')
            self.db.execute('UPDATE products SET data=?,version=version+1 WHERE id=?', (observation['data'], product['id']))
            self.db.execute("UPDATE product_observations SET state='conferido' WHERE product_id=?", (product['id'],))
            self._audit(company_id, 'produto_revisado', {'product_id': product['id'], 'before': dict(product), 'observation_id': observation['id'], 'reason': reason})
        return next(p for p in self.list_products(company_id) if p['id'] == product['id'])
