"""Fetch pinned official test-only applications; never include them in release artifacts."""
import hashlib,json,os,pathlib,stat,subprocess,tarfile,urllib.request
ROOT=pathlib.Path(__file__).resolve().parents[1];WORK=ROOT/'.native';OUT=ROOT/'evidence'
def download(url,target,expected_size,expected_sha):
    request=urllib.request.Request(url,headers={'User-Agent':'GradBefore-native-fixture'})
    total=0;digest=hashlib.sha256()
    with urllib.request.urlopen(request,timeout=90) as response,target.open('wb') as file:
        while True:
            chunk=response.read(1024*1024)
            if not chunk:break
            total+=len(chunk);assert total<=expected_size,'Download exceeds pinned size';digest.update(chunk);file.write(chunk)
    assert total==expected_size and digest.hexdigest()==expected_sha,'Official test asset does not match pin'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true','Hosted native gate only'
    WORK.mkdir(exist_ok=True);OUT.mkdir(exist_ok=True);pins=json.loads((ROOT/'docs/upstream-pins.json').read_text());a=pins['appImage'];image=WORK/'synfig.appimage';download(a['url'],image,a['bytes'],a['sha256']);image.chmod(image.stat().st_mode|stat.S_IXUSR)
    extract=WORK/'synfig-extract';extract.mkdir(exist_ok=True)
    result=subprocess.run([str(image),'--appimage-extract'],cwd=extract,capture_output=True,text=True,timeout=120);assert result.returncode==0,result.stderr[-2000:]
    app=extract/'squashfs-root';assert (app/'AppRun').is_file();cli_candidates={p.resolve() for p in app.rglob('synfig') if p.is_file() and p.read_bytes()[:4]==b'\x7fELF'};assert len(cli_candidates)==1,'Expected one official Synfig CLI ELF';cli=cli_candidates.pop();assert cli.is_relative_to(app.resolve())
    modules=list(app.rglob('synfig_modules.cfg'));assert len(modules)==1,'Expected one vendor module configuration';module=modules[0];prefix=module.parent.parent
    identity={'version':'1.5.5','commit':pins['commit'],'appImage':a,'launcher':str(app/'AppRun'),'cli':str(cli),'prefix':str(prefix),'moduleList':str(module),'launcherSHA256':sha(app/'AppRun'),'cliSHA256':sha(cli),'moduleListSHA256':sha(module)}
    wrappers=[p for p in [app/'synfig',prefix/'synfig'] if p.is_file() and p.read_bytes().startswith(b'#!')]
    identity['cliWrapper']=str(wrappers[0]) if wrappers else None
    (WORK/'synfig-runtime.json').write_text(json.dumps(identity,indent=2)+'\n')
    cleaner=pins['svgcleaner'];archive=WORK/'svgcleaner.tar.gz';download(cleaner['url'],archive,cleaner['bytes'],cleaner['sha256'])
    with tarfile.open(archive) as tar:
        members=tar.getmembers();assert len(members)==1 and members[0].name=='svgcleaner' and members[0].isfile() and members[0].size<4*1024*1024
        (WORK/'svgcleaner').write_bytes(tar.extractfile(members[0]).read())
    (WORK/'svgcleaner').chmod(0o700)
    sources=[]
    for record in pins['sources']:
        url='https://raw.githubusercontent.com/'+pins['repository']+'/'+pins['commit']+'/'+record['path']
        with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'GradBefore-native-fixture'}),timeout=60) as r:data=r.read(2*1024*1024+1)
        assert len(data)<=2*1024*1024 and hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==record['gitBlobSHA']
        sources.append({**record,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
    (OUT/'native-provenance.json').write_text(json.dumps({'synfig':identity,'sourcePins':sources,'svgcleaner':{**cleaner,'binarySHA256':sha(WORK/'svgcleaner')},'scope':'Verified official test-only binaries; no vendor application/source payload is uploaded in the source or evidence archive'},indent=2)+'\n')
if __name__=='__main__':main()
