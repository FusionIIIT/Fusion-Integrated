import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link, useParams } from 'react-router-dom';
import { Alert, Badge, Button, Card, Checkbox, Container, FileInput, Group, Loader, Modal, Select, Stack, Text, Textarea, TextInput, Title } from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { useAuth } from '../../auth/AuthProvider';
import { errorMessage, http } from '../../lib/http';
import { ErrorState } from '../../ui/components/ErrorState';

interface Person {user_id:number; display_name:string}
interface Course {id:number; code:string; title:string; year:number; semester_type:string; role:string; may_announce:boolean; instructors:Person[]; tas:Person[]}
interface Material {id:number; title:string; section:string; kind:string; text:string; link:string; release_at:string|null; state:string; download_url:string|null}
interface Assignment {id:number; title:string; instructions:string; submission_type:string; points_possible:string; due_at:string; release_at:string|null; state:string; download_url:string}
interface Submission {id:number; assignment_id:number; student_id:number; text:string; link:string; submitted_at:string; points:string|null; feedback:string; released:boolean; revision:number; download_url:string|null}
interface CourseData {id:number; course:Course; syllabus:string; schedule:string; materials:Material[]; assignments:Assignment[]; announcements:{id:number; title:string; body:string; created_at:string}[]; submissions:Submission[]}
type Kind = 'details'|'material'|'assignment'|'announcement'|'submission'|'grade';
interface Editor {kind:Kind; itemId?:number; values:Record<string,string>}

function useLms<T>(path:string) {
  const {session} = useAuth();
  return useQuery({queryKey:['lms', session?.user.id, session?.active_role, path],
    queryFn:async ()=>(await http.get<T>(`/lms/${path}`)).data, enabled:Boolean(session), retry:false});
}
function localDate(value:string|null) {
  if (!value) return '';
  const date = new Date(value);
  return new Date(date.getTime()-date.getTimezoneOffset()*60000).toISOString().slice(0,16);
}
async function download(path:string) {
  try {
    const response=await http.get(path.replace(/^\/api\/v1/,''), {responseType:'blob'});
    const url=URL.createObjectURL(response.data); const a=document.createElement('a');
    a.href=url; a.download='lms-file'; a.click(); URL.revokeObjectURL(url);
  } catch(e) {notifications.show({color:'red',message:errorMessage(e)});}
}

export function Courses() {
  const query=useLms<{results:Course[]}>('courses/');
  return <Container><Stack><Title order={2}>Course Management</Title>
    {query.isPending && <Loader />}{query.error && <ErrorState error={query.error} />}
    {query.data?.results.map((c)=><Card key={`${c.id}-${c.role}`} withBorder>
      <Title order={3}><Link to={`/lms/courses/${c.id}`}>{c.code} · {c.title}</Link></Title>
      <Text>{c.year} · {c.semester_type} · {c.role}</Text>
    </Card>)}
    {query.data && !query.data.results.length && <Text>No course associations are available for your active role.</Text>}
  </Stack></Container>;
}

