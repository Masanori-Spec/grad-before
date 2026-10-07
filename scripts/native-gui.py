"""Actual Synfig GUI File Import, native save, fresh reopen/save, then CLI rendering."""
import hashlib,importlib.util,json,os,pathlib,re,shutil,subprocess,time,xml.etree.ElementTree as ET
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
def properties(window):
    return subprocess.run(['xprop','-id',window,'_NET_WM_WINDOW_TYPE','_NET_WM_PID','WM_CLASS','WM_NAME'],capture_output=True,text=True,timeout=5).stdout
def wait_dialog(pattern,pid):
    def find():
        matches=[]
        for window in windows(pattern):
            props=properties(window);owner=re.search(r'_NET_WM_PID\(CARDINAL\) = (\d+)',props)
            if '_NET_WM_WINDOW_TYPE_DIALOG' in props and owner and int(owner.group(1))==pid:matches.append((window,props))
        assert len(matches)<=1,'Ambiguous native dialog'
        return matches[0] if matches else None
    window,props=wait(find,'Expected native dialog missing: '+pattern)
    assert command('xdotool','getactivewindow').strip()==window,'Native dialog does not own focus'
    note('native-dialog',window=window,process=pid,properties=props);return window
def accept_dialog(window,stem):
    assert command('xdotool','getactivewindow').strip()==window,'Native chooser lost focus'
    geometry=command('xdotool','getwindowgeometry','--shell',window);values=dict(line.split('=',1) for line in geometry.splitlines() if '=' in line);width=int(values['WIDTH']);height=int(values['HEIGHT']);assert 600<=width<=1600 and 300<=height<=1000
    # The observed GTK chooser places its explicit accept button at bottom right.
    # Use client-relative coordinates; do not rely on Return having a default response.
    x,y=width-45,height-25;command('scrot',str(OUT/(stem+'-chooser-ready.png')));note('native-chooser-accept',window=window,x=x,y=y,coordinateSpace='client',screenshot=stem+'-chooser-ready.png')
    command('xdotool','mousemove','--window',window,str(x),str(y));command('xdotool','click','1')
def diagnose(stem):
    subprocess.run(['scrot',str(OUT/(stem+'.png'))],capture_output=True,timeout=10)
    listing=[{'id':window,'name':subprocess.run(['xdotool','getwindowname',window],capture_output=True,text=True).stdout.strip(),'properties':properties(window),'geometry':subprocess.run(['xdotool','getwindowgeometry','--shell',window],capture_output=True,text=True).stdout} for window in windows('.*')]
    (OUT/(stem+'-windows.json')).write_text(json.dumps({'activeWindow':subprocess.run(['xdotool','getactivewindow'],capture_output=True,text=True).stdout.strip(),'windows':listing},indent=2)+'\n')
def saved(path):
    try:return path.exists() and path.stat().st_size>100 and ET.parse(path).getroot().tag=='canvas'
    except ET.ParseError:return False
