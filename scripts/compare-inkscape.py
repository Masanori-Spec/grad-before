"""Measure both orders through the unchanged installed Inkscape exporter; do not assume success."""
import hashlib,importlib.util,json,os,pathlib,subprocess,xml.etree.ElementTree as ET
from PIL import Image
ROOT=pathlib.Path(__file__).resolve().parents[1];OUT=ROOT/'evidence';WORK=ROOT/'.native'
spec=importlib.util.spec_from_file_location('runtime',ROOT/'scripts/native-runtime.py');rt=importlib.util.module_from_spec(spec);spec.loader.exec_module(rt)
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def persist(report):(OUT/'inkscape-alternative.json').write_text(json.dumps(report,indent=2)+'\n')
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true' and os.environ.get('DISPLAY'),'Hosted alternative comparison only'
    folder=pathlib.Path('/usr/share/inkscape/extensions');script=folder/'synfig_output.py';assert script.is_file(),'Official distro SIF exporter unavailable'
    pins=json.loads((ROOT/'docs/inkscape-source-pins.json').read_text());package=subprocess.run(['dpkg-query','-W','-f=${Version}','inkscape'],capture_output=True,text=True,check=True,timeout=15).stdout;assert package==pins['version'],'Installed comparison package differs from reviewed pin'
    sources=[]
    for expected in pins['files']:
        path=folder/expected['path'];actual={'path':expected['path'],'sha256':sha(path),'bytes':path.stat().st_size};assert actual==expected,'Installed exporter/preprocessor source differs from official package';sources.append(actual)
    profile=WORK/'inkscape-profile';env=rt.environment(profile);env.pop('APPDIR',None);version=subprocess.run(['inkscape','--version'],env=env,capture_output=True,text=True,check=True,timeout=15).stdout.strip()
    report={'status':'running','version':version,'packageVersion':package,'sourceFiles':sources,'cases':{},'scope':'Unmodified officially installed exporter, including its own preprocessing, on unchanged original/manual-order SVGs. Complete measurements do not imply usable output or a general Inkscape limitation.'};persist(report)
    expected_stops=[{'offset':0.0,'rgba':[1,0,0,1]},{'offset':0.5,'rgba':[0,1,0,1]},{'offset':1.0,'rgba':[0,0,1,1]}]
    for name,source in [('original',ROOT/'fixtures/original.svg'),('manual-control',ROOT/'fixtures/manual-control.svg')]:
        target=OUT/('inkscape-'+name+'.sif');assert not target.exists(),'Refuse stale alternative export';args=['/usr/bin/python3',str(script),str(source),'--output',str(target)];result=subprocess.run(args,cwd=ROOT,env=env,capture_output=True,text=True,timeout=90);(OUT/('inkscape-'+name+'.log')).write_text(result.stdout+result.stderr)
        record={'sourceSHA256':sha(source),'argv':args,'exportReturncode':result.returncode};report['cases'][name]=record;persist(report);assert result.returncode==0 and target.is_file(),result.stderr
        doc=ET.parse(target);layers=list(doc.getroot().iter('layer'));types=[n.get('type') for n in layers];assert not any(x in ('import','svg_layer','imagemagick','ffmpeg') for x in types) and not doc.findall('.//param[@name="filename"]'),'Alternative fixture acquired external/image dependencies'
        gradients=[{'type':layer.get('type'),'stops':[{'offset':float(c.get('pos')),'rgba':[float(c.findtext(k)) for k in ['r','g','b','a']]} for c in layer.findall('./param[@name="gradient"]/gradient/color')]} for layer in layers if layer.get('type') in ['linear_gradient','radial_gradient']]
        structure=types.count('linear_gradient')==2 and types.count('radial_gradient')==1 and all(g['stops']==expected_stops for g in gradients)
        record.update(sifSHA256=sha(target),layerTypes=types,gradients=gradients,expectedGradientStructure=structure);persist(report)
        png=OUT/('inkscape-'+name+'.png');assert not list(OUT.glob('inkscape-'+name+'*.png')),'Refuse existing alternative render targets';render=subprocess.run([*rt.cli_command(),str(target),'-t','png','-o',str(png),'--time','0f','-w','560','-h','200','-T','1'],env=rt.cli_environment(WORK/'inkscape-render-profile'),capture_output=True,text=True,timeout=90);(OUT/('inkscape-'+name+'-render.log')).write_text(render.stdout+render.stderr);record['renderReturncode']=render.returncode;persist(report);assert render.returncode==0,render.stderr
        matches=list(OUT.glob('inkscape-'+name+'*.png'));assert len(matches)==1
        if matches[0]!=png:matches[0].rename(png)
        im=Image.open(png).convert('RGBA');assert im.size==(560,200);record.update(pngSHA256=sha(png),rgbaSHA256=hashlib.sha256(im.tobytes()).hexdigest(),colorCount=len(set(im.getdata())),samples=[im.getpixel(p) for p in [(100,100),(280,100),(460,100)]]);persist(report)
    first=Image.open(OUT/'inkscape-original.png').convert('RGBA');second=Image.open(OUT/'inkscape-manual-control.png').convert('RGBA');equal=first.tobytes()==second.tobytes();colored=all(c['colorCount']>100 for c in report['cases'].values());structure=all(c['expectedGradientStructure'] for c in report['cases'].values());report.update(status='complete',orderIndependentPixels=equal,meaningfullyColored=colored,meetsFixtureGradientChecks=equal and colored and structure,outcome='meets bounded fixture checks' if equal and colored and structure else 'does not meet bounded fixture checks');persist(report)
if __name__=='__main__':main()