export function Workspace() {
  const {id}=useParams(); const {can}=useAuth(); const cache=useQueryClient();
  const query=useLms<CourseData>(`courses/${id}/`); const data=query.data;
  const [editor,setEditor]=useState<Editor|null>(null); const [file,setFile]=useState<File|null>(null);
  const write=useMutation({mutationFn:async ({path,body}:{path:string;body:unknown})=>(await http.post(`/lms/${path}`,body)).data,
    onSuccess:()=>cache.invalidateQueries({queryKey:['lms']})});
  function edit(kind:Kind, itemId?:number, values:Record<string,string>={}) {
    setFile(null); setEditor({kind,itemId,values});
  }
  async function send(path:string, body:unknown) {
    try {await write.mutateAsync({path,body}); setEditor(null); notifications.show({message:'Saved.'});}
    catch(e) {notifications.show({color:'red',message:errorMessage(e)});}
  }
  async function save() {
    if (!editor) return;
    let path=`courses/${id}/write/${editor.kind}/${editor.itemId ? `${editor.itemId}/` : ''}`;
    if (editor.kind==='submission') path=`courses/${id}/assignments/${editor.itemId}/submit/`;
    if (editor.kind==='grade') path=`courses/${id}/submissions/${editor.itemId}/grade/`;
    const body=new FormData();
    for(const [key,value] of Object.entries(editor.values)) body.append(key,value);
    if (editor.kind==='material' && !editor.values.kind) body.append('kind','text');
    if (editor.kind==='assignment' && !editor.values.submission_type) body.append('submission_type','text');
    if (file) body.append('file',file);
    await send(path,body);
  }
  function input(key:string,label:string,type='text') {
    const props={label,value:editor?.values[key]??'',onChange:(e:React.ChangeEvent<HTMLInputElement|HTMLTextAreaElement>)=>setEditor((old)=>old?{...old,values:{...old.values,[key]:e.currentTarget.value}}:null)};
    return type==='textarea'?<Textarea key={key} {...props} />:<TextInput key={key} {...props} type={type} />;
  }
  if (query.isPending) return <Loader />;
  if (query.error) return <ErrorState error={query.error} />;
  if (!data) return null;
  const role=data.course.role, faculty=role==='faculty', reviewer=faculty||role==='ta';
  return <Container size="lg"><Stack>
    <Link to="/lms/courses">My courses</Link><Title order={2}>{data.course.code} · {data.course.title}</Title>
    <Text>{data.course.year} · {data.course.semester_type} · {role}</Text>
    <Text>Faculty: {data.course.instructors.map((p)=>p.display_name||p.user_id).join(', ')||'Not supplied'}</Text>
    <Text>TAs: {data.course.tas.map((p)=>p.display_name||p.user_id).join(', ')||'Not supplied'}</Text>
    <Card withBorder><Title order={3}>Course home</Title><Text style={{whiteSpace:'pre-wrap'}}>{data.syllabus||'Syllabus not entered.'}</Text><Text style={{whiteSpace:'pre-wrap'}}>{data.schedule}</Text>
      {faculty&&can('lms.course.manage')&&<Button mt="sm" onClick={()=>edit('details',undefined,{syllabus:data.syllabus,schedule:data.schedule})}>Edit course details</Button>}</Card>
    <Group justify="space-between"><Title order={3}>Materials</Title>{faculty&&can('lms.material.manage')&&<Button onClick={()=>edit('material',undefined,{kind:'text',publish:'true'})}>Add material</Button>}</Group>
    {data.materials.map((m)=><Card withBorder key={m.id}><Group><Title order={4}>{m.section} · {m.title}</Title><Badge>{m.state}</Badge></Group>
      <Text style={{whiteSpace:'pre-wrap'}}>{m.text}</Text>{m.link&&<a href={m.link} rel="noopener noreferrer">Open link</a>}
      <Group>{m.download_url&&<Button variant="light" onClick={()=>download(m.download_url!)}>Download material</Button>}
        {faculty&&<Button variant="subtle" onClick={()=>edit('material',m.id,{title:m.title,section:m.section,kind:m.kind,text:m.text,link:m.link,release_at:localDate(m.release_at),publish:String(m.state!=='draft')})}>Edit material</Button>}</Group></Card>)}
    <Group justify="space-between"><Title order={3}>Announcements</Title>{(faculty||(role==='ta'&&data.course.may_announce))&&can('lms.announcement.create')&&<Button onClick={()=>edit('announcement')}>Post announcement</Button>}</Group>
    {data.announcements.map((a)=><Card withBorder key={a.id}><Title order={4}>{a.title}</Title><Text size="sm" c="dimmed">{new Date(a.created_at).toLocaleString()}</Text><Text style={{whiteSpace:'pre-wrap'}}>{a.body}</Text></Card>)}
    {role!=='observer'&&<><Group justify="space-between"><Title order={3}>Assignments</Title>{faculty&&can('lms.assignment.manage')&&<Button onClick={()=>edit('assignment',undefined,{submission_type:'text'})}>Create assignment</Button>}</Group>
      {data.assignments.map((a)=><Card withBorder key={a.id}><Group><Title order={4}>{a.title}</Title><Badge>{a.state}</Badge></Group>
        <Text>{a.points_possible} points · {a.submission_type} · Due {new Date(a.due_at).toLocaleString()}</Text><Text style={{whiteSpace:'pre-wrap'}}>{a.instructions}</Text>
        {role==='student'&&!data.submissions.some((s)=>s.assignment_id===a.id)&&<Text c="dimmed">{new Date(a.due_at).getTime()<Date.now()?'Missing; late-submission policy is unresolved.':'Not submitted.'}</Text>}
        <Group mt="sm"><Button variant="light" onClick={()=>download(a.download_url)}>Download assignment</Button>
          {faculty&&a.state==='draft'&&<><Button variant="light" onClick={()=>edit('assignment',a.id,{title:a.title,instructions:a.instructions,submission_type:a.submission_type,points_possible:a.points_possible,due_at:localDate(a.due_at),release_at:localDate(a.release_at)})}>Edit draft</Button><Button loading={write.isPending} onClick={()=>send(`courses/${id}/assignments/${a.id}/publish/`,{})}>Publish</Button></>}
          {role==='student'&&can('lms.submission.create')&&<Button onClick={()=>edit('submission',a.id)}>Submit work</Button>}
        </Group></Card>)}
      <Title order={3}>Submissions and grades</Title>{data.submissions.map((s)=><Card withBorder key={s.id}>
        <Text>Assignment #{s.assignment_id}{reviewer&&` · Student ${s.student_id}`} · Submitted {new Date(s.submitted_at).toLocaleString()}</Text>
        <Text style={{whiteSpace:'pre-wrap'}}>{s.text}</Text>{s.link&&<a href={s.link} rel="noopener noreferrer">Submitted link</a>}
        <Text>{s.released||reviewer?`Points: ${s.points??'Not graded'}`:'Grade and feedback not released.'}</Text><Text>{s.feedback}</Text>
        <Group>{s.download_url&&<Button variant="light" onClick={()=>download(s.download_url!)}>Download submission</Button>}
          {reviewer&&can('lms.submission.review')&&!s.released&&<Button onClick={()=>edit('grade',s.id,{points:s.points??'',feedback:s.feedback,revision:String(s.revision)})}>Grade</Button>}
          {faculty&&can('lms.grade.publish')&&s.points!==null&&!s.released&&<Button loading={write.isPending} onClick={()=>send(`courses/${id}/submissions/${s.id}/release/`,{revision:s.revision})}>Release grade</Button>}
        </Group></Card>)}</>}
    <Modal opened={editor!==null} onClose={()=>setEditor(null)} title={editor?.kind}><Stack>
      {editor?.kind==='details'&&<>{input('syllabus','Syllabus','textarea')}{input('schedule','Schedule','textarea')}</>}
      {(editor?.kind==='material'||editor?.kind==='assignment'||editor?.kind==='announcement')&&input('title','Title')}
      {editor?.kind==='announcement'&&input('body','Announcement','textarea')}
      {editor?.kind==='material'&&<>{input('section','Module / week')}<Select label="Material type" data={['text','link','file']} value={editor.values.kind??'text'} onChange={(v)=>setEditor({...editor,values:{...editor.values,kind:v??'text'}})} />{input('text','Notes','textarea')}{input('link','Link','url')}{input('release_at','Release at (optional)','datetime-local')}<Checkbox label="Publish / schedule" checked={editor.values.publish==='true'} onChange={(e)=>setEditor({...editor,values:{...editor.values,publish:String(e.currentTarget.checked)}})} /></>}
      {editor?.kind==='assignment'&&<>{input('instructions','Instructions','textarea')}<Select label="Submission type" data={['text','link','file']} value={editor.values.submission_type??'text'} onChange={(v)=>setEditor({...editor,values:{...editor.values,submission_type:v??'text'}})} />{input('points_possible','Points possible','number')}{input('due_at','Due at','datetime-local')}{input('release_at','Release at (optional)','datetime-local')}</>}
      {editor?.kind==='submission'&&<><Text size="sm">Provide the type configured for this assignment.</Text>{input('text','Text submission','textarea')}{input('link','Link submission','url')}</>}
      {editor?.kind==='grade'&&<>{input('points','Points','number')}{input('feedback','Feedback','textarea')}</>}
      {editor&&['material','assignment','submission'].includes(editor.kind)&&<FileInput label="File (maximum 10 MB)" value={file} onChange={setFile} />}
      {write.error&&<ErrorState error={write.error} />}<Button loading={write.isPending} onClick={save}>Save</Button>
    </Stack></Modal>
    <Alert color="gray">Late submissions, resubmissions and released-grade edits await policy resolution. Notification delivery channels are not configured.</Alert>
  </Stack></Container>;
}
