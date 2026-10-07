"""Bounded execution of the officially installed Inkscape SIF exporter as a real alternative."""
import hashlib,importlib.util,json,os,pathlib,subprocess,xml.etree.ElementTree as ET
ROOT=pathlib.Path(__file__).resolve().parents[1];OUT=ROOT/'evidence';WORK=ROOT/'.native'
spec=importlib.util.spec_from_file_location('runtime',ROOT/'scripts/native-runtime.py');rt=importlib.util.module_from_spec(spec);spec.loader.exec_module(rt)
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true' and os.environ.get('DISPLAY'),'Hosted alternative comparison only'
    folder=pathlib.Path('/usr/share/inkscape/extensions');script=folder/'synfig_output.py';assert script.is_file(),'Official distro SIF exporter unavailable'
    profile=WORK/'inkscape-profile';env=rt.environment(profile);env.pop('APPDIR',None);version=subprocess.run(['inkscape','--version'],env=env,capture_output=True,text=True,check=True,timeout=15).stdout.strip()
    names=['synfig_output.py','synfig_prepare.py','synfig_fileformat.py','synfig_output.inx'];report={'version':version,'sourceFiles':{name:sha(folder/name) for name in names},'cases':{},'scope':'Unmodified officially installed SIF exporter on fixed original/manual-order SVGs. This is an alternative format conversion, not an order-only SVG repair.'}
    for name,source in [('original',ROOT/'fixtures/original.svg'),('manual-control',ROOT/'fixtures/manual-control.svg')]:
        target=OUT/('inkscape-'+name+'.sif');args=['/usr/bin/python3',str(script),str(source),'--output',str(target)];result=subprocess.run(args,cwd=ROOT,env=env,capture_output=True,text=True,timeout=90);(OUT/('inkscape-'+name+'.log')).write_text(result.stdout+result.stderr);assert result.returncode==0 and target.is_file(),result.stderr
        doc=ET.parse(target);types=[n.get('type') for n in doc.getroot().iter('layer')];assert types.count('linear_gradient')==2 and types.count('radial_gradient')==1 and not any(x in ('import','svg_layer','imagemagick') for x in types),'Inkscape did not export three editable gradients'
        png=OUT/('inkscape-'+name+'.png');assert not list(OUT.glob('inkscape-'+name+'*.png')),'Refuse existing alternative render targets';render=subprocess.run([*rt.cli_command(),str(target),'-t','png','-o',str(png),'--time','0f','-w','560','-h','200','-T','1'],env=rt.cli_environment(WORK/'inkscape-render-profile'),capture_output=True,text=True,timeout=90);(OUT/('inkscape-'+name+'-render.log')).write_text(render.stdout+render.stderr);assert render.returncode==0,render.stderr
        matches=list(OUT.glob('inkscape-'+name+'*.png'));assert len(matches)==1
        if matches[0]!=png:matches[0].rename(png)
        report['cases'][name]={'sifSHA256':sha(target),'pngSHA256':sha(png),'layerTypes':types}
    from PIL import Image
    first=Image.open(OUT/'inkscape-original.png').convert('RGBA');second=Image.open(OUT/'inkscape-manual-control.png').convert('RGBA');assert first.size==second.size==(560,200);assert first.tobytes()==second.tobytes(),'Inkscape alternative depends on definition order';assert len(set(first.getdata()))>100,'Alternative output is not meaningfully colored';report['orderIndependentPixels']=True;report['rgbaSHA256']=hashlib.sha256(first.tobytes()).hexdigest();(OUT/'inkscape-alternative.json').write_text(json.dumps(report,indent=2)+'\n')
if __name__=='__main__':main()
