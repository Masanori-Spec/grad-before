"""Actual Synfig GUI File Import, native save, fresh reopen/save, then CLI rendering."""
import hashlib,importlib.util,json,os,pathlib,shutil,subprocess,time,xml.etree.ElementTree as ET
ROOT=pathlib.Path(__file__).resolve().parents[1];OUT=ROOT/'evidence';WORK=ROOT/'.native'
spec=importlib.util.spec_from_file_location('native_runtime',ROOT/'scripts/native-runtime.py');rt=importlib.util.module_from_spec(spec);spec.loader.exec_module(rt)
progress=[]
def command(*args,timeout=15):return subprocess.run(args,capture_output=True,text=True,check=True,timeout=timeout).stdout
def note(action,**values):
    progress.append({'action':action,**values});(OUT/'native-progress.json').write_text(json.dumps(progress,indent=2)+'\n')
def windows(pattern):
    p=subprocess.run(['xdotool','search','--onlyvisible','--name',pattern],capture_output=True,text=True,timeout=5);return p.stdout.split() if p.returncode==0 else []
def wait(predicate,label,seconds=30):
    end=time.monotonic()+seconds
    while time.monotonic()<end:
        value=predicate()
        if value:return value
        time.sleep(.2)
    raise AssertionError(label)
def activate(window):
    command('xdotool','windowactivate','--sync',window);assert command('xdotool','getactivewindow').strip()==window
    command('xdotool','windowsize',window,'1400','900')
def key(value):command('xdotool','key','--clearmodifiers',value);time.sleep(.15)
def type_text(value):command('xdotool','type','--clearmodifiers','--delay','1',value)
def saved(path):
    try:return path.exists() and path.stat().st_size>100 and ET.parse(path).getroot().tag=='canvas'
    except ET.ParseError:return False
def save_as(path):
    assert not path.exists();key('ctrl+shift+s');wait(lambda:windows('Save'),'Native Save As dialog missing');key('ctrl+l');type_text(str(path));key('Return')
    try:wait(lambda:saved(path),'Native save missing',8)
    except AssertionError:
        assert windows('Save'),'Save did not produce a native document';key('alt+s');wait(lambda:saved(path),'Native Save As did not complete',20)
    wait(lambda:not windows('Save'),'Save dialog remained open');note('native-save-as',file=path.name,sha256=hashlib.sha256(path.read_bytes()).hexdigest())
