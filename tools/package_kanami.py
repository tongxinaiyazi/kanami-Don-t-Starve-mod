"""Build runtime and editable-source packages from explicit project roots."""
import hashlib, json, re, shutil, zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
MOD=ROOT/'mods/klbq_kanami'
OUT=ROOT/'dist';OUT.mkdir(exist_ok=True)
version_match=re.search(r'^version\s*=\s*"([0-9.]+)"', (MOD/'modinfo.lua').read_text(encoding='utf-8'), re.MULTILINE)
if version_match is None:raise ValueError('Missing mod version in modinfo.lua')
VERSION=version_match.group(1)
RELEASE_REL='发布资料/klbq_kanami_v'+VERSION.replace('.','_')
PUBLISH=Path('D:/SOFTWARE/DSTWorkshop/klbq_kanami')
PUBLISH_MANIFEST=PUBLISH.parent/'kanami-current-release.json'

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def archive(path,entries):
 with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
  for source,name in sorted(entries,key=lambda x:x[1]):z.write(source,name)
 with zipfile.ZipFile(path) as z:
  assert z.testzip() is None
 return {'file':path.name,'bytes':path.stat().st_size,'sha256':digest(path),'entries':len(entries)}

runtime=[(p,p.relative_to(MOD).as_posix()) for p in MOD.rglob('*') if p.is_file() and not p.name.startswith('.')]
assert any(n=='modinfo.lua' for _,n in runtime) and any(n=='modmain.lua' for _,n in runtime)
manifest={'version':VERSION,'runtime_files':{n:digest(p) for p,n in runtime},'packages':[]}
manifest['packages'].append(archive(OUT/f'klbq_kanami-{VERSION}-dst.zip',runtime))
engineering=[(p,'mods/klbq_kanami/'+n) for p,n in runtime]
own_tools={'build_kanami_assets.py','deploy_kanami.ps1','inspect_dst_assets.py',
           'kanami_client_qa.py','prepare_kanami_client.py','package_kanami.py','render_kanami_rig.py',
           'run_kanami_engine.py','run_kanami_void.py','qa_imprint_visual.py',
           'build_kanami_body_v2.py','promote_kanami_body_v2.py','audit_kanami_body.py',
           'compare_kanami_native_body.py','register_kanami_legs_v2.py','assemble_kanami_body_v2.py',
           'render_kanami_body_v2.py','preview_body_contract.py','preview_body_joints.py',
           'calibrate_kanami_face.py','audit_kanami_connections.py',
           'retarget_kanami_body.py','derive_kanami_joint_contract.py','check_kanami_joint_poses.py',
           'test_kanami_arm_proportions.py','test_kanami_face_registration.py','test_kanami_joint_registration.py',
           'test_build_kanami_body_v2.py','test_render_kanami_body_v2.py',
           'test_run_kanami_engine_candidate.py','README-body-v2.md'}
for folder in ['art/klbq_kanami','tools','tests/gameplay','tests/engine_mod','tests/void_mod','tests/client_mod',
               RELEASE_REL]:
 for p in (ROOT/folder).rglob('*'):
  if not p.is_file():continue
  rel=p.relative_to(ROOT)
  if any(x in rel.parts for x in ['references','python-deps','__pycache__','history']):continue
  if p.suffix in ['.log','.pyc','.pyd','.dll','.whl']:continue
  if p.name in ['paper-turnaround-v1.png','ghost-native.png','rig-preview.png']:continue
  if p.name.startswith('concept-') or p.name in ['registered-contact.png','registered-hands-contact.png']:continue
  if folder=='tools' and p.name not in own_tools:continue
  engineering.append((p,rel.as_posix()))
# Only current, reviewable documentation belongs in the engineering handoff.
# Internal continuation notes and old failed-run reports remain in the workspace.
for name in ['docs/BUILDING.md','docs/kanami-spec.md','docs/kanami-assets.json',
             'docs/superpowers/plans/2026-10-28-kanami-implementation.md',
             'docs/superpowers/plans/2026-11-02-imprint-materials.md',
             'docs/superpowers/specs/2026-11-02-kanami-terminal-design.md',
             'docs/reports/verification.md','docs/reports/void-compatibility.md',
             'docs/reports/body-v2-2026-11-10.md','docs/reports/body-v2-compiled-readback.json',
             'docs/reports/joint-rebind-2026-11-10.md','docs/reports/joint-rebind-readback.json',
             'docs/reports/profile-work-2026-11-12.md',
             'docs/reports/fate-config-2026-11-01.md',
             'docs/reports/crossbow-launch-2026-11-01.md',
             'docs/reports/terminal-integration-2026-11-02.md',
             'docs/reports/imprint-materials-2026-11-02.md',
             'docs/reports/body-v2-latest.png','docs/reports/joint-rebind-latest.png',
             f'docs/kanami-workshop-v{VERSION}.md','docs/香奈美模组介绍.md',
             f'docs/reports/release-{VERSION}.md']:
 engineering.append((ROOT/name,name))
manifest['packages'].append(archive(OUT/f'klbq_kanami-{VERSION}-source-art.zip',engineering))
# Stable uploader directory. Only files recorded by this publisher may be
# replaced or retired; project source, saves and historical packages stay put.
previous={}
if PUBLISH_MANIFEST.exists():
 previous=json.loads(PUBLISH_MANIFEST.read_text(encoding='utf-8'))
 assert previous['source']==str(MOD) and previous['directory']==str(PUBLISH)
assert PUBLISH.resolve()==PUBLISH.absolute(), 'Linked publish directory'
existing=list(PUBLISH.rglob('*')) if PUBLISH.exists() else []
for p in existing:
 assert p.resolve().is_relative_to(PUBLISH.resolve()), 'Linked publish child'
 if p.is_file():assert p.relative_to(PUBLISH).as_posix() in previous.get('runtime_files',{}), 'Unowned publish file: '+str(p)
PUBLISH.mkdir(parents=True,exist_ok=True)
for source,name in runtime:
 target=PUBLISH/name;target.parent.mkdir(parents=True,exist_ok=True)
 shutil.copy2(source,target)
for name in previous.get('runtime_files',{}):
 if name not in manifest['runtime_files']:
  retired=PUBLISH/name
  assert retired.resolve().is_relative_to(PUBLISH.resolve())
  if retired.is_file():retired.unlink()
actual={p.relative_to(PUBLISH).as_posix():digest(p) for p in PUBLISH.rglob('*') if p.is_file()}
assert actual==manifest['runtime_files'], 'Publish contents do not match runtime package'
PUBLISH_MANIFEST.write_text(json.dumps({'source':str(MOD),'directory':str(PUBLISH),
 'version':VERSION,'runtime_files':actual,'packages':manifest['packages']},ensure_ascii=False,indent=2),encoding='utf-8')
for src,dst in [('preview.png','kanami-preview.png'),('description.txt','kanami-description.txt'),
                ('patch-notes.txt','kanami-patch-notes.txt'),('填写说明.md','kanami-upload-guide.md')]:
 shutil.copy2(ROOT/RELEASE_REL/src,PUBLISH.parent/dst)
manifest['publish_directory']=str(PUBLISH)
(OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(manifest['packages'],ensure_ascii=False,indent=2))
print('Verified stable upload directory: '+str(PUBLISH))
