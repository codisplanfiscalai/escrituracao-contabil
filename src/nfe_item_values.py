"""Observed NF-e/NFC-e 4.00 fields, independent of legal tax classification.

Paths checked against SEF/MG's published PL_010b_NT2025_002_v1.30 tree.
This is a bounded reader, not XSD, signature or authorization validation.
"""
import hashlib
import re
from decimal import Decimal
import xml.etree.ElementTree as ET

PROFILE='nfe-nfce-4.00-item-values-v1'
LAYOUT={'publisher':'SEF/MG','schema':'PL_010b_NT2025_002_v1.30',
        'url':'https://portalsped.fazenda.mg.gov.br/spedmg/nfe/download/EstruturaNFe.html',
        'verified_on':'2026-11-06'}
PRODUCT_TEXT=('cProd','xProd','NCM','CFOP','uCom','indTot')
PRODUCT_NUMBERS=('qCom','vUnCom','vProd','vFrete','vSeg','vDesc','vOutro')
TAX_FIELDS={
    'ICMS/ICMS00':('orig','CST','vBC','pICMS','vICMS','pFCP','vFCP'),
    'ICMS/ICMS10':('orig','CST','vBC','pICMS','vICMS','vBCST','pICMSST','vICMSST','vBCFCP','pFCP','vFCP','vBCFCPST','pFCPST','vFCPST'),
    'PIS/PISAliq':('CST','vBC','pPIS','vPIS'),
    'COFINS/COFINSAliq':('CST','vBC','pCOFINS','vCOFINS'),
}
BASE_PATHS={'icms_base':('ICMS/ICMS00/vBC','ICMS/ICMS10/vBC'),
            'st_base':('ICMS/ICMS10/vBCST',),'fcp_base':('ICMS/ICMS10/vBCFCP',),
            'pis_base':('PIS/PISAliq/vBC',),'cofins_base':('COFINS/COFINSAliq/vBC',)}


def extract_item_values(content):
    from .persistence import parse_nfe,NS,MAX_FILE_BYTES
    if not isinstance(content,bytes) or len(content)>MAX_FILE_BYTES:raise ValueError('XML ausente ou acima do limite de 10 MiB')
    header=parse_nfe(content)  # Existing root/version/model, DTD/entity and encoding guards.
    root=ET.fromstring(content);info=root.find('.//n:infNFe',NS) if root.tag.endswith('nfeProc') else root.find('n:infNFe',NS)
    root_path='nfeProc/NFe/infNFe' if root.tag.endswith('nfeProc') else 'NFe/infNFe'
    details=info.findall('n:det',NS)
    if len(details)>200:raise ValueError('Perfil de itens limitado a 200 detalhes por documento')
    rows=[];seen=set()
    for ordinal,detail in enumerate(details,1):
        number=detail.get('nItem','')
        if not re.fullmatch(r'[1-9][0-9]{0,3}',number) or number in seen:raise ValueError('nItem ausente, inválido ou repetido; detalhes não podem ser confundidos')
        seen.add(number)
        if len(detail.findall('n:prod',NS))!=1:raise ValueError('Cada detalhe exige um único grupo prod')
        fields={};issues=[];locator=f'infNFe/det[{ordinal}]/prod';prefix=f'{root_path}/det[{ordinal}]'
        def observe(path,numeric=False):
            nodes=detail.findall('/'.join('n:'+p for p in path.split('/')),NS)
            if len(nodes)>1:raise ValueError('Campo repetido no XML: '+prefix+'/'+path)
            if not nodes:return
            node=nodes[0]
            if list(node):raise ValueError('Campo escalar contém estrutura não suportada: '+path)
            raw=node.text or '';value=raw.strip();error=''
            if len(raw)>1000:raise ValueError('Campo XML acima do limite do perfil')
            if numeric and (not re.fullmatch(r'[0-9]{1,15}(?:\.[0-9]{1,10})?',value) or (path.split('/')[-1].startswith('v') and path.split('/')[-1] not in {'vUnCom'} and '.' in value and len(value.split('.')[1])>2)):
                error='Valor decimal não suportado pelo perfil; não copiar'
            fields[path]={'path':prefix+'/'+path,'raw':raw,'value':value,'numeric':numeric,'issue':error}
            if error:issues.append(prefix+'/'+path+': '+error)
        for tag in PRODUCT_TEXT:observe('prod/'+tag)
        for tag in PRODUCT_NUMBERS:observe('prod/'+tag,True)
        tax_parents=detail.findall('n:imposto',NS)
        if len(tax_parents)>1:raise ValueError('Grupo imposto repetido')
        unsupported=['det/'+child.tag.removeprefix('{'+NS['n']+'}') for child in detail if child.tag not in {'{'+NS['n']+'}prod','{'+NS['n']+'}imposto'}]
        if tax_parents:
            for group in tax_parents[0]:
                name=group.tag.removeprefix('{'+NS['n']+'}')
                if name in {'ICMS','PIS','COFINS'}:
                    if len(tax_parents[0].findall('n:'+name,NS))>1 or len(group)!=1:raise ValueError('Grupo tributário ausente ou ambíguo: '+name)
                    branch=list(group)[0].tag.removeprefix('{'+NS['n']+'}');key=name+'/'+branch
                    if key not in TAX_FIELDS:unsupported.append('imposto/'+key);continue
                    for tag in TAX_FIELDS[key]:observe('imposto/'+key+'/'+tag,tag.startswith(('v','p')))
                elif name!='vTotTrib':unsupported.append('imposto/'+name)
        bases={}
        for target,paths in BASE_PATHS.items():
            candidates=[fields['imposto/'+p] for p in paths if 'imposto/'+p in fields]
            if len(candidates)==1 and not candidates[0]['issue']:bases[target]=candidates[0]
        if fields.get('prod/indTot',{}).get('value') not in {'0','1'}:issues.append('indTot ausente ou não suportado; nenhuma participação no total presumida')
        rows.append({'nItem':number,'ordinal':ordinal,'source_locator':locator,'fields':fields,'bases':bases,'issues':issues,'unhandled_groups':unsupported})
    # Informative arithmetic only; not vNF and never an allocated item total.
    values=[r['fields'].get('prod/vProd') for r in rows]
    total=format(sum((Decimal(f['value']) for f in values),Decimal(0)),'f') if rows and all(f and not f['issue'] for f in values) else None
    return {'profile':PROFILE,'layout':dict(LAYOUT),'namespace':NS['n'],'file_sha256':hashlib.sha256(content).hexdigest(),
            'key':header['key'],'model':header['model'],'document_total':header['total'],'items':rows,
            'sum_observed_vProd':total,'limits':['Valores observados, sem enquadramento legal','vProd não é total líquido presumido','Campos ausentes não viram zero','CBS/IBS não extraídos nem calculados']}
