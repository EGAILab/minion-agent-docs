"""Emit a reversible apply_patch pair for a real-production-seam mutant.

Never changes files itself. Run from workspace with one of MODES, apply patch,
run the real canonical Rust target, and apply restore before the next mutant.
The temporary helper and fault are both removed by restore.
"""
from pathlib import Path
import difflib,json,sys
ROOT=Path(sys.argv[2]) if len(sys.argv)>2 else Path('.tmp/l0506-d003-rust/code/minion-agent-rust/crates/minion-agent/src')
MODES=['return','drop','hook','end','message','text','nested','keys','numbers','strict-log','log','log-numbers','derive']
mode=sys.argv[1]; assert mode in MODES
original={}; modified={}
def replace(path,old,new):
    p=ROOT/path
    a=modified.get(p,p.read_text(encoding='utf-8')); original.setdefault(p,a)
    assert a.count(old)==1,(path,old,a.count(old))
    modified[p]=a.replace(old,new)
helper=r'''
// TEMPORARY REAL-SEAM NEGATIVE CONTROL, never shipped.
#[cfg(feature="conformance")]
fn __s(s: ResultString) -> ResultString { String::from_utf16_lossy(s.code_units()).into() }
#[cfg(feature="conformance")]
fn __v(v:ResultValue,m:u8)->ResultValue {
    match v {
        ResultValue::String(s) if m==0 || m==2 => ResultValue::String(__s(s)),
        ResultValue::Number(n) if m==4 => {
            let f=n.as_f64(); if !f.is_finite() {ResultValue::Null} else if f==0.0 {ResultValue::number(0.0)} else {ResultValue::number(f)}
        }
        ResultValue::Array(a)=>ResultValue::Array(a.into_iter().map(|v|__v(v,m)).collect()),
        ResultValue::Object(o)=>ResultValue::Object(o.into_iter().map(|(k,v)|(if m==0||m==3 {__s(k)} else {k},__v(v,m))).collect()),
        v=>v,
    }
}
#[cfg(feature="conformance")]
pub fn __fault(mut r:crate::tools::AfterToolCallResult,m:u8)->crate::tools::AfterToolCallResult {
    if m==0||m==1 { for b in &mut r.content { if let super::ToolResultContentBlock::Text(t)=b {t.text=__s(t.text.clone());} } }
    r.details=if m==5 {None} else {r.details.map(|v|__v(v,m))}; r
}
#[cfg(feature="conformance")]
pub fn __message(mut r:super::Message,m:u8)->super::Message {
    if let super::Message::ToolResult(t)=&mut r {
        if m==0||m==1 { for b in &mut t.content {if let super::ToolResultContentBlock::Text(s)=b {s.text=__s(s.text.clone());}} }
        t.details=if m==5 {None} else {t.details.take().map(|v|__v(v,m))};
    }; r
}
'''
p=ROOT/'llm/result_value.rs'; original[p]=p.read_text(encoding='utf-8'); modified[p]=original[p]+helper
if mode=='return':
    replace(Path('tools/execution.rs'),'    let protected = executed.clone();','    let executed = crate::llm::__fault(executed,0);\n    let protected = executed.clone();')
elif mode=='hook':
    p=ROOT/'tools/execution.rs'; original[p]=p.read_text(encoding='utf-8')
    prefix,tail=original[p].split('pub fn register_after_tool_call_hook_with_signal',1)
    old='let future = listener(current.clone());'
    assert tail.count(old)==1
    modified[p]=prefix+'pub fn register_after_tool_call_hook_with_signal'+tail.replace(old,'let mut current=current.clone(); current.result=crate::llm::__fault(current.result,0);\n        '+old)
elif mode=='end':
    replace(Path('tools/execution.rs'),'            result: finalized.clone(),','            result: crate::llm::__fault(finalized.clone(),0),')
elif mode in ['drop','message','text','nested','keys','numbers']:
    number={'drop':5,'message':0,'text':1,'nested':2,'keys':3,'numbers':4}[mode]
    replace(Path('tools/execution.rs'),'    fn into_message(self, timestamp: f64) -> ToolResultMessage {',f'    fn into_message(self, timestamp: f64) -> ToolResultMessage {{\n        let self_=crate::llm::__fault(self,{number});\n        self_.__into_message(timestamp)\n    }}\n    fn __into_message(self,timestamp:f64)->ToolResultMessage {{')
elif mode in ['strict-log','log','log-numbers']:
    old='    ) -> Result<SessionEvent, SessionError> {\n        let mut events = self.inner.events.lock();\n        Ok(Self::append_fields_locked('
    fault='        let _=serde_json::to_value(&message).expect("strict JSON storage");' if mode=='strict-log' else f'        let message=crate::llm::__message(message,{0 if mode=="log" else 4});'
    replace(Path('session/mod.rs'),old,old.replace('        let mut events',fault+'\n        let mut events'))
elif mode=='derive':
    replace(Path('session/mod.rs'),'SessionField::Message(message) => Ok(*message),','SessionField::Message(message) => Ok(crate::llm::__message(*message,0)),')
def patch(a,b):
    lines=['*** Begin Patch']
    for p in a:
        lines+=['*** Update File: '+p.as_posix()]
        lines+=['@@' if s.startswith('@@') else s for s in list(difflib.unified_diff(a[p].splitlines(),b[p].splitlines(),n=15))[2:]]
    lines+=['*** End Patch']
    return '\n'.join(lines)
print(json.dumps({'apply':patch(original,modified),'restore':patch(modified,original)}))

