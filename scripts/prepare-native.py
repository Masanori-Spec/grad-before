"""Fetch pinned official test-only applications; never include them in release artifacts."""
import hashlib,json,os,pathlib,posixpath,stat,subprocess,tarfile,urllib.request
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
def safe_extract_tar(archive,app):
    assert archive.stat().st_size<=512*1024*1024,'Repacked archive exceeds bound'
    with tarfile.open(archive) as tar:
        members=tar.getmembers();assert 0<len(members)<=20000
        table={};total=0
        for member in members:
            path=pathlib.PurePosixPath(member.name);assert not path.is_absolute() and '..' not in path.parts and len(member.name)<=1024,'Unsafe archive path'
            name=str(path);assert name not in table,'Duplicate archive path';table[name]=member
            assert member.isdir() or member.isfile() or member.issym() or member.islnk(),'Unexpected archive entry type'
            assert not member.mode&0o6000,'Unexpected special permission bits'
            if member.isfile():total+=member.size
            assert 0<=member.size<=512*1024*1024 and total<=512*1024*1024,'Expanded official asset exceeds bound'
            if member.issym() or member.islnk():
                target=pathlib.PurePosixPath(member.linkname);assert not target.is_absolute() and len(member.linkname)<=1024,'Absolute archive link'
                target=posixpath.normpath(posixpath.join(str(path.parent) if member.issym() else '',member.linkname));assert target!='..' and not target.startswith('../'),'Archive link escaped root'
        for name,member in table.items():
            assert all(str(parent) not in table or table[str(parent)].isdir() for parent in pathlib.PurePosixPath(name).parents),'Archive entry has a nondirectory parent'
        app.mkdir(parents=True,exist_ok=False);root=app.resolve()
        # Materialize regular files before links, so no archive link can redirect writes.
        for name,member in table.items():
            path=app/name
            if member.isdir():path.mkdir(parents=True,exist_ok=True)
            elif member.isfile():
                path.parent.mkdir(parents=True,exist_ok=True)
                with tar.extractfile(member) as source,path.open('xb') as destination:
                    remaining=member.size
                    while remaining:
                        chunk=source.read(min(remaining,1024*1024));assert chunk;destination.write(chunk);remaining-=len(chunk)
                path.chmod(member.mode&0o777)
        pending=[(name,m) for name,m in table.items() if m.islnk()]
        while pending:
            next_pending=[]
            for name,member in pending:
                target=app/posixpath.normpath(member.linkname)
                if not target.exists():next_pending.append((name,member));continue
                assert target.is_file() and not target.is_symlink() and target.resolve().is_relative_to(root),'Unsafe hardlink target'
                path=app/name;path.parent.mkdir(parents=True,exist_ok=True);os.link(target,path,follow_symlinks=False)
            assert len(next_pending)<len(pending),'Missing or cyclic hardlink target';pending=next_pending
        for name,member in table.items():
            if member.issym():
                path=app/name;path.parent.mkdir(parents=True,exist_ok=True);path.symlink_to(member.linkname)
    for path in app.rglob('*'):
        assert path.resolve().is_relative_to(root),'Extracted path escaped the disposable directory'
    return {'entries':len(table),'symlinks':sum(m.issym() for m in members),'hardlinks':sum(m.islnk() for m in members),'regularBytes':total,'allPathsAndLinksContained':True}
def extract_type1(image,app):
    with image.open('rb') as f:
        header=f.read(32);f.seek(32768);iso=f.read(7)
    assert header[:4]==b'\x7fELF' and header[8:11]==b'AI\x01' and iso==b'\x01CD001\x01','Expected pinned type-1 ISO9660 AppImage'
    # bsdtar reads ISO9660 directly; it does not execute or mount the AppImage runtime.
    archive=image.with_suffix('.tar');assert not archive.exists()
    subprocess.run(['bsdtar','-cf',str(archive),'@'+str(image)],check=True,capture_output=True,text=True,timeout=120)
    return {'format':'type-1 ISO9660','header32Hex':header.hex(),'isoPrimaryDescriptorHex':iso.hex(),'extractor':subprocess.run(['bsdtar','--version'],capture_output=True,text=True,check=True).stdout.strip(),**safe_extract_tar(archive,app)}
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true','Hosted native gate only'
    WORK.mkdir(exist_ok=True);OUT.mkdir(exist_ok=True);pins=json.loads((ROOT/'docs/upstream-pins.json').read_text());a=pins['appImage'];image=WORK/'synfig.appimage';download(a['url'],image,a['bytes'],a['sha256'])
    (OUT/'native-preparation.json').write_text(json.dumps({'verifiedAppImage':a,'stage':'download digest and size verified'},indent=2)+'\n')
    app=WORK/'synfig-extract';extraction=extract_type1(image,app)
    (OUT/'native-preparation.json').write_text(json.dumps({'verifiedAppImage':a,'extraction':extraction,'stage':'archive extraction and containment verified'},indent=2)+'\n')
    assert (app/'AppRun').is_file();cli_candidates={p.resolve() for p in app.rglob('synfig') if p.is_file() and p.read_bytes()[:4]==b'\x7fELF'};assert len(cli_candidates)==1,'Expected one official Synfig CLI ELF';cli=cli_candidates.pop();assert cli.is_relative_to(app.resolve())
    modules=list(app.rglob('synfig_modules.cfg'));assert len(modules)==1,'Expected one vendor module configuration';module=modules[0];prefix=module.parent.parent
    gui=prefix/'bin/synfigstudio';assert gui.is_file() and gui.read_bytes()[:4]==b'\x7fELF' and gui.resolve().is_relative_to(app.resolve())
    identity={'version':'1.5.5','commit':pins['commit'],'appImage':a,'appDir':str(app),'launcher':str(gui),'cli':str(cli),'prefix':str(prefix),'moduleList':str(module),'launcherSHA256':sha(gui),'cliSHA256':sha(cli),'moduleListSHA256':sha(module),'vendorAppRunSHA256':sha(app/'AppRun'),'vendorLaunchScriptSHA256':sha(prefix/'bin/launch.sh'),'vendorIntegrationWrapperSHA256':sha(prefix/'bin/synfigstudio.wrapper'),'extraction':extraction}
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
