"""Bounds and containment for the test-only native archive extraction path."""
import importlib.util,io,pathlib,tarfile,tempfile,unittest
spec=importlib.util.spec_from_file_location('prepare_native',pathlib.Path(__file__).resolve().parents[1]/'scripts/prepare-native.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
class NativeArchive(unittest.TestCase):
    def archive(self,rows):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);root=pathlib.Path(temp.name);archive=root/'test.tar'
        with tarfile.open(archive,'w') as out:
            for name,kind,value in rows:
                info=tarfile.TarInfo(name);info.mode=0o755 if kind=='dir' else 0o644
                if kind=='file':
                    data=value.encode();info.size=len(data);out.addfile(info,io.BytesIO(data))
                else:
                    info.type={'dir':tarfile.DIRTYPE,'sym':tarfile.SYMTYPE,'hard':tarfile.LNKTYPE,'fifo':tarfile.FIFOTYPE}[kind];info.linkname=value;out.addfile(info)
        return archive,root/'extracted'
    def reject(self,rows):
        archive,target=self.archive(rows)
        with self.assertRaises((AssertionError,RuntimeError)):module.safe_extract_tar(archive,target)
    def test_internal_links_preserve_bytes(self):
        archive,target=self.archive([('usr','dir',''),('usr/bin','dir',''),('usr/bin/tool','file','fixed official bytes'),('usr/bin/alias','sym','tool'),('usr/bin/hard','hard','usr/bin/tool')]);result=module.safe_extract_tar(archive,target)
        self.assertEqual((target/'usr/bin/alias').read_text(),'fixed official bytes');self.assertEqual((target/'usr/bin/hard').read_text(),'fixed official bytes');self.assertEqual(result['symlinks'],1);self.assertEqual(result['hardlinks'],1);self.assertTrue(result['allPathsAndLinksContained'])
    def test_parent_traversal_rejects(self):self.reject([('../escaped','file','x')])
    def test_absolute_path_rejects(self):self.reject([('/escaped','file','x')])
    def test_external_symlink_rejects(self):self.reject([('usr/link','sym','../../escaped')])
    def test_external_hardlink_rejects(self):self.reject([('usr/link','hard','../escaped')])
    def test_symlink_parent_rejects_before_write(self):self.reject([('usr','sym','inside'),('usr/tool','file','x')])
    def test_duplicate_and_special_entries_reject(self):
        self.reject([('x','file','a'),('x','file','b')]);self.reject([('pipe','fifo','')])
    def test_missing_or_cyclic_hardlinks_reject(self):
        self.reject([('a','hard','b')]);self.reject([('a','hard','b'),('b','hard','a')])
if __name__=='__main__':unittest.main()
