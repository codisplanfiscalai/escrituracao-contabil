"""Bounded observations of processed NF-e events; never proof of authorization."""
import hashlib
import re
from datetime import datetime
import xml.etree.ElementTree as ET

NS={'n':'http://www.portalfiscal.inf.br/nfe'}
PROFILE='nfe-evento-processado-1.00-v1'
SOURCES={name:'https://moc.sped.fazenda.pr.gov.br/NFe_NFCe/RecepcaoEvento'+page+'.html'
         for name,page in [('general','Geral'),('cancellation','Cancelamento'),('correction','CartaCorrecao')]}


def xml_root(content):
    if not isinstance(content,bytes) or len(content)>10*1024*1024:raise ValueError('XML ausente ou acima de 10 MiB')
    if b'\x00' in content or re.search(rb'<!\s*(DOCTYPE|ENTITY)\b',content,re.I):raise ValueError('XML com DTD, entidades ou encoding não suportado')
    try:return ET.fromstring(content)
    except (ET.ParseError,ValueError) as error:raise ValueError('XML malformado') from error


def is_event_xml(content):
    return xml_root(content).tag=='{'+NS['n']+'}procEventoNFe'


def parse_nfe_event(content):
    root=xml_root(content)
    if root.tag!='{'+NS['n']+'}procEventoNFe' or root.get('versao')!='1.00':raise ValueError('Perfil aceita somente procEventoNFe 1.00')
    if len(root)!=2 or {c.tag for c in root}!={'{'+NS['n']+'}evento','{'+NS['n']+'}retEvento'}:raise ValueError('Envelope processado contém grupos ausentes, repetidos ou fora do perfil')
    fields={};issues=[]
    def child(parent,name):
        nodes=parent.findall('n:'+name,NS)
        if len(nodes)!=1:raise ValueError('Grupo ausente ou repetido: '+name)
        return nodes[0]
    def value(parent,name,prefix,required=True,pattern=None,limit=2000):
        nodes=parent.findall('n:'+name,NS)
        if len(nodes)>1 or (required and not nodes):raise ValueError('Campo ausente ou repetido: '+prefix+'/'+name)
        if not nodes:return ''
        if list(nodes[0]):raise ValueError('Campo escalar contém estrutura: '+name)
        raw=nodes[0].text or '';text=raw.strip()
        if len(raw)>limit or (required and not text) or (text and pattern and not re.fullmatch(pattern,text)):
            raise ValueError('Campo fora do perfil: '+prefix+'/'+name)
        fields[prefix+'/'+name]={'path':prefix+'/'+name,'raw':raw,'value':text}
        return text
    def timestamp(text):
        try:dt=datetime.fromisoformat(text.replace('Z','+00:00'))
        except ValueError as error:raise ValueError('Data/hora do evento inválida') from error
        if dt.tzinfo is None or not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:Z|[+-]\d{2}:\d{2})',text):raise ValueError('Data/hora exige fuso explícito no perfil')
    event=child(root,'evento');returned=child(root,'retEvento')
    if event.get('versao')!='1.00' or returned.get('versao')!='1.00':raise ValueError('Versões de evento/retEvento não suportadas')
    info=child(event,'infEvento');ret=child(returned,'infEvento');p='procEventoNFe/evento/infEvento';r='procEventoNFe/retEvento/infEvento'
    key=value(info,'chNFe',p,pattern=r'\d{44}')
    model=key[20:22]
    if model not in {'55','65'}:raise ValueError('Chave fora dos modelos 55/65')
    kind=value(info,'tpEvento',p,pattern=r'110111|110110')
    sequence=value(info,'nSeqEvento',p,pattern=r'[0-9]{1,2}')
    if not 1<=int(sequence)<=99:raise ValueError('Sequência do evento fora do perfil')
    event_id=info.get('Id','')
    if event_id!='ID'+kind+key+sequence.zfill(2):raise ValueError('Id não corresponde ao tipo, chave e sequência')
    environment=value(info,'tpAmb',p,pattern='1|2');org=value(info,'cOrgao',p,pattern=r'\d{2}')
    author_cnpj=value(info,'CNPJ',p,False,r'\d{14}');author_cpf=value(info,'CPF',p,False,r'\d{11}')
    if bool(author_cnpj)==bool(author_cpf):raise ValueError('Informe exatamente um autor CNPJ/CPF numérico no perfil')
    occurred=value(info,'dhEvento',p);timestamp(occurred)
    if value(info,'verEvento',p)!='1.00':raise ValueError('Versão específica do evento não suportada')
    detail=child(info,'detEvento')
    if detail.get('versao')!='1.00':raise ValueError('Versão detEvento não suportada')
    desc=value(detail,'descEvento',p+'/detEvento',limit=60)
    if desc not in ({'Cancelamento'} if kind=='110111' else {'Carta de Correcao','Carta de Correção'}):raise ValueError('Descrição do evento fora do perfil do tipo informado')
    if kind=='110111':
        value(detail,'nProt',p+'/detEvento',pattern=r'\d{15}',limit=15)
        text=value(detail,'xJust',p+'/detEvento',limit=255)
        if len(text)<15:raise ValueError('Justificativa de cancelamento com menos de 15 caracteres')
    else:
        text=value(detail,'xCorrecao',p+'/detEvento',limit=1000)
        value(detail,'xCondUso',p+'/detEvento')
        if len(text)<15:raise ValueError('Texto da CC-e com menos de 15 caracteres')
        if model=='65':issues.append('CC-e não se aplica à NFC-e modelo 65; fluxo não suportado')
        if int(sequence)>20:issues.append('Sequência de CC-e acima de 20; fluxo não suportado')
    if value(ret,'tpAmb',r,pattern='1|2')!=environment or value(ret,'cOrgao',r,pattern=r'\d{2}')!=org:
        raise ValueError('Ambiente/órgão do retorno diverge do pedido')
    code=value(ret,'cStat',r,pattern=r'\d{3,4}');reason=value(ret,'xMotivo',r,limit=255)
    value(ret,'verAplic',r,limit=20)
    matches={'chNFe':key,'tpEvento':kind,'nSeqEvento':sequence}
    for name,expected in matches.items():
        observed=value(ret,name,r,False)
        if not observed:issues.append('Retorno sem '+name+'; correlação incompleta')
        elif (int(observed)!=int(expected) if name=='nSeqEvento' and observed.isdigit() else observed!=expected):raise ValueError('Pedido e retorno divergem em '+name)
    registered=value(ret,'dhRegEvento',r,False)
    if registered:timestamp(registered)
    protocol=value(ret,'nProt',r,False,r'\d{15}',15)
    value(ret,'xEvento',r,False,limit=60)
    if code=='135' and (not protocol or not registered):issues.append('Registro 135 sem protocolo/data; retorno incompleto')
    known_info={'cOrgao','tpAmb','CNPJ','CPF','chNFe','dhEvento','tpEvento','nSeqEvento','verEvento','detEvento'}
    known_detail={'descEvento','nProt','xJust'} if kind=='110111' else {'descEvento','xCorrecao','xCondUso'}
    unhandled=[p+'/'+c.tag for c in info if c.tag not in {'{'+NS['n']+'}'+x for x in known_info}]
    unhandled += [p+'/detEvento/'+c.tag for c in detail if c.tag not in {'{'+NS['n']+'}'+x for x in known_detail}]
    if unhandled:issues.append('Há campos específicos fora do perfil; tratamento individual necessário')
    return {'profile':PROFILE,'layout':{'sources':dict(SOURCES),'verified_on':'2026-11-06','access':'conteudo oficial indexado; acesso direto HTTP 403'},
            'file_sha256':hashlib.sha256(content).hexdigest(),'key':key,'model':model,'event_type':kind,'sequence':int(sequence),'environment':environment,
            'event_id':event_id,'author':author_cnpj or author_cpf,'occurred_at':occurred,'description':desc,'text':text,
            'return_code':code,'return_reason':reason,'event_protocol':protocol,'registered_at':registered,
            'reported_result':{'135':'registro_vinculado_informado','136':'registro_sem_vinculo_informado'}.get(code,'outro_status_informado'),
            'fields':fields,'issues':issues,'unhandled':unhandled,'authorization_verified':False,
            'limits':['Sem validação XSD/assinatura/consulta SEFAZ','Pedido e retorno são informações do arquivo recebido','Nenhum dado ou efeito fiscal substituído automaticamente']}