def save_as(path,pid):
    assert not path.exists();key('ctrl+shift+s');dialog=wait_dialog(r'^Please choose a file name \(GradBefore native import fixture\)$',pid);key('ctrl+l');type_text(str(path));accept_dialog(dialog,path.stem+'-save')
    wait(lambda:saved(path),'Native Save As did not complete',30)
    wait(lambda:dialog not in windows('.*'),'Save dialog remained open');note('native-save-as',file=path.name,sha256=hashlib.sha256(path.read_bytes()).hexdigest())
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
    log=log_path.open('w');p=subprocess.Popen([rt.runtime()['launcher'],str(input_path)],cwd=ROOT,env=rt.gui_environment(profile),stdout=log,stderr=subprocess.STDOUT)
    observed={}
    def find():
        assert p.poll() is None,'Synfig exited during launch'
        managed={int(value,16) for value in re.findall(r'0x[0-9a-fA-F]+',command('xprop','-root','_NET_CLIENT_LIST'))}
        candidates=windows('Synfig|GradBefore')
        eligible=[]
        for window in candidates:
            props=properties(window);observed[window]=props
            (OUT/(log_path.stem+'-window-observations.json')).write_text(json.dumps(observed,indent=2)+'\n')
            pid=re.search(r'_NET_WM_PID\(CARDINAL\) = (\d+)',props)
            if int(window) not in managed or '_NET_WM_WINDOW_TYPE_NORMAL' not in props or not pid or int(pid.group(1))!=p.pid:continue
            geometry=command('xdotool','getwindowgeometry','--shell',window);values=dict(line.split('=',1) for line in geometry.splitlines() if '=' in line)
            if int(values.get('WIDTH',0))>=650 and int(values.get('HEIGHT',0))>=400:
                eligible.append((window,props,geometry))
        assert len(eligible)<=1,'Multiple qualifying native windows; selection is ambiguous'
        if eligible:
            window,props,geometry=eligible[0];note('select-managed-normal-window',window=window,process=p.pid,properties=props,geometry=geometry);return window
        return None
    try:window=wait(find,'Synfig main window missing',60);activate(window);time.sleep(1);return p,log,window
    except Exception:
        diagnose(log_path.stem+'-launch-failure')
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
    profile=WORK/'recorded-profile';choices=rt.gui_environment(profile);keys=['SYNFIG_USER_SETTINGS','XDG_CONFIG_HOME','XDG_CACHE_HOME','XDG_DATA_HOME','APPDIR','SYNFIG_ROOT','SYNFIG_MODULE_LIST','LD_LIBRARY_PATH','SYNFIG_GTK_THEME','SYNFIG_DISABLE_JACK','XDG_DATA_DIRS','GSETTINGS_SCHEMA_DIR','FONTCONFIG_PATH','MLT_DATA','MLT_REPOSITORY','GDK_PIXBUF_MODULE_FILE','LANG','LC_ALL'];(OUT/'native-runtime-choices.json').write_text(json.dumps({'gui':rt.runtime()['launcher'],'guiSHA256':rt.runtime()['launcherSHA256'],'inheritedHomeUnchanged':choices.get('HOME')==os.environ.get('HOME'),'profilePathNote':'Each launch substitutes its own disposable profile root','processOverrides':{k:choices[k] for k in keys if k in choices}},indent=2)+'\n');assert choices.get('HOME')==os.environ.get('HOME')
    version=subprocess.run([*rt.cli_command(),'--version'],env=rt.cli_environment(WORK/'version-profile'),capture_output=True,text=True,timeout=30);(OUT/'synfig-version.txt').write_text(version.stdout+version.stderr);(OUT/'synfig-version.json').write_text(json.dumps({'argv':[*rt.cli_command(),'--version'],'returncode':version.returncode,'stdout':version.stdout,'stderr':version.stderr,'expectedVersionExit':'SYNFIGTOOL_HELP = 3 in pinned definitions.h'},indent=2)+'\n');assert version.returncode==3 and 'synfig 1.5.5' in (version.stdout+version.stderr).splitlines()
    cases={'original':ROOT/'fixtures/original.svg','repaired':OUT/'repaired.svg','manual-control':ROOT/'fixtures/manual-control.svg','altered-stop':OUT/'altered-stop.svg'};records={}
    wm_log=(OUT/'openbox.log').open('w');wm=subprocess.Popen(['openbox','--config-file','/etc/xdg/openbox/rc.xml'],stdout=wm_log,stderr=subprocess.STDOUT)
    wait(lambda:subprocess.run(['xdotool','get_num_desktops'],capture_output=True).returncode==0,'Window manager did not start',15)
    active=None;active_log=None
    try:
        for case,source in cases.items():
            area=WORK/'cases'/case;area.mkdir(parents=True,exist_ok=True);svg=area/'source.svg';shutil.copyfile(source,svg);blank=area/'blank.sif';shutil.copyfile(ROOT/'fixtures/blank.sif',blank)
            active,active_log,window=launch(blank,area/'profile',OUT/(case+'-gui.log'));note('launch-blank',case=case,window=window)
            key('ctrl+i');dialog=wait_dialog('^Please select files$',active.pid);key('ctrl+l');type_text(str(svg));accept_dialog(dialog,case+'-import');wait(lambda:dialog not in windows('.*'),'Native Import dialog did not close');time.sleep(1)
            command('scrot',str(OUT/(case+'-imported.png')));file=OUT/(case+'.sif');save_as(file,active.pid);first=native_record(file);validate(first,case);quit_app(active,active_log);active=None;active_log=None
            # The saved editable SIF must stand alone, with the actual imported source unavailable.
            svg.rename(area/'source.svg.disabled');active,active_log,window=launch(file,area/'reopen-profile',OUT/(case+'-reopen.log'));reopened=OUT/(case+'-reopened.sif');save_as(reopened,active.pid);second=native_record(reopened);validate(second,case);assert first['gradients']==second['gradients'] and first['layerTypes']==second['layerTypes'];command('scrot',str(OUT/(case+'-reopened.png')));quit_app(active,active_log);active=None;active_log=None
            render(file,case+'-native');render(reopened,case+'-reopened-native');records[case]={'saved':first,'reopened':second,'sourceRemovedBeforeReopen':True};(OUT/'native-structure.json').write_text(json.dumps(records,indent=2)+'\n')
        (OUT/'native-gui-result.json').write_text(json.dumps({'synfigVersion':'1.5.5','cases':records,'actions':progress,'scope':'Actual GUI SVG import into editable native groups/gradients, native save, fresh process reopen/save with source removed, then unchanged official CLI rendering. Synthetic fixtures only.'},indent=2)+'\n')
    except Exception:
        diagnose('native-failure');raise
    finally:
        if active and active.poll() is None:active.terminate()
        if active_log:active_log.close()
        wm.terminate()
        try:wm.wait(timeout=10)
        except subprocess.TimeoutExpired:wm.kill()
        wm_log.close()
if __name__=='__main__':main()
