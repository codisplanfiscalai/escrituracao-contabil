'use strict';
(function(root){
  function cents(value){
    if(typeof value!=='string'||!/^(?:0|[1-9][0-9]{0,15})(?:[.,][0-9]{1,2})?$/.test(value))throw new Error('Informe valor positivo sem separador de milhar, com até duas casas.');
    const [whole,fraction='']=value.replace(',','.').split('.');
    const result=BigInt(whole)*100n+BigInt(fraction.padEnd(2,'0'));
    if(result<=0n)throw new Error('O valor deve ser positivo.');
    return result;
  }
  function money(value){const negative=value<0n;const absolute=negative?-value:value;return (negative?'-':'')+String(absolute/100n)+'.'+String(absolute%100n).padStart(2,'0');}
  function summarize(entries){
    let debit=0n,credit=0n,invalid=0;const groups=new Map();
    for(const entry of entries){
      try{
        if(!/^[1-9][0-9]*$/.test(String(entry.document_id))||!entry.group?.trim()||!['D','C'].includes(entry.side))throw new Error('Linha incompleta');
        const value=cents(entry.amount),key=JSON.stringify([String(entry.document_id),entry.group.trim()]);
        if(!groups.has(key))groups.set(key,{document_id:entry.document_id,group:entry.group.trim(),debit:0n,credit:0n});
        const field=entry.side==='D'?'debit':'credit';groups.get(key)[field]+=value;
        if(field==='debit')debit+=value;else credit+=value;
      }catch{invalid++;}
    }
    const rows=[...groups.values()].map(g=>({...g,debit:money(g.debit),credit:money(g.credit),difference:money(g.debit-g.credit)}));
    return {debit:money(debit),credit:money(credit),difference:money(debit-credit),invalid,groups:rows,balanced:entries.length>=2&&!invalid&&rows.every(g=>g.difference==='0.00')};
  }
  const api={cents,money,normalize:value=>money(cents(value)),summarize};root.PostingMath=api;
  if(typeof module!=='undefined'&&module.exports)module.exports=api;
})(globalThis);