def native_record(path):
    root=ET.parse(path).getroot();layers=list(root.iter('layer'));types=[n.get('type') for n in layers]
    assert 'svg_layer' not in types and not any(t in ('import','imagemagick','ffmpeg') for t in types),'Imported document retained external/image layer'
    assert not list(root.findall('.//param[@name="filename"]')),'Saved editable document still references an input file'
    gradients=[]
    for layer in layers:
        if layer.get('type') not in ['linear_gradient','radial_gradient']:continue
        stop_nodes=layer.findall('./param[@name="gradient"]/gradient/color');stops=[{'offset':float(c.get('pos')),'rgba':[float(c.findtext(k)) for k in ['r','g','b','a']]} for c in stop_nodes]
        gradients.append({'type':layer.get('type'),'stops':stops})
    return {'layerTypes':types,'gradients':gradients,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
def validate(record,case):
    count=0 if case=='original' else 3;assert len(record['gradients'])==count,(case,record)
    assert record['layerTypes'].count('region')>=4,'Closed artwork was not imported as editable vector regions'
    if count:
        assert sorted(g['type'] for g in record['gradients'])==['linear_gradient','linear_gradient','radial_gradient']
        middle=[1,1,0,1] if case=='altered-stop' else [0,1,0,1]
        expected=[{'offset':0.0,'rgba':[1,0,0,1]},{'offset':0.5,'rgba':middle},{'offset':1.0,'rgba':[0,0,1,1]}]
        for g in record['gradients']:assert g['stops']==expected,(case,g)
def launch(input_path,profile,log_path):
    log=log_path.open('w');p=subprocess.Popen([rt.runtime()['launcher'],str(input_path)],cwd=ROOT,env=rt.environment(profile),stdout=log,stderr=subprocess.STDOUT)
    def find():
        assert p.poll() is None,'Synfig exited during launch'
        candidates=windows('Synfig|GradBefore')
        for window in candidates:
            geometry=command('xdotool','getwindowgeometry','--shell',window);values=dict(line.split('=',1) for line in geometry.splitlines() if '=' in line)
            if int(values.get('WIDTH',0))>=650 and int(values.get('HEIGHT',0))>=400:return window
        return None
    try:window=wait(find,'Synfig main window missing',60);activate(window);time.sleep(1);return p,log,window
    except Exception:
        log.flush();log.close()
        if p.poll() is None:
            p.terminate()
            try:p.wait(timeout=5)
            except subprocess.TimeoutExpired:p.kill()
        raise
def quit_app(process,log):
    key('ctrl+q');assert process.wait(timeout=30)==0,'Synfig did not exit cleanly';log.close()
def render(sif,stem):
    target=OUT/(stem+'.png');assert not list(OUT.glob(stem+'*.png')),'Refuse existing native render targets';args=[*rt.cli_command(),str(sif),'-t','png','-o',str(target),'--time','0f','-w','560','-h','200','-T','1'];result=subprocess.run(args,env=rt.cli_environment(WORK/'cli-profile'),cwd=ROOT,capture_output=True,text=True,timeout=90);(OUT/(stem+'-render.log')).write_text(result.stdout+result.stderr);assert result.returncode==0,result.stderr
    matches=list(OUT.glob(stem+'*.png'));assert len(matches)==1,'Expected one native frame';actual=matches[0]
    if actual!=target:actual.rename(target)
    note('native-cli-render',input=sif.name,output=target.name);return target

def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true' and os.environ.get('DISPLAY'),'Hosted disposable-display gate only'
    version=subprocess.run([*rt.cli_command(),'--version'],env=rt.cli_environment(WORK/'version-profile'),capture_output=True,text=True,timeout=30);(OUT/'synfig-version.txt').write_text(version.stdout+version.stderr);assert version.returncode==0 and '1.5.5' in version.stdout+version.stderr
    cases={'original':ROOT/'fixtures/original.svg','repaired':OUT/'repaired.svg','manual-control':ROOT/'fixtures/manual-control.svg','altered-stop':OUT/'altered-stop.svg'};records={}
    wm_log=(OUT/'openbox.log').open('w');wm=subprocess.Popen(['openbox','--config-file','/etc/xdg/openbox/rc.xml'],stdout=wm_log,stderr=subprocess.STDOUT)
    wait(lambda:subprocess.run(['xdotool','get_num_desktops'],capture_output=True).returncode==0,'Window manager did not start',15)
    active=None;active_log=None
    try:
        for case,source in cases.items():
            area=WORK/'cases'/case;area.mkdir(parents=True,exist_ok=True);svg=area/'source.svg';shutil.copyfile(source,svg);blank=area/'blank.sif';shutil.copyfile(ROOT/'fixtures/blank.sif',blank)
            active,active_log,window=launch(blank,area/'profile',OUT/(case+'-gui.log'));note('launch-blank',case=case,window=window)
            key('ctrl+i');wait(lambda:windows('Import'),'Native Import dialog missing');key('ctrl+l');type_text(str(svg));key('Return');wait(lambda:not windows('Import'),'Native Import dialog did not close');time.sleep(1)
            command('scrot',str(OUT/(case+'-imported.png')));file=OUT/(case+'.sif');save_as(file);first=native_record(file);validate(first,case);quit_app(active,active_log);active=None;active_log=None
            # The saved editable SIF must stand alone, with the actual imported source unavailable.
            svg.rename(area/'source.svg.disabled');active,active_log,window=launch(file,area/'reopen-profile',OUT/(case+'-reopen.log'));reopened=OUT/(case+'-reopened.sif');save_as(reopened);second=native_record(reopened);validate(second,case);assert first['gradients']==second['gradients'] and first['layerTypes']==second['layerTypes'];command('scrot',str(OUT/(case+'-reopened.png')));quit_app(active,active_log);active=None;active_log=None
            render(file,case+'-native');render(reopened,case+'-reopened-native');records[case]={'saved':first,'reopened':second,'sourceRemovedBeforeReopen':True};(OUT/'native-structure.json').write_text(json.dumps(records,indent=2)+'\n')
        (OUT/'native-gui-result.json').write_text(json.dumps({'synfigVersion':'1.5.5','cases':records,'actions':progress,'scope':'Actual GUI SVG import into editable native groups/gradients, native save, fresh process reopen/save with source removed, then unchanged official CLI rendering. Synthetic fixtures only.'},indent=2)+'\n')
    except Exception:
        subprocess.run(['scrot',str(OUT/'native-failure.png')],capture_output=True)
        listing=[]
        for window in windows('.*'):
            listing.append({'id':window,'name':subprocess.run(['xdotool','getwindowname',window],capture_output=True,text=True).stdout.strip(),'geometry':subprocess.run(['xdotool','getwindowgeometry','--shell',window],capture_output=True,text=True).stdout})
        (OUT/'native-windows.json').write_text(json.dumps(listing,indent=2)+'\n');raise
    finally:
        if active and active.poll() is None:active.terminate()
        if active_log:active_log.close()
        wm.terminate()
        try:wm.wait(timeout=10)
        except subprocess.TimeoutExpired:wm.kill()
        wm_log.close()
if __name__=='__main__':main()
