"""Process-local vendor runtime environment and disposable profile helpers."""
import json,os,pathlib,shutil
ROOT=pathlib.Path(__file__).resolve().parents[1]
def runtime():return json.loads((ROOT/'.native/synfig-runtime.json').read_text())
def environment(profile):
    profile.mkdir(parents=True,exist_ok=True);env=os.environ.copy();env.update({'SYNFIG_USER_SETTINGS':str(profile/'synfig'),'XDG_CONFIG_HOME':str(profile/'config'),'XDG_CACHE_HOME':str(profile/'cache'),'XDG_DATA_HOME':str(profile/'data'),'LC_ALL':'C.UTF-8','LANG':'C.UTF-8','APPDIR':runtime()['appDir']})
    return env
def cli_command():
    r=runtime();return [r['cliWrapper'] or r['cli']]
def cli_environment(profile):
    env=environment(profile);r=runtime();prefix=pathlib.Path(r['prefix']);libs=[p for p in [prefix/'lib',prefix/'lib64',prefix/'lib/x86_64-linux-gnu',prefix/'lib.extra/jack'] if p.is_dir()]
    env.update({'SYNFIG_ROOT':str(prefix),'SYNFIG_MODULE_LIST':r['moduleList'],'LD_LIBRARY_PATH':':'.join(str(p) for p in libs)})
    if shutil.which('jackd') is None:env['SYNFIG_DISABLE_JACK']='1'
    return env
def gui_environment(profile):
    env=cli_environment(profile);prefix=pathlib.Path(runtime()['prefix']);config=profile/'synfig';config.mkdir(exist_ok=True)
    env.update({'SYNFIG_GTK_THEME':'Adwaita','XDG_DATA_DIRS':str(prefix/'share')+':/usr/local/share:/usr/share','GSETTINGS_SCHEMA_DIR':str(prefix/'share/glib-2.0/schemas'),'FONTCONFIG_PATH':str(prefix/'etc/fonts'),'MLT_DATA':str(prefix/'share/mlt'),'MLT_REPOSITORY':str(prefix/'lib/mlt')})
    template=prefix/'lib/gdk-pixbuf-2.0/2.10.0/loaders.cache.in'
    if template.is_file():
        cache=config/'gdk-pixbuf.loaders';cache.write_text(template.read_text().replace('@ROOTDIR@/loaders',str(prefix/'lib/gdk-pixbuf-2.0/2.10.0/loaders')));env['GDK_PIXBUF_MODULE_FILE']=str(cache)
    return env
