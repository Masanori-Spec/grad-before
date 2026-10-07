"""Compare real native/browser pixels with fixed semantic samples and deliberate mutations."""
import hashlib,json,pathlib
from PIL import Image
ROOT=pathlib.Path(__file__).resolve().parents[1];OUT=ROOT/'evidence'
def image(name):
    im=Image.open(OUT/name).convert('RGBA');assert im.size==(560,200),name;return im

def digest(im):return hashlib.sha256(im.tobytes()).hexdigest()
def difference(a,b):return sum(x!=y for x,y in zip(a.getdata(),b.getdata()))
def main():
    native={name:image(name+'-native.png') for name in ['original','repaired','manual-control','altered-stop']}
    browser={name:image(name+'-browser.png') for name in native}
    samples=[(100,100),(280,100),(460,100)]
    for name in native:
        reopened=image(name+'-reopened-native.png');assert native[name].tobytes()==reopened.tobytes(),name+' changed on fresh native reopen/save'
    assert native['repaired'].tobytes()==native['manual-control'].tobytes(),'Repaired native render differs from independent ordered control'
    assert difference(native['original'],native['manual-control'])>50000,'Original did not reproduce a substantial ordering defect'
    assert difference(native['altered-stop'],native['manual-control'])>10000,'Native stop mutation escaped the pixel oracle'
    for point in samples:assert sum(native['original'].getpixel(point)[:3])<30,'Original expected black failed-gradient sample missing'
    for point in samples[:2]:
        r,g,b,a=native['manual-control'].getpixel(point);assert g>180 and r<100 and b<100 and a==255,'Expected green center in linear panel'
    r,g,b,a=native['manual-control'].getpixel(samples[2]);assert r>180 and g<100 and b<100 and a==255,'Expected red radial center'
    assert len(set(native['manual-control'].getdata()))>100,'Native control was not a meaningful multicolor gradient render'
    assert browser['original'].tobytes()==browser['repaired'].tobytes()==browser['manual-control'].tobytes(),'Order-only repair changed browser SVG pixels'
    assert difference(browser['altered-stop'],browser['manual-control'])>10000,'Browser stop mutation escaped the pixel oracle'
    comparisons=json.loads((OUT/'optimizers/comparison.json').read_text());competitors=[]
    for result in comparisons['results']:
        rendered=image(result['name']+'-browser.png');competitors.append({'name':result['name'],'browserDifferentPixels':difference(rendered,browser['original']),'gradientDependencyOrdered':result['dependencyOrdered'],'sameIds':result['sameIds'],'sameSharedEdges':result['sameEdges']})
    report={'nativeRGBA':{n:digest(im) for n,im in native.items()},'browserRGBA':{n:digest(im) for n,im in browser.items()},'nativeOriginalDifferentPixels':difference(native['original'],native['manual-control']),'nativeAlteredStopDifferentPixels':difference(native['altered-stop'],native['manual-control']),'browserOriginalRepairIdentical':True,'browserAlteredStopDifferentPixels':difference(browser['altered-stop'],browser['manual-control']),'nativeSamples':{n:[im.getpixel(p) for p in samples] for n,im in native.items()},'optimizerOutputs':competitors,'scope':'Exact pixel equality within the same native engine and within the same browser. No cross-engine SVG fidelity claim.'}
    (OUT/'pixel-result.json').write_text(json.dumps(report,indent=2)+'\n')
if __name__=='__main__':main()
