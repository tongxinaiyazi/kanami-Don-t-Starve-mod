# Upper-body original artwork candidate

`register_upper.py` writes only 39 owned sprites and `registration-upper.json`.
It never writes the combined registration, production Mod or deployment.
Every frame records its source crop, explicit three-point anatomical registration,
canvas, native centre, native duration and pose semantics. Native animation matrices
are unchanged. Native pixels are used only by temporary QA readers.

## Original sources

- `../body-cutouts-source.png`: original approved costume cutouts.
- `supplement-source.png`: built-in imagegen, six original cells: bending torso
  (superseded), rib cage, pelvis bones, humerus, radius/ulna, foreshortened upper arm.
- `torso-bend-source.png`: built-in imagegen, dedicated crescent upper-back costume
  opening LEFT around the large head. Original outfit supplied for style; native
  torso/9 supplied only as geometry reference. No native pixels are sampled.
- `skirt-topdown-source.png`: built-in imagegen, dedicated radial top-down skirt.
- `skirt-topdown-closed-source.png`: final built-in edit filling the central waist
  aperture with opaque dark shorts; this is the source actually registered.

Prompt requirements: preserve original white/pink/black gothic costume and dark
ink style; isolated technical cutouts; transparent outside; no text, head, hands,
or unrelated elements. Skeleton cells use original cream shaded bones. Bend torso
is a C-shaped upper back with an empty left-facing head opening, not an intact
upright chest. Top-down skirt has a closed opaque dark shorts panel inside its belt.

## Connection corrections and verification

- Initial upright back skirt reuse for pelvis/9 was rejected and replaced with
  separately generated top-down artwork.
- First bent torso was rejected because its filled chest obstructed the giant
  head opening; replaced with a separately generated crescent upper back.
- Side chop had a roughly 2-pixel elbow gap. Extended original forearm elbow
  overlap by 3 local pixels and wrist overlap by 2 pixels.
- Back pickaxe's extreme native stretch exposed an insufficiently wide upper-arm
  elbow. Increased upper-arm end overlap by 3 pixels and calibrated elbow width.
- All 39 entries pass `registered_build` validation against their native subset.
- `check_joint_overlap.py` checks 6 complete native action cycles, actual available
  facings, both empty/carry modes: 2303 elbow and 2303 wrist comparisons. It unions
  all corresponding limb masks because native actions rename/reuse layers.
  Candidate has 27 distance alerts versus native baseline's 42. Matched by action,
  facing, frame, mode, layer and lower-arm frame: no new regression over 1 pixel.
  This is a diagnostic alpha test, not proof of correct visible occlusion. Extreme
  native stretch frames and reused weapon layers already produce baseline alerts.
- `qa_upper.py` renders full idle/run/chop/eat/pickaxe/shovel cycles plus bugnet
  (torso/9 and pelvis/9) and mounted shock (skeleton) references. Native head,
  hands and legs are temporary QA references only; all mixed files stay under
  `D:/SOFTWARE/CodexData/temp/kanami_upper_qa` and must never be distributed.

Mounted shock was additionally checked at frames 1, 3 and 7 in a larger 1000x1100
canvas (`skeleton-*.png` in the same temp QA directory) because its rider origin is
outside the ordinary standing-player crop. Original bone arm/torso/pelvis joins
remain connected in the inspected skeleton pose.

Full character integration, final original hands,
and actual in-game loading remain the integrating agent's checks. These upper
sprites are a validated candidate, not a claim that the entire Mod passed gameplay.

## 2026-11-03 cuff ownership correction

Integration with the original hand atlas exposed a duplicated wrist band. The
built-in imagegen tool edited `forearm-cuffed-edit-input.png` into
`forearm-bare-source.png`: remove every black/pink cuff, continue peach bare skin
to the wrist, preserve dark ink, taper, joint caps and exterior transparency.
No script painted over garment pixels. Only arm_lower 0/1/2/5 now use this source.
All 3 target anchors, canvas, centre and duration are exactly unchanged. Source
joint markers sit inside the limb ends to preserve overlap at elbow and wrist.
All other 35 PNG hashes, including all bone variants, remain unchanged.

`bare-wrist-detail.png` under the upper QA temp folder compares three carried idle
directions, run, eat and chop using the new original hands. The duplicate bands
are absent in these reviewed samples. The hand QA script regenerates 32 complete
native cycles with the bare forearm; no production output is used or overwritten.
`check_joint_overlap.py --hands` additionally checks current original hand masks.
These new hand-mask results are not numerically comparable with the earlier
native-hand diagnostic counts above.
Final bare-forearm/original-hand diagnostic: 2303 elbow and 2303 wrist checks;
no distance alert in any idle, run or eat frame. The remaining 28 diagnostic
alerts concern action layer/squash frames (17 elbow, 11 wrist); they must be
interpreted with occlusion and native transforms, not labeled as visible gaps.

## 2026-11-04 shoulder audit

`audit_shoulders.py` compares actual torso/upper alpha intersections through all
six native cycles and both carry modes, separately measuring foreground hair/head
occlusion. It also removes the whole headbase for body-only comparison because
the current front hairstyle is baked into headbase and `hide_hair` cannot hide it.

Torso/2 right shoulder control point changed from (66,21) to (70,13), expressed in
the unpadded native-sized canvas. Native animation matrices and arm_upper/1 were
unchanged. This eliminated 16 chop and 20 shovel shoulder-distance regressions.
The 2380 shoulder checks now have no new distance regression over native >1px.
These diagnostics include native occlusion/layer reuse and are not proof that
every listed native separation is a visible defect.

Eat frame 18 has actual torso/upper overlaps of 145/225 pixels, yet the complete
headbase hairstyle hides 100% of both upper arms. At frame 26 it hides 98.1%/100%.
The isolated-looking bare tips are forearms. The head-art integration must resolve
that foreground occlusion; moving the shoulder would not repair it.

Neck skin already exists in torso: 10.19 front, 8.76 side, 7.53 back build units.
No neck was extended to follow the head. Full authored neck top/root, native collar
top, and native idle attachment coordinates are in the temp
`kanami_shoulder_qa/neck-shoulder-landmarks.json`. The report and before/after visual
evidence are alongside it; mixed native pixels must not be redistributed.
