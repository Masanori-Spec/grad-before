"""Process-local vendor runtime environment and disposable profile helpers."""
import json,os,pathlib
ROOT=pathlib.Path(__file__).resolve().parents[1]
def runtime():return json.loads((ROOT/'.native/synfig-runtime.json').read_text())
def environment(profile):
    profile.mkdir(parents=True,exist_ok=True);env=os.environ.copy();env.update({'SYNFIG_USER_SETTINGS':str(profile/'synfig'),'XDG_CONFIG_HOME':str(profile/'config'),'XDG_CACHE_HOME':str(profile/'cache'),'XDG_DATA_HOME':str(profile/'data'),'LC_ALL':'C.UTF-8','LANG':'C.UTF-8','APPDIR':str(pathlib.Path(runtime()['launcher']).parent)})
    return env
def cli_command():
    r=runtime();return [r['cliWrapper'] or r['cli']]
def cli_environment(profile):
    env=environment(profile);r=runtime();prefix=pathlib.Path(r['prefix']);libs=[p for p in [prefix/'lib',prefix/'lib64',prefix/'lib/x86_64-linux-gnu'] if p.is_dir()]
    env.update({'SYNFIG_ROOT':str(prefix),'SYNFIG_MODULE_LIST':r['moduleList'],'LD_LIBRARY_PATH':':'.join(str(p) for p in libs)})
    return env
